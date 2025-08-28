import json, sys, argparse, pathlib, csv, codecs, os
from jsonschema import validate

# ------------------ Helpers ------------------
TCN_HEADER = ["; ai3dcnc v0.1-lite", "UNITS=MM"]
CSV_HEADER = [
    "id","op","face","x_mm","y_mm","z_mm","dia_mm",
    "x1_mm","y1_mm","x2_mm","y2_mm","width_mm",
    "axis","offset_mm","length_mm"
]


def _read_json(p: str):
    """Read JSON accepting UTF-8 with or without BOM. Better error on missing file."""
    try:
        with open(p, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except FileNotFoundError as e:
        raise FileNotFoundError(f"missing file: {p} (cwd={os.getcwd()})") from e


def _fmt_mm(v):
    if isinstance(v, (int, float)):
        s = f"{float(v):.3f}"
        s = s.rstrip("0").rstrip(".")
        return s if s else "0"
    return v if v is not None else ""


# ------------------ Validate ------------------

def cmd_validate(ops_path, schema_path):
    data = _read_json(ops_path)
    schema = _read_json(schema_path)
    validate(instance=data, schema=schema)
    print(f"valid: {ops_path} against {schema_path}")
    return 0


# ------------------ Custom TCN (simple) ------------------

def _line_drill(op):
    return " ".join([
        "DRILL",
        f"id={op['id']}",
        f"FACE={op['face']}",
        f"X={_fmt_mm(op['x_mm'])}",
        f"Y={_fmt_mm(op['y_mm'])}",
        f"Z={_fmt_mm(op['z_mm'])}",
        f"W={_fmt_mm(op['dia_mm'])}",
    ])


def _line_slot(op):
    return " ".join([
        "SLOT",
        f"id={op['id']}",
        f"FACE={op['face']}",
        f"X1={_fmt_mm(op['x1_mm'])}",
        f"Y1={_fmt_mm(op['y1_mm'])}",
        f"X2={_fmt_mm(op['x2_mm'])}",
        f"Y2={_fmt_mm(op['y2_mm'])}",
        f"W={_fmt_mm(op['width_mm'])}",
        f"Z={_fmt_mm(op['z_mm'])}",
        "ANGLE=0",
    ])


def _line_saw(op):
    return " ".join([
        "SAW",
        f"id={op['id']}",
        f"FACE={op['face']}",
        f"AXIS={op['axis']}",
        f"OFFSET={_fmt_mm(op['offset_mm'])}",
        f"LENGTH={_fmt_mm(op['length_mm'])}",
        f"Z={_fmt_mm(op['z_mm'])}",
    ])


def cmd_to_tcn(ops_path, profile_path, out_path):
    ops = _read_json(ops_path)["ops"]
    profile = _read_json(profile_path)
    lines = list(TCN_HEADER)
    hc = profile.get("tcn", {}).get("header_comment")
    if hc:
        lines.insert(0, f"; {hc}")
    for op in ops:
        t = op.get("op")
        if t == "DRILL":
            lines.append(_line_drill(op))
        elif t == "SLOT":
            lines.append(_line_slot(op))
        elif t == "SAW":
            lines.append(_line_saw(op))
    data = ("\r\n".join(lines) + "\r\n").encode("cp1252", "replace")  # CRLF, CP1252, no BOM
    pathlib.Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(data)
    print(f"written: {out_path}")
    return 0


# ------------------ CSV ------------------

def cmd_to_csv(ops_path, out_csv):
    ops = _read_json(ops_path)["ops"]
    pathlib.Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_HEADER)
        w.writeheader()
        for op in ops:
            row = {k: "" for k in CSV_HEADER}
            row["id"] = op.get("id", "")
            row["op"] = op.get("op", "")
            row["face"] = op.get("face", "")
            if op["op"] == "DRILL":
                row["x_mm"] = _fmt_mm(op.get("x_mm"))
                row["y_mm"] = _fmt_mm(op.get("y_mm"))
                row["z_mm"] = _fmt_mm(op.get("z_mm"))
                row["dia_mm"] = _fmt_mm(op.get("dia_mm"))
            elif op["op"] == "SLOT":
                row["x1_mm"] = _fmt_mm(op.get("x1_mm"))
                row["y1_mm"] = _fmt_mm(op.get("y1_mm"))
                row["x2_mm"] = _fmt_mm(op.get("x2_mm"))
                row["y2_mm"] = _fmt_mm(op.get("y2_mm"))
                row["width_mm"] = _fmt_mm(op.get("width_mm"))
                row["z_mm"] = _fmt_mm(op.get("z_mm"))
            elif op["op"] == "SAW":
                row["axis"] = op.get("axis", "")
                row["offset_mm"] = _fmt_mm(op.get("offset_mm"))
                row["length_mm"] = _fmt_mm(op.get("length_mm"))
                row["z_mm"] = _fmt_mm(op.get("z_mm"))
            w.writerow(row)
    print(f"written: {out_csv}")
    return 0


