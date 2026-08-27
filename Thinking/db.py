import os
import time
import json
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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS current_status (
                location TEXT PRIMARY KEY,
                status TEXT NOT NULL DEFAULT 'unknown',
                source TEXT,
                detail TEXT,
                audio_url TEXT,
                updated_at TEXT NOT NULL,
                danger_sources TEXT DEFAULT '[]'
            )
        """)

        try:
            conn.execute("ALTER TABLE current_status ADD COLUMN danger_sources TEXT DEFAULT '[]'")
        except sqlite3.OperationalError:
            pass


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

def get_distinct_locations():
    with sqlite3.connect(get_db_path()) as conn:
        cursor = conn.execute(
            "SELECT DISTINCT location FROM routine_logs WHERE resident_in_picture = 'yes' AND location IS NOT NULL AND location != 'Unknown'"
        )
        rows = cursor.fetchall()

    return [row[0] for row in rows]

def get_hours_since_resident_last_seen_at(location):
    with sqlite3.connect(get_db_path()) as conn:
        cursor = conn.execute(
            "SELECT datestamp, timestamp FROM routine_logs WHERE resident_in_picture = 'yes' AND location = ? ORDER BY id DESC LIMIT 1",
            (location,)
        )
        row = cursor.fetchone()

    if not row:
        return -1.0

    try:
        last_time = datetime.datetime.strptime(f"{row[0]} {row[1]}", "%Y-%m-%d %H:%M:%S")
        now = datetime.datetime.now()
        return (now - last_time).total_seconds() / 3600.0
    except Exception as e:
        log.error(f"Error parsing timestamp for location '{location}': {e}")
        return -1.0

def get_all_historical_timestamps_for(location):
    with sqlite3.connect(get_db_path()) as conn:
        cursor = conn.execute(
            "SELECT datestamp, timestamp FROM routine_logs WHERE resident_in_picture = 'yes' AND location = ?",
            (location,)
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

VISUAL_SOURCES = {"detection", "inactive_posture", "routine_anomaly"}

def update_current_status(location, status, source, detail=None, audio_url=None):
    updated_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with sqlite3.connect(get_db_path()) as conn:
        cursor = conn.execute("SELECT status, danger_sources FROM current_status WHERE location = ?", (location,))
        row = cursor.fetchone()

        danger_sources = set()
        if row:
            try:
                danger_sources = set(json.loads(row[1])) if row[1] else set()
            except (json.JSONDecodeError, TypeError):
                danger_sources = set()

        # Update per-source danger tracking
        if status == "danger":
            danger_sources.add(source)
        else:
            # Each visual source can only clear its own danger flag
            if source in VISUAL_SOURCES:
                danger_sources.discard(source)
            elif source == "stt":
                # Voice confirmation clears ALL danger sources
                danger_sources.clear()

        # Overall status stays 'danger' until ALL sources are resolved
        effective_status = "danger" if danger_sources else status
        danger_sources_json = json.dumps(sorted(danger_sources))

        conn.execute(
            """
            INSERT INTO current_status (location, status, source, detail, audio_url, updated_at, danger_sources)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(location) DO UPDATE SET
                status = excluded.status,
                source = excluded.source,
                detail = excluded.detail,
                audio_url = COALESCE(excluded.audio_url, current_status.audio_url),
                updated_at = excluded.updated_at,
                danger_sources = excluded.danger_sources
            """,
            (location, effective_status, source, detail, audio_url, updated_at, danger_sources_json)
        )
        conn.commit()

def get_current_status(location, clear_audio=True):
    with sqlite3.connect(get_db_path()) as conn:
        cursor = conn.execute(
            "SELECT status, source, detail, audio_url, updated_at, danger_sources FROM current_status WHERE location = ?",
            (location,)
        )
        row = cursor.fetchone()

        if not row:
            return None

        try:
            danger_sources = json.loads(row[5]) if row[5] else []
        except (json.JSONDecodeError, TypeError):
            danger_sources = []

        result = {
            "status": row[0],
            "source": row[1],
            "detail": row[2],
            "audio_url": row[3],
            "updated_at": row[4],
            "danger_sources": danger_sources
        }

        # Clear audio_url after read so it only plays once
        if row[3] and clear_audio:
            conn.execute(
                "UPDATE current_status SET audio_url = NULL WHERE location = ?",
                (location,)
            )
            conn.commit()

        return result
