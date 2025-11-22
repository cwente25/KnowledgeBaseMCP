"""AI chat routes with SSE streaming and tool execution"""
import json
import uuid
from typing import Optional, Dict, List, Any
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import ChatMessage
from ..dependencies import get_optional_active_user
from ..models import User
from ..services.claude_service import ClaudeService, KNOWLEDGE_BASE_TOOLS
from ..services.tool_executor import ToolExecutor

router = APIRouter(prefix="/chat", tags=["chat"])

# In-memory conversation storage
conversations: Dict[str, List[Dict[str, Any]]] = {}

SYSTEM_PROMPT = """You are a helpful assistant with access to the user's knowledge base. Use the tools to search and retrieve notes to answer questions.

When the user asks about their notes or knowledge base, use the available tools:
- search_notes: Search for notes by query
- get_note: Get full content of a specific note
- create_note: Create a new note
- update_note: Update an existing note
- list_categories: List all categories with note counts

Always be helpful and provide accurate information based on the user's knowledge base."""


@router.post("/")
async def chat(
    message: ChatMessage,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_active_user)
):
    """
    Send a message to the AI assistant with SSE streaming

    The AI assistant can:
    - Search your knowledge base for relevant information
    - Answer questions about your notes
    - Help create, update, or organize notes
    - Provide summaries and insights

    Returns Server-Sent Events stream with chat chunks.
    """
    # Generate or use existing conversation ID
    conversation_id = message.conversation_id or str(uuid.uuid4())

    # Get or create conversation history
    if conversation_id not in conversations:
        conversations[conversation_id] = []

    # Add user message to history
    conversations[conversation_id].append({
        "role": "user",
        "content": message.message
    })

    async def generate_stream():
        try:
            # Initialize services
            claude_service = ClaudeService()
            tool_executor = ToolExecutor(db)

            # Send conversation_id first
            yield f"data: {json.dumps({'type': 'conversation_id', 'conversation_id': conversation_id})}\n\n"

            # Get current messages
            messages = conversations[conversation_id].copy()

            # Tool loop
            while True:
                # Call Claude API
                response = await claude_service.send_message(
                    messages=messages,
                    tools=KNOWLEDGE_BASE_TOOLS,
                    system=SYSTEM_PROMPT,
                    max_tokens=4096
                )

                # Process response content
                assistant_content = response["content"]
                text_response = ""
                tool_uses = []

                for block in assistant_content:
                    if hasattr(block, 'type'):
                        if block.type == "text":
                            text_response += block.text
                            # Stream text chunks
                            yield f"data: {json.dumps({'type': 'text', 'content': block.text})}\n\n"
                        elif block.type == "tool_use":
                            tool_uses.append({
                                "id": block.id,
                                "name": block.name,
                                "input": block.input
                            })

                # Add assistant message to history
                conversations[conversation_id].append({
                    "role": "assistant",
                    "content": assistant_content
                })
                messages = conversations[conversation_id].copy()

                # If no tool use, we're done
                if response["stop_reason"] != "tool_use" or not tool_uses:
                    break

                # Execute tools and add results
                tool_results = []
                for tool_use in tool_uses:
                    # Notify about tool execution
                    yield f"data: {json.dumps({'type': 'tool_call', 'tool': tool_use['name'], 'input': tool_use['input']})}\n\n"

                    # Execute tool
                    result = tool_executor.execute(tool_use["name"], tool_use["input"])

                    # Notify about tool result
                    yield f"data: {json.dumps({'type': 'tool_result', 'tool': tool_use['name'], 'result': result})}\n\n"

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use["id"],
                        "content": json.dumps(result)
                    })

                # Add tool results to conversation
                conversations[conversation_id].append({
                    "role": "user",
                    "content": tool_results
                })
                messages = conversations[conversation_id].copy()

            # Send done event
            yield f"data: {json.dumps({'type': 'done', 'conversation_id': conversation_id})}\n\n"

        except ValueError as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': f'Internal error: {str(e)}'})}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.delete("/{conversation_id}")
async def clear_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_active_user)
):
    """
    Clear a conversation history

    This removes the conversation from memory. Use this to start fresh.
    """
    if conversation_id in conversations:
        del conversations[conversation_id]

    return {"message": "Conversation cleared"}
