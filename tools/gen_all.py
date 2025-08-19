# tools/gen_all.py
# Concatenate parsers/ and builders/ into parsers_all.py and builders_all.py
# AUTO-GENERATED. DO NOT EDIT THE OUTPUT FILES.

from pathlib import Path
from datetime import datetime

# Repo root = parent of this file's folder (tools/)
ROOT = Path(__file__).resolve().parents[1]

# Exact order to concatenate
PARSERS = [
    "parsers/parser_mesh.py",
    "parsers/parser_scene.py",
    "parsers/parser_materials.py",
    "parsers/parser_collections.py",
    "parsers/parser_boolops.py",
    "parsers/parser_gn.py",
    "parsers/parser_scene_view.py",
]

BUILDERS = [
    # build order hint: materials -> mesh -> collections -> scene_view -> gn_overrides -> boolops -> scene_import
    "builders/builder_materials.py",
    "builders/builder_mesh.py",
    "builders/builder_collections.py",
    "builders/builder_scene_view.py",
    "builders/builder_gn_overrides.py",
    "builders/builder_boolops.py",
    "builders/builder_scene_import.py",
]

HEADER = (
    "# AUTO-GENERATED. DO NOT EDIT.\n"
    "# Generated UTC: {ts}\n"
)


def _concat(rel_paths: list[str], out_name: str) -> None:
    out_path = ROOT / out_name
    parts = []
    ts = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    parts.append(HEADER.format(ts=ts))
    for rel in rel_paths:
        src = ROOT / rel
        if not src.exists():
            parts.append(f"\n# [WARNING] Missing file: {rel}\n")
            continue
        parts.append(f"\n# ===== file: {rel} =====\n")
        parts.append(src.read_text(encoding="utf-8"))
        if not parts[-1].endswith("\n"):
            parts.append("\n")
        parts.append(f"# ===== end {rel} =====\n")
    out_path.write_text("".join(parts), encoding="utf-8")
    print(f"[SUMMARY] wrote {out_name} parts={len(rel_paths)} -> {out_path}")


if __name__ == "__main__":
    _concat(PARSERS, "parsers_all.py")
    _concat(BUILDERS, "builders_all.py")
    print("[SUMMARY] done")
