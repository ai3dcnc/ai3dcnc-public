import bpy
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Iterable, Set

"""
KEROS_exportGPT — Mesh Parser for Blender 4.2 LTS

Exports mesh objects (with optional modifiers, UVs, vertex colors, normals) to JSON.
Target use: downstream AI/CNC pipelines.

Default export path: G:/My Drive/BLENDER_EXPORT
Default filename: scene_export_[timestamp].json

Tested Blender: 4.2 LTS

Notes:
- Uses depsgraph + evaluated objects when apply_modifiers=True.
- Color Attributes API (Blender 4.x): mesh.color_attributes (domains: POINT or CORNER).
- UVs: mesh.uv_layers, exported per-triangle-corner (consistent with triangulation).
- Materials: exported at object level + per triangle material_index.
- Transform: location/rotation_euler/scale and world_matrix (flattened row-major).
- Visibility: default exports only *visible* objects (viewport visibility via visible_get) and skips hide_render if set.
- Recommended workflow: for early testing use target_collections=None (export all visible meshes). Later you can restrict to a collection like "KRS_EXPORT".

Tested Blender: 4.2 LTS

Notes:
- Uses depsgraph + evaluated objects when apply_modifiers=True.
- Color Attributes API (Blender 4.x): mesh.color_attributes (domains: POINT or CORNER).
- UVs: mesh.uv_layers, exported per-triangle-corner (consistent with triangulation).
- Materials: exported at object level + per triangle material_index.
- Transform: location/rotation_euler/scale and world_matrix (flattened row-major).

You can import this as a module and call export_mesh() to get a Python dict,
or run the file inside Blender to also write the JSON to disk.
"""

# ===============================
# Config
# ===============================
DEFAULT_EXPORT_DIR = r"G:/My Drive/BLENDER_EXPORT"
DEFAULT_FILENAME_FMT = "scene_export_{timestamp}.json"

# ===============================
# Dataclasses (typed schema)
# ===============================
@dataclass
class Tri:
    v: Tuple[int, int, int]                 # vertex indices
    material_index: int                     # material slot index on object
    uvs: Dict[str, Tuple[Tuple[float, float], Tuple[float, float], Tuple[float, float]]] = field(default_factory=dict)
    # vertex colors by attribute name; values are triples of RGB(A) tuples per corner
    colors: Dict[str, Tuple[Tuple[float, float, float, float], Tuple[float, float, float, float], Tuple[float, float, float, float]]] = field(default_factory=dict)

@dataclass
class MeshExport:
    name: str
    object_name: str
    collection_path: List[str]
    transform: Dict[str, List[float]]      # location, rotation_euler, scale
    world_matrix: List[float]              # 16 floats, row-major
    dimensions: Dict[str, List[float]]     # bbox_min, bbox_max (world)
    vertices: List[Tuple[float, float, float]]
    normals: Optional[List[Tuple[float, float, float]]] = None
    materials: List[str] = field(default_factory=list)
    triangles: List[Tri] = field(default_factory=list)

@dataclass
class MeshExportBundle:
    meshes: List[MeshExport]
    meta: Dict[str, str]

# ===============================
# Helpers
# ===============================

def ensure_dir(path: str) -> None:
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def get_collection_hierarchy(obj: bpy.types.Object) -> List[str]:
    """Returns the list of collection names from root to the deepest collection that directly contains the object.
    If object is in multiple collections, returns the longest path of names (heuristic).
    """
    paths: List[List[str]] = []

    def walk(coll: bpy.types.Collection, trail: List[str]):
        trail2 = trail + [coll.name]
        if obj.name in coll.objects:
            paths.append(trail2)
        for child in coll.children:
            walk(child, trail2)

    # Top-level collections are in bpy.context.scene.collection (root) and all view layer collections
    for c in bpy.data.collections:
        try:
            walk(c, [])
        except RecursionError:
            pass

    if not paths:
        return []
    # Longest path
    return max(paths, key=len)


def flatten_matrix(m) -> List[float]:
    # row-major 4x4
    return [m[i][j] for i in range(4) for j in range(4)]


def object_world_bbox(obj: bpy.types.Object) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
    import mathutils
    coords = [obj.matrix_world @ mathutils.Vector(corner) for corner in obj.bound_box]
    xs = [v.x for v in coords]; ys = [v.y for v in coords]; zs = [v.z for v in coords]
    return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))


