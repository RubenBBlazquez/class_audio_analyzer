import sqlite3
import os
from typing import Optional

# Compute absolute path to config/audio_analyzer.db based on project structure
# database_manager.py is in /app/
# we want /config/audio_analyzer.db
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
DB_NAME = os.path.join(BASE_DIR, "app", "config", "audio_analyzer.db")

print(f"DEBUG: DB_NAME set to: {DB_NAME}")

def init_db():
    # Ensure directory exists
    os.makedirs(os.path.dirname(DB_NAME), exist_ok=True)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Transcriptions Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transcriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            audio_filename TEXT NOT NULL,
            subject_folder TEXT,
            transcription_file_path TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Summarizations Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS summarizations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transcription_id INTEGER,
            theme TEXT,
            objective TEXT,
            mandatory_rules TEXT,
            summary_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (transcription_id) REFERENCES transcriptions (id)
        )
    ''')

    # Check if mandatory_rules column exists (for migration)
    cursor.execute("PRAGMA table_info(summarizations)")
    columns = [info[1] for info in cursor.fetchall()]
    if 'mandatory_rules' not in columns:
        cursor.execute('ALTER TABLE summarizations ADD COLUMN mandatory_rules TEXT')

    conn.commit()
    conn.close()

def log_transcription(audio_filename: str, subject_folder: Optional[str], transcription_file_path: str) -> int:
    """
    Logs a transcription record and returns its ID.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO transcriptions (audio_filename, subject_folder, transcription_file_path)
        VALUES (?, ?, ?)
    ''', (audio_filename, subject_folder, transcription_file_path))

    transcription_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return transcription_id

def log_summarization(transcription_id: int, theme: str, objective: str, summary_text: str, mandatory_rules: str = None) -> int:
    """
    Logs a summarization record linked to a transcription.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO summarizations (transcription_id, theme, objective, summary_text, mandatory_rules)
        VALUES (?, ?, ?, ?, ?)
    ''', (transcription_id, theme, objective, summary_text, mandatory_rules))

    summarization_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return summarization_id

def get_transcription_by_filename(audio_filename: str):
    """
    Finds a transcription record by audio filename.
    Returns the row (id, audio_filename, ...) or None.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM transcriptions WHERE audio_filename = ? ORDER BY created_at DESC LIMIT 1', (audio_filename,))
    row = cursor.fetchone()
    conn.close()
    return row

def get_recent_transcriptions(limit=10):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Left join to check for summary existence
    # Also fetching theme to make selector more descriptive if available
    cursor.execute('''
        SELECT t.id, t.audio_filename, t.subject_folder, t.transcription_file_path, t.created_at,
               s.theme, s.objective, s.mandatory_rules
        FROM transcriptions t
        LEFT JOIN summarizations s ON t.id = s.transcription_id
        ORDER BY t.created_at DESC 
        LIMIT ?
    ''', (limit,))
    rows = cursor.fetchall()
    conn.close()

    # Return formatted strings for dropdown
    # Format: "[Date] Subject - Filename (Theme: ...)"
    formatted = []
    for row in rows:
        # row: 0=id, 1=filename, 2=subject, 3=path, 4=date, 5=theme, 6=objective, 7=mandatory_rules
        date_str = row[4]
        filename = row[1]
        subject = row[2] if row[2] else "General"
        theme = f" | {row[5]}" if row[5] else ""

        display_str = f"{row[0]}: [{date_str}] {subject} - {filename}{theme}"
        formatted.append(display_str)

    return formatted, rows

def get_transcription_details(record_str):
    if not record_str:
        return None
    try:
        record_id = int(record_str.split(":")[0])
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        # Get transcription info
        cursor.execute("SELECT * FROM transcriptions WHERE id=?", (record_id,))
        t_row = cursor.fetchone()

        # Get associated summary info (if any)
        cursor.execute("SELECT * FROM summarizations WHERE transcription_id=? ORDER BY created_at DESC LIMIT 1", (record_id,))
        s_row = cursor.fetchone()

        conn.close()

        # Structure: (audio_path, subject, theme, objective, summary_text)
        # Note: audio_path might strictly be the filename stored, we might need to assume location or just fill text fields.
        # If the file still exists in the upload temp (unlikely) or original path is absolute.
        # For this feature, we mostly want to recall the context (Subject, Theme, Objective) and maybe the result.

        if t_row:
            subject = t_row[2] # subject_folder
            # Attempt to reconstruct audio path if possible, but Gradio Audio input expects a temp file or URL.
            # We probably can't easily pre-fill the Audio component with a local server path unless allowed.
            # But we can fill text fields.

            theme = ""
            objective = ""
            summary = ""
            mandatory_rules = ""
            if s_row:
                # s_row structure is id, transcription_id, theme, objective, mandatory_rules, summary_text, created_at
                # But wait, I changed the CREATE TABLE, but s_row depends on SELECT *
                # Since I'm doing SELECT *, I should rely on column names or specific indices matching the table schema.
                # However, if existing rows don't have mandatory_rules, retrieving them might be tricky if I rely on indices and the order changed or if using row_factory.
                # SQLite usually appends new columns at the end when using ALTER TABLE.
                # So existing columns indices are preserved. mandatory_rules will be at the end (before or after existing cols depending on when I added it relative to others?)
                # Actually, I added it in CREATE TABLE between objective and summary_text, but ALTER TABLE adds to the end.
                # So for new table: id, t_id, theme, obj, mandatory, summary, created
                # For altered table: id, t_id, theme, obj, summary, created, mandatory

                # To be safe, I should select by name or handle indices carefully.
                # Let's check column names.
                columns = [description[0] for description in cursor.description]
                s_dict = dict(zip(columns, s_row))

                theme = s_dict.get('theme', "")
                objective = s_dict.get('objective', "")
                summary = s_dict.get('summary_text', "")
                mandatory_rules = s_dict.get('mandatory_rules', "")

            return subject, theme, objective, mandatory_rules, summary

    except Exception as e:
        print(f"Error fetching details: {e}")
        return None

# Initialize DB on import if not exists
if not os.path.exists(DB_NAME):
    init_db()
else:
    # Ensure tables exist even if file exists
    init_db()
