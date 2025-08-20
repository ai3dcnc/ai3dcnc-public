# -*- coding: utf-8 -*-
"""
KEROS_import — builder_scene_view (Cameras & Lights) — Blender 3.6 ↔ 4.2 LTS

Small, robust importer that recreates/updates cameras and lights from the
Scene View JSON exported by `parser_scene_view.py` or from the aggregated
`parser_scene.py` document.

Accepts either a full doc with {"scene_view": {...}} or just the section:
{
  "cameras": [...],
  "lights": [...]
}

Functions exposed (kept stable for builders_all):
- import_from_data(doc_or_section: dict, *, verbose=False) -> dict
- import_from_file(path: str, *, verbose=False) -> dict
(Aliases `apply_from_*` are provided for convenience.)

Behavior:
- Uses world_matrix if provided (16 floats). Falls back to {location, rotation_euler, scale}.
- Creates data blocks by `name` (camera/light data) and objects by `object_name`.
- Safe-sets: camera type/lens/sensor/clip/shift/DOF; light type/color/energy/soft size,
  extras (spot/sun/area), and basic shadow flags.
- Prints a single [SUMMARY] line with created/updated counts.

Note: angle_x/angle_y are derived properties in Blender → not settable; ignored on import.
"""
from __future__ import annotations

import os, json
from typing import Any, Dict, List, Optional, Tuple

try:
    import bpy  # type: ignore
    import mathutils  # type: ignore
except Exception:  # running outside Blender (CI)
    bpy = None  # type: ignore
    mathutils = None  # type: ignore

# === utils ================================================================

def _read_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _as_list(x) -> List[Any]:
    if x is None:
        return []
    if isinstance(x, (list, tuple, set)):
        return list(x)
    return [x]


def _norm_scene_view(doc_or_sec: Any) -> Dict[str, List[Dict[str, Any]]]:
    sec = doc_or_sec
    if isinstance(doc_or_sec, dict):
        sec = doc_or_sec.get("scene_view") or doc_or_sec
    cams: List[Dict[str, Any]] = []
    lts: List[Dict[str, Any]] = []
    if isinstance(sec, dict):
        for c in _as_list(sec.get("cameras", [])):
            cams.append(c if isinstance(c, dict) else {})
        for l in _as_list(sec.get("lights", [])):
            lts.append(l if isinstance(l, dict) else {})
    return {"cameras": cams, "lights": lts}


def _ensure_scene_link(obj: "bpy.types.Object"):
    sc = bpy.context.scene if bpy else None
    if not sc:
        return
    coll = sc.collection
    try:
        if obj.name not in coll.objects:
            coll.objects.link(obj)
    except Exception:
        pass


def _apply_transform(obj: "bpy.types.Object", t: Dict[str, Any], wm: Optional[List[float]] = None):
    if not bpy or not obj:
        return
    # world_matrix wins if valid
    if wm and isinstance(wm, (list, tuple)) and len(wm) == 16 and mathutils:
        try:
            m = mathutils.Matrix(((wm[0], wm[1], wm[2], wm[3]),
                                  (wm[4], wm[5], wm[6], wm[7]),
                                  (wm[8], wm[9], wm[10], wm[11]),
                                  (wm[12], wm[13], wm[14], wm[15])))
            obj.matrix_world = m
            return
        except Exception:
            pass
    # fallback: TRS
    try:
        loc = t.get("location") or [0.0, 0.0, 0.0]
        rot = t.get("rotation_euler") or [0.0, 0.0, 0.0]
        scl = t.get("scale") or [1.0, 1.0, 1.0]
        obj.location = (float(loc[0]), float(loc[1]), float(loc[2]))
        obj.rotation_euler = (float(rot[0]), float(rot[1]), float(rot[2]))
        obj.scale = (float(scl[0]), float(scl[1]), float(scl[2]))
    except Exception:
        pass


# === camera / light builders ==============================================

def _get_or_create_camera(data_name: str, obj_name: str) -> "bpy.types.Object":
    cam_data = bpy.data.cameras.get(data_name) or bpy.data.cameras.new(data_name)
    obj = bpy.data.objects.get(obj_name)
    if not obj:
        obj = bpy.data.objects.new(obj_name, cam_data)
        _ensure_scene_link(obj)
    else:
        # ensure object holds a camera datablock
        if obj.type != 'CAMERA':
            obj.data = cam_data
    return obj


