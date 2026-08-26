import os
import sqlite3
import datetime
from pathlib import Path

# Set dummy env vars to allow db/logger to load safely
os.environ["THINKING_DB"] = "SharedData/test_db.sqlite3"

from db import init_db, get_db_path, get_all_historical_timestamps
from anomaly_model import predict_anomaly

def inject_test_data():
    db_file = get_db_path()
    
    # Start with a fresh test database
    if db_file.exists():
        db_file.unlink()
        
    init_db()
    
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    now = datetime.datetime.now()
    
    print(f"Injecting 5 days of normal routine data into {db_file}...")
    print("Routine: Resident is seen regularly every ~2 hours between 08:00 and 22:00.")
    
    # Generate 5 days of history
    for day_offset in range(5, 0, -1):
        for hour in range(8, 23, 2): 
            dt = now - datetime.timedelta(days=day_offset)
            dt = dt.replace(hour=hour, minute=15, second=0, microsecond=0)
            
            datestamp = dt.strftime("%Y-%m-%d")
            timestamp = dt.strftime("%H:%M:%S")
            
            cursor.execute(
                "INSERT INTO routine_logs (datestamp, timestamp, resident_in_picture, multiple_people, status) VALUES (?, ?, ?, ?, ?)",
                (datestamp, timestamp, "yes", "no", "ok")
            )
            
    conn.commit()
    conn.close()
    print("Data injection complete.\n")

def test_predictions():
    historical_dts = get_all_historical_timestamps()
    print(f"Loaded {len(historical_dts)} historical timestamps for training.")
    
    now = datetime.datetime.now()
    
    print("\n--- TEST 0: Normal Absence ---")
    test_time_0 = now.replace(hour=12, minute=0)
    hours_missing_0 = 1.5
    print(f"Scenario: It is 12:00. Resident is missing for {hours_missing_0} hours.")
    is_anomaly = predict_anomaly(historical_dts, test_time_0, hours_missing_0)
    print(f"ML Prediction: {'🚨 ANOMALY' if is_anomaly else '✅ NORMAL'}")

    print("\n--- TEST 1: Normal Daytime Absence ---")
    test_time_1 = now.replace(hour=14, minute=0)
    hours_missing_1 = 3.0
    print(f"Scenario: It is 14:00. Resident is missing for {hours_missing_1} hours.")
    is_anomaly = predict_anomaly(historical_dts, test_time_1, hours_missing_1)
    print(f"ML Prediction: {'🚨 ANOMALY' if is_anomaly else '✅ NORMAL'}")
    
    print("\n--- TEST 2: Severe Daytime Absence ---")
    test_time_2 = now.replace(hour=19, minute=0)
    hours_missing_2 = 11.0
    print(f"Scenario: It is 19:00. Resident is missing for {hours_missing_2} hours.")
    is_anomaly = predict_anomaly(historical_dts, test_time_2, hours_missing_2)
    print(f"ML Prediction: {'🚨 ANOMALY' if is_anomaly else '✅ NORMAL'}")

if __name__ == "__main__":
    inject_test_data()
    test_predictions()
