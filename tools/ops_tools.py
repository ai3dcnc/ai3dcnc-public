#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ops_tools.py – utilitare CLI pentru AI3DCNC

Comenzi:
  validate <ops.json> <schema.json>
  to-tpa   <ops.json> <profile.json> <out.tcn>
  to-tcn   <ops.json> <profile.json> <out.tcn>
  to-csv   <ops.json> <out.csv>

Note:
- Evită raw-strings pentru căile Windows. Folosește backslash dublu.
- La scrierea TPA/TCN folosește CRLF și, pentru TpaCAD, UTF-16LE + BOM.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from typing import Dict, List, Any

# -------------------------------------------------------------
# Utilitare I/O
# -------------------------------------------------------------

def _read_json(path: str) -> Any:
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except FileNotFoundError as e:
        raise FileNotFoundError(f"missing file: {path} (cwd={os.getcwd()})") from e


def _ensure_dir(p: str) -> None:
    d = os.path.dirname(os.path.abspath(p))
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)


def _write_text(path: str, lines: List[str], *, encoding: str = "utf-16-le", add_bom: bool = True) -> None:
    """Scrie fișier text cu CRLF. Implicit UTF‑16LE + BOM (compatibil TpaCAD)."""
    _ensure_dir(path)
    data = ("\r\n".join(lines) + "\r\n").encode(encoding)
    if add_bom and encoding.lower().replace("_", "-") in ("utf-16", "utf-16-le"):
        # BOM pentru UTF-16LE
        data = b"\xff\xfe" + data
    with open(path, "wb") as f:
        f.write(data)


# -------------------------------------------------------------
# Validare JSON Schema (opțional – jsonschema)
# -------------------------------------------------------------

def cmd_validate(ops_path: str, schema_path: str) -> int:
    doc = _read_json(ops_path)
    schema = _read_json(schema_path)
    try:
        from jsonschema import validate  # type: ignore
        validate(instance=doc, schema=schema)
    except ModuleNotFoundError:
        print("jsonschema nu este instalat – omitem validarea formală.")
        return 0
    except Exception as e:  # pragma: no cover
        print(e)
        return 1
    print(f"valid: {ops_path} against {schema_path}")
    return 0


# -------------------------------------------------------------
# Generator TPA/TCN
# -------------------------------------------------------------

def _fmt_mm(v: Any) -> str:
    try:
        x = float(v)
    except Exception:
        return str(v)
    if abs(x - round(x)) < 1e-9:
        return str(int(round(x)))
    return ("%.3f" % x).rstrip("0").rstrip(".")


def _header_tpa(board: Dict[str, Any]) -> List[str]:
    DL = _fmt_mm(board.get("DL_mm", 800))
    DH = _fmt_mm(board.get("DH_mm", 450))
    DS = _fmt_mm(board.get("DS_mm", 18))
    return [
        "TPA\\ALBATROS\\EDICAD\\02.00:1565:r0w0h0s1",
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
    ]


# Maparea burghielor pe fețe (convențiile tale)
_FACE_TOOL: Dict[int, int] = {
    1: 1,    # generic pentru face 1
    3: 41,
    4: 51,
    5: 42,
    6: 52,
}


def _w81_drill(x: float, y: float, z: float, dia: float, face: int) -> str:
    tool_id = _FACE_TOOL.get(face, 1)
    return (
        "W#81{ ::WTp WS=1  #8015=0 "
        f"#1={_fmt_mm(x)} #2={_fmt_mm(y)} #3=-{_fmt_mm(z)} "
        f"#1002={_fmt_mm(dia)} #201=1 #203=1 #205={tool_id} #1001=0 #9505=0 }}W"
    )


def _tpa_saw_W1050(op: Dict[str, Any], saw_tool_id: int, start_x_mm: float = 50.0, start_y_mm: float = 50.0) -> List[str]:
    """Macro ferăstrău – fără raw strings, backslash dublu pentru cale."""
    axis = str(op.get("axis", "X")).upper()
    z = _fmt_mm(op.get("z_mm", 10))
    off = float(op.get("offset_mm", 0))
    L = float(op.get("length_mm", 100))

    if axis == "X":
        x0 = _fmt_mm(start_x_mm)
        x1 = _fmt_mm(start_x_mm + L)
        y = _fmt_mm(off)
        return [
            ("W#1050{"  # saw along X
             " ::WT2 WS=1  #8098=..\\custom\\mcr\\lame.tmcr #6=1 "
             f"#8020={x0} #8021={y} #8022=-{z} #9505=0 #8503=0 #8509=0 "
             f"#8514=1 #8515=1 #8516={int(saw_tool_id)} #8517={x1} #8525=0 #8526=0 #8527=0 }}W")
        ]
    else:
        y0 = _fmt_mm(start_y_mm)
        y1 = _fmt_mm(start_y_mm + L)
        x = _fmt_mm(off)
        return [
            ("W#1050{"  # saw along Y
             " ::WT2 WS=1  #8098=..\\custom\\mcr\\lame.tmcr #6=2 "
             f"#8020={x} #8021={y0} #8022=-{z} #9505=0 #8503=0 #8509=0 "
             f"#8514=1 #8515=1 #8516={int(saw_tool_id)} #8517={y1} #8525=0 #8526=0 #8527=0 }}W")
        ]


# -------------------------------------------------------------
# Emitere TPA pe fețe
# -------------------------------------------------------------

