"""Authentication routes"""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import UserCreate, UserLogin, UserResponse, Token
from ..auth import (
    authenticate_user,
    create_access_token,
    create_user,
    get_current_user
)
from ..config import settings
from ..models import User

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Create a new user account

    Note: For MVP, this endpoint might be disabled in production
    to maintain single-user mode.
    """
    try:
        user = create_user(
            db=db,
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name
        )
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=Token)
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """
    Login with email and password

    Returns a JWT access token that should be used in the Authorization header
    for subsequent requests:
    Authorization: Bearer <token>
    """
    user = authenticate_user(db, user_data.email, user_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current user information

    Requires authentication.
    """
    return current_user


@router.post("/logout")
async def logout():
    """
    Logout (client should discard the token)

    For JWT tokens, logout is handled client-side by discarding the token.
    This endpoint is provided for API consistency.
    """
    return {"message": "Successfully logged out"}
