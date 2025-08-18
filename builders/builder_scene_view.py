import bpy, json, os

"""
KEROS_exportGPT — builder_collections (canonical, robust)

Recreates/updates the collection hierarchy and object membership from JSON.
- Accepts {"collections":{"collections":[...]}} or {"collections":[...]} or a raw list.
- Supports either explicit hierarchical paths (e.g. "Room/Kitchen/Cabinets") or {parent, name} per item.
- Links collections under Scene root if no parent is provided.
- Links objects to target collections (doesn't unlink from other collections).
- Applies basic layer flags (exclude / hide_viewport) when available.
- Prints short [SUMMARY] lines.

Expected minimal item keys (any of the following styles):
  {"path": "A/B/C", "objects":["Cube"]}
  {"name": "C", "parent": "B", "objects":["Cube"]}
  {"name": "Top", "objects": []}

Optional keys per item:
  "children": ["sub1", "sub2", ...]   # informational; actual creation driven by path/parent or separate items
  "exclude": bool, "hide": bool        # also accepts "hide_viewport", "excluded"
"""

# -----------------------------
# JSON helpers
# -----------------------------

def _read_json(path: str):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _collection_items_from_data(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        d = data.get('collections')
        if isinstance(d, dict):
            return d.get('collections') or []
        if isinstance(d, list):
            return d
    return []


# -----------------------------
# Blender helpers
# -----------------------------

def _find_object_case_insensitive(name: str):
    if not name:
        return None
    lname = name.lower()
    for ob in bpy.data.objects:
        if ob.name.lower() == lname:
            return ob
    for ob in bpy.data.objects:
        if ob.name.lower().startswith(lname):
            return ob
    for ob in bpy.data.objects:
        if lname in ob.name.lower():
            return ob
    return None


def _is_linked_collection(parent: bpy.types.Collection, child: bpy.types.Collection) -> bool:
    return any(c is child for c in parent.children)


def _ensure_collection(name: str) -> bpy.types.Collection:
    col = bpy.data.collections.get(name)
    if not col:
        col = bpy.data.collections.new(name)
    # ensure it's linked into the scene if top-level
    if not any(c is col for c in bpy.context.scene.collection.children):
        bpy.context.scene.collection.children.link(col)
    return col


def _ensure_chain(parts: list[str]) -> bpy.types.Collection:
    parent = None
    for i, part in enumerate(parts):
        # reuse if exists; else create
        col = bpy.data.collections.get(part)
        if not col:
            col = bpy.data.collections.new(part)
        # link under parent or scene
        if parent:
            if not _is_linked_collection(parent, col):
                parent.children.link(col)
        else:
            if not any(c is col for c in bpy.context.scene.collection.children):
                bpy.context.scene.collection.children.link(col)
        parent = col
    return parent


def _layer_collection_for(view_layer: bpy.types.ViewLayer, collection: bpy.types.Collection):
    def _recurse(lc):
        if lc.collection == collection:
            return lc
        for ch in lc.children:
            got = _recurse(ch)
            if got:
                return got
        return None
    return _recurse(view_layer.layer_collection)


def _apply_layer_flags(collection: bpy.types.Collection, item: dict):
    if not collection:
        return False
    flags = item or {}
    # normalize keys
    exclude = flags.get('exclude')
    if exclude is None:
        exclude = flags.get('excluded')
    hide = flags.get('hide')
    if hide is None:
        hide = flags.get('hide_viewport')

    applied = False
    lc = _layer_collection_for(bpy.context.view_layer, collection)
    if lc:
        try:
            if exclude is not None:
                lc.exclude = bool(exclude); applied = True
            if hide is not None:
                lc.hide_viewport = bool(hide); applied = True
        except Exception:
            pass
    return applied


def _link_object_to_collection(obj: bpy.types.Object, col: bpy.types.Collection) -> bool:
    if not obj or not col:
        return False
    if any(c is col for c in obj.users_collection):
        return False
    try:
        col.objects.link(obj)
        return True
    except Exception:
        return False


# -----------------------------
# Core build
# -----------------------------

def _parts_from_item(item: dict) -> list[str]:
    path = item.get('path') or item.get('hierarchy_path') or item.get('hierarchy') or item.get('full_path')
    if isinstance(path, str) and path.strip():
        return [p for p in path.split('/') if p]
    name = item.get('name') or 'Collection'
    parent = item.get('parent')
    parts = []
    if parent and isinstance(parent, str) and parent.strip():
        parts.append(parent.strip())
    parts.append(name)
    return parts


def build_single_collection(item: dict, verbose: bool=False) -> dict:
    parts = _parts_from_item(item)
    col = _ensure_chain(parts)

    objs = item.get('objects') or item.get('items') or []
    linked = 0; missing = 0
    for on in objs:
        ob = _find_object_case_insensitive(on)
        if not ob:
            missing += 1
            continue
        if _link_object_to_collection(ob, col):
            linked += 1

    flags_applied = _apply_layer_flags(col, item)

    if verbose:
        print(f"[DEBUG] collection '{col.name}' parts={parts} linked={linked} missing={missing} flags={flags_applied}")
    print(f"[SUMMARY] collections_build: name={col.name} linked={linked} missing={missing}")
    return {"name": col.name, "linked": linked, "missing": missing, "flags": bool(flags_applied)}


# -----------------------------
# Batch API
# -----------------------------

def import_from_data(data: dict, only_first_n: int | None = None, verbose: bool=False) -> dict:
    items = _collection_items_from_data(data)
    if only_first_n is not None:
        items = items[:only_first_n]
    stats = {"items": len(items), "built": 0, "linked": 0, "missing": 0, "flags": 0}
    for it in items:
        try:
            out = build_single_collection(it, verbose=verbose)
            stats["built"] += 1
            stats["linked"] += out.get("linked", 0)
            stats["missing"] += out.get("missing", 0)
            stats["flags"] += 1 if out.get("flags") else 0
        except Exception as e:
            print(f"[WARN] collection build failed for {it.get('name','?')}: {e}")
    print(f"[SUMMARY] collections_apply: items={stats['items']} built={stats['built']} linked={stats['linked']} missing={stats['missing']} flags={stats['flags']}")
    return stats


def import_from_file(path: str, only_first_n: int | None = None, verbose: bool=False) -> dict:
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    data = _read_json(path)
    return import_from_data(data, only_first_n=only_first_n, verbose=verbose)


# -----------------------------
# Self-test (disabled)
# -----------------------------
if __name__ == "__main__" and False:
    p = bpy.path.abspath("//_EXPORTS/scene_export_test.json")
    import_from_file(p, only_first_n=3, verbose=True)
