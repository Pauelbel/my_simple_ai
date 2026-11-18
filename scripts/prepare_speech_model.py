"""Build-time download only. The application itself never downloads models."""
import json
import sys
import shutil
from urllib.request import urlopen
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from desktop_assistant.services.speech_model import (
    MODEL_REPOSITORY, MODEL_REVISION, MODEL_BIN_SHA256, REQUIRED_FILES, model_directory, validate_model, file_sha256,
)


def main():
    directory = model_directory()
    directory.mkdir(parents=True, exist_ok=True)
    manifest_path = directory / "manifest.json"
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest["revision"] == MODEL_REVISION and manifest["sha256"]["model.bin"] == MODEL_BIN_SHA256 and all(
                (directory / name).is_file() and file_sha256(directory / name) == manifest["sha256"][name]
                for name in REQUIRED_FILES
            ):
                validate_model(directory)
                print(f"Offline model already prepared: {directory}")
                return
        except (OSError, ValueError, KeyError, RuntimeError):
            pass
    for name in (*REQUIRED_FILES, "README.md"):
        print(f"Downloading {name}…", flush=True)
        url = f"https://huggingface.co/{MODEL_REPOSITORY}/resolve/{MODEL_REVISION}/{name}"
        partial = directory / (name + ".part")
        try:
            with urlopen(url, timeout=120) as response, partial.open("wb") as target:
                shutil.copyfileobj(response, target, length=1024 * 1024)
            partial.replace(directory / name)
        finally:
            partial.unlink(missing_ok=True)
    validate_model(directory)
    hashes = {}
    for name in REQUIRED_FILES:
        hashes[name] = file_sha256(directory / name)
    if hashes["model.bin"] != MODEL_BIN_SHA256:
        raise RuntimeError("Downloaded model checksum does not match the pinned upstream model")
    (directory / "manifest.json").write_text(json.dumps({
        "repository": MODEL_REPOSITORY, "revision": MODEL_REVISION, "sha256": hashes,
    }, indent=2), encoding="utf-8")
    print(f"Offline model prepared: {directory}")


if __name__ == "__main__":
    main()
