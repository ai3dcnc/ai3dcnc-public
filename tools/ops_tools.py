# -*- coding: utf-8 -*-
"""
ops_tools.py – utilitare pentru validare și export (TCN/TPA/CSV)

✅ Adăugat: SLOT, SAW și găuri în cant (fețele 3,4,5,6 – Vitap K2)

Comenzi:
  validate <ops.json> <schema.json>
  to-tpa   <ops.json> <machine.profile.json> <out.tcn>
  to-tcn   <ops.json> <machine.profile.json> <out.tcn>
  to-csv   <ops.json> <out.csv>

Nota: generatorul TPA scrie UTF-16 LE + BOM și CRLF.
"""
from __future__ import annotations

import json
import csv
import os
import sys
from typing import Any, Dict, List, Tuple

try:
    from jsonschema import validate  # type: ignore
except Exception:  # pragma: no cover
    validate = None  # lăsăm validate să eșueze frumos dacă nu e instalat

# ------------------------------
# Utilitare
# ------------------------------

def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _read_json(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except FileNotFoundError as e:  # mesaje clare în CLI
        raise FileNotFoundError(f"missing file: {path} (cwd={os.getcwd()})") from e


def _writelines_tpa(path: str, lines: List[str]) -> None:
    # TpaCAD iubește UTF-16 LE + BOM și CRLF
    with open(path, "w", encoding="utf-16-le", newline="\r\n") as f:
        f.write("\ufeff")  # BOM
        for ln in lines:
            if not ln.endswith("\r\n"):
                ln = ln + "\r\n"
            f.write(ln)


# ------------------------------
# Mapări tool-uri (Vitap K2)
# ------------------------------

# DRILL – tool id per față (F1 liber, F3..F6 dedicate)
_DRILL_FACE_TOOL = {
    1: {"5": 1, "6": 1, "8": 1, "10": 1},  # Top: T1 (generic)
    3: {"5": 41, "6": 41, "8": 41, "10": 41},
    4: {"5": 51, "6": 51, "8": 51, "10": 51},
    5: {"5": 42, "6": 42, "8": 42, "10": 42},
    6: {"5": 52, "6": 52, "8": 52, "10": 52},
}

# SLOT – freze pe lățimi (ex. W16 → 1006)
_MILL_BY_WIDTH = {
    "16": 1006,
}

# SAW – macro LAME.TMCR
_SAW_MACRO_PATH = r"..\custom\mcr\lame.tmcr"
_SAW_TOOL_ID = 2001  # uzual pe K2

# Diametre permise în cant (observația din TPACAD: 5,6,8,10)
_EDGE_ALLOWED_DIA = {5, 6, 8, 10}


# ------------------------------
# Generator TPA – blocuri W
# ------------------------------

def _W_hole(x: float, y: float, z: float, dia: float, tool_id: int) -> str:
    d = int(round(float(dia)))
    return (
        f"W#81{{ ::WTp WS=1  #8015=0 #1={int(round(x))} #2={int(round(y))} #3=-{int(round(z))} "
        f"#1002={d} #201=1 #203=1 #205={int(tool_id)} #1001=0 #9505=0 }}W"
    )


def _W_slot_pair(x1: float, y1: float, x2: float, y2: float, z: float, tool_id: int) -> List[str]:
    # Start segment (WTs) + linie (WTl) – minim necesar pentru TPACAD
    a = (
        f"W#89{{ ::WTs WS=1  #8015=0 #1={int(round(x1))} #2={int(round(y1))} #3=-{int(round(z))} "
        f"#201=1 #203=1 #205={int(tool_id)} #1001=0 #9505=0 }}W"
    )
    b = (
        f"W#2201{{ ::WTl  #8015=0 #1={int(round(x2))} #2={int(round(y2))} #3=-{int(round(z))} #42=0 #49=0 }}W"
    )
    return [a, b]


def _W_saw(op: Dict[str, Any], tool_id: int = _SAW_TOOL_ID) -> List[str]:
    """Generează macro LAME.TMCR (W#1050) pentru tăietură pe X sau Y.
    Așteptări JSON (minim):
      - SAW pe X:  {"op":"SAW","face":1,"x0_mm":50,"x1_mm":750,"y_mm":250,"z_mm":9}
      - SAW pe Y:  {"op":"SAW","face":1,"y0_mm":50,"y1_mm":400,"x_mm":250,"z_mm":9}
    """
    z = float(op.get("z_mm", 9))
    lines: List[str] = []
    if "x0_mm" in op and "x1_mm" in op and "y_mm" in op:  # tăiere paralelă cu X (orientarea 1)
        x0 = int(round(float(op["x0_mm"])))
        x1 = int(round(float(op["x1_mm"])))
        y = int(round(float(op["y_mm"])))
        lines.append(
            f"W#1050{{ ::WT2 WS=1  #8098={_SAW_MACRO_PATH} #6=1 #8020={x0} #8021={y} #8022=-{int(round(z))} "
            f"#9505=0 #8503=0 #8509=0 #8514=1 #8515=1 #8516={int(tool_id)} #8517={x1} #8525=0 #8526=0 #8527=0 }}W"
        )
    elif "y0_mm" in op and "y1_mm" in op and "x_mm" in op:  # tăiere paralelă cu Y (orientarea 2)
        y0 = int(round(float(op["y0_mm"])))
        y1 = int(round(float(op["y1_mm"])))
        x = int(round(float(op["x_mm"])))
        lines.append(
            f"W#1050{{ ::WT2 WS=1  #8098={_SAW_MACRO_PATH} #6=2 #8020={x} #8021={y0} #8022=-{int(round(z))} "
            f"#9505=0 #8503=0 #8509=0 #8514=1 #8515=1 #8516={int(tool_id)} #8517={y1} #8525=0 #8526=0 #8527=0 }}W"
        )
    else:
        raise ValueError("SAW op needs (x0_mm,x1_mm,y_mm) or (y0_mm,y1_mm,x_mm)")
    return lines


# ------------------------------
# Generator TPA – document
# ------------------------------

def _header_tpa(board: Dict[str, Any]) -> List[str]:
    DL = int(round(float(board["DL_mm"])))
    DH = int(round(float(board["DH_mm"])))
    DS = int(round(float(board["DS_mm"])))
    return [
        r"TPA\ALBATROS\EDICAD\02.00:1565:r0w0h0s1",
        r"::SIDE=0;1;3;4;5;6;",
        r"::ATTR=hide;varv",
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


def _emit_face(out: List[str], face: int, payload: List[str]) -> None:
    if not payload:
        return
    if face == 1:
        out.append(f"SIDE#{face}{{")
        out.append("$=Up")
    else:
        out.append(f"SIDE#{face}{{")
        out.append("::DX=0 XY=1")
    out.extend(payload)
    out.append("}SIDE")


# ------------------------------
# Exportatoare
# ------------------------------

def _build_tpa(doc: Dict[str, Any], profile: Dict[str, Any]) -> List[str]:
    board = doc["board"]

    DS = float(board["DS_mm"])
    def _clamp_qy(y: float) -> float:
        # Y în TpaCAD pe fețele 3..6 = în grosime: [0 .. DS]
        return max(0.0, min(DS, y))

    by_face: Dict[int, List[str]] = {1: [], 3: [], 4: [], 5: [], 6: []}

    for op in doc.get("ops", []):
        kind = op.get("op")
        face = int(op.get("face", 1))
        if face not in by_face:
            continue

        if kind == "DRILL":
            x = float(op["x_mm"])
            y = float(op["y_mm"]) if face == 1 else _clamp_qy(float(op["y_mm"]))
            z = float(op.get("z_mm", 10))
            dia = float(op["dia_mm"]) if "dia_mm" in op else float(op.get("dia", 5))

            if face in (3, 4, 5, 6) and int(round(dia)) not in _EDGE_ALLOWED_DIA:
                raise ValueError(f"Edge drill dia {dia} not allowed on face {face}. Use one of {_EDGE_ALLOWED_DIA}.")

            face_map = _DRILL_FACE_TOOL.get(face, {})
            tool_id = face_map.get(str(int(round(dia))))
            if tool_id is None:
                # fallback: T1
                tool_id = 1
            by_face[face].append(_W_hole(x, y, z, dia, tool_id))

        elif kind == "SLOT":
            w = int(round(float(op["width_mm"])))
            tool_id = _MILL_BY_WIDTH.get(str(w), next(iter(_MILL_BY_WIDTH.values())))
            x1 = float(op["x1_mm"]); y1 = float(op["y1_mm"]) if face == 1 else _clamp_qy(float(op["y1_mm"]))
            x2 = float(op["x2_mm"]); y2 = float(op["y2_mm"]) if face == 1 else _clamp_qy(float(op["y2_mm"]))
            z = float(op.get("z_mm", 10))
            by_face[face].extend(_W_slot_pair(x1, y1, x2, y2, z, tool_id))

        elif kind == "SAW":
            by_face[face].extend(_W_saw(op, _SAW_TOOL_ID))

        else:
            # ignorăm necunoscute – păstrăm robustețe
            continue

    out: List[str] = []
    out.extend(_header_tpa(board))
    # Emitem fețele în ordinea clasică
    for f in (0,):
        out.append(f"SIDE#{f}{{")
        out.append("}SIDE")
    for f in (1, 3, 4, 5, 6):
        _emit_face(out, f, by_face[f])
    return out


# ------------------------------
# CSV simplu
# ------------------------------

def _to_csv(doc: Dict[str, Any], out_csv: str) -> None:
    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "op", "face", "x_mm", "y_mm", "z_mm", "dia_mm", "width_mm", "x2_mm", "y2_mm"])
        for op in doc.get("ops", []):
            w.writerow([
                op.get("id", ""), op.get("op", ""), op.get("face", ""),
                op.get("x_mm", ""), op.get("y_mm", ""), op.get("z_mm", ""),
                op.get("dia_mm", ""), op.get("width_mm", ""), op.get("x2_mm", ""), op.get("y2_mm", ""),
            ])


