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
# Context safeguards (token estimates; no summarization LLM call)
CONTEXT_WINDOW_TOKENS=32768
CONTEXT_OUTPUT_RESERVE_TOKENS=2000
MAX_USER_MESSAGE_TOKENS=8000
SHORT_TERM_MAX_MESSAGES=20
INGESTION_QUEUE_ENABLED=true
REDIS_URL=redis://localhost:6379/0
INGESTION_WORKER_MAX_JOBS=4
INGESTION_EMBEDDING_CONCURRENCY=4
INGESTION_EMBEDDING_BATCH_SIZE=16
EMBEDDING_TIMEOUT_SECONDS=60
EMBEDDING_MAX_RETRIES=5
EMBEDDING_RETRY_MIN_SECONDS=1
EMBEDDING_RETRY_MAX_SECONDS=20
SYNC_THREAD_POOL_WORKERS=8
```

### Durable resume ingestion

When `INGESTION_QUEUE_ENABLED=true`, `POST /api/upload-resume` only streams
the file to `UPLOAD_DATA_DIRECTORY`, creates an idempotent job keyed by the
SHA-256 file hash, and returns `job_id` with status `queued`. Start the ARQ
worker from the `backend` directory:

```bash
python -m arq app.jobs.worker.WorkerSettings
```

Poll `GET /api/upload-jobs/{job_id}` for `queued`, `processing`, `indexed`, or
`failed`. The worker persists parsed text, metadata, chunks, and embeddings
before advancing stages. Chroma IDs use `{file_hash}:{chunk_index}` and are
upserted, so retries resume safely instead of duplicating vectors. API and
worker processes must share `UPLOAD_DATA_DIRECTORY`, `CHROMA_PERSIST_DIRECTORY`
and `INGESTION_ARTIFACT_DIRECTORY` (or replace local storage with S3/MinIO and
an external vector database in a multi-host deployment).

## License

MIT
