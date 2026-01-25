import pytest
from unittest.mock import MagicMock, patch, mock_open
import os
from app.services.audio_transcriber import AudioTranscriber
@pytest.fixture
def mock_whisper_class():
    with patch('app.services.audio_transcriber.WhisperModel') as mock:
        yield mock
@patch("app.services.audio_transcriber.datetime")
@patch("os.makedirs")
@patch("builtins.open", new_callable=mock_open)
def test_transcribe_saves_file_default_format(mock_file, mock_makedirs, mock_datetime, mock_whisper_class):
    # Setup Date Mock
    mock_datetime.now.return_value.strftime.return_value = "01-01-2024"
    # Setup Whisper Mock
    mock_instance = MagicMock()
    mock_instance.transcribe.return_value = ([MagicMock(text="Hola", start=0, end=1)], MagicMock(language="es", language_probability=1))
    mock_whisper_class.return_value = mock_instance
    transcriber = AudioTranscriber()
    # Run with simple filename (no subject)
    result_path = transcriber.transcribe("test.mp3")
    # Assert suffix equality to avoid directory issues
    assert result_path.endswith(os.path.join("transcriptions", "test_01-01-2024.txt"))
    assert mock_makedirs.called
    mock_file.assert_called_with(result_path, "w", encoding="utf-8")
@patch("app.services.audio_transcriber.datetime")
@patch("os.makedirs")
@patch("builtins.open", new_callable=mock_open)
def test_transcribe_saves_file_with_subject(mock_file, mock_makedirs, mock_datetime, mock_whisper_class):
    # Setup Date Mock
    mock_datetime.now.return_value.strftime.return_value = "01-01-2024"
    # Setup Whisper Mock
    mock_instance = MagicMock()
    mock_instance.transcribe.return_value = ([], MagicMock(language="es", language_probability=1))
    mock_whisper_class.return_value = mock_instance
    transcriber = AudioTranscriber()
    # Run with subject filename
    result_path = transcriber.transcribe("physics_lecture1.mp3")
    # Expected suffix
    assert result_path.endswith(os.path.join("transcriptions", "physics", "physics_lecture1_01-01-2024.txt"))
    assert mock_makedirs.called
    mock_file.assert_called_with(result_path, "w", encoding="utf-8")
@patch("builtins.open", new_callable=mock_open)
def test_transcribe_custom_output_ignores_logic(mock_file, mock_whisper_class):
    # If output_file_path is provided, it should skip the auto-logic
    mock_instance = MagicMock()
    mock_instance.transcribe.return_value = ([], MagicMock(language="es", language_probability=1))
    mock_whisper_class.return_value = mock_instance
    transcriber = AudioTranscriber()
    result_path = transcriber.transcribe("input.mp3", output_file_path="custom/path.txt")
    assert result_path == "custom/path.txt"
    mock_file.assert_called_with("custom/path.txt", "w", encoding="utf-8")
