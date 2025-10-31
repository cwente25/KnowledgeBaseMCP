"""Pytest configuration and fixtures for API tests"""
import os
import tempfile
import shutil
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Set test environment variables before importing app
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["KNOWLEDGE_BASE_PATH"] = tempfile.mkdtemp()
os.environ["ANTHROPIC_API_KEY"] = ""  # Disable AI for tests
os.environ["DEBUG"] = "true"

from api.main import app
from api.database import Base, get_db
from api.models import User, Note
from api.auth import get_password_hash


# Create test database engine
@pytest.fixture(scope="function")
def test_db():
    """Create a fresh test database for each test"""
    # Create in-memory SQLite database
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False}
    )

    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Create session
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()

    yield db

    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(test_db):
    """Create a test client with test database"""

    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def test_user(test_db):
    """Create a test user in the database"""
    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("testpass"),
        full_name="Test User"
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def auth_headers(client, test_user):
    """Get authentication headers for test user"""
    response = client.post(
        "/auth/login",
        json={"email": "test@example.com", "password": "testpass"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_note(test_db, test_user):
    """Create a test note in the database"""
    note = Note(
        title="Test Note",
        content="This is a test note content",
        category="people",
        tags=["test", "sample"],
        note_metadata={"key": "value"},
        file_path="/tmp/test-note.md",
        user_id=test_user.id
    )
    test_db.add(note)
    test_db.commit()
    test_db.refresh(note)
    return note


@pytest.fixture(scope="session", autouse=True)
def cleanup():
    """Cleanup temp directories after all tests"""
    yield
    # Cleanup happens after all tests
    kb_path = os.environ.get("KNOWLEDGE_BASE_PATH")
    if kb_path and os.path.exists(kb_path):
        shutil.rmtree(kb_path, ignore_errors=True)
