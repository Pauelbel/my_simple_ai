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

from desktop_assistant.dictation.speech_model import REQUIRED_FILES, validate_model
from desktop_assistant.dictation.transcription import Transcriber, format_text
from desktop_assistant.history.repository import RecognitionHistory
from desktop_assistant.settings.store import Settings


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
        with patch("desktop_assistant.dictation.transcription.validate_model", return_value=self.root), patch.dict(sys.modules, {"faster_whisper": SimpleNamespace(WhisperModel=factory)}):
            first = self.worker._load_model({"speech_cpu_threads": 2})
            self.assertIs(first, self.worker._load_model({"speech_cpu_threads": 2}))
        factory.assert_called_once_with(str(self.root), device="cpu", compute_type="int8", cpu_threads=2, num_workers=1, local_files_only=True)

    def test_selected_model_is_checked_loaded_and_reloaded_when_changed(self):
        first = self.root / "first"
        second = self.root / "second"
        for directory in (first, second):
            directory.mkdir()
            for name in REQUIRED_FILES:
                (directory / name).write_text("{}")
        factory = Mock(side_effect=[object(), object()])
        with patch("desktop_assistant.dictation.transcription.find_spec", return_value=True), \
             patch.dict(sys.modules, {"faster_whisper": SimpleNamespace(WhisperModel=factory)}):
            self.worker.check_ready({"speech_model_directory": str(first)})
            self.worker._load_model({"speech_model_directory": str(first)})
            self.worker._load_model({"speech_model_directory": str(second)})
        self.assertEqual([call.args[0] for call in factory.call_args_list], [str(first), str(second)])
        (first / "tokenizer.json").unlink()
        with self.assertRaisesRegex(RuntimeError, "tokenizer.json"):
            self.worker.check_ready({"speech_model_directory": str(first)})

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
        with patch("desktop_assistant.settings.store.app_data_dir", return_value=self.root):
            settings = Settings()
            self.assertEqual(settings.values["speech_cpu_threads"], 4)
            self.assertTrue(settings.values["always_on_top"])
            settings.save({"speech_cpu_threads": 2})
            self.assertEqual(Settings().values["speech_cpu_threads"], 2)
            self.assertTrue(Settings().values["always_on_top"])
            self.assertEqual(Settings().values["api_key"], "old-value")


class AudioRecorderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_audio_input_is_retained_by_capture_session(self):
        from desktop_assistant.dictation.recorder import AudioRecorder
        recorder = AudioRecorder()
        self.assertIsNotNone(recorder.capture.audioInput())


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
        self.app_settings = SimpleNamespace(values={'speech_cpu_threads': 4, 'always_on_top': True})
        self.app_settings.save = Mock(side_effect=lambda updates: self.app_settings.values.update(updates))
        with patch('desktop_assistant.dictation.controller.AudioRecorder', return_value=self.recorder), patch('desktop_assistant.dictation.controller.Transcriber', return_value=self.transcriber), patch('desktop_assistant.controller.RecognitionHistory', return_value=self.history), patch('desktop_assistant.controller.NotesRepository'), patch('desktop_assistant.controller.Settings', return_value=self.app_settings):
            self.controller = AssistantController(self.app)
            self.dictation = self.controller.dictation
        self.notifications=[]
        self.controller.notification.connect(self.notifications.append)

    def test_click_record_stop_copy_history_and_cleanup(self):
        self.dictation.toggleRecording()
        self.assertEqual(self.dictation.status, 'recording')
        self.dictation.toggleRecording()
        self.assertEqual(self.dictation.status, 'processing')
        self.transcriber.transcribe.assert_called_once_with('/tmp/test.wav', {'speech_cpu_threads': 4, 'always_on_top': True})
        self.dictation.toggleRecording()
        self.recorder.start.assert_called_once()
        self.transcriber.completed.emit('Привет, мир!')
        self.transcriber.finished.emit('/tmp/test.wav')
        self.assertEqual(self.app.clipboard().text(), 'Привет, мир!')
        self.history.add.assert_called_once_with('Привет, мир!')
        self.recorder.cleanup.assert_called_once_with('/tmp/test.wav')
        self.assertEqual(self.dictation.status, 'idle')

    def test_missing_model_does_not_start_recording(self):
        self.transcriber.check_ready.side_effect=RuntimeError('Нет локальной модели')
        self.dictation.toggleRecording()
        self.recorder.start.assert_not_called()
        self.assertEqual(self.dictation.status, 'idle')
        self.assertIn('Нет локальной модели', self.notifications)

    def test_recognition_failure_preserves_clipboard(self):
        self.app.clipboard().setText('Предыдущий текст')
        self.dictation.toggleRecording(); self.dictation.toggleRecording()
        self.transcriber.failed.emit('Речь не обнаружена')
        self.assertEqual(self.app.clipboard().text(), 'Предыдущий текст')
        self.history.add.assert_not_called()
        self.assertEqual(self.dictation.status, 'idle')

    def test_busy_transcriber_restores_idle_and_cleans_recording(self):
        self.transcriber.transcribe.return_value = False
        self.dictation.toggleRecording(); self.dictation.toggleRecording()
        self.recorder.cleanup.assert_called_once_with('/tmp/test.wav')
        self.assertEqual(self.dictation.status, 'idle')
        self.assertIn('Распознавание уже выполняется', self.notifications[-1])

    def test_always_on_top_toggle_updates_open_history_and_notes(self):
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QDialog
        self.history.list.return_value = []
        self.controller.showHistory()
        notes = QDialog()
        self.controller.notes.window = notes
        notes.show()
        history = self.controller.history.window
        try:
            self.assertTrue(history.windowFlags() & Qt.WindowStaysOnTopHint)
            self.controller.notes.set_always_on_top(True)
            self.assertTrue(notes.windowFlags() & Qt.WindowStaysOnTopHint)

            self.controller.toggleAlwaysOnTop()
            self.assertFalse(self.controller.alwaysOnTop)
            self.assertFalse(history.windowFlags() & Qt.WindowStaysOnTopHint)
            self.assertFalse(notes.windowFlags() & Qt.WindowStaysOnTopHint)
            self.app_settings.save.assert_called_with({'always_on_top': False})

            self.controller.toggleAlwaysOnTop()
            self.assertTrue(self.controller.alwaysOnTop)
            self.assertTrue(history.windowFlags() & Qt.WindowStaysOnTopHint)
            self.assertTrue(notes.windowFlags() & Qt.WindowStaysOnTopHint)
        finally:
            history.close()
            notes.close()

    def test_history_window_is_modeless_and_can_be_cleared(self):
        from PySide6.QtWidgets import QMessageBox
        item = {'created_at': '2026-11-18T21:31:07', 'text': 'Привет'}
        self.history.list.side_effect = [[item], [item], []]
        self.controller.showHistory()
        window = self.controller.history.window
        try:
            self.assertTrue(window.isVisible())
            self.assertFalse(window.isModal())
            with patch('desktop_assistant.history.window.QMessageBox.question', return_value=QMessageBox.StandardButton.Yes):
                window.clear_button.click()
            self.history.clear.assert_called_once()
            self.assertEqual(window.text.toPlainText(), 'История пока пуста.')
            self.assertFalse(window.clear_button.isEnabled())
        finally:
            window.close()

    def test_qml_click_starts_recording_and_processing_indicator_animates(self):
        from pathlib import Path
        from PySide6.QtCore import QObject, QPoint, QUrl, Qt
        from PySide6.QtQml import QQmlApplicationEngine
        from PySide6.QtTest import QTest

        engine = QQmlApplicationEngine()
        engine.rootContext().setContextProperty('assistant', self.controller)
        engine.rootContext().setContextProperty('dictation', self.dictation)
        engine.load(QUrl.fromLocalFile(str(Path('desktop_assistant/ui/overlay/Head.qml').resolve())))
        self.assertTrue(engine.rootObjects())
        window = engine.rootObjects()[0]
        try:
            window.show()
            QTest.qWait(80)
            self.assertTrue(window.flags() & Qt.WindowStaysOnTopHint)
            self.assertTrue(window.flags() & Qt.WindowDoesNotAcceptFocus)
            self.assertFalse(window.flags() & Qt.Tool)
            QTest.mouseClick(window, Qt.RightButton, Qt.NoModifier, QPoint(68, 68))
            QTest.qWait(50)
            menu = window.findChild(QObject, 'assistantMenu')
            self.assertTrue(menu.property('visible'))
            self.assertFalse(window.flags() & Qt.WindowDoesNotAcceptFocus)
            menu.close()
            QTest.qWait(150)
            self.assertTrue(window.flags() & Qt.WindowDoesNotAcceptFocus)
            QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, QPoint(68, 68))
            QTest.qWait(30)
            self.recorder.start.assert_called_once()
            self.assertEqual(self.dictation.status, 'recording')

            self.assertIsNotNone(window.findChild(QObject, 'assistantOrb'))
            sound = window.findChild(QObject, 'recordingStartSound')
            self.assertTrue(sound.property('source').toString().endswith('recording-start.wav'))
            indicator = window.findChild(QObject, 'processingIndicator')
            self.assertFalse(indicator.property('visible'))
            self.dictation.toggleRecording()
            QTest.qWait(100)
            self.assertTrue(indicator.property('visible'))
            phase = indicator.property('phase')
            QTest.qWait(100)
            self.assertNotEqual(indicator.property('phase'), phase)
            self.transcriber.completed.emit('Готово')
            QTest.qWait(30)
            self.assertFalse(indicator.property('visible'))
            self.assertIsNone(window.findChild(QObject, 'thoughtToast'))

            self.controller.toggleAlwaysOnTop()
            QTest.qWait(50)
            self.assertFalse(window.flags() & Qt.WindowStaysOnTopHint)
            pin_item = window.findChild(QObject, 'pinMenuItem')
            self.assertFalse(pin_item.property('checked'))
            self.controller.toggleAlwaysOnTop()
            QTest.qWait(50)
            self.assertTrue(window.flags() & Qt.WindowStaysOnTopHint)
        finally:
            window.close()
            window.deleteLater()
            self.app.processEvents()
            engine.deleteLater()
            self.app.processEvents()


class HistoryRepositoryTests(unittest.TestCase):
    def test_clear_removes_all_saved_recognitions(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch('desktop_assistant.history.repository.app_data_dir', return_value=Path(directory)):
                history = RecognitionHistory()
                history.add('Первая запись')
                history.add('Вторая запись')
                history.clear()
                self.assertEqual(history.list(), [])
                self.assertEqual(RecognitionHistory().list(), [])
