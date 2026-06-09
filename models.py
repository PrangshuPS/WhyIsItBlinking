from sqlalchemy import Column, Integer, Float, Boolean, DateTime, Text
from sqlalchemy.sql import func
from database import Base

class SensorReading(Base):
    __tablename__ = "sensor_readings"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=func.now())
    rpm = Column(Float, nullable=True)
    speed = Column(Float, nullable=True)
    coolant_temp = Column(Float, nullable=True)
    throttle = Column(Float, nullable=True)
    engine_load = Column(Float, nullable=True)
    fuel_pressure = Column(Float, nullable=True)
    intake_temp = Column(Float, nullable=True)
    battery_voltage = Column(Float, nullable=True)
    anomaly = Column(Boolean, default=False)

class Anomaly(Base):
    __tablename__ = "anomalies"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=func.now())
    parameter = Column(Text)
    value = Column(Float)
    message = Column(Text)