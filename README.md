# AI3DCNC – Public Knowledge Repo

This repository contains **parsers, builders, and documentation** for the AI3DCNC project.

## Goals
- Open-core knowledge base for CNC automation in Blender 4.2 LTS
- Defensive publication → protects ideas from being patented by others
- Learning resource for step-by-step, verifiable automation scripts

## Structure
- `parsers/` → Blender data exporters (mesh, scene, materials, etc.)
- `builders/` → Re-importers / reconstructors
- `docs/` → Standards, roadmap, notes
- `samples/` → Example JSON exports

## License
Apache-2.0 License – free to use, modify, and distribute with proper attribution.

## Acknowledgments
Developed by **Balaur Ionuț Doru / AI3DCNC**, with assistance from **ChatGPT (OpenAI)**.


## Docs
- [Defensive Publication](docs/defensive-publication.md)

Generated artifacts: parsers_all.py, builders_all.py (run: python tools/gen_all.py). Do not edit.
 vb How to regenerate:
python tools/gen_all.py

[![Release](https://img.shields.io/github/v/release/ai3dcnc/ai3dcnc-public?sort=semver)](https://github.com/ai3dcnc/ai3dcnc-public/releases)


## Context and Inspiration
For details about the relationship between KEROS and NodeKit, see [BACKGROUND.md](./BACKGROUND.md).

.