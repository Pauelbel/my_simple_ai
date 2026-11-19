from PySide6.QtCore import QObject, Property, QSettings, Qt, Signal, Slot
from PySide6.QtGui import QClipboard, QGuiApplication
from PySide6.QtWidgets import QDialog, QFormLayout, QLabel, QMessageBox, QPushButton, QSpinBox, QVBoxLayout

from .notes_window import NotesWindow
from .history_window import HistoryWindow
from .services.history import RecognitionHistory
from .services.notes import NotesRepository
from .services.recorder import AudioRecorder
from .services.transcription import Transcriber
from .services.speech_model import model_directory, validate_model
from .settings import Settings


class AssistantController(QObject):
    statusChanged = Signal()
    themeChanged = Signal()
    alwaysOnTopChanged = Signal()
    notification = Signal(str)
    processingNotification = Signal(str)

    def __init__(self, app: QGuiApplication) -> None:
        super().__init__()
        self.app = app
        self.settings = Settings(); self.history = RecognitionHistory(); self.notes = NotesRepository()
        self.recorder = AudioRecorder(); self.transcriber = Transcriber()
        self._status = "idle"; self.notes_window: NotesWindow | None = None
        self.history_window: HistoryWindow | None = None
        self.recorder.recording_started.connect(lambda: self._set_status("recording"))
        self.recorder.recording_finished.connect(self._transcribe)
        self.recorder.error.connect(self._failed)
        self.transcriber.completed.connect(self._recognized); self.transcriber.failed.connect(self._failed)
        self.transcriber.progress.connect(self.processingNotification.emit)
        self.transcriber.finished.connect(self.recorder.cleanup)

    @Property(str, notify=statusChanged)
    def status(self) -> str: return self._status

    @Property(bool, notify=themeChanged)
    def darkTheme(self) -> bool:
        if self.notes_window is not None:
            return self.notes_window.bridge.dark
        return QSettings().value("notes/dark", True, type=bool)

    @Property(bool, notify=alwaysOnTopChanged)
    def alwaysOnTop(self) -> bool:
        return bool(self.settings.values.get("always_on_top", True))

    @Slot()
    def toggleAlwaysOnTop(self) -> None:
        previous = self.alwaysOnTop
        try:
            self.settings.save({"always_on_top": not previous})
        except OSError as error:
            self.settings.values["always_on_top"] = previous
            self.notification.emit(f"Не удалось сохранить настройку закрепления: {error}")
            return
        self.alwaysOnTopChanged.emit()
        for window in (self.notes_window, self.history_window):
            if window is not None:
                self._update_window_on_top(window)

    def _update_window_on_top(self, window) -> None:
        visible = window.isVisible()
        window.setWindowFlag(Qt.WindowStaysOnTopHint, self.alwaysOnTop)
        if visible:
            window.show()

    def _set_status(self, status: str) -> None:
        self._status = status; self.statusChanged.emit()

    @Slot()
    def toggleRecording(self) -> None:
        if self._status == "recording":
            self._set_status("processing")
            self.recorder.stop()
        elif self._status == "idle":
            try:
                self.transcriber.check_ready()
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
        else:
            if self.history_window is not None:
                self.history_window.refresh()
            self.notification.emit("Текст скопирован в буфер обмена")

    def _failed(self, message: str) -> None:
        self._set_status("idle"); self.notification.emit(message)

    @Slot()
    def showNotes(self) -> None:
        if self.notes_window is None:
            self.notes_window = NotesWindow(self.notes)
            self.notes_window.bridge.themeChanged.connect(self.themeChanged.emit)
        self._update_window_on_top(self.notes_window)
        self.notes_window.showNormal(); self.notes_window.raise_(); self.notes_window.activateWindow()

    @Slot()
    def showHistory(self) -> None:
        if self.history_window is None:
            self.history_window = HistoryWindow(self.history)
        self.history_window.refresh()
        self._update_window_on_top(self.history_window)
        self.history_window.showNormal()
        self.history_window.raise_()
        self.history_window.activateWindow()

    @Slot()
    def showSettings(self) -> None:
        dialog = QDialog()
        self._update_window_on_top(dialog)
        dialog.setWindowTitle("Распознавание речи")
        dialog.setMinimumWidth(440)
        layout = QVBoxLayout(dialog)
        description = QLabel("Faster Whisper Small · русский язык\nЛокально на процессоре · INT8 · без интернета")
        description.setWordWrap(True)
        layout.addWidget(description)
        try:
            validate_model()
            status = "Модель установлена"
        except (RuntimeError, OSError):
            status = "Модель отсутствует или повреждена — нужна полная сборка"
        label = QLabel(status)
        label.setWordWrap(True)
        label.setToolTip(str(model_directory()))
        layout.addWidget(label)
        form = QFormLayout()
        threads = QSpinBox()
        threads.setRange(1, 32)
        threads.setValue(int(self.settings.values["speech_cpu_threads"]))
        threads.setToolTip("Больше потоков может ускорить распознавание, но увеличивает нагрузку на процессор")
        form.addRow("Потоков процессора:", threads)
        layout.addLayout(form)
        save = QPushButton("Сохранить")
        def save_settings():
            try:
                self.settings.save({"speech_cpu_threads": threads.value()})
                dialog.accept()
            except OSError as error:
                QMessageBox.warning(dialog, "Настройки", str(error))
        save.clicked.connect(save_settings)
        layout.addWidget(save)
        dialog.exec()

    @Slot()
    def quit(self) -> None: self.app.quit()
