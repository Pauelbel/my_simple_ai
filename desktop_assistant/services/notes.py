from pathlib import Path

from ..paths import app_data_dir


class NotesRepository:
    """Filesystem-backed Markdown repository with path traversal protection."""

    def __init__(self) -> None:
        self.root = app_data_dir() / "notes"
        self.root.mkdir(exist_ok=True)

    def resolve(self, relative: str) -> Path:
        candidate = (self.root / relative).resolve()
        if candidate != self.root.resolve() and self.root.resolve() not in candidate.parents:
            raise ValueError("Недопустимый путь")
        return candidate

    def tree(self) -> list[dict]:
        def entries(folder: Path) -> list[dict]:
            result = []
            for item in sorted(folder.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
                relative = item.relative_to(self.root).as_posix()
                if item.is_dir():
                    result.append({"name": item.name, "path": relative, "folder": True, "children": entries(item)})
                elif item.suffix.lower() == ".md":
                    result.append({"name": item.stem, "path": relative, "folder": False})
            return result
        return entries(self.root)

    def read(self, relative: str) -> str:
        return self.resolve(relative).read_text(encoding="utf-8")

    def save(self, relative: str, content: str) -> None:
        path = self.resolve(relative)
        if path.suffix.lower() != ".md":
            raise ValueError("Заметка должна иметь расширение .md")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def create_note(self, parent: str, title: str) -> str:
        clean = "".join(c for c in title.strip() if c not in '\\/:*?\"<>|').strip(".")
        if not clean:
            raise ValueError("Укажите название заметки")
        relative = (Path(parent) / f"{clean}.md").as_posix()
        path = self.resolve(relative)
        if path.exists():
            raise ValueError("Заметка уже существует")
        self.save(relative, f"# {clean}\n")
        return relative

    def create_folder(self, parent: str, title: str) -> str:
        clean = "".join(c for c in title.strip() if c not in '\\/:*?\"<>|').strip(".")
        if not clean:
            raise ValueError("Укажите название папки")
        path = self.resolve(str(Path(parent) / clean))
        path.mkdir()
        return path.relative_to(self.root).as_posix()

    def delete(self, relative: str) -> None:
        path = self.resolve(relative)
        if path == self.root.resolve():
            raise ValueError("Нельзя удалить корень библиотеки")
        if path.is_dir():
            if any(path.iterdir()):
                raise ValueError("Папка не пуста")
            path.rmdir()
        else:
            path.unlink()

    def rename(self, relative: str, title: str) -> str:
        source = self.resolve(relative)
        clean = "".join(c for c in title.strip() if c not in '\\/:*?"<>|').strip(". ")
        if not clean:
            raise ValueError("Укажите название")
        if source.is_file() and not clean.lower().endswith(".md"):
            clean += ".md"
        return self._relocate(source, source.with_name(clean))

    def move(self, relative: str, parent: str) -> str:
        source = self.resolve(relative)
        folder = self.resolve(parent)
        if not folder.is_dir():
            raise ValueError("Папка назначения не существует")
        return self._relocate(source, folder / source.name)

    def _relocate(self, source: Path, destination: Path) -> str:
        if source == self.root.resolve():
            raise ValueError("Нельзя переместить корень библиотеки")
        destination = self.resolve(destination.relative_to(self.root.resolve()).as_posix())
        if source == destination:
            return source.relative_to(self.root.resolve()).as_posix()
        if source.is_dir() and source in destination.parents:
            raise ValueError("Нельзя переместить папку внутрь самой себя")
        if destination.exists():
            raise ValueError("Элемент с таким названием уже существует")
        source.rename(destination)
        return destination.relative_to(self.root.resolve()).as_posix()

    def search(self, query: str) -> list[str]:
        needle = query.casefold().strip()
        if not needle:
            return []
        return [p.relative_to(self.root).as_posix() for p in self.root.rglob("*.md")
                if needle in p.stem.casefold() or needle in p.read_text(encoding="utf-8").casefold()]

    def note_summaries(self, folder: str = "", query: str = "") -> list[dict]:
        """Notes directly inside a folder, ordered by most recently modified."""
        directory = self.resolve(folder)
        needle = query.casefold().strip()
        notes = []
        paths = directory.rglob("*.md") if not folder else directory.glob("*.md")
        for path in paths:
            content = path.read_text(encoding="utf-8")
            if needle and needle not in path.stem.casefold() and needle not in content.casefold():
                continue
            lines = [line.strip().lstrip("#").strip() for line in content.splitlines() if line.strip()]
            title = lines[0] if lines else path.stem
            excerpt = next((line for line in lines[1:] if line), "Нет дополнительного текста")
            notes.append({"path": path.relative_to(self.root).as_posix(), "title": title, "excerpt": excerpt[:110], "modified": path.stat().st_mtime})
        return sorted(notes, key=lambda item: item["modified"], reverse=True)
