"""Storage layer for managing markdown files in the knowledge base."""

import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict

import yaml

from .models import Note, NoteFrontmatter, CategoryInfo, CategoryMetadata
from .path_utils import (
    normalize_path,
    validate_path,
    split_path,
    join_path,
    get_parent_path,
    get_category_name,
    get_depth,
    is_subpath_of,
    would_create_cycle,
    InvalidPathError
)


class StorageError(Exception):
    """Base exception for storage operations."""
    pass


class NoteNotFoundError(StorageError):
    """Raised when a note cannot be found."""
    pass


class DuplicateNoteError(StorageError):
    """Raised when attempting to create a note that already exists."""
    pass


class CategoryNotFoundError(StorageError):
    """Raised when a category cannot be found."""
    pass


class CategoryExistsError(StorageError):
    """Raised when attempting to create a category that already exists."""
    pass


class KnowledgeBaseStorage:
    """Manages file operations for the knowledge base."""

    def __init__(self, base_path: str, legacy_categories: Optional[List[str]] = None):
        """
        Initialize the storage layer.

        Args:
            base_path: Path to the knowledge base directory
            legacy_categories: Optional list of legacy category names to ensure exist
                             (for backwards compatibility)
        """
        self.base_path = Path(base_path).expanduser()
        self.base_path.mkdir(parents=True, exist_ok=True)

        # Create legacy categories if specified (backwards compatibility)
        if legacy_categories:
            for category in legacy_categories:
                cat_path = self.base_path / category
                cat_path.mkdir(exist_ok=True)

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

    def _get_note_path(self, category_path: str, title: str) -> Path:
        """
        Get the file path for a note.

        Args:
            category_path: Category path (e.g., "work/clients/acme")
            title: Note title

        Returns:
            Full path to the note file
        """
        normalized = normalize_path(category_path)
        filename = self.sanitize_filename(title)
        cat_path = self._get_category_path(normalized)
        return cat_path / f"{filename}.md"

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

            # Get category path relative to base_path
            try:
                rel_path = file_path.parent.relative_to(self.base_path)
                category = str(rel_path) if str(rel_path) != '.' else ''
            except ValueError:
                # If not relative to base_path, use parent name
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

    # Category management helper methods

    def _get_category_path(self, category_path: str) -> Path:
        """
        Get the filesystem path for a category.

        Args:
            category_path: Category path (e.g., "work/clients/acme")

        Returns:
            Full filesystem Path object
        """
        normalized = normalize_path(category_path)
        if not normalized:
            return self.base_path
        return self.base_path / normalized

    def _category_exists(self, category_path: str) -> bool:
        """Check if a category exists."""
        cat_path = self._get_category_path(category_path)
        return cat_path.exists() and cat_path.is_dir()

    def _get_category_metadata_path(self, category_path: str) -> Path:
        """Get the path to the category metadata file."""
        cat_path = self._get_category_path(category_path)
        return cat_path / ".meta.json"

    def _load_category_metadata(self, category_path: str) -> Optional[CategoryMetadata]:
        """Load category metadata from .meta.json file."""
        meta_path = self._get_category_metadata_path(category_path)
        if not meta_path.exists():
            return None

        try:
            with open(meta_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return CategoryMetadata.from_dict(data)
        except Exception as e:
            print(f"Warning: Failed to load metadata for {category_path}: {e}")
            return None

    def _save_category_metadata(
        self,
        category_path: str,
        metadata: CategoryMetadata
    ) -> None:
        """Save category metadata to .meta.json file."""
        meta_path = self._get_category_metadata_path(category_path)

        try:
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(metadata.to_dict(), f, indent=2)
        except Exception as e:
            raise StorageError(f"Failed to save metadata for {category_path}: {e}")

    def _count_notes_in_category(self, category_path: str, recursive: bool = False) -> int:
        """
        Count notes in a category.

        Args:
            category_path: Category path
            recursive: If True, count notes in subcategories too

        Returns:
            Number of notes
        """
        cat_path = self._get_category_path(category_path)
        if not cat_path.exists():
            return 0

        if recursive:
            return len(list(cat_path.rglob("*.md")))
        else:
            return len(list(cat_path.glob("*.md")))

    # Public category management methods

    def create_category(
        self,
        category_path: str,
        description: Optional[str] = None,
        create_parents: bool = True
    ) -> str:
        """
        Create a new category.

        Args:
            category_path: Category path (e.g., "work/clients/acme")
            description: Optional description for the category
            create_parents: If True, create parent directories as needed

        Returns:
            Success message

        Raises:
            CategoryExistsError: If category already exists
            InvalidPathError: If path is invalid
            StorageError: If creation fails
        """
        # Normalize and validate path
        normalized = normalize_path(category_path)
        if not normalized:
            raise InvalidPathError("Category path cannot be empty")

        is_valid, error_msg = validate_path(normalized)
        if not is_valid:
            raise InvalidPathError(error_msg)

        # Check if already exists
        if self._category_exists(normalized):
            raise CategoryExistsError(
                f"❌ Error: Category '{normalized}' already exists\n"
                f"💡 Tip: Use rename_category to rename it"
            )

        # Create the directory
        cat_path = self._get_category_path(normalized)
        try:
            cat_path.mkdir(parents=create_parents, exist_ok=False)
        except FileExistsError:
            raise CategoryExistsError(f"Category '{normalized}' already exists")
        except FileNotFoundError:
            parent = get_parent_path(normalized)
            raise StorageError(
                f"❌ Error: Parent category '{parent}' does not exist\n"
                f"💡 Tip: Create parent first or use create_parents=True"
            )
        except Exception as e:
            raise StorageError(f"Failed to create category '{normalized}': {e}")

        # Save metadata if description provided
        if description:
            metadata = CategoryMetadata(description=description)
            self._save_category_metadata(normalized, metadata)

        return f"✓ Category '{normalized}' created successfully"

    def delete_category(
        self,
        category_path: str,
        recursive: bool = True,
        confirm: bool = False
    ) -> Dict[str, int]:
        """
        Delete a category.

        Args:
            category_path: Category path to delete
            recursive: If True, delete subcategories and notes
            confirm: Must be True to delete non-empty category

        Returns:
            Dictionary with counts of deleted items

        Raises:
            CategoryNotFoundError: If category doesn't exist
            StorageError: If deletion fails or confirmation not provided
        """
        normalized = normalize_path(category_path)
        if not normalized:
            raise InvalidPathError("Category path cannot be empty")

        if not self._category_exists(normalized):
            raise CategoryNotFoundError(
                f"❌ Error: Category '{normalized}' not found\n"
                f"💡 Tip: Use list_categories to see available categories"
            )

        cat_path = self._get_category_path(normalized)

        # Count what will be deleted
        notes_count = self._count_notes_in_category(normalized, recursive=True)
        subcats = [d for d in cat_path.rglob("*") if d.is_dir()] if recursive else []
        subcats_count = len(subcats)

        # Check if confirmation needed
        if (notes_count > 0 or subcats_count > 0) and not confirm:
            raise StorageError(
                f"❌ Error: Category '{normalized}' is not empty "
                f"({notes_count} notes, {subcats_count} subcategories)\n"
                f"💡 Tip: Set confirm=True to delete non-empty category"
            )

        # Perform deletion
        try:
            if recursive:
                shutil.rmtree(cat_path)
            else:
                # Only delete if empty
                cat_path.rmdir()
        except OSError as e:
            raise StorageError(f"Failed to delete category '{normalized}': {e}")

        return {
            "notes_deleted": notes_count,
            "subcategories_deleted": subcats_count
        }

    def rename_category(
        self,
        old_path: str,
        new_name: str
    ) -> str:
        """
        Rename a category (keeps it in same parent location).

        Args:
            old_path: Current category path (e.g., "work/clients")
            new_name: New name for the category (just the name, not full path)

        Returns:
            Success message with new path

        Raises:
            CategoryNotFoundError: If category doesn't exist
            CategoryExistsError: If new name conflicts
            InvalidPathError: If new name is invalid
        """
        old_normalized = normalize_path(old_path)
        if not old_normalized:
            raise InvalidPathError("Category path cannot be empty")

        if not self._category_exists(old_normalized):
            raise CategoryNotFoundError(
                f"❌ Error: Category '{old_normalized}' not found"
            )

        # Validate new name
        is_valid, error_msg = validate_path(new_name)
        if not is_valid:
            raise InvalidPathError(f"Invalid new name: {error_msg}")

        if "/" in new_name:
            raise InvalidPathError(
                "New name should be just the category name, not a full path"
            )

        # Determine new path
        parent = get_parent_path(old_normalized)
        new_path = join_path(parent, new_name) if parent else new_name

        # Check if new path already exists
        if self._category_exists(new_path):
            raise CategoryExistsError(
                f"❌ Error: Category '{new_path}' already exists"
            )

        # Perform rename
        old_cat_path = self._get_category_path(old_normalized)
        new_cat_path = self._get_category_path(new_path)

        try:
            old_cat_path.rename(new_cat_path)
        except Exception as e:
            raise StorageError(f"Failed to rename category: {e}")

        return f"✓ Category renamed: '{old_normalized}' → '{new_path}'"

    def move_category(
        self,
        source_path: str,
        destination_path: str,
        create_destination: bool = True
    ) -> str:
        """
        Move a category to a new location.

        Args:
            source_path: Current category path
            destination_path: New parent path (or full new path)
            create_destination: If True, create destination if it doesn't exist

        Returns:
            Success message with new path

        Raises:
            CategoryNotFoundError: If source doesn't exist
            StorageError: If move would create circular reference or fails
        """
        source_normalized = normalize_path(source_path)
        dest_normalized = normalize_path(destination_path)

        if not source_normalized:
            raise InvalidPathError("Source path cannot be empty")

        if not self._category_exists(source_normalized):
            raise CategoryNotFoundError(
                f"❌ Error: Category '{source_normalized}' not found"
            )

        # Check for circular reference
        if would_create_cycle(source_normalized, dest_normalized):
            raise StorageError(
                f"❌ Error: Cannot move '{source_normalized}' to '{dest_normalized}' "
                "(would create circular reference)"
            )

        # Determine final destination
        source_name = get_category_name(source_normalized)
        final_dest = join_path(dest_normalized, source_name)

        # Check if destination parent exists
        if dest_normalized and not self._category_exists(dest_normalized):
            if create_destination:
                self.create_category(dest_normalized, create_parents=True)
            else:
                raise CategoryNotFoundError(
                    f"❌ Error: Destination '{dest_normalized}' does not exist\n"
                    f"💡 Tip: Use create_destination=True to create it"
                )

        # Check if final destination already exists
        if self._category_exists(final_dest):
            raise CategoryExistsError(
                f"❌ Error: Category '{final_dest}' already exists"
            )

        # Perform move
        source_cat_path = self._get_category_path(source_normalized)
        final_dest_path = self._get_category_path(final_dest)

        try:
            shutil.move(str(source_cat_path), str(final_dest_path))
        except Exception as e:
            raise StorageError(f"Failed to move category: {e}")

        return f"✓ Category moved: '{source_normalized}' → '{final_dest}'"

    def create_note(
        self,
        category_path: str,
        title: str,
        content: str,
        tags: list[str],
        metadata: Optional[dict] = None,
        create_category: bool = True
    ) -> Note:
        """
        Create a new note.

        Args:
            category_path: Category path (e.g., "work/clients/acme")
            title: Note title
            content: Markdown content
            tags: List of tags
            metadata: Additional metadata fields
            create_category: If True, create category if it doesn't exist

        Returns:
            Created Note object

        Raises:
            DuplicateNoteError: If note already exists
            InvalidPathError: If category path is invalid
            StorageError: If write fails
        """
        # Normalize and validate path
        normalized = normalize_path(category_path)
        is_valid, error_msg = validate_path(normalized) if normalized else (True, None)
        if not is_valid:
            raise InvalidPathError(error_msg)

        # Create category if needed
        if normalized and not self._category_exists(normalized):
            if create_category:
                self.create_category(normalized, create_parents=True)
            else:
                raise CategoryNotFoundError(
                    f"❌ Error: Category '{normalized}' does not exist\n"
                    f"💡 Tip: Use create_category first or set create_category=True"
                )

        file_path = self._get_note_path(normalized, title)

        if file_path.exists():
            raise DuplicateNoteError(
                f"❌ Error: Note '{title}' already exists in {normalized or 'root'}/\n"
                f"💡 Tip: Use update_note to modify existing notes"
            )

        # Create frontmatter
        frontmatter = NoteFrontmatter(
            tags=tags,
            category=normalized,
            metadata=metadata or {}
        )

        # Create note object
        note = Note(
            title=title,
            category=normalized,
            frontmatter=frontmatter,
            content=content,
            file_path=str(file_path)
        )

        # Write to file
        self._write_note_file(note, file_path, backup=False)

        return note

    def get_note(self, category_path: str, title: str) -> Note:
        """
        Retrieve a note by category path and title.

        Args:
            category_path: Category path (e.g., "work/clients/acme")
            title: Note title (can be friendly name or filename)

        Returns:
            Note object

        Raises:
            NoteNotFoundError: If note doesn't exist
        """
        normalized = normalize_path(category_path)
        file_path = self._get_note_path(normalized, title)

        if not file_path.exists():
            raise NoteNotFoundError(
                f"❌ Error: Note '{title}' not found in {normalized or 'root'}/\n"
                f"💡 Tip: Use search_notes to find existing notes"
            )

        return self._parse_note_file(file_path)

    def update_note(
        self,
        category_path: str,
        title: str,
        content: Optional[str] = None,
        tags: Optional[list[str]] = None,
        append: bool = False,
        metadata: Optional[dict] = None
    ) -> Note:
        """
        Update an existing note.

        Args:
            category_path: Category path (e.g., "work/clients/acme")
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
        normalized = normalize_path(category_path)
        note = self.get_note(normalized, title)

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

    def delete_note(self, category_path: str, title: str) -> str:
        """
        Delete a note.

        Args:
            category_path: Category path (e.g., "work/clients/acme")
            title: Note title

        Returns:
            Success message

        Raises:
            NoteNotFoundError: If note doesn't exist
        """
        normalized = normalize_path(category_path)
        file_path = self._get_note_path(normalized, title)

        if not file_path.exists():
            raise NoteNotFoundError(
                f"❌ Error: Note '{title}' not found in {normalized or 'root'}/\n"
                f"💡 Tip: Use list_notes to see available notes"
            )

        # Create backup before deletion
        backup_path = file_path.with_suffix('.md.deleted')
        shutil.copy2(file_path, backup_path)

        # Delete the file
        file_path.unlink()

        return f"✓ Note '{title}' deleted from {normalized or 'root'}/"

    def list_notes(
        self,
        category_path: Optional[str] = None,
        tag: Optional[str] = None,
        recursive: bool = True
    ) -> list[Note]:
        """
        List all notes, optionally filtered by category path or tag.

        Args:
            category_path: Optional category path filter (e.g., "work/clients")
            tag: Optional tag filter
            recursive: If True, include notes from subcategories (default: True)

        Returns:
            List of Note objects
        """
        notes = []

        # Determine which path to search
        if category_path:
            normalized = normalize_path(category_path)
            search_path = self._get_category_path(normalized)
            if not search_path.exists():
                return []
        else:
            search_path = self.base_path

        # Find all markdown files
        if recursive:
            pattern = "**/*.md"
        else:
            pattern = "*.md"

        for file_path in search_path.glob(pattern):
            # Skip backup and temp files
            if file_path.suffix in ('.backup', '.tmp', '.deleted'):
                continue

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

    def get_category_hierarchy(
        self,
        parent_path: Optional[str] = None
    ) -> List[CategoryInfo]:
        """
        Get hierarchical category structure.

        Args:
            parent_path: Optional parent path to list subcategories of

        Returns:
            List of CategoryInfo objects representing the category tree
        """
        if parent_path:
            normalized = normalize_path(parent_path)
            search_path = self._get_category_path(normalized)
        else:
            search_path = self.base_path
            normalized = ""

        if not search_path.exists():
            return []

        categories = []

        # Find all direct subdirectories
        for item in search_path.iterdir():
            if not item.is_dir():
                continue

            # Get relative path from base
            try:
                rel_path = item.relative_to(self.base_path)
                cat_path = str(rel_path)
            except ValueError:
                continue

            # Count notes in this category (non-recursive)
            note_count = self._count_notes_in_category(cat_path, recursive=False)

            # Load metadata
            metadata = self._load_category_metadata(cat_path)

            # Get depth
            depth = get_depth(cat_path)

            # Create CategoryInfo
            cat_info = CategoryInfo(
                name=item.name,
                path=cat_path,
                note_count=note_count,
                depth=depth,
                metadata=metadata
            )

            # Recursively get children
            cat_info.children = self.get_category_hierarchy(cat_path)

            categories.append(cat_info)

        return sorted(categories, key=lambda c: c.name)

    def get_category_stats(self) -> dict[str, int]:
        """
        Get statistics about each category (flat dict for backwards compatibility).

        Returns:
            Dictionary mapping category paths to note counts
        """
        stats = {}

        # Walk through all directories
        for dirpath, dirnames, filenames in os.walk(self.base_path):
            dir_path = Path(dirpath)

            # Get relative path from base
            try:
                rel_path = dir_path.relative_to(self.base_path)
                cat_path = str(rel_path) if str(rel_path) != '.' else ''
            except ValueError:
                continue

            # Count markdown files in this directory only
            md_count = len([f for f in filenames if f.endswith('.md')])

            if cat_path or md_count > 0:  # Include root if it has notes
                stats[cat_path if cat_path else 'root'] = md_count

        return stats
