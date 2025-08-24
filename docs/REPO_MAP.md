mkdir -p docs
cat > docs/REPO_MAP.md << 'EOF'
# REPO_MAP

## Structure
- addons/                 — AI_TOOLS_Lite.py (public UI)
- builders/               — import pipeline per section (materials, mesh, collections, scene_view, GN, boolops)
- parsers/                — export pipeline per section
- docs/                   — public docs (README_Lite, ROADMAP_KNOWLEDGE, credits, defensive-publication)
- schemas/                — JSON Schemas (mesh_v1; TPA planned, mm)
- samples/                — minimal examples (min_scene_export.json)
- tools/                  — helper scripts (non-core)
- manifest.json           — loader manifest (raw_base, entrypoints, aliases)
- parsers_all.py          — bundle exporter (lives also in GPT)
- builders_all.py         — bundle importer (lives also in GPT)

## Conventions
- Units: design in meters (3 decimals), CAM export in millimeters.
- Entry points (manifest): parsers_all.py, builders_all.py, docs/ROADMAP_KNOWLEDGE.json.
- Source of truth: INTRODUCTION (kept in GPT).
EOF
git add docs/REPO_MAP.md
git commit -m "add docs/REPO_MAP.md"
git push
