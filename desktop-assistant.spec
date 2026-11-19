# Build with: .venv/bin/pyinstaller desktop-assistant.spec --noconfirm
import json
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs
from desktop_assistant.services.speech_model import MODEL_BIN_SHA256, REQUIRED_FILES, validate_model, file_sha256

root = Path(SPECPATH)
model = validate_model(root / "models" / "faster-whisper-small")
manifest = json.loads((model / "manifest.json").read_text(encoding="utf-8"))
if manifest["sha256"]["model.bin"] != MODEL_BIN_SHA256:
    raise RuntimeError("Unexpected model revision; run scripts/prepare_speech_model.py")
for name in REQUIRED_FILES:
    if file_sha256(model / name) != manifest["sha256"][name]:
        raise RuntimeError(f"Model checksum mismatch: {name}")

datas = collect_data_files("desktop_assistant", includes=["qml/*.qml", "qml/notes/*.qml", "qml/notes/qmldir", "assets/*.png", "assets/*.ico", "assets/*.wav"])
datas += collect_data_files("faster_whisper")  # Includes the local Silero VAD model.
datas += [(str(model / name), "models/faster-whisper-small") for name in (*REQUIRED_FILES, "manifest.json", "README.md") if (model / name).is_file()]
binaries = collect_dynamic_libs("ctranslate2") + collect_dynamic_libs("onnxruntime")

a = Analysis([str(root / "desktop_assistant/__main__.py")], pathex=[str(root)],
             datas=datas, binaries=binaries,
             hiddenimports=["PySide6.QtMultimedia", "faster_whisper", "onnxruntime"])
pyz = PYZ(a.pure)
# Models stay in the installed application directory; no 500 MB extraction per launch.
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="DesktopAssistant", console=False,
          icon=str(root / "desktop_assistant/assets/assistant-icon.ico"))
coll = COLLECT(exe, a.binaries, a.datas, name="DesktopAssistant")