def _emit_face(face: int, payload: List[str], out: List[str]) -> None:
    if not payload:
        # Emit totuși placeholderul de SIDE, conform TPA
        if face == 1:
            out.append("SIDE#1{")
            out.append("$=Up")
            out.append("}SIDE")
        else:
            out.append(f"SIDE#{face}{")
            out.append("::DX=0 XY=1")
            out.append("}SIDE")
        return

    if face == 1:
        out.append("SIDE#1{")
        out.append("$=Up")
    else:
        out.append(f"SIDE#{face}{")
        out.append("::DX=0 XY=1")

    out.extend(payload)
    out.append("}SIDE")


# -------------------------------------------------------------
# Construire document TPA
# -------------------------------------------------------------

def build_tpa(doc: Dict[str, Any]) -> List[str]:
    board = doc.get("board", {})
    ops = doc.get("ops", [])

    lines: List[str] = []
    lines.extend(_header_tpa(board))

    # grupăm operațiile pe fețe
    by_face: Dict[int, List[str]] = {}
    for op in ops:
        face = int(op.get("face", 1))
        kind = str(op.get("op", "")).upper()

        if kind == "DRILL":
            x = float(op["x_mm"]); y = float(op["y_mm"]); z = float(op.get("z_mm", 10)); dia = float(op.get("dia_mm", 5))
            by_face.setdefault(face, []).append(_w81_drill(x, y, z, dia, face))
        elif kind == "SAW":
            # exemplu simplu – un singur W#1050
            saw_tool = 2001
            by_face.setdefault(face, []).extend(_tpa_saw_W1050(op, saw_tool))
        elif kind == "SLOT":
            # fallback: traduce slot într-o pereche de găuri capete (opțional)
            x1 = float(op.get("x1_mm", 100)); x2 = float(op.get("x2_mm", 200))
            y1 = float(op.get("y1_mm", 50));  y2 = float(op.get("y2_mm", 50))
            z = float(op.get("z_mm", 10)); dia = float(op.get("width_mm", 6))
            by_face.setdefault(face, []).append(_w81_drill(x1, y1, z, dia, face))
            by_face[face].append(_w81_drill(x2, y2, z, dia, face))
        else:
            # necunoscut – ignorăm
            continue

    # Emit fețele în ordinea standard
    for f in (0, 1, 3, 4, 5, 6):
        if f == 0:
            lines.append("SIDE#0{")
            lines.append("}SIDE")
            continue
        _emit_face(f, by_face.get(f, []), lines)

    return lines


# -------------------------------------------------------------
# Comenzi de generare
# -------------------------------------------------------------

def cmd_to_tpa(ops_path: str, profile_path: str, out_path: str) -> int:
    doc = _read_json(ops_path)
    # profile-ul poate fi folosit în viitor; îl citim pentru consistență
    _ = _read_json(profile_path)

    lines = build_tpa(doc)
    _write_text(out_path, lines, encoding="utf-16-le", add_bom=True)
    print(f"written: {out_path}")
    return 0


def cmd_to_tcn(ops_path: str, profile_path: str, out_path: str) -> int:
    # Pentru simplitate folosim același generator – multe postprocesoare TPA citesc aceste fișiere.
    return cmd_to_tpa(ops_path, profile_path, out_path)


def cmd_to_csv(ops_path: str, out_path: str) -> int:
    doc = _read_json(ops_path)
    ops = doc.get("ops", [])
    _ensure_dir(out_path)
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "op", "face", "x_mm", "y_mm", "z_mm", "dia_mm", "width_mm"])  # cap de tabel canonic
        for op in ops:
            w.writerow([
                op.get("id", ""), op.get("op", ""), op.get("face", ""),
                op.get("x_mm", ""), op.get("y_mm", ""), op.get("z_mm", ""),
                op.get("dia_mm", ""), op.get("width_mm", ""),
            ])
    print(f"written: {out_path}")
    return 0


# -------------------------------------------------------------
# CLI
# -------------------------------------------------------------

def main(argv: List[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="ops_tools.py", description="AI3DCNC ops tools")
    sub = p.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("validate", help="validate <ops.json> <schema.json>")
    v.add_argument("ops_json")
    v.add_argument("schema_json")

    tpa = sub.add_parser("to-tpa", help="to-tpa <ops.json> <profile.json> <out.tcn>")
    tpa.add_argument("ops_json")
    tpa.add_argument("profile_json")
    tpa.add_argument("out_tcn")

    tcn = sub.add_parser("to-tcn", help="to-tcn <ops.json> <profile.json> <out.tcn>")
    tcn.add_argument("ops_json")
    tcn.add_argument("profile_json")
    tcn.add_argument("out_tcn")

    csvp = sub.add_parser("to-csv", help="to-csv <ops.json> <out.csv>")
    csvp.add_argument("ops_json")
    csvp.add_argument("out_csv")

    args = p.parse_args(argv)

    if args.cmd == "validate":
        return cmd_validate(args.ops_json, args.schema_json)
    if args.cmd == "to-tpa":
        return cmd_to_tpa(args.ops_json, args.profile_json, args.out_tcn)
    if args.cmd == "to-tcn":
        return cmd_to_tcn(args.ops_json, args.profile_json, args.out_tcn)
    if args.cmd == "to-csv":
        return cmd_to_csv(args.ops_json, args.out_csv)

    p.print_help()
    return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
