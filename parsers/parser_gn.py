import bpy
import json
import os
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

"""
KEROS_exportGPT — Geometry Nodes Parser v4 (Blender 3.6 ↔ 4.2 safe)

Focus: **future‑proofing for new/unknown nodes** so exports don't break later.

What v4 adds over v3:
- For every node we export `bl_idname`.
- For **unknown nodes** (idname not in our allowlist):
  - `is_unknown=True`
  - `props` = safe RNA snapshot of node properties (numbers/enums/bools/vectors/strings trimmed)
  - `inputs_defaults` = defaults for unlinked inputs (name, type, value)
- Scene‑independent **tree fingerprint** (sha1 of nodes+links) in `meta.tree_fingerprint` per group.

Config flags:
- `DUMP_PROPS_UNKNOWN_ONLY=True`  # if False dumps props for all nodes (heavier)
- `MAX_UNKNOWN_DETAILS=24`        # how many unknown nodes to mirror in meta preview

Defaults:
- target_collections=None (scan whole scene)
- only_visible=True
- Writes JSON to G:/My Drive/BLENDER_EXPORT/scene_export_[timestamp].json
"""

# ===============================
# Config
# ===============================
DEFAULT_EXPORT_DIR = r"G:/My Drive/BLENDER_EXPORT"
DEFAULT_FILENAME_FMT = "scene_export_{timestamp}.json"

ALLOWED_NODE_PREFIXES: Sequence[str] = ("GeometryNode", "ShaderNode", "FunctionNode")
ALLOWED_NODE_ID_EXACT: Sequence[str] = ("NodeGroupInput", "NodeGroupOutput", "NodeFrame", "NodeReroute")

DUMP_PROPS_UNKNOWN_ONLY = True
MAX_UNKNOWN_DETAILS = 24

# ===============================
# Dataclasses
# ===============================
@dataclass
class GNSocket:
    name: str
    identifier: str
    socket_type: str
    default: Any

@dataclass
class GNNode:
    name: str
    type: str
    bl_idname: str
    label: str
    location: Tuple[float, float]
    group_ref: Optional[str] = None
    is_unknown: bool = False
    props: Optional[Dict[str, Any]] = None
    inputs_defaults: Optional[List[Dict[str, Any]]] = None

@dataclass
class GNLink:
    from_node: str
    from_socket: str
    to_node: str
    to_socket: str

@dataclass
class GNGroupExport:
    name: str
    inputs: List[GNSocket]
    outputs: List[GNSocket]
    nodes: List[GNNode]
    links: List[GNLink]
    fingerprint: str

@dataclass
class GNObjectOverride:
    object_name: str
    modifier_name: str
    group_name: str
    enabled_viewport: bool
    enabled_render: bool
    inputs: Dict[str, Any]

@dataclass
class GNBundle:
    groups: List[GNGroupExport]
    overrides: List[GNObjectOverride]
    meta: Dict[str, str]

# ===============================
# Helpers
# ===============================

def ensure_dir(path: str) -> None:
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def iter_objects_in_collections(target_collections: Optional[Iterable[str]]) -> Iterable[bpy.types.Object]:
    if not target_collections:
        yield from bpy.data.objects
        return
    allowed = set()
    def collect_objects(coll: bpy.types.Collection):
        for obj in coll.objects:
            allowed.add(obj)
        for child in coll.children:
            collect_objects(child)
    names = set(target_collections)
    for coll in bpy.data.collections:
        if coll.name in names:
            collect_objects(coll)
    yield from allowed

# ---- Interface sockets: 3.6 (group.inputs/outputs) vs 4.2 (group.interface.items_tree)

