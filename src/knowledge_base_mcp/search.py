"""Search functionality for the knowledge base."""

from typing import Optional

from .models import Note, SearchResult


class KnowledgeBaseSearch:
    """Handles searching through notes."""

    def __init__(self, storage):
        """
        Initialize the search engine.

        Args:
            storage: KnowledgeBaseStorage instance
        """
        self.storage = storage

    def search(
        self,
        query: str = "",
        category: Optional[str] = None,
        tags: Optional[list[str]] = None
    ) -> list[SearchResult]:
        """
        Search through all notes.

        Args:
            query: Search term (searches title, content, tags) - case insensitive
            category: Optional category filter
            tags: Optional list of tags to filter by (matches any)

        Returns:
            List of SearchResult objects sorted by relevance
        """
        # Get all notes (potentially filtered by category)
        all_notes = self.storage.list_notes(category=category)

        results = []

        for note in all_notes:
            # Apply tag filter if specified (match any tag)
            if tags:
                note_tags_lower = [t.lower() for t in note.frontmatter.tags]
                search_tags_lower = [t.lower() for t in tags]

                if not any(tag in note_tags_lower for tag in search_tags_lower):
                    continue

            # Calculate relevance score
            relevance = self._calculate_relevance(note, query)

            # Include all notes if no query, or only matches if query provided
            if not query or relevance > 0:
                results.append(SearchResult(note=note, relevance_score=relevance))

        # Sort by relevance (highest first)
        results.sort(key=lambda r: r.relevance_score, reverse=True)

        return results

    def _calculate_relevance(self, note: Note, query: str) -> float:
        """
        Calculate relevance score for a note based on query.

        Args:
            note: Note to score
            query: Search query

        Returns:
            Relevance score (higher is more relevant)
        """
        if not query:
            return 1.0  # All notes equally relevant if no query

        query_lower = query.lower()
        score = 0.0

        # Title match (highest weight)
        title_lower = note.title.lower()
        if query_lower == title_lower:
            score += 10.0  # Exact match
        elif query_lower in title_lower:
            score += 5.0  # Partial match

        # Tag match (high weight)
        for tag in note.frontmatter.tags:
            tag_lower = tag.lower()
            if query_lower == tag_lower:
                score += 8.0  # Exact tag match
            elif query_lower in tag_lower:
                score += 4.0  # Partial tag match

        # Content match (lower weight, but count occurrences)
        content_lower = note.content.lower()
        occurrences = content_lower.count(query_lower)
        score += occurrences * 0.5

        # Metadata match (medium weight)
        for key, value in note.frontmatter.metadata.items():
            if isinstance(value, str):
                value_lower = value.lower()
                if query_lower in value_lower:
                    score += 2.0

        return score

    def search_formatted(
        self,
        query: str = "",
        category: Optional[str] = None,
        tags: Optional[list[str]] = None
    ) -> str:
        """
        Search and return formatted results as a string.

        Args:
            query: Search term
            category: Optional category filter
            tags: Optional list of tags to filter by

        Returns:
            Formatted search results string
        """
        results = self.search(query=query, category=category, tags=tags)

        if not results:
            return "No results found."

        # Format results
        output_lines = [f"Found {len(results)} result(s):\n"]

        for result in results:
            output_lines.append(str(result))
            output_lines.append("")  # Blank line between results

        return "\n".join(output_lines)
