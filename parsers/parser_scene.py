import bpy
import json
import os
from datetime import datetime
from typing import Optional, Dict, Any

"""
KEROS_exportGPT — parser_scene.py (aggregator, Blender 4.2 LTS)

Simple, robust aggregator that calls each parser, loads their JSON, and writes a single
combined file with sections:
  - mesh, scene_view, materials, collections, geometry_nodes, bool_ops
  - world, color_management, render

Defaults:
  export_dir = G:/My Drive/BLENDER_EXPORT
  filename   = scene_export_[timestamp].json

Controls:
  - target_collections: None (export all) or list of names
  - only_visible: True
  - apply_modifiers: True (mesh)
  - keep_individual_files: False (delete the per-parser files after merge)

Module name resolution matches current files where possible.
"""

DEFAULT_EXPORT_DIR = r"G:/My Drive/BLENDER_EXPORT"
DEFAULT_FILENAME_FMT = "scene_export_{timestamp}.json"

# -----------------------------
# Safe imports (no hard deps)
# -----------------------------

def _try_import(name: str):
    try:
        return __import__(name)
    except Exception as e:
        print(f"[WARN] Could not import {name}: {e}")
        return None


def _try_import_many(candidates):
    for nm in candidates:
        mod = _try_import(nm)
        if mod:
            print(f"[INFO] Using module: {nm}")
            return mod
    return None


def _write_and_load(module, fn_export: str, fn_write: str, export_kwargs: Dict[str, Any]):
    try:
        export = getattr(module, fn_export)
        write = getattr(module, fn_write)
    except Exception as e:
        print(f"[WARN] Module {getattr(module,'__name__',module)} missing {fn_export}/{fn_write}: {e}")
        return None
    try:
        bundle = export(**export_kwargs)
        path = write(bundle)
        with open(path, 'r', encoding='utf-8') as f:
            doc = json.load(f)
        return {"_path": path, "_doc": doc}
    except Exception as e:
        print(f"[WARN] Failed export via {getattr(module,'__name__',module)}: {e}")
        return None


# -----------------------------
# World / ColorManagement / Render
# -----------------------------

def export_world(scene: bpy.types.Scene) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    w = scene.world
    if not w:
        return {"use_nodes": False}

    out["use_nodes"] = bool(getattr(w, 'use_nodes', False))
    out["color"] = list(getattr(w, 'color', (0.0, 0.0, 0.0)))

    bg_strength = None
    env_path = None
    env_colorspace = None
    if out["use_nodes"] and getattr(w, 'node_tree', None):
        try:
            for n in w.node_tree.nodes:
                if n.type == 'BACKGROUND':
                    inp = n.inputs.get('Strength')
                    if inp and hasattr(inp, 'default_value'):
                        try:
                            bg_strength = float(inp.default_value)
                        except Exception:
                            pass
                if n.type == 'TEX_ENVIRONMENT':
                    img = getattr(n, 'image', None)
                    if img:
                        try:
                            env_path = bpy.path.abspath(img.filepath) if getattr(img, 'filepath', None) else None
                            env_colorspace = getattr(img.colorspace_settings, 'name', None)
                        except Exception:
                            pass
        except Exception:
            pass
    out["background_strength"] = bg_strength
    out["environment_texture"] = {"filepath": env_path, "colorspace": env_colorspace} if env_path else None
    return out


def export_color_management(scene: bpy.types.Scene) -> Dict[str, Any]:
    cm = scene.view_settings
    disp = scene.display_settings
    out = {
        "display_device": getattr(disp, 'display_device', ''),
        "view_transform": getattr(cm, 'view_transform', ''),
        "look": getattr(cm, 'look', ''),
        "exposure": float(getattr(cm, 'exposure', 0.0)),
        "gamma": float(getattr(cm, 'gamma', 1.0)),
    }
    return out


def export_render(scene: bpy.types.Scene) -> Dict[str, Any]:
    r = scene.render
    engine = getattr(r, 'engine', '')
    out = {
        "engine": engine,
        "resolution_x": int(getattr(r, 'resolution_x', 0)),
        "resolution_y": int(getattr(r, 'resolution_y', 0)),
        "resolution_percentage": int(getattr(r, 'resolution_percentage', 100)),
        "fps": int(getattr(r, 'fps', 24)),
        "fps_base": float(getattr(r, 'fps_base', 1.0)),
        "pixel_aspect_x": float(getattr(r, 'pixel_aspect_x', 1.0)),
        "pixel_aspect_y": float(getattr(r, 'pixel_aspect_y', 1.0)),
        "film_transparent": bool(getattr(r, 'film_transparent', False)),
    }
    try:
        if engine.startswith('CYCLES'):
            c = getattr(scene, 'cycles', None)
            if c:
                out["cycles"] = {
                    "samples": int(getattr(c, 'samples', 0)),
                    "preview_samples": int(getattr(c, 'preview_samples', 0)),
                    "use_denoising": bool(getattr(c, 'use_denoising', False)),
                }
        elif engine.startswith('BLENDER_EEVEE'):
            e = getattr(scene, 'eevee', None)
            if e:
                out["eevee"] = {
                    "taa_render_samples": int(getattr(e, 'taa_render_samples', 0)),
                    "use_bloom": bool(getattr(e, 'use_bloom', False)),
                }
    except Exception:
        pass
    return out


