"""Categories routes"""
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import CategoriesResponse, CategoryInfo
from ..dependencies import get_optional_active_user
from ..models import User
from ..services.note_service import NoteService

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("/", response_model=CategoriesResponse)
async def list_categories(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_active_user)
):
    """
    List all categories with note counts

    Authentication optional (controlled by REQUIRE_AUTH setting).
    Returns all categories that have at least one note.
    """
    service = NoteService(db)

    # Get categories with counts
    category_counts = service.get_categories()

    # Convert to response format
    categories = [
        CategoryInfo(name=name, count=count)
        for name, count in sorted(category_counts.items())
    ]

    total_notes = sum(cat.count for cat in categories)

    return CategoriesResponse(
        categories=categories,
        total_notes=total_notes
    )