def iter_objects_in_collections(target_collections: Optional[Iterable[str]]) -> Iterable[bpy.types.Object]:
    """Yield mesh objects filtered by collection names (or all if None).
    Includes objects in children collections.
    """
    if not target_collections:
        for obj in bpy.data.objects:
            if obj.type == 'MESH':
                yield obj
        return

    # Build allowed set
    allowed: Set[bpy.types.Object] = set()

    def collect_objects(coll: bpy.types.Collection):
        for obj in coll.objects:
            if obj.type == 'MESH':
                allowed.add(obj)
        for child in coll.children:
            collect_objects(child)

    names = set(target_collections)
    for coll in bpy.data.collections:
        if coll.name in names:
            collect_objects(coll)

    for obj in allowed:
        yield obj


# ===============================
# Core extraction
# ===============================

def extract_mesh_of_object(
    obj: bpy.types.Object,
    *,
    apply_modifiers: bool = True,
    include_uvs: bool = True,
    include_colors: bool = True,
    include_normals: bool = True,
    triangulate: bool = True,
) -> Optional[MeshExport]:
    """Extracts mesh data from a single object as MeshExport.
    Returns None if object has no usable mesh data.
    """
    if obj.type != 'MESH':
        return None

    depsgraph = bpy.context.evaluated_depsgraph_get()
    if apply_modifiers:
        eval_obj = obj.evaluated_get(depsgraph)
        me = eval_obj.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
        cleanup = (eval_obj, True)
    else:
        # Use original (make a temp copy to avoid touching original data)
        me = obj.data.copy()
        cleanup = (obj, False)

    try:
        # Calculate derived data (safe normals for Blender 4.2)
        precomputed_normals = None
        if include_normals:
            try:
                did_any = False
                if hasattr(me, "calc_normals_split"):
                    try:
                        me.calc_normals_split()
                        did_any = True
                    except Exception:
                        pass
                if not did_any and hasattr(me, "calc_normals"):
                    try:
                        me.calc_normals()
                        did_any = True
                    except Exception:
                        pass
                if not did_any:
                    import bmesh
                    bm = bmesh.new()
                    bm.from_mesh(me)
                    bm.normal_update()
                    precomputed_normals = [(v.normal.x, v.normal.y, v.normal.z) for v in bm.verts]
                    bm.free()
            except Exception:
                import bmesh
                bm = bmesh.new()
                bm.from_mesh(me)
                bm.normal_update()
                precomputed_normals = [(v.normal.x, v.normal.y, v.normal.z) for v in bm.verts]
                bm.free()

        if triangulate:
            me.calc_loop_triangles()

        # Vertices
        vertices = [(v.co.x, v.co.y, v.co.z) for v in me.vertices]
        normals = None
        if include_normals:
            if precomputed_normals is not None:
                normals = precomputed_normals
            else:
                normals = [(v.normal.x, v.normal.y, v.normal.z) for v in me.vertices]

        # Materials
        material_names = [slot.material.name if slot.material else "" for slot in obj.material_slots]

        # Prepare UVs and Colors accessors (per loop)
        uv_layers = {uv.name: uv for uv in me.uv_layers} if include_uvs else {}
        color_attrs = {ca.name: ca for ca in me.color_attributes} if include_colors else {}

        # Triangles
        triangles: List[Tri] = []
        if triangulate:
            # per-loop arrays
            loop_to_vert = [l.vertex_index for l in me.loops]

            def get_uv_triplet(layer, li0, li1, li2):
                data = layer.data
                return (
                    (data[li0].uv.x, data[li0].uv.y),
                    (data[li1].uv.x, data[li1].uv.y),
                    (data[li2].uv.x, data[li2].uv.y),
                )

            def get_color_triplet(attr, li0, li1, li2):
                data = attr.data
                def rgba(i):
                    c = data[i].color
                    # Some attributes may be RGB only; pad alpha = 1.0
                    if len(c) == 3:
                        return (c[0], c[1], c[2], 1.0)
                    return (c[0], c[1], c[2], c[3])
                return (rgba(li0), rgba(li1), rgba(li2))

            for tri in me.loop_triangles:
                li0, li1, li2 = tri.loops
                vi0, vi1, vi2 = loop_to_vert[li0], loop_to_vert[li1], loop_to_vert[li2]
                t = Tri(v=(vi0, vi1, vi2), material_index=tri.material_index)

                if include_uvs:
                    for name, layer in uv_layers.items():
                        t.uvs[name] = get_uv_triplet(layer, li0, li1, li2)

                if include_colors:
                    # Export CORNER domain attrs per loop; POINT domain will be reindexed per corner using vertex index
                    for name, attr in color_attrs.items():
                        if attr.domain == 'CORNER':
                            t.colors[name] = get_color_triplet(attr, li0, li1, li2)
                        elif attr.domain == 'POINT':
                            # Map vertex colors to corners via vertex indices
                            data = attr.data
                            def vcol(vi):
                                c = data[vi].color
                                if len(c) == 3:
                                    return (c[0], c[1], c[2], 1.0)
                                return (c[0], c[1], c[2], c[3])
                            t.colors[name] = (vcol(vi0), vcol(vi1), vcol(vi2))

                triangles.append(t)
        else:
            # Non-triangulated: export polygon loops as fan triangles for robustness
            me.calc_loop_triangles()
            return extract_mesh_of_object(
                obj,
                apply_modifiers=apply_modifiers,
                include_uvs=include_uvs,
                include_colors=include_colors,
                include_normals=include_normals,
                triangulate=True,
            )

        # Transform and bbox
        loc = list(obj.location)
        rot = list(obj.rotation_euler)
        scale = list(obj.scale)
        wm = flatten_matrix(obj.matrix_world)
        bb_min, bb_max = object_world_bbox(obj)

        export = MeshExport(
            name=(obj.data.name or obj.name),
            object_name=obj.name,
            collection_path=get_collection_hierarchy(obj),
            transform={"location": loc, "rotation_euler": rot, "scale": scale},
            world_matrix=wm,
            dimensions={"bbox_min": list(bb_min), "bbox_max": list(bb_max)},
            vertices=vertices,
            normals=normals,
            materials=material_names,
            triangles=triangles,
        )
        return export

    finally:
        # cleanup temporary mesh
        eval_obj, used_eval = cleanup
        if used_eval:
            try:
                eval_obj.to_mesh_clear()
            except Exception:
                pass
        else:
            try:
                me.user_clear()
                bpy.data.meshes.remove(me)
            except Exception:
                pass