def _iter_group_sockets(group: bpy.types.NodeTree, direction: str) -> List[Any]:
    # Try legacy first
    try:
        return list(group.inputs if direction == 'INPUT' else group.outputs)
    except Exception:
        pass
    # 4.x API
    try:
        iface = getattr(group, 'interface', None)
        items = getattr(iface, 'items_tree', None)
        out = []
        if items:
            for it in items:
                try:
                    if getattr(it, 'item_type', '') == 'SOCKET' and getattr(it, 'in_out', '') == direction:
                        out.append(it)
                except Exception:
                    pass
        return out
    except Exception:
        return []


def iter_group_inputs(group: bpy.types.NodeTree) -> List[Any]:
    return _iter_group_sockets(group, 'INPUT')


def iter_group_outputs(group: bpy.types.NodeTree) -> List[Any]:
    return _iter_group_sockets(group, 'OUTPUT')


def _sanitize(value: Any) -> Any:
    try:
        # ID datablocks → name only
        import bpy.types as T
        if isinstance(value, T.ID):
            return getattr(value, 'name', str(value))
    except Exception:
        pass
    # Vectors/arrays
    try:
        if hasattr(value, '__iter__') and not isinstance(value, (str, bytes)):
            return [float(x) if isinstance(x, (int, float)) else str(x) for x in list(value)]
    except Exception:
        pass
    # Primitives
    if isinstance(value, (bool, int, float)):
        return float(value) if isinstance(value, (int, float)) else bool(value)
    if isinstance(value, str):
        return value[:256]
    # Fallback
    try:
        return float(value)
    except Exception:
        return str(value)


def _dump_node_props(n: bpy.types.Node) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    try:
        rna = n.bl_rna
        for prop in rna.properties:
            try:
                key = prop.identifier
                if key in {"rna_type", "name", "label", "inputs", "outputs", "select", "parent", "location", "type"}:
                    continue
                val = getattr(n, key)
                out[key] = _sanitize(val)
            except Exception:
                continue
    except Exception:
        pass
    return out


def _dump_inputs_defaults(n: bpy.types.Node) -> List[Dict[str, Any]]:
    arr: List[Dict[str, Any]] = []
    for s in n.inputs:
        try:
            if s.is_linked:
                continue
            dv = getattr(s, 'default_value', None)
            arr.append({
                'name': s.name,
                'type': getattr(s, 'type', ''),
                'default': _sanitize(dv),
            })
        except Exception:
            continue
    return arr


def to_default_value(sock) -> Any:
    dv = None
    if hasattr(sock, 'default_value'):
        dv = getattr(sock, 'default_value')
    elif hasattr(sock, 'default_float_value'):
        dv = getattr(sock, 'default_float_value')
    elif hasattr(sock, 'default_int_value'):
        dv = getattr(sock, 'default_int_value')
    elif hasattr(sock, 'default_bool_value'):
        dv = getattr(sock, 'default_bool_value')
    return _sanitize(dv)


