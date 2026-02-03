import os
from pypdf import PdfReader

def extract_text_from_file(file_path: str) -> str:
    """
    Extracts text from a file based on its extension.
    Supports .txt and .pdf.
    """
    if not os.path.exists(file_path):
        return f"[Error: File not found {file_path}]"

    _, ext = os.path.splitext(file_path)
    ext = ext.lower()

    try:
        if ext == ".pdf":
            reader = PdfReader(file_path)
            text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            return text
        else:
            # Default to text file
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    return f.read()
            except UnicodeDecodeError:
                with open(file_path, "r", encoding="latin-1") as f:
                    return f.read()
    except Exception as e:
        return f"[Error reading file {os.path.basename(file_path)}: {e}]"
