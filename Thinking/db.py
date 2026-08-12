import sqlite3
import datetime
import os


def init_db():
    db_path = os.environ.get("THINKING_DB", None)
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                datestamp TEXT,
                timestamp TEXT,
                entry TEXT
            )
        """)

def write_conversation(entry):
    db_path = os.environ.get("THINKING_DB", None)

    datestamp = datetime.datetime.now().strftime("%Y-%m-%d")
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO conversations (datestamp, timestamp, entry) VALUES (?, ?, ?)",
            (datestamp, timestamp, entry)
        )

def get_conversations():
    db_path = os.environ.get("THINKING_DB", None)

    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(
            "SELECT timestamp, entry FROM conversations WHERE datestamp = ?", 
            (today,)
        )
        rows = cursor.fetchall()
    
    if not rows:
        return "No conversations yet for today - this is the first interaction."
    
    return "\n".join([f"{row[0]} - {row[1]}" for row in rows])