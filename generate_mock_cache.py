import sqlite3
import json
import os
import math
from datetime import datetime, timedelta

CACHE_DB = "openf1_cache.db"

# Remove existing database if it exists
if os.path.exists(CACHE_DB):
    try:
        os.remove(CACHE_DB)
    except OSError:
        pass

# Initialize DB
conn = sqlite3.connect(CACHE_DB)
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS api_cache (
        url TEXT,
        params TEXT,
        response TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (url, params)
    )
""")
cursor.execute("""
    CREATE TABLE IF NOT EXISTS request_log (
        timestamp REAL
    )
""")
conn.commit()

def save_cache(url, params, data):
    params_str = json.dumps(params, sort_keys=True) if params else "{}"
    response_str = json.dumps(data)
    cursor.execute(
        "INSERT OR REPLACE INTO api_cache (url, params, response) VALUES (?, ?, ?)",
        (url, params_str, response_str)
    )

# 1. Sessions by Year
session_2023 = [
    {
        "meeting_key": 1200,
        "session_key": 9000,
        "year": 2023,
        "country_name": "Bahrain",
        "location": "Sakhir",
        "circuit_short_name": "Bahrain",
        "meeting_name": "Bahrain Grand Prix",
        "session_name": "Race",
        "date_start": "2023-03-05T15:00:00+00:00",
        "date_end": "2023-03-05T17:00:00+00:00"
    }
]

# We will only cache 2023 to keep it simple and clean
save_cache("sessions", {"year": 2023}, session_2023)
save_cache("sessions", {"year": 2024}, [])
save_cache("sessions", {"year": 2025}, [])
save_cache("sessions", {"year": 2026}, [])

# 2. Sessions by meeting_key
save_cache("sessions", {"meeting_key": 1200}, session_2023)

# 3. Drivers Catalog for Bahrain 2023 (Session 9000)
# We only return Hamilton (44) so he is selected as the default driver
drivers_9000 = [
    {
        "driver_number": 44,
        "full_name": "Lewis Hamilton",
        "team_name": "Mercedes",
        "name_acronym": "HAM",
        "session_key": 9000
    }
]
save_cache("drivers", {"session_key": 9000}, drivers_9000)
save_cache("drivers", {"session_key": 9000, "driver_number": 44}, drivers_9000)

# 4. Laps for Lewis Hamilton (Session 9000, Driver 44)
laps_44 = []
start_time = datetime.fromisoformat("2023-03-05T15:01:30+00:00")
for lap_num in range(1, 15):
    lap_dur = 94.5 + math.sin(lap_num) * 0.8
    laps_44.append({
        "lap_number": lap_num,
        "lap_duration": round(lap_dur, 3),
        "st_speed": round(295.0 + math.cos(lap_num) * 5, 1),
        "i1_speed": round(238.0 + math.sin(lap_num) * 3, 1),
        "i2_speed": round(268.0 - math.cos(lap_num) * 4, 1),
        "date_start": (start_time + timedelta(seconds=lap_num * 95)).isoformat()
    })
save_cache("laps", {"session_key": 9000, "driver_number": 44}, laps_44)

# 5. Weather for Session 9000
weather_9000 = [
    {
        "air_temperature": 24.5,
        "track_temperature": 32.8,
        "humidity": 41.2,
        "wind_speed": 2.8,
        "rainfall": 0
    }
]
save_cache("weather", {"session_key": 9000}, weather_9000)

# 6. Car Telemetry Data for Hamilton (Session 9000, Driver 44)
# Generate a series of 360 points to simulate a complete lap
car_data_44 = []
base_time = datetime.fromisoformat("2023-03-05T15:05:00+00:00")
for i in range(360):
    t_sec = i * 0.25 # 4Hz sampling
    # Simulate a race track: corners and straights
    speed_factor = 0.5 * (1 + math.sin(t_sec / 10.0)) + 0.3 * math.cos(t_sec / 3.0)
    speed_factor = max(0.0, min(1.0, speed_factor))
    
    speed = 80.0 + speed_factor * 240.0 # 80 to 320 km/h
    rpm = 8500.0 + speed_factor * 4200.0 + math.sin(t_sec) * 300.0 # 8500 to 13000 RPM
    
    if speed_factor > 0.6:
        throttle = 100.0
        brake = 0.0
        n_gear = int(5 + speed_factor * 3) # Gear 5 to 8
        drs = 12 if speed_factor > 0.85 else 0
    elif speed_factor < 0.25:
        throttle = 0.0
        brake = 80.0
        n_gear = int(1 + speed_factor * 8) # Gear 1 to 3
        drs = 0
    else:
        throttle = (speed_factor - 0.25) / 0.35 * 100.0
        brake = 0.0
        n_gear = int(3 + speed_factor * 4) # Gear 3 to 6
        drs = 0

    car_data_44.append({
        "date": (base_time + timedelta(seconds=t_sec)).isoformat(),
        "rpm": int(rpm),
        "speed": int(speed),
        "throttle": int(throttle),
        "brake": int(brake),
        "n_gear": n_gear,
        "drs": drs
    })
    
# Save for the default parameters queried by the application
save_cache("car_data", {
    "session_key": 9000, 
    "driver_number": 44,
    "date>=": "2023-03-05T15:00:00+00:00",
    "date<=": "2023-03-05T17:00:00+00:00"
}, car_data_44)

conn.commit()
conn.close()
print("Mock openf1_cache.db generated successfully with default track/driver telemetry data!")
