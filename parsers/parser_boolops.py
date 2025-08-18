import bpy, os, json
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import List, Dict, Any, Optional

DEFAULT_EXPORT_DIR = r"G:/My Drive/BLENDER_EXPORT"
FALLBACK_EXPORT_DIR = "//_EXPORTS"
DEFAULT_FILENAME_FMT = "scene_export_{timestamp}.json"

# -------- helpers --------
def _abs(p: str) -> str:
    try:  return os.path.abspath(bpy.path.abspath(p))
    except Exception: return bpy.path.abspath(p)

def _ensure_dir(path: str) -> str:
    p = _abs(path)
    try:
        os.makedirs(p, exist_ok=True)
        # writability probe
        test = os.path.join(p, "__krs_probe.tmp")
        open(test, "w").write("ok"); os.remove(test)
        return p
    except Exception:
        fp = _abs(FALLBACK_EXPORT_DIR)
        os.makedirs(fp, exist_ok=True)
        return fp

def _visible(obj) -> bool:
    try: return obj.visible_get()
    except Exception: return True

def _in_collections(obj, names: Optional[List[str]]) -> bool:
    if not names: return True
    cols = {c.name for c in obj.users_collection}
    return any(n in cols for n in names)

# -------- schema --------
@dataclass
class BoolMod:
    name: str
    operation: str
    solver: str
    cutter: str
    show_viewport: bool
    show_render: bool
    is_krs: bool

@dataclass
class BoolTarget:
    name: str
    hidden: bool
    collections: List[str]
    modifiers: List[BoolMod] = field(default_factory=list)

@dataclass
class BoolOpsBundle:
    targets: List[BoolTarget]
    meta: Dict[str, Any]

# -------- export --------
def export_boolops(target_collections: Optional[List[str]] = None,
                   only_visible: bool = True) -> BoolOpsBundle:
    targets: List[BoolTarget] = []
    for ob in bpy.context.scene.objects:
        if getattr(ob, "type", None) != "MESH": continue
        if only_visible and not _visible(ob): continue
        if not _in_collections(ob, target_collections): continue
        mods = [m for m in ob.modifiers if m.type == "BOOLEAN"]
        if not mods: continue
        targets.append(BoolTarget(
            name=ob.name,
            hidden=bool(getattr(ob, "hide_render", False) or ob.hide_get()),
            collections=[c.name for c in ob.users_collection],
            modifiers=[BoolMod(
                name=m.name,
                operation=str(getattr(m, "operation", "DIFFERENCE")),
                solver=str(getattr(m, "solver", "EXACT")),
                cutter=getattr(getattr(m, "object", None), "name", ""),
                show_viewport=bool(getattr(m, "show_viewport", True)),
                show_render=bool(getattr(m, "show_render", True)),
                is_krs=str(m.name).startswith("KRS_BOOL_"),
            ) for m in mods],
        ))
    meta = {
        "exporter": "parser_boolops",
        "blender_version": bpy.app.version_string,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "target_collections": ",".join(target_collections) if target_collections else "",
        "only_visible": bool(only_visible),
        "notes": "Boolean modifier inventory by object",
    }
    return BoolOpsBundle(targets=targets, meta=meta)

def write_json(bundle: BoolOpsBundle,
               export_dir: str = DEFAULT_EXPORT_DIR,
               filename_fmt: str = DEFAULT_FILENAME_FMT) -> str:
    out_dir = _ensure_dir(export_dir)
    path = os.path.join(out_dir, filename_fmt.format(
        timestamp=datetime.now().strftime("%Y-%m-%d_%H-%M-%S")))
    data = {
        "bool_ops": {
            "targets": [{
                "name": t.name,
                "hidden": t.hidden,
                "collections": t.collections,
                "modifiers": [asdict(m) for m in t.modifiers],
            } for t in bundle.targets],
            "meta": bundle.meta,
        }
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"[INFO] BoolOps export written: {path}")
    print(f"[SUMMARY] bool_targets={len(bundle.targets)}")
    return path
