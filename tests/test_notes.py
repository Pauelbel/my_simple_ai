from pathlib import Path

from desktop_assistant.services.notes import NotesRepository


def test_notes_repository_blocks_parent_escape(tmp_path: Path) -> None:
    repository = NotesRepository()
    repository.root = tmp_path / "notes"
    repository.root.mkdir()
    repository.save("work/idea.md", "hello")
    assert repository.read("work/idea.md") == "hello"
    assert repository.search("hello") == ["work/idea.md"]
    try:
        repository.resolve("../secret.md")
    except ValueError:
        pass
    else:
        raise AssertionError("Path traversal must be rejected")
