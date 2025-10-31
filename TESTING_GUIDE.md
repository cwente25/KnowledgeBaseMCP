# Testing the Knowledge Base API

This guide shows you how to test your Knowledge Base API server.

## Step 1: Start the Server

```bash
cd /home/user/KnowledgeBaseMCP
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
✓ Database initialized
✓ Knowledge base path: /home/user/knowledge-base
✓ Categories: people, recipes, meetings, procedures, tasks
```

## Step 2: Test Using Web Browser (Easiest!)

Open your browser and visit:

### Interactive API Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

Click on any endpoint → "Try it out" → Fill in parameters → "Execute"

### Quick Health Check
- http://localhost:8000/health

Should show:
```json
{
  "status": "healthy",
  "version": "0.2.0",
  "database": "sqlite",
  "mcp_enabled": true
}
```

## Step 3: Test Using curl (Command Line)

### 1. Health Check
```bash
curl http://localhost:8000/health
```

### 2. Create a User
```bash
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "you@example.com",
    "password": "yourpass",
    "full_name": "Your Name"
  }'
```

### 3. Login (Get Token)
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "you@example.com",
    "password": "yourpass"
  }'
```

**Save the token** from the response:
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

### 4. Create a Note (Use Your Token!)
```bash
curl -X POST http://localhost:8000/notes \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "My First Note",
    "content": "This is my note content!",
    "category": "people",
    "tags": ["test", "api"],
    "metadata": {}
  }'
```

### 5. List Notes
```bash
curl http://localhost:8000/notes \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### 6. Search Notes
```bash
curl "http://localhost:8000/search?q=first" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### 7. Chat with AI (Requires API Key)
```bash
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What notes do I have?"
  }'
```

### 8. Get Categories
```bash
curl http://localhost:8000/categories \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## Step 4: Test Using Python

```python
import requests

BASE_URL = "http://localhost:8000"

# 1. Create user
signup = requests.post(f"{BASE_URL}/auth/signup", json={
    "email": "test@example.com",
    "password": "testpass",
    "full_name": "Test User"
})
print("Signup:", signup.json())

# 2. Login
login = requests.post(f"{BASE_URL}/auth/login", json={
    "email": "test@example.com",
    "password": "testpass"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# 3. Create note
note = requests.post(f"{BASE_URL}/notes", headers=headers, json={
    "title": "Python Test Note",
    "content": "Created from Python!",
    "category": "procedures",
    "tags": ["python"],
    "metadata": {}
})
print("Note created:", note.json())

# 4. List notes
notes = requests.get(f"{BASE_URL}/notes", headers=headers)
print(f"Total notes: {len(notes.json())}")

# 5. Search
search = requests.get(f"{BASE_URL}/search?q=python", headers=headers)
print("Search results:", search.json())
```

## Common Issues

### "Connection refused"
- Server isn't running
- Wrong port (should be 8000)
- Solution: Start the server with the command in Step 1

### "Not authenticated" / 403 error
- Missing or invalid token
- Solution: Login again and use the new token

### "Incorrect email or password"
- User doesn't exist or wrong password
- Solution: Create user first with `/auth/signup`

### Chat returns "AI service is not configured"
- ANTHROPIC_API_KEY not set in .env.local
- Solution: Add your API key (optional, other features still work)

## Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_auth_api.py -v

# Run with coverage
python -m pytest tests/ --cov=src/api --cov-report=html
```

## Next Steps

1. Try the Swagger UI at http://localhost:8000/docs
2. Create a user and test all endpoints
3. Build a simple script to automate your workflows
4. Integrate with your own applications

Happy testing! 🚀
