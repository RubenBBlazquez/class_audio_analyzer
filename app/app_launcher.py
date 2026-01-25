import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
from app.interface.layout import create_interface

if __name__ == "__main__":
    load_dotenv("config/.env")

    app = create_interface()
    app.launch(server_name="0.0.0.0", server_port=7860)
