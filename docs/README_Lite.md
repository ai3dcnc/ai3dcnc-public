# AI\_TOOLS Lite (Blender 4.2)

Minimal add‑on for quick I/O checks in **meters (3 decimals)** and a **QA DXF stub**. Designed as a public‑lite companion for the private core exporters/importers.

> RO scurt: Addonul scrie `min_scene_export.json`, parsează la import (fără a crea obiecte) și generează un DXF de verificare. Pentru import real folosește **AI\_TOOLS (single‑file)**.

---

## What it does

* **Export min JSON**: writes `min_scene_export.json` with a tiny, valid schema sample.
* **Import JSON (noop)**: parses a JSON file to confirm shape. **Does not build objects**.
* **Write QA DXF (stub)**: generates `qa_panel.dxf` with minimal geometry for visual checks (meters, 3dp).
* **Open dirs**: quick buttons for Export/Import folders.

## Requirements

* Blender **4.2** (works on 3.6 for basics).
* Windows/macOS/Linux.

## Installation

1. Download `addons/AI_TOOLS_Lite.py`.
2. Blender → **Edit > Preferences > Add-ons > Install…** → pick the file.
3. Enable **AI\_TOOLS Lite**.
4. Open panel: 3D View → press **N** → tab **AI\_TOOLS Lite**.

## Default paths

* **Export Dir** (default): `~/BLENDER_EXPORT` (e.g., `C:\Users\<user>\BLENDER_EXPORT`).
* **Import Dir** (default): same.

You can change both in the panel. Use **Open Export Dir** / **Open Import Dir** to verify.

## Usage

1. In the **AI\_TOOLS Lite** panel set **Export Dir** and **Import Dir**.
2. Click **Export min\_scene\_export.json**.

   * Console prints: `[SUMMARY] min_scene_export -> <full path>`.
3. Click **Write QA DXF (stub)**.

   * Console prints: `[SUMMARY] dxf_stub -> <full path>`.
4. (Optional) Click **Import JSON (noop lite)** and pick the JSON.

   * Console prints: `[SUMMARY] (lite) parsed JSON OK: <file>`.

## Units policy

* All values are **meters** with **3 decimals**.
* QC thresholds used by the ecosystem: `edge ≥ 0.003 m`, `hole‑to‑hole ≥ 0.016 m`.

## Scope and limits

* Lite add‑on is for I/O smoke tests and DXF preview only.
* **Does not** create Blender objects at import time.
* For real export/import use the core add‑on: **AI\_TOOLS (single‑file)**.

## Troubleshooting

* "Repository data … sync required" during startup: harmless when installing from file; the add‑on still works.
* If nothing appears in the export folder, press **Export min\_scene\_export.json** and then **Open Export Dir** to locate the path actually used.
* Send the first 3–6 console lines and all `[SUMMARY]` lines when reporting issues.

## Files in this folder

* `AI_TOOLS_Lite.py` – this add‑on.

## Example repo layout

```
/addons/AI_TOOLS_Lite.py
/docs/README_Lite.md  ← this file
/samples/min_scene_export.json
```

## Changelog

* 0.2.2 – Public‑lite release. Panel, min JSON export, noop import, DXF stub, open dirs.

## License

* License: add your project license here (MIT recommended for the Lite add‑on).

## Acknowledgements

* Built as part of the AI3DCNC public‑lite toolchain.
