import os
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

    db_folder = Path(__file__).resolve().parent.parent / "SharedData/db"
    db_folder.mkdir(parents=True, exist_ok=True)

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

def write_conversation(entry):
    datestamp = datetime.datetime.now().strftime("%Y-%m-%d")
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    
    with sqlite3.connect(get_db_path()) as conn:
        conn.execute(
            "INSERT INTO conversations (datestamp, timestamp, entry) VALUES (?, ?, ?)",
            (datestamp, timestamp, entry)
        )

def get_conversations():
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    with sqlite3.connect(get_db_path()) as conn:
        cursor = conn.execute(
            "SELECT timestamp, entry FROM conversations WHERE datestamp = ?", 
            (today,)
        )
        rows = cursor.fetchall()
    
    if not rows:
        return "No conversations yet for today - this is the first interaction."
    
    return "\n".join([f"{row[0]} - {row[1]}" for row in rows])