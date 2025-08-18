import bpy
import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Iterable, Set, Any

"""
KEROS_exportGPT — Scene View Parser (Cameras & Lights) for Blender 4.2 LTS — DRAFT #2

Exports cameras and lights to JSON for downstream AI/CNC pipelines.

Default export path: G:/My Drive/BLENDER_EXPORT
Default filename: scene_export_[timestamp].json

Design notes:
- Visibility gate ON by default (viewport + hide_render).
- Collection filter supported (recommended collection name: "KRS_EXPORT").
- Camera fields: transform, world_matrix, type, lens_unit, lens (mm), sensor (size/fit), shifts,
  FOV angles, clipping, DOF (incl. focus_object_name), and Cycles panorama extras when type==PANO.
- Light fields: type, color, energy, shadow_soft_size, extras (spot/sun/area), and shadow flags
  (use_shadow, use_contact_shadow, contact_* if available in Blender 4.2/Eevee).
- Transform is always object transform.

You can import and call export_scene_view() to get a Python dict-like bundle,
or run the file inside Blender to write the JSON on disk.
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
class CameraExport:
    name: str
    object_name: str
    collection_path: List[str]
    transform: Dict[str, List[float]]      # location, rotation_euler, scale
    world_matrix: List[float]              # 16 floats, row-major
    cam_type: str                          # PERSP / ORTHO / PANO
    lens_unit: str                         # FOCAL_LENGTH / FOV (Blender)
    lens_mm: Optional[float]
    sensor_fit: str                        # HORIZONTAL / VERTICAL / AUTO
    sensor_width: float
    sensor_height: float
    shift_x: float
    shift_y: float
    angle_x: Optional[float]               # radians (if available)
    angle_y: Optional[float]
    clip_start: float
    clip_end: float
    dof: Dict[str, Optional[float]]        # enabled (0/1), focus_distance, aperture_fstop, aperture_size, focus_object_name
    panorama: Dict[str, Any] = field(default_factory=dict)  # Only for PANO (Cycles)

@dataclass
class LightExport:
    name: str
    object_name: str
    collection_path: List[str]
    transform: Dict[str, List[float]]
    world_matrix: List[float]
    light_type: str                        # POINT / SUN / SPOT / AREA
    color: Tuple[float, float, float]
    energy: float
    shadow_soft_size: Optional[float]      # for Point/Spot/Area (Sun uses angle)
    extras: Dict[str, float] = field(default_factory=dict)  # spot_size, spot_blend, area_size, area_size_y, sun_angle
    shadow: Dict[str, Optional[float]] = field(default_factory=dict)  # use_shadow, use_contact_shadow, contact_* values

@dataclass
class SceneViewBundle:
    cameras: List[CameraExport]
    lights: List[LightExport]
    meta: Dict[str, str]

# ===============================
# Helpers
# ===============================

def ensure_dir(path: str) -> None:
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def flatten_matrix(m) -> List[float]:
    return [m[i][j] for i in range(4) for j in range(4)]


def get_collection_hierarchy(obj: bpy.types.Object) -> List[str]:
    paths: List[List[str]] = []

    def walk(coll: bpy.types.Collection, trail: List[str]):
        trail2 = trail + [coll.name]
        if obj.name in coll.objects:
            paths.append(trail2)
        for child in coll.children:
            walk(child, trail2)

    for c in bpy.data.collections:
        try:
            walk(c, [])
        except RecursionError:
            pass

    if not paths:
        return []
    return max(paths, key=len)


def iter_objects_in_collections(target_collections: Optional[Iterable[str]]) -> Iterable[bpy.types.Object]:
    if not target_collections:
        for obj in bpy.data.objects:
            if obj.type in {"CAMERA", "LIGHT"}:
                yield obj
        return

    allowed: Set[bpy.types.Object] = set()

    def collect_objects(coll: bpy.types.Collection):
        for obj in coll.objects:
            if obj.type in {"CAMERA", "LIGHT"}:
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
# Extraction
# ===============================

def extract_camera(obj: bpy.types.Object) -> Optional[CameraExport]:
    if obj.type != 'CAMERA' or not isinstance(obj.data, bpy.types.Camera):
        return None
    cam: bpy.types.Camera = obj.data

    # Safe accessors across 4.x changes
    lens_unit = getattr(cam, 'lens_unit', 'FOCAL_LENGTH')
    lens_mm = getattr(cam, 'lens', None)
    sensor_fit = getattr(cam, 'sensor_fit', 'AUTO')
    sensor_width = getattr(cam, 'sensor_width', 36.0)
    sensor_height = getattr(cam, 'sensor_height', 24.0)
    shift_x = getattr(cam, 'shift_x', 0.0)
    shift_y = getattr(cam, 'shift_y', 0.0)
    angle_x = getattr(cam, 'angle_x', None)
    angle_y = getattr(cam, 'angle_y', None)

    # Clipping
    clip_start = getattr(cam, 'clip_start', 0.1)
    clip_end = getattr(cam, 'clip_end', 1000.0)

    # DOF
    dof = getattr(cam, 'dof', None)
    dof_enabled = bool(getattr(dof, 'use_dof', False)) if dof else False
    focus_distance = getattr(dof, 'focus_distance', None) if dof else None
    # Blender 4.x can expose either fstop or size depending on physical model — guard both
    aperture_fstop = getattr(dof, 'aperture_fstop', None) if dof else None
    aperture_size = getattr(dof, 'aperture_size', None) if dof else None
    focus_obj = getattr(dof, 'focus_object', None) if dof else None
    focus_object_name = getattr(focus_obj, 'name', None) if focus_obj else None

    # Panorama (Cycles) when cam.type == 'PANO'
    panorama: Dict[str, Any] = {}
    cam_type = getattr(cam, 'type', 'PERSP')
    if cam_type == 'PANO':
        cycles = getattr(cam, 'cycles', None)
        if cycles is not None:
            panorama_type = getattr(cycles, 'panorama_type', None)  # 'EQUIRECTANGULAR', 'FISHEYE_EQUISOLID', 'FISHEYE_EQUDISTANT', etc.
            fisheye_fov = getattr(cycles, 'fisheye_fov', None)
            fisheye_lens = getattr(cycles, 'fisheye_lens', None)
            panorama = {
                'panorama_type': panorama_type,
                'fisheye_fov': fisheye_fov,
                'fisheye_lens': fisheye_lens,
            }

    export = CameraExport(
        name=(cam.name or obj.name),
        object_name=obj.name,
        collection_path=get_collection_hierarchy(obj),
        transform={
            'location': list(obj.location),
            'rotation_euler': list(obj.rotation_euler),
            'scale': list(obj.scale),
        },
        world_matrix=flatten_matrix(obj.matrix_world),
        cam_type=cam_type,
        lens_unit=lens_unit,
        lens_mm=lens_mm,
        sensor_fit=sensor_fit,
        sensor_width=sensor_width,
        sensor_height=sensor_height,
        shift_x=shift_x,
        shift_y=shift_y,
        angle_x=angle_x,
        angle_y=angle_y,
        clip_start=clip_start,
        clip_end=clip_end,
        dof={
            'enabled': float(dof_enabled),  # kept numeric for easier downstream typing
            'focus_distance': focus_distance,
            'aperture_fstop': aperture_fstop,
            'aperture_size': aperture_size,
            'focus_object_name': focus_object_name,
        },
        panorama=panorama,
    )
    return export


def extract_light(obj: bpy.types.Object) -> Optional[LightExport]:
    if obj.type != 'LIGHT' or not isinstance(obj.data, bpy.types.Light):
        return None
    light: bpy.types.Light = obj.data

    light_type = getattr(light, 'type', 'POINT')
    color = tuple(getattr(light, 'color', (1.0, 1.0, 1.0)))
    energy = float(getattr(light, 'energy', 10.0))
    shadow_soft_size = getattr(light, 'shadow_soft_size', None)

    extras: Dict[str, float] = {}
    if light_type == 'SPOT':
        extras['spot_size'] = float(getattr(light, 'spot_size', 0.785398))  # ~45deg
        extras['spot_blend'] = float(getattr(light, 'spot_blend', 0.15))
    elif light_type == 'AREA':
        extras['area_shape'] = getattr(light, 'shape', 'SQUARE')
        extras['area_size'] = float(getattr(light, 'size', 1.0))
        extras['area_size_y'] = float(getattr(light, 'size_y', extras['area_size']))
    elif light_type == 'SUN':
        extras['sun_angle'] = float(getattr(light, 'angle', 0.00918))  # ~0.526 deg

    # Shadow flags (available primarily for Eevee)
    shadow: Dict[str, Optional[float]] = {}
    shadow['use_shadow'] = float(1.0 if getattr(light, 'use_shadow', True) else 0.0)
    shadow['use_contact_shadow'] = float(1.0 if getattr(light, 'use_contact_shadow', False) else 0.0)
    shadow['contact_shadow_distance'] = getattr(light, 'contact_shadow_distance', None)
    shadow['contact_shadow_bias'] = getattr(light, 'contact_shadow_bias', None)
    shadow['contact_shadow_thickness'] = getattr(light, 'contact_shadow_thickness', None)

    export = LightExport(
        name=(light.name or obj.name),
        object_name=obj.name,
        collection_path=get_collection_hierarchy(obj),
        transform={
            'location': list(obj.location),
            'rotation_euler': list(obj.rotation_euler),
            'scale': list(obj.scale),
        },
        world_matrix=flatten_matrix(obj.matrix_world),
        light_type=light_type,
        color=(float(color[0]), float(color[1]), float(color[2])),
        energy=energy,
        shadow_soft_size=shadow_soft_size,
        extras=extras,
        shadow=shadow,
    )
    return export

# ===============================
# Public API
# ===============================

def export_scene_view(
    *,
    target_collections: Optional[Iterable[str]] = None,
    only_visible: bool = True,
) -> SceneViewBundle:
    cameras: List[CameraExport] = []
    lights: List[LightExport] = []

    for obj in iter_objects_in_collections(target_collections):
        # Visibility gate (viewport + render)
        if only_visible:
            try:
                if not obj.visible_get(bpy.context.view_layer):
                    continue
            except Exception:
                if getattr(obj, "hide_viewport", False) or obj.hide_get():
                    continue
            if getattr(obj, "hide_render", False):
                continue

        if obj.type == 'CAMERA':
            ex = extract_camera(obj)
            if ex:
                cameras.append(ex)
        elif obj.type == 'LIGHT':
            ex = extract_light(obj)
            if ex:
                lights.append(ex)

    meta = {
        'exporter': 'KEROS_exportGPT.scene_view',
        'blender_version': bpy.app.version_string,
        'timestamp': datetime.now().isoformat(timespec='seconds'),
        'only_visible': str(only_visible),
        'target_collections': ",".join(target_collections) if target_collections else "",
    }
    return SceneViewBundle(cameras=cameras, lights=lights, meta=meta)


def write_json(bundle: SceneViewBundle, export_dir: str = DEFAULT_EXPORT_DIR, filename_fmt: str = DEFAULT_FILENAME_FMT) -> str:
    ensure_dir(export_dir)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    path = os.path.join(export_dir, filename_fmt.format(timestamp=timestamp))

    def cam_to_dict(c: CameraExport):
        return {
            'name': c.name,
            'object_name': c.object_name,
            'collection_path': c.collection_path,
            'transform': c.transform,
            'world_matrix': c.world_matrix,
            'type': c.cam_type,
            'lens_unit': c.lens_unit,
            'lens_mm': c.lens_mm,
            'sensor_fit': c.sensor_fit,
            'sensor_width': c.sensor_width,
            'sensor_height': c.sensor_height,
            'shift_x': c.shift_x,
            'shift_y': c.shift_y,
            'angle_x': c.angle_x,
            'angle_y': c.angle_y,
            'clip_start': c.clip_start,
            'clip_end': c.clip_end,
            'dof': c.dof,
            'panorama': c.panorama,
        }

    def light_to_dict(l: LightExport):
        return {
            'name': l.name,
            'object_name': l.object_name,
            'collection_path': l.collection_path,
            'transform': l.transform,
            'world_matrix': l.world_matrix,
            'type': l.light_type,
            'color': list(l.color),
            'energy': l.energy,
            'shadow_soft_size': l.shadow_soft_size,
            'extras': l.extras,
            'shadow': l.shadow,
        }

    data = {
        'scene_view': {
            'cameras': [cam_to_dict(c) for c in bundle.cameras],
            'lights': [light_to_dict(l) for l in bundle.lights],
            'meta': bundle.meta,
        }
    }

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

    print(f"[INFO] Scene View export written: {path}")
    return path



if __name__ == "__main__":
    bundle = export_scene_view(
        target_collections=None,  # exportă TOATE camerele și luminile
        only_visible=True,        # dacă iese gol, schimbă temporar în False
    )
    out = write_json(bundle)
    print(f"[SUMMARY] cameras={len(bundle.cameras)} lights={len(bundle.lights)} out={out}")
