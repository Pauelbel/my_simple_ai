from pathlib import Path

from PySide6.QtCore import QObject, Property, Qt, Signal, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QMessageBox

from desktop_assistant.dictation.controller import DictationController
from desktop_assistant.core.global_hotkey import GlobalHotkey
from desktop_assistant.dictation.speech_model import model_directory, validate_model
from desktop_assistant.history.controller import HistoryController
from desktop_assistant.history.repository import RecognitionHistory
from desktop_assistant.notes.controller import NotesController
from desktop_assistant.notes.repository import NotesRepository
from desktop_assistant.settings.dialog import SettingsDialog
from desktop_assistant.settings.store import Settings


class AssistantController(QObject):
    themeChanged = Signal()
    alwaysOnTopChanged = Signal()
    notification = Signal(str)

    def __init__(self, app: QGuiApplication) -> None:
        super().__init__()
        self.app = app
        self.settings = Settings()
        self.notes = NotesController(NotesRepository(self.settings.values.get("notes_directory") or None))
        self.history = HistoryController(RecognitionHistory(), self.notes.dark_theme)
        self.dictation = DictationController(app, self.settings, self.history.repository)
        self.record_hotkey = GlobalHotkey(self.settings.values.get("record_hotkey", "Ctrl+Shift+Space"))
        self.record_hotkey.activated.connect(self.dictation.toggleRecording)
        self._error_dialogs: set[QMessageBox] = set()
        self.dictation.notification.connect(self.notification.emit)
        self.dictation.recognized.connect(lambda _text: self.history.refresh())
        self.notes.themeChanged.connect(self.themeChanged.emit)
        self.notes.themeChanged.connect(lambda: self.history.set_dark_theme(self.notes.dark_theme))

    @Property(bool, notify=themeChanged)
    def darkTheme(self) -> bool:
        return self.notes.dark_theme

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

    @Slot(str)
    def showError(self, message: str) -> None:
        dialog = QMessageBox(QMessageBox.Icon.Warning, "Desktop Assistant", message)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self._error_dialogs.add(dialog)
        dialog.finished.connect(lambda: self._error_dialogs.discard(dialog))
        dialog.show()

    @Slot()
    def showNotes(self) -> None:
        self.notes.show()

    @Slot()
    def showHistory(self) -> None:
        self.history.show()

    @Slot()
    def showSettings(self) -> None:
        dialog = SettingsDialog(self.settings, self.notes.root, self._save_preferences, self.darkTheme)
        dialog.exec()

    def _save_preferences(self, threads: int, folder: str, model: str | None = None,
                          hotkey: str | None = None) -> bool:
        path = Path(folder).expanduser().resolve()
        if not path.is_dir():
            raise ValueError("Папка заметок не существует")
        model_path = Path(model).expanduser().resolve() if model else None
        current_model = Path(self.settings.values.get("speech_model_directory") or model_directory()).resolve()
        if model_path and model_path != current_model:
            validate_model(model_path)
        changed = path != self.notes.root.resolve()
        if changed and not self.notes.save():
            return False
        repository = NotesRepository(path) if changed else self.notes.repository
        values = {"speech_cpu_threads": threads, "notes_directory": str(path)}
        if model_path is not None:
            values["speech_model_directory"] = str(model_path)
        if hotkey is not None:
            values["record_hotkey"] = hotkey
        self.settings.save(values)
        if hotkey is not None:
            self.record_hotkey.set_sequence(hotkey)
        if changed:
            self.notes.replace_repository(repository)
        return True

    @Slot()
    def quit(self) -> None:
        self.app.quit()
