# AI3DCNC — Defensive Publication (open‑core)

Version: v0.1 • Date: 2025‑08‑19  • License: Apache‑2.0

## Purpose

Establishes **prior art** for the AI3DCNC open‑core: JSON exporters from Blender 3.6↔4.2, corresponding import/builders, and a single‑file add‑on "AI\_TOOLS" embedding parsers and builders. No patent claims. This is defensive publication under Apache‑2.0 (see `LICENSE`).

## Scope

Publicly fixed:

* **Parsers v1**: `mesh`, `materials`, `collections_v1`, `scene_view`, `geometry_nodes v4`, `parser_scene_v1` (aggregator), `bool_ops`.
* **Builders**: `builder_mesh`, `builder_materials`, `builder_collections`, `builder_scene_view`, `builder_gn_overrides`, `builder_boolops`, `builder_scene_import` (orders import: materials→mesh→collections→scene\_view→GN overrides).
* **Single‑file add‑on**: `AI_TOOLS` with sidebar: Export/Import ALL, per‑parser export/import, Quick Camera+Light, Quick JPG Render, "Apply BoolOps from JSON". Preferences: Export Dir, Import Dir, "Apply BoolOps on import".
* **JSON format**: sections `mesh, scene_view, materials, collections, geometry_nodes, meta, render, world, bool_ops`.

## Key technical contributions (prior art)

1. **Mesh export** with `apply_modifiers=True`, consistent triangulation, per‑corner UVs and colors, per‑triangle materials, object/world transforms and world‑space bbox. Visibility and collection filters. Console emits \[SUMMARY].
2. **Materials v1** focused on PBR: extract Principled BSDF, auto map upstream textures, colorspaces, optional full node‑tree.
3. **Collections v1**: full hierarchy, flags from Collection + active View Layer's LayerCollection, non‑recursive membership per item.
4. **Scene View**: cameras and lights with transforms, FOV, clipping, DOF, Cycles panorama, shadows, extras by light type.
5. **Geometry Nodes v4** tolerance: unknown nodes marked `is_unknown=true`, safe RNA snapshot (`props`) and `inputs_defaults`; group fingerprint `sha1(nodes+links)`.
6. **Non‑destructive BoolOps**: export targets + BOOLEAN modifier lists; import can recreate modifiers or apply baked mesh from JSON.
7. **Aggregator**: writes combined `scene_export_[timestamp].json`; may keep or remove per‑parser files.
8. **Builders** tolerant to JSON shape variations, no crashes, concise \[SUMMARY].
9. **Single‑file add‑on**: embedded modules, directory preferences, granular operators, optional integration with KRS Bool Tool Lite without UI coupling.
10. **3.6↔4.2 compatibility**: defensive API lookups, fallbacks (e.g., GN interface sockets 3.6 vs 4.2).
11. **Error policy**: on failure ask for first 3–6 console lines + \[SUMMARY] counts; return minimal one‑function patches.
12. **Reporting**: all tools emit brief `[SUMMARY]` lines for automated testing.

## Reference implementations (files)

`parsers/`: `parser_mesh.py`, `parser_materials.py`, `parser_collections.py`, `parser_scene_view.py`, `parser_gn.py`, `parser_boolops.py`, `parser_scene.py` (aggregator).
`builders/`: `builder_mesh.py`, `builder_materials.py`, `builder_collections.py`, `builder_scene_view.py`, `builder_gn_overrides.py`, `builder_boolops.py`, `builder_scene_import.py`.

## Reproduction procedure

1. Use Blender 4.2 LTS (3.6 supported).
2. Install **AI\_TOOLS (single‑file)** add‑on. Enable it.
3. Set Preferences → AI\_TOOLS: **Export Dir** and **Import Dir**.
4. In Sidebar → AI\_TOOLS run **Export Scene JSON (ALL)**. Check `[SUMMARY]` and the combined file.
5. Optionally **Import Scene JSON (ALL)** into an empty scene. Toggle "Apply BoolOps on import" to recreate BOOLEAN modifiers.
6. Test order: Mesh → Scene View → Materials → Collections → GN → Aggregator → Builders.

## Known limitations

* Missing textures do not stop import; fallback materials are created.
* GN: links to ID data (objects/collections) are not set by `builder_gn_overrides` in v1; only scalar/vector/color inputs.
* Do not commit private data or files >50 MB.

## Ethics and privacy

* Public repo without passwords, tokens, or client data.
* Goal: verifiable technical memory, transparency, interoperability.
* `docs/credits.md` carries ethical positioning on AI; license remains under the author's name.

## Public roadmap

* v0.1: parsers + builders + add‑on, minimal JSON Schemas, 1–2 real sample JSONs.
* v0.2: broader GN overrides including ID links, CI schema validators.
* Optional: Zenodo release for DOI after stabilization.

## Suggested citation

“AI3DCNC open‑core defensive publication, v0.1, 2025‑08‑19, Apache‑2.0.” Link to GitHub repo.

## Changelog

* 2025‑08‑19 • v0.1 • Initial publication.
