"""QML notes workspace and its filesystem-backed presentation model."""
from datetime import datetime
import hashlib
import json
import re
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, Property, QSettings, Qt, QUrl, Signal, Slot
from PySide6.QtGui import QColor, QDesktopServices, QFont, QImageReader, QPalette, QTextBlockFormat, QTextCursor, QTextDocument
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtWidgets import QFileDialog, QInputDialog, QMainWindow, QMessageBox

from .repository import NotesRepository


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
        settings_suffix = hashlib.sha256(str(repository.root).encode()).hexdigest()[:16]
        self._layout_key = f"notes/layout/{settings_suffix}"
        try:
            self._folder_order = json.loads(self.preferences.value(self._layout_key + "/folderOrder", "[]"))
        except (TypeError, json.JSONDecodeError):
            self._folder_order = []
        self._library_visible = self.preferences.value("notes/libraryVisible", True, type=bool)
        self._list_visible = self.preferences.value("notes/listVisible", True, type=bool)
        self._preview_style = ("Sans Serif", 16, "#96b6f1")
        self._preview_zoom = max(60, min(200, self.preferences.value("notes/previewZoom", 100, type=int)))
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
    def title(self):
        return (self.repository.presentation(self._content, Path(self._path).stem)[0]
                if self._path else "Выберите заметку")

    @Property(str, notify=changed)
    def breadcrumbs(self):
        if not self._path:
            return ""
        parts = list(Path(self._path).parts[:-1]) + [self.title]
        return "  ›  ".join(parts)

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

    @Property(bool, notify=changed)
    def libraryVisible(self): return self._library_visible

    @Property(bool, notify=changed)
    def listVisible(self): return self._list_visible

    @Property(int, notify=changed)
    def previewZoom(self): return self._preview_zoom

    @Property(str, notify=changed)
    def previewHtml(self):
        if self._editing:
            return self._preview_cache[1]
        key = (self._content, self._preview_style, self._preview_zoom, self._path)
        if self._preview_cache[0] == key:
            return self._preview_cache[1]
        doc = QTextDocument()
        family, size, accent = self._preview_style
        font = QFont(family)
        font.setPixelSize(max(8, round(size * self._preview_zoom / 100)))
        doc.setDefaultFont(font)
        doc.setDefaultStyleSheet(
            f"a {{ color: {accent}; text-decoration: underline; }} "
            f"table {{ border-collapse: collapse; margin: 8px 0; }} "
            f"th, td {{ border: 1px solid {accent}; padding: 6px 10px; }} "
            f"th {{ font-weight: 600; }}"
        )
        # QTextDocument created by QML does not inherit our base URL. Absolute
        # file URLs keep library-local Markdown images visible in the preview.
        _, markdown = self.repository.split_front_matter(self._content)
        if self._path:
            note_dir = self.repository.resolve(self._path).parent
            def absolute_image(match):
                target = match.group(2).strip()
                if target.startswith("<") and target.endswith(">"):
                    target = target[1:-1].strip()
                url = QUrl(target)
                if url.scheme() in ("http", "https", "data"):
                    return match.group(0)
                if url.scheme() == "file":
                    image = Path(url.toLocalFile())
                else:
                    image = Path(target)
                    if not image.is_absolute():
                        image = note_dir / image
                encoded = bytes(QUrl.fromLocalFile(str(image.resolve())).toEncoded()).decode()
                return f"![{match.group(1)}]({encoded})"
            markdown = re.sub(r"!\[([^\]]*)\]\(([^\n]+?)\)", absolute_image, markdown)
        # Qt's Markdown parser requires explicit link syntax. Make pasted bare
        # web addresses clickable without touching existing Markdown links.
        markdown = re.sub(
            r"(?<![<(])(https?://[^\s<>]+?)(?=[.,;:!?)]?(?:\s|$))",
            lambda match: f"<{match.group(1)}>", markdown
        )
        doc.setMarkdown(markdown)
        block = doc.begin()
        while block.isValid():
            cursor = QTextCursor(block)
            fmt = block.blockFormat()
            fmt.setLineHeight(145, QTextBlockFormat.LineHeightTypes.ProportionalHeight.value)
            fmt.setTopMargin(12 if fmt.headingLevel() else 4)
            fmt.setBottomMargin(10)
            cursor.setBlockFormat(fmt)
            block = block.next()
        html = doc.toHtml()
        def constrain_image(match):
            source = match.group(1)
            local = QUrl(source).toLocalFile()
            size = QImageReader(local).size() if local else None
            if size and size.isValid() and size.width() > 860:
                return match.group(0).replace("<img ", f'<img width="860" ')
            return match.group(0)
        html = re.sub(r'<img[^>]*src="([^"]+)"[^>]*>', constrain_image, html)
        self._preview_cache = (key, html)
        return self._preview_cache[1]

    @Slot(str, int, QColor)
    def setPreviewStyle(self, family, size, accent):
        self._preview_style = (family, size, accent.name())
        self.changed.emit()

    @Slot(int)
    def zoomPreview(self, steps):
        zoom = 100 if steps == 0 else max(60, min(200, self._preview_zoom + (10 if steps > 0 else -10)))
        if zoom == self._preview_zoom:
            return
        self._preview_zoom = zoom
        self.preferences.setValue("notes/previewZoom", zoom)
        self._preview_cache = (None, "")
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

            def ordered(nodes):
                rank = {path: index for index, path in enumerate(self._folder_order)}
                folders = [node for node in nodes if node["folder"]]
                files = [node for node in nodes if not node["folder"]]
                folders.sort(key=lambda node: (rank.get(node["path"], len(rank)), node["name"].casefold()))
                for node in folders:
                    node["children"] = ordered(node["children"])
                return folders + files

            if "" in self._expanded:
                append(ordered(self.repository.tree()), 1, [])
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

    @Slot()
    def toggleLibrary(self):
        self._library_visible = not self._library_visible
        self.preferences.setValue("notes/libraryVisible", self._library_visible)
        self.changed.emit()

    @Slot()
    def toggleNoteList(self):
        self._list_visible = not self._list_visible
        self.preferences.setValue("notes/listVisible", self._list_visible)
        self.changed.emit()

    @Slot(str, str)
    def reorderFolder(self, source, target):
        """Place a folder before another folder, reparenting across tree levels."""
        if not source or not target or source == target:
            return
        source_path, target_path = Path(source), Path(target)
        if source_path in target_path.parents:
            self.error("Нельзя переместить папку внутрь самой себя")
            return
        try:
            destination = source
            target_parent = target_path.parent.as_posix() if target_path.parent != Path(".") else ""
            source_parent = source_path.parent.as_posix() if source_path.parent != Path(".") else ""
            if source_parent != target_parent:
                if not self.save():
                    return
                destination = self.repository.move(source, target_parent)

            def remap(path):
                if path == source: return destination
                if path.startswith(source + "/"): return destination + path[len(source):]
                return path

            order = [remap(path) for path in self._folder_order
                     if path != source and not path.startswith(source + "/")]
            # Include folders not ordered before so every drag has a stable result.
            all_folders = []
            def collect(nodes):
                for node in nodes:
                    if node["folder"]:
                        all_folders.append(node["path"])
                        collect(node["children"])
            collect(self.repository.tree())
            for path in all_folders:
                if path != destination and path not in order:
                    order.append(path)
            insert_at = order.index(target) if target in order else len(order)
            order.insert(insert_at, destination)
            self._folder_order = order
            self.preferences.setValue(self._layout_key + "/folderOrder", json.dumps(order, ensure_ascii=False))
            if destination != source:
                self._relocated(source, destination)
            else:
                self.refresh()
        except (OSError, ValueError) as error:
            self.error(error)

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

    @Slot(result=str)
    def importImage(self):
        if not self._path:
            return ""
        source, _ = QFileDialog.getOpenFileName(
            self.window, "Вставить изображение", "",
            "Изображения (*.png *.jpg *.jpeg *.gif *.webp *.bmp *.svg)"
        )
        if not source:
            return ""
        try:
            relative = self.repository.import_image(self._path, source)
            alt = Path(source).stem.replace("[", "").replace("]", "") or "Изображение"
            return f"![{alt}]({relative})"
        except (OSError, ValueError) as error:
            self.error(error)
            return ""

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
        # QQuick ScrollView consumes wheel input before nested QML handlers on
        # some Qt/platform combinations. Catch Ctrl+wheel at widget level.
        self.view.installEventFilter(self)

    def eventFilter(self, watched, event):
        if (watched is self.view and event.type() == QEvent.Type.Wheel
                and event.modifiers() & Qt.KeyboardModifier.ControlModifier
                and self.bridge.currentPath and not self.bridge.editing):
            delta = event.angleDelta().y() or event.pixelDelta().y()
            if delta:
                self.bridge.zoomPreview(1 if delta > 0 else -1)
                event.accept()
                return True
        return super().eventFilter(watched, event)

    def closeEvent(self, event):
        if self.bridge.save(): super().closeEvent(event)
        else: event.ignore()
