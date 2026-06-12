from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os
import time
from sqlalchemy.exc import OperationalError

load_dotenv()

DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME')

use_mysql = all([DB_HOST, DB_USER, DB_NAME])

if use_mysql:
    DB_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT or 3306}/{DB_NAME}"
    engine = create_engine(DB_URL)
    
    # Retry logic to wait for MySQL/MariaDB to start up
    print("Checking database connection...")
    connected = False
    for attempt in range(1, 31):
        try:
            with engine.connect() as conn:
                pass
            print("Database connection established!")
            connected = True
            break
        except OperationalError as e:
            print(f"Database connection attempt {attempt}/30 failed: {e}. Retrying in 2 seconds...")
            time.sleep(2)
            
    if not connected:
        print("Warning: Could not connect to MariaDB/MySQL after 30 attempts. Falling back to local SQLite database.")
        DB_URL = "sqlite:///./vehicle_telemetry.db"
        engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
else:
    print("No MySQL/MariaDB credentials configured. Using local SQLite database.")
    DB_URL = "sqlite:///./vehicle_telemetry.db"
    engine = create_engine(DB_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()