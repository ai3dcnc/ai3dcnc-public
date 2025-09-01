# AI3DCNC – Public Knowledge Repo

<!-- DOI pentru versiunea curentă -->
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.17025381.svg)](https://doi.org/10.5281/zenodo.17025381)

<!-- DOI “concept” – recomandat pentru citare pe termen lung -->
[![DOI](https://zenodo.org/badge/DOI/<CONCEPT_DOI>.svg)](https://doi.org/<CONCEPT_DOI>)


[![E2E](https://github.com/ai3dcnc/ai3dcnc-public/actions/workflows/e2e.yml/badge.svg)](https://github.com/ai3dcnc/ai3dcnc-public/actions/workflows/e2e.yml)
[![Release](https://img.shields.io/github/v/release/ai3dcnc/ai3dcnc-public?sort=semver)](https://github.com/ai3dcnc/ai3dcnc-public/releases)

Repo cu **parsers, builders și documentație** pentru AI3DCNC.

> **Units:** authoring în metri, export **mm**.

## Quickstart

```powershell
python tools/ops_tools.py validate samples/ops_min.json schemas/ops_json.schema.json
python tools/ops_tools.py to-tcn samples/ops_min.json profiles/Vitap_K2.profile.json exports/ops_min.tcn
python tools/ops_tools.py to-csv samples/ops_min.json exports/ops_min.csv
```

Artefacte locale: `exports/ops_min.tcn`, `exports/ops_min.csv`.

## Goals

* Open-core knowledge base pentru automatizări CNC în Blender 4.2 LTS
* Defensive publication
* Resurse de învățare cu pași verificabili

## Structure

* `parsers/` – exportori Blender (mesh, scene, materials)
* `builders/` – reimport / reconstrucție
* `docs/` – standarde, roadmap, note
* `samples/` – exemple JSON
* `schemas/` – JSON Schemas pentru validare
* `profiles/` – profile mașini
* `tools/` – utilitare CLI (TCN/CSV, E2E, mem)
* `corpus/` – mostre TCN/DXF pentru testare

## CI

* Workflow: **E2E** pe Windows. Rulează `tools/test_e2e.ps1` și urcă artefactele `exports`.
* Status: vezi badge-ul de mai sus și fila **Actions**.

## Docs

* [Defensive Publication](docs/defensive-publication.md)
* [Memory Sets proposal](docs/MEMORY_SETS.md)
* [BACKGROUND.md](./BACKGROUND.md)

## License

Apache-2.0 – liber de folosit și modificat cu atribuție.

## Acknowledgments

Dezvoltat de **Balaur Ionuț Doru / AI3DCNC**, cu asistență **ChatGPT (OpenAI)**.

# AI3DCNC – Public Knowledge Repo

[![E2E](https://github.com/ai3dcnc/ai3dcnc-public/actions/workflows/e2e.yml/badge.svg)](https://github.com/ai3dcnc/ai3dcnc-public/actions/workflows/e2e.yml)
[![Release](https://img.shields.io/github/v/release/ai3dcnc/ai3dcnc-public?sort=semver)](https://github.com/ai3dcnc/ai3dcnc-public/releases)

Repo cu **parsers, builders și documentație** pentru AI3DCNC.

> **Units:** authoring în metri, export **mm**.

## Quickstart

```powershell
python tools/ops_tools.py validate samples/ops_min.json schemas/ops_json.schema.json
python tools/ops_tools.py to-tcn samples/ops_min.json profiles/Vitap_K2.profile.json exports/ops_min.tcn
python tools/ops_tools.py to-csv samples/ops_min.json exports/ops_min.csv
```

Artefacte locale: `exports/ops_min.tcn`, `exports/ops_min.csv`.

## Goals

* Open-core knowledge base pentru automatizări CNC în Blender 4.2 LTS
* Defensive publication
* Resurse de învățare cu pași verificabili

## Structure

* `parsers/` – exportori Blender (mesh, scene, materials)
* `builders/` – reimport / reconstrucție
* `docs/` – standarde, roadmap, note
* `samples/` – exemple JSON
* `schemas/` – JSON Schemas pentru validare
* `profiles/` – profile mașini
* `tools/` – utilitare CLI (TCN/CSV, E2E, mem)
* `corpus/` – mostre TCN/DXF pentru testare

## CI

* Workflow: **E2E** pe Windows. Rulează `tools/test_e2e.ps1` și urcă artefactele `exports`.
* Status: vezi badge-ul de mai sus și fila **Actions**.

## Docs

* [Defensive Publication](docs/defensive-publication.md)
* [Memory Sets proposal](docs/MEMORY_SETS.md)
* [BACKGROUND.md](./BACKGROUND.md)

## License

Apache-2.0 – liber de folosit și modificat cu atribuție.

## Acknowledgments

Dezvoltat de **Balaur Ionuț Doru / AI3DCNC**, cu asistență **ChatGPT (OpenAI)**.