def gn_group_to_export(group: bpy.types.NodeTree, unknown_accum: Optional[List[Tuple[str, str, str]]] = None) -> GNGroupExport:
    inputs: List[GNSocket] = []
    for s in iter_group_inputs(group):
        inputs.append(GNSocket(
            name=getattr(s, 'name', ''),
            identifier=getattr(s, 'identifier', getattr(s, 'name', '')),
            socket_type=getattr(s, 'type', getattr(s, 'socket_type', '')),
            default=to_default_value(s),
        ))

    outputs: List[GNSocket] = []
    for s in iter_group_outputs(group):
        outputs.append(GNSocket(
            name=getattr(s, 'name', ''),
            identifier=getattr(s, 'identifier', getattr(s, 'name', '')),
            socket_type=getattr(s, 'type', getattr(s, 'socket_type', '')),
            default=to_default_value(s),
        ))

    nodes: List[GNNode] = []
    for n in group.nodes:
        group_ref = None
        if n.type == 'GROUP' and getattr(n, 'node_tree', None):
            group_ref = n.node_tree.name
        bl_id = getattr(n, 'bl_idname', '')
        is_allowed = (bl_id in ALLOWED_NODE_ID_EXACT) or any(bl_id.startswith(p) for p in ALLOWED_NODE_PREFIXES)
        is_unknown = bool(bl_id) and not is_allowed
        if is_unknown and unknown_accum is not None:
            unknown_accum.append((group.name, n.name, bl_id))
        props = _dump_node_props(n) if (is_unknown or not DUMP_PROPS_UNKNOWN_ONLY) else None
        inputs_defaults = _dump_inputs_defaults(n) if is_unknown else None
        nodes.append(GNNode(
            name=n.name,
            type=n.type,
            bl_idname=bl_id,
            label=getattr(n, 'label', ''),
            location=tuple(getattr(n, 'location', (0.0, 0.0))),
            group_ref=group_ref,
            is_unknown=is_unknown,
            props=props,
            inputs_defaults=inputs_defaults,
        ))

    links: List[GNLink] = []
    for l in group.links:
        links.append(GNLink(
            from_node=l.from_node.name,
            from_socket=l.from_socket.name,
            to_node=l.to_node.name,
            to_socket=l.to_socket.name,
        ))

    # Fingerprint (stable): node types+names+bl_idname + links
    fp_struct = {
        'nodes': [(nd.type, nd.bl_idname, nd.name) for nd in nodes],
        'links': [(lk.from_node, lk.from_socket, lk.to_node, lk.to_socket) for lk in links],
    }
    fp_bytes = json.dumps(fp_struct, sort_keys=True).encode('utf-8')
    fingerprint = hashlib.sha1(fp_bytes).hexdigest()

    return GNGroupExport(name=group.name, inputs=inputs, outputs=outputs, nodes=nodes, links=links, fingerprint=fingerprint)


def collect_overrides_for_object(obj: bpy.types.Object) -> List[GNObjectOverride]:
    out: List[GNObjectOverride] = []
    for mod in getattr(obj, 'modifiers', []):
        try:
            if getattr(mod, 'type', '') != 'NODES':
                continue
            group = getattr(mod, 'node_group', None)
            if not group or getattr(group, 'bl_idname', '') != 'GeometryNodeTree':
                continue
            enabled_vp = bool(getattr(mod, 'show_viewport', True))
            enabled_rn = bool(getattr(mod, 'show_render', True))
            inputs_map: Dict[str, Any] = {}
            for idx, s in enumerate(iter_group_inputs(group), start=1):
                candidates = [f"Input_{idx}", getattr(s, 'identifier', ''), getattr(s, 'name', '')]
                val = None
                for key in candidates:
                    if not key:
                        continue
                    try:
                        val = mod[key]
                        break
                    except Exception:
                        val = None
                if val is None:
                    val = to_default_value(s)
                inputs_map[getattr(s, 'name', f'Input_{idx}')] = _sanitize(val)
            out.append(GNObjectOverride(
                object_name=obj.name,
                modifier_name=getattr(mod, 'name', 'GeometryNodes'),
                group_name=group.name,
                enabled_viewport=enabled_vp,
                enabled_render=enabled_rn,
                inputs=inputs_map,
            ))
        except Exception as e:
            print(f"[WARN] GN override on {obj.name} failed: {e}")
    return out


