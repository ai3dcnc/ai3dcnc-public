import bpy, json, os
from typing import Any, Dict, List, Tuple, Optional

"""
KEROS_exportGPT — builder_mesh.py (fixed, robust v1.1)

- Safe import for Mesh section exported by our parsers/aggregator
- Accepts both wrappers {"mesh":{"meshes":[...]}} and flat lists
- Normalizes vertices and triangles before from_pydata
- Supports triangle formats: [i0,i1,i2,...], [{"indices":[i0,i1,i2]}, ...], [{"verts":[i0,i1,i2]}],
  or dicts with keys (i0,i1,i2) / (v0,v1,v2) / (a,b,c)
- Ignores malformed entries instead of crashing
- Prints short [SUMMARY] lines

Public API:
  apply_from_data(data, only_first_n=None, verbose=False) -> dict
  apply_from_file(path,  only_first_n=None, verbose=False) -> dict
Returns a stats dict: {"items": N, "built": K}
"""

# -----------------------------
# Helpers
# -----------------------------

def _read_json(path:str)->Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _unwrap_mesh_list(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(data, dict):
        return []
    # accept combined scene JSON {"mesh": {"meshes": [...]}}
    if "mesh" in data:
        mesh = data.get("mesh")
        if isinstance(mesh, dict):
            return mesh.get("meshes") or []
        if isinstance(mesh, list):
            return mesh
        return data.get("meshes") or []
    # accept flat {"meshes": [...]} or direct list already handled by caller
    return data.get("meshes") or []


def _ensure_object(name: str) -> bpy.types.Object:
    obj = bpy.data.objects.get(name)
    if obj and obj.type == 'MESH' and obj.data:
        return obj
    if obj and obj.type != 'MESH':
        obj.name = name + "_OLD"
        obj = None
    if obj is None:
        me = bpy.data.meshes.get(name) or bpy.data.meshes.new(name)
        obj = bpy.data.objects.new(name, me)
        if bpy.context.scene.collection is not None and obj.name not in bpy.context.scene.collection.objects:
            bpy.context.scene.collection.objects.link(obj)
    if obj.data is None:
        obj.data = bpy.data.meshes.new(name)
    return obj


def _as_vec3(v) -> Tuple[float, float, float]:
    if isinstance(v, (list, tuple)) and len(v) >= 3:
        return float(v[0]), float(v[1]), float(v[2])
    if isinstance(v, dict):
        x = float(v.get('x') or v.get('X') or 0.0)
        y = float(v.get('y') or v.get('Y') or 0.0)
        z = float(v.get('z') or v.get('Z') or 0.0)
        return x, y, z
    return 0.0, 0.0, 0.0


def _norm_tri(t) -> Optional[Tuple[int, int, int]]:
    a = b = c = None
    if isinstance(t, (list, tuple)) and len(t) >= 3:
        a, b, c = t[0], t[1], t[2]
    elif isinstance(t, dict):
        if isinstance(t.get('v'), (list, tuple)) and len(t['v']) >= 3:
            a, b, c = t['v'][0], t['v'][1], t['v'][2]
        elif isinstance(t.get('verts'), (list, tuple)) and len(t['verts']) >= 3:
            a, b, c = t['verts'][0], t['verts'][1], t['verts'][2]
        elif isinstance(t.get('indices'), (list, tuple)) and len(t['indices']) >= 3:
            a, b, c = t['indices'][0], t['indices'][1], t['indices'][2]
        elif all(k in t for k in ('i0','i1','i2')):
            a, b, c = t['i0'], t['i1'], t['i2']
        elif all(k in t for k in ('v0','v1','v2')):
            a, b, c = t['v0'], t['v1'], t['v2']
        elif all(k in t for k in ('a','b','c')):
            a, b, c = t['a'], t['b'], t['c']
    if a is None:
        return None
    try:
        return int(a), int(b), int(c)
    except Exception:
        return None
    try:
        return int(a), int(b), int(c)
    except Exception:
        return None


def _set_materials(obj: bpy.types.Object, item: Dict[str, Any]):
    names = item.get('materials') or item.get('material_names') or []
    if not isinstance(names, list):
        return
    # ensure slots
    for nm in names:
        if not isinstance(nm, str):
            continue
        mat = bpy.data.materials.get(nm) or bpy.data.materials.new(nm)
        if mat.name not in [s.name for s in obj.material_slots]:
            obj.data.materials.append(mat)
    # per-face material indices
    poly_mats = item.get('polygon_material_indices') or item.get('poly_material_indices')
    if isinstance(poly_mats, list) and len(poly_mats) == len(obj.data.polygons):
        for p, mi in zip(obj.data.polygons, poly_mats):
            try:
                p.material_index = int(mi)
            except Exception:
                pass


def _apply_transform(obj: bpy.types.Object, item: Dict[str, Any]):
    mw = item.get('matrix_world') or item.get('world_matrix')
    if isinstance(mw, list) and len(mw) == 16:
        try:
            import mathutils
            obj.matrix_world = mathutils.Matrix([mw[0:4], mw[4:8], mw[8:12], mw[12:16]])
            return
        except Exception:
            pass
    loc = item.get('location') or item.get('loc')
    rot = item.get('rotation_euler') or item.get('rot')
    sca = item.get('scale') or item.get('scl')
    try:
        if isinstance(loc, (list, tuple)) and len(loc) >= 3:
            obj.location = (float(loc[0]), float(loc[1]), float(loc[2]))
        if isinstance(rot, (list, tuple)) and len(rot) >= 3:
            obj.rotation_euler = (float(rot[0]), float(rot[1]), float(rot[2]))
        if isinstance(sca, (list, tuple)) and len(sca) >= 3:
            obj.scale = (float(sca[0]), float(sca[1]), float(sca[2]))
    except Exception:
        pass


# -----------------------------
# Core build
# -----------------------------

def _build_one(item: Dict[str, Any], verbose: bool=False) -> bool:
    if not isinstance(item, dict):
        return False
    name = item.get('name') or item.get('object') or "Mesh"

    # normalize geometry
    vraw = item.get('vertices') or item.get('verts') or []
    verts: List[Tuple[float, float, float]] = []
    for v in vraw:
        verts.append(_as_vec3(v))

    traw = item.get('triangles') or item.get('tris') or item.get('polygons') or []
    tris: List[Tuple[int, int, int]] = []
    # flat indices: [a,b,c,a,b,c,...]
    if traw and isinstance(traw, list) and traw and all(not isinstance(x, (list, tuple, dict)) for x in traw):
        it = iter(traw)
        try:
            while True:
                a = int(next(it)); b = int(next(it)); c = int(next(it))
                tris.append((a,b,c))
        except StopIteration:
            pass
    else:
        for t in traw:
            nt = _norm_tri(t)
            if nt is not None:
                tris.append(nt)

    # create/update object
    obj = _ensure_object(name)
    me = obj.data
    try:
        me.clear_geometry()
        me.from_pydata(verts, [], tris)
        me.validate()
        me.update()
    except Exception as e:
        print(f"[WARN] build failed for {name}: {e}")
        return False

    # materials and transform if present
    _set_materials(obj, item)
    _apply_transform(obj, item)

    return True


# -----------------------------
# Public API
# -----------------------------

def apply_from_data(data: Dict[str, Any] | List[Dict[str, Any]],
                    only_first_n: Optional[int] = None,
                    verbose: bool = False) -> Dict[str, int]:
    # accept either wrapped dict or direct list
    items: List[Dict[str, Any]]
    if isinstance(data, list):
        items = data
    else:
        items = _unwrap_mesh_list(data)

    if only_first_n is not None:
        items = items[:max(0, int(only_first_n))]

    built = 0
    for it in items:
        if _build_one(it, verbose=verbose):
            built += 1

    print(f"[SUMMARY] mesh_apply: items={len(items)} built={built}")
    return {"items": len(items), "built": built}


def apply_from_file(path: str,
                    only_first_n: Optional[int] = None,
                    verbose: bool = False) -> Dict[str, int]:
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    data = _read_json(path)
    return apply_from_data(data, only_first_n=only_first_n, verbose=verbose)


# -----------------------------
# Self-test (disabled)
# -----------------------------
if __name__ == "__main__" and False:
    p = bpy.path.abspath("//_EXPORTS/scene_export_test.json")
    apply_from_file(p, only_first_n=1, verbose=True)
