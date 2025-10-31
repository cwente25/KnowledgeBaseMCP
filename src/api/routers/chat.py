"""AI chat routes"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import ChatMessage, ChatResponse
from ..auth import get_current_user
from ..models import User
from ..services.ai_service import AIService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/", response_model=ChatResponse)
async def chat(
    message: ChatMessage,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Send a message to the AI assistant

    The AI assistant can:
    - Search your knowledge base for relevant information
    - Answer questions about your notes
    - Help create, update, or organize notes
    - Provide summaries and insights

    Requires authentication and ANTHROPIC_API_KEY to be configured.
    """
    service = AIService(db)

    result = service.chat(
        message=message.message,
        conversation_id=message.conversation_id,
        user_id=current_user.id
    )

    return ChatResponse(**result)


@router.delete("/{conversation_id}")
async def clear_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Clear a conversation history

    This removes the conversation from memory. Use this to start fresh.
    """
    service = AIService(db)
    service.clear_conversation(conversation_id)

    return {"message": "Conversation cleared"}