def export_geometry_nodes(*, target_collections: Optional[Iterable[str]] = None, only_visible: bool = True) -> GNBundle:
    view_layer = bpy.context.view_layer
    groups_used: Dict[str, bpy.types.NodeTree] = {}
    overrides: List[GNObjectOverride] = []

    for obj in iter_objects_in_collections(target_collections):
        if only_visible:
            try:
                if not obj.visible_get(view_layer):
                    continue
            except Exception:
                if getattr(obj, 'hide_viewport', False) or obj.hide_get():
                    continue
            if getattr(obj, 'hide_render', False):
                continue
        obj_over = collect_overrides_for_object(obj)
        if obj_over:
            overrides.extend(obj_over)
            for o in obj_over:
                try:
                    ng = bpy.data.node_groups.get(o.group_name)
                    if ng and getattr(ng, 'bl_idname', '') == 'GeometryNodeTree':
                        groups_used[ng.name] = ng
                except Exception:
                    pass

    def add_nested_groups(base: bpy.types.NodeTree):
        for n in base.nodes:
            if n.type == 'GROUP' and getattr(n, 'node_tree', None):
                g = n.node_tree
                if getattr(g, 'bl_idname', '') == 'GeometryNodeTree' and g.name not in groups_used:
                    groups_used[g.name] = g
                    add_nested_groups(g)

    for g in list(groups_used.values()):
        add_nested_groups(g)

    groups_exports: List[GNGroupExport] = []
    unknown_nodes: List[Tuple[str, str, str]] = []
    for g in groups_used.values():
        try:
            groups_exports.append(gn_group_to_export(g, unknown_accum=unknown_nodes))
        except Exception as e:
            print(f"[WARN] Export GN group {g.name} failed: {e}")

    meta = {
        'exporter': 'KEROS_exportGPT.gn_v4',
        'blender_version': bpy.app.version_string,
        'timestamp': datetime.now().isoformat(timespec='seconds'),
        'only_visible': str(only_visible),
        'target_collections': ",".join(target_collections) if target_collections else '',
        'groups_count': str(len(groups_exports)),
        'overrides_count': str(len(overrides)),
        'unknown_nodes_count': str(len(unknown_nodes)),
        'unknown_nodes_preview': '; '.join(f"{g}:{n}:{bl}" for g, n, bl in unknown_nodes[:MAX_UNKNOWN_DETAILS]),
    }

    return GNBundle(groups=groups_exports, overrides=overrides, meta=meta)


def write_json(bundle: GNBundle, export_dir: str = DEFAULT_EXPORT_DIR, filename_fmt: str = DEFAULT_FILENAME_FMT) -> str:
    ensure_dir(export_dir)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    path = os.path.join(export_dir, filename_fmt.format(timestamp=timestamp))

    def sock_to_dict(s: GNSocket):
        return {'name': s.name, 'identifier': s.identifier, 'type': s.socket_type, 'default': s.default}

    def node_to_dict(n: GNNode):
        return {
            'name': n.name,
            'type': n.type,
            'bl_idname': n.bl_idname,
            'label': n.label,
            'location': list(n.location),
            'group_ref': n.group_ref,
            'is_unknown': n.is_unknown,
            'props': n.props,
            'inputs_defaults': n.inputs_defaults,
        }

    def link_to_dict(l: GNLink):
        return {'from_node': l.from_node, 'from_socket': l.from_socket, 'to_node': l.to_node, 'to_socket': l.to_socket}

    data = {
        'geometry_nodes': {
            'groups': [
                {
                    'name': g.name,
                    'fingerprint': g.fingerprint,
                    'inputs': [sock_to_dict(s) for s in g.inputs],
                    'outputs': [sock_to_dict(s) for s in g.outputs],
                    'nodes': [node_to_dict(n) for n in g.nodes],
                    'links': [link_to_dict(l) for l in g.links],
                } for g in bundle.groups
            ],
            'overrides': [
                {'object_name': o.object_name,
                 'modifier_name': o.modifier_name,
                 'group_name': o.group_name,
                 'enabled_viewport': o.enabled_viewport,
                 'enabled_render': o.enabled_render,
                 'inputs': o.inputs,
                } for o in bundle.overrides
            ],
            'meta': bundle.meta,
        }
    }

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

    print(f"[INFO] GN export written: {path}")
    return path


if __name__ == '__main__':
    bundle = export_geometry_nodes(target_collections=None, only_visible=True)
    out = write_json(bundle)
    try:
        print(f"[SUMMARY] GN groups={len(bundle.groups)} overrides={len(bundle.overrides)} unknown_nodes={bundle.meta.get('unknown_nodes_count')} out={out}")
    except Exception:
        pass
