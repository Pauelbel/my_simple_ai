import json
from datetime import datetime
from pathlib import Path

from ..paths import app_data_dir


class RecognitionHistory:
    def __init__(self) -> None:
        self.path: Path = app_data_dir() / "recognition_history.json"

    def list(self) -> list[dict]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []

    def add(self, text: str) -> None:
        items = self.list()
        items.insert(0, {"created_at": datetime.now().isoformat(timespec="seconds"), "text": text})
        self.path.write_text(json.dumps(items[:100], ensure_ascii=False, indent=2), encoding="utf-8")

    def clear(self) -> None:
        self.path.write_text("[]", encoding="utf-8")