# -----------------------------
# Aggregation
# -----------------------------

def export_scene(
    *,
    target_collections=None,
    only_visible: bool = True,
    apply_modifiers: bool = True,
    keep_individual_files: bool = False,
    export_dir: str = DEFAULT_EXPORT_DIR,
    filename_fmt: str = DEFAULT_FILENAME_FMT,
) -> str:
    os.makedirs(export_dir, exist_ok=True)

    # 1) Run sub-parsers and load their JSON
    docs: Dict[str, Dict[str, Any]] = {}

    # Mesh
    mesh_mod = _try_import_many(['parser_mesh', 'parser_mesh_v5', 'parser_mesh_v2', 'parser_mesh_4_2'])
    if mesh_mod:
        mesh_doc = _write_and_load(mesh_mod, 'export_mesh', 'write_json', {
            'target_collections': target_collections,
            'only_visible': only_visible,
            'apply_modifiers': apply_modifiers,
            'include_uvs': True,
            'include_colors': True,
            'include_normals': True,
            'triangulate': True,
        })
        if mesh_doc:
            docs['mesh'] = mesh_doc

    # Scene View
    sv_mod = _try_import_many(['parser_scene_view', 'parser_scene_view_v3', 'parser_scene_view_4_2'])
    if sv_mod:
        sv_doc = _write_and_load(sv_mod, 'export_scene_view', 'write_json', {
            'target_collections': target_collections,
            'only_visible': only_visible,
        })
        if sv_doc:
            docs['scene_view'] = sv_doc

    # Materials
    mat_mod = _try_import_many(['parser_materials', 'parser_materials_v1'])
    if mat_mod:
        mat_doc = _write_and_load(mat_mod, 'export_materials', 'write_json', {
            'include_users': True,
            'full_nodes': False,
            'target_materials': None,
        })
        if mat_doc:
            docs['materials'] = mat_doc

    # Collections
    col_mod = _try_import_many(['parser_collections', 'parser_colections_v1', 'parser_collections_v1'])
    if col_mod:
        col_doc = _write_and_load(col_mod, 'export_collections', 'write_json', {
            'active_view_layer': bpy.context.view_layer,
        })
        if col_doc:
            docs['collections'] = col_doc

    # Geometry Nodes
    gn_mod = _try_import_many(['parser_gn', 'parser_gn_v4', 'parser_gn_v3', 'parser_gn_v2', 'parser_gn_v1'])
    if gn_mod:
        gn_doc = _write_and_load(gn_mod, 'export_geometry_nodes', 'write_json', {
            'target_collections': target_collections,
            'only_visible': only_visible,
        })
        if gn_doc:
            docs['geometry_nodes'] = gn_doc

    # Boolean Ops inventory
    bool_mod = _try_import_many(['parser_boolops'])
    if bool_mod:
        bool_doc = _write_and_load(bool_mod, 'export_boolops', 'write_json', {
            'target_collections': target_collections,
            'only_visible': only_visible,
        })
        if bool_doc:
            docs['bool_ops'] = bool_doc

    # 2) Build final combined structure
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    out_path = os.path.join(export_dir, filename_fmt.format(timestamp=timestamp))

    combined: Dict[str, Any] = {}

    # Copy sub-docs root sections as-is
    for key, pack in docs.items():
        sub = pack.get('_doc', {})
        if key in sub:
            combined[key] = sub[key]
        else:
            combined[key] = sub

    # Add World / CM / Render
    scene = bpy.context.scene
    combined['world'] = export_world(scene)
    combined['color_management'] = export_color_management(scene)
    combined['render'] = export_render(scene)

    # Meta about aggregator & file origins
    combined['meta'] = {
        'exporter': 'KEROS_exportGPT.scene',
        'blender_version': bpy.app.version_string,
        'timestamp': datetime.now().isoformat(timespec='seconds'),
        'target_collections': ",".join(target_collections) if target_collections else '',
        'only_visible': str(only_visible),
        'apply_modifiers': str(apply_modifiers),
        'parts': { k: pack.get('_path', '') for k, pack in docs.items() },
    }

    # 3) Write combined JSON
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(combined, f, indent=2)

    # 4) Optionally delete individual files
    if not keep_individual_files:
        for k, pack in docs.items():
            p = pack.get('_path')
            try:
                if p and os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass

    print(f"[INFO] Scene export (combined) written: {out_path}")
    print("[SUMMARY] sections=", ", ".join(sorted(combined.keys())))
    return out_path


if __name__ == '__main__':
    export_scene(
        target_collections=None,
        only_visible=True,
        apply_modifiers=True,
        keep_individual_files=False,
    )
