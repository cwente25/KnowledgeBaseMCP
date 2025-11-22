"""Pydantic schemas for request/response validation"""
from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, EmailStr, Field


# ============= Auth Schemas =============

class UserCreate(BaseModel):
    """Schema for creating a new user"""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=72, description="Password (8-72 characters)")
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    """Schema for user login"""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Schema for user response (without password)"""
    id: str
    email: str
    full_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    """Schema for authentication token"""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Schema for token payload data"""
    email: Optional[str] = None


# ============= Note Schemas =============

class NoteBase(BaseModel):
    """Base schema for note attributes"""
    title: str = Field(..., min_length=1, max_length=500)
    content: str
    category: str = Field(..., min_length=1, max_length=100)
    tags: List[str] = Field(default_factory=list)
    metadata: Dict = Field(default_factory=dict)


class NoteCreate(NoteBase):
    """Schema for creating a new note"""
    pass


class NoteUpdate(BaseModel):
    """Schema for updating a note (all fields optional)"""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    content: Optional[str] = None
    category: Optional[str] = Field(None, min_length=1, max_length=100)
    tags: Optional[List[str]] = None
    metadata: Optional[Dict] = None


class NoteResponse(BaseModel):
    """Schema for note response"""
    id: str
    title: str = Field(..., min_length=1, max_length=500)
    content: str
    category: str = Field(..., min_length=1, max_length=100)
    tags: List[str] = Field(default_factory=list)
    metadata: Dict = Field(default_factory=dict, validation_alias='note_metadata')
    file_path: str
    created_at: datetime
    updated_at: datetime
    user_id: Optional[str] = None

    class Config:
        from_attributes = True
        populate_by_name = True


# ============= Search Schemas =============

class SearchQuery(BaseModel):
    """Schema for search query"""
    q: str = Field(..., min_length=1, description="Search query")
    category: Optional[str] = Field(None, description="Filter by category")
    tags: Optional[str] = Field(None, description="Filter by tags (comma-separated)")
    limit: int = Field(10, ge=1, le=100, description="Maximum number of results")
    offset: int = Field(0, ge=0, description="Offset for pagination")


class SearchResult(BaseModel):
    """Schema for search result"""
    note: NoteResponse
    score: float = Field(..., description="Relevance score")


class SearchResponse(BaseModel):
    """Schema for search response"""
    results: List[SearchResult]
    total: int
    query: str


# ============= Chat Schemas =============

class ChatMessage(BaseModel):
    """Schema for chat message"""
    message: str = Field(..., min_length=1)
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Schema for chat response"""
    response: str
    conversation_id: str
    notes_accessed: List[str] = Field(default_factory=list, description="IDs of notes accessed")
    actions_taken: List[Dict] = Field(default_factory=list, description="Actions performed by AI")


# ============= Category Schemas =============

class CategoryInfo(BaseModel):
    """Schema for category information"""
    name: str
    count: int


class CategoriesResponse(BaseModel):
    """Schema for categories response"""
    categories: List[CategoryInfo]
    total_notes: int


# ============= General Schemas =============

class HealthCheck(BaseModel):
    """Schema for health check response"""
    status: str
    version: str
    database: str
    mcp_enabled: bool


class ErrorResponse(BaseModel):
    """Schema for error response"""
    detail: str
    error_code: Optional[str] = None
