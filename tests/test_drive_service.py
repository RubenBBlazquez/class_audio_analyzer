import os
import pytest
from unittest.mock import MagicMock, patch
from app.services.drive_service import DriveService

@pytest.fixture
def mock_env_vars(monkeypatch):
    """Sets standard environment variables for tests."""
    monkeypatch.setenv("GOOGLE_DRIVE_FOLDER_ID", "test_folder_id")
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", "/tmp/fake_service_account.json")

class TestDriveService:

    @patch("app.services.drive_service.os.path.exists")
    def test_init_success(self, mock_exists, mock_env_vars):
        """Test initialization when config works."""
        mock_exists.return_value = True
        service = DriveService()
        assert service.enabled is True
        assert service.folder_id == "test_folder_id"
        assert service.service_account_path == "/tmp/fake_service_account.json"

    @patch("app.services.drive_service.os.path.exists")
    def test_init_missing_file(self, mock_exists, mock_env_vars):
        """Test initialization when service account file is missing."""
        mock_exists.return_value = False
        service = DriveService()
        assert service.enabled is False

    @patch("app.services.drive_service.os.path.exists")
    def test_init_missing_folder_id_env(self, mock_exists, monkeypatch):
        """Test initialization when folder ID is missing."""
        monkeypatch.delenv("GOOGLE_DRIVE_FOLDER_ID", raising=False)
        mock_exists.return_value = True
        service = DriveService()
        assert service.enabled is False

    @patch("app.services.drive_service.os.path.exists")
    @patch("app.services.drive_service.service_account.Credentials")
    @patch("app.services.drive_service.build")
    def test_authenticate_success(self, mock_build, mock_creds, mock_exists, mock_env_vars):
        """Test successful authentication falling back to Service Account."""

        # Configure os.path.exists to return False for user token/secrets, True for service account
        def side_effect(path):
            if "token.json" in str(path) or "client_secrets" in str(path):
                return False
            return True
        mock_exists.side_effect = side_effect

        service = DriveService()

        # Mock credentials and build return
        mock_creds_obj = MagicMock()
        mock_creds.from_service_account_file.return_value = mock_creds_obj
        mock_service_obj = MagicMock()
        mock_build.return_value = mock_service_obj

        result = service.authenticate()

        assert result is True
        assert service.service == mock_service_obj
        mock_creds.from_service_account_file.assert_called_with(
            "/tmp/fake_service_account.json", scopes=service.SCOPES
        )

    @patch("app.services.drive_service.os.path.exists")
    def test_authenticate_disabled(self, mock_exists):
        """Test authentication when service is disabled."""
        mock_exists.return_value = False
        service = DriveService()
        assert service.authenticate() is False

    @patch("app.services.drive_service.os.path.exists")
    @patch("app.services.drive_service.service_account.Credentials")
    @patch("app.services.drive_service.build")
    def test_authenticate_exception(self, mock_build, mock_creds, mock_exists, mock_env_vars):
        """Test authentication handling exceptions."""
        def side_effect(path):
            if "token.json" in str(path) or "client_secrets" in str(path):
                return False
            return True
        mock_exists.side_effect = side_effect

        service = DriveService()

        mock_creds.from_service_account_file.side_effect = Exception("Credentials error")

        result = service.authenticate()
        assert result is False
        assert service.service is None

    @patch("app.services.drive_service.os.path.exists")
    @patch("app.services.drive_service.MediaFileUpload")
    def test_upload_file_success(self, mock_media, mock_exists, mock_env_vars):
        """Test successful file upload."""
        mock_exists.return_value = True
        service = DriveService()

        # Manually set up authenticated state
        mock_service = MagicMock()
        service.service = mock_service
        service.authenticate = MagicMock(return_value=True)

        # Mock API response
        mock_create = mock_service.files.return_value.create
        mock_create.return_value.execute.return_value = {"id": "12345", "webViewLink": "http://gdrive/link"}

        link, error = service.upload_file("/path/to/test_file.txt")

        assert link == "http://gdrive/link"
        assert error is None

        # Verify call args
        mock_create.assert_called_once()
        _, kwargs = mock_create.call_args
        assert kwargs['body']['name'] == "test_file.txt"
        assert kwargs['body']['parents'] == ["test_folder_id"]

    @patch("app.services.drive_service.os.path.exists")
    @patch("app.services.drive_service.DriveService.authenticate") # Mock authenticate method directly
    def test_upload_file_disabled(self, mock_authenticate, mock_exists):
        """Test upload when disabled/auth fails."""
        mock_exists.return_value = False
        service = DriveService()

        # When disabled, authenticate returns False (or logic inside upload checks service)
        # Actually in new code: if not self.service: if not self.authenticate(): return None, "msg"
        mock_authenticate.return_value = False

        link, error = service.upload_file("file.txt")
        assert link is None
        # Check actual error message from new implementation
        assert "Drive authentication failed" in error

    @patch("app.services.drive_service.os.path.exists")
    def test_upload_file_auth_failure(self, mock_exists, mock_env_vars):
        """Test upload when auth fails."""
        mock_exists.return_value = True
        service = DriveService()

        # Mock auth failure
        service.authenticate = MagicMock(return_value=False)

        link, error = service.upload_file("file.txt")
        assert link is None
        assert "Drive authentication failed" in error

    @patch("app.services.drive_service.os.path.exists")
    @patch("app.services.drive_service.MediaFileUpload")
    def test_upload_api_error(self, mock_media, mock_exists, mock_env_vars):
        """Test upload when API call raises exception."""
        mock_exists.return_value = True
        service = DriveService()

        mock_service = MagicMock()
        service.service = mock_service
        service.authenticate = MagicMock(return_value=True)

        # Make execute raise an exception
        mock_service.files.return_value.create.return_value.execute.side_effect = Exception("API Error")

        link, error = service.upload_file("file.txt")

        assert link is None
        assert "Upload error" in error
        assert "API Error" in error
