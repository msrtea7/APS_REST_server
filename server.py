from functools import wraps
import time
import os
import simcentralconnect
import clr

clr.AddReference("System")
import System
from System import Array, String, Object
from System.Collections.Generic import Dictionary
from fastapi import FastAPI, Body
import uvicorn

# ── Config ─────────────────────────────────────────────────────────────────────

HOST = "0.0.0.0"
PORT = 8000
SIMCENTRAL_TIMEOUT = 40000
VAR_TIMEOUT = 5000
PARAM_TIMEOUT = 30000

# ── SimCentral setup ───────────────────────────────────────────────────────────

sc = simcentralconnect.connect().Result
sc.SetOptions(repr({"Timeout": SIMCENTRAL_TIMEOUT, "WaitForNoSimulationActivity": "true"}))

sim_mgr   = sc.GetService("ISimulationManager")
mdl_mgr   = sc.GetService("IModelManager")
conn_mgr  = sc.GetService("IConnectorManager")
var_mgr   = sc.GetService("IVariableManager")
param_mgr = sc.GetService("IParameterManager")
lib_mgr   = sc.GetService("ILibraryManager")
snap_mgr  = sc.GetService("ISnapshotManager")

def nd(d: dict) -> Dictionary[System.String, System.Object]:
    out = Dictionary[System.String, System.Object]()
    for k, v in d.items():
        out[k] = v
    return out

# ── App ────────────────────────────────────────────────────────────────────────

