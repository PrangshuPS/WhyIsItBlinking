from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import pandas as pd
import numpy as np
import pickle
import os

MODEL_PATH = "isolation_forest.pkl"
SCALER_PATH = "scaler.pkl"

FEATURES = ["rpm", "speed", "coolant_temp", 
            "throttle", "engine_load", "battery_voltage"]

def train_model(df: pd.DataFrame):
    df_clean = df[FEATURES].dropna()
    if len(df_clean) < 50:
        print("Not enough data to train yet")
        return None, None
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(df_clean)
    
    model = IsolationForest(
        contamination=0.05,  # expects 5% anomalies
        random_state=42
    )
    model.fit(X_scaled)
    
    # Save model
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    with open(SCALER_PATH, "wb") as f:
        pickle.dump(scaler, f)
    
    print("Model trained and saved")
    return model, scaler

def predict_anomaly(data: dict):
    # Rule-based fallback if no model yet
    if not os.path.exists(MODEL_PATH):
        return rule_based_check(data)
    
    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)
    with open(SCALER_PATH, "rb") as f:
        scaler = pickle.load(f)
    
    values = [[data.get(f, 0) or 0 for f in FEATURES]]
    scaled = scaler.transform(values)
    prediction = model.predict(scaled)
    
    # -1 = anomaly, 1 = normal
    return prediction[0] == -1

def rule_based_check(data: dict):
    # Simple threshold rules as fallback
    flags = []
    if data.get("coolant_temp", 0) > 100:
        flags.append("High coolant temp")
    if data.get("rpm", 0) > 6500:
        flags.append("RPM overrev")
    if data.get("battery_voltage", 14) < 11.5:
        flags.append("Low battery voltage")
    if data.get("engine_load", 0) > 95:
        flags.append("Max engine load")
    return len(flags) > 0, flags