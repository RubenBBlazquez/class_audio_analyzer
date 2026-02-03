import pytest
from unittest.mock import MagicMock, patch
from app.services.drive_service import DriveService

@pytest.fixture
def mock_env_vars(monkeypatch):
    """Sets standard environment variables for tests."""
    monkeypatch.setenv("GOOGLE_DRIVE_FOLDER_ID", "default_folder_id")
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", "/tmp/fake_service_account.json")

class TestDriveServiceCustomFolder:

    @patch("app.services.drive_service.os.path.exists")
    @patch("app.services.drive_service.MediaFileUpload")
    @patch("app.services.drive_service.DriveService._ensure_subfolder")
    def test_upload_with_custom_folder(self, mock_ensure_subfolder, mock_media, mock_exists, mock_env_vars):
        """Test upload using a custom folder override (simulating subfolder resolution)."""
        mock_exists.return_value = True
        service = DriveService()

        # Manually set up authenticated state
        mock_service = MagicMock()
        service.service = mock_service
        service.authenticate = MagicMock(return_value=True)

        # Mock API response for FILE UPLOAD
        mock_create = mock_service.files.return_value.create
        mock_create.return_value.execute.return_value = {"id": "12345", "webViewLink": "http://gdrive/custom_link"}

        # Mock _ensure_subfolder to return a fake ID for "custom_folder_name"
        mock_ensure_subfolder.return_value = "resolved_custom_folder_id"

        # ACT: Call with custom folder NAME/ID
        link, error = service.upload_file("/path/to/test_file.txt", custom_folder_id="custom_folder_name")

        assert link == "http://gdrive/custom_link"
        assert error is None

        # ASSERT: Check that the resolved folder ID was used in the API call
        mock_create.assert_called_once()
        _, kwargs = mock_create.call_args
        assert kwargs['body']['parents'] == ["resolved_custom_folder_id"]

    @patch("app.services.drive_service.os.path.exists")
    @patch("app.services.drive_service.MediaFileUpload")
    def test_upload_fallback_to_default(self, mock_media, mock_exists, mock_env_vars):
        """Test fallback to default env var when custom folder is None."""
        mock_exists.return_value = True
        service = DriveService()

        mock_service = MagicMock()
        service.service = mock_service
        service.authenticate = MagicMock(return_value=True)

        mock_create = mock_service.files.return_value.create
        mock_create.return_value.execute.return_value = {"id": "12345", "webViewLink": "http://gdrive/default_link"}

        # ACT: Call without custom folder ID or subfolder name
        link, error = service.upload_file("/path/to/test_file.txt", custom_folder_id=None, subfolder_name=None)

        assert link == "http://gdrive/default_link"

        # ASSERT: Check that the default folder ID was used (root)
        mock_create.assert_called_once()
        _, kwargs = mock_create.call_args
        assert kwargs['body']['parents'] == ["default_folder_id"]
