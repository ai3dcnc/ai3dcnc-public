import json, sys, argparse, pathlib
from jsonschema import validate

TCN_HEADER = ["; ai3dcnc v0.1-lite", "UNITS=MM"]

def _read_json(p): 
    with open(p, "r", encoding="utf-8") as f: 
        return json.load(f)

def cmd_validate(ops_path, schema_path):
    data = _read_json(ops_path)
    schema = _read_json(schema_path)
    validate(instance=data, schema=schema)
    return 0

def _fmt_mm(v): 
    # Vitap K2 preferă 3 zecimale în multe posturi; păstrăm valoarea brută
    return f"{float(v):.3f}".rstrip('0').rstrip('.') if isinstance(v,(int,float)) else str(v)

def _line_drill(op):
    # DRILL id=d1 FACE=1 X=100 Y=80 Z=15 W=5
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
    # SLOT id=s1 FACE=1 X1=.. Y1=.. X2=.. Y2=.. W=.. Z=.. ANGLE=0
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

def cmd_to_tcn(ops_path, profile_path, out_path):
    ops = _read_json(ops_path)["ops"]
    lines = list(TCN_HEADER)
    for op in ops:
        t = op.get("op")
        if t == "DRILL":
            lines.append(_line_drill(op))
        elif t == "SLOT":
            lines.append(_line_slot(op))
        else:
            # Ignoră PROFILE/SAW în v0.1-lite generator
            continue
    out = "\n".join(lines) + "\n"
    pathlib.Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(out)
    return 0

def main(argv=None):
    p = argparse.ArgumentParser(prog="ops_tools")
    sub = p.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("validate", help="validate ops.json against schema")
    v.add_argument("ops_json")
    v.add_argument("schema_json")

    t = sub.add_parser("to-tcn", help="generate minimal TCN (DRILL,SLOT)")
    t.add_argument("ops_json")
    t.add_argument("machine_profile_json")  # rezervat pentru viitor
    t.add_argument("out_tcn")

    args = p.parse_args(argv)
    if args.cmd == "validate":
        return cmd_validate(args.ops_json, args.schema_json)
    if args.cmd == "to-tcn":
        return cmd_to_tcn(args.ops_json, args.machine_profile_json, args.out_tcn)

if __name__ == "__main__":
    sys.exit(main())
