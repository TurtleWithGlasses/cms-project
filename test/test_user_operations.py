import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# Test user creation
def test_create_user():
    response = client.post("/api/v1/users/register", json={
        "email": "newuser@example.com",
        "username": "newuser",
        "password": "newuserpassword"
    })
    assert response.status_code == 201
    assert response.json()["email"] == "newuser@example.com"
    assert response.json()["username"] == "newuser"

# Test retrieving a user profile with token
def test_retrieve_user_profile():
    # Log in as the created user to get the token
    login_response = client.post("/auth/token", data={"username": "newuser@example.com", "password": "newuserpassword"})
    token = login_response.json()["access_token"]

    # Retrieve profile with token
    profile_response = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert profile_response.status_code == 200
    assert profile_response.json()["username"] == "newuser"

# Test user update
def test_update_user_profile():
    # Log in as the user to get the token
    login_response = client.post("/auth/token", data={"username": "newuser@example.com", "password": "newuserpassword"})
    token = login_response.json()["access_token"]

    # Update user profile
    update_response = client.patch("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"}, json={
        "email": "updateduser@example.com"
    })
    assert update_response.status_code == 200
    assert update_response.json()["email"] == "updateduser@example.com"

# Test user deletion by an admin
def test_delete_user_by_admin():
    # Log in as admin to get the token
    login_response = client.post("/auth/token", data={"username": "admin@example.com", "password": "adminpassword"})
    admin_token = login_response.json()["access_token"]

    # Delete the created user
    delete_response = client.delete("/api/v1/users/2", headers={"Authorization": f"Bearer {admin_token}"})
    assert delete_response.status_code == 204
