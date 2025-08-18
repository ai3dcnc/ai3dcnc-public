import bpy
import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Iterable, Any, Set

"""
KEROS_exportGPT — Materials Parser v1 (Blender 4.2 LTS)

Goal: export a lean, PBR-focused summary of materials, with optional node-tree dump.

Default export path: G:/My Drive/BLENDER_EXPORT
Default filename: scene_export_[timestamp].json

What we export (v1):
- Material core: name, blend_method, use_nodes
- Principled BSDF PBR subset: base_color (RGBA), metallic, roughness, specular, ior, alpha
- Texture mapping for key channels (if an Image Texture is found upstream):
  {channel} -> { image_name, filepath, colorspace, packed }
  Channels covered: base_color, metallic, roughness, specular, normal, alpha
- Optional: list of user objects (object names that use this material)
- Optional: full node tree (nodes + links) when full_nodes=True (minimal schema)

Notes:
- Upstream image detection follows links recursively (limited depth) and picks the first TEX_IMAGE encountered.
- File paths are resolved via bpy.path.abspath; `packed=True` if the image is packed in the blend file.
- Colorspace is taken from image.colorspace_settings.name.
- Normal map detection: looks for a Normal Map node feeding Principled->Normal; otherwise tries to find an upstream image.
"""

# ===============================
# Config
# ===============================
DEFAULT_EXPORT_DIR = r"G:/My Drive/BLENDER_EXPORT"
DEFAULT_FILENAME_FMT = "scene_export_{timestamp}.json"
MAX_RECURSE_LINKS = 12

# ===============================
# Dataclasses
# ===============================
@dataclass
class TextureRef:
    image_name: Optional[str]
    filepath: Optional[str]
    colorspace: Optional[str]
    packed: Optional[bool]

@dataclass
class PrincipledPBR:
    base_color: Tuple[float, float, float, float]
    metallic: float
    roughness: float
    specular: float
    ior: float
    alpha: float
    textures: Dict[str, TextureRef] = field(default_factory=dict)  # base_color, metallic, roughness, specular, normal, alpha

@dataclass
class MaterialExport:
    name: str
    blend_method: str
    use_nodes: bool
    pbr: Optional[PrincipledPBR]
    users: Optional[List[str]] = None
    full_nodes: Optional[Dict[str, Any]] = None

@dataclass
class MaterialsBundle:
    materials: List[MaterialExport]
    meta: Dict[str, str]

# ===============================
# Helpers
# ===============================

def ensure_dir(path: str) -> None:
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def to_texture_ref(img: Optional[bpy.types.Image]) -> TextureRef:
    if not img:
        return TextureRef(None, None, None, None)
    try:
        filepath = bpy.path.abspath(img.filepath) if getattr(img, 'filepath', None) else None
        colorspace = getattr(img.colorspace_settings, 'name', None) if getattr(img, 'colorspace_settings', None) else None
        packed = bool(getattr(img, 'packed_file', None))
        return TextureRef(img.name, filepath, colorspace, packed)
    except Exception:
        return TextureRef(getattr(img, 'name', None), None, None, None)


def find_first_image_from_input(socket: bpy.types.NodeSocket, depth: int = 0) -> Optional[bpy.types.Image]:
    """Follow links upstream from a node input socket until an Image Texture is found.
    Returns the bpy.types.Image or None.
    """
    if depth > MAX_RECURSE_LINKS:
        return None
    if not socket:
        return None
    if not socket.is_linked:
        return None
    for link in socket.links:
        from_node = link.from_node
        if from_node.type == 'TEX_IMAGE':
            return getattr(from_node, 'image', None)
        # Try primary color output sockets heuristics
        out_sockets = [s for s in from_node.outputs if s.is_linked]
        for out in out_sockets:
            # Continue upstream
            img = None
            # Prefer obvious color/height outputs if present
            if hasattr(from_node, 'type') and from_node.type in {'NORMAL_MAP', 'SEPARATE_COLOR', 'MIX', 'MIX_RGB'}:
                for candidate_name in ['Color', 'Image', 'Normal']:
                    if candidate_name in from_node.outputs and from_node.outputs[candidate_name].is_linked:
                        img = find_first_image_from_output(from_node.outputs[candidate_name], depth + 1)
                        if img:
                            return img
            # Fallback: first linked output
            if not img:
                img = find_first_image_from_output(out, depth + 1)
                if img:
                    return img
    return None


