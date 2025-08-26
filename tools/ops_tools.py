import json, sys, argparse, pathlib, csv
from jsonschema import validate

TCN_HEADER = ["; ai3dcnc v0.1-lite", "UNITS=MM"]
CSV_HEADER = ["id","op","face","x_mm","y_mm","z_mm","dia_mm",
              "x1_mm","y1_mm","x2_mm","y2_mm","width_mm",
              "axis","offset_mm","length_mm"]

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

    args = p.parse_args(argv)
    if args.cmd == "validate":
        return cmd_validate(args.ops_json, args.schema_json)
    if args.cmd == "to-tcn":
        return cmd_to_tcn(args.ops_json, args.machine_profile_json, args.out_tcn)
    if args.cmd == "to-csv":
        return cmd_to_csv(args.ops_json, args.out_csv)

if __name__ == "__main__":
    sys.exit(main())
