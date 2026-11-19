from pathlib import Path

from desktop_assistant.notes.repository import NotesRepository


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


def test_import_image_copies_next_to_note_and_avoids_collisions(tmp_path: Path) -> None:
    repository = NotesRepository(tmp_path / "notes")
    repository.save("work/idea.md", "# Idea")
    first = tmp_path / "diagram.png"
    second_dir = tmp_path / "other"
    second_dir.mkdir()
    second = second_dir / "diagram.png"
    first.write_bytes(b"first")
    second.write_bytes(b"second")

    assert repository.import_image("work/idea.md", first) == ".assets/idea/diagram.png"
    assert repository.import_image("work/idea.md", first) == ".assets/idea/diagram.png"
    assert repository.import_image("work/idea.md", second) == ".assets/idea/diagram-2.png"
    assert repository.resolve("work/.assets/idea/diagram-2.png").read_bytes() == b"second"
