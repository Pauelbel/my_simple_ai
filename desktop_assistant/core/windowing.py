from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget


def set_always_on_top(window: QWidget, enabled: bool) -> None:
    visible = window.isVisible()
    window.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, enabled)
    if visible:
        window.show()