def _apply_camera_props(obj: "bpy.types.Object", c: Dict[str, Any]):
    cam = obj.data if obj and hasattr(obj, "data") else None
    if not cam:
        return
    try:
        t = str(c.get("type") or c.get("cam_type") or "PERSP").upper()
        if hasattr(cam, "type"):
            cam.type = t if t in {"PERSP", "ORTHO", "PANO"} else "PERSP"
        # lens & sensor
        if c.get("lens_mm") is not None:
            cam.lens = float(c["lens_mm"])  # mm
        if c.get("sensor_width") is not None:
            cam.sensor_width = float(c["sensor_width"])
        if c.get("sensor_height") is not None:
            cam.sensor_height = float(c["sensor_height"])
        if c.get("clip_start") is not None:
            cam.clip_start = float(c["clip_start"])
        if c.get("clip_end") is not None:
            cam.clip_end = float(c["clip_end"])
        if c.get("shift_x") is not None:
            cam.shift_x = float(c["shift_x"])
        if c.get("shift_y") is not None:
            cam.shift_y = float(c["shift_y"])
        # DOF
        dof = c.get("dof") or {}
        if hasattr(cam, "dof") and isinstance(dof, dict):
            cam.dof.use_dof = bool(dof.get("enabled") or dof.get("use_dof") or False)
            if dof.get("focus_distance") is not None:
                cam.dof.focus_distance = float(dof["focus_distance"])
            # Blender variants: aperture_fstop or aperture_size
            if dof.get("aperture_fstop") is not None:
                try:
                    cam.dof.aperture_fstop = float(dof["aperture_fstop"])  # 3.6/4.x
                except Exception:
                    pass
            if dof.get("aperture_size") is not None and not hasattr(cam.dof, "aperture_fstop"):
                try:
                    cam.dof.aperture_size = float(dof["aperture_size"])  # some builds
                except Exception:
                    pass
        # Panorama extras (Cycles) when type == PANO
        pano = c.get("panorama") or {}
        if t == "PANO" and isinstance(pano, dict):
            cycles = getattr(cam, 'cycles', None)
            if cycles is not None:
                if pano.get("panorama_type") is not None:
                    try: cycles.panorama_type = str(pano["panorama_type"]).upper()
                    except Exception: pass
                if pano.get("fisheye_fov") is not None:
                    try: cycles.fisheye_fov = float(pano["fisheye_fov"]) 
                    except Exception: pass
                if pano.get("fisheye_lens") is not None:
                    try: cycles.fisheye_lens = float(pano["fisheye_lens"]) 
                    except Exception: pass
    except Exception:
        pass


def _get_or_create_light(data_name: str, obj_name: str, ltype: str) -> "bpy.types.Object":
    map_type = ltype if ltype in {"POINT", "SUN", "SPOT", "AREA"} else "POINT"
    ldata = bpy.data.lights.get(data_name) or bpy.data.lights.new(data_name, map_type)
    if ldata.type != map_type:
        try: ldata.type = map_type
        except Exception: pass
    obj = bpy.data.objects.get(obj_name)
    if not obj:
        obj = bpy.data.objects.new(obj_name, ldata)
        _ensure_scene_link(obj)
    else:
        if obj.type != 'LIGHT':
            obj.data = ldata
    return obj


