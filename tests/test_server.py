"""Integration tests for the MCP server."""

import os
import tempfile
from unittest.mock import patch

import pytest

from knowledge_base_mcp.server import (
    handle_add_note,
    handle_search_notes,
    handle_get_note,
    handle_update_note,
    handle_list_notes,
    handle_delete_note,
    handle_list_categories,
    storage,
)
from knowledge_base_mcp.storage import KnowledgeBaseStorage


@pytest.fixture
def temp_server():
    """Set up a temporary server environment."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Patch the global storage object
        categories = ["people", "recipes", "meetings", "procedures", "tasks"]
        temp_storage = KnowledgeBaseStorage(tmpdir, categories)

        with patch('knowledge_base_mcp.server.storage', temp_storage):
            with patch('knowledge_base_mcp.server.search_engine.storage', temp_storage):
                yield temp_storage


@pytest.mark.asyncio
async def test_add_note_tool(temp_server):
    """Test the add_note tool."""
    arguments = {
        "category": "people",
        "title": "Sarah Chen",
        "content": "Battery engineer at Tesla",
        "tags": "conference, tesla, important"
    }

    result = await handle_add_note(arguments)

    assert len(result) == 1
    assert "created" in result[0].text.lower()
    assert "Sarah Chen" in result[0].text
    assert "people" in result[0].text


@pytest.mark.asyncio
async def test_add_note_duplicate_error(temp_server):
    """Test adding duplicate note returns error."""
    arguments = {
        "category": "people",
        "title": "John Doe",
        "content": "First note",
        "tags": ""
    }

    # Add first note
    await handle_add_note(arguments)

    # Try to add duplicate
    result = await handle_add_note(arguments)

    assert len(result) == 1
    assert "already exists" in result[0].text.lower()


@pytest.mark.asyncio
async def test_search_notes_tool(temp_server):
    """Test the search_notes tool."""
    # Add some notes first
    await handle_add_note({
        "category": "people",
        "title": "Sarah Chen",
        "content": "Battery engineer",
        "tags": "tesla, batteries"
    })

    await handle_add_note({
        "category": "people",
        "title": "John Doe",
        "content": "Software engineer",
        "tags": "google, software"
    })

    # Search
    arguments = {
        "query": "engineer"
    }

    result = await handle_search_notes(arguments)

    assert len(result) == 1
    assert "found" in result[0].text.lower()
    assert "Sarah Chen" in result[0].text or "John Doe" in result[0].text


@pytest.mark.asyncio
async def test_search_notes_by_category(temp_server):
    """Test searching with category filter."""
    # Add notes in different categories
    await handle_add_note({
        "category": "people",
        "title": "Person 1",
        "content": "Content",
        "tags": ""
    })

    await handle_add_note({
        "category": "recipes",
        "title": "Recipe 1",
        "content": "Content",
        "tags": ""
    })

    # Search in recipes only
    arguments = {
        "query": "",
        "category": "recipes"
    }

    result = await handle_search_notes(arguments)

    assert len(result) == 1
    assert "Recipe 1" in result[0].text
    assert "Person 1" not in result[0].text


@pytest.mark.asyncio
async def test_search_notes_by_tags(temp_server):
    """Test searching with tag filter."""
    await handle_add_note({
        "category": "people",
        "title": "Person 1",
        "content": "Content",
        "tags": "important, work"
    })

    await handle_add_note({
        "category": "people",
        "title": "Person 2",
        "content": "Content",
        "tags": "personal"
    })

    # Search by tag
    arguments = {
        "query": "",
        "tags": "important"
    }

    result = await handle_search_notes(arguments)

    assert len(result) == 1
    assert "Person 1" in result[0].text


@pytest.mark.asyncio
async def test_get_note_tool(temp_server):
    """Test the get_note tool."""
    # Add a note first
    await handle_add_note({
        "category": "recipes",
        "title": "Brussels Sprouts",
        "content": "Cook at 400F for 15 minutes",
        "tags": "quick, vegetables"
    })

    # Get the note
    arguments = {
        "category": "recipes",
        "title": "Brussels Sprouts"
    }

    result = await handle_get_note(arguments)

    assert len(result) == 1
    assert "Brussels Sprouts" in result[0].text
    assert "400F" in result[0].text
    assert "quick" in result[0].text


@pytest.mark.asyncio
async def test_get_note_not_found(temp_server):
    """Test getting non-existent note."""
    arguments = {
        "category": "people",
        "title": "Non Existent"
    }

    result = await handle_get_note(arguments)

    assert len(result) == 1
    assert "not found" in result[0].text.lower()


@pytest.mark.asyncio
async def test_update_note_tool(temp_server):
    """Test the update_note tool."""
    # Add a note first
    await handle_add_note({
        "category": "people",
        "title": "John Doe",
        "content": "Original content",
        "tags": "old"
    })

    # Update the note
    arguments = {
        "category": "people",
        "title": "John Doe",
        "content": "Updated content",
        "tags": "new, updated",
        "append": False
    }

    result = await handle_update_note(arguments)

    assert len(result) == 1
    assert "updated successfully" in result[0].text.lower()

    # Verify update
    get_result = await handle_get_note({
        "category": "people",
        "title": "John Doe"
    })

    assert "Updated content" in get_result[0].text


@pytest.mark.asyncio
async def test_update_note_append(temp_server):
    """Test appending to a note."""
    # Add a note first
    await handle_add_note({
        "category": "people",
        "title": "Jane Smith",
        "content": "Original content",
        "tags": ""
    })

    # Append content
    arguments = {
        "category": "people",
        "title": "Jane Smith",
        "content": "Additional content",
        "append": True
    }

    result = await handle_update_note(arguments)

    assert len(result) == 1
    assert "updated successfully" in result[0].text.lower()

    # Verify both contents are present
    get_result = await handle_get_note({
        "category": "people",
        "title": "Jane Smith"
    })

    assert "Original content" in get_result[0].text
    assert "Additional content" in get_result[0].text


@pytest.mark.asyncio
async def test_list_notes_tool(temp_server):
    """Test the list_notes tool."""
    # Add some notes
    await handle_add_note({
        "category": "people",
        "title": "Person 1",
        "content": "Content",
        "tags": "tag1"
    })

    await handle_add_note({
        "category": "people",
        "title": "Person 2",
        "content": "Content",
        "tags": "tag2"
    })

    await handle_add_note({
        "category": "recipes",
        "title": "Recipe 1",
        "content": "Content",
        "tags": "tag3"
    })

    # List all notes
    arguments = {}

    result = await handle_list_notes(arguments)

    assert len(result) == 1
    assert "3 total" in result[0].text
    assert "people" in result[0].text
    assert "recipes" in result[0].text


@pytest.mark.asyncio
async def test_list_notes_by_category(temp_server):
    """Test listing notes filtered by category."""
    await handle_add_note({
        "category": "people",
        "title": "Person 1",
        "content": "Content",
        "tags": ""
    })

    await handle_add_note({
        "category": "recipes",
        "title": "Recipe 1",
        "content": "Content",
        "tags": ""
    })

    # List only people
    arguments = {
        "category": "people"
    }

    result = await handle_list_notes(arguments)

    assert len(result) == 1
    assert "people" in result[0].text
    assert "Recipe 1" not in result[0].text


@pytest.mark.asyncio
async def test_list_notes_by_tag(temp_server):
    """Test listing notes filtered by tag."""
    await handle_add_note({
        "category": "people",
        "title": "Person 1",
        "content": "Content",
        "tags": "important"
    })

    await handle_add_note({
        "category": "people",
        "title": "Person 2",
        "content": "Content",
        "tags": "other"
    })

    # List only important
    arguments = {
        "tag": "important"
    }

    result = await handle_list_notes(arguments)

    assert len(result) == 1
    assert "Person 1" in result[0].text
    assert "Person 2" not in result[0].text


@pytest.mark.asyncio
async def test_delete_note_tool(temp_server):
    """Test the delete_note tool."""
    # Add a note first
    await handle_add_note({
        "category": "tasks",
        "title": "Todo Item",
        "content": "Something to do",
        "tags": ""
    })

    # Delete it
    arguments = {
        "category": "tasks",
        "title": "Todo Item"
    }

    result = await handle_delete_note(arguments)

    assert len(result) == 1
    assert "deleted" in result[0].text.lower()

    # Verify it's gone
    get_result = await handle_get_note(arguments)
    assert "not found" in get_result[0].text.lower()


@pytest.mark.asyncio
async def test_delete_note_not_found(temp_server):
    """Test deleting non-existent note."""
    arguments = {
        "category": "people",
        "title": "Non Existent"
    }

    result = await handle_delete_note(arguments)

    assert len(result) == 1
    assert "not found" in result[0].text.lower()


@pytest.mark.asyncio
async def test_list_categories_tool(temp_server):
    """Test the list_categories tool."""
    # Add notes in different categories
    await handle_add_note({
        "category": "people",
        "title": "Person 1",
        "content": "Content",
        "tags": ""
    })

    await handle_add_note({
        "category": "people",
        "title": "Person 2",
        "content": "Content",
        "tags": ""
    })

    await handle_add_note({
        "category": "recipes",
        "title": "Recipe 1",
        "content": "Content",
        "tags": ""
    })

    # List categories
    arguments = {}

    result = await handle_list_categories(arguments)

    assert len(result) == 1
    assert "people" in result[0].text
    assert "2 notes" in result[0].text
    assert "recipes" in result[0].text
    assert "1 note" in result[0].text


@pytest.mark.asyncio
async def test_add_note_no_tags(temp_server):
    """Test adding a note without tags."""
    arguments = {
        "category": "people",
        "title": "No Tags Person",
        "content": "Content without tags",
        "tags": ""
    }

    result = await handle_add_note(arguments)

    assert len(result) == 1
    assert "created" in result[0].text.lower()


@pytest.mark.asyncio
async def test_update_note_tags_only(temp_server):
    """Test updating only tags without changing content."""
    # Add a note
    await handle_add_note({
        "category": "people",
        "title": "Person",
        "content": "Original content",
        "tags": "old"
    })

    # Update only tags
    arguments = {
        "category": "people",
        "title": "Person",
        "tags": "new, updated"
    }

    result = await handle_update_note(arguments)

    assert len(result) == 1
    assert "updated successfully" in result[0].text.lower()

    # Verify content unchanged but tags updated
    get_result = await handle_get_note({
        "category": "people",
        "title": "Person"
    })

    assert "Original content" in get_result[0].text
    assert "new" in get_result[0].text


@pytest.mark.asyncio
async def test_empty_knowledge_base_list(temp_server):
    """Test listing notes in empty knowledge base."""
    arguments = {}

    result = await handle_list_notes(arguments)

    assert len(result) == 1
    assert "no notes found" in result[0].text.lower()


@pytest.mark.asyncio
async def test_search_no_results(temp_server):
    """Test search with no results."""
    arguments = {
        "query": "nonexistent"
    }

    result = await handle_search_notes(arguments)

    assert len(result) == 1
    assert "no results found" in result[0].text.lower()
