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

sim_mgr = sc.GetService("ISimulationManager")
var_mgr = sc.GetService("IVariableManager")

sim_name = "Haber7"
path = "Comp1.P2"
value = 201
unit = "bar"

r = sim_mgr.OpenSimulation(sim_name).Result
time.sleep(4)
print(r)

# 直接调用，不走FastAPI
result = var_mgr.SetVariableValue(sim_name, path, value, unit).Result
print("Result:", result)

# 验证：读回来看看值对不对
read_result = var_mgr.GetVariableValue(sim_name, path, unit).Result
print("Read back:", read_result)

sim_mgr.SaveSimulation(sim_name)