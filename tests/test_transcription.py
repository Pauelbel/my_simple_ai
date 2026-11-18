import json
import sys
import tempfile
import threading
import unittest
import wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from PySide6.QtCore import QCoreApplication

from desktop_assistant.services.speech_model import REQUIRED_FILES, validate_model
from desktop_assistant.services.transcription import Transcriber, format_text
from desktop_assistant.settings import Settings


class TranscriptionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.audio = self.root / "speech.wav"
        with wave.open(str(self.audio), "wb") as audio:
            audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(16000)
            audio.writeframes(b"\0" * 32000)
        self.worker = Transcriber()
        self.completed, self.failed, self.finished = [], [], []
        # Direct connections let these unit tests collect worker results without an event loop.
        from PySide6.QtCore import Qt
        self.worker.completed.connect(self.completed.append, Qt.DirectConnection)
        self.worker.failed.connect(self.failed.append, Qt.DirectConnection)
        self.worker.finished.connect(self.finished.append, Qt.DirectConnection)

    def tearDown(self):
        if self.worker._thread: self.worker._thread.join(timeout=5)
        self.temp.cleanup()

    def run_worker(self, model):
        with patch.object(self.worker, "_load_model", return_value=model):
            self.assertTrue(self.worker.transcribe(str(self.audio), {}))
            self.worker._thread.join(timeout=5)
            self.assertFalse(self.worker._thread.is_alive())

    def test_lazy_segments_are_consumed_in_worker_and_punctuation_preserved(self):
        thread_ids = []
        def segments():
            thread_ids.append(threading.get_ident())
            yield SimpleNamespace(text=" Привет, мир!")
            yield SimpleNamespace(text=" Это проверка.")
        model = Mock()
        model.transcribe.return_value = (segments(), None)
        self.run_worker(model)
        self.assertEqual(self.completed, ["Привет, мир! Это проверка."])
        self.assertNotEqual(thread_ids[0], threading.get_ident())
        kwargs = model.transcribe.call_args.kwargs
        self.assertEqual(kwargs["language"], "ru")
        self.assertTrue(kwargs["vad_filter"])
        self.assertEqual(self.finished, [str(self.audio)])

    def test_silence_does_not_emit_text(self):
        model = Mock()
        model.transcribe.return_value = (iter([]), None)
        self.run_worker(model)
        self.assertEqual(self.completed, [])
        self.assertIn("Речь не обнаружена", self.failed[0])

    def test_failure_in_generator_releases_worker(self):
        def broken():
            raise RuntimeError("decoder failed")
            yield
        model = Mock()
        model.transcribe.return_value = (broken(), None)
        self.run_worker(model)
        self.assertIn("decoder failed", self.failed[0])
        self.assertFalse(self.worker._lock.locked())
        self.assertEqual(self.finished, [str(self.audio)])

    def test_parallel_request_is_rejected(self):
        entered, release = threading.Event(), threading.Event()
        def load(_settings):
            entered.set(); release.wait(3)
            return SimpleNamespace(transcribe=lambda *a, **kw: (iter([]), None))
        with patch.object(self.worker, "_load_model", side_effect=load):
            self.assertTrue(self.worker.transcribe(str(self.audio), {}))
            self.assertTrue(entered.wait(2))
            self.assertFalse(self.worker.transcribe(str(self.audio), {}))
            release.set()
            self.worker._thread.join(3)

    def test_model_is_reused_and_cpu_int8_offline_are_explicit(self):
        factory = Mock(return_value=object())
        with patch("desktop_assistant.services.transcription.validate_model", return_value=self.root), patch.dict(sys.modules, {"faster_whisper": SimpleNamespace(WhisperModel=factory)}):
            first = self.worker._load_model({"speech_cpu_threads": 2})
            self.assertIs(first, self.worker._load_model({"speech_cpu_threads": 2}))
        factory.assert_called_once_with(str(self.root), device="cpu", compute_type="int8", cpu_threads=2, num_workers=1, local_files_only=True)

    def test_missing_tokenizer_is_rejected_before_model_import(self):
        for name in REQUIRED_FILES:
            (self.root / name).write_text("{}")
        (self.root / "tokenizer.json").unlink()
        with self.assertRaisesRegex(RuntimeError, "tokenizer.json"):
            validate_model(self.root)

    def test_invalid_json_is_rejected(self):
        for name in REQUIRED_FILES:
            (self.root / name).write_text("invalid")
        with self.assertRaisesRegex(RuntimeError, "Повреждены"):
            validate_model(self.root)

    def test_formatting_preserves_names_case_and_end_punctuation(self):
        self.assertEqual(format_text('  iPhone,  API?\nДа!  '), 'iPhone, API? Да!')
        self.assertEqual(format_text('«Привет!»'), '«Привет!»')
        self.assertEqual(format_text(''), '')

    def test_existing_settings_migrate_without_requiring_api(self):
        (self.root / "settings.json").write_text(json.dumps({"api_key": "old-value", "model": "old-cloud-model"}))
        with patch("desktop_assistant.settings.app_data_dir", return_value=self.root):
            settings = Settings()
            self.assertEqual(settings.values["speech_cpu_threads"], 4)
            settings.save({"speech_cpu_threads": 2})
            self.assertEqual(Settings().values["speech_cpu_threads"], 2)
            self.assertEqual(Settings().values["api_key"], "old-value")


class DictationFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        from PySide6.QtCore import QObject, Signal
        from desktop_assistant.controller import AssistantController
        class FakeRecorder(QObject):
            recording_started = Signal()
            recording_finished = Signal(str)
            error = Signal(str)
            def __init__(self):
                super().__init__()
                self.start = Mock(side_effect=self.recording_started.emit)
                self.stop = Mock(side_effect=lambda: self.recording_finished.emit('/tmp/test.wav'))
                self.cleanup = Mock()
        class FakeTranscriber(QObject):
            completed = Signal(str)
            failed = Signal(str)
            progress = Signal(str)
            finished = Signal(str)
            def __init__(self):
                super().__init__()
                self.check_ready = Mock()
                self.transcribe = Mock(return_value=True)
        self.recorder, self.transcriber = FakeRecorder(), FakeTranscriber()
        self.history = Mock()
        with patch('desktop_assistant.controller.AudioRecorder', return_value=self.recorder), patch('desktop_assistant.controller.Transcriber', return_value=self.transcriber), patch('desktop_assistant.controller.RecognitionHistory', return_value=self.history), patch('desktop_assistant.controller.NotesRepository'), patch('desktop_assistant.controller.Settings', return_value=SimpleNamespace(values={'speech_cpu_threads':4})):
            self.controller = AssistantController(self.app)
        self.notifications=[]
        self.controller.notification.connect(self.notifications.append)

    def test_click_record_stop_copy_history_and_cleanup(self):
        self.controller.toggleRecording()
        self.assertEqual(self.controller.status, 'recording')
        self.controller.toggleRecording()
        self.assertEqual(self.controller.status, 'processing')
        self.transcriber.transcribe.assert_called_once_with('/tmp/test.wav', {'speech_cpu_threads':4})
        self.controller.toggleRecording()
        self.recorder.start.assert_called_once()
        self.transcriber.completed.emit('Привет, мир!')
        self.transcriber.finished.emit('/tmp/test.wav')
        self.assertEqual(self.app.clipboard().text(), 'Привет, мир!')
        self.history.add.assert_called_once_with('Привет, мир!')
        self.recorder.cleanup.assert_called_once_with('/tmp/test.wav')
        self.assertEqual(self.controller.status, 'idle')

    def test_missing_model_does_not_start_recording(self):
        self.transcriber.check_ready.side_effect=RuntimeError('Нет локальной модели')
        self.controller.toggleRecording()
        self.recorder.start.assert_not_called()
        self.assertEqual(self.controller.status, 'idle')
        self.assertIn('Нет локальной модели', self.notifications)

    def test_recognition_failure_preserves_clipboard(self):
        self.app.clipboard().setText('Предыдущий текст')
        self.controller.toggleRecording(); self.controller.toggleRecording()
        self.transcriber.failed.emit('Речь не обнаружена')
        self.assertEqual(self.app.clipboard().text(), 'Предыдущий текст')
        self.history.add.assert_not_called()
        self.assertEqual(self.controller.status, 'idle')
