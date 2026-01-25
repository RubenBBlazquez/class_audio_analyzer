import logging

from pydantic.dataclasses import dataclass
from pydantic import ConfigDict
from typing import Optional, Any, Generator, Tuple
from faster_whisper import WhisperModel
import os
from datetime import datetime


@dataclass(config=ConfigDict(arbitrary_types_allowed=True))
class AudioTranscriber:
    """
    Transcribes audio files using Faster Whisper (CTranslate2).

    Attributes:
    -----------
    model_name: str
        The name of the Whisper model to use (default is "large-v3").
        Accepts "turbo", "large-v3", "medium", etc.
    device: str
        Device to use ("cuda", "cpu", "auto").
    compute_type: str
        Quantization type ("float16", "int8_float16", "int8").
        "int8" is recommended for CPU speed.
    cpu_threads: int
        Number of threads to use for CPU inference.
        Increase this for better "velocity" on multicore CPUs.
    """
    model_name: str = "turbo"
    device: str = "auto"
    compute_type: str = "int8"
    cpu_threads: int = 12
    whisper_model: Any = None

    def __post_init__(self):
        target_model = self.model_name
        if self.model_name == "turbo":
            target_model = "deepdml/faster-whisper-large-v3-turbo-ct2"

        try:
            self.whisper_model = WhisperModel(
                target_model,
                device=self.device,
                compute_type=self.compute_type,
                cpu_threads=self.cpu_threads
            )
        except Exception as e:
            print(f"Model '{target_model}' load failed: {e}. Falling back to 'medium'.")
            self.whisper_model = WhisperModel(
                "medium",
                device=self.device,
                compute_type=self.compute_type,
                cpu_threads=self.cpu_threads,
            )

    @staticmethod
    def _seconds_to_hms(seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def transcribe_with_logs(self, audio_file_path: str, output_file_path: Optional[str] = None, subject: Optional[str] = None) -> Generator[Tuple[str, str], None, None]:
        """
        Transcribes the audio file yielding logs and the final result path.

        Yields:
        -------
        Tuple[str, str]
            ("log", message) or ("result", file_path)
        """
        if not audio_file_path:
            raise ValueError("No audio file path provided.")

        message = f"Transcribing audio file: {audio_file_path}"
        logging.info(message)
        yield "log", message

        segments, info = self.whisper_model.transcribe(
            audio_file_path,
            language="es",
            beam_size=5,
            vad_filter=False,           # Disabled: prevents aggressive skipping of quiet speech
            condition_on_previous_text=False, # Disabled: prevents loops/skipping based on bad context
            no_speech_threshold=0.6,    # Lower threshold: easier to detect speech
            log_prob_threshold=None     # Disabled: prevents discarding low-confidence segments
        )

        detected_lang_msg = f"Detected language '{info.language}' with probability {info.language_probability:.2f}"
        logging.info(detected_lang_msg)
        yield "log", detected_lang_msg

        text_segments = []

        for segment in segments:
            start_str = self._seconds_to_hms(segment.start)
            end_str = self._seconds_to_hms(segment.end)
            seg_msg = f"[{start_str} -> {end_str}] {segment.text}"
            logging.info(seg_msg)
            yield "log", seg_msg
            text_segments.append(segment.text)

        full_text = " ".join(text_segments).strip()

        save_path = output_file_path

        if not output_file_path:
            basename = os.path.basename(audio_file_path)
            name_without_ext, _ = os.path.splitext(basename)
            current_date = datetime.now().strftime("%d-%m-%Y")

            target_subject = subject
            if not target_subject:
                parts = name_without_ext.split('_', 1)

                if len(parts) > 1:
                    target_subject = parts[0]

            # Use path relative to this file to ensure it goes into app/transcriptions
            base_dir = os.path.dirname(os.path.abspath(__file__))
            final_dir = os.path.join(base_dir, "../transcriptions")

            if target_subject:
                final_dir = os.path.join(final_dir, target_subject)

            os.makedirs(final_dir, exist_ok=True)
            save_path = os.path.join(final_dir, f"{name_without_ext}_{current_date}.txt")

        try:
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(full_text)
            message = f"Transcription saved to file: {save_path}"
            logging.info(message)
            yield "log", message
        except Exception as e:
             logging.error(f"Failed to save transcription to file: {e}")
             raise

        yield "result", save_path


    def transcribe(self, audio_file_path: str, output_file_path: Optional[str] = None, subject: Optional[str] = None) -> str:
        """
        Transcribes the audio file and saves the result to a text file.
        Wraps transcribe_with_logs to maintain backward compatibility.
        """
        generator = self.transcribe_with_logs(audio_file_path, output_file_path, subject)
        final_path = ""

        for kind, value in generator:
            if kind == "result":
                final_path = value

        return final_path


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    transcriber = AudioTranscriber()

    audio_path = "/home/rubenbblaz/251218_1714.mp3"

    transcriber.transcribe(audio_path)
