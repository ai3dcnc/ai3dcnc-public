{
  "version": 2,
  "raw_base": "https://raw.githubusercontent.com/ai3dcnc/ai3dcnc-public/v0.1.1/",
  "groups": [
    {
      "name": "parsers",
      "files": [
        "parsers/parser_mesh.py",
        "parsers/parser_scene.py",
        "parsers/parser_materials.py",
        "parsers/parser_collections.py",
        "parsers/parser_boolops.py",
        "parsers/parser_gn.py",
        "parsers/parser_scene_view.py"
      ]
    },
    {
      "name": "builders",
      "files": [
        "builders/builder_mesh.py",
        "builders/builder_scene_import.py",
        "builders/builder_scene_view.py",
        "builders/builder_materials.py",
        "builders/builder_collections.py",
        "builders/builder_gn_overrides.py",
        "builders/builder_boolops.py"
      ]
    },
    {
      "name": "docs",
      "files": [
        "docs/credits.md",
        "docs/defensive-publication.md"
      ]
    },
    {
      "name": "schemas",
      "files": []
    },
    {
      "name": "samples",
      "files": []
    },
    {
      "name": "tools",
      "files": [
        "tools/gen_all.py"
      ]
    }
  ],
  "entrypoints": [
    "parsers/parser_mesh.py",
    "parsers/parser_scene.py",
    "parsers/parser_materials.py",
    "parsers/parser_collections.py",
    "parsers/parser_boolops.py",
    "parsers/parser_gn.py",
    "parsers/parser_scene_view.py",
    "builders/builder_mesh.py",
    "builders/builder_scene_import.py",
    "builders/builder_scene_view.py",
    "builders/builder_materials.py",
    "builders/builder_collections.py",
    "builders/builder_gn_overrides.py",
    "builders/builder_boolops.py",
    "docs/credits.md",
    "docs/defensive-publication.md",
    "tools/gen_all.py"
  ],
  "aliases": {}
}
