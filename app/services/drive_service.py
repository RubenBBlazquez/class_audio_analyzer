import os
import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

class DriveService:
    SCOPES = ['https://www.googleapis.com/auth/drive.file']

    def __init__(self):
        self.creds = None
        self.service = None
        self.folder_id = os.environ.get("GOOGLE_DRIVE_FOLDER_ID")

        # Check env var for path first
        env_service_path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
        if env_service_path and os.path.exists(env_service_path):
             self.service_account_path = env_service_path
        else:
             # Locate service account file: project_root/config/service_account.json
             base_dir = os.path.dirname(os.path.abspath(__file__))
             project_root = os.path.abspath(os.path.join(base_dir, "..", ".."))
             self.service_account_path = os.path.join(project_root, "config", "service_account.json")

        self.enabled = bool(os.path.exists(self.service_account_path) and self.folder_id)

    def authenticate(self):
        if not self.enabled:
            return False

        try:
            self.creds = service_account.Credentials.from_service_account_file(
                self.service_account_path, scopes=self.SCOPES
            )
            self.service = build('drive', 'v3', credentials=self.creds)
            return True
        except Exception as e:
            logging.error(f"Failed to authenticate with Google Drive: {e}")
            return False

    def upload_file(self, file_path: str):
        if not self.enabled:
            return None, "Drive sync disabled (missing config/service_account.json or GOOGLE_DRIVE_FOLDER_ID)"

        if not self.service:
            if not self.authenticate():
                return None, "Drive authentication failed"

        try:
            file_metadata = {
                'name': os.path.basename(file_path),
                'parents': [self.folder_id]
            }
            media = MediaFileUpload(file_path, resumable=True)

            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink'
            ).execute()

            return file.get('webViewLink'), None
        except Exception as e:
            return None, f"Upload error: {e}"