# ------------------------------
# CLI
# ------------------------------

def cmd_validate(ops_path: str, schema_path: str) -> int:
    if validate is None:
        print("jsonschema not installed. Run: python -m pip install jsonschema", file=sys.stderr)
        return 2
    data = _read_json(ops_path)
    schema = _read_json(schema_path)
    validate(instance=data, schema=schema)
    print(f"valid: {ops_path} against {schema_path}")
    return 0


def cmd_to_tpa(ops_path: str, profile_path: str, out_tcn: str) -> int:
    doc = _read_json(ops_path)
    profile = _read_json(profile_path)
    lines = _build_tpa(doc, profile)
    _writelines_tpa(out_tcn, lines)
    print(f"written: {out_tcn}")
    return 0


def cmd_to_tcn(ops_path: str, profile_path: str, out_tcn: str) -> int:
    # pentru moment este același dialect
    return cmd_to_tpa(ops_path, profile_path, out_tcn)


def cmd_to_csv(ops_path: str, out_csv: str) -> int:
    doc = _read_json(ops_path)
    _to_csv(doc, out_csv)
    print(f"written: {out_csv}")
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    cmd = sys.argv[1]
    if cmd == "validate" and len(sys.argv) == 4:
        return cmd_validate(sys.argv[2], sys.argv[3])
    if cmd in ("to-tpa", "to-tcn") and len(sys.argv) == 5:
        return cmd_to_tpa(sys.argv[2], sys.argv[3], sys.argv[4])
    if cmd == "to-csv" and len(sys.argv) == 4:
        return cmd_to_csv(sys.argv[2], sys.argv[3])
    print("invalid args", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