def find_first_image_from_output(socket: bpy.types.NodeSocket, depth: int) -> Optional[bpy.types.Image]:
    # Traverse forward to consumers, then continue upstream from their inputs
    if depth > MAX_RECURSE_LINKS:
        return None
    if not socket.is_linked:
        return None
    for link in socket.links:
        to_node = link.to_node
        # Look for an image inside this node first (rare)
        if to_node.type == 'TEX_IMAGE':
            return getattr(to_node, 'image', None)
        # Then climb further upstream via the inputs of this node
        for inp in to_node.inputs:
            if inp.is_linked:
                img = find_first_image_from_input(inp, depth + 1)
                if img:
                    return img
    return None


def get_principled_node(mat: bpy.types.Material) -> Optional[bpy.types.Node]:
    if not mat.use_nodes or not mat.node_tree:
        return None
    for n in mat.node_tree.nodes:
        if n.type == 'BSDF_PRINCIPLED':
            return n
    return None


def socket_value(node: bpy.types.Node, name: str, fallback):
    try:
        s = node.inputs.get(name)
        if s is None:
            return fallback
        if s.is_linked:
            # Value comes from upstream; we still record numeric fallback
            if hasattr(s, 'default_value'):
                return tuple(s.default_value) if hasattr(s.default_value, '__iter__') else float(s.default_value)
            return fallback
        dv = getattr(s, 'default_value', fallback)
        if hasattr(dv, '__iter__'):
            dv = tuple(dv)
        return dv
    except Exception:
        return fallback


def build_pbr_from_principled(mat: bpy.types.Material, node: bpy.types.Node) -> PrincipledPBR:
    # Numerics
    base_color = socket_value(node, 'Base Color', (1.0, 1.0, 1.0, 1.0))
    metallic = float(socket_value(node, 'Metallic', 0.0))
    roughness = float(socket_value(node, 'Roughness', 0.5))
    specular = float(socket_value(node, 'Specular', 0.5))
    ior = float(socket_value(node, 'IOR', 1.45))
    alpha = float(socket_value(node, 'Alpha', 1.0))

    # Textures (first upstream image)
    tex: Dict[str, TextureRef] = {}
    try:
        s_base = node.inputs.get('Base Color')
        tex['base_color'] = to_texture_ref(find_first_image_from_input(s_base)) if s_base else TextureRef(None, None, None, None)
        s_metal = node.inputs.get('Metallic')
        tex['metallic'] = to_texture_ref(find_first_image_from_input(s_metal)) if s_metal else TextureRef(None, None, None, None)
        s_rough = node.inputs.get('Roughness')
        tex['roughness'] = to_texture_ref(find_first_image_from_input(s_rough)) if s_rough else TextureRef(None, None, None, None)
        s_spec = node.inputs.get('Specular')
        tex['specular'] = to_texture_ref(find_first_image_from_input(s_spec)) if s_spec else TextureRef(None, None, None, None)
        s_alpha = node.inputs.get('Alpha')
        tex['alpha'] = to_texture_ref(find_first_image_from_input(s_alpha)) if s_alpha else TextureRef(None, None, None, None)

        # Normal: prefer a NORMAL_MAP node feeding 'Normal'; else first image upstream
        s_norm = node.inputs.get('Normal')
        norm_img = None
        if s_norm and s_norm.is_linked:
            for link in s_norm.links:
                src = link.from_node
                if src.type == 'NORMAL_MAP':
                    col_in = src.inputs.get('Color')
                    norm_img = find_first_image_from_input(col_in) if col_in else None
                if not norm_img:
                    # fallback: keep searching upstream
                    for inp in src.inputs:
                        if inp.is_linked:
                            norm_img = find_first_image_from_input(inp)
                            if norm_img:
                                break
        if not norm_img:
            norm_img = find_first_image_from_input(s_norm) if s_norm else None
        tex['normal'] = to_texture_ref(norm_img)
    except Exception:
        pass

    return PrincipledPBR(
        base_color=tuple(base_color) if isinstance(base_color, (list, tuple)) else (base_color, base_color, base_color, 1.0),
        metallic=metallic,
        roughness=roughness,
        specular=specular,
        ior=ior,
        alpha=alpha,
        textures=tex,
    )


