import sys
from pathlib import Path

from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QApplication

from desktop_assistant.controller import AssistantController


def main() -> int:
    # QApplication is required because the Markdown notes window uses QWidget.
    # It is a QGuiApplication subclass and remains fully compatible with QML.
    app = QApplication(sys.argv)
    app.setApplicationName("DesktopAssistant")
    app.setOrganizationName("DesktopAssistant")
    app.setWindowIcon(QIcon(str(Path(__file__).with_name("assets") / "assistant-icon.png")))
    controller = AssistantController(app)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("assistant", controller)
    engine.load(QUrl.fromLocalFile(str(Path(__file__).with_name("qml") / "Head.qml")))
    if not engine.rootObjects():
        return 1
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
