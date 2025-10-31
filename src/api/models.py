"""Database models for Phase 2 API"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, ARRAY as PG_ARRAY
from sqlalchemy.orm import relationship
from .database import Base


# Helper function for UUID column compatible with both SQLite and PostgreSQL
def get_uuid_column(primary_key=False):
    """Create a UUID column that works with both SQLite and PostgreSQL"""
    return Column(
        String(36) if Base.metadata.bind and "sqlite" in str(Base.metadata.bind.url) else PG_UUID(as_uuid=True),
        primary_key=primary_key,
        default=lambda: str(uuid.uuid4()) if primary_key else None,
        nullable=False
    )


class User(Base):
    """User model for authentication"""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    notes = relationship("Note", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(email={self.email})>"


class Note(Base):
    """Note model for knowledge base entries"""
    __tablename__ = "notes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(500), nullable=False, index=True)
    category = Column(String(100), nullable=False, index=True)
    content = Column(Text, nullable=False)

    # Tags stored as JSON array (works with both SQLite and PostgreSQL)
    tags = Column(JSON, nullable=False, default=list)

    # Custom metadata stored as JSON (note: 'metadata' is reserved by SQLAlchemy)
    note_metadata = Column(JSON, nullable=False, default=dict)

    # File path for markdown file
    file_path = Column(String(1000), unique=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Foreign key to user
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)

    # Relationships
    user = relationship("User", back_populates="notes")

    def __repr__(self):
        return f"<Note(title={self.title}, category={self.category})>"

    def to_dict(self):
        """Convert note to dictionary"""
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "content": self.content,
            "tags": self.tags if isinstance(self.tags, list) else [],
            "metadata": self.note_metadata if isinstance(self.note_metadata, dict) else {},
            "file_path": self.file_path,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "user_id": self.user_id,
        }
