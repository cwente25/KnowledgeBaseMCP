"""Storage layer for managing markdown files in the knowledge base."""

import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

from .models import Note, NoteFrontmatter


class StorageError(Exception):
    """Base exception for storage operations."""
    pass


class NoteNotFoundError(StorageError):
    """Raised when a note cannot be found."""
    pass


class DuplicateNoteError(StorageError):
    """Raised when attempting to create a note that already exists."""
    pass


class KnowledgeBaseStorage:
    """Manages file operations for the knowledge base."""

    def __init__(self, base_path: str, categories: list[str]):
        """
        Initialize the storage layer.

        Args:
            base_path: Path to the knowledge base directory
            categories: List of valid category names
        """
        self.base_path = Path(base_path).expanduser()
        self.categories = categories
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Create base directory and category folders if they don't exist."""
        self.base_path.mkdir(parents=True, exist_ok=True)

        for category in self.categories:
            category_path = self.base_path / category
            category_path.mkdir(exist_ok=True)

    @staticmethod
    def sanitize_filename(title: str) -> str:
        """
        Convert a title to a valid filename.

        Args:
            title: The note title

        Returns:
            Sanitized filename (lowercase, hyphens, no special chars)
        """
        # Convert to lowercase
        filename = title.lower()

        # Replace spaces and underscores with hyphens
        filename = re.sub(r'[\s_]+', '-', filename)

        # Remove any characters that aren't alphanumeric or hyphens
        filename = re.sub(r'[^a-z0-9-]', '', filename)

        # Remove multiple consecutive hyphens
        filename = re.sub(r'-+', '-', filename)

        # Remove leading/trailing hyphens
        filename = filename.strip('-')

        return filename

    def _get_note_path(self, category: str, title: str) -> Path:
        """Get the file path for a note."""
        filename = self.sanitize_filename(title)
        return self.base_path / category / f"{filename}.md"

    def _parse_note_file(self, file_path: Path) -> Note:
        """
        Parse a markdown file into a Note object.

        Args:
            file_path: Path to the markdown file

        Returns:
            Note object

        Raises:
            StorageError: If file cannot be parsed
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Split frontmatter and content
            frontmatter_data = {}
            note_content = content

            if content.startswith('---\n'):
                parts = content.split('---\n', 2)
                if len(parts) >= 3:
                    try:
                        frontmatter_data = yaml.safe_load(parts[1]) or {}
                    except yaml.YAMLError as e:
                        # If frontmatter is malformed, log but continue
                        print(f"Warning: Malformed frontmatter in {file_path}: {e}")
                        frontmatter_data = {}

                    note_content = parts[2].strip()

            # Create frontmatter object
            frontmatter = NoteFrontmatter.from_dict(frontmatter_data)

            # Extract title from filename
            title = file_path.stem.replace('-', ' ').title()

            # Get category from parent directory
            category = file_path.parent.name

            return Note(
                title=title,
                category=category,
                frontmatter=frontmatter,
                content=note_content,
                file_path=str(file_path)
            )

        except Exception as e:
            raise StorageError(f"Failed to parse note {file_path}: {e}")

    def _write_note_file(self, note: Note, file_path: Path, backup: bool = True) -> None:
        """
        Write a Note object to a markdown file.

        Args:
            note: Note to write
            file_path: Destination file path
            backup: Whether to create a backup if file exists

        Raises:
            StorageError: If file cannot be written
        """
        try:
            # Create backup if requested and file exists
            if backup and file_path.exists():
                backup_path = file_path.with_suffix('.md.backup')
                shutil.copy2(file_path, backup_path)

            # Generate frontmatter YAML
            frontmatter_dict = note.frontmatter.to_dict()
            frontmatter_yaml = yaml.dump(frontmatter_dict, sort_keys=False, allow_unicode=True)

            # Combine frontmatter and content
            full_content = f"---\n{frontmatter_yaml}---\n\n{note.content}"

            # Write atomically (write to temp file, then rename)
            temp_path = file_path.with_suffix('.md.tmp')
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(full_content)

            # Atomic rename
            temp_path.rename(file_path)

        except Exception as e:
            raise StorageError(f"Failed to write note to {file_path}: {e}")

    def create_note(
        self,
        category: str,
        title: str,
        content: str,
        tags: list[str],
        metadata: Optional[dict] = None
    ) -> Note:
        """
        Create a new note.

        Args:
            category: Category folder name
            title: Note title
            content: Markdown content
            tags: List of tags
            metadata: Additional metadata fields

        Returns:
            Created Note object

        Raises:
            DuplicateNoteError: If note already exists
            StorageError: If category is invalid or write fails
        """
        if category not in self.categories:
            valid = ', '.join(self.categories)
            raise StorageError(
                f"❌ Error: Invalid category '{category}'\n"
                f"💡 Valid categories: {valid}"
            )

        file_path = self._get_note_path(category, title)

        if file_path.exists():
            raise DuplicateNoteError(
                f"❌ Error: Note '{title}' already exists in {category}/\n"
                f"💡 Tip: Use update_note to modify existing notes"
            )

        # Create frontmatter
        frontmatter = NoteFrontmatter(
            tags=tags,
            category=category,
            metadata=metadata or {}
        )

        # Create note object
        note = Note(
            title=title,
            category=category,
            frontmatter=frontmatter,
            content=content,
            file_path=str(file_path)
        )

        # Write to file
        self._write_note_file(note, file_path, backup=False)

        return note

    def get_note(self, category: str, title: str) -> Note:
        """
        Retrieve a note by category and title.

        Args:
            category: Category folder name
            title: Note title (can be friendly name or filename)

        Returns:
            Note object

        Raises:
            NoteNotFoundError: If note doesn't exist
        """
        file_path = self._get_note_path(category, title)

        if not file_path.exists():
            raise NoteNotFoundError(
                f"❌ Error: Note '{title}' not found in {category}/\n"
                f"💡 Tip: Use search_notes to find existing notes"
            )

        return self._parse_note_file(file_path)

    def update_note(
        self,
        category: str,
        title: str,
        content: Optional[str] = None,
        tags: Optional[list[str]] = None,
        append: bool = False,
        metadata: Optional[dict] = None
    ) -> Note:
        """
        Update an existing note.

        Args:
            category: Category folder name
            title: Note title
            content: New content (or content to append)
            tags: New tags (replaces existing)
            append: If True, append content instead of replacing
            metadata: Additional metadata to update

        Returns:
            Updated Note object

        Raises:
            NoteNotFoundError: If note doesn't exist
        """
        # Get existing note
        note = self.get_note(category, title)

        # Update content
        if content is not None:
            if append:
                note.content = note.content.strip() + "\n\n" + content
            else:
                note.content = content

        # Update tags
        if tags is not None:
            note.frontmatter.tags = tags

        # Update metadata
        if metadata is not None:
            note.frontmatter.metadata.update(metadata)

        # Update timestamp
        note.frontmatter.updated = datetime.now().strftime("%Y-%m-%d")

        # Write updated note
        file_path = Path(note.file_path)
        self._write_note_file(note, file_path, backup=True)

        return note

    def delete_note(self, category: str, title: str) -> str:
        """
        Delete a note.

        Args:
            category: Category folder name
            title: Note title

        Returns:
            Success message

        Raises:
            NoteNotFoundError: If note doesn't exist
        """
        file_path = self._get_note_path(category, title)

        if not file_path.exists():
            raise NoteNotFoundError(
                f"❌ Error: Note '{title}' not found in {category}/\n"
                f"💡 Tip: Use list_notes to see available notes"
            )

        # Create backup before deletion
        backup_path = file_path.with_suffix('.md.deleted')
        shutil.copy2(file_path, backup_path)

        # Delete the file
        file_path.unlink()

        return f"✓ Note '{title}' deleted from {category}/"

    def list_notes(
        self,
        category: Optional[str] = None,
        tag: Optional[str] = None
    ) -> list[Note]:
        """
        List all notes, optionally filtered by category or tag.

        Args:
            category: Optional category filter
            tag: Optional tag filter

        Returns:
            List of Note objects
        """
        notes = []

        # Determine which categories to search
        categories_to_search = [category] if category else self.categories

        for cat in categories_to_search:
            cat_path = self.base_path / cat
            if not cat_path.exists():
                continue

            # Find all markdown files
            for file_path in cat_path.glob("*.md"):
                try:
                    note = self._parse_note_file(file_path)

                    # Apply tag filter if specified
                    if tag and tag.lower() not in [t.lower() for t in note.frontmatter.tags]:
                        continue

                    notes.append(note)

                except StorageError:
                    # Skip files that can't be parsed
                    continue

        return notes

    def get_category_stats(self) -> dict[str, int]:
        """
        Get statistics about each category.

        Returns:
            Dictionary mapping category names to note counts
        """
        stats = {}

        for category in self.categories:
            cat_path = self.base_path / category
            if cat_path.exists():
                count = len(list(cat_path.glob("*.md")))
                stats[category] = count
            else:
                stats[category] = 0

        return stats
