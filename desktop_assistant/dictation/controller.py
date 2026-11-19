from PySide6.QtCore import QObject, Property, Signal, Slot
from PySide6.QtGui import QClipboard, QGuiApplication

from desktop_assistant.history.repository import RecognitionHistory
from desktop_assistant.settings.store import Settings

from .recorder import AudioRecorder
from .transcription import Transcriber


class DictationController(QObject):
    statusChanged = Signal()
    notification = Signal(str)
    recognized = Signal(str)

    def __init__(
        self,
        app: QGuiApplication,
        settings: Settings,
        history: RecognitionHistory,
        recorder: AudioRecorder | None = None,
        transcriber: Transcriber | None = None,
    ) -> None:
        super().__init__()
        self.app = app
        self.settings = settings
        self.history = history
        self.recorder = recorder or AudioRecorder()
        self.transcriber = transcriber or Transcriber()
        self._status = "idle"
        self.recorder.recording_started.connect(lambda: self._set_status("recording"))
        self.recorder.recording_finished.connect(self._transcribe)
        self.recorder.error.connect(self._failed)
        self.transcriber.completed.connect(self._recognized)
        self.transcriber.failed.connect(self._failed)
        self.transcriber.finished.connect(self.recorder.cleanup)

    @Property(str, notify=statusChanged)
    def status(self) -> str:
        return self._status

    def _set_status(self, status: str) -> None:
        self._status = status
        self.statusChanged.emit()

    @Slot()
    def toggleRecording(self) -> None:
        if self._status == "recording":
            self._set_status("processing")
            self.recorder.stop()
        elif self._status == "idle":
            try:
                self.transcriber.check_ready(self.settings.values)
                self._set_status("starting")
                self.recorder.start()
            except (OSError, RuntimeError) as error:
                self._failed(str(error))

    def _transcribe(self, path: str) -> None:
        self._set_status("processing")
        if not self.transcriber.transcribe(path, self.settings.values):
            self.recorder.cleanup(path)
            self._failed("Распознавание уже выполняется. Дождитесь его завершения.")

    def _recognized(self, text: str) -> None:
        self.app.clipboard().setText(text, QClipboard.Mode.Clipboard)
        self._set_status("idle")
        try:
            self.history.add(text)
        except OSError:
            self.notification.emit("Текст скопирован, но не удалось сохранить историю")
        self.recognized.emit(text)

    def _failed(self, message: str) -> None:
        self._set_status("idle")
        self.notification.emit(message)
