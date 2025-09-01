# README.md

[![E2E](https://github.com/ai3dcnc/ai3dcnc-public/actions/workflows/e2e.yml/badge.svg)](https://github.com/ai3dcnc/ai3dcnc-public/actions/workflows/e2e.yml)
[![Release](https://img.shields.io/github/v/release/ai3dcnc/ai3dcnc-public?sort=semver)](https://github.com/ai3dcnc/ai3dcnc-public/releases)
[![DOI (this version)](https://zenodo.org/badge/DOI/10.5281/zenodo.17025381.svg)](https://doi.org/10.5281/zenodo.17025381)
[![DOI (concept)](https://zenodo.org/badge/DOI/<CONCEPT_DOI>.svg)](https://doi.org/<CONCEPT_DOI>)

Repo cu **parsers, builders și documentație** pentru AI3DCNC (automatizări CNC, Vitap K2 / TpaCAD, export TCN/CSV).

> **Units:** authoring în **metri**, export în **mm**.

---

## Quickstart

```powershell
# Validare JSON vs. schemă
python tools/ops_tools.py validate samples/ops_min.json schemas/ops_json.schema.json

# Export TCN minim
python tools/ops_tools.py to-tcn samples/ops_min.json profiles/Vitap_K2.profile.json exports/ops_min.tcn

# Export CSV canonic
python tools/ops_tools.py to-csv samples/ops_min.json exports/ops_min.csv
```

Artefacte locale: `exports/ops_min.tcn`, `exports/ops_min.csv`.

---

## Structure

* `parsers/` – exportori Blender (mesh, scene, materials)
* `builders/` – reimport / reconstrucție
* `docs/` – standarde, roadmap, note
* `samples/` – exemple JSON (DRILL/SLOT/SAW etc.)
* `schemas/` – JSON Schemas pentru validare
* `profiles/` – profile mașini (ex. **Vitap\_K2.profile.json**)
* `tools/` – utilitare CLI (TCN/CSV/TPA, E2E)
* `corpus/` – mostre TCN/DXF pentru testare

---

## CLI – tools/ops\_tools.py

* `validate <ops.json> <schema.json>` – validează un document de operații
* `to-tcn <ops.json> <profile.json> <out.tcn>` – generează TCN simplu (DRILL/SLOT/SAW)
* `to-tpa <ops.json> <profile.json> <out.tcn>` – generează dialect **Vitap TpaCAD** (UTF‑16LE + BOM)
* `to-csv <ops.json> <out.csv>` – export canonic CSV
* `from-tcn <in.tcn> <board.json> <out.ops.json>` – parse TCN → JSON canonic

> Pentru TpaCAD: header `TPA\ALBATROS\EDICAD\02.00:1565:r0w0h0s1`, `::SIDE=0;1;3;4;5;6;`, CRLF, **UTF‑16LE + BOM**.

---

## CI

* Workflow **E2E** (Windows) – rulează `tools/test_e2e.ps1` și urcă artefactele din `exports/`.

---

## Cite

* **DOI (versiunea curentă):** `10.5281/zenodo.17025381`
* **DOI (concept – recomandat pentru citare pe termen lung):** `<CONCEPT_DOI>`

BibTeX:

```bibtex
@software{ai3dcnc_public,
  author  = {Balaur, Ionuț Doru},
  title   = {AI3DCNC – Public Knowledge Repo},
  year    = {2025},
  version = {v0.1.0},
  doi     = {10.5281/zenodo.17025381}
}
```

## License

Apache-2.0 – liber de folosit și modificat cu atribuție.

---


