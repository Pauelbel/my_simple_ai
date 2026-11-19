from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtMultimedia import QAudioInput, QMediaCaptureSession, QMediaFormat, QMediaRecorder

from ..paths import app_data_dir


class AudioRecorder(QObject):
    recording_started = Signal()
    recording_finished = Signal(str)
    error = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.capture = QMediaCaptureSession()
        self.audio_input = QAudioInput()
        self.capture.setAudioInput(self.audio_input)
        self.recorder = QMediaRecorder()
        self.capture.setRecorder(self.recorder)
        self.recorder.recorderStateChanged.connect(self._state_changed)
        self.recorder.errorOccurred.connect(self._recording_error)
        media_format = QMediaFormat(QMediaFormat.FileFormat.Wave)
        media_format.setAudioCodec(QMediaFormat.AudioCodec.Wave)
        self.recorder.setMediaFormat(media_format)
        self.recorder.setAudioChannelCount(1)
        self.recorder.setAudioSampleRate(16000)
        self._output = ""
        self._requested_stop = False

    def start(self) -> None:
        if self.recorder.recorderState() == QMediaRecorder.RecorderState.RecordingState:
            return
        recordings = app_data_dir() / "recordings"
        recordings.mkdir(exist_ok=True)
        self._output = str(recordings / f"{uuid4().hex}.wav")
        self._requested_stop = False
        self.recorder.setOutputLocation(QUrl.fromLocalFile(self._output))
        self.recorder.record()

    def stop(self) -> None:
        if self.recorder.recorderState() == QMediaRecorder.RecorderState.RecordingState:
            self._requested_stop = True
            self.recorder.stop()

    def _state_changed(self, state: QMediaRecorder.RecorderState) -> None:
        if state == QMediaRecorder.RecorderState.RecordingState:
            self.recording_started.emit()
        elif self._requested_stop and state == QMediaRecorder.RecorderState.StoppedState:
            self._requested_stop = False
            if Path(self._output).exists():
                self.recording_finished.emit(self._output)
            else:
                self.error.emit("Не удалось создать аудиозапись")

    def _recording_error(self, _error, message: str) -> None:
        self._requested_stop = False
        self.recorder.stop()
        if self._output:
            self.cleanup(self._output)
        self.error.emit(message)

    def cleanup(self, path: str) -> None:
        recording = Path(path)
        if recording.parent.resolve() == (app_data_dir() / "recordings").resolve():
            try:
                recording.unlink(missing_ok=True)
            except OSError:
                pass
