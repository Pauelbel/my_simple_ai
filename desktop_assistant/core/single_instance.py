from PySide6.QtCore import QLockFile

from desktop_assistant.core.paths import app_data_dir


def acquire_instance_lock() -> QLockFile | None:
    lock = QLockFile(str(app_data_dir() / "instance.lock"))
    if lock.tryLock(100):
        return lock
    return None
