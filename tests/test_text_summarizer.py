import pytest
from unittest.mock import MagicMock, patch, mock_open
from app.summarizer_strategy.openai_summarizer import OpenAIStrategy as TextSummarizer
import os

@pytest.fixture
def mock_openai_client():
    client = MagicMock()
    return client

def test_summarize_from_file_success(mock_openai_client):
    # Setup mocks
    # Files
    mock_file_obj = MagicMock()
    mock_file_obj.id = "file_123"
    mock_openai_client.files.create.return_value = mock_file_obj

    # Threads
    mock_thread = MagicMock()
    mock_thread.id = "thread_123"
    mock_openai_client.beta.threads.create.return_value = mock_thread

    # Run
    mock_run = MagicMock()
    mock_run.status = "completed"
    mock_run.id = "run_123"

    # Run create returns the run object
    mock_openai_client.beta.threads.runs.create.return_value = mock_run
    # Run retrieve returns the run object (for polling loop if needed)
    mock_openai_client.beta.threads.runs.retrieve.return_value = mock_run

    # Messages
    mock_msg = MagicMock()
    mock_msg.role = "assistant"

    # Mock Content Part
    mock_content_part = MagicMock()
    mock_content_part.type = 'text'
    mock_content_part.text.value = "This is the summary."
    # Ensure annotations doesn't cause errors or side effects if accessed
    mock_content_part.text.annotations = []

    mock_msg.content = [mock_content_part]

    mock_messages_list = MagicMock()
    mock_messages_list.data = [mock_msg]
    mock_openai_client.beta.threads.messages.list.return_value = mock_messages_list

    # Init Summarizer with mock client
    summarizer = TextSummarizer(
        client=mock_openai_client,
        theme="Test Theme",
        objective="Test Objective"
    )

    with patch("builtins.open", mock_open(read_data="content")), \
         patch("os.path.exists", return_value=True):

        # We need to iterate the generator to trigger the logic
        gen = summarizer.summarize_with_logs("test.txt")

        result_text = ""
        for kind, msg in gen:
            if kind == "result":
                result_text = msg

        assert result_text == "This is the summary."

        # Verify calls
        mock_openai_client.files.create.assert_called_once()
        mock_openai_client.beta.threads.create.assert_called_once()
        mock_openai_client.beta.threads.messages.create.assert_called_once()
        mock_openai_client.beta.threads.runs.create.assert_called_once()

        # Check message content format
        call_args = mock_openai_client.beta.threads.messages.create.call_args
        assert call_args
        _, kwargs = call_args
        # kwargs['content'] should contain theme
        assert 'Test Theme' in kwargs['content']
        assert "attachments" in kwargs
        assert kwargs['attachments'][0]['file_id'] == "file_123"

def test_file_not_found(mock_openai_client):
     summarizer = TextSummarizer(
         client=mock_openai_client,
         theme="Test Theme",
         objective="Test Objective"
     )
     with pytest.raises(FileNotFoundError):
         # Logic checks os.path.exists, so we don't need to patch open if it fails before
         # But wait, summarize_with_logs is a generator. We must consume it to trigger code.
         gen = summarizer.summarize_with_logs("ghost.txt")
         next(gen)