# ------------------ TPA-CAD (.tcn ALBATROS/EDICAD) ------------------

def _write_utf16le_bom(out_path: str, lines):
    data = ("\r\n".join(lines) + "\r\n").encode("utf-16-le")
    pathlib.Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(codecs.BOM_UTF16_LE)
        f.write(data)
    return 0


def _tpa_slot_W_blocks(op, tool_id: int):
    x1 = _fmt_mm(op["x1_mm"]); y1 = _fmt_mm(op["y1_mm"])
    x2 = _fmt_mm(op["x2_mm"]); y2 = _fmt_mm(op["y2_mm"])
    z = _fmt_mm(op["z_mm"])
    return [
        ("W#89{"  # set start, tool
         f" ::WTs WS=1  #8015=0 #1={x1} #2={y1} #3=-{z} #201=1 #203=1 #205={tool_id} "
         "#1001=100 #9502=0 #9503=0 #9505=0 #9506=0 #9504=0 #8101=0 #8096=0 #8095=0 "
         "#37=0 #40=0 #39=0 #46=0 #8135=0 #8136=0 #38=0 #8180=0 #8181=0 #8185=0 #8186=0 }W"),
        ("W#2201{"  # move end
         f" ::WTl  #8015=0 #1={x2} #2={y2} #3=-{z} #42=0 #49=0 }}W")
    ]


def _tpa_saw_W1050(op, tool_id: int, start_x_mm: float = 50.0, start_y_mm: float = 50.0):
    axis = str(op.get("axis", "X")).upper()
    z = _fmt_mm(op["z_mm"])
    off = float(op["offset_mm"])  # const pe axa perpendiculară
    L = float(op["length_mm"])    # lungime de tăiere

    if axis == "X":
        x0 = _fmt_mm(start_x_mm)
        x1 = _fmt_mm(start_x_mm + L)
        y = _fmt_mm(off)
        # #6=1 -> axa X; #8020=X0 #8021=Y const #8022=-Z; #8516=tool; #8517=X1
        return [
            ("W#1050{"  # circular
             " ::WT2 WS=1  #8098=..\\custom\\mcr\\lame.tmcr #6=1 "
             f"#8020={x0} #8021={y} #8022=-{z} #9505=0 #8503=0 #8509=0 "
             f"#8514=1 #8515=1 #8516={int(tool_id)} #8517={x1} #8525=0 #8526=0 #8527=0 }}W")
        ]
    else:  # axa Y
        y0 = _fmt_mm(start_y_mm)
        y1 = _fmt_mm(start_y_mm + L)
        x = _fmt_mm(off)
        return [
            ("W#1050{"  # circular
             " ::WT2 WS=1  #8098=..\\custom\\mcr\\lame.tmcr #6=2 "
             f"#8020={x} #8021={y0} #8022=-{z} #9505=0 #8503=0 #8509=0 "
             f"#8514=1 #8515=1 #8516={int(tool_id)} #8517={y1} #8525=0 #8526=0 #8527=0 }}W")
        ]


