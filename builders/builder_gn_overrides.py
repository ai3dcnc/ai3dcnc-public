import bpy, json, os
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

"""
KEROS_exportGPT — Geometry Nodes Overrides Builder — Perfect v1.2
Blender 3.6 ↔ 4.2 LTS safe, zero‑crash philosophy, short [SUMMARY].

What it does
- Applies GN **overrides** onto objects' Geometry Nodes modifiers, in correct order.
- Case‑insensitive lookup for **objects**, **modifiers**, and **node groups**.
- Accepts inputs by **name**, **identifier** (e.g. "Input_3" / "Socket_3"), or **Socket_N / Input_N**.
- Handles value types: float/int/bool, 3D vectors, 4D colors, strings. (Object/Collection links are ignored in overrides here.)
- Creates **placeholders** when asked: missing object → Mesh Cube; missing group/modifier → minimal GN group + Nodes modifier.
- Honors optional flags: `enabled_viewport`, `enabled_render`.

Accepted JSON shapes
- {"geometry_nodes": {"overrides": [ ... ]}}
- {"overrides": [ ... ]}
- raw list of overrides

Each override item (common fields)
{
  "object_name": "MyObject",
  "modifier_name": "MyGN",            # optional
  "group_name": "MyGroup",            # recommended
  "enabled_viewport": true,            # optional
  "enabled_render": true,              # optional
  "inputs": {                          # name or identifier → value
     "Socket_2": 0.5,
     "Input_3": [1.0, 0.0, 0.0],
     "MyScalar": 2.0,
     "MyToggle": true
  }
}

Public API
- apply_from_file(path, create_placeholders=True, verbose=False)
- apply_from_data(data, create_placeholders=True, verbose=False)

Prints a single line:
[SUMMARY] gn_overrides: overrides=.. targets=.. created_modifiers=.. inputs_set=.. failed=.. placeholders=.. missing_objects=.. missing_groups=..
"""

# =============================
# Helpers — search & creation
# =============================

def _ci_equal(a: Optional[str], b: Optional[str]) -> bool:
    return (a or '').lower() == (b or '').lower()


def _find_object_ci(name: Optional[str]) -> Optional[bpy.types.Object]:
    if not name:
        return None
    lname = name.lower()
    # exact
    for ob in bpy.data.objects:
        if ob.name.lower() == lname:
            return ob
    # startswith
    for ob in bpy.data.objects:
        if ob.name.lower().startswith(lname):
            return ob
    # contains
    for ob in bpy.data.objects:
        if lname in ob.name.lower():
            return ob
    return None


def _ensure_mesh_placeholder(name: str) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    ob = bpy.context.active_object
    ob.name = name
    return ob


def _find_node_group_ci(name: Optional[str]) -> Optional[bpy.types.NodeTree]:
    if not name:
        return None
    lname = name.lower()
    # direct
    ng = bpy.data.node_groups.get(name)
    if ng:
        return ng
    for g in bpy.data.node_groups:
        try:
            if g.bl_idname != 'GeometryNodeTree':
                continue
        except Exception:
            continue
        if g.name.lower() == lname:
            return g
    for g in bpy.data.node_groups:
        try:
            if g.bl_idname != 'GeometryNodeTree':
                continue
        except Exception:
            continue
        if lname in g.name.lower():
            return g
    return None


