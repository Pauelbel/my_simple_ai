"""QML notes workspace and its filesystem-backed presentation model."""
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, Property, QSettings, QUrl, Signal, Slot
from PySide6.QtGui import QColor, QDesktopServices, QFont, QPalette, QTextBlockFormat, QTextCursor, QTextDocument
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtWidgets import QInputDialog, QMainWindow, QMessageBox

from .services.notes import NotesRepository


class NotesBridge(QObject):
    changed = Signal()
    collectionsChanged = Signal()
    documentChanged = Signal()
    themeChanged = Signal()

    def __init__(self, repository: NotesRepository, window: QMainWindow):
        super().__init__(window)
        self.repository = repository
        self.window = window
        self.preferences = QSettings()
        self._dark = self.preferences.value("notes/dark", True, type=bool)
        self._path = ""
        self._folder = ""
        self._selected = ""
        self._content = ""
        self._dirty = False
        self._query = ""
        self._editing = False
        self._expanded = {""}
        self._preview_style = ("Sans Serif", 16, "#96b6f1")
        self._preview_cache = (None, "")
        self._tree = []
        self._notes = []
        self.refresh()

    @Property("QVariantList", notify=collectionsChanged)
    def treeRows(self): return self._tree

    @Property("QVariantList", notify=collectionsChanged)
    def notes(self): return self._notes

    @Property(str, notify=changed)
    def selectedPath(self): return self._selected

    @Property(str, notify=changed)
    def folderTitle(self): return Path(self._folder).name if self._folder else "Все заметки"

    @Property(str, notify=changed)
    def currentPath(self): return self._path

    @Property(str, notify=changed)
    def title(self): return Path(self._path).stem if self._path else "Выберите заметку"

    @Property(str, notify=documentChanged)
    def content(self): return self._content

    @Property(bool, notify=changed)
    def dirty(self): return self._dirty

    @Property(bool, notify=changed)
    def editing(self): return self._editing

    @Property(str, notify=changed)
    def statistics(self): return f"{len(self._content.split())} слов · {len(self._content)} символов"

    @Property(bool, notify=themeChanged)
    def dark(self): return self._dark

    @Property(str, notify=changed)
    def previewHtml(self):
        if self._editing:
            return self._preview_cache[1]
        key = (self._content, self._preview_style)
        if self._preview_cache[0] == key:
            return self._preview_cache[1]
        doc = QTextDocument()
        family, size, accent = self._preview_style
        font = QFont(family)
        font.setPixelSize(size)
        doc.setDefaultFont(font)
        doc.setDefaultStyleSheet(f"a {{ color: {accent}; }}")
        doc.setMarkdown(self._content)
        block = doc.begin()
        while block.isValid():
            cursor = QTextCursor(block)
            fmt = block.blockFormat()
            fmt.setLineHeight(145, QTextBlockFormat.LineHeightTypes.ProportionalHeight.value)
            fmt.setTopMargin(12 if fmt.headingLevel() else 4)
            fmt.setBottomMargin(10)
            cursor.setBlockFormat(fmt)
            block = block.next()
        self._preview_cache = (key, doc.toHtml())
        return self._preview_cache[1]

    @Slot(str, int, QColor)
    def setPreviewStyle(self, family, size, accent):
        self._preview_style = (family, size, accent.name())
        self.changed.emit()

    @Slot(QColor, QColor, QColor, QColor, QColor)
    def setDialogPalette(self, background, surface, text, accent, muted):
        palette = QPalette()
        for role, color in ((QPalette.Window, background), (QPalette.Base, surface),
                            (QPalette.Button, surface), (QPalette.WindowText, text),
                            (QPalette.Text, text), (QPalette.ButtonText, text),
                            (QPalette.Highlight, accent), (QPalette.HighlightedText, background),
                            (QPalette.PlaceholderText, muted)):
            palette.setColor(role, color)
        self.window.setPalette(palette)

    def error(self, error):
        QMessageBox.warning(self.window, "Заметки", str(error))

    def refresh(self):
        try:
            rows = [{"name": "Все заметки", "path": "", "folder": True,
                     "depth": 0, "expanded": "" in self._expanded, "guides": [], "last": True}]

            def append(nodes, depth, guides):
                for index, node in enumerate(nodes):
                    last = index == len(nodes) - 1
                    rows.append({**node, "depth": depth, "expanded": node["path"] in self._expanded,
                                 "guides": guides, "last": last})
                    if node["folder"] and node["path"] in self._expanded:
                        append(node["children"], depth + 1, guides + [not last])

            if "" in self._expanded:
                append(self.repository.tree(), 1, [])
            notes = self.repository.note_summaries(self._folder, self._query)
            for note in notes:
                note["date"] = datetime.fromtimestamp(note["modified"]).strftime("%d.%m.%Y · %H:%M")
            self._tree, self._notes = rows, notes
            self.collectionsChanged.emit()
            self.changed.emit()
        except (OSError, ValueError) as error:
            self.error(error)

    @Slot(str)
    def toggleFolder(self, path):
        if path in self._expanded: self._expanded.remove(path)
        else: self._expanded.add(path)
        self.refresh()

    @Slot(str, bool)
    def select(self, path, folder):
        if not self.save(): return
        if folder:
            self._folder = path
            self._selected = path
            self._path = ""
            self._content = ""
            self._editing = False
            self.documentChanged.emit()
            self.refresh()
        else:
            self.openNote(path)

    @Slot(str)
    def openNote(self, path):
        if path == self._path: return
        if not self.save(): return
        try:
            content = self.repository.read(path)
            self._path = path
            self._content = content
            self._selected = path
            # Opening from the tree selects the containing folder in the list.
            self._folder = Path(path).parent.as_posix() if Path(path).parent != Path(".") else ""
            self._expanded.add("")
            for parent in Path(path).parents:
                if parent != Path("."): self._expanded.add(parent.as_posix())
            self._dirty = False
            self.documentChanged.emit()
            self.refresh()
        except (OSError, ValueError) as error:
            self.error(error)

    @Slot(str)
    def updateContent(self, content):
        if not self._path or content == self._content: return
        self._content = content
        self._dirty = True
        self.changed.emit()

    @Slot(result=bool)
    def save(self):
        if not self._path or not self._dirty: return True
        try:
            self.repository.save(self._path, self._content)
            self._dirty = False
            self.refresh()
            return True
        except (OSError, ValueError) as error:
            self.error(error)
            return False

    @Slot(bool)
    def setEditing(self, editing):
        self._editing = editing
        self.changed.emit()

    @Slot()
    def toggleTheme(self):
        self._dark = not self._dark
        self.preferences.setValue("notes/dark", self._dark)
        self.themeChanged.emit()

    @Slot(str, bool)
    def create(self, parent, folder):
        if not self.save(): return
        title, ok = QInputDialog.getText(self.window, "Новая папка" if folder else "Новая заметка", "Название:")
        if not ok: return
        try:
            if folder:
                path = self.repository.create_folder(parent, title)
                self._expanded.add(parent)
                self._expanded.add(path)
                self.select(path, True)
            else:
                path = self.repository.create_note(parent, title)
                self.openNote(path)
                self.setEditing(True)
        except (OSError, ValueError) as error:
            self.error(error)

    @Slot(bool)
    def createHere(self, folder): self.create(self._folder, folder)

    @Slot(str)
    def rename(self, path):
        if not path or not self.save(): return
        title, ok = QInputDialog.getText(self.window, "Переименовать", "Новое название:", text=Path(path).stem if path.lower().endswith(".md") else Path(path).name)
        if not ok: return
        try:
            destination = self.repository.rename(path, title)
            self._relocated(path, destination)
        except (OSError, ValueError) as error:
            self.error(error)

    @Slot(str)
    def move(self, path):
        if not path or not self.save(): return
        folders = [""]
        def visit(nodes):
            for node in nodes:
                if node["folder"] and node["path"] != path and not node["path"].startswith(path + "/"):
                    folders.append(node["path"])
                    visit(node["children"])
        try:
            visit(self.repository.tree())
            labels = ["Все заметки (корень)"] + folders[1:]
            label, ok = QInputDialog.getItem(self.window, "Переместить", "Папка назначения:", labels, editable=False)
            if not ok: return
            destination = self.repository.move(path, folders[labels.index(label)])
            self._relocated(path, destination)
        except (OSError, ValueError) as error:
            self.error(error)

    def _relocated(self, old, new):
        def remap(path):
            if path == old: return new
            if path.startswith(old + "/"): return new + path[len(old):]
            return path
        self._path = remap(self._path)
        self._selected = remap(self._selected)
        self._folder = remap(self._folder)
        self._expanded = {remap(path) for path in self._expanded}
        self._expanded.add(Path(new).parent.as_posix() if Path(new).parent != Path(".") else "")
        if self._path == new:
            self._folder = Path(new).parent.as_posix() if Path(new).parent != Path(".") else ""
        self.refresh()

    @Slot(str)
    def delete(self, path):
        if not path: return
        if not self.save(): return
        if QMessageBox.question(self.window, "Удаление", f"Удалить «{Path(path).name}»?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        try:
            self.repository.delete(path)
            if self._path == path:
                self._path = ""; self._content = ""; self._editing = False
                self.documentChanged.emit()
            if self._folder == path:
                self._folder = Path(path).parent.as_posix() if Path(path).parent != Path(".") else ""
            self._selected = self._folder
            self._expanded.discard(path)
            self.refresh()
        except (OSError, ValueError) as error:
            self.error(error)

    @Slot(str)
    def search(self, query):
        self._query = query
        self.refresh()

    @Slot(str)
    def openLink(self, link):
        url = QUrl(link)
        if url.scheme() in ("https", "http", "mailto"):
            QDesktopServices.openUrl(url)


class NotesWindow(QMainWindow):
    def __init__(self, repository: NotesRepository):
        super().__init__()
        self.setWindowTitle("Заметки")
        self.resize(1180, 740)
        self.setMinimumSize(900, 540)
        self.bridge = NotesBridge(repository, self)
        self.view = QQuickWidget(self)
        # Keep the context object alive until the QML view has been destroyed.
        self.bridge.setParent(self.view)
        self.view.setResizeMode(QQuickWidget.ResizeMode.SizeRootObjectToView)
        self.view.rootContext().setContextProperty("notesBridge", self.bridge)
        self.view.setSource(QUrl.fromLocalFile(str(Path(__file__).with_name("qml") / "Notes.qml")))
        if self.view.status() == QQuickWidget.Status.Error:
            raise RuntimeError("\n".join(error.toString() for error in self.view.errors()))
        self.setCentralWidget(self.view)

    def closeEvent(self, event):
        if self.bridge.save(): super().closeEvent(event)
        else: event.ignore()
