AI3DCNC — MANIFEST (v1)

Public, Apache-2.0. No secrets. No files >50 MB.

Structure: parsers/, builders/, docs/, schemas/, samples/, tools/.

Combined JSON: scene_export_[timestamp].json with sections: mesh, scene_view, materials, collections, geometry_nodes, world, render, meta, bool_ops.

Test order: Mesh → Scene View → Materials → Collections → GN → Aggregator → Builders.

Generated artifacts (committed for convenience):

parsers_all.py, builders_all.py

Header: # AUTO-GENERATED. DO NOT EDIT.

Source of truth: the modular files in parsers/ and builders/.

Generation script

Located at tools/gen_all.py. Run with python tools/gen_all.py from repo root.

Concatenates in fixed order and writes parsers_all.py and builders_all.py.

Inserts clear separators like # ===== file: parsers/parser_mesh.py =====.

UTC timestamp in header.

File order

Parsers

parsers/parser_mesh.py

parsers/parser_scene.py

parsers/parser_materials.py

parsers/parser_collections.py

parsers/parser_boolops.py

parsers/parser_gn.py

parsers/parser_scene_view.py

Builders

builders/builder_mesh.py

builders/builder_scene_import.py

builders/builder_scene_view.py

builders/builder_materials.py

builders/builder_collections.py

builders/builder_gn_overrides.py

builders/builder_boolops.py

Commit rules

Short messages. Examples:add MANIFEST.md and manifest.jsonadd generator and concatenated filesupdate gen_all order

Never edit generated files by hand.