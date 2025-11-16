# Knowledge Base MCP Server

A Model Context Protocol (MCP) server for managing a personal markdown-based knowledge base. Enable AI assistants like Claude to read, search, and update your notes naturally.

## Overview

This MCP server provides AI-native access to a personal knowledge base stored as markdown files with YAML frontmatter. It allows you to:

- Create and organize notes across multiple categories
- Search through your knowledge base using natural language
- Update and maintain notes with AI assistance
- Keep all data in human-readable, portable markdown format
- Access your notes from Claude Desktop, Claude Code, or any MCP-compatible client

## Features

### Core Capabilities

- **7 MCP Tools** for complete knowledge base management
  - `add_note` - Create new notes
  - `search_notes` - Search by content, tags, or category
  - `get_note` - Retrieve full note content
  - `update_note` - Modify existing notes (replace or append)
  - `list_notes` - List notes with optional filters
  - `delete_note` - Remove notes (with backup)
  - `list_categories` - View all categories and counts

- **Smart Search** with relevance scoring
  - Search across titles, content, tags, and metadata
  - Case-insensitive matching
  - Filter by category or tags
  - Ranked results by relevance

- **Flexible Organization**
  - Default categories: people, recipes, meetings, procedures, tasks
  - Configurable category system
  - Tag-based organization
  - Rich metadata support

- **Data Safety**
  - Automatic backups before updates
  - Atomic file writes
  - Human-readable markdown format
  - No vendor lock-in

## Installation

### Prerequisites

- Python 3.11 or higher
- `uv` package manager (recommended) or `pip`

### Install with uv (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd knowledge-base-mcp

# Install dependencies
uv sync

# The server is now ready to use
```

### Install with pip

```bash
# Clone the repository
git clone <repository-url>
cd knowledge-base-mcp

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .
```

## Running the Server

This project provides **two ways** to run the knowledge base:

### Option 1: MCP Server (for Claude Desktop/Code)

The MCP server runs via stdio and is designed to be used with Claude Desktop or Claude Code.

**Start the MCP server:**

```bash
# Using uv
uv run knowledge-base-server

# Using pip/venv
knowledge-base-server
```

The MCP server will:
- Listen on stdin/stdout for MCP protocol messages
- Wait for commands from an MCP client (like Claude Desktop)
- Not show a web interface or HTTP endpoint

**Note:** The MCP server is typically not run standalone. Instead, configure it in Claude Desktop (see Configuration section below) and let Claude Desktop manage the server lifecycle.

### Option 2: HTTP API Server (for Web/API Access)

The HTTP API server provides a web interface and REST API.

**Quick Start (No Authentication):**

By default, authentication is **disabled** for easy local development. Just run:

```bash
# Using uv
uv run knowledge-base-api

# Using pip/venv
knowledge-base-api

# Or run directly with uvicorn
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

The API server will start on `http://localhost:8000` with:
- **Web UI**: `http://localhost:8000` (if web files exist)
- **API Docs**: `http://localhost:8000/docs` (Swagger UI)
- **Alternative Docs**: `http://localhost:8000/redoc` (ReDoc)
- **Health Check**: `http://localhost:8000/health`

**Using the API (No Auth):**

```bash
# Create a note
curl -X POST http://localhost:8000/notes \
  -H "Content-Type: application/json" \
  -d '{"title": "My Note", "content": "Hello World", "category": "people", "tags": ["test"]}'

# List all notes
curl http://localhost:8000/notes

# Search notes
curl "http://localhost:8000/search?q=hello"
```

**Optional: Enable Authentication**

To enable authentication (recommended for production), create a `.env.local` file:

```bash
# Enable authentication
REQUIRE_AUTH=true

# Required when auth is enabled
JWT_SECRET_KEY=your-secret-key-here-change-this-in-production

# Optional - AI features
ANTHROPIC_API_KEY=sk-ant-xxxxx

# Optional - custom paths
KNOWLEDGE_BASE_PATH=~/knowledge-base
CATEGORIES=people,recipes,meetings,procedures,tasks

# Optional - server settings
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false
```

**Generate a secure JWT secret:**

