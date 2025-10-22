"""MCP server for the knowledge base."""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .search import KnowledgeBaseSearch
from .storage import (
    KnowledgeBaseStorage,
    DuplicateNoteError,
    NoteNotFoundError,
    StorageError,
)

# Load environment variables
load_dotenv()

# Configuration
KNOWLEDGE_BASE_PATH = os.getenv("KNOWLEDGE_BASE_PATH", "~/knowledge-base")
CATEGORIES = os.getenv("CATEGORIES", "people,recipes,meetings,procedures,tasks").split(",")
SERVER_NAME = os.getenv("SERVER_NAME", "Knowledge Base")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Initialize storage and search
storage = KnowledgeBaseStorage(KNOWLEDGE_BASE_PATH, CATEGORIES)
search_engine = KnowledgeBaseSearch(storage)

# Create MCP server
app = Server(SERVER_NAME)


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools."""
    return [
        Tool(
            name="add_note",
            description="Create a new note in the knowledge base",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": f"Category folder (options: {', '.join(CATEGORIES)})",
                        "enum": CATEGORIES,
                    },
                    "title": {
                        "type": "string",
                        "description": "Note title (becomes filename)",
                    },
                    "content": {
                        "type": "string",
                        "description": "Markdown content of the note",
                    },
                    "tags": {
                        "type": "string",
                        "description": "Comma-separated tags (optional)",
                        "default": "",
                    },
                },
                "required": ["category", "title", "content"],
            },
        ),
        Tool(
            name="search_notes",
            description="Search through all notes by query, category, or tags",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search term (searches title, content, tags) - case insensitive",
                        "default": "",
                    },
                    "category": {
                        "type": "string",
                        "description": f"Optional category filter (options: {', '.join(CATEGORIES)})",
                    },
                    "tags": {
                        "type": "string",
                        "description": "Optional comma-separated tags to filter by (matches any)",
                    },
                },
            },
        ),
        Tool(
            name="get_note",
            description="Retrieve the full content of a specific note",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": f"Category folder (options: {', '.join(CATEGORIES)})",
                        "enum": CATEGORIES,
                    },
                    "title": {
                        "type": "string",
                        "description": "Note title (can use full filename or friendly title)",
                    },
                },
                "required": ["category", "title"],
            },
        ),
        Tool(
            name="update_note",
            description="Update an existing note's content or tags",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": f"Category folder (options: {', '.join(CATEGORIES)})",
                        "enum": CATEGORIES,
                    },
                    "title": {
                        "type": "string",
                        "description": "Note title",
                    },
                    "content": {
                        "type": "string",
                        "description": "New content (optional)",
                    },
                    "tags": {
                        "type": "string",
                        "description": "New comma-separated tags (optional)",
                    },
                    "append": {
                        "type": "boolean",
                        "description": "If true, append content instead of replacing (default: false)",
                        "default": False,
                    },
                },
                "required": ["category", "title"],
            },
        ),
        Tool(
            name="list_notes",
            description="List all notes, optionally filtered by category or tag",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": f"Optional category filter (options: {', '.join(CATEGORIES)})",
                    },
                    "tag": {
                        "type": "string",
                        "description": "Optional tag filter",
                    },
                },
            },
        ),
        Tool(
            name="delete_note",
            description="Delete a note from the knowledge base",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": f"Category folder (options: {', '.join(CATEGORIES)})",
                        "enum": CATEGORIES,
                    },
                    "title": {
                        "type": "string",
                        "description": "Note title",
                    },
                },
                "required": ["category", "title"],
            },
        ),
        Tool(
            name="list_categories",
            description="List all available categories with note counts",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    try:
        if name == "add_note":
            return await handle_add_note(arguments)
        elif name == "search_notes":
            return await handle_search_notes(arguments)
        elif name == "get_note":
            return await handle_get_note(arguments)
        elif name == "update_note":
            return await handle_update_note(arguments)
        elif name == "list_notes":
            return await handle_list_notes(arguments)
        elif name == "delete_note":
            return await handle_delete_note(arguments)
        elif name == "list_categories":
            return await handle_list_categories(arguments)
        else:
            raise ValueError(f"Unknown tool: {name}")

    except (DuplicateNoteError, NoteNotFoundError, StorageError) as e:
        return [TextContent(type="text", text=str(e))]
    except Exception as e:
        error_msg = f"❌ Error: {str(e)}"
        return [TextContent(type="text", text=error_msg)]


async def handle_add_note(arguments: dict) -> list[TextContent]:
    """Handle add_note tool call."""
    try:
        category = arguments["category"]
        title = arguments["title"]
        content = arguments["content"]
        tags_str = arguments.get("tags", "")

        # Parse tags
        tags = [tag.strip() for tag in tags_str.split(",") if tag.strip()]

        # Create note
        note = storage.create_note(
            category=category,
            title=title,
            content=content,
            tags=tags
        )

        filename = storage.sanitize_filename(title)
        result = f"✓ Note '{title}' created in {category}/\n"
        result += f"  File: {filename}.md\n"
        if tags:
            result += f"  Tags: {', '.join(tags)}"

        return [TextContent(type="text", text=result)]
    except (DuplicateNoteError, NoteNotFoundError, StorageError) as e:
        return [TextContent(type="text", text=str(e))]
    except Exception as e:
        return [TextContent(type="text", text=f"❌ Error: {str(e)}")]


async def handle_search_notes(arguments: dict) -> list[TextContent]:
    """Handle search_notes tool call."""
    query = arguments.get("query", "")
    category = arguments.get("category")
    tags_str = arguments.get("tags")

    # Parse tags
    tags = None
    if tags_str:
        tags = [tag.strip() for tag in tags_str.split(",") if tag.strip()]

    # Search
    result = search_engine.search_formatted(
        query=query,
        category=category,
        tags=tags
    )

    return [TextContent(type="text", text=result)]


async def handle_get_note(arguments: dict) -> list[TextContent]:
    """Handle get_note tool call."""
    try:
        category = arguments["category"]
        title = arguments["title"]

        # Get note
        note = storage.get_note(category, title)

        # Format output with frontmatter
        output = f"# {note.title}\n\n"
        output += f"**Category:** {note.category}\n"
        output += f"**Tags:** {', '.join(note.frontmatter.tags) if note.frontmatter.tags else 'none'}\n"
        output += f"**Date:** {note.frontmatter.date}\n"

        if note.frontmatter.updated:
            output += f"**Updated:** {note.frontmatter.updated}\n"

        # Add metadata if any
        if note.frontmatter.metadata:
            output += "\n**Additional Info:**\n"
            for key, value in note.frontmatter.metadata.items():
                output += f"- {key}: {value}\n"

        output += f"\n---\n\n{note.content}"

        return [TextContent(type="text", text=output)]
    except (DuplicateNoteError, NoteNotFoundError, StorageError) as e:
        return [TextContent(type="text", text=str(e))]
    except Exception as e:
        return [TextContent(type="text", text=f"❌ Error: {str(e)}")]


async def handle_update_note(arguments: dict) -> list[TextContent]:
    """Handle update_note tool call."""
    try:
        category = arguments["category"]
        title = arguments["title"]
        content = arguments.get("content")
        tags_str = arguments.get("tags")
        append = arguments.get("append", False)

        # Parse tags
        tags = None
        if tags_str:
            tags = [tag.strip() for tag in tags_str.split(",") if tag.strip()]

        # Update note
        note = storage.update_note(
            category=category,
            title=title,
            content=content,
            tags=tags,
            append=append
        )

        result = f"✓ Note '{title}' updated successfully\n"
        result += f"  Category: {category}\n"

        if tags:
            result += f"  Tags: {', '.join(note.frontmatter.tags)}\n"

        result += f"  Last updated: {note.frontmatter.updated}"

        return [TextContent(type="text", text=result)]
    except (DuplicateNoteError, NoteNotFoundError, StorageError) as e:
        return [TextContent(type="text", text=str(e))]
    except Exception as e:
        return [TextContent(type="text", text=f"❌ Error: {str(e)}")]


async def handle_list_notes(arguments: dict) -> list[TextContent]:
    """Handle list_notes tool call."""
    category = arguments.get("category")
    tag = arguments.get("tag")

    # Get notes
    notes = storage.list_notes(category=category, tag=tag)

    if not notes:
        return [TextContent(type="text", text="No notes found.")]

    # Group by category
    by_category = {}
    for note in notes:
        if note.category not in by_category:
            by_category[note.category] = []
        by_category[note.category].append(note)

    # Format output
    output_lines = []

    if category:
        output_lines.append(f"Notes in {category}/ ({len(notes)} total):\n")
    else:
        output_lines.append(f"All notes ({len(notes)} total):\n")

    for cat in sorted(by_category.keys()):
        cat_notes = by_category[cat]
        output_lines.append(f"\n{cat}/ ({len(cat_notes)} notes):")

        for note in sorted(cat_notes, key=lambda n: n.title):
            tags_str = ', '.join(note.frontmatter.tags) if note.frontmatter.tags else 'no tags'
            output_lines.append(f"  - {note.title} [{tags_str}]")

    return [TextContent(type="text", text="\n".join(output_lines))]


async def handle_delete_note(arguments: dict) -> list[TextContent]:
    """Handle delete_note tool call."""
    try:
        category = arguments["category"]
        title = arguments["title"]

        # Delete note
        result = storage.delete_note(category, title)

        return [TextContent(type="text", text=result)]
    except (DuplicateNoteError, NoteNotFoundError, StorageError) as e:
        return [TextContent(type="text", text=str(e))]
    except Exception as e:
        return [TextContent(type="text", text=f"❌ Error: {str(e)}")]


async def handle_list_categories(arguments: dict) -> list[TextContent]:
    """Handle list_categories tool call."""
    stats = storage.get_category_stats()

    output_lines = ["Available categories:\n"]

    for category, count in sorted(stats.items()):
        plural = "note" if count == 1 else "notes"
        output_lines.append(f"  - {category}/ ({count} {plural})")

    return [TextContent(type="text", text="\n".join(output_lines))]


def main():
    """Run the MCP server."""
    import asyncio

    async def run():
        async with stdio_server() as (read_stream, write_stream):
            await app.run(
                read_stream,
                write_stream,
                app.create_initialization_options()
            )

    asyncio.run(run())


if __name__ == "__main__":
    main()
