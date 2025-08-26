import json, sys, argparse, pathlib, csv
from jsonschema import validate

TCN_HEADER = ["; ai3dcnc v0.1-lite", "UNITS=MM"]
CSV_HEADER = [
    "id","op","face","x_mm","y_mm","z_mm","dia_mm",
    "x1_mm","y1_mm","x2_mm","y2_mm","width_mm",
    "axis","offset_mm","length_mm"
]

def _read_json(p):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def _fmt_mm(v):
    return f"{float(v):.3f}".rstrip('0').rstrip('.') if isinstance(v, (int, float)) else (v if v is not None else "")

def cmd_validate(ops_path, schema_path):
    data = _read_json(ops_path)
    schema = _read_json(schema_path)
    validate(instance=data, schema=schema)
    return 0

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
        else:
            continue
    out = "\n".join(lines) + "\n"
    pathlib.Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(out)
    return 0

def cmd_to_csv(ops_path, out_csv):
    ops = _read_json(ops_path)["ops"]
    pathlib.Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_HEADER)
        w.writeheader()
        for op in ops:
            row = {k: "" for k in CSV_HEADER}
            row["id"] = op.get("id","")
            row["op"] = op.get("op","")
            row["face"] = op.get("face","")
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
                row["axis"] = op.get("axis","")
                row["offset_mm"] = _fmt_mm(op.get("offset_mm"))
                row["length_mm"] = _fmt_mm(op.get("length_mm"))
                row["z_mm"] = _fmt_mm(op.get("z_mm"))
            w.writerow(row)
    return 0

# ---------- TCN -> JSON ----------
def _parse_kv(token):
    if "=" not in token:
        return token, None
    k, v = token.split("=", 1)
    try:
        if v.upper() in ("X","Y"):
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
            if not line or line.startswith(";") or line.startswith("UNITS="):
                continue
            parts = line.split()
            kind = parts[0].upper()
            kv = dict(_parse_kv(t) for t in parts[1:])
            if kind == "DRILL":
                ops.append({
                    "id": str(kv.get("id","")),
                    "op": "DRILL",
                    "face": int(kv.get("FACE",1)),
                    "x_mm": float(kv.get("X",0)),
                    "y_mm": float(kv.get("Y",0)),
                    "z_mm": float(kv.get("Z",0)),
                    "dia_mm": float(kv.get("W",0)),
                })
            elif kind == "SLOT":
                ops.append({
                    "id": str(kv.get("id","")),
                    "op": "SLOT",
                    "face": int(kv.get("FACE",1)),
                    "x1_mm": float(kv.get("X1",0)),
                    "y1_mm": float(kv.get("Y1",0)),
                    "x2_mm": float(kv.get("X2",0)),
                    "y2_mm": float(kv.get("Y2",0)),
                    "width_mm": float(kv.get("W",0)),
                    "z_mm": float(kv.get("Z",0)),
                })
            elif kind == "SAW":
                ops.append({
                    "id": str(kv.get("id","")),
                    "op": "SAW",
                    "face": int(kv.get("FACE",1)),
                    "axis": str(kv.get("AXIS","X")),
                    "offset_mm": float(kv.get("OFFSET",0)),
                    "length_mm": float(kv.get("LENGTH",0)),
                    "z_mm": float(kv.get("Z",0)),
                })
            else:
                continue
    doc = {
        "version": "0.1-lite",
        "units": "mm",
        "from_finished_edges": True,
        "board": board,
        "ops": ops
    }
    pathlib.Path(out_ops_json).parent.mkdir(parents=True, exist_ok=True)
    with open(out_ops_json, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    return 0

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
    if args.cmd == "from-tcn":
        return cmd_from_tcn(args.in_tcn, args.board_json, args.out_ops_json)

if __name__ == "__main__":
    sys.exit(main())
