"""Note service layer - bridges API to Phase 1 storage"""
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_

from ..models import Note as DBNote, User
from ..config import settings

# Import Phase 1 storage and search
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from knowledge_base_mcp.storage import KnowledgeBaseStorage
from knowledge_base_mcp.search import KnowledgeBaseSearch


class NoteService:
    """Service for managing notes with hybrid storage (DB + markdown files)"""

    def __init__(self, db: Session):
        self.db = db
        self.storage = KnowledgeBaseStorage(Path(settings.knowledge_base_path))
        self.search_engine = KnowledgeBaseSearch(self.storage)

    def create_note(
        self,
        title: str,
        content: str,
        category: str,
        tags: List[str],
        metadata: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> DBNote:
        """
        Create a new note (saves to both database and markdown file)

        Args:
            title: Note title
            content: Note content
            category: Note category
            tags: List of tags
            metadata: Custom metadata dictionary
            user_id: Optional user ID

        Returns:
            Created note object

        Raises:
            ValueError: If note creation fails
        """
        try:
            # 1. Use Phase 1 storage to create markdown file
            file_path = self.storage.add_note(
                title=title,
                content=content,
                category=category,
                tags=tags,
                metadata=metadata
            )

            # 2. Also save to database for efficient search
            db_note = DBNote(
                title=title,
                content=content,
                category=category,
                tags=tags,
                note_metadata=metadata,
                file_path=str(file_path),
                user_id=user_id
            )
            self.db.add(db_note)
            self.db.commit()
            self.db.refresh(db_note)

            return db_note

        except Exception as e:
            self.db.rollback()
            raise ValueError(f"Failed to create note: {str(e)}")

    def get_note(self, note_id: str) -> Optional[DBNote]:
        """Get a note by ID"""
        return self.db.query(DBNote).filter(DBNote.id == note_id).first()

    def get_note_by_path(self, file_path: str) -> Optional[DBNote]:
        """Get a note by file path"""
        return self.db.query(DBNote).filter(DBNote.file_path == file_path).first()

    def list_notes(
        self,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0,
        user_id: Optional[str] = None
    ) -> List[DBNote]:
        """
        List notes with optional filters

        Args:
            category: Filter by category
            tags: Filter by tags (notes must have at least one of these tags)
            limit: Maximum number of results
            offset: Offset for pagination
            user_id: Filter by user ID

        Returns:
            List of notes
        """
        query = self.db.query(DBNote)

        if user_id:
            query = query.filter(DBNote.user_id == user_id)

        if category:
            query = query.filter(DBNote.category == category)

        if tags:
            # SQLite JSON contains check (this works differently in PostgreSQL)
            # For SQLite, we'll do a simpler check
            for tag in tags:
                query = query.filter(DBNote.tags.contains([tag]))

        query = query.order_by(DBNote.created_at.desc())
        query = query.limit(limit).offset(offset)

        return query.all()

    def search_notes(
        self,
        query: str,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search notes using Phase 1 search engine

        Args:
            query: Search query
            category: Optional category filter
            tags: Optional tags filter
            limit: Maximum number of results

        Returns:
            List of search results with scores
        """
        # Use Phase 1 search engine
        results = self.search_engine.search(
            query=query,
            category=category,
            tags=tags
        )

        # Convert to database notes with scores
        search_results = []
        for result in results[:limit]:  # Apply limit after search
            # Find note in database by file path
            note_path = result.note.file_path
            db_note = self.get_note_by_path(str(note_path))
            if db_note:
                search_results.append({
                    "note": db_note,
                    "score": result.relevance_score
                })

        return search_results

    def update_note(
        self,
        note_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[DBNote]:
        """
        Update a note

        Args:
            note_id: Note ID
            title: New title (optional)
            content: New content (optional)
            category: New category (optional)
            tags: New tags (optional)
            metadata: New metadata (optional)

        Returns:
            Updated note or None if not found
        """
        note = self.get_note(note_id)
        if not note:
            return None

        try:
            # Update database fields
            if title is not None:
                note.title = title
            if content is not None:
                note.content = content
            if category is not None:
                note.category = category
            if tags is not None:
                note.tags = tags
            if metadata is not None:
                note.note_metadata = metadata

            # Update markdown file using Phase 1 storage
            self.storage.update_note(
                file_path=Path(note.file_path),
                title=note.title,
                content=note.content,
                tags=note.tags,
                metadata=note.note_metadata
            )

            self.db.commit()
            self.db.refresh(note)

            return note

        except Exception as e:
            self.db.rollback()
            raise ValueError(f"Failed to update note: {str(e)}")

    def delete_note(self, note_id: str) -> bool:
        """
        Delete a note (removes from database and markdown file)

        Args:
            note_id: Note ID

        Returns:
            True if deleted, False if not found
        """
        note = self.get_note(note_id)
        if not note:
            return False

        try:
            # Delete markdown file using Phase 1 storage
            self.storage.delete_note(Path(note.file_path))

            # Delete from database
            self.db.delete(note)
            self.db.commit()

            return True

        except Exception as e:
            self.db.rollback()
            raise ValueError(f"Failed to delete note: {str(e)}")

    def get_categories(self) -> Dict[str, int]:
        """
        Get all categories with note counts

        Returns:
            Dictionary mapping category names to note counts
        """
        from sqlalchemy import func

        results = self.db.query(
            DBNote.category,
            func.count(DBNote.id).label('count')
        ).group_by(DBNote.category).all()

        return {category: count for category, count in results}