```bash
# On Linux/macOS
openssl rand -hex 32

# Or use Python
python -c "import secrets; print(secrets.token_hex(32))"
```

**Using the API with Authentication:**

When `REQUIRE_AUTH=true`, you need to authenticate:

1. Create an account:
```bash
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "your-password", "full_name": "Your Name"}'
```

2. Login to get a token:
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "your-password"}'
```

3. Use the token for authenticated requests:
```bash
curl http://localhost:8000/notes \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## Configuration

### Environment Variables

Create a `.env` file in the project root (optional):

```bash
# Knowledge base location (default: ~/knowledge-base)
KNOWLEDGE_BASE_PATH=~/knowledge-base

# Categories (comma-separated)
CATEGORIES=people,recipes,meetings,procedures,tasks

# Server settings
SERVER_NAME=Knowledge Base
LOG_LEVEL=INFO
```

### Claude Desktop Setup

Add the server to your Claude Desktop configuration:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

**Linux**: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "knowledge-base": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/knowledge-base-mcp",
        "run",
        "knowledge-base-server"
      ]
    }
  }
}
```

**Alternative (using pip/venv)**:

```json
{
  "mcpServers": {
    "knowledge-base": {
      "command": "/absolute/path/to/venv/bin/python",
      "args": [
        "-m",
        "knowledge_base_mcp.server"
      ],
      "env": {
        "KNOWLEDGE_BASE_PATH": "/path/to/your/knowledge-base"
      }
    }
  }
}
```

After configuration, restart Claude Desktop.

## Usage

### Example Interactions

#### Adding Notes

```
You: "I just met Sarah Chen at a conference. She works at Tesla on battery
     tech and is interested in our AI product. Tag this as important."

Claude: [Calls add_note tool]
✓ Note 'Sarah Chen' created in people/
  File: sarah-chen.md
  Tags: conference, tesla, important
```

#### Searching

```
You: "Who did I meet that works on batteries?"

Claude: [Calls search_notes with query="batteries"]
Found 1 result(s):

[people] Sarah Chen [conference, tesla, batteries, important]
   Battery engineer at Tesla. Met at tech conference. Interested in AI...
```

#### Retrieving Notes

```
You: "Show me my note about Sarah Chen"

Claude: [Calls get_note tool]
# Sarah Chen

**Category:** people
**Tags:** conference, tesla, batteries, important
**Date:** 2025-10-21

---

Battery engineer at Tesla...
```

#### Updating Notes

```
You: "Add to Sarah Chen's note that we scheduled a call for next Tuesday"

Claude: [Calls update_note with append=True]
✓ Note 'Sarah Chen' updated successfully
  Category: people
  Last updated: 2025-10-22
```

#### Quick Reference

```
You: "How long do I cook brussels sprouts in the air fryer?"

Claude: [Calls search_notes with query="brussels sprouts"]
Found 1 result(s):

[recipes] Brussels Sprouts [quick, vegetables, air-fryer]
   Cook at 400°F for 15-18 minutes, shake halfway through...
```

## Knowledge Base Structure

Your knowledge base is stored as markdown files in a simple folder structure:

```
~/knowledge-base/
├── people/
│   ├── sarah-chen.md
│   ├── john-doe.md
│   └── ...
├── recipes/
│   ├── brussels-sprouts.md
│   ├── chocolate-cake.md
│   └── ...
├── meetings/
│   └── q4-planning.md
├── procedures/
│   └── onboarding-checklist.md
└── tasks/
    └── launch-preparation.md
```

### Markdown Format

Each note is a markdown file with YAML frontmatter:

```markdown
---
tags: [conference, tesla, batteries, important]
date: 2025-10-21
category: people
company: Tesla
role: Battery Engineer
email: sarah.chen@tesla.com
---

# Sarah Chen

**Met:** Tech Conference 2025, Silicon Valley
**Contact:** sarah.chen@tesla.com

## Notes

Interested in our AI product for battery optimization.
Has budget approval for Q1 2026.

## Follow-up

