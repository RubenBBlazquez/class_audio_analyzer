from typing import Tuple, Generator, List, Any, Optional
from pydantic.dataclasses import dataclass
from pydantic import ConfigDict
import os
from openai import OpenAI
import time
from .base_summarizer import SummarizerStrategy
from app.services.drive_service import DriveService

@dataclass(config=ConfigDict(arbitrary_types_allowed=True))
class OpenAIStrategy(SummarizerStrategy):
    theme: str
    objective: str
    mandatory_rules: Optional[str] = None
    context_files: Optional[List[str]] = None
    drive_custom_folder_id: Optional[str] = None
    client: Optional[Any] = None
    assistant_id: str = "asst_hBlXzak1TOaNVM0wZdNP4rcB"
    _is_transcription_and_summarize_process = False

    def __post_init__(self):
        self._is_transcription_and_summarize_process = False
        if self.client is None:
            self.client = OpenAI()

    def set_is_transcription_and_sumerize_process(self, value: bool):
        self._is_transcription_and_summarize_process  = value

    def summarize_with_logs(
            self,
            file_path: str,
    ) -> Generator[Tuple[str, str], None, None]:
        """
        Uploads the file to OpenAI, sends it to the assistant with metadata, and retrieves the summary.
        Yields logs and final result.
        """
        if not os.path.exists(file_path):
             raise FileNotFoundError(f"File not found: {file_path}")

        attachments = []

        msg = f"Starting upload for: {os.path.basename(file_path)}"
        yield "log", msg

        with open(file_path, "rb") as f:
            file_obj = self.client.files.create(
                file=f,
                purpose="assistants"
            )

        msg = f"File uploaded with ID: {file_obj.id}"
        yield "log", msg

        attachments.append({
            "file_id": file_obj.id,
            "tools": [{"type": "file_search"}]
        })

        if self.context_files:
            yield from self._process_context_files(self.context_files, attachments)

        thread = self.client.beta.threads.create()
        msg = f"Thread created: {thread.id}"
        yield "log", msg

        content = f'- Tema/clase: "{self.theme}" - Objetivo: "{self.objective}":'
        if self.mandatory_rules:
            content += f'\n- Reglas OBLIGATORIAS: {self.mandatory_rules}'

        content += " Genera un archivo PDF con el resumen estructurado y detallado para descargar."

        self.client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=content,
            attachments=attachments
        )

        msg = "Running assistant..."
        yield "log", msg

        run = self.client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=self.assistant_id
        )

        while run.status in ["queued", "in_progress", "cancelling"]:
            time.sleep(1)
            run = self.client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )

        if run.status != 'completed':
            fail_msg = f"Run failed or incomplete. Status: {run.status}"
            yield "log", fail_msg
            yield "result", f"Error: {fail_msg}"
            return

        yield from self._handle_completed_run(thread.id, file_path)

    def _process_context_files(self, context_files: List[str], attachments: List[dict]) -> Generator[Tuple[str, str], None, None]:
        for ctx_path in context_files:
            if not os.path.exists(ctx_path):
                yield "log", f"Warning: Context file not found: {ctx_path}"
                continue

            yield "log", f"Uploading context file: {os.path.basename(ctx_path)}"
            with open(ctx_path, "rb") as f_ctx:
                ctx_obj = self.client.files.create(file=f_ctx, purpose="assistants")

            attachments.append({
                "file_id": ctx_obj.id,
                "tools": [{"type": "file_search"}]
            })

    def _handle_completed_run(self, thread_id: str, origin_file_path: str) -> Generator[Tuple[str, str], None, None]:
        messages = self.client.beta.threads.messages.list(thread_id=thread_id)

        for msg_obj in messages.data:
            if msg_obj.role == "assistant":
                yield from self._process_assistant_response(msg_obj, origin_file_path)
                return

        yield "result", "No assistant response found."

    def _process_assistant_response(self, msg_obj: Any, origin_file_path: str) -> Generator[Tuple[str, str], None, None]:
        response_text = ""
        for content_part in msg_obj.content:
            if content_part.type != 'text':
                continue

            response_text += content_part.text.value

            if not hasattr(content_part.text, 'annotations'):
                continue

            for kind, msg in self._process_annotations(content_part.text.annotations, origin_file_path):
                yield kind, msg

                if kind == "log" and msg.startswith("Saved file to: "):
                    path = msg.replace("Saved file to: ", "")
                    response_text += f"\n\n[File downloaded: {path}]"

        yield "log", "Summary retrieved."
        yield "result", response_text

    def _process_annotations(self, annotations: List[Any], origin_file_path: str) -> Generator[Tuple[str, str], None, None]:
        for annotation in annotations:
            if annotation.type == 'file_path':
                yield from self._download_annotation_file(annotation, origin_file_path)

    def _download_annotation_file(self, annotation: Any, origin_file_path: str) -> Generator[Tuple[str, str], None, None]:
        file_id = annotation.file_path.file_id
        original_name = self._extract_filename(annotation.text)
        target_path = self._prepare_target_path(origin_file_path, original_name)

        yield "log", f"Downloading generated file: {original_name}"

        try:
            file_content = self.client.files.content(file_id)
            with open(target_path, "wb") as f_out:
                f_out.write(file_content.read())
            yield "log", f"Saved file to: {target_path}"

            # --- GOOGLE DRIVE UPLOAD INTEGRATION ---
            drive_service = DriveService()
            if drive_service.enabled:
                yield "log", "Uploading to Google Drive..."
                drive_link, error = drive_service.upload_file(
                    target_path,
                    custom_folder_id=self.drive_custom_folder_id,
                    subfolder_name=self.theme,
                    fixed_subfolder="resumes"
                )
                if error:
                    yield "log", f"Drive Upload Warning: {error}"
                else:
                    yield "log", f"Uploaded to Drive: {drive_link}"
            # ---------------------------------------

        except Exception as e:
            yield "log", f"Error downloading file {file_id}: {e}"

    def _extract_filename(self, annotation_text: str) -> str:
        name = os.path.basename(annotation_text)
        if '/' in name:
            name = name.split('/')[-1]

        if not name.endswith('.pdf'):
             name += ".pdf"

        return name

    def _prepare_target_path(self, origin_path: str, filename: str) -> str:
        subject_dir = os.path.dirname(origin_path)
        resumes_dir = os.path.join(subject_dir, "resumes")

        if not self._is_transcription_and_summarize_process:
             project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

             if self.drive_custom_folder_id:
                 resumes_dir = os.path.join(
                    project_root,
                    "transcriptions",
                    self.drive_custom_folder_id,
                    "resumes"
                 )
             else:
                 safe_theme = self.theme.replace(" ", "_") if self.theme else "General"
                 resumes_dir = os.path.join(project_root, "transcriptions", "other_resumes", safe_theme)

        os.makedirs(resumes_dir, exist_ok=True)
        return os.path.join(resumes_dir, filename)
