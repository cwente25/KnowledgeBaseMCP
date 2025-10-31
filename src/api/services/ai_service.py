"""AI service for Claude API integration"""
import json
import uuid
from typing import List, Dict, Any, Optional
from anthropic import Anthropic
from sqlalchemy.orm import Session

from ..config import settings
from .note_service import NoteService


class AIService:
    """Service for AI-assisted note management using Claude"""

    def __init__(self, db: Session):
        self.db = db
        self.client = Anthropic(api_key=settings.anthropic_api_key) if settings.anthropic_api_key else None
        self.note_service = NoteService(db)

        # In-memory conversation storage (for MVP, could be moved to database later)
        self.conversations: Dict[str, List[Dict[str, str]]] = {}

    def chat(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a chat message with AI assistance

        Args:
            message: User message
            conversation_id: Optional conversation ID to continue a conversation
            user_id: Optional user ID

        Returns:
            Dictionary with response, conversation_id, notes_accessed, and actions_taken
        """
        if not self.client:
            return {
                "response": "AI service is not configured. Please set ANTHROPIC_API_KEY in .env.local",
                "conversation_id": conversation_id or str(uuid.uuid4()),
                "notes_accessed": [],
                "actions_taken": []
            }

        # Get or create conversation
        if not conversation_id:
            conversation_id = str(uuid.uuid4())

        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = []

        conversation_history = self.conversations[conversation_id]

        # Search knowledge base for relevant context
        relevant_notes = []
        notes_accessed = []

        try:
            # Simple keyword search to find relevant notes
            search_results = self.note_service.search_notes(
                query=message,
                limit=5
            )

            for result in search_results:
                note = result["note"]
                relevant_notes.append(f"Note: {note.title}\nCategory: {note.category}\nContent: {note.content[:500]}...")
                notes_accessed.append(note.id)

        except Exception as e:
            print(f"Error searching notes: {e}")

        # Build context
        context = "\n\n".join(relevant_notes) if relevant_notes else "No relevant notes found in knowledge base."

        # System prompt
        system_prompt = f"""You are a personal knowledge base assistant. You help users manage their notes and find information.

You have access to the user's knowledge base through search. Here are the most relevant notes for the current query:

{context}

You can help users:
1. Find information in their notes
2. Create new notes (tell them what you would create and ask for confirmation)
3. Update existing notes
4. Organize and categorize information

Current categories available: {', '.join(settings.categories_list)}

Be helpful, concise, and accurate. If you don't find relevant information, say so clearly."""

        # Prepare messages
        messages = [
            *[{"role": msg["role"], "content": msg["content"]} for msg in conversation_history],
            {"role": "user", "content": message}
        ]

        # Call Claude API
        try:
            response = self.client.messages.create(
                model=settings.default_model,
                max_tokens=settings.max_tokens,
                system=system_prompt,
                messages=messages
            )

            assistant_message = response.content[0].text

            # Update conversation history
            conversation_history.append({"role": "user", "content": message})
            conversation_history.append({"role": "assistant", "content": assistant_message})

            # Keep conversation history manageable (last 20 messages)
            if len(conversation_history) > 20:
                self.conversations[conversation_id] = conversation_history[-20:]

            # Extract any actions (simplified for MVP)
            actions_taken = []

            return {
                "response": assistant_message,
                "conversation_id": conversation_id,
                "notes_accessed": notes_accessed,
                "actions_taken": actions_taken
            }

        except Exception as e:
            return {
                "response": f"Error communicating with AI: {str(e)}",
                "conversation_id": conversation_id,
                "notes_accessed": notes_accessed,
                "actions_taken": []
            }

    def clear_conversation(self, conversation_id: str):
        """Clear a conversation history"""
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]
