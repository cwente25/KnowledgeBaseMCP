"""Tests for the search functionality."""

import tempfile

import pytest

from knowledge_base_mcp.search import KnowledgeBaseSearch
from knowledge_base_mcp.storage import KnowledgeBaseStorage


@pytest.fixture
def temp_kb_with_notes():
    """Create a temporary knowledge base with sample notes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        categories = ["people", "recipes", "meetings", "procedures", "tasks"]
        storage = KnowledgeBaseStorage(tmpdir, categories)

        # Add sample notes
        storage.create_note(
            category="people",
            title="Sarah Chen",
            content="Battery engineer at Tesla. Met at tech conference. Interested in AI for battery optimization.",
            tags=["conference", "tesla", "batteries", "important"],
            metadata={"company": "Tesla", "role": "Battery Engineer"}
        )

        storage.create_note(
            category="people",
            title="John Doe",
            content="Software engineer at Google. Working on search algorithms.",
            tags=["google", "software", "algorithms"],
            metadata={"company": "Google", "role": "Software Engineer"}
        )

        storage.create_note(
            category="recipes",
            title="Brussels Sprouts",
            content="Air fryer recipe. Cook at 400F for 15-18 minutes. Shake halfway through.",
            tags=["quick", "vegetables", "air-fryer"]
        )

        storage.create_note(
            category="recipes",
            title="Chocolate Cake",
            content="Bake at 350F for 30 minutes. Use dark chocolate for best results.",
            tags=["dessert", "baking"]
        )

        storage.create_note(
            category="meetings",
            title="Q4 Planning",
            content="Discuss budget and team goals for Q4. Need to finalize hiring plan.",
            tags=["planning", "important", "q4"]
        )

        search_engine = KnowledgeBaseSearch(storage)
        yield search_engine, storage


def test_search_by_title(temp_kb_with_notes):
    """Test searching by title."""
    search_engine, _ = temp_kb_with_notes

    results = search_engine.search(query="Sarah")

    assert len(results) == 1
    assert results[0].note.title == "Sarah Chen"


def test_search_by_content(temp_kb_with_notes):
    """Test searching by content."""
    search_engine, _ = temp_kb_with_notes

    results = search_engine.search(query="battery")

    assert len(results) >= 1
    assert any("battery" in r.note.content.lower() for r in results)


def test_search_by_tag(temp_kb_with_notes):
    """Test searching by tag."""
    search_engine, _ = temp_kb_with_notes

    results = search_engine.search(query="important")

    assert len(results) >= 2  # Sarah Chen and Q4 Planning


def test_search_case_insensitive(temp_kb_with_notes):
    """Test that search is case insensitive."""
    search_engine, _ = temp_kb_with_notes

    results_lower = search_engine.search(query="tesla")
    results_upper = search_engine.search(query="TESLA")
    results_mixed = search_engine.search(query="TeSLa")

    assert len(results_lower) == len(results_upper) == len(results_mixed)


def test_search_filter_by_category(temp_kb_with_notes):
    """Test filtering search results by category."""
    search_engine, _ = temp_kb_with_notes

    results = search_engine.search(query="", category="recipes")

    assert len(results) == 2
    assert all(r.note.category == "recipes" for r in results)


def test_search_filter_by_tags(temp_kb_with_notes):
    """Test filtering search results by tags."""
    search_engine, _ = temp_kb_with_notes

    results = search_engine.search(tags=["important"])

    assert len(results) >= 2
    assert all(any(tag.lower() == "important" for tag in r.note.frontmatter.tags) for r in results)


def test_search_multiple_tag_filter(temp_kb_with_notes):
    """Test filtering by multiple tags (OR logic)."""
    search_engine, _ = temp_kb_with_notes

    results = search_engine.search(tags=["tesla", "google"])

    assert len(results) == 2  # Sarah Chen and John Doe


def test_search_combined_filters(temp_kb_with_notes):
    """Test combining query, category, and tag filters."""
    search_engine, _ = temp_kb_with_notes

    results = search_engine.search(
        query="engineer",
        category="people",
        tags=["tesla"]
    )

    assert len(results) == 1
    assert results[0].note.title == "Sarah Chen"


def test_search_no_results(temp_kb_with_notes):
    """Test search with no matching results."""
    search_engine, _ = temp_kb_with_notes

    results = search_engine.search(query="nonexistent term xyz")

    assert len(results) == 0


def test_search_empty_query(temp_kb_with_notes):
    """Test search with empty query returns all notes."""
    search_engine, _ = temp_kb_with_notes

    results = search_engine.search(query="")

    assert len(results) == 5  # All notes


def test_search_relevance_scoring(temp_kb_with_notes):
    """Test that results are sorted by relevance."""
    search_engine, _ = temp_kb_with_notes

    results = search_engine.search(query="engineer")

    # Should find both engineers, but more relevant one first
    assert len(results) >= 2

    # Results should be sorted by relevance
    for i in range(len(results) - 1):
        assert results[i].relevance_score >= results[i + 1].relevance_score


def test_search_exact_title_match_high_score(temp_kb_with_notes):
    """Test that exact title match gets highest score."""
    search_engine, _ = temp_kb_with_notes

    results = search_engine.search(query="sarah chen")

    assert len(results) >= 1
    assert results[0].note.title == "Sarah Chen"
    assert results[0].relevance_score > 5.0  # Should have high score


def test_search_tag_exact_match_high_score(temp_kb_with_notes):
    """Test that exact tag match gets high score."""
    search_engine, _ = temp_kb_with_notes

    results = search_engine.search(query="tesla")

    # Find Sarah Chen's note
    sarah_result = next((r for r in results if r.note.title == "Sarah Chen"), None)
    assert sarah_result is not None
    assert sarah_result.relevance_score > 5.0  # Tag exact match


def test_search_formatted_output(temp_kb_with_notes):
    """Test formatted search output."""
    search_engine, _ = temp_kb_with_notes

    output = search_engine.search_formatted(query="engineer")

    assert "Found" in output
    assert "result" in output
    assert "Sarah Chen" in output or "John Doe" in output


def test_search_formatted_no_results(temp_kb_with_notes):
    """Test formatted output with no results."""
    search_engine, _ = temp_kb_with_notes

    output = search_engine.search_formatted(query="nonexistent")

    assert "No results found" in output


def test_search_metadata_fields(temp_kb_with_notes):
    """Test searching through metadata fields."""
    search_engine, _ = temp_kb_with_notes

    results = search_engine.search(query="Google")

    # Should find John Doe via company metadata
    assert len(results) >= 1
    assert any(r.note.title == "John Doe" for r in results)


def test_search_partial_word_match(temp_kb_with_notes):
    """Test partial word matching."""
    search_engine, _ = temp_kb_with_notes

    results = search_engine.search(query="batter")

    # Should match "battery" and "batteries"
    assert len(results) >= 1
    assert any("batter" in r.note.content.lower() for r in results)


def test_search_by_category_only(temp_kb_with_notes):
    """Test filtering by category without query."""
    search_engine, _ = temp_kb_with_notes

    results = search_engine.search(category="people")

    assert len(results) == 2
    assert all(r.note.category == "people" for r in results)


def test_search_by_tag_only(temp_kb_with_notes):
    """Test filtering by tag without query."""
    search_engine, _ = temp_kb_with_notes

    results = search_engine.search(tags=["quick"])

    assert len(results) == 1
    assert results[0].note.title == "Brussels Sprouts"


def test_search_content_multiple_occurrences(temp_kb_with_notes):
    """Test that multiple occurrences increase relevance."""
    search_engine, storage = temp_kb_with_notes

    # Add a note with multiple occurrences of a term
    storage.create_note(
        category="tasks",
        title="AI Project",
        content="AI planning meeting. Need to discuss AI architecture and AI implementation. AI is important.",
        tags=["ai", "project"]
    )

    results = search_engine.search(query="AI")

    # Find the AI Project note (title() converts "ai-project" to "Ai Project")
    ai_project = next((r for r in results if r.note.title == "Ai Project"), None)
    assert ai_project is not None

    # Should have higher score due to multiple occurrences
    assert ai_project.relevance_score > 2.0