# ===============================
# Public API
# ===============================

def export_mesh(
    *,
    target_collections: Optional[Iterable[str]] = None,
    only_visible: bool = True,
    apply_modifiers: bool = True,
    include_uvs: bool = True,
    include_colors: bool = True,
    include_normals: bool = True,
    triangulate: bool = True,
) -> MeshExportBundle:
    """Collect all matching mesh objects and export them into a typed bundle."""
    meshes: List[MeshExport] = []

    for obj in iter_objects_in_collections(target_collections):
        # Visibility gate (viewport + render)
        if only_visible:
            try:
                if not obj.visible_get(bpy.context.view_layer):
                    continue
            except Exception:
                # Fallback for safety
                if getattr(obj, "hide_viewport", False) or obj.hide_get():
                    continue
            if getattr(obj, "hide_render", False):
                continue

        ex = extract_mesh_of_object(
            obj,
            apply_modifiers=apply_modifiers,
            include_uvs=include_uvs,
            include_colors=include_colors,
            include_normals=include_normals,
            triangulate=triangulate,
        )
        if ex is not None:
            meshes.append(ex)

    meta = {
        "exporter": "KEROS_exportGPT.mesh",
        "blender_version": bpy.app.version_string,
        "timestamp": datetime.now().isoformat(timespec='seconds'),
        "apply_modifiers": str(apply_modifiers),
        "triangulate": str(triangulate),
        "only_visible": str(only_visible),
        "target_collections": ",".join(target_collections) if target_collections else "",
    }
    return MeshExportBundle(meshes=meshes, meta=meta)


def write_json(bundle: MeshExportBundle, export_dir: str = DEFAULT_EXPORT_DIR, filename_fmt: str = DEFAULT_FILENAME_FMT) -> str:
    ensure_dir(export_dir)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    path = os.path.join(export_dir, filename_fmt.format(timestamp=timestamp))

    # Convert dataclasses -> dict recursively
    def tri_to_dict(t: Tri):
        d = {
            "v": list(t.v),
            "material_index": t.material_index,
        }
        if t.uvs:
            d["uvs"] = {k: [list(uv) for uv in v] for k, v in t.uvs.items()}
        if t.colors:
            d["colors"] = {k: [list(c) for c in v] for k, v in t.colors.items()}
        return d

    data = {
        "mesh": {
            "meshes": [
                {
                    "name": m.name,
                    "object_name": m.object_name,
                    "collection_path": m.collection_path,
                    "transform": m.transform,
                    "world_matrix": m.world_matrix,
                    "dimensions": m.dimensions,
                    "vertices": [list(v) for v in m.vertices],
                    "normals": ([list(n) for n in m.normals] if m.normals else None),
                    "materials": m.materials,
                    "triangles": [tri_to_dict(t) for t in m.triangles],
                }
                for m in bundle.meshes
            ],
            "meta": bundle.meta,
        }
    }

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

    print(f"[INFO] Mesh export written: {path}")
    return path


# ===============================
# CLI / Script entry
# ===============================
if __name__ == "__main__":
    bundle = export_mesh(
        target_collections=None,  # export all mesh objects
        only_visible=True,
        apply_modifiers=True,
        include_uvs=True,
        include_colors=True,
        include_normals=True,
        triangulate=True,
    )
    write_json(bundle)
