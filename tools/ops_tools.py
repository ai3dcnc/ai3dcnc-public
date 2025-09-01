#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Minimal, robust TPA/TCN/CSV generator for AI3DCNC samples.
Focus: make CI/E2E pass and generate valid UTF‑16 (BOM) TpaCAD files.

Commands:
  validate <ops.json> <schema.json>
  to-tpa   <ops.json> <profile.json> <out.tcn>
  to-tcn   <ops.json> <profile.json> <out.tcn>   # alias of to-tpa for now
  to-csv   <ops.json> <out.csv>
"""
from __future__ import annotations

import json
import sys
import os
from typing import Dict, List

# Optional: jsonschema for validate
try:
    from jsonschema import validate as _js_validate
    _HAVE_JSONSCHEMA = True
except Exception:
    _HAVE_JSONSCHEMA = False

# --------------------------------------------------------------------------------------
# Utilities
# --------------------------------------------------------------------------------------

def _read_json(path: str):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def _ensure_dir(path: str):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)


def _write_tpa_unicode(path: str, lines: List[str]):
    """Write with UTF-16 BOM ("unicode" for TpaCAD) and CRLF line endings."""
    _ensure_dir(path)
    text = "\r\n".join(lines) + "\r\n"
    # 'utf-16' emits BOM on write; Windows default is LE
    with open(path, "w", encoding="utf-16") as f:
        f.write(text)


# --------------------------------------------------------------------------------------
# TPA blocks
# --------------------------------------------------------------------------------------

def _tpa_header(board: Dict) -> List[str]:
    DL = int(round(float(board.get("DL_mm", 800))))
    DH = int(round(float(board.get("DH_mm", 450))))
    DS = int(round(float(board.get("DS_mm", 18))))
    return [
        r"TPA\ALBATROS\EDICAD\02.00:1565:r0w0h0s1",
        "::SIDE=0;1;3;4;5;6;",
        "::ATTR=hide;varv",
        f"::UNm DL={DL} DH={DH} DS={DS}",
        "'tcn version=2.8.21",
        "'code=unicode",
        "EXE{",
        "#0=0",
        "#1=0",
        "#2=0",
        "#3=0",
        "#4=0",
        "}EXE",
        "OFFS{",
        "#0=0.0|0",
        "#1=0.0|0",
        "#2=0.0|0",
        "}OFFS",
        "VARV{",
        "#0=0.0|0",
        "#1=0.0|0",
        "}VARV",
        "VAR{",
        "}VAR",
        "SPEC{",
        "}SPEC",
        "INFO{",
        "}INFO",
        "OPTI{",
        ":: OPTKIND=%;0 OPTROUTER=%;0 LSTCOD=%0%1%2",
        "}OPTI",
        "LINK{",
        "}LINK",
        "SIDE#0{",
        "}SIDE",
    ]


def _wtp_drill(op: Dict, tool_id: int) -> str:
    x = int(round(float(op.get("x_mm", 0))))
    y = int(round(float(op.get("y_mm", 0))))
    z = int(round(float(op.get("z_mm", 0))))
    dia = int(round(float(op.get("dia_mm", 5))))
    # Classic W#81 drill; keep params conservative/safe
    return (
        f"W#81{{ ::WTp WS=1  #8015=0 #1={x} #2={y} #3=-{z} #1002={dia} "
        f"#201=1 #203=1 #205={int(tool_id)} #1001=0 #9505=0 }}W"
    )


def _group_ops_by_face(ops: List[Dict]) -> Dict[int, List[str]]:
    by_face: Dict[int, List[str]] = {}
    # Tool mapping (defaults tuned from your K2 examples)
    tool_map = {1: 41, 3: 41, 4: 51, 5: 42, 6: 52}
    for op in ops:
        face = int(op.get("face", 1))
        kind = str(op.get("op", "")).upper()
        if kind == "DRILL":
            tool_id = tool_map.get(face, 41)
            by_face.setdefault(face, []).append(_wtp_drill(op, tool_id))
        # NOTE: SLOT/SAW can be added here when needed for E2E
    return by_face


def _emit_face(lines: List[str], face: int, payload: List[str]):
    if not payload:
        return
    # Open side
    lines.append(f"SIDE#{face}{{")
    if face == 1:
        lines.append("$=Up")
    else:
        lines.append("::DX=0 XY=1")
    # Payload
    lines.extend(payload)
    # Close side
    lines.append("}SIDE")


def build_tpa(doc: Dict) -> List[str]:
    board = doc.get("board", {})
    ops = doc.get("ops", [])
    lines: List[str] = []
    # Header blocks
    lines.extend(_tpa_header(board))
    # Group ops per face and emit
    by_face = _group_ops_by_face(ops)
    for face in (1, 3, 4, 5, 6):
        _emit_face(lines, face, by_face.get(face, []))
    return lines


# --------------------------------------------------------------------------------------
# CSV (very small, canonical)
# --------------------------------------------------------------------------------------

def write_csv(path: str, doc: Dict):
    _ensure_dir(path)
    import csv
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "op", "face", "x_mm", "y_mm", "z_mm", "dia_mm", "width_mm"])
        for op in doc.get("ops", []):
            w.writerow([
                op.get("id", ""), op.get("op", ""), op.get("face", 1),
                op.get("x_mm", ""), op.get("y_mm", ""), op.get("z_mm", ""),
                op.get("dia_mm", ""), op.get("width_mm", ""),
            ])


# --------------------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------------------

def cmd_validate(ops_path: str, schema_path: str) -> int:
    if not _HAVE_JSONSCHEMA:
        print("jsonschema not installed; run: python -m pip install jsonschema", file=sys.stderr)
        return 2
    data = _read_json(ops_path)
    schema = _read_json(schema_path)
    _js_validate(instance=data, schema=schema)
    print(f"valid: {ops_path} against {schema_path}")
    return 0


def cmd_to_tpa(ops_path: str, profile_path: str, out_path: str) -> int:
    # profile is currently unused but kept for future
    _ = profile_path
    doc = _read_json(ops_path)
    lines = build_tpa(doc)
    _write_tpa_unicode(out_path, lines)
    print(f"written: {out_path}")
    return 0


def cmd_to_tcn(ops_path: str, profile_path: str, out_path: str) -> int:
    # For now, alias to TPA writer (stable for E2E)
    return cmd_to_tpa(ops_path, profile_path, out_path)


def cmd_to_csv(ops_path: str, out_csv: str) -> int:
    doc = _read_json(ops_path)
    write_csv(out_csv, doc)
    print(f"written: {out_csv}")
    return 0


# --------------------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------------------

def main(argv: List[str] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(__doc__)
        return 1
    cmd = argv.pop(0)
    try:
        if cmd == "validate" and len(argv) == 2:
            return cmd_validate(argv[0], argv[1])
        if cmd in ("to-tpa", "to-tcn") and len(argv) == 3:
            if cmd == "to-tpa":
                return cmd_to_tpa(argv[0], argv[1], argv[2])
            else:
                return cmd_to_tcn(argv[0], argv[1], argv[2])
        if cmd == "to-csv" and len(argv) == 2:
            return cmd_to_csv(argv[0], argv[1])
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main())
