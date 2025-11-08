"""Data models for the knowledge base."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional, List


@dataclass
class NoteFrontmatter:
    """Represents the YAML frontmatter of a note."""

    tags: list[str] = field(default_factory=list)
    date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    category: str = ""
    updated: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)  # For category-specific fields

    def to_dict(self) -> dict[str, Any]:
        """Convert frontmatter to dictionary for YAML serialization."""
        result = {
            "tags": self.tags,
            "date": self.date,
            "category": self.category,
        }

        if self.updated:
            result["updated"] = self.updated

        # Add any additional metadata fields
        result.update(self.metadata)

        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NoteFrontmatter":
        """Create frontmatter from dictionary."""
        tags = data.get("tags", [])
        date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
        category = data.get("category", "")
        updated = data.get("updated")

        # Extract metadata (everything else)
        metadata = {
            k: v for k, v in data.items()
            if k not in {"tags", "date", "category", "updated"}
        }

        return cls(
            tags=tags if isinstance(tags, list) else [],
            date=date,
            category=category,
            updated=updated,
            metadata=metadata
        )


@dataclass
class Note:
    """Represents a complete note with frontmatter and content."""

    title: str
    category: str
    frontmatter: NoteFrontmatter
    content: str
    file_path: str = ""

    def get_preview(self, length: int = 150) -> str:
        """Get a preview of the note content."""
        # Remove markdown headers and extra whitespace
        preview = self.content.strip()
        lines = [line.strip() for line in preview.split('\n') if line.strip() and not line.startswith('#')]
        preview = ' '.join(lines)

        if len(preview) > length:
            return preview[:length] + "..."
        return preview

    def __str__(self) -> str:
        """String representation of the note."""
        tags_str = ', '.join(self.frontmatter.tags) if self.frontmatter.tags else 'no tags'
        return f"[{self.category}] {self.title} [{tags_str}]"


@dataclass
class SearchResult:
    """Represents a search result."""

    note: Note
    relevance_score: float = 0.0

    def __str__(self) -> str:
        """Format search result for display."""
        preview = self.note.get_preview()
        tags_str = ', '.join(self.note.frontmatter.tags) if self.note.frontmatter.tags else 'no tags'
        return f"[{self.note.category}] {self.note.title} [{tags_str}]\n   {preview}"


@dataclass
class CategoryMetadata:
    """Metadata for a category."""

    description: Optional[str] = None
    created: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    custom_fields: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {"created": self.created}
        if self.description:
            result["description"] = self.description
        result.update(self.custom_fields)
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CategoryMetadata":
        """Create from dictionary."""
        description = data.get("description")
        created = data.get("created", datetime.now().strftime("%Y-%m-%d"))
        custom_fields = {
            k: v for k, v in data.items()
            if k not in {"description", "created"}
        }
        return cls(
            description=description,
            created=created,
            custom_fields=custom_fields
        )


@dataclass
class CategoryInfo:
    """Information about a category in the hierarchical structure."""

    name: str
    path: str
    note_count: int = 0
    depth: int = 0
    children: List["CategoryInfo"] = field(default_factory=list)
    metadata: Optional[CategoryMetadata] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "path": self.path,
            "note_count": self.note_count,
            "depth": self.depth,
            "children": [child.to_dict() for child in self.children],
            "metadata": self.metadata.to_dict() if self.metadata else None
        }

    def format_tree(self, indent: int = 0, show_counts: bool = True) -> str:
        """
        Format category as indented tree structure.

        Args:
            indent: Current indentation level
            show_counts: Whether to show note counts

        Returns:
            Formatted string representation
        """
        indent_str = "  " * indent
        count_str = f" ({self.note_count} notes)" if show_counts else ""
        result = f"{indent_str}{self.name}/{count_str}\n"

        for child in sorted(self.children, key=lambda c: c.name):
            result += child.format_tree(indent + 1, show_counts)

        return result
