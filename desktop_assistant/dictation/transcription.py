"""Russian offline dictation with a lazily loaded, reusable CPU model."""
import os
import threading
from importlib.util import find_spec
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from .speech_model import validate_model


def format_text(text: str) -> str:
    # Preserve Whisper punctuation and wording; do not invent sentence endings.
    return " ".join(text.split())


class Transcriber(QObject):
    completed = Signal(str)
    failed = Signal(str)
    finished = Signal(str)

    def __init__(self):
        super().__init__()
        self._model = None
        self._model_key = None
        self._lock = threading.Lock()
        self._thread = None

    @staticmethod
    def check_ready(settings: dict | None = None) -> None:
        directory = (settings or {}).get("speech_model_directory")
        validate_model(Path(directory) if directory else None)
        if find_spec("faster_whisper") is None:
            raise RuntimeError("Faster Whisper не установлен. Выполните pip install -r requirements.txt")

    def transcribe(self, audio_path: str, settings: dict) -> bool:
        if not self._lock.acquire(blocking=False):
            return False
        self._thread = threading.Thread(target=self._run, args=(audio_path, settings.copy()), daemon=True)
        try:
            self._thread.start()
        except RuntimeError:
            self._lock.release()
            raise
        return True

    def _load_model(self, settings: dict):
        selected = settings.get("speech_model_directory")
        directory = validate_model(Path(selected) if selected else None)
        threads = max(1, min(32, int(settings.get("speech_cpu_threads", 4))))
        key = (str(directory), threads)
        if self._model is None or key != self._model_key:
            # Both the hub and tokenizer must remain offline, including first launch.
            os.environ["HF_HUB_OFFLINE"] = "1"
            os.environ["TRANSFORMERS_OFFLINE"] = "1"
            from faster_whisper import WhisperModel
            self._model = WhisperModel(str(directory), device="cpu", compute_type="int8",
                                       cpu_threads=threads, num_workers=1, local_files_only=True)
            self._model_key = key
        return self._model

    def _run(self, audio_path: str, settings: dict) -> None:
        try:
            audio = Path(audio_path)
            if not audio.is_file() or audio.stat().st_size <= 44:
                raise RuntimeError("Запись пуста. Проверьте микрофон и повторите попытку.")
            model = self._load_model(settings)
            segments, _info = model.transcribe(
                str(audio), language="ru", task="transcribe", beam_size=5,
                temperature=0.0, condition_on_previous_text=False,
                vad_filter=True, vad_parameters={"min_silence_duration_ms": 500},
            )
            # The generator performs the inference; consume it in this worker.
            text = format_text(" ".join(segment.text for segment in segments))
            if not text:
                raise RuntimeError("Речь не обнаружена. Подойдите ближе к микрофону и повторите запись.")
            self.completed.emit(text)
        except Exception as error:
            # Native inference/decoder libraries use several exception classes.
            self.failed.emit(f"Не удалось распознать аудио: {str(error)[:300]}")
        finally:
            self._lock.release()
            self.finished.emit(audio_path)
