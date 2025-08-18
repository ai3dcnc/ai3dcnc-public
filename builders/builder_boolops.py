import bpy, json
from typing import Dict, Any

def _get(name: str):
    return bpy.data.objects.get(name)

def apply_boolops_dict(doc: Dict[str, Any], create_missing_cutters: bool = False) -> int:
    data = doc.get("bool_ops") or {}
    targets = data.get("targets") or []
    applied = 0
    for t in targets:
        tgt = _get(t.get("name", ""))
        if not tgt or getattr(tgt, "type", None) != "MESH":
            continue
        # remove existing KRS bools to avoid dupes
        for m in list(tgt.modifiers):
            if m.type == "BOOLEAN" and m.name.startswith("KRS_BOOL_"):
                try: tgt.modifiers.remove(m)
                except Exception: pass
        for m in t.get("modifiers", []):
            cutter = _get(m.get("cutter", ""))
            if not cutter:
                if not create_missing_cutters: continue
                try:
                    me = bpy.data.meshes.new(m.get("cutter") or "Cutter")
                    cutter = bpy.data.objects.new(m.get("cutter") or "Cutter", me)
                    bpy.context.scene.collection.objects.link(cutter)
                except Exception: continue
            try:
                mod = tgt.modifiers.new(name=m.get("name") or "KRS_BOOL", type="BOOLEAN")
                mod.operation = m.get("operation", "DIFFERENCE")
                mod.solver = m.get("solver", "EXACT")
                mod.object = cutter
                mod.show_viewport = bool(m.get("show_viewport", True))
                mod.show_render = bool(m.get("show_render", True))
                applied += 1
            except Exception:
                pass
    print(f"[SUMMARY] builder_boolops applied_mods={applied}")
    return applied

def apply_boolops_json(path: str, create_missing_cutters: bool = False) -> int:
    with open(path, "r", encoding="utf-8") as f:
        doc = json.load(f)
    return apply_boolops_dict(doc, create_missing_cutters=create_missing_cutters)
