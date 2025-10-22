"""Tests for the storage layer."""

import tempfile
from pathlib import Path

import pytest

from knowledge_base_mcp.models import Note, NoteFrontmatter
from knowledge_base_mcp.storage import (
    KnowledgeBaseStorage,
    DuplicateNoteError,
    NoteNotFoundError,
    StorageError,
)


@pytest.fixture
def temp_kb():
    """Create a temporary knowledge base for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        categories = ["people", "recipes", "meetings", "procedures", "tasks"]
        storage = KnowledgeBaseStorage(tmpdir, categories)
        yield storage


def test_init_creates_directories(temp_kb):
    """Test that initialization creates all category directories."""
    for category in temp_kb.categories:
        category_path = temp_kb.base_path / category
        assert category_path.exists()
        assert category_path.is_dir()


def test_sanitize_filename():
    """Test filename sanitization."""
    assert KnowledgeBaseStorage.sanitize_filename("Sarah Chen") == "sarah-chen"
    assert KnowledgeBaseStorage.sanitize_filename("John O'Brien") == "john-obrien"
    assert KnowledgeBaseStorage.sanitize_filename("Test  Multiple   Spaces") == "test-multiple-spaces"
    assert KnowledgeBaseStorage.sanitize_filename("CamelCase Title") == "camelcase-title"
    assert KnowledgeBaseStorage.sanitize_filename("title_with_underscores") == "title-with-underscores"
    assert KnowledgeBaseStorage.sanitize_filename("---leading-trailing---") == "leading-trailing"


def test_create_note(temp_kb):
    """Test creating a new note."""
    note = temp_kb.create_note(
        category="people",
        title="Sarah Chen",
        content="Battery engineer at Tesla",
        tags=["conference", "tesla", "important"]
    )

    assert note.title == "Sarah Chen"
    assert note.category == "people"
    assert note.content == "Battery engineer at Tesla"
    assert note.frontmatter.tags == ["conference", "tesla", "important"]

    # Check file was created
    file_path = temp_kb.base_path / "people" / "sarah-chen.md"
    assert file_path.exists()


def test_create_note_invalid_category(temp_kb):
    """Test creating a note with invalid category."""
    with pytest.raises(StorageError, match="Invalid category"):
        temp_kb.create_note(
            category="invalid",
            title="Test",
            content="Test content",
            tags=[]
        )


def test_create_duplicate_note(temp_kb):
    """Test that creating duplicate note raises error."""
    temp_kb.create_note(
        category="people",
        title="Sarah Chen",
        content="First note",
        tags=[]
    )

    with pytest.raises(DuplicateNoteError, match="already exists"):
        temp_kb.create_note(
            category="people",
            title="Sarah Chen",
            content="Duplicate note",
            tags=[]
        )


def test_get_note(temp_kb):
    """Test retrieving a note."""
    temp_kb.create_note(
        category="recipes",
        title="Brussels Sprouts",
        content="Cook at 400F for 15 minutes",
        tags=["quick", "vegetables"]
    )

    note = temp_kb.get_note("recipes", "Brussels Sprouts")

    assert note.title == "Brussels Sprouts"
    assert note.category == "recipes"
    assert "400F" in note.content
    assert "quick" in note.frontmatter.tags


def test_get_note_not_found(temp_kb):
    """Test getting non-existent note."""
    with pytest.raises(NoteNotFoundError, match="not found"):
        temp_kb.get_note("people", "Non Existent")


def test_update_note_content(temp_kb):
    """Test updating note content."""
    temp_kb.create_note(
        category="people",
        title="John Doe",
        content="Original content",
        tags=["test"]
    )

    updated_note = temp_kb.update_note(
        category="people",
        title="John Doe",
        content="Updated content"
    )

    assert updated_note.content == "Updated content"
    assert updated_note.frontmatter.updated is not None


def test_update_note_append(temp_kb):
    """Test appending content to a note."""
    temp_kb.create_note(
        category="people",
        title="John Doe",
        content="Original content",
        tags=[]
    )

    updated_note = temp_kb.update_note(
        category="people",
        title="John Doe",
        content="Additional content",
        append=True
    )

    assert "Original content" in updated_note.content
    assert "Additional content" in updated_note.content


def test_update_note_tags(temp_kb):
    """Test updating note tags."""
    temp_kb.create_note(
        category="people",
        title="Jane Smith",
        content="Content",
        tags=["old"]
    )

    updated_note = temp_kb.update_note(
        category="people",
        title="Jane Smith",
        tags=["new", "updated"]
    )

    assert updated_note.frontmatter.tags == ["new", "updated"]


def test_delete_note(temp_kb):
    """Test deleting a note."""
    temp_kb.create_note(
        category="tasks",
        title="Todo Item",
        content="Something to do",
        tags=[]
    )

    result = temp_kb.delete_note("tasks", "Todo Item")

    assert "deleted" in result.lower()

    # Verify file is gone
    file_path = temp_kb.base_path / "tasks" / "todo-item.md"
    assert not file_path.exists()

    # Backup should exist
    backup_path = temp_kb.base_path / "tasks" / "todo-item.md.deleted"
    assert backup_path.exists()


def test_delete_note_not_found(temp_kb):
    """Test deleting non-existent note."""
    with pytest.raises(NoteNotFoundError, match="not found"):
        temp_kb.delete_note("people", "Non Existent")


def test_list_notes_all(temp_kb):
    """Test listing all notes."""
    temp_kb.create_note("people", "Person 1", "Content 1", ["tag1"])
    temp_kb.create_note("people", "Person 2", "Content 2", ["tag2"])
    temp_kb.create_note("recipes", "Recipe 1", "Content 3", ["tag3"])

    notes = temp_kb.list_notes()

    assert len(notes) == 3


def test_list_notes_by_category(temp_kb):
    """Test listing notes filtered by category."""
    temp_kb.create_note("people", "Person 1", "Content", [])
    temp_kb.create_note("recipes", "Recipe 1", "Content", [])
    temp_kb.create_note("recipes", "Recipe 2", "Content", [])

    notes = temp_kb.list_notes(category="recipes")

    assert len(notes) == 2
    assert all(note.category == "recipes" for note in notes)


def test_list_notes_by_tag(temp_kb):
    """Test listing notes filtered by tag."""
    temp_kb.create_note("people", "Person 1", "Content", ["important"])
    temp_kb.create_note("people", "Person 2", "Content", ["important", "work"])
    temp_kb.create_note("people", "Person 3", "Content", ["personal"])

    notes = temp_kb.list_notes(tag="important")

    assert len(notes) == 2


def test_get_category_stats(temp_kb):
    """Test getting category statistics."""
    temp_kb.create_note("people", "Person 1", "Content", [])
    temp_kb.create_note("people", "Person 2", "Content", [])
    temp_kb.create_note("recipes", "Recipe 1", "Content", [])

    stats = temp_kb.get_category_stats()

    assert stats["people"] == 2
    assert stats["recipes"] == 1
    assert stats["meetings"] == 0


def test_create_note_with_metadata(temp_kb):
    """Test creating a note with additional metadata."""
    metadata = {
        "company": "Tesla",
        "role": "Engineer",
        "email": "sarah@tesla.com"
    }

    note = temp_kb.create_note(
        category="people",
        title="Sarah Chen",
        content="Battery engineer",
        tags=["tesla"],
        metadata=metadata
    )

    assert note.frontmatter.metadata["company"] == "Tesla"
    assert note.frontmatter.metadata["role"] == "Engineer"

    # Verify it persists
    retrieved_note = temp_kb.get_note("people", "Sarah Chen")
    assert retrieved_note.frontmatter.metadata["company"] == "Tesla"


def test_note_preview(temp_kb):
    """Test note preview generation."""
    note = temp_kb.create_note(
        category="people",
        title="Test Person",
        content="This is a long piece of content that should be truncated when displayed as a preview. " * 10,
        tags=[]
    )

    preview = note.get_preview(50)
    assert len(preview) <= 53  # 50 + "..."
    assert preview.endswith("...")


def test_backup_on_update(temp_kb):
    """Test that backup is created when updating a note."""
    temp_kb.create_note(
        category="people",
        title="Test Person",
        content="Original content",
        tags=[]
    )

    temp_kb.update_note(
        category="people",
        title="Test Person",
        content="Updated content"
    )

    backup_path = temp_kb.base_path / "people" / "test-person.md.backup"
    assert backup_path.exists()

    # Read backup and verify it has original content
    backup_content = backup_path.read_text()
    assert "Original content" in backup_content
