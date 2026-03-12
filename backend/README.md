# Resume Screening and Matching System - Backend

Production-ready AI-powered resume screening system using RAG (Retrieval Augmented Generation).

## Features

- **Resume Upload**: Upload and parse PDF resumes
- **Vector Search**: Semantic search using ChromaDB
- **Resume Scoring**: Score resumes against job descriptions
- **Candidate Ranking**: Rank candidates using LLM
- **Chat Interface**: Natural language query support

## Tech Stack

- **FastAPI**: Modern async web framework
- **LangChain**: LLM orchestration
- **OpenAI**: Embeddings and LLM
- **ChromaDB**: Vector database
- **PyPDF**: PDF parsing
- **Pydantic**: Data validation

## Setup

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and add your OpenAI API key:

```bash
cp .env.example .env
```

Edit `.env`:
```
OPENAI_API_KEY=your_openai_api_key_here
```

### 3. Run the Server

```bash
python -m app.main
```

Or with uvicorn:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at: http://localhost:8000

API Documentation: http://localhost:8000/docs

## API Endpoints

### Resume Management

- `POST /api/upload-resume` - Upload a resume PDF
- `GET /api/resumes/count` - Get total resume count
- `GET /api/resumes/list` - List all resumes

### Search & Query

- `POST /api/search-resumes` - Search resumes with natural language
- `POST /api/rank-candidates` - Rank candidates for a job
- `POST /api/chat` - Chat interface for queries

### Scoring

- `POST /api/score-resume` - Score a resume against job description

## Project Structure

```
backend/
├── app/
│   ├── main.py                 # FastAPI app entry point
│   ├── config.py              # Configuration management
│   ├── dependencies.py        # Dependency injection
│   ├── api/
│   │   ├── routes_resume.py   # Resume upload routes
│   │   ├── routes_query.py    # Search and query routes
│   │   └── routes_scoring.py  # Scoring routes
│   ├── services/
│   │   ├── resume_parser.py   # PDF parsing
│   │   ├── chunking_service.py # Text chunking
│   │   ├── embedding_service.py # Embeddings
│   │   ├── vector_store_service.py # ChromaDB
│   │   └── ranking_service.py  # Candidate ranking
│   ├── llm/
│   │   ├── llm_client.py      # OpenAI client
│   │   └── prompt_templates.py # Prompt templates
│   ├── rag/
│   │   ├── retrieval_pipeline.py # RAG retrieval
│   │   └── scoring_pipeline.py   # RAG scoring
│   ├── models/
│   │   ├── request_models.py  # Request schemas
│   │   └── response_models.py # Response schemas
│   └── utils/
│       └── file_utils.py      # File utilities
├── data/
│   └── resumes/               # Uploaded resumes
├── chroma_db/                 # ChromaDB persistence
├── requirements.txt
└── .env.example
```

## Example Usage

### Upload a Resume

```bash
curl -X POST "http://localhost:8000/api/upload-resume" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@resume.pdf"
```

### Search Resumes

```bash
curl -X POST "http://localhost:8000/api/search-resumes" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Find candidates with 5 years experience in Python and FastAPI",
    "top_k": 5
  }'
```

### Score a Resume

```bash
curl -X POST "http://localhost:8000/api/score-resume" \
  -H "Content-Type: application/json" \
  -d '{
    "resume_text": "...",
    "job_description": "..."
  }'
```

## Development

### Running Tests

```bash
pytest tests/
```

### Code Quality

```bash
# Format code
black app/

# Check types
mypy app/

# Lint
flake8 app/
```

## Configuration

Edit `.env` or environment variables:

```
OPENAI_API_KEY=your_key
CHUNK_SIZE=500
CHUNK_OVERLAP=50
TOP_K_RESULTS=5
CHROMA_PERSIST_DIRECTORY=./chroma_db
```

## License

MIT
