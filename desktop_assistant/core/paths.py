from pathlib import Path

from PySide6.QtCore import QStandardPaths


def app_data_dir() -> Path:
    location = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)
    path = Path(location)
    path.mkdir(parents=True, exist_ok=True)
    return path
