import os
import logging
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError


class DriveService:
    # If modifying these scopes, delete the file token.json.
    SCOPES = ['https://www.googleapis.com/auth/drive.file']


    def __init__(self):
        self.creds = None
        self.service = None
        self.folder_id = os.environ.get("GOOGLE_DRIVE_FOLDER_ID")

        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.project_root = os.path.abspath(os.path.join(base_dir, ".."))
        self.config_dir = os.path.join(self.project_root, "config")

        # Paths for different auth methods
        # Updated to match user provided filename: client_secrets_drive.json
        self.oauth_secrets_path = os.path.join(self.config_dir, "client_secrets_drive.json")
        self.user_token_path = os.path.join(self.config_dir, "token.json")
        self.service_account_path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON") or os.path.join(self.config_dir,
                                                                                                  "drive_service_account.json")

    @property
    def enabled(self):
        """Checks if Drive integration is possible (Config exists)."""
        has_auth = (os.path.exists(self.oauth_secrets_path) or
                    os.path.exists(self.user_token_path) or
                    os.path.exists(self.service_account_path))
        return bool(self.folder_id and has_auth)

    def authenticate(self):
        """
        Attempts User Auth (OAuth) first for Personal Drives.
        Falls back to Service Account if OAuth secrets are missing.
        """
        self.creds = None

        # 1. PARAM: Try User OAuth (Best for Personal Drives)
        # Check if we already have a valid user token
        if os.path.exists(self.user_token_path):
            try:
                self.creds = Credentials.from_authorized_user_file(self.user_token_path, self.SCOPES)
            except Exception as e:
                logging.warning(f"Invalid token.json, will regenerate: {e}")

        # If no valid creds yet, lets log the user in
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                except Exception:
                    self.creds = None  # Force re-login

            # If still no creds, try to trigger browser flow if secrets exist
            if not self.creds and os.path.exists(self.oauth_secrets_path):
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(self.oauth_secrets_path, self.SCOPES)
                    print("Attempting to open browser for Google Drive authentication...")
                    # Desktop/Installed apps support dynamic ports with http://localhost
                    self.creds = flow.run_local_server(port=0)
                    # Save the credentials for the next run
                    with open(self.user_token_path, 'w') as token:
                        token.write(self.creds.to_json())
                except Exception as e:
                    logging.error(f"OAuth Login failed: {e}")

        # 2. PARAM: Fallback to Service Account (Only for Shared Drives / Entprise)
        if not self.creds and os.path.exists(self.service_account_path):
            try:
                logging.info("Falling back to Service Account authentication...")
                self.creds = service_account.Credentials.from_service_account_file(
                    self.service_account_path, scopes=self.SCOPES
                )
            except Exception as e:
                logging.error(f"Service Account auth failed: {e}")

        if self.creds:
            self.service = build('drive', 'v3', credentials=self.creds)
            return True

        logging.error("No valid authentication method found (Missing client_secrets.json or service_account.json)")
        return False

    def _handle_http_error(self, error):
        """Parses HttpError to give actionable advice."""
        if error.resp.status == 403:
            reason = error.error_details[0].get('reason') if error.error_details else "unknown"
            if reason == 'accessNotConfigured':
                logging.error("CRITICAL: Google Drive API is NOT enabled for this project.")
                logging.error(f"Enable it here: https://console.developers.google.com/apis/api/drive.googleapis.com/overview")
            elif reason == 'storageQuotaExceeded':
                logging.error("CRITICAL: Storage quota exceeded. Using User Authentication allows you to use your personal quota.")
        logging.error(f"Google Drive API Error: {error}")

    def _find_subfolder(self, parent_id, folder_name):
        try:
            safe_name = folder_name.replace("'", "\\'")
            query = f"mimeType='application/vnd.google-apps.folder' and name='{safe_name}' and '{parent_id}' in parents and trashed=false"

            results = self.service.files().list(
                q=query,
                fields="files(id, name)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()

            files = results.get('files', [])
            return files[0]['id'] if files else None
        except HttpError as e:
            self._handle_http_error(e)
            return None
        except Exception as e:
            logging.error(f"Error finding folder '{folder_name}': {e}")
            return None

    def _create_subfolder(self, parent_id, folder_name):
        try:
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_id]
            }
            file = self.service.files().create(
                body=file_metadata,
                fields='id',
                supportsAllDrives=True
            ).execute()
            return file.get('id')
        except HttpError as e:
            self._handle_http_error(e)
            return None
        except Exception as e:
            logging.error(f"Error creating folder '{folder_name}': {e}")
            return None

    def _ensure_subfolder(self, parent_id, folder_name):
        if not parent_id: return None
        found = self._find_subfolder(parent_id, folder_name)
        if found: return found
        return self._create_subfolder(parent_id, folder_name)

    def upload_file(self, file_path: str, custom_folder_id: str = None, subfolder_name: str = None, fixed_subfolder: str = None):
        if not self.service:
            if not self.authenticate():
                return None, "Drive authentication failed. Check logs for details."

        # 1. Start with Root
        target_folder_id = self.folder_id
        if not target_folder_id:
            return None, "No Root Folder ID configured in .env"

        # 2. Determine Subfolder Path
        # Priority: Custom Folder Input OVERRIDES Theme/Subfolder Name
        folder_path_string = custom_folder_id if custom_folder_id else subfolder_name

        current_parent_id = target_folder_id

        if folder_path_string:
            # Handle nested paths (e.g. "Year 1/Subject A")
            # Convert to list of folder names
            folder_names = folder_path_string.replace('\\', '/').split('/')

            for name in folder_names:
                name = name.strip()
                if not name: continue

                # Check/Create this level
                next_id = self._ensure_subfolder(current_parent_id, name)
                if next_id:
                    current_parent_id = next_id
                else:
                    return None, f"Failed to resolve/create folder '{name}' inside parent path"

        # 3. Fixed Subfolder (e.g. "resumes" or "transcriptions")
        if fixed_subfolder:
             # This creates a folder like "resumes" inside the resolved destination
             resolved_fixed = self._ensure_subfolder(current_parent_id, fixed_subfolder)
             if resolved_fixed:
                 current_parent_id = resolved_fixed
             else:
                 return None, f"Failed to ensure fixed subfolder '{fixed_subfolder}'"

        target_folder_id = current_parent_id

        try:
            file_metadata = {
                'name': os.path.basename(file_path),
                'parents': [target_folder_id]
            }
            media = MediaFileUpload(file_path, resumable=True)

            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink',
                supportsAllDrives=True
            ).execute()

            return file.get('webViewLink'), None
        except Exception as e:
            return None, f"Upload error: {e}"
