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
    CategoryNotFoundError,
    CategoryExistsError,
)
from .path_utils import InvalidPathError

# Load environment variables
load_dotenv()

# Configuration
KNOWLEDGE_BASE_PATH = os.getenv("KNOWLEDGE_BASE_PATH", "~/knowledge-base")
# Legacy categories for backwards compatibility (optional)
LEGACY_CATEGORIES = os.getenv("CATEGORIES", "people,recipes,meetings,procedures,tasks").split(",")
SERVER_NAME = os.getenv("SERVER_NAME", "Knowledge Base")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Initialize storage and search
storage = KnowledgeBaseStorage(KNOWLEDGE_BASE_PATH, legacy_categories=LEGACY_CATEGORIES)
search_engine = KnowledgeBaseSearch(storage)

# Create MCP server
app = Server(SERVER_NAME)


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools."""
    return [
        # Category Management Tools
        Tool(
            name="create_category",
            description="Create a new category or subcategory in the knowledge base",
            inputSchema={
                "type": "object",
                "properties": {
                    "category_path": {
                        "type": "string",
                        "description": "Category path (e.g., 'work', 'work/clients', 'personal/spiritual/devotionals'). Use forward slashes for nested categories.",
                    },
                    "description": {
                        "type": "string",
                        "description": "Optional description for the category",
                    },
                },
                "required": ["category_path"],
            },
        ),
        Tool(
            name="delete_category",
            description="Delete a category and optionally all its contents",
            inputSchema={
                "type": "object",
                "properties": {
                    "category_path": {
                        "type": "string",
                        "description": "Category path to delete (e.g., 'work/clients/acme')",
                    },
                    "confirm": {
                        "type": "boolean",
                        "description": "Must be true to delete non-empty category (safety check)",
                        "default": False,
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "If true, delete all subcategories and notes (default: true)",
                        "default": True,
                    },
                },
                "required": ["category_path"],
            },
        ),
        Tool(
            name="rename_category",
            description="Rename a category while keeping it in the same parent location",
            inputSchema={
                "type": "object",
                "properties": {
                    "old_path": {
                        "type": "string",
                        "description": "Current category path (e.g., 'work/clients')",
                    },
                    "new_name": {
                        "type": "string",
                        "description": "New name for the category (just the name, not full path)",
                    },
                },
                "required": ["old_path", "new_name"],
            },
        ),
        Tool(
            name="move_category",
            description="Move a category to a different parent location",
            inputSchema={
                "type": "object",
                "properties": {
                    "source_path": {
                        "type": "string",
                        "description": "Current category path (e.g., 'personal/work-notes')",
                    },
                    "destination_path": {
                        "type": "string",
                        "description": "New parent path (e.g., 'work/archived')",
                    },
                },
                "required": ["source_path", "destination_path"],
            },
        ),
        Tool(
            name="list_categories",
            description="List all categories in a hierarchical tree structure",
            inputSchema={
                "type": "object",
                "properties": {
                    "parent_path": {
                        "type": "string",
                        "description": "Optional: list only subcategories of this path",
                    },
                },
            },
        ),
        # Note Management Tools
        Tool(
            name="add_note",
            description="Create a new note in the knowledge base (supports hierarchical categories)",
            inputSchema={
                "type": "object",
                "properties": {
                    "category_path": {
                        "type": "string",
                        "description": "Category path (e.g., 'work', 'work/clients/acme', 'personal/spiritual'). Category will be created if it doesn't exist.",
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
                "required": ["category_path", "title", "content"],
            },
        ),
        Tool(
            name="search_notes",
            description="Search through all notes by query, category path, or tags",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search term (searches title, content, tags) - case insensitive",
                        "default": "",
                    },
                    "category_path": {
                        "type": "string",
                        "description": "Optional category path filter (e.g., 'work/clients'). Searches in this path and all subcategories by default.",
                    },
                    "tags": {
                        "type": "string",
                        "description": "Optional comma-separated tags to filter by (matches any)",
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "If true, search in subcategories too (default: true)",
                        "default": True,
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
                    "category_path": {
                        "type": "string",
                        "description": "Category path (e.g., 'work/clients/acme')",
                    },
                    "title": {
                        "type": "string",
                        "description": "Note title (can use full filename or friendly title)",
                    },
                },
                "required": ["category_path", "title"],
            },
        ),
        Tool(
            name="update_note",
            description="Update an existing note's content or tags",
            inputSchema={
                "type": "object",
                "properties": {
                    "category_path": {
                        "type": "string",
                        "description": "Category path (e.g., 'work/clients/acme')",
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
                "required": ["category_path", "title"],
            },
        ),
        Tool(
            name="list_notes",
            description="List all notes, optionally filtered by category path or tag",
            inputSchema={
                "type": "object",
                "properties": {
                    "category_path": {
                        "type": "string",
                        "description": "Optional category path filter (e.g., 'work/clients')",
                    },
                    "tag": {
                        "type": "string",
                        "description": "Optional tag filter",
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "If true, list notes in subcategories too (default: true)",
                        "default": True,
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
                    "category_path": {
                        "type": "string",
                        "description": "Category path (e.g., 'work/clients/acme')",
                    },
                    "title": {
                        "type": "string",
                        "description": "Note title",
                    },
                },
                "required": ["category_path", "title"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    try:
        # Category management tools
        if name == "create_category":
            return await handle_create_category(arguments)
        elif name == "delete_category":
            return await handle_delete_category(arguments)
        elif name == "rename_category":
            return await handle_rename_category(arguments)
        elif name == "move_category":
            return await handle_move_category(arguments)
        elif name == "list_categories":
            return await handle_list_categories(arguments)
        # Note management tools
        elif name == "add_note":
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
        else:
            raise ValueError(f"Unknown tool: {name}")

    except (DuplicateNoteError, NoteNotFoundError, StorageError,
            CategoryNotFoundError, CategoryExistsError, InvalidPathError) as e:
        return [TextContent(type="text", text=str(e))]
    except Exception as e:
        error_msg = f"❌ Error: {str(e)}"
        return [TextContent(type="text", text=error_msg)]


# Category Management Handlers

async def handle_create_category(arguments: dict) -> list[TextContent]:
    """Handle create_category tool call."""
    try:
        category_path = arguments["category_path"]
        description = arguments.get("description")

        result = storage.create_category(
            category_path=category_path,
            description=description,
            create_parents=True
        )

        return [TextContent(type="text", text=result)]
    except (CategoryExistsError, InvalidPathError, StorageError) as e:
        return [TextContent(type="text", text=str(e))]
    except Exception as e:
        return [TextContent(type="text", text=f"❌ Error: {str(e)}")]


async def handle_delete_category(arguments: dict) -> list[TextContent]:
    """Handle delete_category tool call."""
    try:
        category_path = arguments["category_path"]
        confirm = arguments.get("confirm", False)
        recursive = arguments.get("recursive", True)

        result = storage.delete_category(
            category_path=category_path,
            recursive=recursive,
            confirm=confirm
        )

        notes_deleted = result["notes_deleted"]
        subcats_deleted = result["subcategories_deleted"]

        msg = f"✓ Category '{category_path}' deleted successfully\n"
        msg += f"  Notes deleted: {notes_deleted}\n"
        msg += f"  Subcategories deleted: {subcats_deleted}"

        return [TextContent(type="text", text=msg)]
    except (CategoryNotFoundError, StorageError) as e:
        return [TextContent(type="text", text=str(e))]
    except Exception as e:
        return [TextContent(type="text", text=f"❌ Error: {str(e)}")]


async def handle_rename_category(arguments: dict) -> list[TextContent]:
    """Handle rename_category tool call."""
    try:
        old_path = arguments["old_path"]
        new_name = arguments["new_name"]

        result = storage.rename_category(
            old_path=old_path,
            new_name=new_name
        )

        return [TextContent(type="text", text=result)]
    except (CategoryNotFoundError, CategoryExistsError, InvalidPathError, StorageError) as e:
        return [TextContent(type="text", text=str(e))]
    except Exception as e:
        return [TextContent(type="text", text=f"❌ Error: {str(e)}")]


async def handle_move_category(arguments: dict) -> list[TextContent]:
    """Handle move_category tool call."""
    try:
        source_path = arguments["source_path"]
        destination_path = arguments["destination_path"]

        result = storage.move_category(
            source_path=source_path,
            destination_path=destination_path,
            create_destination=True
        )

        return [TextContent(type="text", text=result)]
    except (CategoryNotFoundError, CategoryExistsError, StorageError) as e:
        return [TextContent(type="text", text=str(e))]
    except Exception as e:
        return [TextContent(type="text", text=f"❌ Error: {str(e)}")]


# Note Management Handlers

async def handle_add_note(arguments: dict) -> list[TextContent]:
    """Handle add_note tool call."""
    try:
        category_path = arguments["category_path"]
        title = arguments["title"]
        content = arguments["content"]
        tags_str = arguments.get("tags", "")

        # Parse tags
        tags = [tag.strip() for tag in tags_str.split(",") if tag.strip()]

        # Create note (will auto-create category if needed)
        note = storage.create_note(
            category_path=category_path,
            title=title,
            content=content,
            tags=tags,
            create_category=True
        )

        filename = storage.sanitize_filename(title)
        result = f"✓ Note '{title}' created in {category_path or 'root'}/\n"
        result += f"  File: {filename}.md\n"
        if tags:
            result += f"  Tags: {', '.join(tags)}"

        return [TextContent(type="text", text=result)]
    except (DuplicateNoteError, CategoryNotFoundError, InvalidPathError, StorageError) as e:
        return [TextContent(type="text", text=str(e))]
    except Exception as e:
        return [TextContent(type="text", text=f"❌ Error: {str(e)}")]


async def handle_search_notes(arguments: dict) -> list[TextContent]:
    """Handle search_notes tool call."""
    query = arguments.get("query", "")
    category_path = arguments.get("category_path")
    tags_str = arguments.get("tags")
    recursive = arguments.get("recursive", True)

    # Parse tags
    tags = None
    if tags_str:
        tags = [tag.strip() for tag in tags_str.split(",") if tag.strip()]

    # Search
    result = search_engine.search_formatted(
        query=query,
        category_path=category_path,
        tags=tags,
        recursive=recursive
    )

    return [TextContent(type="text", text=result)]


async def handle_get_note(arguments: dict) -> list[TextContent]:
    """Handle get_note tool call."""
    try:
        category_path = arguments["category_path"]
        title = arguments["title"]

        # Get note
        note = storage.get_note(category_path, title)

        # Format output with frontmatter
        output = f"# {note.title}\n\n"
        output += f"**Category:** {note.category or 'root'}\n"
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
    except (NoteNotFoundError, StorageError) as e:
        return [TextContent(type="text", text=str(e))]
    except Exception as e:
        return [TextContent(type="text", text=f"❌ Error: {str(e)}")]


async def handle_update_note(arguments: dict) -> list[TextContent]:
    """Handle update_note tool call."""
    try:
        category_path = arguments["category_path"]
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
            category_path=category_path,
            title=title,
            content=content,
            tags=tags,
            append=append
        )

        result = f"✓ Note '{title}' updated successfully\n"
        result += f"  Category: {category_path or 'root'}\n"

        if tags:
            result += f"  Tags: {', '.join(note.frontmatter.tags)}\n"

        result += f"  Last updated: {note.frontmatter.updated}"

        return [TextContent(type="text", text=result)]
    except (NoteNotFoundError, StorageError) as e:
        return [TextContent(type="text", text=str(e))]
    except Exception as e:
        return [TextContent(type="text", text=f"❌ Error: {str(e)}")]


async def handle_list_notes(arguments: dict) -> list[TextContent]:
    """Handle list_notes tool call."""
    category_path = arguments.get("category_path")
    tag = arguments.get("tag")
    recursive = arguments.get("recursive", True)

    # Get notes
    notes = storage.list_notes(
        category_path=category_path,
        tag=tag,
        recursive=recursive
    )

    if not notes:
        return [TextContent(type="text", text="No notes found.")]

    # Group by category
    by_category = {}
    for note in notes:
        cat = note.category or 'root'
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(note)

    # Format output
    output_lines = []

    if category_path:
        recursive_str = " (including subcategories)" if recursive else " (non-recursive)"
        output_lines.append(f"Notes in {category_path}/{recursive_str} ({len(notes)} total):\n")
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
        category_path = arguments["category_path"]
        title = arguments["title"]

        # Delete note
        result = storage.delete_note(category_path, title)

        return [TextContent(type="text", text=result)]
    except (NoteNotFoundError, StorageError) as e:
        return [TextContent(type="text", text=str(e))]
    except Exception as e:
        return [TextContent(type="text", text=f"❌ Error: {str(e)}")]


async def handle_list_categories(arguments: dict) -> list[TextContent]:
    """Handle list_categories tool call."""
    parent_path = arguments.get("parent_path")

    # Get hierarchical category structure
    categories = storage.get_category_hierarchy(parent_path=parent_path)

    if not categories:
        if parent_path:
            return [TextContent(type="text", text=f"No subcategories found in '{parent_path}/'")]
        else:
            return [TextContent(type="text", text="No categories found. Create one with create_category!")]

    # Format as tree
    if parent_path:
        output = f"Categories in {parent_path}/:\n\n"
    else:
        output = "Category Hierarchy:\n\n"

    for cat in categories:
        output += cat.format_tree(indent=0, show_counts=True)

    return [TextContent(type="text", text=output)]


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
