"""Tests for authentication endpoints"""
import pytest


def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "0.2.0"
    assert data["database"] == "sqlite"


def test_signup_success(client):
    """Test successful user signup"""
    response = client.post(
        "/auth/signup",
        json={
            "email": "newuser@example.com",
            "password": "pass1234",
            "full_name": "New User"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["full_name"] == "New User"
    assert "id" in data
    assert "hashed_password" not in data  # Should not expose password


def test_signup_duplicate_email(client, test_user):
    """Test signup with duplicate email fails"""
    response = client.post(
        "/auth/signup",
        json={
            "email": test_user.email,
            "password": "password123",
            "full_name": "Duplicate User"
        }
    )
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"].lower()


def test_signup_invalid_email(client):
    """Test signup with invalid email fails"""
    response = client.post(
        "/auth/signup",
        json={
            "email": "not-an-email",
            "password": "password123",
            "full_name": "Test User"
        }
    )
    assert response.status_code == 422  # Validation error


def test_signup_short_password(client):
    """Test signup with too short password fails"""
    response = client.post(
        "/auth/signup",
        json={
            "email": "test@example.com",
            "password": "short",  # Less than 8 characters
            "full_name": "Test User"
        }
    )
    assert response.status_code == 422  # Validation error


def test_login_success(client, test_user):
    """Test successful login"""
    response = client.post(
        "/auth/login",
        json={
            "email": "test@example.com",
            "password": "testpass"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert len(data["access_token"]) > 0


def test_login_wrong_password(client, test_user):
    """Test login with wrong password fails"""
    response = client.post(
        "/auth/login",
        json={
            "email": "test@example.com",
            "password": "wrongpassword"
        }
    )
    assert response.status_code == 401
    assert "incorrect" in response.json()["detail"].lower()


def test_login_nonexistent_user(client):
    """Test login with non-existent user fails"""
    response = client.post(
        "/auth/login",
        json={
            "email": "nonexistent@example.com",
            "password": "password123"
        }
    )
    assert response.status_code == 401


def test_get_current_user(client, auth_headers):
    """Test getting current user info"""
    response = client.get("/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["full_name"] == "Test User"
    assert "id" in data


def test_get_current_user_no_token(client):
    """Test getting current user without token fails"""
    response = client.get("/auth/me")
    assert response.status_code == 403  # No credentials provided


def test_get_current_user_invalid_token(client):
    """Test getting current user with invalid token fails"""
    response = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalid-token"}
    )
    assert response.status_code == 401


def test_logout(client, auth_headers):
    """Test logout endpoint"""
    response = client.post("/auth/logout", headers=auth_headers)
    assert response.status_code == 200
    assert "message" in response.json()
