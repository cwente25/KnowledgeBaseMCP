"""Common FastAPI dependencies"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from .auth import get_current_user, get_optional_user
from .database import get_db
from .models import User


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user (for future extension with active/inactive status)

    Args:
        current_user: Current authenticated user

    Returns:
        Current user if active

    Raises:
        HTTPException: If user is inactive (future implementation)
    """
    # For now, all users are active
    # In the future, you could add an 'is_active' field to User model
    return current_user


async def get_optional_active_user(
    current_user: Optional[User] = Depends(get_optional_user)
) -> Optional[User]:
    """
    Get current active user if authentication is enabled.
    Returns None if authentication is disabled.

    Args:
        current_user: Current authenticated user (or None if auth disabled)

    Returns:
        Current user if active and authenticated, None if auth disabled
    """
    return current_user


def require_categories(category: str, db: Session = Depends(get_db)) -> str:
    """
    Validate that a category exists in the configured categories

    Args:
        category: Category to validate
        db: Database session

    Returns:
        Validated category

    Raises:
        HTTPException: If category is not valid
    """
    from .config import settings

    if category not in settings.categories_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid category. Must be one of: {', '.join(settings.categories_list)}"
        )
    return category
