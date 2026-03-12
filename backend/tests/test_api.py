"""Tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient


def test_root_endpoint(client):
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_search_resumes_empty_query(client):
    """Test search with empty query."""
    response = client.post(
        "/api/search-resumes",
        json={"query": "", "top_k": 5}
    )
    # Should handle empty query gracefully
    assert response.status_code in [200, 400]


def test_score_resume_missing_data(client):
    """Test scoring with missing data."""
    response = client.post(
        "/api/score-resume",
        json={"resume_text": "short"}
    )
    assert response.status_code == 422  # Validation error


# Add more integration tests as needed
