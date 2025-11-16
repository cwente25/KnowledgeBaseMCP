# Knowledge Base MCP - Current Status

**Last Updated**: 2025-11-16
**Branch**: `claude/fix-authentication-ui-01436PCW2kpvWajnsH8Fd14d`

## Current Issues

### 1. Password Validation Bug
**Status**: IDENTIFIED - NEEDS FIX

**Problem**:
- Schema requires min 8 characters
- bcrypt throws "password cannot be longer than 72 bytes" error even for short passwords
- Likely a bcrypt version compatibility issue or encoding problem

**Root Cause**:
- Password validation shows `min_length=8` in schemas.py:12
- bcrypt has hardcoded 72-byte limit
- May be related to the bcrypt 4.x vs 5.x compatibility issues

**Quick Fix Options**:
1. Add max_length=72 to password field validation
2. Add password length check before hashing: `password[:72]`
3. Disable authentication entirely (if not needed)

### 2. Authentication Not Required
**User Feedback**: Authentication not needed for current use case (MCP via Claude Desktop)

**Options**:
- Keep authentication but fix password validation
- Make authentication optional via environment variable
- Disable authentication endpoints

## What Was Fixed (This Session)

### Fixed Issues:
1. ✅ **Missing JWT_SECRET_KEY** - Created `.env.local` with secure key
2. ✅ **bcrypt 5.0 incompatibility** - Pinned to bcrypt 4.x in pyproject.toml
3. ✅ **Missing .env.example entries** - Added JWT_SECRET_KEY, CORS, DEBUG settings
4. ✅ **Server starts successfully** - Running on http://localhost:8000
5. ✅ **Basic auth flow works** - Signup/login tested with shorter passwords

### Changes Made:
- **`.env.local`** (created, gitignored):
  ```env
  JWT_SECRET_KEY=qNnv8HjRZ6KdfosGThMSflgSQk69zxrAVwTBOtL7Qng
  CORS_ORIGINS=http://localhost:3000,http://localhost:8000,http://127.0.0.1:8000
  DEBUG=true
  ```

- **`.env.example`** (updated):
  - Added JWT_SECRET_KEY with generation instructions
  - Added CORS_ORIGINS configuration
  - Added DEBUG mode setting

- **`pyproject.toml`** (updated):
  - Pinned `bcrypt>=4.0.0,<5.0.0` for passlib compatibility

### Git Status:
- All changes committed to: `claude/fix-authentication-ui-01436PCW2kpvWajnsH8Fd14d`
- Pushed to remote ✅
- Ready for PR if needed

## Architecture Overview

### Project Structure:
```
/home/user/KnowledgeBaseMCP/
├── src/
│   ├── api/                 # FastAPI HTTP API
│   │   ├── main.py         # App entry point
│   │   ├── auth.py         # Auth utilities (JWT, bcrypt)
│   │   ├── schemas.py      # Pydantic models
│   │   ├── models.py       # SQLAlchemy DB models
│   │   ├── config.py       # Settings (loads from .env)
│   │   ├── database.py     # DB session management
│   │   └── routers/        # API endpoints
│   │       ├── auth.py     # /auth/* endpoints
│   │       ├── notes.py    # /notes/* endpoints
│   │       ├── search.py   # /search endpoint
│   │       ├── chat.py     # /chat endpoint
│   │       └── categories.py
│   └── knowledge_base_mcp/  # MCP Server
│       └── server.py       # MCP protocol implementation
├── tests/                   # pytest tests
├── .env.local              # Local config (gitignored)
├── .env.example            # Config template
├── pyproject.toml          # Dependencies & config
└── knowledge_base.db       # SQLite database
```

### Authentication Flow:
1. **Signup**: `POST /auth/signup` → Creates user, hashes password with bcrypt
2. **Login**: `POST /auth/login` → Returns JWT token (24hr expiry)
3. **Protected routes**: Require `Authorization: Bearer <token>` header
4. **Token validation**: JWT decoded with secret from .env

### Dependencies:
- **FastAPI** - HTTP API framework
- **SQLAlchemy** - Database ORM
- **passlib + bcrypt** - Password hashing
- **PyJWT** - JWT token creation/validation
- **MCP** - Model Context Protocol server
- **Anthropic** - AI integration

## API Endpoints

### Public:
- `POST /auth/signup` - Create account (min 8 char password)
- `POST /auth/login` - Get JWT token
- `GET /health` - Health check

### Protected (require auth):
- `GET /auth/me` - Current user info
- `GET /notes` - List notes
- `POST /notes` - Create note
- `GET /notes/{id}` - Get note
- `PATCH /notes/{id}` - Update note
- `DELETE /notes/{id}` - Delete note
- `GET /categories` - List categories
- `POST /chat` - Chat with AI
- `POST /search` - Search notes

## Environment Variables

### Required:
- `JWT_SECRET_KEY` - **MUST BE SET** (generate with: `python -c "import secrets; print(secrets.token_urlsafe(32))"`)

### Optional (with defaults):
- `DATABASE_URL` - Default: `sqlite:///./knowledge_base.db`
- `KNOWLEDGE_BASE_PATH` - Default: `~/knowledge-base`
- `API_HOST` - Default: `0.0.0.0`
- `API_PORT` - Default: `8000`
- `CORS_ORIGINS` - Default: `http://localhost:8000`
- `DEBUG` - Default: `false`
- `ANTHROPIC_API_KEY` - Optional for AI features
- `CATEGORIES` - Default: `people,recipes,meetings,procedures,tasks`

## How to Run

### Start API Server:
```bash
# Option 1: Using uvicorn directly
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --loop asyncio

# Option 2: Using project script (after pip install -e .)
knowledge-base-api

# Option 3: Using python module
python -m src.api.main
```

### Start MCP Server (for Claude Desktop):
```bash
knowledge-base-server
```

## Known Issues & TODOs

### Immediate:
- [ ] Fix password validation (72 byte bcrypt limit error on 8 char passwords)
- [ ] Decide if authentication should be optional
- [ ] Add password max_length validation to schema

### Future:
- [ ] Web UI (currently only API exists)
- [ ] Better error messages for auth failures
- [ ] Password reset functionality
- [ ] Multi-user support vs single-user mode
- [ ] Migration from SQLite to PostgreSQL for production

## Quick Commands

### Test authentication:
```bash
# Signup
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "test1234", "full_name": "Test User"}'

# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "test1234"}'

# Access protected endpoint
curl -X GET http://localhost:8000/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### Database:
```bash
# View database
sqlite3 knowledge_base.db "SELECT * FROM users;"
sqlite3 knowledge_base.db "SELECT * FROM notes;"

# Reset database
rm knowledge_base.db
# Server will recreate on next startup
```

## Next Steps (Choose One)

### Option A: Fix Password Validation
1. Add `max_length=72` to password field in schemas.py
2. Add pre-hash validation to truncate passwords
3. Update error messages to be clearer
4. Test with various password lengths

### Option B: Make Authentication Optional
1. Add `REQUIRE_AUTH=false` environment variable
2. Skip JWT validation when disabled
3. All endpoints become public
4. Suitable for single-user local use

### Option C: Remove Authentication
1. Remove auth router
2. Remove user_id from notes table
3. Simplify to single-user mode
4. Focus on MCP server functionality

## Contact / Notes
- User doesn't need authentication for current use case
- Currently using MCP server via Claude Desktop
- API was added but authentication blocking usage
