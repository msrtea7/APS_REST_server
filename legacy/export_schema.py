import simcentralconnect
import csv
import os
import System
from System import Array, Object, String
from System.Collections.Generic import Dictionary

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

sc = simcentralconnect.connect().Result
sm = sc.GetService("ISimulationManager")

simName = "SchemaRef"
sm.OpenSimulation(simName).Result
print("Opened\n")

resource = Array[String]([simName])
child_types = Array[Object]([
    convert({"type": "model", "fields": Array[String](["name", "modeltype"])}),
])
result = sm.Query("Simulation", resource, child_types, 5000).Result
models = list(getattr(result, "model", []) or [])

os.makedirs("schemas", exist_ok=True)

for m in models:
    r = sm.Query(
        "Simulation",
        Array[String]([simName, m.name]),
        Array[Object]([
            convert({"type": "variable",  "fields": Array[String](["*"])}),
            convert({"type": "parameter", "fields": Array[String](["*"])}),
            convert({"type": "port",      "fields": Array[String](["*"])}),
        ]),
        5000
    ).Result

    safe_name = m.modeltype.replace(":", "_").replace(".", "_")

    # Variables
    with open(f"schemas/{safe_name}_var.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["name", "vartype", "uom", "specified", "group", "range", "description"])
        for v in getattr(r, "variable", []) or []:
            w.writerow([v.name, v.vartype, v.uom, v.specified, v.group, f"[{v.minvalue}, {v.maxvalue}]", v.description])

    # Parameters
    with open(f"schemas/{safe_name}_parameter.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["name", "paramtype", "uom", "issetbyuser", "group", "description"])
        for p in getattr(r, "parameter", []) or []:
            w.writerow([p.name, p.paramtype, p.uom, p.issetbyuser, p.group, p.description])

    # Ports
    with open(f"schemas/{safe_name}_port.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["name", "direction", "porttype", "ismultiple"])
        for p in getattr(r, "port", []) or []:
            w.writerow([p.name, p.direction, p.porttype, p.ismultiple])

    print(f"Written: schemas/{safe_name}_{{var,parameter,port}}.csv")