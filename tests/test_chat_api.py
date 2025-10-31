"""Tests for chat/AI endpoint"""
import pytest


def test_chat_without_api_key(client, auth_headers):
    """Test chat endpoint when API key is not configured"""
    response = client.post(
        "/chat",
        headers=auth_headers,
        json={"message": "Hello, AI!"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "conversation_id" in data
    assert "notes_accessed" in data
    assert "actions_taken" in data

    # Should return error message about missing API key
    assert "not configured" in data["response"].lower() or "api" in data["response"].lower()


def test_chat_with_conversation_id(client, auth_headers):
    """Test chat with existing conversation ID"""
    conv_id = "test-conversation-123"

    response = client.post(
        "/chat",
        headers=auth_headers,
        json={
            "message": "Test message",
            "conversation_id": conv_id
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["conversation_id"] == conv_id


def test_chat_missing_message(client, auth_headers):
    """Test chat without message fails"""
    response = client.post(
        "/chat",
        headers=auth_headers,
        json={}
    )
    assert response.status_code == 422  # Validation error


def test_chat_empty_message(client, auth_headers):
    """Test chat with empty message fails"""
    response = client.post(
        "/chat",
        headers=auth_headers,
        json={"message": ""}
    )
    assert response.status_code == 422  # Min length validation


def test_chat_no_auth(client):
    """Test chat without authentication fails"""
    response = client.post(
        "/chat",
        json={"message": "Hello"}
    )
    assert response.status_code == 403


def test_clear_conversation(client, auth_headers):
    """Test clearing a conversation"""
    conv_id = "test-conversation-to-clear"

    response = client.delete(f"/chat/{conv_id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "message" in data


def test_clear_conversation_no_auth(client):
    """Test clearing conversation without authentication fails"""
    response = client.delete("/chat/some-id")
    assert response.status_code == 403
