# vehicle telemetry database - WhyisItBlinking

CREATE DATABASE vehicle_telemetry;
USE vehicle_telemetry;

CREATE TABLE sensor_readings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    rpm FLOAT,
    speed FLOAT,
    coolant_temp FLOAT,
    throttle FLOAT,
    engine_load FLOAT,
    fuel_pressure FLOAT,
    intake_temp FLOAT,
    battery_voltage FLOAT,
    anomaly BOOLEAN DEFAULT FALSE
);

CREATE TABLE anomalies (
    id INT AUTO_INCREMENT PRIMARY KEY,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    parameter TEXT,
    value FLOAT,
    message TEXT
);

select * from sensor_readings;