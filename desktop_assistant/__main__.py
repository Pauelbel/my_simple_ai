import sys
from importlib.resources import files
from pathlib import Path

from PySide6.QtGui import QIcon
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
    package_dir = Path(str(files("desktop_assistant")))
    app.setWindowIcon(QIcon(str(package_dir / "assets" / "assistant-icon.png")))
    controller = AssistantController(app)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("assistant", controller)
    engine.load(QUrl.fromLocalFile(str(package_dir / "qml" / "Head.qml")))
    if not engine.rootObjects():
        return 1
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