- [ ] Send demo link by end of week
- [ ] Schedule call for next Tuesday
```

### Metadata Fields

**Required:**
- `tags`: List of tags for categorization
- `date`: Creation date (YYYY-MM-DD)
- `category`: Category folder name

**Optional (category-specific):**
- **People**: `company`, `role`, `email`, `phone`
- **Recipes**: `prep_time`, `cook_time`, `servings`
- **Meetings**: `attendees`, `meeting_date`, `location`
- **Tasks**: `priority`, `due_date`, `status`

You can add any custom metadata fields as needed.

## Development

### Running Tests

```bash
# With uv
uv run pytest

# With pip
pytest

# Run specific test file
pytest tests/test_storage.py

# Run with coverage
pytest --cov=knowledge_base_mcp tests/
```

### Project Structure

```
knowledge-base-mcp/
├── src/
│   └── knowledge_base_mcp/
│       ├── __init__.py
│       ├── server.py       # MCP server and tools
│       ├── storage.py      # File operations
│       ├── search.py       # Search functionality
│       └── models.py       # Data models
├── tests/
│   ├── test_server.py      # Integration tests
│   ├── test_storage.py     # Storage layer tests
│   └── test_search.py      # Search tests
├── examples/
│   └── sample-notes/       # Example notes
├── pyproject.toml          # Project configuration
└── README.md
```

### Adding Custom Categories

Edit your `.env` file or environment configuration:

```bash
CATEGORIES=people,recipes,meetings,procedures,tasks,books,articles,ideas
```

The server will automatically create folders for new categories.

## Troubleshooting

### Common Issues

**Server not appearing in Claude Desktop:**
- Verify the path in `claude_desktop_config.json` is absolute
- Check that the command path is correct (`uv` or python path)
- Restart Claude Desktop completely
- Check Claude Desktop logs for errors

**Notes not being created:**
- Verify `KNOWLEDGE_BASE_PATH` exists and is writable
- Check file permissions
- Ensure category is valid (use `list_categories` tool)

**Search not finding notes:**
- Verify notes have proper YAML frontmatter
- Check that tags are formatted as lists
- Try searching with simpler queries
- Use `list_notes` to see what notes exist

**Permission errors:**
- Ensure the knowledge base directory has write permissions
- On macOS, you may need to grant Claude Desktop disk access in System Preferences

### Viewing Logs

Claude Desktop logs can help diagnose issues:

- **macOS**: `~/Library/Logs/Claude/`
- **Windows**: `%APPDATA%\Claude\logs\`
- **Linux**: `~/.config/Claude/logs/`

## Use Cases

### Conference CRM
Track people you meet at conferences with contact info, notes, and follow-up tasks.

### Recipe Collection
Store recipes with tags, cook times, and personal notes about modifications.

### Meeting Notes
Keep meeting agendas, discussion points, and action items organized by topic.

### Procedure Documentation
Maintain step-by-step procedures and checklists for recurring tasks.

### Task Management
Track projects, deadlines, and task lists with priorities and status.

## Integration with Other Tools

### Obsidian
The markdown format is fully compatible with Obsidian. You can:
- Open the knowledge base in Obsidian
- Edit notes in either Obsidian or via Claude
- Use Obsidian mobile for on-the-go access
- Sync via Obsidian Sync or iCloud

### Git Version Control
Consider adding git version control to your knowledge base:

```bash
cd ~/knowledge-base
git init
git add .
git commit -m "Initial knowledge base"
```

This provides:
- Version history of all changes
- Ability to revert changes
- Backup to remote repository
- Collaboration capabilities

### File Sync
Use any file sync service:
- iCloud Drive
- Dropbox
- Google Drive
- Syncthing

## Roadmap

### Phase 2 Features (Planned)
- HTTP API for web and mobile access
- Web UI for browsing and editing
- AI pendant integration via webhooks
- Automatic summarization and insights
- Calendar integration
- Email integration

### Future Considerations
- Multi-user support
- Real-time collaboration
- Advanced search with embeddings
- Automatic tagging suggestions
- Template system for note types

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

- Report issues: [GitHub Issues]
- Documentation: [MCP Documentation](https://modelcontextprotocol.io)
- Community: [MCP Discord]

## Acknowledgments

Built with:
- [Model Context Protocol](https://modelcontextprotocol.io)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [PyYAML](https://pyyaml.org/)

---

Made with Claude Code
