from PySide6.QtCore import QObject

from desktop_assistant.core.windowing import set_always_on_top

from .repository import RecognitionHistory
from .window import HistoryWindow


class HistoryController(QObject):
    def __init__(self, history: RecognitionHistory) -> None:
        super().__init__()
        self.repository = history
        self.window: HistoryWindow | None = None
        self._always_on_top = True

    def set_always_on_top(self, enabled: bool) -> None:
        self._always_on_top = enabled
        if self.window is not None:
            set_always_on_top(self.window, enabled)

    def show(self) -> None:
        if self.window is None:
            self.window = HistoryWindow(self.repository)
        self.refresh()
        set_always_on_top(self.window, self._always_on_top)
        self.window.showNormal()
        self.window.raise_()
        self.window.activateWindow()

    def refresh(self) -> None:
        if self.window is not None:
            self.window.refresh()
