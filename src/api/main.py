"""FastAPI application entry point"""
import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse

from .config import settings
from .database import init_db
from .routers import auth, notes, search, chat, categories
from .schemas import HealthCheck

# Initialize FastAPI app
app = FastAPI(
    title="Knowledge Base API",
    description="HTTP API for personal knowledge base with AI assistance",
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
if settings.require_auth:
    app.include_router(auth.router)
app.include_router(notes.router)
app.include_router(search.router)
app.include_router(chat.router)
app.include_router(categories.router)

# Mount static files if web directory exists
web_dir = Path(__file__).parent.parent.parent / "web"
if web_dir.exists():
    app.mount("/static", StaticFiles(directory=str(web_dir / "static")), name="static")


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    init_db()
    print(f"✓ Database initialized")
    print(f"✓ Knowledge base path: {settings.knowledge_base_path}")
    print(f"✓ Categories: {', '.join(settings.categories_list)}")
    print(f"✓ AI enabled: {bool(settings.anthropic_api_key)}")
    print(f"✓ Authentication: {'enabled' if settings.require_auth else 'disabled'}")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint - serve web UI or API info"""
    # Check if web UI exists
    web_index = Path(__file__).parent.parent.parent / "web" / "index.html"

    if web_index.exists():
        return FileResponse(web_index)

    # Build getting started steps based on auth status
    auth_steps = ""
    if settings.require_auth:
        auth_steps = """
                <li>Create an account: POST /auth/signup</li>
                <li>Login: POST /auth/login</li>
                <li>Use the returned token in Authorization header: Bearer &lt;token&gt;</li>
"""

    auth_status = "enabled" if settings.require_auth else "disabled"

    # Otherwise return API info
    return f"""
    <html>
        <head>
            <title>Knowledge Base API</title>
            <style>
                body {{ font-family: sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }}
                h1 {{ color: #333; }}
                a {{ color: #0066cc; text-decoration: none; }}
                a:hover {{ text-decoration: underline; }}
                .info {{ background: #f5f5f5; padding: 20px; border-radius: 5px; margin: 20px 0; }}
                .status {{ background: #e3f2fd; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #2196F3; }}
            </style>
        </head>
        <body>
            <h1>Knowledge Base API</h1>
            <div class="info">
                <p>Welcome to the Knowledge Base API!</p>
                <p>This API provides access to your personal knowledge base with AI assistance.</p>
            </div>
            <div class="status">
                <p><strong>Status:</strong> Authentication is currently <strong>{auth_status}</strong></p>
            </div>
            <h2>Quick Links</h2>
            <ul>
                <li><a href="/docs">API Documentation (Swagger UI)</a></li>
                <li><a href="/redoc">API Documentation (ReDoc)</a></li>
                <li><a href="/health">Health Check</a></li>
            </ul>
            <h2>Getting Started</h2>
            <ol>{auth_steps}
                <li>Start creating notes: POST /notes</li>
                <li>Chat with AI: POST /chat</li>
            </ol>
        </body>
    </html>
    """


@app.get("/health", response_model=HealthCheck)
async def health_check():
    """Health check endpoint"""
    return HealthCheck(
        status="healthy",
        version="0.2.0",
        database=settings.database_url.split("://")[0],  # sqlite or postgresql
        mcp_enabled=settings.mcp_enable_http
    )


def run():
    """Run the API server (used by CLI command)"""
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )


if __name__ == "__main__":
    run()
