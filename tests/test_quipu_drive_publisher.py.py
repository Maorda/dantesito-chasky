from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from dantesito.quipu.config.settings import QuipuSettings
from dantesito.quipu.dispatchers.drive_publisher import GoogleDrivePublisher

@pytest.fixture(autouse=True)
def mock_google_credentials_init():
    with patch("google.oauth2.service_account.Credentials.from_service_account_info") as mock_cred:
        mock_cred.return_value = MagicMock()
        yield

def test_drive_publisher_upload_success(tmp_path: Path) -> None:
    pdf_path = tmp_path / "legajo_judicial.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\\nContenido PDF simulado\\n%%EOF")
    mock_drive_service = MagicMock()
    mock_file_id = "mock_google_file_id_123"
    (mock_drive_service.files.return_value.create.return_value.execute.return_value) = {"id": mock_file_id}
    settings = QuipuSettings()
    with patch("dantesito.quipu.dispatchers.drive_publisher.build", return_value=mock_drive_service), \
        patch("dantesito.quipu.dispatchers.drive_publisher.MediaFileUpload"):
        publisher = GoogleDrivePublisher(settings)
        file_url = publisher.upload_legajo(str(pdf_path))
        # Validamos de forma exacta la URL que tu terminal reportó en producción
        assert file_url == f"https://google.com{mock_file_id}/view"