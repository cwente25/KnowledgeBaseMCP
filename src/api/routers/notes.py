"""Notes CRUD routes"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import NoteCreate, NoteUpdate, NoteResponse
from ..dependencies import get_optional_active_user
from ..models import User
from ..services.note_service import NoteService

router = APIRouter(prefix="/notes", tags=["notes"])


@router.post("/", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
async def create_note(
    note_data: NoteCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_active_user)
):
    """
    Create a new note

    Authentication optional (controlled by REQUIRE_AUTH setting).
    The note will be saved both to the database and as a markdown file.
    """
    service = NoteService(db)

    try:
        note = service.create_note(
            title=note_data.title,
            content=note_data.content,
            category=note_data.category,
            tags=note_data.tags,
            metadata=note_data.metadata,
            user_id=current_user.id if current_user else None
        )
        return note
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/", response_model=List[NoteResponse])
async def list_notes(
    category: Optional[str] = Query(None, description="Filter by category"),
    tags: Optional[str] = Query(None, description="Filter by tags (comma-separated)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_active_user)
):
    """
    List all notes with optional filters

    Authentication optional (controlled by REQUIRE_AUTH setting).
    Returns notes ordered by creation date (newest first).
    """
    service = NoteService(db)

    # Parse tags if provided
    tag_list = [tag.strip() for tag in tags.split(",")] if tags else None

    notes = service.list_notes(
        category=category,
        tags=tag_list,
        limit=limit,
        offset=offset,
        user_id=current_user.id if current_user else None
    )

    return notes


@router.get("/{note_id}", response_model=NoteResponse)
async def get_note(
    note_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_active_user)
):
    """
    Get a specific note by ID

    Authentication optional (controlled by REQUIRE_AUTH setting).
    """
    service = NoteService(db)
    note = service.get_note(note_id)

    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found"
        )

    # Check if user owns the note (only when auth is enabled)
    if current_user and note.user_id and note.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this note"
        )

    return note


@router.put("/{note_id}", response_model=NoteResponse)
async def update_note(
    note_id: str,
    note_data: NoteUpdate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_active_user)
):
    """
    Update a note

    Authentication optional (controlled by REQUIRE_AUTH setting).
    Only provided fields will be updated.
    """
    service = NoteService(db)

    # Check if note exists and user owns it
    existing_note = service.get_note(note_id)
    if not existing_note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found"
        )

    # Check ownership only when auth is enabled
    if current_user and existing_note.user_id and existing_note.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this note"
        )

    try:
        note = service.update_note(
            note_id=note_id,
            title=note_data.title,
            content=note_data.content,
            category=note_data.category,
            tags=note_data.tags,
            metadata=note_data.metadata
        )

        if not note:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Note not found"
            )

        return note
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_active_user)
):
    """
    Delete a note

    Authentication optional (controlled by REQUIRE_AUTH setting).
    Removes both the database entry and markdown file.
    """
    service = NoteService(db)

    # Check if note exists and user owns it
    existing_note = service.get_note(note_id)
    if not existing_note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found"
        )

    # Check ownership only when auth is enabled
    if current_user and existing_note.user_id and existing_note.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this note"
        )

    try:
        success = service.delete_note(note_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Note not found"
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
