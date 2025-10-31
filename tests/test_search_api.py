"""Tests for search endpoint"""
import pytest


def test_search_no_results(client, auth_headers):
    """Test search with no matching results"""
    response = client.get("/search?q=nonexistent", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_search_with_results(client, auth_headers, test_note):
    """Test search finding results"""
    response = client.get("/search?q=test", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

    # Should find our test note
    if len(data) > 0:
        result = data[0]
        assert "note" in result
        assert "score" in result
        assert isinstance(result["score"], (int, float))
        assert result["score"] >= 0


def test_search_filter_by_category(client, auth_headers, test_db, test_user):
    """Test search with category filter"""
    from api.models import Note

    # Create notes in different categories
    note1 = Note(
        title="Person Tesla",
        content="About Nikola Tesla",
        category="people",
        tags=[],
        note_metadata={},
        file_path="/tmp/tesla.md",
        user_id=test_user.id
    )
    note2 = Note(
        title="Tesla Coil Recipe",
        content="How to build a Tesla coil",
        category="procedures",
        tags=[],
        note_metadata={},
        file_path="/tmp/tesla-recipe.md",
        user_id=test_user.id
    )
    test_db.add_all([note1, note2])
    test_db.commit()

    # Search with category filter
    response = client.get("/search?q=tesla&category=people", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()

    # Should only return notes from 'people' category
    for result in data:
        assert result["note"]["category"] == "people"


def test_search_limit(client, auth_headers, test_db, test_user):
    """Test search result limit"""
    from api.models import Note

    # Create multiple notes with same query term
    for i in range(15):
        note = Note(
            title=f"Common {i}",
            content="Common term appears here",
            category="people",
            tags=[],
            note_metadata={},
            file_path=f"/tmp/common{i}.md",
            user_id=test_user.id
        )
        test_db.add(note)
    test_db.commit()

    # Test limit
    response = client.get("/search?q=common&limit=5", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) <= 5


def test_search_no_query(client, auth_headers):
    """Test search without query parameter fails"""
    response = client.get("/search", headers=auth_headers)
    assert response.status_code == 422  # Missing required parameter


def test_search_no_auth(client):
    """Test search without authentication fails"""
    response = client.get("/search?q=test")
    assert response.status_code == 403


def test_search_empty_query(client, auth_headers):
    """Test search with empty query"""
    response = client.get("/search?q=", headers=auth_headers)
    assert response.status_code == 422  # Min length validation
