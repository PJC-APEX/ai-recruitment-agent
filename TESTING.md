# Testing Guide

## Running Tests

### Backend Tests

```bash
cd backend

# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_resume_parser.py

# Run with verbose output
pytest -v

# Run specific test
pytest tests/test_api.py::test_health_check
```

### Frontend Tests

```bash
cd frontend

# Install test dependencies
npm install --save-dev @testing-library/react @testing-library/jest-dom vitest

# Run tests (when configured)
npm test
```

## Test Structure

### Backend Tests

```
backend/tests/
├── conftest.py              # Test configuration and fixtures
├── test_api.py             # API endpoint tests
├── test_resume_parser.py   # Resume parser tests
├── test_chunking.py        # Chunking service tests
├── test_embedding.py       # Embedding service tests
└── test_vector_store.py    # Vector store tests
```

### Writing Tests

#### Unit Test Example

```python
import pytest
from app.services.resume_parser import ResumeParserService

@pytest.fixture
def parser():
    return ResumeParserService()

def test_extract_email(parser):
    text = "Contact: john@example.com"
    email = parser.extract_email(text)
    assert email == "john@example.com"
```

#### Async Test Example

```python
import pytest

@pytest.mark.asyncio
async def test_parse_pdf(parser):
    result = await parser.parse_pdf("test.pdf")
    assert result is not None
```

#### API Test Example

```python
def test_search_endpoint(client):
    response = client.post(
        "/api/search-resumes",
        json={"query": "Python developer", "top_k": 5}
    )
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
```

## Test Categories

### 1. Unit Tests

Test individual functions and methods:

- Resume parsing
- Text chunking
- Email/phone extraction
- File utilities

### 2. Integration Tests

Test component interactions:

- API endpoints
- Service layer integration
- Database operations

### 3. End-to-End Tests

Test complete workflows:

- Upload → Parse → Embed → Store
- Search → Retrieve → Rank
- Score resume flow

## Mocking External Services

### Mock OpenAI API

```python
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_embedding_service():
    with patch('openai.AsyncOpenAI') as mock_client:
        mock_client.embeddings.create = AsyncMock(
            return_value={"data": [{"embedding": [0.1] * 1536}]}
        )
        
        service = EmbeddingService(api_key="test")
        result = await service.embed_text("test")
        
        assert len(result) == 1536
```

### Mock ChromaDB

```python
@pytest.fixture
def mock_chroma():
    with patch('chromadb.Client') as mock:
        yield mock
```

## Test Data

Create test fixtures for common data:

### Sample Resume

```python
@pytest.fixture
def sample_resume():
    return {
        "text": "Senior Developer with 8 years...",
        "file_name": "test_resume.pdf",
        "candidate_name": "John Doe"
    }
```

### Sample Job Description

```python
@pytest.fixture
def sample_job():
    return "Senior Python Developer needed..."
```

## Coverage Goals

Aim for:

- **80%+** overall code coverage
- **90%+** for critical paths (scoring, ranking)
- **100%** for utility functions

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        cd backend
        pip install -r requirements.txt
        pip install pytest pytest-cov
    
    - name: Run tests
      run: |
        cd backend
        pytest --cov=app --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v2
```

## Best Practices

1. **Isolate Tests**: Each test should be independent
2. **Use Fixtures**: Reuse common setup code
3. **Mock External Services**: Don't hit real APIs in tests
4. **Test Edge Cases**: Empty inputs, errors, limits
5. **Keep Tests Fast**: Mock slow operations
6. **Descriptive Names**: `test_parse_pdf_with_invalid_file`
7. **Arrange-Act-Assert**: Clear test structure

## Debugging Tests

### Run with debugging

```bash
pytest --pdb  # Drop into debugger on failure
pytest -s     # Show print statements
pytest -v     # Verbose output
pytest -k "test_name"  # Run specific test by name
```

### VSCode Debugging

Add to `.vscode/launch.json`:

```json
{
  "name": "Python: Pytest",
  "type": "python",
  "request": "launch",
  "module": "pytest",
  "args": ["-v"],
  "cwd": "${workspaceFolder}/backend"
}
```

## Performance Testing

### Load Testing with Locust

```python
from locust import HttpUser, task

class ResumeUser(HttpUser):
    @task
    def search_resumes(self):
        self.client.post("/api/search-resumes", json={
            "query": "Python developer",
            "top_k": 5
        })
```

## Future Test Additions

- [ ] PDF parsing with various formats
- [ ] Large file upload tests
- [ ] Concurrent request handling
- [ ] Rate limiting tests
- [ ] Security tests (injection, XSS)
- [ ] Performance benchmarks
- [ ] Frontend component tests
- [ ] E2E browser tests with Playwright

---

**Remember**: Write tests as you develop, not after!
