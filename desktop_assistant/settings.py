import json
from pathlib import Path

from .paths import app_data_dir


DEFAULTS = {"speech_cpu_threads": 4, "always_on_top": True}



class Settings:
    def __init__(self) -> None:
        self.path: Path = app_data_dir() / "settings.json"
        self.values = DEFAULTS.copy()
        self.load()

    def load(self) -> None:
        try:
            self.values.update(json.loads(self.path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            pass

    def save(self, values: dict) -> None:
        self.values.update({key: values.get(key, self.values[key]) for key in DEFAULTS})
        self.path.write_text(json.dumps(self.values, ensure_ascii=False, indent=2), encoding="utf-8")
