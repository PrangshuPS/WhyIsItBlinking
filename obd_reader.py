# will work woth pytho 3.11 

# import obd
# import time
# from dotenv import load_dotenv
# import os

# load_dotenv()

# # If no real OBD, simulate data for testing
# SIMULATE = True  # Set False when real ELM327 connected

# def get_simulated_data():
#     import random
#     return {
#         "rpm": round(random.uniform(700, 6000), 1),
#         "speed": round(random.uniform(0, 120), 1),
#         "coolant_temp": round(random.uniform(70, 105), 1),
#         "throttle": round(random.uniform(0, 100), 1),
#         "engine_load": round(random.uniform(10, 90), 1),
#         "fuel_pressure": round(random.uniform(30, 50), 1),
#         "intake_temp": round(random.uniform(20, 60), 1),
#         "battery_voltage": round(random.uniform(12.0, 14.8), 2)
#     }

# def get_real_data():
#     connection = obd.OBD(os.getenv("OBD_PORT"))
#     data = {}
#     commands = {
#         "rpm": obd.commands.RPM,
#         "speed": obd.commands.SPEED,
#         "coolant_temp": obd.commands.COOLANT_TEMP,
#         "throttle": obd.commands.THROTTLE_POS,
#         "engine_load": obd.commands.ENGINE_LOAD,
#         "fuel_pressure": obd.commands.FUEL_PRESSURE,
#         "intake_temp": obd.commands.INTAKE_TEMP,
#         "battery_voltage": obd.commands.CONTROL_MODULE_VOLTAGE
#     }
#     for key, cmd in commands.items():
#         response = connection.query(cmd)
#         data[key] = float(response.value.magnitude) if not response.is_null() else None
#     connection.close()
#     return data

# def fetch_data():
#     if SIMULATE:
#         return get_simulated_data()
#     return get_real_data()




# works for python 3.13 but simulation only

import random

SIMULATE = True  # Set False when real ELM327 connected

def get_simulated_data():
    return {
        "rpm": round(random.uniform(700, 6000), 1),
        "speed": round(random.uniform(0, 120), 1),
        "coolant_temp": round(random.uniform(70, 105), 1),
        "throttle": round(random.uniform(0, 100), 1),
        "engine_load": round(random.uniform(10, 90), 1),
        "fuel_pressure": round(random.uniform(30, 50), 1),
        "intake_temp": round(random.uniform(20, 60), 1),
        "battery_voltage": round(random.uniform(12.0, 14.8), 2)
    }

def fetch_data():
    return get_simulated_data()