def cmd_to_tpa(ops_path, profile_path, out_path):
    # Dialect Vitap TpaCAD (ALBATROS/EDICAD). Scriere UTF-16LE + BOM + CRLF.
    doc = _read_json(ops_path)
    ops = doc["ops"]
    board = doc.get("board", {})
    DL = int(board.get("DL_mm", 800))
    DH = int(board.get("DH_mm", 450))
    DS = int(board.get("DS_mm", 18))

    prof = _read_json(profile_path)
    tool_cfg = prof.get("tpa", {}).get("tools", {})
    tool_map_mill = {str(k): int(v) for k, v in tool_cfg.get("mill_by_diam_mm", {}).items()}
    mill_default = int(tool_cfg.get("default_mill_id", 1004))
    drill_map = {str(k): int(v) for k, v in tool_cfg.get("drill_by_diam_mm", {}).items()} if "drill_by_diam_mm" in tool_cfg else {}
    drill_default = int(tool_cfg.get("default_drill_id", 1))
    saw_tool_id = int(tool_cfg.get("saw_default_id", 2001))

    defaults = prof.get("tpa", {}).get("defaults", {})
    saw_x0 = float(defaults.get("saw_start_x_mm", 50))
    saw_y0 = float(defaults.get("saw_start_y_mm", 50))

    lines = [
        r"TPA\ALBATROS\EDICAD\02.00:1565:r0w0h0s1",
        "::SIDE=0;1;",
        "::ATTR=hide;varv",
        f"::UNm DL={DL} DH={DH} DS={DS}",
        "'tcn version=2.8.21",
        "'code=unicode",
        "EXE{", "#0=0", "#1=0", "#2=0", "#3=0", "#4=0", "}EXE",
        "OFFS{", "#0=0.0|0", "#1=0.0|0", "#2=0.0|0", "}OFFS",
        "VARV{", "#0=0.0|0", "#1=0.0|0", "}VARV",
        "VAR{", "}VAR",
        "SPEC{", "}SPEC",
        "INFO{", "}INFO",
        "OPTI{", ":: OPTKIND=%;0 OPTROUTER=%;0 LSTCOD=%0%1%2", "}OPTI",
        "LINK{", "}LINK",
        "SIDE#0{", "}SIDE",
        "SIDE#1{",
        "$=Up",
    ]

    for op in ops:
        kind = op.get("op")
        if kind == "DRILL":
            x = _fmt_mm(op["x_mm"]); y = _fmt_mm(op["y_mm"]); z = _fmt_mm(op["z_mm"])
            d = _fmt_mm(op["dia_mm"])
            tool_id = int(drill_map.get(str(int(round(float(op["dia_mm"])))), drill_default))
            lines.append(
                ("W#81{"  # hole
                 f" ::WTp WS=1  #8015=0 #1={x} #2={y} #3=-{z} #1002={d} #201=1 #203=1 #205={tool_id} #1001=0 #9505=0 }}W")
            )
        elif kind == "SLOT":
            width = int(round(float(op["width_mm"])))
            tool_id = int(tool_map_mill.get(str(width), mill_default))
            lines += _tpa_slot_W_blocks(op, tool_id)
        elif kind == "SAW":
            lines += _tpa_saw_W1050(op, saw_tool_id, start_x_mm=saw_x0, start_y_mm=saw_y0)
        else:
            continue

    lines += [
        "}SIDE",
        "SIDE#3{", "::DX=0 XY=1", "}SIDE",
        "SIDE#4{", "::DX=0 XY=1", "}SIDE",
        "SIDE#5{", "::DX=0 XY=1", "}SIDE",
        "SIDE#6{", "::DX=0 XY=1", "}SIDE",
    ]
    rc = _write_utf16le_bom(out_path, lines)
    print(f"written: {out_path}")
    return rc


# ------------------ TCN -> JSON (custom) ------------------

def _parse_kv(token):
    if "=" not in token:
        return token, None
    k, v = token.split("=", 1)
    try:
        if v.upper() in ("X", "Y"):
            return k, v.upper()
        if "." in v or "e" in v.lower():
            return k, float(v)
        return k, int(v)
    except Exception:
        return k, v