def handle_exceptions(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            return {"success": False, "error": str(e)}
    return wrapper

app = FastAPI()

@app.post("/get_open_simulations")
@handle_exceptions
def get_open_simulations():
    open_sims = sim_mgr.GetOpenSimulations().Result
    return {"open_simulations": [str(s) for s in open_sims]}

@app.post("/get_all_simulations")
@handle_exceptions
def get_all_simulations():
    all_sims = sim_mgr.GetAvailableSimulations().Result
    return {"all_simulations": [str(s) for s in all_sims]}

@app.post("/open_simulation")
@handle_exceptions
def open_simulation(body: dict = Body(...)):
    sim_mgr.OpenSimulation(body["sim_name"]).Result
    return {"sim_name": body["sim_name"]}

@app.post("/create_simulation")
@handle_exceptions
def create_simulation(body: dict = Body(...)):
    temp_name = sim_mgr.CreateSim(os.getlogin(), body.get("template", "ProcessTemplate")).Result
    sim_mgr.RenameSim(temp_name, body["sim_name"]).Result
    return {"sim_name": body["sim_name"], "template": body.get("template", "ProcessTemplate")}

@app.post("/save_simulation")
@handle_exceptions
def save_simulation(body: dict = Body(...)):
    sim_mgr.SaveSimulation(body["sim_name"]).Result
    return {"sim_name": body["sim_name"]}

# @app.post("/get_simulation_statistics")
# @handle_exceptions
# def get_simulation_statistics(body: dict = Body(...)):
#     s = sim_mgr.GetSimulationStats(body["sim_name"], 120000).Result
#     return {"statistics": s}

@app.post("/get_simulation_status")
def get_simulation_status(body: dict = Body(...)):
    s = sim_mgr.GetSimulationStatus(body["sim_name"]).Result
    return {"has_data": bool(s[0]), "specified": bool(s[1]), "solved": bool(s[2])}

# @app.post("/trigger_Manual_Solve")
# @handle_exceptions
# def trigger_Manual_Solve(body: dict = Body(...)):
#     s = sim_mgr.TriggerManualSolvePartialWait(body["sim_name"], 0.5, SIMCENTRAL_TIMEOUT).Result
#     return {"is trigger sent": bool(s)}

@app.post("/get_existing_models")
@handle_exceptions
def get_existing_models(body: dict = Body(...)):
    resource = Array[String]([body["sim_name"]])
    child_types = Array[Object]([
        nd({"type": "model", "fields": Array[String](["name", "modelType"])}),
    ])
    result = sim_mgr.Query("simulation", resource, child_types, VAR_TIMEOUT).Result
    return {
        "models": [
            {"name": str(m.name), "type": str(m.modeltype)}
            for m in getattr(result, "model", []) or []
        ]
    }

@app.post("/add_model")
@handle_exceptions
def add_model(body: dict = Body(...)):
    name = mdl_mgr.AddModel(body["sim_name"], None, body["model_type"], body.get("x", 100), body.get("y", 100)).Result
    if body.get("model_name"):
        time.sleep(0.5)
        mdl_mgr.RenameModel(body["sim_name"], name, body["model_name"]).Result
        name = body["model_name"]
    return {"model_name": name}

@app.post("/remove_model")
@handle_exceptions
def remove_model(body: dict = Body(...)):
    mdl_mgr.RemoveModel(body["sim_name"], body["model_name"]).Result
    return {"model_name": body["model_name"]}

@app.post("/rename_model")
@handle_exceptions
def rename_model(body: dict = Body(...)):
    mdl_mgr.RenameModel(body["sim_name"], body["old_name"], body["new_name"]).Result
    return {"old_name": body["old_name"], "new_name": body["new_name"]}

@app.post("/connect_ports")
@handle_exceptions
def connect_ports(body: dict = Body(...)):
    name = conn_mgr.AddConnector(body["sim_name"], None, body["from_port"], body["to_port"]).Result
    return {"connector_name": str(name)}

@app.post("/remove_connector")
@handle_exceptions
def remove_connector(body: dict = Body(...)):
    conn_mgr.RemoveConnector(body["sim_name"], body["connector_name"]).Result
    return {"connector_name": body["connector_name"]}

@app.post("/set_variable_specification")
@handle_exceptions
def set_variable_specification(body: dict = Body(...)):
    result = var_mgr.SetVariableSpecification(body["sim_name"], body["path"], body["is_specified"], VAR_TIMEOUT).Result
    return {"path": body["path"], "is_specified": body["is_specified"], "result": bool(result)}

# @app.post("/get_variable_value")
# @handle_exceptions
# def get_variable_value(body: dict = Body(...)):
#     val = var_mgr.GetVariableValue(body["sim_name"], body["path"], None, VAR_TIMEOUT).Result
#     return {"path": body["path"], "value": str(val)}

@app.post("/get_variable_value")
@handle_exceptions
def get_variable_value(body: dict = Body(...)):
    unit = body.get("unit")
    val = var_mgr.GetVariableValue(body["sim_name"], body["path"], unit, VAR_TIMEOUT).Result
    result = {"path": body["path"], "value": str(val)}
    if unit is not None:
        result["unit"] = unit
    return result

@app.post("/set_variable")
@handle_exceptions
def set_variable(body: dict = Body(...)):
    result = var_mgr.SetVariableValue(body["sim_name"], body["path"], float(body["value"]), body.get("unit")).Result
    print(result)
    return {"path": body["path"], "value": body["value"], "unit": body.get("unit")}

@app.post("/set_parameter")
@handle_exceptions
def set_parameter(body: dict = Body(...)):
    param_mgr.UpdateParameterValue(body["sim_name"], body["path"], body["value"], PARAM_TIMEOUT).Result
    return {"path": body["path"], "value": body["value"]}

@app.post("/get_parameter_value")
@handle_exceptions
def get_parameter(body: dict = Body(...)):
    val = param_mgr.ReadParameterValue(body["sim_name"], body["path"], body.get("unit"), PARAM_TIMEOUT).Result
    return {"path": body["path"], "value": str(val)}

@app.post("/create_fluid")
@handle_exceptions
def create_fluid(body: dict = Body(...)):
    sim_name, fluid_name = body["sim_name"], body["fluid_name"]
    databank = body.get("databank", "System:SIMSCI")
    lib_mgr.CreateFluid(sim_name, fluid_name, PARAM_TIMEOUT).Result
    for comp in body["components"]:
        lib_mgr.AddComponent(sim_name, fluid_name, databank, comp, PARAM_TIMEOUT).Result
    lib_mgr.UpdateFluidMethodData(sim_name, fluid_name, "System", body.get("thermo_method", "Non-Random Two-Liquid (NRTL)"), PARAM_TIMEOUT).Result
    lib_mgr.UpdateFluidMethodData(sim_name, fluid_name, "Phases", body.get("phases", "Vapor/Liquid (VLE)"), PARAM_TIMEOUT).Result
    return {"fluid_name": fluid_name, "components": body["components"]}

@app.post("/assign_fluid")
@handle_exceptions
def assign_fluid(body: dict = Body(...)):
    fluid_path = f"{body['sim_name']}.Models.{body['fluid_name']}"
    param_mgr.UpdateParameterValue(body["sim_name"], f"{body['source_name']}.FluidType", fluid_path, PARAM_TIMEOUT).Result
    return {"source": body["source_name"], "fluid": body["fluid_name"]}

@app.post("/create_snapshot")
@handle_exceptions
def create_snapshot(body: dict = Body(...)):
    name = snap_mgr.CreateSnapshot(body["sim_name"]).Result
    return {"snapshot_name": str(name)}

@app.post("/get_flowsheet_topology")
@handle_exceptions
def get_flowsheet_topology(body: dict = Body(...)):
    resource = Array[String]([body["sim_name"]])
    child_types = Array[Object]([
        nd({"type": "connector", "fields": Array[String](["name", "from", "to"])}),
    ])
    result = sim_mgr.Query("Simulation", resource, child_types, VAR_TIMEOUT).Result
    return {
        "connectors": [
            {"name": str(c.name), "from": str(getattr(c, "from")), "to": str(c.to)}
            for c in getattr(result, "connector", []) or []
        ]
    }

@app.post("/get_connectable_ports")
@handle_exceptions
def get_connectable_ports(body: dict = Body(...)):
    resource = Array[String]([body["sim_name"], body["model_name"]])
    child_types = Array[Object]([
        nd({"type": "port", "fields": Array[String](["name", "direction", "porttype", "ismultiple", "isportelement"])}),
    ])
    result = sim_mgr.Query("Simulation", resource, child_types, VAR_TIMEOUT).Result

    fixed, multiple = [], {}
    for p in getattr(result, "port", []) or []:
        if p.isportelement:
            base = str(p.name).split("[")[0]
            multiple.setdefault(base, []).append(str(p.name))
        else:
            fixed.append({"name": str(p.name), "direction": str(p.direction), "porttype": str(p.porttype)})

    return {
        "fixed_ports": fixed,
        "multiple_ports": [{"name": k, "instances": v} for k, v in multiple.items()],
    }

@app.post("/get_model_error_messages")
@handle_exceptions
def get_model_error_messages(body: dict = Body(...)):
    result = mdl_mgr.GetModelErrorMessages(body["sim_name"], body["model_name"], None).Result
    return {"model_name": body["model_name"], "error_messages": {str(k): str(v) for k, v in result.items()}}

# @app.post("/get_model_badge_status")
# def get_model_badge_status(body: dict = Body(...)):
#     result = mdl_mgr.GetModelBadgeStatus(body["sim_name"], body["model_name"], None).Result
#     return {"model_name": body["model_name"], "badge_status": any(result)}

if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT)