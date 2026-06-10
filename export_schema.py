import simcentralconnect
import os
import pandas as pd
import System
from System import Array, Object, String
from System.Collections.Generic import Dictionary

# ── Configuration ─────────────────────────────────────────────────────────────
SIM_NAME   = "Sep_MeOHWater_base_2"
OUTPUT_DIR = "schemas"
TIMEOUT    = 5000
# ──────────────────────────────────────────────────────────────────────────────

SCHEMAS = [
    ("variable",  ["name", "vartype", "uom", "specified", "group", "minvalue", "maxvalue", "description"]),
    ("parameter", ["name", "paramtype", "uom", "issetbyuser", "group", "description"]),
    ("port",      ["name", "direction", "porttype", "ismultiple"]),
]


def convert(py_dict):
    ndict = Dictionary[String, Object]()
    for k, v in py_dict.items():
        if isinstance(v, dict):
            ndict[k] = convert(v)
        elif isinstance(v, (list, tuple)):
            ndict[k] = Array[Object]([convert(x) if isinstance(x, dict) else x for x in v])
        else:
            ndict[k] = v
    return ndict


def to_csv(records, columns, path):
    out_columns = list(dict.fromkeys(
        "range" if c in ("minvalue", "maxvalue") else c for c in columns
    ))

    def make_row(rec):
        row = {c: getattr(rec, c, None) for c in columns}
        if "minvalue" in row or "maxvalue" in row:
            row["range"] = f"[{row.pop('minvalue', None)}, {row.pop('maxvalue', None)}]"
        return row

    pd.DataFrame(
        [make_row(rec) for rec in records],
        columns=out_columns,
    ).to_csv(path, index=False, encoding="utf-8")


def main():
    sc = simcentralconnect.connect().Result
    sm = sc.GetService("ISimulationManager")

    sm.OpenSimulation(SIM_NAME).Result
    print("Opened\n")

    result = sm.Query(
        "Simulation",
        Array[String]([SIM_NAME]),
        Array[Object]([convert({"type": "model", "fields": Array[String](["name", "modeltype"])})]),
        TIMEOUT,
    ).Result
    models = list(getattr(result, "model", []) or [])
    models = list({m.modeltype: m for m in (getattr(result, "model", []) or [])}.values())

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for m in models:
        r = sm.Query(
            "Simulation",
            Array[String]([SIM_NAME, m.name]),
            Array[Object]([convert({"type": t, "fields": Array[String](["*"])}) for t, _ in SCHEMAS]),
            TIMEOUT,
        ).Result
        print(m.modeltype)
        base_path = f"{OUTPUT_DIR}/{m.modeltype.replace(':', '_').replace('.', '_')}"

        for type_name, columns in SCHEMAS:
            records = list(getattr(r, type_name, []) or [])
            to_csv(records, columns, f"{base_path}_{type_name}.csv")

        print(f"Written: {base_path}_{{variable,parameter,port}}.csv")


if __name__ == "__main__":
    main()