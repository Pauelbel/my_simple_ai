import os
import sys
from importlib.resources import files
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication, QMessageBox

from desktop_assistant.controller import AssistantController
from desktop_assistant.core.single_instance import acquire_instance_lock


def main() -> int:
    # Wayland does not provide a general always-on-top request; XWayland does.
    if (sys.platform.startswith("linux") and os.environ.get("XDG_SESSION_TYPE") == "wayland"
            and os.environ.get("DISPLAY") and not os.environ.get("QT_QPA_PLATFORM")):
        os.environ["QT_QPA_PLATFORM"] = "xcb"
    app = QApplication(sys.argv)
    app.setApplicationName("DesktopAssistant")
    app.setOrganizationName("DesktopAssistant")
    instance_lock = acquire_instance_lock()
    if instance_lock is None:
        QMessageBox.information(None, "Desktop Assistant", "Desktop Assistant уже запущен.")
        return 0
    package_dir = Path(str(files("desktop_assistant")))
    app.setWindowIcon(QIcon(str(package_dir / "assets" / "assistant-icon.png")))
    controller = AssistantController(app)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("assistant", controller)
    engine.rootContext().setContextProperty("dictation", controller.dictation)
    engine.load(QUrl.fromLocalFile(str(package_dir / "ui" / "overlay" / "Head.qml")))
    if not engine.rootObjects():
        return 1
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
