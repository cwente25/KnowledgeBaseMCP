"""Search routes"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import SearchResult, NoteResponse
from ..auth import get_current_user
from ..models import User
from ..services.note_service import NoteService

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/", response_model=list[dict])
async def search_notes(
    q: str = Query(..., min_length=1, description="Search query"),
    category: Optional[str] = Query(None, description="Filter by category"),
    tags: Optional[str] = Query(None, description="Filter by tags (comma-separated)"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of results"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Search notes using full-text search

    Requires authentication. Returns notes ordered by relevance score.

    The search uses the Phase 1 search engine which indexes title, content, and tags.
    """
    service = NoteService(db)

    # Parse tags if provided
    tag_list = [tag.strip() for tag in tags.split(",")] if tags else None

    # Perform search
    results = service.search_notes(
        query=q,
        category=category,
        tags=tag_list,
        limit=limit
    )

    # Format results
    return [
        {
            "note": result["note"],
            "score": result["score"]
        }
        for result in results
    ]
