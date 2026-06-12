from fastapi import FastAPI, Depends
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
import pandas as pd
import threading
import time

from database import engine, get_db, Base
from models import SensorReading, Anomaly
from obd_reader import (
    fetch_data,
    get_driver_options,
    get_openf1_state,
    get_track_options,
    select_openf1_source,
)
from ml_model import predict_anomaly, train_model
from openf1_client import get_historical_analysis

Base.metadata.create_all(bind=engine)

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

latest_reading = {}

# ── Background data collector ──────────────────────────────
def collect_data():
    global latest_reading
    counter = 0
    while True:
        try:
            data = fetch_data()
            if not data:
                time.sleep(2)
                continue
            is_anomaly = predict_anomaly(data)
            data["anomaly"] = bool(is_anomaly)
            latest_reading = data

            db = next(get_db())
            try:
                reading = SensorReading(**data)
                db.add(reading)
                db.commit()

                if is_anomaly:
                    anomaly = Anomaly(
                        parameter="multiple",
                        value=data.get("rpm", 0),
                        message=f"Anomaly detected: RPM={data.get('rpm')} "
                                f"Temp={data.get('coolant_temp')}"
                    )
                    db.add(anomaly)
                    db.commit()
            finally:
                db.close()

            # Retrain model every 200 readings
            counter += 1
            if counter % 200 == 0:
                df = pd.read_sql("SELECT * FROM sensor_readings", 
                                  engine)
                train_model(df)

        except Exception as e:
            print(f"Collection error: {e}")
        time.sleep(2)

thread = threading.Thread(target=collect_data, daemon=True)
thread.start()

# ── API Routes ─────────────────────────────────────────────

@app.get("/")
def serve_dashboard():
    with open("static/index.html", encoding="utf-8") as f:
        return HTMLResponse(f.read())
    # with open("static/index.html") as f:
    #     return HTMLResponse(f.read())

@app.get("/api/latest")
def get_latest():
    return latest_reading

@app.get("/api/history")
def get_history(limit: int = 50, db: Session = Depends(get_db)):
    rows = db.query(SensorReading)\
             .order_by(SensorReading.timestamp.desc())\
             .limit(limit).all()
    return [
        {
            "timestamp": str(r.timestamp),
            "rpm": r.rpm,
            "speed": r.speed,
            "coolant_temp": r.coolant_temp,
            "throttle": r.throttle,
            "engine_load": r.engine_load,
            "battery_voltage": r.battery_voltage,
            "anomaly": r.anomaly
        }
        for r in reversed(rows)
    ]

@app.get("/api/anomalies")
def get_anomalies(db: Session = Depends(get_db)):
    rows = db.query(Anomaly)\
             .order_by(Anomaly.timestamp.desc())\
             .limit(20).all()
    return [
        {
            "timestamp": str(r.timestamp),
            "parameter": r.parameter,
            "value": r.value,
            "message": r.message
        }
        for r in rows
    ]

@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    df = pd.read_sql("SELECT * FROM sensor_readings "
                     "ORDER BY timestamp DESC LIMIT 500", engine)
    if df.empty:
        return {}
    return {
        "avg_rpm": round(df["rpm"].mean(), 1),
        "max_rpm": round(df["rpm"].max(), 1),
        "avg_temp": round(df["coolant_temp"].mean(), 1),
        "max_temp": round(df["coolant_temp"].max(), 1),
        "total_readings": len(df),
        "anomaly_count": int(df["anomaly"].sum())
    }


@app.get("/api/openf1/tracks")
def openf1_tracks():
    return {"tracks": get_track_options()}


@app.get("/api/openf1/drivers")
def openf1_drivers(meeting_key: int):
    return {"drivers": get_driver_options(meeting_key)}


@app.get("/api/openf1/analysis")
def openf1_analysis(meeting_key: int, driver_number: int):
    return get_historical_analysis(meeting_key, driver_number)


@app.post("/api/openf1/select")
def openf1_select(meeting_key: int, driver_number: int):
    return select_openf1_source(meeting_key, driver_number)


@app.get("/api/openf1/state")
def openf1_state():
    return get_openf1_state()


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)