import os
import time
import sqlite3
import datetime
from pathlib import Path
from logger import get_logger


log = get_logger("thinking")

def get_db_path():
    db_path = os.environ.get("THINKING_DB", None)
    if not db_path:
        log.error("THINKING_DB environment variable is not set.")
        raise ValueError("THINKING_DB environment variable is not set.")

    full_path = Path(__file__).resolve().parent.parent / db_path
    full_path.parent.mkdir(parents=True, exist_ok=True)

    return Path(__file__).resolve().parent.parent / db_path

def init_db():

    with sqlite3.connect(get_db_path()) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                datestamp TEXT,
                timestamp TEXT,
                entry TEXT
            )
        """)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS routine_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                datestamp TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                resident_in_picture TEXT NOT NULL,
                multiple_people TEXT NOT NULL,
                status TEXT NOT NULL,
                location TEXT
            )
            """
        )
        
        try:
            conn.execute("ALTER TABLE routine_logs ADD COLUMN location TEXT")
        except sqlite3.OperationalError:
            pass

        conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                datestamp TEXT,
                timestamp TEXT,
                event_type TEXT,
                details TEXT
            )
        """)


def write_conversation(entry):
    datestamp = datetime.datetime.now().strftime("%Y-%m-%d")
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    
    with sqlite3.connect(get_db_path()) as conn:
        conn.execute(
            "INSERT INTO conversations (datestamp, timestamp, entry) VALUES (?, ?, ?)",
            (datestamp, timestamp, entry)
        )

def write_routine_log(resident_in_picture, multiple_people, status, location="Unknown"):
    datestamp = time.strftime("%Y-%m-%d")
    timestamp = time.strftime("%H:%M:%S")

    with sqlite3.connect(get_db_path()) as conn:
        conn.execute(
            """
            INSERT INTO routine_logs (datestamp, timestamp, resident_in_picture, multiple_people, status, location)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (datestamp, timestamp, resident_in_picture, multiple_people, status, location)
        )

def write_event(event_type, details):
    datestamp = datetime.datetime.now().strftime("%Y-%m-%d")
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    
    with sqlite3.connect(get_db_path()) as conn:
        conn.execute(
            "INSERT INTO events (datestamp, timestamp, event_type, details) VALUES (?, ?, ?, ?)",
            (datestamp, timestamp, event_type, details)
        )

def get_conversations():
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    with sqlite3.connect(get_db_path()) as conn:
        cursor = conn.execute(
            "SELECT timestamp, entry FROM conversations WHERE datestamp = ? ORDER BY id DESC LIMIT 3", 
            (today,)
        )
        rows = cursor.fetchall()
    
    if not rows:
        return "No conversations yet for today - this is the first interaction."
    
    rows.reverse()
    return "\n".join([f"{row[0]} - {row[1]}" for row in rows])

def get_seconds_since_last_conversation():
    with sqlite3.connect(get_db_path()) as conn:
        cursor = conn.execute(
            "SELECT datestamp, timestamp FROM conversations ORDER BY id DESC LIMIT 1"
        )
        row = cursor.fetchone()
    
    if not row:
        return 999999
        
    last_datestamp_str = row[0]
    last_timestamp_str = row[1]
    try:
        last_time = datetime.datetime.strptime(f"{last_datestamp_str} {last_timestamp_str}", "%Y-%m-%d %H:%M:%S")
        now = datetime.datetime.now()
        return (now - last_time).total_seconds()
    except Exception as e:
        log.error(f"Error parsing timestamp: {e}")
        return 999999

def get_all_historical_timestamps():
    with sqlite3.connect(get_db_path()) as conn:
        cursor = conn.execute(
            "SELECT datestamp, timestamp FROM routine_logs WHERE resident_in_picture = 'yes'"
        )
        rows = cursor.fetchall()
        
    datetimes = []
    for row in rows:
        try:
            dt = datetime.datetime.strptime(f"{row[0]} {row[1]}", "%Y-%m-%d %H:%M:%S")
            datetimes.append(dt)
        except Exception as e:
            continue
            
    return datetimes

def get_hours_since_resident_last_seen():
    with sqlite3.connect(get_db_path()) as conn:
        cursor = conn.execute(
            "SELECT datestamp, timestamp FROM routine_logs WHERE resident_in_picture = 'yes' ORDER BY id DESC LIMIT 1"
        )
        row = cursor.fetchone()
        
    if not row:
        return -1.0 # Never seen
        
    try:
        last_time = datetime.datetime.strptime(f"{row[0]} {row[1]}", "%Y-%m-%d %H:%M:%S")
        now = datetime.datetime.now()
        return (now - last_time).total_seconds() / 3600.0
    except Exception as e:
        log.error(f"Error parsing timestamp: {e}")
        return -1.0
