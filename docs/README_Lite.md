# AI\_TOOLS Lite (Blender 4.2)

Minimal add‑on for **quick I/O checks** in **meters (3 decimals)** and a **QA DXF stub**. Public‑lite companion for the private core exporters/importers.

> RO scurt: Addonul scrie `min_scene_export.json`, parsează la import (fără a crea obiecte) și generează un DXF de verificare. Pentru import real folosește **AI\_TOOLS (single‑file)**.

---

## Features

* **Export min JSON** → writes `min_scene_export.json` (valid schema sample).
* **Import JSON (noop)** → parses JSON, confirms shape. **Does not build objects**.
* **QA DXF (stub)** → writes `qa_panel.dxf` for a quick visual check (meters, 3dp).
* **Open dirs** → buttons to open Export/Import folders.

## Why “Lite” vs Core

* Lite = smoke tests + DXF preview.
* Core (**AI\_TOOLS single‑file**) = real export/import for mesh, scene view, materials, collections, GN, bool ops.

## Requirements

* Blender **4.2** (basic functions also work on 3.6).
* Windows/macOS/Linux.

## Installation

1. Download `addons/AI_TOOLS_Lite.py` from this repo.
2. Blender → **Edit > Preferences > Add‑ons > Install…** → pick the file.
3. Enable **AI\_TOOLS Lite**.
4. Open panel: 3D View → press **N** → tab **AI\_TOOLS Lite**.

## Default paths

* **Export Dir**: `~/BLENDER_EXPORT` (e.g., `C:/Users/<user>/BLENDER_EXPORT`).
* **Import Dir**: same. Change them in the panel. Use **Open Export/Import Dir** to verify.

## Usage

1. In the **AI\_TOOLS Lite** panel set **Export Dir** and **Import Dir**.
2. Click **Export min\_scene\_export.json** → console: `[SUMMARY] min_scene_export -> <full path>`.
3. Click **Write QA DXF (stub)** → console: `[SUMMARY] dxf_stub -> <full path>`.
4. (Optional) **Import JSON (noop lite)** and pick the file → console: `[SUMMARY] (lite) parsed JSON OK: <file>`.

## Outputs

* `min_scene_export.json` — minimal valid sample of the scene export shape.
* `qa_panel.dxf` — lightweight DXF for eyeballing geometry; meters with 3 decimals.

## Units policy

* All values are **meters** with **3 decimals**.
* Ecosystem QC thresholds: `edge ≥ 0.003 m`, `hole‑to‑hole ≥ 0.016 m`.

## Scope and limits

* No object creation on import (noop check only).
* Use **AI\_TOOLS (single‑file)** for real export/import.

## Troubleshooting

* *“Repository data … sync required”* on startup is harmless when installing from file.
* If nothing appears in the export folder, press **Export min\_scene\_export.json** then **Open Export Dir** to see the actual path.
* When reporting issues, include the first 3–6 console lines and all `[SUMMARY]` lines.

## Files in this folder

* `AI_TOOLS_Lite.py` — this add‑on.

## Example repo layout

```
/addons/AI_TOOLS_Lite.py
/docs/README_Lite.md  ← this file
/samples/min_scene_export.json
/samples/sample_min_scene.json
```

## Samples

* [min\_scene\_export.json](../samples/min_scene_export.json)
* [sample\_min\_scene.json](../samples/sample_min_scene.json)

## Changelog

* **0.2.2** — Public‑lite release. Panel, min JSON export, noop import, DXF stub, open dirs.

## License

* Add your project license here. **MIT** recommended for the Lite add‑on.

## Acknowledgements

* Part of the AI3DCNC public‑lite toolchain.
