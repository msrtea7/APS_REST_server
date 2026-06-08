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

simName = "HaberBoschPlant_origin"
sm.OpenSimulation(simName).Result

res = sm.GetSimulationStats(simName, 300000).Result

print(res)