def export_material(mat: bpy.types.Material, *, include_users: bool = True, full_nodes: bool = False) -> MaterialExport:
    name = mat.name
    blend_method = getattr(mat, 'blend_method', 'OPAQUE')
    use_nodes = bool(getattr(mat, 'use_nodes', False))

    pbr: Optional[PrincipledPBR] = None
    if use_nodes:
        node = get_principled_node(mat)
        if node:
            pbr = build_pbr_from_principled(mat, node)

    users: Optional[List[str]] = None
    if include_users:
        users = []
        try:
            for obj in bpy.data.objects:
                if obj.type not in {'MESH', 'CURVES', 'CURVE', 'SURFACE', 'META', 'FONT'}:
                    continue
                for slot in getattr(obj, 'material_slots', []):
                    if slot.material and slot.material.name == name:
                        users.append(obj.name)
                        break
        except Exception:
            pass

    full_dump: Optional[Dict[str, Any]] = None
    if full_nodes and use_nodes and mat.node_tree:
        try:
            nodes_data = []
            for n in mat.node_tree.nodes:
                nd = {
                    'name': n.name,
                    'type': n.type,
                    'label': getattr(n, 'label', ''),
                    'location': list(getattr(n, 'location', (0.0, 0.0))),
                }
                # inputs
                ins = []
                for s in n.inputs:
                    ins.append({'name': s.name, 'type': s.type, 'is_linked': s.is_linked})
                nd['inputs'] = ins
                # outputs
                outs = []
                for s in n.outputs:
                    outs.append({'name': s.name, 'type': s.type, 'is_linked': s.is_linked})
                nd['outputs'] = outs
                nodes_data.append(nd)

            links_data = []
            for l in mat.node_tree.links:
                links_data.append({
                    'from_node': l.from_node.name,
                    'from_socket': l.from_socket.name,
                    'to_node': l.to_node.name,
                    'to_socket': l.to_socket.name,
                })
            full_dump = {'nodes': nodes_data, 'links': links_data}
        except Exception:
            full_dump = None

    return MaterialExport(
        name=name,
        blend_method=blend_method,
        use_nodes=use_nodes,
        pbr=pbr,
        users=users,
        full_nodes=full_dump,
    )

# ===============================
# Public API
# ===============================

def export_materials(
    *,
    include_users: bool = True,
    full_nodes: bool = False,
    target_materials: Optional[Iterable[str]] = None,
) -> MaterialsBundle:
    materials: List[MaterialExport] = []

    def mat_iter():
        if target_materials:
            names = set(target_materials)
            for m in bpy.data.materials:
                if m.name in names:
                    yield m
        else:
            for m in bpy.data.materials:
                yield m

    for m in mat_iter():
        try:
            materials.append(export_material(m, include_users=include_users, full_nodes=full_nodes))
        except Exception as e:
            # Keep going even if a material misbehaves
            print(f"[WARN] Failed to export material {m.name}: {e}")

    meta = {
        'exporter': 'KEROS_exportGPT.materials_v1',
        'blender_version': bpy.app.version_string,
        'timestamp': datetime.now().isoformat(timespec='seconds'),
        'include_users': str(include_users),
        'full_nodes': str(full_nodes),
        'target_materials': ",".join(target_materials) if target_materials else '',
    }
    return MaterialsBundle(materials=materials, meta=meta)


def write_json(bundle: MaterialsBundle, export_dir: str = DEFAULT_EXPORT_DIR, filename_fmt: str = DEFAULT_FILENAME_FMT) -> str:
    ensure_dir(export_dir)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    path = os.path.join(export_dir, filename_fmt.format(timestamp=timestamp))

    def texref_to_dict(tr: TextureRef):
        return {
            'image_name': tr.image_name,
            'filepath': tr.filepath,
            'colorspace': tr.colorspace,
            'packed': tr.packed,
        }

    def pbr_to_dict(p: PrincipledPBR):
        return {
            'base_color': list(p.base_color),
            'metallic': p.metallic,
            'roughness': p.roughness,
            'specular': p.specular,
            'ior': p.ior,
            'alpha': p.alpha,
            'textures': {k: texref_to_dict(v) for k, v in p.textures.items()},
        }

    data = {
        'materials': {
            'materials': [
                {
                    'name': m.name,
                    'blend_method': m.blend_method,
                    'use_nodes': m.use_nodes,
                    'pbr': (pbr_to_dict(m.pbr) if m.pbr else None),
                    'users': m.users,
                    'full_nodes': m.full_nodes,
                }
                for m in bundle.materials
            ],
            'meta': bundle.meta,
        }
    }

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

    print(f"[INFO] Materials export (v1) written: {path}")
    return path


if __name__ == '__main__':
    bundle = export_materials(
        include_users=True,
        full_nodes=False,            # set True for node dump
        target_materials=None,       # or e.g. ["Mat_Wood", "Mat_Metal"]
    )
    write_json(bundle)
