import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pytest
from fastapi.testclient import TestClient
# from httpx import WSGITransport
from app.main import app

# transport = WSGITransport(app)
client = TestClient(app)

def test_token_creation():
    response = client.post("/token", data={"username": "admin@example.com", "password": "adminpassword"})
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_invalid_token_access():
    response = client.get("/users/me", headers={"Authorization": "Bearer invalid_token"})
    assert response.status_code == 401

def test_admin_access_to_user_list():
    # Log in as an admin to get the token
    response = client.post("/token", data={"username": "admin@example.com", "password": "adminpassword"})
    token = response.json()["access_token"]
    
    # Use token to access admin-protected route
    response = client.get("/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200  # Admin should access user list

def test_user_access_to_admin_route():
    # Log in as a regular user to get the token
    response = client.post("/token", data={"username": "user@example.com", "password": "userpassword"})
    token = response.json()["access_token"]
    
    # Try to access admin-protected route
    response = client.get("/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403  # User should not access user list
