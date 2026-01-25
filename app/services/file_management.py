import os
import glob

# app/services/file_management.py
# Going up one level from 'services' gets us to 'app'
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRANSCRIPTIONS_DIR = os.path.join(BASE_DIR, "transcriptions")

def get_transcriptions_dir():
    return TRANSCRIPTIONS_DIR

def get_subjects():
    """Returns a list of subject folders in the transcriptions directory."""
    if not os.path.exists(TRANSCRIPTIONS_DIR):
        return []

    # List all subdirectories in TRANSCRIPTIONS_DIR
    subjects = [
        d for d in os.listdir(TRANSCRIPTIONS_DIR)
        if os.path.isdir(os.path.join(TRANSCRIPTIONS_DIR, d)) and d != "__pycache__"
    ]
    subjects.sort()
    return subjects

def get_html_files(subject):
    """Returns a list of HTML files for a given subject (recursive)."""
    if not subject:
        return []

    subject_path = os.path.join(TRANSCRIPTIONS_DIR, subject)

    html_files = []

    if os.path.exists(subject_path):
        # Recursive search for .html files
        files = glob.glob(os.path.join(subject_path, "**", "*.html"), recursive=True)
        # Convert to relative paths key for display and retrieval
        html_files = [os.path.relpath(f, subject_path) for f in files]

    return sorted(html_files)

def get_html_content(subject, filename):
    """Reads the content of an HTML file."""
    if not subject or not filename:
        return ""

    # Filename is expected to be a relative path from inside the subject folder
    full_path = os.path.join(TRANSCRIPTIONS_DIR, subject, filename)

    if os.path.exists(full_path):
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {e}"

    return "File not found."
