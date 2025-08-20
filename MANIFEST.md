{
  "version": 2,
  "updated": "2025-08-20",
  "license": "Apache-2.0",
  "raw_base": "https://raw.githubusercontent.com/<owner>/<repo>/main/",
  "bundles": {
    "parsers_all": "parsers_all.py",
    "builders_all": "builders_all.py"
  },
  "modules": {
    "parsers": [
      "parsers/parser_mesh.py",
      "parsers/parser_scene.py",
      "parsers/parser_materials.py",
      "parsers/parser_collections.py",
      "parsers/parser_boolops.py",
      "parsers/parser_gn.py",
      "parsers/parser_scene_view.py"
    ],
    "builders": [
      "builders/builder_materials.py",
      "builders/builder_mesh.py",
      "builders/builder_collections.py",
      "builders/builder_scene_view.py",
      "builders/builder_gn_overrides.py",
      "builders/builder_boolops.py",
      "builders/builder_scene_import.py"
    ],
    "docs": [
      "docs/defensive-publication.md",
      "docs/credits.md",
      "docs/REPO_MAP.md"
    ],
    "samples": [
      "samples/sample_min_scene.json"
    ],
    "schemas": [
      "schemas/mesh_v1.schema.json"
    ],
    "tools": [
      "tools/gen_all.py"
    ]
  },
  "entrypoints": {
    "export_scene": "parsers/parser_scene.py:export_scene",
    "write_scene_json": "parsers/parser_scene.py:write_scene_json",
    "import_scene": "builders/builder_scene_import.py:import_scene_from_file",
    "apply_mesh": "builders/builder_mesh.py:apply_from_file",
    "apply_materials": "builders/builder_materials.py:apply_from_file",
    "apply_collections": "builders/builder_collections.py:apply_from_file",
    "apply_scene_view": "builders/builder_scene_view.py:apply_from_file",
    "apply_gn_overrides": "builders/builder_gn_overrides.py:apply_from_file"
  },
  "aliases": {
    "builder_materials": ["builder_materials", "builder_materials_v1", "materials_builder"],
    "builder_mesh": ["builder_mesh", "builder_mesh_v2", "mesh_builder"],
    "builder_collections": ["builder_collections", "builder_collections_v1", "collections_builder"],
    "builder_scene_view": ["builder_scene_view", "builder_scene_view_4_2", "scene_view_builder"],
    "builder_gn_overrides": ["builder_gn_overrides", "builder_gn", "builder_geometry_nodes", "gn_overrides_builder"]
  },
  "rules": {
    "resolution": "prefer bundles; if detail needed, read modules under raw_base",
    "fallback": "if an entrypoint is missing, try aliases in order"
  }
}
