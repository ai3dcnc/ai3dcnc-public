import bpy, json, os

"""
KEROS_exportGPT — builder_materials (canonical, robust)

Rebuilds/updates Principled BSDF materials from JSON (materials_v1 snapshot style).
- Accepts both wrappers {"materials":{"materials":[...]}} and plain {"materials":[...]} or a list.
- Sets scalar props: roughness, metallic, specular, ior, alpha.
- Sets base_color (RGBA) from list/tuple/hex string.
- Optionally wires textures if filepaths are present (base_color/roughness/metallic/alpha).
- Colorspace: defaults to sRGB for base_color, Non-Color for others (can be overridden by JSON).
- Short [SUMMARY] lines. No crashes if files are missing.

Expected minimal item keys:
  {
    "name": "MatName",
    "base_color": [r,g,b] or [r,g,b,a] or "#rrggbb",
    "roughness": 0.5, "metallic": 0.0, "specular": 0.5, "ior": 1.45, "alpha": 1.0,
    "textures": {
        "base_color": {"filepath": "//tex/albedo.png", "colorspace": "sRGB"},
        "roughness": {"filepath": "//tex/rough.png"},
        "metallic":  {"filepath": "//tex/metal.png"},
        "alpha":     {"filepath": "//tex/alpha.png"}
    }
  }
Alternative texture keys also accepted: base_color_texture, roughness_texture, metallic_texture, alpha_texture.
"""

# -----------------------------
# Utils
# -----------------------------

def _read_json(path:str):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _material_items_from_data(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        # {"materials":{"materials":[...]}}
        d = data.get('materials')
        if isinstance(d, dict):
            return d.get('materials') or []
        # {"materials":[...]}
        if isinstance(d, list):
            return d
    return []


def _to_rgba(v):
    # list/tuple length 3 or 4
    if isinstance(v, (list, tuple)) and len(v) >= 3:
        r, g, b = float(v[0]), float(v[1]), float(v[2])
        a = float(v[3]) if len(v) > 3 else 1.0
        return (r, g, b, a)
    # hex string
    if isinstance(v, str) and v.startswith('#') and len(v) in (7, 9):
        r = int(v[1:3], 16) / 255.0
        g = int(v[3:5], 16) / 255.0
        b = int(v[5:7], 16) / 255.0
        a = int(v[7:9], 16) / 255.0 if len(v) == 9 else 1.0
        return (r, g, b, a)
    # single number -> grey
    try:
        f = float(v)
        return (f, f, f, 1.0)
    except Exception:
        return (0.8, 0.8, 0.8, 1.0)


def _ensure_nodes(mat: bpy.types.Material):
    mat.use_nodes = True
    nt = mat.node_tree
    nodes = nt.nodes
    links = nt.links
    # find or create Principled and Output
    principled = None
    out = None
    for n in nodes:
        if n.bl_idname == 'ShaderNodeBsdfPrincipled': principled = n
        if n.bl_idname == 'ShaderNodeOutputMaterial': out = n
    if not principled:
        principled = nodes.new('ShaderNodeBsdfPrincipled')
        principled.location = (0, 0)
    if not out:
        out = nodes.new('ShaderNodeOutputMaterial')
        out.location = (220, 0)
    # ensure link
    try:
        if not any(l.to_node == out and l.from_node == principled for l in links):
            links.new(principled.outputs['BSDF'], out.inputs['Surface'])
    except Exception:
        pass
    return nt, nodes, links, principled, out


def _load_image(filepath: str):
    fp = bpy.path.abspath(filepath)
    try:
        return bpy.data.images.load(fp, check_existing=True)
    except Exception:
        return None


def _ensure_tex_setup(nt, nodes, links, principled, socket_name: str, filepath: str, colorspace: str | None):
    img = _load_image(filepath)
    if not img:
        return False
    tex = nodes.new('ShaderNodeTexImage')
    tex.image = img
    tex.label = os.path.basename(filepath)
    try:
        if colorspace:
            img.colorspace_settings.name = colorspace
        else:
            # defaults: base_color -> sRGB, others -> Non-Color
            img.colorspace_settings.name = 'sRGB' if socket_name == 'Base Color' else 'Non-Color'
    except Exception:
        pass
    # place node
    tex.location = (-300, 0)
    # link
    try:
        links.new(tex.outputs['Color'], principled.inputs[socket_name])
        if socket_name == 'Alpha' and 'Alpha' in tex.outputs:
            links.new(tex.outputs['Alpha'], principled.inputs['Alpha'])
    except Exception:
        return False
    return True


# -----------------------------
# Core build
# -----------------------------

def build_single_material(item: dict, verbose: bool=False) -> dict:
    name = item.get('name') or 'Material'
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name=name)
    nt, nodes, links, principled, out = _ensure_nodes(mat)

    # scalar props
    if 'roughness' in item: principled.inputs['Roughness'].default_value = float(item['roughness'])
    if 'metallic'  in item: principled.inputs['Metallic'].default_value  = float(item['metallic'])
    if 'specular'  in item: principled.inputs['Specular'].default_value  = float(item['specular'])
    if 'ior'       in item:
        try:
            principled.inputs['IOR'].default_value = float(item['ior'])
        except Exception:
            pass
    if 'alpha'     in item:
        try:
            principled.inputs['Alpha'].default_value = float(item['alpha'])
            mat.blend_method = 'BLEND' if item['alpha'] < 1.0 else 'OPAQUE'
            mat.shadow_method = 'HASHED' if item['alpha'] < 1.0 else 'OPAQUE'
        except Exception:
            pass

    # base color
    if 'base_color' in item:
        principled.inputs['Base Color'].default_value = _to_rgba(item['base_color'])

    # textures
    tex_block = item.get('textures') or {}
    # alternate flat keys allowed
    def _texdict(k):
        td = tex_block.get(k)
        if isinstance(td, dict):
            return td
        alt = item.get(f"{k}_texture") or item.get(f"{k}_tex")
        if isinstance(alt, dict):
            return alt
        if isinstance(alt, str):
            return {"filepath": alt}
        return None

    for sock, key in (('Base Color','base_color'), ('Roughness','roughness'), ('Metallic','metallic'), ('Alpha','alpha')):
        td = _texdict(key)
        if not td: continue
        fp = td.get('filepath') or td.get('path')
        if not fp: continue
        cs = td.get('colorspace')
        _ensure_tex_setup(nt, nodes, links, principled, sock, fp, cs)

    if verbose:
        print(f"[DEBUG] material '{name}' updated")
    print(f"[SUMMARY] materials_build: name={name}")
    return {"name": name}


# -----------------------------
# Batch API
# -----------------------------

def import_from_data(data: dict, only_first_n: int | None = None, verbose: bool=False) -> dict:
    items = _material_items_from_data(data)
    if only_first_n is not None:
        items = items[:only_first_n]
    built = 0
    for it in items:
        try:
            build_single_material(it, verbose=verbose)
            built += 1
        except Exception as e:
            print(f"[WARN] material build failed for {it.get('name','?')}: {e}")
    print(f"[SUMMARY] materials_apply: items={len(items)} built={built}")
    return {"items": len(items), "built": built}


def import_from_file(path: str, only_first_n: int | None = None, verbose: bool=False) -> dict:
    data = _read_json(path)
    return import_from_data(data, only_first_n=only_first_n, verbose=verbose)


# -----------------------------
# Quick self-test (disabled)
# -----------------------------
if __name__ == "__main__" and False:
    p = bpy.path.abspath("//_EXPORTS/scene_export_test.json")
    import_from_file(p, only_first_n=1, verbose=True)
