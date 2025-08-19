# AI3DCNC — MANIFEST (v1)

* Public, Apache-2.0. No secrets. No files >50 MB.
* Structure: `parsers/`, `builders/`, `docs/`, `schemas/`, `samples/`, `tools/`.
* Combined JSON: `scene_export_[timestamp].json` with sections: `mesh`, `scene_view`, `materials`, `collections`, `geometry_nodes`, `world`, `render`, `meta`, `bool_ops`.
* Test order: Mesh → Scene View → Materials → Collections → GN → Aggregator → Builders.
* Generated artifacts (committed for convenience):

  * `parsers_all.py`, `builders_all.py`
  * Header: `# AUTO-GENERATED. DO NOT EDIT.`
  * Source of truth: the modular files in `parsers/` and `builders/`.

## Generation script

Located at `tools/gen_all.py`. Run with `python tools/gen_all.py` from repo root.

```python
# tools/gen_all.py
# Concatenate parsers/ and builders/ into parsers_all.py and builders_all.py
# AUTO-GENERATED SCRIPT

import os, datetime

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

HEADER = "# AUTO-GENERATED. DO NOT EDIT.\\n# UTC: {}\\n"

def concat(files, out_file):
    with open(out_file, "w", encoding="utf-8") as out:
        out.write(HEADER.format(datetime.datetime.utcnow().isoformat()))
        for f in files:
            out.write(f"\\n# ===== file: {f} =====\\n")
            with open(f, "r", encoding="utf-8") as src:
                out.write(src.read())
            out.write(f"\\n# ===== end {f} =====\\n")

if __name__ == "__main__":
    concat(PARSERS, "parsers_all.py")
    concat(BUILDERS, "builders_all.py")
    print("[SUMMARY] parsers_all.py and builders_all.py generated.")
```

## Commit rules

* Short messages. Examples:
  `add MANIFEST.md and manifest.json`
  `add generator and concatenated files`
  `update gen_all order`
* Never edit generated files by hand.
