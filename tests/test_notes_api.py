"""Tests for notes CRUD endpoints"""
import pytest


def test_create_note_success(client, auth_headers):
    """Test creating a new note"""
    response = client.post(
        "/notes",
        headers=auth_headers,
        json={
            "title": "My First Note",
            "content": "This is the content of my note",
            "category": "people",
            "tags": ["test", "important"],
            "metadata": {"source": "test"}
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "My First Note"
    assert data["content"] == "This is the content of my note"
    assert data["category"] == "people"
    assert data["tags"] == ["test", "important"]
    assert data["metadata"] == {"source": "test"}
    assert "id" in data
    assert "file_path" in data
    assert "created_at" in data


def test_create_note_no_auth(client):
    """Test creating note without authentication fails"""
    response = client.post(
        "/notes",
        json={
            "title": "Unauthorized Note",
            "content": "This should fail",
            "category": "people",
            "tags": [],
            "metadata": {}
        }
    )
    assert response.status_code == 403


def test_create_note_invalid_data(client, auth_headers):
    """Test creating note with invalid data fails"""
    response = client.post(
        "/notes",
        headers=auth_headers,
        json={
            "title": "",  # Empty title
            "content": "Content",
            "category": "people",
            "tags": [],
            "metadata": {}
        }
    )
    assert response.status_code == 422  # Validation error


def test_list_notes_empty(client, auth_headers):
    """Test listing notes when none exist"""
    response = client.get("/notes", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_list_notes_with_data(client, auth_headers, test_note):
    """Test listing notes when notes exist"""
    response = client.get("/notes", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1

    # Check first note
    note = data[0]
    assert "id" in note
    assert "title" in note
    assert "content" in note
    assert "category" in note
    assert "tags" in note


def test_list_notes_filter_by_category(client, auth_headers, test_db, test_user):
    """Test filtering notes by category"""
    from api.models import Note

    # Create notes in different categories
    note1 = Note(
        title="Person Note",
        content="About a person",
        category="people",
        tags=[],
        note_metadata={},
        file_path="/tmp/person.md",
        user_id=test_user.id
    )
    note2 = Note(
        title="Recipe Note",
        content="How to cook",
        category="recipes",
        tags=[],
        note_metadata={},
        file_path="/tmp/recipe.md",
        user_id=test_user.id
    )
    test_db.add_all([note1, note2])
    test_db.commit()

    # Filter by category
    response = client.get("/notes?category=people", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    for note in data:
        assert note["category"] == "people"


def test_list_notes_pagination(client, auth_headers, test_db, test_user):
    """Test notes pagination"""
    from api.models import Note

    # Create multiple notes
    for i in range(5):
        note = Note(
            title=f"Note {i}",
            content=f"Content {i}",
            category="people",
            tags=[],
            note_metadata={},
            file_path=f"/tmp/note{i}.md",
            user_id=test_user.id
        )
        test_db.add(note)
    test_db.commit()

    # Test limit
    response = client.get("/notes?limit=2", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

    # Test offset
    response = client.get("/notes?limit=2&offset=2", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


def test_get_note_success(client, auth_headers, test_note):
    """Test getting a specific note"""
    response = client.get(f"/notes/{test_note.id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_note.id
    assert data["title"] == test_note.title
    assert data["content"] == test_note.content


def test_get_note_not_found(client, auth_headers):
    """Test getting non-existent note"""
    response = client.get("/notes/nonexistent-id", headers=auth_headers)
    assert response.status_code == 404


def test_get_note_no_auth(client, test_note):
    """Test getting note without authentication fails"""
    response = client.get(f"/notes/{test_note.id}")
    assert response.status_code == 403


def test_update_note_success(client, auth_headers, test_note):
    """Test updating a note"""
    response = client.put(
        f"/notes/{test_note.id}",
        headers=auth_headers,
        json={
            "title": "Updated Title",
            "content": "Updated content"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["content"] == "Updated content"
    assert data["id"] == test_note.id


def test_update_note_partial(client, auth_headers, test_note):
    """Test partial update (only some fields)"""
    original_content = test_note.content

    response = client.put(
        f"/notes/{test_note.id}",
        headers=auth_headers,
        json={"title": "New Title Only"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "New Title Only"
    # Content should remain unchanged
    assert data["content"] == original_content


def test_update_note_not_found(client, auth_headers):
    """Test updating non-existent note"""
    response = client.put(
        "/notes/nonexistent-id",
        headers=auth_headers,
        json={"title": "New Title"}
    )
    assert response.status_code == 404


def test_update_note_no_auth(client, test_note):
    """Test updating note without authentication fails"""
    response = client.put(
        f"/notes/{test_note.id}",
        json={"title": "Unauthorized Update"}
    )
    assert response.status_code == 403


def test_delete_note_success(client, auth_headers, test_note):
    """Test deleting a note"""
    note_id = test_note.id

    response = client.delete(f"/notes/{note_id}", headers=auth_headers)
    assert response.status_code == 204

    # Verify note is deleted
    response = client.get(f"/notes/{note_id}", headers=auth_headers)
    assert response.status_code == 404


def test_delete_note_not_found(client, auth_headers):
    """Test deleting non-existent note"""
    response = client.delete("/notes/nonexistent-id", headers=auth_headers)
    assert response.status_code == 404


def test_delete_note_no_auth(client, test_note):
    """Test deleting note without authentication fails"""
    response = client.delete(f"/notes/{test_note.id}")
    assert response.status_code == 403
