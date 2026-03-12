"""Test configuration and fixtures."""

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_resume_text():
    """Sample resume text for testing."""
    return """
    John Doe
    Senior Software Engineer
    john.doe@example.com
    
    EXPERIENCE
    Senior Software Engineer at Tech Corp (2019-Present)
    - Developed microservices using Python and FastAPI
    - Implemented CI/CD pipelines with Docker and Kubernetes
    - Led team of 5 engineers
    
    SKILLS
    Python, FastAPI, Docker, Kubernetes, AWS, PostgreSQL
    
    EDUCATION
    BS Computer Science, University (2015)
    """


@pytest.fixture
def sample_job_description():
    """Sample job description for testing."""
    return """
    Senior Backend Engineer
    
    Requirements:
    - 5+ years of Python experience
    - Strong FastAPI and microservices knowledge
    - Experience with Docker and Kubernetes
    - AWS cloud platform experience
    - Team leadership experience preferred
    """
