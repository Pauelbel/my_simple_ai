from pathlib import Path

from PySide6.QtCore import QObject, QSettings, Signal

from .repository import NotesRepository
from .window import NotesWindow


class NotesController(QObject):
    themeChanged = Signal()
    historyRequested = Signal()
    settingsRequested = Signal()
    quitRequested = Signal()

    def __init__(self, repository: NotesRepository) -> None:
        super().__init__()
        self.repository = repository
        self.window: NotesWindow | None = None

    @property
    def root(self) -> Path:
        return self.repository.root

    @property
    def dark_theme(self) -> bool:
        if self.window is not None:
            return self.window.bridge.dark
        return QSettings().value("notes/dark", True, type=bool)

    def show(self) -> None:
        if self.window is None:
            self.window = NotesWindow(self.repository)
            self.window.bridge.themeChanged.connect(self.themeChanged.emit)
            self.window.bridge.historyRequested.connect(self.historyRequested.emit)
            self.window.bridge.settingsRequested.connect(self.settingsRequested.emit)
            self.window.bridge.quitRequested.connect(self.quitRequested.emit)
        self.window.showNormal()
        self.window.raise_()
        self.window.activateWindow()

    def save(self) -> bool:
        return self.window.bridge.save() if self.window is not None else True

    def replace_repository(self, repository: NotesRepository) -> None:
        was_visible = self.window is not None and self.window.isVisible()
        if self.window is not None:
            self.window.close()
            self.window.deleteLater()
            self.window = None
        self.repository = repository
        if was_visible:
            self.show()
