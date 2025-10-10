import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_create_content():
    response = client.post("/content", json={
        "title": "Sample Title",
        "body": "Sample body of the content.",
        "status": "draft"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Sample Title"
    assert data["status"] == "draft"
