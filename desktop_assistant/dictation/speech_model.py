"""Offline speech model location and validation."""
import hashlib
import json
from pathlib import Path

MODEL_NAME = "faster-whisper-small"
MODEL_REPOSITORY = "Systran/faster-whisper-small"
MODEL_REVISION = "536b0662742c02347bc0e980a01041f333bce120"
MODEL_BIN_SHA256 = "3e305921506d8872816023e4c273e75d2419fb89b24da97b4fe7bce14170d671"
REQUIRED_FILES = ("model.bin", "config.json", "tokenizer.json", "vocabulary.txt")


def model_directory() -> Path:
    base = Path(__file__).resolve().parents[2]
    return base / "data" / "speech-models" / MODEL_NAME


def validate_model(directory: Path | None = None) -> Path:
    directory = directory if directory is not None else model_directory()
    missing = [name for name in REQUIRED_FILES if not (directory / name).is_file() or (directory / name).stat().st_size == 0]
    if missing:
        raise RuntimeError("Локальная модель распознавания отсутствует или неполна. "
                           "Запустите python scripts/prepare_speech_model.py. Отсутствуют: " + ", ".join(missing))
    # In particular, a missing tokenizer would otherwise trigger a network fallback.
    try:
        for name in ("config.json", "tokenizer.json"):
            with (directory / name).open(encoding="utf-8") as file:
                if not isinstance(json.load(file), dict):
                    raise ValueError(name)
    except (OSError, ValueError) as error:
        raise RuntimeError("Повреждены файлы локальной модели распознавания") from error
    return directory


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