def _ensure_minimal_group(name: str) -> bpy.types.NodeTree:
    """Create a minimal GeometryNodeTree with a Geometry input and output
    so that modifier properties (Input_N/Socket_N) are available.
    Idempotent: if exists, returns it as-is.
    """
    tree = bpy.data.node_groups.get(name)
    if tree and getattr(tree, 'bl_idname', '') == 'GeometryNodeTree':
        return tree
    tree = bpy.data.node_groups.new(name, 'GeometryNodeTree')
    nodes = tree.nodes
    links = tree.links

    # Clear and create minimal IO
    try:
        nodes.clear()
    except Exception:
        pass

    # Interface sockets (order is stable for Socket_N mapping)
    try:
        iface = tree.interface
        iface.clear()
        iface.new_socket("Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
    except Exception:
        # Fallback: ignore interface on very old versions
        pass

    try:
        # Nodes: Group Input -> Group Output, pass-through geometry
        n_in = nodes.new('NodeGroupInput')
        n_out = nodes.new('NodeGroupOutput')
        n_in.location = (-200, 0)
        n_out.location = (200, 0)
        links.new(n_in.outputs.get('Geometry'), n_out.inputs.get('Geometry'))
    except Exception:
        pass

    return tree


def _find_nodes_modifier_ci(obj: bpy.types.Object,
                            group_name: Optional[str] = None,
                            modifier_name: Optional[str] = None) -> Optional[bpy.types.NodesModifier]:
    if obj is None:
        return None

    # 1) match by modifier_name (CI)
    if modifier_name:
        lname = modifier_name.lower()
        for md in obj.modifiers:
            if getattr(md, 'type', '') != 'NODES':
                continue
            if md.name.lower() == lname:
                return md

    # 2) match by node_group name (CI)
    if group_name:
        lg = group_name.lower()
        for md in obj.modifiers:
            if getattr(md, 'type', '') != 'NODES':
                continue
            ng = getattr(md, 'node_group', None)
            try:
                if ng and ng.name.lower() == lg:
                    return md
            except Exception:
                pass

    # 3) fallback: first NODES modifier
    for md in obj.modifiers:
        if getattr(md, 'type', '') == 'NODES':
            return md
    return None


def _ensure_nodes_modifier(obj: bpy.types.Object,
                           group: bpy.types.NodeTree,
                           modifier_name: Optional[str] = None) -> bpy.types.NodesModifier:
    # Reuse existing modifier already bound to this group if possible
    md = _find_nodes_modifier_ci(obj, group_name=group.name, modifier_name=modifier_name)
    if md:
        try:
            md.node_group = group
        except Exception:
            pass
        return md
    # else create new
    name = modifier_name or group.name
    md = obj.modifiers.new(name=name, type='NODES')
    try:
        md.node_group = group
    except Exception:
        pass
    return md


# ======================================
# Inputs mapping & setting (safe, CI)
# ======================================

class _IfaceSocket:
    __slots__ = ("name", "identifier", "index")
    def __init__(self, name: str, identifier: str, index: int):
        self.name = name
        self.identifier = identifier
        self.index = index


def _collect_interface_inputs(tree: Optional[bpy.types.NodeTree]) -> List[_IfaceSocket]:
    out: List[_IfaceSocket] = []
    if not tree:
        return out
    # Blender 4.x: tree.interface.items_tree (sockets in order)
    try:
        items = list(getattr(tree.interface, 'items_tree'))
        idx = 0
        for it in items:
            try:
                if getattr(it, 'in_out', None) == 'INPUT' and getattr(it, 'item_type', None) == 'SOCKET':
                    name = getattr(it, 'name', f'Input_{idx}')
                    ident = getattr(it, 'identifier', f'Input_{idx}')
                    out.append(_IfaceSocket(name, ident, idx))
                    idx += 1
            except Exception:
                pass
        if out:
            return out
    except Exception:
        pass

    # Fallback (older versions): try to infer from modifier ID properties later
    return out


def _key_candidates(sock: _IfaceSocket) -> List[str]:
    idx = sock.index
    ident = sock.identifier or f"Input_{idx}"
    # Try the provided identifier first
    cands = [ident]
    # Then both Input_N and Socket_N forms
    cands.append(f"Input_{idx}")
    cands.append(f"Socket_{idx}")
    return cands


def _coerce_value(v: Any) -> Any:
    # Accept scalars, 3/4 tuples, strings; pass others as-is.
    try:
        if isinstance(v, bool):
            return bool(v)
        if isinstance(v, int):
            return int(v)
        if isinstance(v, float):
            return float(v)
        if isinstance(v, (list, tuple)):
            if len(v) == 3 or len(v) == 4:
                return tuple(float(x) for x in v)
            if len(v) == 2:
                return tuple(float(x) for x in v)
        if isinstance(v, str):
            return v
    except Exception:
        pass
    return v


def _set_modifier_input(mod: bpy.types.NodesModifier, key: str, value: Any) -> bool:
    """Set a single modifier input key (IDProperty) if present.
    Also disables `<key>_use_attribute` when available.
    Returns True if a property was set.
    """
    ok = False
    val = _coerce_value(value)
    try:
        mod[key] = val
        ok = True
    except Exception:
        # some types need tuple conversion or fail silently
        try:
            if isinstance(val, list):
                mod[key] = tuple(val)
                ok = True
        except Exception:
            pass
    # Try to disable attribute mode companion flag
    if ok:
        try:
            attr_flag = f"{key}_use_attribute"
            if attr_flag in mod.keys():
                mod[attr_flag] = False
        except Exception:
            pass
    return ok


def _apply_inputs(mod: bpy.types.NodesModifier,
                  inputs_map: Dict[str, Any],
                  verbose: bool = False) -> Tuple[int, int]:
    """Apply inputs by names/identifiers. Returns (set_count, failed_count)."""
    set_cnt = 0
    fail_cnt = 0

    # Build interface map once
    iface = _collect_interface_inputs(getattr(mod, 'node_group', None))

    def find_socket_by_name(name: str) -> Optional[_IfaceSocket]:
        lname = (name or '').lower()
        for s in iface:
            if s.name.lower() == lname:
                return s
        return None

    for raw_key, value in (inputs_map or {}).items():
        key = str(raw_key)
        done = False

        # 1) If key looks like Input_N / Socket_N, set directly
        if key.startswith('Input_') or key.startswith('Socket_'):
            if _set_modifier_input(mod, key, value):
                set_cnt += 1; done = True
            else:
                # try the other prefix with same index
                try:
                    idx = int(key.split('_', 1)[1])
                    alt = f"Socket_{idx}" if key.startswith('Input_') else f"Input_{idx}"
                    if _set_modifier_input(mod, alt, value):
                        set_cnt += 1; done = True
                except Exception:
                    pass

        # 2) Try by exact identifier from interface
        if not done and iface:
            s = None
            for it in iface:
                if it.identifier == key:
                    s = it; break
            if s:
                for cand in _key_candidates(s):
                    if _set_modifier_input(mod, cand, value):
                        set_cnt += 1; done = True; break

        # 3) Try by socket name
        if not done:
            s = find_socket_by_name(key)
            if s:
                for cand in _key_candidates(s):
                    if _set_modifier_input(mod, cand, value):
                        set_cnt += 1; done = True; break

        if not done:
            fail_cnt += 1
            if verbose:
                print(f"[WARN] GN input not applied: key={key}")

    return set_cnt, fail_cnt


# =============================
# Core apply API
# =============================

def apply_single_override(obj_name: Optional[str],
                          group_name: Optional[str],
                          modifier_name: Optional[str],
                          inputs: Optional[Dict[str, Any]],
                          create_placeholders: bool = True,
                          enabled_viewport: Optional[bool] = None,
                          enabled_render: Optional[bool] = None,
                          verbose: bool = False) -> Dict[str, Any]:
    stats = {
        'target': obj_name or '',
        'group': group_name or '',
        'modifier': modifier_name or '',
        'created_modifier': 0,
        'placeholders': 0,
        'inputs_set': 0,
        'inputs_failed': 0,
        'missing_object': 0,
        'missing_group': 0,
    }

    # Object
    obj = _find_object_ci(obj_name)
    if not obj:
        if create_placeholders:
            obj = _ensure_mesh_placeholder(obj_name or 'KRS_GN_Target')
            stats['placeholders'] += 1
            if verbose:
                print(f"[WARN] missing object → placeholder created: {obj.name}")
        else:
            stats['missing_object'] = 1
            return stats

    # Group
    group = _find_node_group_ci(group_name) if group_name else None
    if not group:
        if create_placeholders and group_name:
            group = _ensure_minimal_group(group_name)
            stats['placeholders'] += 1
            if verbose:
                print(f"[WARN] missing node group → placeholder group created: {group.name}")
        else:
            stats['missing_group'] = 1
            return stats

    # Ensure Nodes modifier bound to this group
    mod = _find_nodes_modifier_ci(obj, group_name=group.name, modifier_name=modifier_name)
    if not mod:
        mod = _ensure_nodes_modifier(obj, group, modifier_name=modifier_name)
        stats['created_modifier'] += 1
    else:
        # Ensure correct group
        try:
            mod.node_group = group
        except Exception:
            pass

    # Apply visibility flags
    try:
        if enabled_viewport is not None:
            mod.show_viewport = bool(enabled_viewport)
        if enabled_render is not None:
            mod.show_render = bool(enabled_render)
    except Exception:
        pass

    # Apply inputs
    s, f = _apply_inputs(mod, inputs or {}, verbose=verbose)
    stats['inputs_set'] += s
    stats['inputs_failed'] += f

    return stats


# Dispatcher over a data blob

def _overrides_from_data(data: Any) -> List[Dict[str, Any]]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        gn = data.get('geometry_nodes')
        if isinstance(gn, dict) and isinstance(gn.get('overrides'), list):
            return gn['overrides']
        if isinstance(data.get('overrides'), list):
            return data['overrides']
    return []


def apply_from_data(data: Any, create_placeholders: bool = True, verbose: bool = False) -> str:
    items = _overrides_from_data(data)
    overrides_total = len(items)
    targets = 0
    created_mods = 0
    placeholders = 0
    inputs_set = 0
    inputs_failed = 0
    missing_objects = 0
    missing_groups = 0

    for ov in items:
        obj_name = ov.get('object_name') or ov.get('object')
        group_name = ov.get('group_name') or ov.get('group')
        modifier_name = ov.get('modifier_name') or None
        enabled_vp = ov.get('enabled_viewport')
        enabled_rn = ov.get('enabled_render')
        inputs = ov.get('inputs') or {}

        st = apply_single_override(obj_name, group_name, modifier_name, inputs,
                                   create_placeholders=create_placeholders,
                                   enabled_viewport=enabled_vp,
                                   enabled_render=enabled_rn,
                                   verbose=verbose)
        targets += 1
        created_mods += st['created_modifier']
        placeholders += st['placeholders']
        inputs_set += st['inputs_set']
        inputs_failed += st['inputs_failed']
        missing_objects += st['missing_object']
        missing_groups += st['missing_group']

    print(f"[SUMMARY] gn_overrides: overrides={overrides_total} targets={targets} created_modifiers={created_mods} inputs_set={inputs_set} failed={inputs_failed} placeholders={placeholders} missing_objects={missing_objects} missing_groups={missing_groups}")
    return ("overrides=%d targets=%d created_modifiers=%d inputs_set=%d failed=%d placeholders=%d "
            "missing_objects=%d missing_groups=%d" % (overrides_total, targets, created_mods, inputs_set, inputs_failed, placeholders, missing_objects, missing_groups))


def apply_from_file(path: str, create_placeholders: bool = True, verbose: bool = False) -> str:
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return apply_from_data(data, create_placeholders=create_placeholders, verbose=verbose)


# Backward‑compat alias
import_from_file = apply_from_file
import_from_data = apply_from_data
