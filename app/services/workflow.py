import os
from app.services import database_manager
from app.services.audio_transcriber import AudioTranscriber
from app.summarizer_strategy.openai_summarizer import OpenAIStrategy
from app.summarizer_strategy.gemini_summarizer import GeminiStrategy
from app.utils.formatting import format_log_message

def transcribe_workflow(audio_path, subject, theme, objective, mandatory_rules, do_summarize, context_files, summarizer_type):
    if not audio_path:
        print("Error: No audio file provided.")
        yield "Error: No audio file provided.", ""
        return

    status_log = []
    start_msg = f"Starting transcription for {os.path.basename(audio_path)}..."
    print(start_msg)
    status_log.append(start_msg)
    yield "\n".join(status_log), ""

    final_path = None
    transcription_id = None

    try:
        transcriber = AudioTranscriber()
        generator = transcriber.transcribe_with_logs(
            audio_file_path=audio_path,
            subject=subject.strip() if subject else None
        )

        for kind, msg in generator:
            if kind == "log":
                formatted_msg = format_log_message(msg)
                print(formatted_msg)
                status_log.append(formatted_msg)
                yield "\n".join(status_log), ""
            elif kind == "result":
                final_path = msg

        if not final_path:
            raise RuntimeError("Transcription finished without returning a file path.")

        saved_msg = f"Transcription saved to: {final_path}"
        print(saved_msg)
        status_log.append(saved_msg)
        yield "\n".join(status_log), ""

    except Exception as e:
        error_msg = f"Transcription Failed: {str(e)}"
        print(error_msg)
        status_log.append(error_msg)
        yield "\n".join(status_log), ""
        return

    try:
        audio_filename = os.path.basename(audio_path)
        subject_folder = subject.strip() if subject else "root"
        transcription_id = database_manager.log_transcription(audio_filename, subject_folder, final_path)

        db_msg = f"Transcription logged to DB with ID: {transcription_id}"
        print(db_msg)
        status_log.append(db_msg)
        yield "\n".join(status_log), ""
    except Exception as e:
        warn_msg = f"DB Warning: {str(e)}"
        print(warn_msg)
        status_log.append(warn_msg)
        yield "\n".join(status_log), ""

    if not do_summarize:
        return

    # --- Summarization Phase ---
    theme = theme or "Clase General"
    objective = objective or "Resumir contenido principal"

    enc_msg = "Starting summarization..."
    print(enc_msg)
    status_log.append(enc_msg)
    yield "\n".join(status_log), ""

    try:
        # Strategy selection
        context_paths = [f.name for f in context_files] if context_files else None

        if summarizer_type == "Gemini Pro":
            summarizer = GeminiStrategy(theme=theme, objective=objective, mandatory_rules=mandatory_rules, context_files=context_paths)
        else:
            summarizer = OpenAIStrategy(theme=theme, objective=objective, mandatory_rules=mandatory_rules, context_files=context_paths)

        summarizer.set_is_transcription_and_sumerize_process(True)
        gen = summarizer.summarize_with_logs(final_path)

        summary_result = ""
        for kind, msg in gen:
            if kind == "log":
                print(msg)
                status_log.append(msg)
                yield "\n".join(status_log), ""
            elif kind == "result":
                summary_result = msg

        comp_msg = "Summarization complete."
        print(comp_msg)
        status_log.append(comp_msg)
        yield "\n".join(status_log), summary_result

        if transcription_id:
             database_manager.log_summarization(transcription_id, theme, objective, summary_result)
             db_sum_msg = "Summarization logged to DB."
             print(db_sum_msg)
             status_log.append(db_sum_msg)
             yield "\n".join(status_log), summary_result

    except Exception as e:
        error_msg = f"Summarization Failed: {str(e)}"
        print(error_msg)
        status_log.append(error_msg)
        yield "\n".join(status_log), ""


def summarize_workflow(file_path, theme, objective, mandatory_rules, context_files, summarizer_type):
    if not file_path:
        yield "Error: No text file provided.", ""
        return

    # Handle file_path being either a string or a file-like object
    input_path = file_path.name if hasattr(file_path, "name") else file_path

    status_log = ["Processing text file..."]
    yield "\n".join(status_log), ""

    summary_text = ""
    try:
        # Strategy selection
        context_paths = [f.name for f in context_files] if context_files else None

        if summarizer_type == "Gemini Pro":
            summarizer = GeminiStrategy(theme=theme, objective=objective, mandatory_rules=mandatory_rules, context_files=context_paths)
        else:
            summarizer = OpenAIStrategy(theme=theme, objective=objective, mandatory_rules=mandatory_rules, context_files=context_paths)

        summarizer.set_is_transcription_and_sumerize_process(False)


        gen = summarizer.summarize_with_logs(input_path)

        for kind, msg in gen:
            if kind == "log":
                status_log.append(msg)
                yield "\n".join(status_log), ""
            elif kind == "result":
                summary_text = msg
                pass

        status_log.append("Summarization complete.")
        yield "\n".join(status_log), summary_text

    except Exception as e:
        error_msg = f"Error: {str(e)}"
        status_log.append(error_msg)
        yield "\n".join(status_log), ""
        return

    try:
        filename = os.path.basename(input_path)
        existing_row = database_manager.get_transcription_by_filename(filename)

        if existing_row:
            transcription_id = existing_row[0]
            status_log.append(f"Linked to existing transcription ID: {transcription_id}")
        else:
            subject_to_log = theme.strip() if theme else "manual_upload"
            transcription_id = database_manager.log_transcription(filename, subject_to_log, input_path)
            status_log.append(f"Created new transcription record ID: {transcription_id}")

        database_manager.log_summarization(transcription_id, theme, objective, summary_text)

        db_msg = "Summarization logged to DB."
        status_log.append(db_msg)
        yield "\n".join(status_log), summary_text
    except Exception as db_err:
        warn_msg = f"DB Logging failed: {db_err}"
        status_log.append(warn_msg)
        yield "\n".join(status_log), summary_text
