# ChromaDB Data Structure in Resume Screening System

## Overview
ChromaDB stores resume data in a collection called "resumes". Each document chunk is stored with 4 key components.

---

## Data Structure

```
┌─────────────────────────────────────────────────────────────────┐
│                       ChromaDB Collection                        │
│                         "resumes"                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Contains multiple documents
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Document (Chunk)                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1️⃣  ID (string)                                                 │
│     ├─ Format: {filename}_{uuid}_{chunk_index}                  │
│     └─ Example: "john_doe.pdf_a1b2c3d4_0"                       │
│                                                                  │
│  2️⃣  Document (string) - The actual text content                │
│     └─ Example: "John Doe is a senior software engineer..."     │
│                                                                  │
│  3️⃣  Metadata (dictionary) - Structured information             │
│     ├─ file_name: "john_doe.pdf"                                │
│     ├─ candidate_name: "John Doe"                               │
│     ├─ chunk_index: 0                                           │
│     ├─ total_chunks: 3                                          │
│     ├─ skills: ["Python", "FastAPI", "SQL", "Docker"]          │
│     └─ years_experience: 5                                      │
│                                                                  │
│  4️⃣  Embedding (vector) - Numerical representation              │
│     ├─ Dimensions: 1536 (for text-embedding-3-small)           │
│     ├─ Type: List of floats                                    │
│     ├─ Example: [0.023, -0.145, 0.567, ..., -0.234]           │
│     └─ Used for: Semantic similarity search                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Example: Actual Data Flow

### When You Upload "john_doe_resume.pdf":

```python
# 1. PDF is parsed → raw text extracted
resume_text = """
John Doe
Senior Software Engineer
Email: john@example.com

SKILLS
Python, FastAPI, Django, PostgreSQL, Docker, Kubernetes

EXPERIENCE
Senior Developer at TechCorp (2019-2024) - 5 years
- Built REST APIs using FastAPI
- Optimized database queries
...
"""

# 2. LLM extracts metadata
extracted_metadata = {
    "skills": ["Python", "FastAPI", "Django", "PostgreSQL", "Docker", "Kubernetes"],
    "years_experience": 5
}

# 3. Text is chunked (split into smaller pieces)
chunks = [
    "John Doe\nSenior Software Engineer\nEmail: john@example.com\nSKILLS...",
    "EXPERIENCE\nSenior Developer at TechCorp (2019-2024)...",
    "...rest of the text"
]

# 4. Each chunk is converted to embedding vector
chunk_1_embedding = [0.023, -0.145, 0.567, ..., -0.234]  # 1536 numbers

# 5. Stored in ChromaDB
{
    "id": "john_doe_resume.pdf_a1b2c3d4_0",
    "document": "John Doe\nSenior Software Engineer...",
    "metadata": {
        "file_name": "john_doe_resume.pdf",
        "candidate_name": "John Doe",
        "chunk_index": 0,
        "total_chunks": 3,
        "skills": ["Python", "FastAPI", "Django", "PostgreSQL", "Docker", "Kubernetes"],
        "years_experience": 5
    },
    "embedding": [0.023, -0.145, 0.567, ..., -0.234]  # 1536 dimensions
}
```

---

## How Search Works

```
User Query: "Find Python developers with 5+ years experience"
                              │
                              ▼
                    Convert to embedding
                    [0.045, -0.234, ...]
                              │
                              ▼
              ChromaDB calculates similarity
              (cosine distance between vectors)
                              │
                              ▼
              Returns closest matching chunks
                              │
                              ▼
    ┌────────────────────┬────────────────────┬────────────────────┐
    │   Match #1         │   Match #2         │   Match #3         │
    │   Score: 95%       │   Score: 88%       │   Score: 82%       │
    │   John Doe         │   Jane Smith       │   Bob Wilson       │
    │   Skills: Python.. │   Skills: Python.. │   Skills: Java...  │
    │   5 years exp      │   7 years exp      │   4 years exp      │
    └────────────────────┴────────────────────┴────────────────────┘
```

---

## Key Benefits of This Structure

### 1. **Semantic Search**
   - Not just keyword matching
   - Understands meaning and context
   - "Python expert" matches "Python developer", "Pythonist", etc.

### 2. **Efficient Retrieval**
   - Vector similarity is very fast
   - Can search thousands of resumes in milliseconds
   - No need to scan all text

### 3. **Rich Metadata**
   - Skills and experience pre-extracted
   - Can filter by metadata before searching
   - Example: "Show only candidates with 5+ years experience"

### 4. **Chunking Benefits**
   - Large resumes split into manageable pieces
   - Better embedding quality (each chunk is focused)
   - Can return specific relevant sections

---

## Storage Location

```
ResumeBuilder/
└── backend/
    └── data/
        └── chroma_db/          ← ChromaDB persists here
            ├── chroma.sqlite3  ← Main database
            └── [vector files]  ← Binary vector data
```

---

## Metadata Fields Explained

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `file_name` | string | Original PDF filename | "john_doe_resume.pdf" |
| `candidate_name` | string | Extracted from filename | "John Doe" |
| `chunk_index` | int | Position of this chunk | 0, 1, 2... |
| `total_chunks` | int | Total chunks for this resume | 3 |
| `skills` | list[string] | LLM-extracted skills | ["Python", "FastAPI"] |
| `years_experience` | int | LLM-extracted experience | 5 |

---

## Embedding Details

- **Model**: Azure OpenAI `text-embedding-3-small`
- **Dimensions**: 1536 (1,536 numbers per chunk)
- **Range**: Each number is between -1.0 and 1.0
- **Purpose**: Captures semantic meaning of text
- **Comparison Method**: Cosine similarity
  - 0.0 = completely different
  - 1.0 = identical meaning

---

## To View Actual Data

1. **Upload a resume** via the API or frontend
2. **Run the inspection script**:
   ```bash
   cd backend
   python inspect_chromadb.py
   ```
3. **Or query via API**:
   ```bash
   curl http://localhost:8000/api/resumes/list
   ```
