import bpy
import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Iterable, Any

"""
KEROS_exportGPT — Collections Parser v1 (Blender 4.2 LTS)

Exports the collection hierarchy, visibility flags (collection + view layer), and object membership.

Default export path: G:/My Drive/BLENDER_EXPORT
Default filename: scene_export_[timestamp].json

Notes:
- We export *all* bpy.data.collections by default, preserving parent/children relations.
- Visibility flags are exported from both Collection and active View Layer's LayerCollection (if found).
- Object membership lists object names directly contained in the collection (no recursion).
- Safe getattr is used to tolerate Blender API differences.
"""

# ===============================
# Config
# ===============================
DEFAULT_EXPORT_DIR = r"G:/My Drive/BLENDER_EXPORT"
DEFAULT_FILENAME_FMT = "scene_export_{timestamp}.json"

# ===============================
# Dataclasses
# ===============================
@dataclass
class CollectionFlags:
    # Collection-level flags (may not control view layer display)
    hide_viewport: Optional[bool]
    hide_render: Optional[bool]
    color_tag: Optional[str]

@dataclass
class LayerFlags:
    found: bool
    exclude: Optional[bool]
    hide_viewport: Optional[bool]
    hide_render: Optional[bool]

@dataclass
class CollectionExport:
    name: str
    path: List[str]                       # ancestry from root(s)
    parent: Optional[str]
    children: List[str]
    objects: List[str]                    # names directly in this collection
    flags: CollectionFlags
    layer_flags: LayerFlags

@dataclass
class CollectionsBundle:
    collections: List[CollectionExport]
    meta: Dict[str, str]

# ===============================
# Helpers
# ===============================

def ensure_dir(path: str) -> None:
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def get_parent(coll: bpy.types.Collection) -> Optional[bpy.types.Collection]:
    # There's no direct parent pointer; we find it by searching all collections' children
    for c in bpy.data.collections:
        if coll.name in [ch.name for ch in c.children]:
            return c
    return None


def ancestry_path(coll: bpy.types.Collection) -> List[str]:
    names: List[str] = []
    cur = coll
    guard = 0
    while cur and guard < 128:
        p = get_parent(cur)
        if p is None:
            names.insert(0, cur.name)
            break
        names.insert(0, p.name)
        cur = p
        guard += 1
    return names


def find_layer_collection(layer_coll: bpy.types.LayerCollection, target: bpy.types.Collection) -> Optional[bpy.types.LayerCollection]:
    if layer_coll.collection == target:
        return layer_coll
    for child in layer_coll.children:
        found = find_layer_collection(child, target)
        if found:
            return found
    return None


def collect_one(coll: bpy.types.Collection, view_layer: bpy.types.ViewLayer) -> CollectionExport:
    # Collection-level flags
    hide_viewport = getattr(coll, 'hide_viewport', None)
    hide_render = getattr(coll, 'hide_render', None)
    color_tag = getattr(coll, 'color_tag', None)

    flags = CollectionFlags(hide_viewport=hide_viewport, hide_render=hide_render, color_tag=color_tag)

    # Layer flags from the active view layer
    lc = find_layer_collection(view_layer.layer_collection, coll) if view_layer else None
    if lc is not None:
        layer_flags = LayerFlags(
            found=True,
            exclude=getattr(lc, 'exclude', None),
            hide_viewport=getattr(lc, 'hide_viewport', None),
            hide_render=getattr(lc, 'hide_render', None),
        )
    else:
        layer_flags = LayerFlags(found=False, exclude=None, hide_viewport=None, hide_render=None)

    # Children + objects
    children = [c.name for c in coll.children]
    objects = [o.name for o in coll.objects]

    return CollectionExport(
        name=coll.name,
        path=ancestry_path(coll),
        parent=get_parent(coll).name if get_parent(coll) else None,
        children=children,
        objects=objects,
        flags=flags,
        layer_flags=layer_flags,
    )

# ===============================
# Public API
# ===============================

def export_collections(*, active_view_layer: Optional[bpy.types.ViewLayer] = None) -> CollectionsBundle:
    if active_view_layer is None:
        active_view_layer = bpy.context.view_layer

    exports: List[CollectionExport] = []
    for coll in bpy.data.collections:
        try:
            exports.append(collect_one(coll, active_view_layer))
        except Exception as e:
            print(f"[WARN] Failed to export collection {coll.name}: {e}")

    meta = {
        'exporter': 'KEROS_exportGPT.collections_v1',
        'blender_version': bpy.app.version_string,
        'timestamp': datetime.now().isoformat(timespec='seconds'),
        'view_layer': active_view_layer.name if active_view_layer else '',
    }
    return CollectionsBundle(collections=exports, meta=meta)


def write_json(bundle: CollectionsBundle, export_dir: str = DEFAULT_EXPORT_DIR, filename_fmt: str = DEFAULT_FILENAME_FMT) -> str:
    ensure_dir(export_dir)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    path = os.path.join(export_dir, filename_fmt.format(timestamp=timestamp))

    def flags_to_dict(f: CollectionFlags):
        return {
            'hide_viewport': f.hide_viewport,
            'hide_render': f.hide_render,
            'color_tag': f.color_tag,
        }

    def layer_to_dict(l: LayerFlags):
        return {
            'found': l.found,
            'exclude': l.exclude,
            'hide_viewport': l.hide_viewport,
            'hide_render': l.hide_render,
        }

    data = {
        'collections': {
            'collections': [
                {
                    'name': c.name,
                    'path': c.path,
                    'parent': c.parent,
                    'children': c.children,
                    'objects': c.objects,
                    'flags': flags_to_dict(c.flags),
                    'layer_flags': layer_to_dict(c.layer_flags),
                }
                for c in bundle.collections
            ],
            'meta': bundle.meta,
        }
    }

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

    print(f"[INFO] Collections export (v1) written: {path}")
    return path


if __name__ == '__main__':
    bundle = export_collections(active_view_layer=bpy.context.view_layer)
    write_json(bundle)
