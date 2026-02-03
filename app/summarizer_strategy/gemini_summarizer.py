from typing import Tuple, Generator, List, Optional
from pydantic.dataclasses import dataclass
from pydantic import ConfigDict
import os
from google import genai
from weasyprint import HTML
from .base_summarizer import SummarizerStrategy
from app.utils.file_processing import extract_text_from_file
from app.services.drive_service import DriveService

@dataclass(config=ConfigDict(arbitrary_types_allowed=True))
class GeminiStrategy(SummarizerStrategy):
    theme: str
    objective: str
    mandatory_rules: Optional[str] = None
    context_files: Optional[List[str]] = None
    model_name: str = "models/gemini-2.5-pro"
    _is_transcription_and_summarize_process = False

    def __post_init__(self):
        # Assumes GOOGLE_API_KEY is set in environment
        # Force load dotenv if key is missing, assuming structure
        if not os.environ.get("GOOGLE_API_KEY"):
             try:
                 from dotenv import load_dotenv
                 # Look for .env in standard locations
                 base_dir = os.path.dirname(os.path.abspath(__file__)) # app/summarizer_strategy
                 project_root = os.path.abspath(os.path.join(base_dir, "..", ".."))
                 env_path = os.path.join(project_root, "config", ".env")
                 load_dotenv(env_path)
             except ImportError:
                 pass

        api_key = os.environ.get("GOOGLE_API_KEY")

        if not api_key:
            # If still missing, we can't initialize Client without erroring later
            # But the error message seen by user comes from Client initialization inside Pydantic validation
            print("WARNING: GOOGLE_API_KEY not found in environment variables.")

        self.client = genai.Client(api_key=api_key)

    def _load_system_prompt(self) -> str:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        # Go up two levels from app/summarizer_strategy to project root if config is there
        # Structure: root -> config/gemini_prompt_instructions.txt
        # __file__ is app/summarizer_strategy/gemini_summarizer.py
        # dirname -> app/summarizer_strategy
        # up -> app
        # up -> root
        project_root = os.path.abspath(os.path.join(base_dir, "..", ".."))
        prompt_path = os.path.join(project_root, "config", "gemini_prompt_instructions.txt")

        if not os.path.exists(prompt_path):
            # Fallback if file missing (should not happen if created correctly)
            return "Genera un resumen estructurado y detallado de la siguiente transcripción."

        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()

    def set_is_transcription_and_sumerize_process(self, value: bool):
        self._is_transcription_and_summarize_process  = value

    def summarize_with_logs(
            self,
            file_path: str,
    ) -> Generator[Tuple[str, str], None, None]:

        if not os.path.exists(file_path):
             raise FileNotFoundError(f"File not found: {file_path}")

        yield "log", f"Reading transcription file: {os.path.basename(file_path)}"
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                transcription_text = f.read()
        except:
             # fallback encoding
             with open(file_path, "r", encoding="latin-1") as f:
                transcription_text = f.read()

        system_instructions = self._load_system_prompt()

        prompt = f"""
        {system_instructions}

        ---
        Input de la tarea:
        Tema: {self.theme}
        Objetivo: {self.objective}
        """

        if self.mandatory_rules:
            prompt += f"\nReglas OBLIGATORIAS: {self.mandatory_rules}\n"

        prompt += f"""
        Transcripción a procesar:
        {transcription_text}
        """

        if self.context_files:
            yield "log", "Processing context files (PDF/TXT supported)..."
            for cf in self.context_files:
                if os.path.exists(cf):
                    try:
                        content = extract_text_from_file(cf)
                        prompt += f"\n\nContexto adicional ({os.path.basename(cf)}):\n{content}"
                    except Exception as e:
                         yield "log", f"Failed to read context file {os.path.basename(cf)}: {e}"

        yield "log", f"Sending request to {self.model_name}..."

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            html_content = response.text

            # Clean potential markdown wrapping if the model ignores instruction
            if html_content.startswith("```html"):
                html_content = html_content.replace("```html", "", 1)
            if html_content.endswith("```"):
                html_content = html_content.rsplit("```", 1)[0]

            html_content = html_content.strip()

            yield "log", "Received HTML response from Gemini."

            # Save HTML locally
            html_filename = f"{os.path.splitext(os.path.basename(file_path))[0]}_resumen_gemini.html"
            html_path = self._prepare_target_path(file_path, html_filename)

            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            yield "log", f"Saved HTML to: {html_path}"

            # --- GENERATE PDF ---
            pdf_path = html_path.replace(".html", ".pdf")
            try:
                HTML(string=html_content).write_pdf(pdf_path)
                yield "log", f"Generated PDF: {pdf_path}"
            except Exception as pdf_err:
                yield "log", f"PDF Generation Error: {pdf_err}"
                pdf_path = None

            # --- GOOGLE DRIVE UPLOAD INTEGRATION ---
            drive_service = DriveService()
            if drive_service.enabled:
                yield "log", "Uploading to Google Drive..."

                # Upload HTML
                drive_link_html, error_html = drive_service.upload_file(html_path)
                if error_html:
                    yield "log", f"Drive Upload Warning (HTML): {error_html}"
                else:
                    yield "log", f"Uploaded HTML to Drive: {drive_link_html}"

                # Upload PDF
                if pdf_path and os.path.exists(pdf_path):
                     drive_link_pdf, error_pdf = drive_service.upload_file(pdf_path)
                     if error_pdf:
                         yield "log", f"Drive Upload Warning (PDF): {error_pdf}"
                     else:
                         yield "log", f"Uploaded PDF to Drive: {drive_link_pdf}"
            # ---------------------------------------

            # Optionally, we can also try to generate a PDF from this HTML if needed,
            # but user specifically asked to try HTML format.
            # Returning the HTML file path.

            final_output = f"[HTML Document generated: {html_path}]\n\nPreview:\n" + html_content[:500] + "..."
            yield "result", final_output

        except Exception as e:
            yield "log", f"Gemini Error: {e}"
            yield "result", f"Error: {e}"

    def _prepare_target_path(self, origin_path: str, filename: str) -> str:
        subject_dir = os.path.dirname(origin_path)
        resumes_dir = os.path.join(subject_dir, "resumes")

        if not self._is_transcription_and_summarize_process:
             resumes_dir = os.path.join(
                "transcriptions",
                "other_resumes",
                self.theme.replace(" ", "_")
            )

        os.makedirs(resumes_dir, exist_ok=True)
        return os.path.join(resumes_dir, filename)