def _apply_light_props(obj: "bpy.types.Object", l: Dict[str, Any]):
    ldata = obj.data if obj and hasattr(obj, "data") else None
    if not ldata:
        return
    try:
        if l.get("energy") is not None:
            ldata.energy = float(l["energy"])
        col = l.get("color") or [1.0, 1.0, 1.0]
        if hasattr(ldata, "color") and isinstance(col, (list, tuple)) and len(col) >= 3:
            ldata.color = (float(col[0]), float(col[1]), float(col[2]))
        if l.get("shadow_soft_size") is not None and hasattr(ldata, "shadow_soft_size"):
            ldata.shadow_soft_size = float(l["shadow_soft_size"])  # POINT/SUN/AREA
        # extras
        extras = l.get("extras") or {}
        ltype = str(l.get("light_type") or l.get("type") or getattr(ldata, 'type', 'POINT')).upper()
        if ltype == 'SPOT':
            if extras.get("spot_size") is not None:
                try: ldata.spot_size = float(extras["spot_size"]) 
                except Exception: pass
            if extras.get("spot_blend") is not None:
                try: ldata.spot_blend = float(extras["spot_blend"]) 
                except Exception: pass
        elif ltype == 'AREA':
            if extras.get("area_shape") is not None and hasattr(ldata, 'shape'):
                try: ldata.shape = str(extras["area_shape"]).upper()
                except Exception: pass
            if extras.get("area_size") is not None and hasattr(ldata, 'size'):
                try: ldata.size = float(extras["area_size"]) 
                except Exception: pass
            if extras.get("area_size_y") is not None and hasattr(ldata, 'size_y'):
                try: ldata.size_y = float(extras["area_size_y"]) 
                except Exception: pass
        elif ltype == 'SUN':
            if extras.get("sun_angle") is not None and hasattr(ldata, 'angle'):
                try: ldata.angle = float(extras["sun_angle"]) 
                except Exception: pass
        # shadow flags (mainly Eevee)
        sh = l.get("shadow") or {}
        if hasattr(ldata, 'use_shadow') and sh.get("use_shadow") is not None:
            ldata.use_shadow = bool(sh.get("use_shadow", True))
        if hasattr(ldata, 'use_contact_shadow') and sh.get("use_contact_shadow") is not None:
            ldata.use_contact_shadow = bool(sh.get("use_contact_shadow", False))
        for attr_json, attr_bpy in (
            ("contact_shadow_distance", "contact_shadow_distance"),
            ("contact_shadow_bias", "contact_shadow_bias"),
            ("contact_shadow_thickness", "contact_shadow_thickness"),
        ):
            if sh.get(attr_json) is not None and hasattr(ldata, attr_bpy):
                try: setattr(ldata, attr_bpy, float(sh[attr_json]))
                except Exception: pass
    except Exception:
        pass


# === public API ============================================================

def import_from_data(doc_or_section: Any, *, verbose: bool=False) -> Dict[str, int]:
    """Create/update cameras and lights from a doc or a scene_view section.
    Returns counts dict: {"cameras": N, "lights": M}.
    """
    sv = _norm_scene_view(doc_or_section)
    cams = 0; lts = 0

    if not bpy:
        # dry run for CI/knowledge store
        print(f"[SUMMARY] builder_scene_view(dry): cameras_in={len(sv['cameras'])} lights_in={len(sv['lights'])}")
        return {"cameras": len(sv['cameras']), "lights": len(sv['lights'])}

    # Cameras
    for c in sv["cameras"]:
        try:
            data_name = c.get("name") or (c.get("object_name") or "Camera") + "_Cam"
            obj_name = c.get("object_name") or c.get("name") or "Camera"
            cam_obj = _get_or_create_camera(data_name, obj_name)
            _apply_camera_props(cam_obj, c)
            _apply_transform(cam_obj, c.get("transform") or {}, c.get("world_matrix"))
            cams += 1
        except Exception:
            # keep going — importer must be resilient
            continue

    # Lights
    for l in sv["lights"]:
        try:
            ltype = str(l.get("light_type") or l.get("type") or "POINT").upper()
            data_name = l.get("name") or (l.get("object_name") or "Light") + "_Light"
            obj_name = l.get("object_name") or l.get("name") or "Light"
            lgt_obj = _get_or_create_light(data_name, obj_name, ltype)
            _apply_light_props(lgt_obj, l)
            _apply_transform(lgt_obj, l.get("transform") or {}, l.get("world_matrix"))
            lts += 1
        except Exception:
            continue

    print(f"[SUMMARY] builder_scene_view cameras_built={cams} lights_built={lts}")
    return {"cameras": cams, "lights": lts}


def import_from_file(path: str, *, verbose: bool=False) -> Dict[str, int]:
    doc = _read_json(path)
    sec = doc.get("scene_view") or doc
    return import_from_data(sec, verbose=verbose)

# aliases kept for builders_all compatibility
apply_from_data = import_from_data
apply_from_file = import_from_file


# -----------------------------
# Self-test (disabled)
# -----------------------------
if __name__ == "__main__" and False:
    p = bpy.path.abspath("//_EXPORTS/scene_view.json")
    import_from_file(p, verbose=True)
