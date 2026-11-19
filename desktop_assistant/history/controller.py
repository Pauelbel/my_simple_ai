from PySide6.QtCore import QObject

from .repository import RecognitionHistory
from .window import HistoryWindow


class HistoryController(QObject):
    def __init__(self, history: RecognitionHistory, dark: bool = True) -> None:
        super().__init__()
        self.repository = history
        self.window: HistoryWindow | None = None
        self._dark = dark

    def set_dark_theme(self, dark: bool) -> None:
        self._dark = dark
        if self.window is not None:
            self.window.apply_theme(dark)

    def show(self) -> None:
        if self.window is None:
            self.window = HistoryWindow(self.repository, self._dark)
        self.refresh()
        self.window.showNormal()
        self.window.raise_()
        self.window.activateWindow()

    def refresh(self) -> None:
        if self.window is not None:
            self.window.refresh()
