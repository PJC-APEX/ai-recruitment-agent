# Resume Screening and Matching System

Production-ready AI-powered resume screening system using RAG (Retrieval Augmented Generation).

![System Architecture](https://img.shields.io/badge/Stack-FastAPI%20%2B%20React-blue)
![AI Powered](https://img.shields.io/badge/AI-OpenAI%20%2B%20LangChain-green)
![Database](https://img.shields.io/badge/Vector%20DB-ChromaDB-orange)

## 🎯 Overview

A full-stack application that enables recruiters to:

- **Upload** resumes (PDF) and automatically index them
- **Search** for candidates using natural language
- **Score** resumes against job descriptions
- **Rank** candidates based on relevance
- **Chat** with an AI assistant for conversational queries

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Frontend (React)                  │
│  Chat UI | Resume Upload | Candidate Display       │
└────────────────────┬────────────────────────────────┘
                     │ HTTP/REST
┌────────────────────▼────────────────────────────────┐
│              Backend (FastAPI)                      │
│  Routes | Services | RAG Pipeline | LLM Client     │
└────────────────────┬────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
┌───────▼──────┐ ┌──▼──────┐ ┌──▼─────────┐
│   OpenAI     │ │ ChromaDB │ │   PyPDF    │
│  Embeddings  │ │  Vector  │ │   Parser   │
│     LLM      │ │   Store  │ │            │
└──────────────┘ └──────────┘ └────────────┘
```

## 📁 Project Structure

```
resume-ai/
├── backend/                    # FastAPI Backend
│   ├── app/
│   │   ├── main.py            # Application entry point
│   │   ├── config.py          # Configuration
│   │   ├── dependencies.py    # Dependency injection
│   │   ├── api/               # API routes
│   │   │   ├── routes_resume.py
│   │   │   ├── routes_query.py
│   │   │   └── routes_scoring.py
│   │   ├── services/          # Business logic
│   │   │   ├── resume_parser.py
│   │   │   ├── chunking_service.py
│   │   │   ├── embedding_service.py
│   │   │   ├── vector_store_service.py
│   │   │   └── ranking_service.py
│   │   ├── llm/               # LLM integration
│   │   │   ├── llm_client.py
│   │   │   └── prompt_templates.py
│   │   ├── rag/               # RAG pipelines
│   │   │   ├── retrieval_pipeline.py
│   │   │   └── scoring_pipeline.py
│   │   ├── models/            # Pydantic models
│   │   │   ├── request_models.py
│   │   │   └── response_models.py
│   │   └── utils/
│   │       └── file_utils.py
│   ├── data/
│   │   └── resumes/           # Uploaded PDFs
│   ├── requirements.txt
│   ├── .env.example
│   └── README.md
│
└── frontend/                   # React Frontend
    ├── src/
    │   ├── components/        # React components
    │   │   ├── ChatBox.jsx
    │   │   ├── MessageBubble.jsx
    │   │   ├── ResumeUpload.jsx
    │   │   └── CandidateCard.jsx
    │   ├── pages/
    │   │   └── ChatPage.jsx
    │   ├── services/
    │   │   └── api.js         # API client
    │   ├── App.jsx
    │   ├── main.jsx
    │   └── index.css
    ├── package.json
    ├── vite.config.js
    ├── tailwind.config.js
    └── README.md
```

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Node.js 18+
- OpenAI API Key

### Backend Setup

```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Run server
python -m app.main
```

Backend will be available at: **http://localhost:8000**

API Docs: **http://localhost:8000/docs**

### Frontend Setup

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

Frontend will be available at: **http://localhost:5173**

## 🎨 Features

### 1. Resume Upload & Indexing

- Upload PDF resumes via drag-and-drop
- Automatic text extraction using PyPDF
- Text chunking (500 chars, 50 overlap)
- Embedding generation (OpenAI)
- Vector storage in ChromaDB

### 2. Semantic Search

Natural language queries like:

- "Find Python developers with 5+ years experience"
- "Who has machine learning and AWS skills?"
- "Search for senior full-stack engineers"

### 3. Resume Scoring

Score resumes against job descriptions with:

- **Match Score** (0-100)
- **Matching Skills**
- **Missing Skills**
- **Experience Match**
- **AI Summary**

### 4. Candidate Ranking

Rank multiple candidates for a position:

- Retrieve relevant candidates
- Score each against job description
- Return ranked list with analysis

### 5. Chat Interface

ChatGPT-style conversational UI:

- Natural language interaction
- Real-time candidate display
- Message history
- Inline candidate cards

## 🔧 Technology Stack

### Backend

| Technology | Purpose |
|------------|---------|
| **FastAPI** | Modern async web framework |
| **LangChain** | LLM orchestration |
| **OpenAI API** | Embeddings & LLM |
| **ChromaDB** | Vector database |
| **PyPDF** | PDF text extraction |
| **Pydantic** | Data validation |

### Frontend

| Technology | Purpose |
|------------|---------|
| **React 18** | UI framework |
| **Vite** | Build tool |
| **TailwindCSS** | Styling |
| **Axios** | HTTP client |
| **React Dropzone** | File upload |

## 📡 API Endpoints

### Resume Management

```
POST   /api/upload-resume      Upload resume PDF
GET    /api/resumes/count      Get resume count
GET    /api/resumes/list       List all resumes
```

### Search & Query

```
POST   /api/search-resumes     Search with natural language
POST   /api/rank-candidates    Rank candidates for job
POST   /api/chat              Chat interface
```

### Scoring

```
POST   /api/score-resume       Score resume vs job description
```

## 💡 Example Usage

### Search Request

```bash
curl -X POST http://localhost:8000/api/search-resumes \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Find senior Python developers with FastAPI experience",
    "top_k": 5
  }'
```

### Score Request

```bash
curl -X POST http://localhost:8000/api/score-resume \
  -H "Content-Type: application/json" \
  -d '{
    "resume_text": "...",
    "job_description": "We are looking for a senior Python developer..."
  }'
```

### Upload Request

```bash
curl -X POST http://localhost:8000/api/upload-resume \
  -F "file=@john_doe_resume.pdf"
```

## ⚙️ Configuration

### Backend (.env)

```env
OPENAI_API_KEY=your_key_here
CHUNK_SIZE=500
CHUNK_OVERLAP=50
TOP_K_RESULTS=5
CHROMA_PERSIST_DIRECTORY=./chroma_db
```

### Frontend (src/services/api.js)

```javascript
const API_BASE_URL = 'http://localhost:8000/api';
```

## 🧪 Testing

### Backend Tests

```bash
cd backend
pytest tests/
```

### Frontend Tests

```bash
cd frontend
npm test
```

## 🐳 Docker Deployment (Optional)

```bash
# Coming soon
docker-compose up -d
```

## 📈 Workflow

```
1. Upload Resume → Parse PDF → Extract Text
                              ↓
2. Chunk Text → Generate Embeddings → Store in ChromaDB
                                              ↓
3. User Query → Convert to Embedding → Search Vectors
                                              ↓
4. Retrieve Matches → Rank with LLM → Return Results
                                              ↓
5. Display in Chat UI ← Show Candidate Cards
```

## 🤝 Contributing

Contributions welcome! Please follow:

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push and create a Pull Request

## 📄 License

MIT License - see LICENSE file for details

## 🙋 Support

For issues or questions:

- Open an issue on GitHub
- Check API documentation at `/docs`

## 🔮 Future Enhancements

- [ ] Multi-language support
- [ ] Bulk resume upload
- [ ] Advanced filtering
- [ ] Resume comparison
- [ ] Export reports
- [ ] User authentication
- [ ] Role-based access
- [ ] Analytics dashboard

## 🏆 Credits

Built with ❤️ using FastAPI, React, OpenAI, and LangChain.

---

**Made for recruiters, powered by AI** 🚀
