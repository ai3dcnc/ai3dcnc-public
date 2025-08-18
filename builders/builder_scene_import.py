import bpy, json, os, importlib, sys
from typing import Any, Dict, List, Optional, Tuple

"""
KEROS_exportGPT — Scene Import Aggregator (builder_scene_import.py) — Perfect v1.2
Blender 3.6 ↔ 4.2 LTS safe. Canonical‑first, tolerant, short [SUMMARY].

What it does
- Loads a combined JSON (scene_export_*.json) and calls builders in **correct order**:
  1) Materials → 2) Mesh → 3) Collections → 4) Scene View → 5) Geometry Nodes (overrides)
- Canonical module names first, with **fallbacks** to older names. Never crashes if a builder is missing.
- Accepts wrapped sections (e.g. {"materials":{...}}) or flat lists; builders are tolerant anyway.
- Optionally creates GN placeholders (cubes/groups) when `auto_create_placeholders=True`.
- Emits one concise `[SUMMARY] import_scene: ...` line.

Public API
- import_scene_from_file(file_path, auto_create_placeholders=False, only_first_n=None, verbose=False, builders_path=None)
- import_scene_from_data(data,    auto_create_placeholders=False, only_first_n=None, verbose=False, builders_path=None)
- (compat) import_scene(file_path, auto_create_placeholders=False, **kw)
"""

# =============================
# Module loading (canonical-first + fallback)
# =============================

_BUILDER_CANDIDATES = {
    'materials':  ['builder_materials', 'builder_materials_v1', 'materials_builder'],
    'mesh':       ['builder_mesh', 'builder_mesh_v2', 'mesh_builder'],
    'collections':['builder_collections', 'builder_collections_v1', 'collections_builder'],
    'scene_view': ['builder_scene_view', 'builder_scene_view_4_2', 'scene_view_builder'],
    'gn':         ['builder_gn_overrides', 'builder_gn', 'builder_geometry_nodes', 'gn_overrides_builder'],
}

_FUNC_CANDIDATES = ['apply_from_data', 'import_from_data', 'apply', 'run']


def _maybe_add_builders_path(path: Optional[str]) -> None:
    if not path:
        return
    if path not in sys.path:
        sys.path.insert(0, path)


def _import_first(names: List[str]) -> Optional[Any]:
    for name in names:
        try:
            return importlib.import_module(name)
        except Exception:
            continue
    return None


def _get_apply_func(mod: Any) -> Optional[Any]:
    if not mod:
        return None
    for fname in _FUNC_CANDIDATES:
        fn = getattr(mod, fname, None)
        if callable(fn):
            return fn
    return None


# =============================
# Section extraction + optional limiting (only_first_n)
# =============================

_LIST_KEYS_BY_SECTION = {
    'materials': ['materials'],
    'mesh': ['meshes'],
    'collections': ['collections'],
    'scene_view': ['cameras', 'lights'],
    'gn': ['overrides'],
}


def _section(data: Dict[str, Any], key: str) -> Dict[str, Any]:
    """Return the expected subsection. Tolerates several shapes."""
    if key in data and isinstance(data[key], dict):
        return data[key]
    # geometry_nodes is the canonical container for GN
    if key == 'gn':
        gn = data.get('geometry_nodes')
        if isinstance(gn, dict):
            return gn
    return data  # plain blob; builders are tolerant


def _limited_section(sec: Dict[str, Any], key: str, only_first_n: Optional[int]) -> Dict[str, Any]:
    if not only_first_n or only_first_n <= 0:
        return sec
    out = dict(sec)
    list_keys = _LIST_KEYS_BY_SECTION.get(key, [])
    for lk in list_keys:
        lst = sec.get(lk)
        if isinstance(lst, list):
            out[lk] = lst[:only_first_n]
    return out


# =============================
# Core API
# =============================

def import_scene_from_data(data: Dict[str, Any],
                           auto_create_placeholders: bool = False,
                           only_first_n: Optional[int] = None,
                           verbose: bool = False,
                           builders_path: Optional[str] = None) -> Dict[str, Any]:
    """Import all sections in the canonical order. Returns stats dict.
    Prints one [SUMMARY] line.
    """
    _maybe_add_builders_path(builders_path)

    stats = {
        'materials': 'missing',
        'mesh': 'missing',
        'collections': 'missing',
        'scene_view': 'missing',
        'gn': 'missing',
        'missing_modules': [],
        'errors': [],
    }

    def _run(section_key: str, module_key: str, extra_kwargs: Dict[str, Any] = None):
        nonlocal stats
        extra_kwargs = extra_kwargs or {}
        mod = _import_first(_BUILDER_CANDIDATES[module_key])
        fn = _get_apply_func(mod)
        if not fn:
            stats['missing_modules'].append(module_key)
            if verbose:
                print(f"[WARN] builder module missing for {module_key}: {_BUILDER_CANDIDATES[module_key]}")
            return 'missing'

        sec = _section(data, section_key if module_key != 'gn' else 'gn')
        sec = _limited_section(sec, module_key, only_first_n)

        try:
            if module_key == 'gn':
                # geometry nodes overrides accept placeholders flag
                fn(sec, create_placeholders=bool(auto_create_placeholders), verbose=verbose)
            else:
                fn(sec, verbose=verbose)
            return 'ok'
        except Exception as e:
            stats['errors'].append(f"{module_key}: {e}")
            if verbose:
                import traceback; traceback.print_exc()
            return 'error'

    # 1) Materials
    stats['materials'] = _run('materials', 'materials')
    # 2) Mesh
    stats['mesh'] = _run('mesh', 'mesh')
    # 3) Collections
    stats['collections'] = _run('collections', 'collections')
    # 4) Scene View
    stats['scene_view'] = _run('scene_view', 'scene_view')
    # 5) GN Overrides
    stats['gn'] = _run('geometry_nodes', 'gn')

    missing = [k for k,v in stats.items() if k in ('materials','mesh','collections','scene_view','gn') and v=='missing']
    errs = len(stats['errors'])
    missing_str = 'none' if not missing else ','.join(missing)

    print(f"[SUMMARY] import_scene: materials={stats['materials']} mesh={stats['mesh']} collections={stats['collections']} scene_view={stats['scene_view']} gn={stats['gn']} missing={missing_str} errors={errs}")
    return stats


def import_scene_from_file(file_path: str,
                           auto_create_placeholders: bool = False,
                           only_first_n: Optional[int] = None,
                           verbose: bool = False,
                           builders_path: Optional[str] = None) -> Dict[str, Any]:
    if not os.path.exists(file_path):
        raise FileNotFoundError(file_path)
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return import_scene_from_data(data,
                                  auto_create_placeholders=auto_create_placeholders,
                                  only_first_n=only_first_n,
                                  verbose=verbose,
                                  builders_path=builders_path)


# Back-compat name used by KRS Tools

def import_scene(file_path: str, auto_create_placeholders: bool = False, **kw) -> Dict[str, Any]:
    return import_scene_from_file(file_path, auto_create_placeholders=auto_create_placeholders, **kw)


# =============================
# Self-test (disabled)
# =============================
if __name__ == "__main__" and False:
    p = bpy.path.abspath("//_EXPORTS/scene_export_test.json")
    import_scene_from_file(p, auto_create_placeholders=True, verbose=True)
