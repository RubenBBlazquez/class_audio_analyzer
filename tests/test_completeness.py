import pytest
from unittest.mock import MagicMock, patch
from app.services.audio_transcriber import AudioTranscriber
@pytest.fixture
def mock_whisper_class():
    with patch('app.services.audio_transcriber.WhisperModel') as mock:
        yield mock

def test_transcribe_completeness_params(mock_whisper_class):
    mock_instance = MagicMock()
    mock_instance.transcribe.return_value = ([], MagicMock(language="es", language_probability=0.99))
    mock_whisper_class.return_value = mock_instance
    transcriber = AudioTranscriber()
    transcriber.transcribe("test.mp3")
    # Verify strict parameters to avoid skipping
    mock_instance.transcribe.assert_called_with(
        "test.mp3",
        language="es",
        beam_size=5,
        vad_filter=False,                # Must be False
        condition_on_previous_text=False,# Must be False
        no_speech_threshold=0.6,
        log_prob_threshold=None
    )
