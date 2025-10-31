"""Tests for categories endpoint"""
import pytest


def test_get_categories_empty(client, auth_headers):
    """Test getting categories when no notes exist"""
    response = client.get("/categories", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "categories" in data
    assert "total_notes" in data
    assert isinstance(data["categories"], list)
    assert data["total_notes"] == 0


def test_get_categories_with_notes(client, auth_headers, test_db, test_user):
    """Test getting categories with notes"""
    from api.models import Note

    # Create notes in different categories
    notes = [
        Note(
            title=f"Person {i}",
            content=f"Person content {i}",
            category="people",
            tags=[],
            note_metadata={},
            file_path=f"/tmp/person{i}.md",
            user_id=test_user.id
        )
        for i in range(3)
    ] + [
        Note(
            title=f"Recipe {i}",
            content=f"Recipe content {i}",
            category="recipes",
            tags=[],
            note_metadata={},
            file_path=f"/tmp/recipe{i}.md",
            user_id=test_user.id
        )
        for i in range(2)
    ]

    test_db.add_all(notes)
    test_db.commit()

    response = client.get("/categories", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()

    assert "categories" in data
    assert "total_notes" in data
    assert data["total_notes"] == 5

    # Check categories
    categories = {cat["name"]: cat["count"] for cat in data["categories"]}
    assert categories.get("people") == 3
    assert categories.get("recipes") == 2


def test_get_categories_no_auth(client):
    """Test getting categories without authentication fails"""
    response = client.get("/categories")
    assert response.status_code == 403
