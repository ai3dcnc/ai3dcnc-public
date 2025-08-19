# tools/gen_all.py
# Concatenate parsers/ and builders/ into parsers_all.py and builders_all.py
# AUTO-GENERATED SCRIPT

import os
import datetime

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
    "builders/builder_mesh.py",
    "builders/builder_scene_import.py",
    "builders/builder_scene_view.py",
    "builders/builder_materials.py",
    "builders/builder_collections.py",
    "builders/builder_gn_overrides.py",
    "builders/builder_boolops.py",
]

HEADER = "# AUTO-GENERATED. DO NOT EDIT.\n# UTC: {}\n"

def concat(files, out_file):
    with open(out_file, "w", encoding="utf-8") as out:
        out.write(HEADER.format(datetime.datetime.utcnow().isoformat()))
        for f in files:
            if os.path.exists(f):
                out.write(f"\n# ===== file: {f} =====\n")
                with open(f, "r", encoding="utf-8") as src:
                    out.write(src.read())
                out.write(f"\n# ===== end {f} =====\n")
            else:
                out.write(f"\n# [WARNING] Missing file: {f}\n")

if __name__ == "__main__":
    concat(PARSERS, "parsers_all.py")
    concat(BUILDERS, "builders_all.py")
    print("[SUMMARY] parsers_all.py and builders_all.py generated.")
```
