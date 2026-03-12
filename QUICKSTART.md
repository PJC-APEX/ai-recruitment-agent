# Quick Start Guide

Get the Resume Screening System running in 5 minutes.

## Prerequisites

- Python 3.9+ installed
- Node.js 18+ installed
- OpenAI API key ([Get one here](https://platform.openai.com/api-keys))

## Step 1: Clone or Download

```bash
cd ResumeBuilder
```

## Step 2: Backend Setup

### Install Python Dependencies

```bash
cd backend
python -m venv venv

# On Windows
venv\Scripts\activate

# On Mac/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### Configure OpenAI API Key

```bash
# Copy the example env file
copy .env.example .env

# Edit .env and add your OpenAI API key
```

Edit `.env`:
```
OPENAI_API_KEY=sk-your-actual-api-key-here
```

### Start Backend Server

```bash
python -m app.main
```

✅ Backend running at: http://localhost:8000

✅ API Docs at: http://localhost:8000/docs

## Step 3: Frontend Setup

Open a **new terminal** window:

```bash
cd frontend
npm install
npm run dev
```

✅ Frontend running at: http://localhost:5173

## Step 4: Test the System

### Open the App

Navigate to: http://localhost:5173

### Upload a Resume

1. Click **"Upload Resume"** button
2. Drag and drop a PDF resume or click to browse
3. Wait for confirmation

### Search for Candidates

Type in the chat input:

```
Find candidates with Python experience
```

Press Enter and see results!

## Common Issues

### Backend won't start

**Error**: `ModuleNotFoundError: No module named 'fastapi'`

**Solution**: Make sure virtual environment is activated and dependencies installed:
```bash
pip install -r requirements.txt
```

### Frontend won't start

**Error**: `Cannot find module`

**Solution**: Install dependencies:
```bash
npm install
```

### OpenAI API Error

**Error**: `AuthenticationError: Invalid API key`

**Solution**: Check your `.env` file has the correct API key:
```
OPENAI_API_KEY=sk-...
```

### ChromaDB Error

**Error**: `Failed to initialize ChromaDB`

**Solution**: Delete the chroma_db folder and restart:
```bash
rm -rf chroma_db/
```

## What's Next?

- Upload more resumes to build your database
- Try different search queries
- Use the scoring feature to match resumes to job descriptions
- Explore the API documentation at http://localhost:8000/docs

## Example Queries

Try these in the chat interface:

```
Find senior Python developers
Find candidates with 5+ years of experience
Who has React and TypeScript skills?
Search for full-stack developers
Find machine learning engineers
```

## Stop the Servers

**Backend**: Press `Ctrl+C` in the backend terminal

**Frontend**: Press `Ctrl+C` in the frontend terminal

## API Testing (Optional)

### Using curl

```bash
# Health check
curl http://localhost:8000/health

# Upload resume
curl -X POST http://localhost:8000/api/upload-resume \
  -F "file=@path/to/resume.pdf"

# Search resumes
curl -X POST http://localhost:8000/api/search-resumes \
  -H "Content-Type: application/json" \
  -d '{"query": "Find Python developers", "top_k": 5}'
```

### Using Browser

Visit http://localhost:8000/docs for interactive API documentation.

## Need Help?

- Check the [README.md](README.md) for detailed documentation
- Review API docs at http://localhost:8000/docs
- Check backend logs in the terminal
- Verify environment variables in `.env`

---

**Happy recruiting! 🚀**
