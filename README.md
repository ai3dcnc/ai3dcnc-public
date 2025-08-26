# AI3DCNC – Public Knowledge Repo

[![E2E](https://github.com/ai3dcnc/ai3dcnc-public/actions/workflows/e2e.yml/badge.svg)](https://github.com/ai3dcnc/ai3dcnc-public/actions/workflows/e2e.yml)
[![Release](https://img.shields.io/github/v/release/ai3dcnc/ai3dcnc-public?sort=semver)](https://github.com/ai3dcnc/ai3dcnc-public/releases)

This repository contains **parsers, builders, and documentation** for the AI3DCNC project.

> **Units:** authoring în metri, export **mm**.

## Quickstart

```powershell
python tools/ops_tools.py validate samples/ops_min.json schemas/ops_json.schema.json
python tools/ops_tools.py to-tcn samples/ops_min.json profiles/Vitap_K2.profile.json exports/ops_min.tcn
python tools/ops_tools.py to-csv samples/ops_min.json exports/ops_min.csv
```

Artefacte: `exports/ops_min.tcn`, `exports/ops_min.csv`.

## Goals

* Open-core knowledge base for CNC automation in Blender 4.2 LTS
* Defensive publication → protects ideas from being patented by others
* Learning resource for step-by-step, verifiable automation scripts

## Structure

* `parsers/` → Blender data exporters (mesh, scene, materials, etc.)
* `builders/` → Re-importers / reconstructors
* `docs/` → Standards, roadmap, notes
* `samples/` → Example JSON exports
* `schemas/` → JSON Schemas pentru validare
* `profiles/` → Machine profiles
* `tools/` → CLI utilitare (TCN/CSV, E2E)

## License

Apache-2.0 License – free to use, modify, and distribute with proper attribution.

## Acknowledgments

Developed by **Balaur Ionuț Doru / AI3DCNC**, with assistance from **ChatGPT (OpenAI)**.

## Docs

* [Defensive Publication](docs/defensive-publication.md)

## Context and Inspiration

For details about the relationship between KEROS and NodeKit, see [BACKGROUND.md](./BACKGROUND.md).