def cmd_from_tcn(tcn_path, board_json_path, out_ops_json):
    bj = _read_json(board_json_path)
    board = bj.get("board", bj)
    ops = []
    with open(tcn_path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith(";") or line.startswith("UNITS=") or line.startswith("[") or line.startswith("TPA\\"):
                continue
            parts = line.split()
            kind = parts[0].upper()
            kv = dict(_parse_kv(t) for t in parts[1:])
            if kind == "DRILL":
                ops.append({
                    "id": str(kv.get("id", "")),
                    "op": "DRILL",
                    "face": int(kv.get("FACE", 1)),
                    "x_mm": float(kv.get("X", 0)),
                    "y_mm": float(kv.get("Y", 0)),
                    "z_mm": float(kv.get("Z", 0)),
                    "dia_mm": float(kv.get("W", 0)),
                })
            elif kind == "SLOT":
                ops.append({
                    "id": str(kv.get("id", "")),
                    "op": "SLOT",
                    "face": int(kv.get("FACE", 1)),
                    "x1_mm": float(kv.get("X1", 0)),
                    "y1_mm": float(kv.get("Y1", 0)),
                    "x2_mm": float(kv.get("X2", 0)),
                    "y2_mm": float(kv.get("Y2", 0)),
                    "width_mm": float(kv.get("W", 0)),
                    "z_mm": float(kv.get("Z", 0)),
                })
            elif kind == "SAW":
                ops.append({
                    "id": str(kv.get("id", "")),
                    "op": "SAW",
                    "face": int(kv.get("FACE", 1)),
                    "axis": str(kv.get("AXIS", "X")),
                    "offset_mm": float(kv.get("OFFSET", 0)),
                    "length_mm": float(kv.get("LENGTH", 0)),
                    "z_mm": float(kv.get("Z", 0)),
                })
            else:
                continue
    doc = {
        "version": "0.1-lite",
        "units": "mm",
        "from_finished_edges": True,
        "board": board,
        "ops": ops,
    }
    pathlib.Path(out_ops_json).parent.mkdir(parents=True, exist_ok=True)
    with open(out_ops_json, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    print(f"written: {out_ops_json}")
    return 0


# ------------------ CLI ------------------

def main(argv=None):
    p = argparse.ArgumentParser(prog="ops_tools")
    sub = p.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("validate", help="validate ops.json against schema")
    v.add_argument("ops_json")
    v.add_argument("schema_json")

    t = sub.add_parser("to-tcn", help="generate minimal TCN (DRILL,SLOT,SAW)")
    t.add_argument("ops_json")
    t.add_argument("machine_profile_json")
    t.add_argument("out_tcn")

    c = sub.add_parser("to-csv", help="export canonical CSV from ops.json")
    c.add_argument("ops_json")
    c.add_argument("out_csv")

    tp = sub.add_parser("to-tpa", help="generate Vitap TpaCAD .tcn (ALBATROS/EDICAD)")
    tp.add_argument("ops_json")
    tp.add_argument("machine_profile_json")
    tp.add_argument("out_tcn")

    f = sub.add_parser("from-tcn", help="parse TCN into ops.json (needs board json)")
    f.add_argument("in_tcn")
    f.add_argument("board_json")
    f.add_argument("out_ops_json")

    args = p.parse_args(argv)
    if args.cmd == "validate":
        return cmd_validate(args.ops_json, args.schema_json)
    if args.cmd == "to-tcn":
        return cmd_to_tcn(args.ops_json, args.machine_profile_json, args.out_tcn)
    if args.cmd == "to-csv":
        return cmd_to_csv(args.ops_json, args.out_csv)
    if args.cmd == "to-tpa":
        return cmd_to_tpa(args.ops_json, args.machine_profile_json, args.out_tcn)
    if args.cmd == "from-tcn":
        return cmd_from_tcn(args.in_tcn, args.board_json, args.out_ops_json)

    return 1


if __name__ == "__main__":
    sys.exit(main())
