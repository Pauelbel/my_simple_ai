from PySide6.QtCore import QObject, Property, QSettings, Qt, Signal, Slot
from PySide6.QtGui import QClipboard, QGuiApplication
from pathlib import Path

from PySide6.QtWidgets import QDialog, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QSpinBox, QVBoxLayout

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

    def __init__(self, app: QGuiApplication) -> None:
        super().__init__()
        self.app = app
        self.settings = Settings(); self.history = RecognitionHistory()
        self.notes = NotesRepository(self.settings.values.get("notes_directory") or None)
        self.recorder = AudioRecorder(); self.transcriber = Transcriber()
        self._status = "idle"; self.notes_window: NotesWindow | None = None
        self.history_window: HistoryWindow | None = None
        self._error_dialogs: set[QMessageBox] = set()
        self.recorder.recording_started.connect(lambda: self._set_status("recording"))
        self.recorder.recording_finished.connect(self._transcribe)
        self.recorder.error.connect(self._failed)
        self.transcriber.completed.connect(self._recognized); self.transcriber.failed.connect(self._failed)
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
        else:
            if self.history_window is not None:
                self.history_window.refresh()

    def _failed(self, message: str) -> None:
        self._set_status("idle"); self.notification.emit(message)

    @Slot(str)
    def showError(self, message: str) -> None:
        dialog = QMessageBox(QMessageBox.Icon.Warning, "Desktop Assistant", message)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self._error_dialogs.add(dialog)
        dialog.finished.connect(lambda: self._error_dialogs.discard(dialog))
        self._update_window_on_top(dialog)
        dialog.show()

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
        dialog.setWindowTitle("Настройки")
        dialog.setFixedWidth(560)
        layout = QVBoxLayout(dialog)
        layout.setSpacing(8)

        def hint(text):
            label = QLabel(text)
            label.setWordWrap(True)
            label.setStyleSheet("color: palette(mid);")
            layout.addWidget(label)

        layout.addWidget(QLabel("Модель распознавания"))
        hint("Русская речь распознаётся локально, без интернета. Выберите многоязычную модель Faster Whisper в формате CTranslate2.")
        model = QLineEdit(self.settings.values.get("speech_model_directory") or str(model_directory()))
        model.setReadOnly(True)
        model.setToolTip(model.text())
        model_button = QPushButton("Выбрать…")
        model_row = QHBoxLayout()
        model_row.addWidget(model)
        model_row.addWidget(model_button)
        layout.addLayout(model_row)
        status = QLabel()
        status.setWordWrap(True)
        layout.addWidget(status)

        def update_model_status():
            model.setToolTip(model.text())
            try:
                validate_model(Path(model.text()))
                status.setText("Модель готова к использованию")
            except (RuntimeError, OSError):
                status.setText("Модель отсутствует или неполна. Подготовьте её по инструкции в README.")
        update_model_status()

        def choose_model():
            selected = QFileDialog.getExistingDirectory(dialog, "Папка модели распознавания", model.text())
            if selected:
                model.setText(selected)
                update_model_status()
        model_button.clicked.connect(choose_model)

        layout.addSpacing(6)
        layout.addWidget(QLabel("Потоки процессора"))
        hint("Сколько потоков использовать для распознавания. Больше потоков может ускорить работу, но сильнее нагрузит компьютер.")
        threads = QSpinBox()
        threads.setRange(1, 32)
        threads.setValue(int(self.settings.values["speech_cpu_threads"]))
        threads.setToolTip("Больше потоков может ускорить распознавание, но увеличивает нагрузку на процессор")
        layout.addWidget(threads)
        layout.addSpacing(6)
        layout.addWidget(QLabel("Папка заметок"))
        hint("Здесь хранятся Markdown-файлы. При смене папки существующие заметки остаются на прежнем месте.")
        folder = QLineEdit(str(self.notes.root))
        folder.setReadOnly(True)
        folder.setToolTip(folder.text())
        choose = QPushButton("Выбрать…")
        folder_row = QHBoxLayout()
        folder_row.addWidget(folder)
        folder_row.addWidget(choose)
        layout.addLayout(folder_row)

        def choose_folder():
            selected = QFileDialog.getExistingDirectory(dialog, "Папка заметок", folder.text())
            if selected:
                folder.setText(selected)
                folder.setToolTip(selected)
        choose.clicked.connect(choose_folder)
        layout.addSpacing(8)
        save = QPushButton("Сохранить")
        def save_settings():
            try:
                if not self._save_preferences(threads.value(), folder.text(), model.text()):
                    return
                dialog.accept()
            except (OSError, ValueError, RuntimeError) as error:
                QMessageBox.warning(dialog, "Настройки", str(error))
        save.clicked.connect(save_settings)
        layout.addWidget(save)
        dialog.setFixedHeight(dialog.sizeHint().height())
        dialog.exec()

    def _save_preferences(self, threads: int, folder: str, model: str | None = None) -> bool:
        path = Path(folder).expanduser().resolve()
        if not path.is_dir():
            raise ValueError("Папка заметок не существует")
        model_path = Path(model).expanduser().resolve() if model else None
        current_model = Path(self.settings.values.get("speech_model_directory") or model_directory()).resolve()
        if model_path and model_path != current_model:
            validate_model(model_path)
        changed = path != self.notes.root.resolve()
        if changed and self.notes_window is not None and not self.notes_window.bridge.save():
            return False
        repository = NotesRepository(path) if changed else self.notes
        values = {"speech_cpu_threads": threads, "notes_directory": str(path)}
        if model_path is not None:
            values["speech_model_directory"] = str(model_path)
        self.settings.save(values)
        if changed:
            was_visible = self.notes_window is not None and self.notes_window.isVisible()
            if self.notes_window is not None:
                self.notes_window.close()
                self.notes_window.deleteLater()
                self.notes_window = None
            self.notes = repository
            if was_visible:
                self.showNotes()
        return True

    @Slot()
    def quit(self) -> None: self.app.quit()
