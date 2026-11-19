"""Run with QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software python -m unittest discover -s tests."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

from PySide6.QtCore import QObject, Qt
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QInputDialog

from desktop_assistant.notes_window import NotesWindow
from desktop_assistant.services.notes import NotesRepository
from desktop_assistant.controller import AssistantController


class NotesWorkspaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setOrganizationName("NotesWorkspaceTests")
        cls.app.setApplicationName("NotesWorkspaceTests")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.repo = NotesRepository.__new__(NotesRepository)
        self.repo.root = Path(self.temp.name)
        self.repo.create_folder("", "Работа")
        self.repo.create_folder("Работа", "Вложенная")
        self.repo.save("Работа/Вложенная/Идея.md", "# Идея\n\nТекст заметки")
        self.repo.save("Вторая.md", "# Вторая\n\nПоисковая фраза")
        self.window = NotesWindow(self.repo)
        self.bridge = self.window.bridge
        self.errors = []
        self.bridge.error = lambda error: self.errors.append(str(error))

    def tearDown(self):
        self.bridge._dirty = False
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()
        self.temp.cleanup()

    def test_qml_loads_and_both_themes_render(self):
        self.assertEqual(self.window.view.status(), QQuickWidget.Ready)
        self.window.show()
        self.bridge.openNote("Работа/Вложенная/Идея.md")
        QTest.qWait(60)
        first = self.window.view.grabFramebuffer()
        self.assertFalse(first.isNull())
        first_color = first.pixelColor(500, 500)
        self.bridge.toggleTheme()
        QTest.qWait(60)
        second = self.window.view.grabFramebuffer()
        self.assertNotEqual(first_color, second.pixelColor(500, 500))
        self.assertEqual(self.errors, [])

    def test_tree_expansion_and_folder_filter(self):
        self.bridge.toggleFolder("Работа")
        self.bridge.toggleFolder("Работа/Вложенная")
        self.assertIn("Работа/Вложенная/Идея.md", [r["path"] for r in self.bridge.treeRows])
        self.bridge.toggleFolder("Работа")
        self.assertNotIn("Работа/Вложенная/Идея.md", [r["path"] for r in self.bridge.treeRows])
        self.bridge.select("Работа/Вложенная", True)
        self.assertEqual(len(self.bridge.notes), 1)
        self.bridge.search("нет совпадений")
        self.assertEqual(self.bridge.notes, [])
        self.bridge.select("", True)
        self.bridge.search("Поисковая")
        self.assertEqual(self.bridge.notes[0]["path"], "Вторая.md")

    def test_edit_save_and_navigation(self):
        self.bridge.openNote("Вторая.md")
        self.bridge.updateContent("# Изменено\n\nНовый текст")
        self.assertTrue(self.bridge.dirty)
        self.bridge.openNote("Работа/Вложенная/Идея.md")
        self.assertEqual(self.repo.read("Вторая.md"), "# Изменено\n\nНовый текст")
        self.assertFalse(self.bridge.dirty)
        self.assertEqual(self.bridge.currentPath, "Работа/Вложенная/Идея.md")

    def test_reading_does_not_update_modification_date(self):
        before = self.repo.resolve("Вторая.md").stat().st_mtime_ns
        self.bridge.openNote("Вторая.md")
        self.bridge.save()
        self.bridge.select("", True)
        self.assertEqual(before, self.repo.resolve("Вторая.md").stat().st_mtime_ns)

    def test_failed_save_keeps_document_and_prevents_close(self):
        self.bridge.openNote("Вторая.md")
        self.bridge.updateContent("Не потерять")
        with patch.object(self.repo, "save", side_effect=OSError("Нет места")):
            self.bridge.openNote("Работа/Вложенная/Идея.md")
            self.assertEqual(self.bridge.currentPath, "Вторая.md")
            self.assertEqual(self.bridge.content, "Не потерять")
            self.assertTrue(self.bridge.dirty)
            self.window.show()
            self.assertFalse(self.window.close())
        self.assertTrue(self.errors)

    def test_rename_and_move_open_folder_preserve_content(self):
        self.bridge.openNote("Работа/Вложенная/Идея.md")
        self.bridge.updateContent("Правки перед переносом")
        with patch.object(QInputDialog, "getText", return_value=("Проекты", True)):
            self.bridge.rename("Работа")
        self.assertEqual(self.bridge.currentPath, "Проекты/Вложенная/Идея.md")
        self.assertEqual(self.repo.read(self.bridge.currentPath), "Правки перед переносом")
        with patch.object(QInputDialog, "getItem", return_value=("Все заметки (корень)", True)):
            self.bridge.move("Проекты/Вложенная")
        self.assertEqual(self.bridge.currentPath, "Вложенная/Идея.md")
        self.assertEqual(self.repo.read(self.bridge.currentPath), "Правки перед переносом")
        self.assertEqual(self.errors, [])

    def test_file_operations_reject_collision_cycle_and_escape(self):
        self.repo.save("Работа/Вторая.md", "Существующее содержимое")
        with self.assertRaises(ValueError): self.repo.move("Вторая.md", "Работа")
        with self.assertRaises(ValueError): self.repo.move("Работа", "Работа/Вложенная")
        with self.assertRaises(ValueError): self.repo.move("Вторая.md", "..")
        with self.assertRaises(ValueError): self.repo.delete("")
        with self.assertRaises(ValueError): self.repo.rename("", "Другое")
        with self.assertRaises(ValueError): self.repo.delete("Работа")
        self.assertEqual(self.repo.read("Работа/Вторая.md"), "Существующее содержимое")

    def test_editor_binding_formatting_and_keyboard_save(self):
        self.bridge.openNote("Вторая.md")
        self.bridge.setEditing(True)
        self.window.show()
        QTest.qWait(60)
        editor = self.window.view.rootObject().findChild(QObject, "markdownEditor")
        editor.setProperty("text", "Текст")
        self.assertEqual(self.bridge.content, "Текст")
        editor.forceActiveFocus()
        QTest.keyClick(self.window.view, Qt.Key_A, Qt.ControlModifier)
        QTest.keyClick(self.window.view, Qt.Key_B, Qt.ControlModifier)
        self.assertEqual(self.bridge.content, "**Текст**")
        QTest.keyClick(self.window.view, Qt.Key_S, Qt.ControlModifier)
        self.assertEqual(self.repo.read("Вторая.md"), "**Текст**")
        self.assertFalse(self.bridge.dirty)

    def test_changing_notes_directory_saves_edits_and_persists(self):
        base = Path(self.temp.name)
        old = base / "old"
        new = base / "new"
        old.mkdir()
        new.mkdir()
        with patch("desktop_assistant.settings.app_data_dir", return_value=base), \
             patch("desktop_assistant.services.notes.app_data_dir", return_value=base):
            controller = AssistantController(self.app)
            controller.notes = NotesRepository(old)
            controller.notes.save("note.md", "before")
            controller.notes_window = NotesWindow(controller.notes)
            controller.notes_window.bridge.openNote("note.md")
            controller.notes_window.bridge.updateContent("after")
            self.assertTrue(controller._save_preferences(4, str(new)))
            self.assertEqual((old / "note.md").read_text(), "after")
            self.assertEqual(controller.notes.root, new)
            self.assertEqual(AssistantController(self.app).notes.root, new)

    def test_failed_note_save_prevents_directory_change(self):
        base = Path(self.temp.name)
        new = base / "new"
        new.mkdir()
        with patch("desktop_assistant.settings.app_data_dir", return_value=base), \
             patch("desktop_assistant.services.notes.app_data_dir", return_value=base):
            controller = AssistantController(self.app)
            controller.notes_window = self.window
            self.bridge.openNote("Вторая.md")
            self.bridge.updateContent("Не потерять")
            with patch.object(self.repo, "save", side_effect=OSError("Нет места")):
                self.assertFalse(controller._save_preferences(4, str(new)))
            self.assertEqual(self.bridge.content, "Не потерять")
            self.assertNotEqual(controller.notes.root, new)
            self.assertFalse(controller.settings.path.exists())

    def test_model_selection_is_saved_and_invalid_model_rejected(self):
        from desktop_assistant.services.speech_model import REQUIRED_FILES
        base = Path(self.temp.name)
        model = base / "model"
        model.mkdir()
        with patch("desktop_assistant.settings.app_data_dir", return_value=base), \
             patch("desktop_assistant.services.notes.app_data_dir", return_value=base):
            controller = AssistantController(self.app)
            with self.assertRaises(RuntimeError):
                controller._save_preferences(2, str(controller.notes.root), str(model))
            for name in REQUIRED_FILES:
                (model / name).write_text("{}")
            self.assertTrue(controller._save_preferences(2, str(controller.notes.root), str(model)))
            self.assertEqual(AssistantController(self.app).settings.values["speech_model_directory"], str(model))


if __name__ == "__main__":
    unittest.main()
