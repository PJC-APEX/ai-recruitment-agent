# API Examples

Complete examples for using the Resume Screening System API.

## Base URL

```
http://localhost:8000/api
```

## Authentication

Currently no authentication required. For production, implement JWT or API keys.

---

## 1. Upload Resume

Upload a PDF resume and index it in the vector database.

### Request

```bash
curl -X POST "http://localhost:8000/api/upload-resume" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@John_Doe_Resume.pdf"
```

### Response (200 OK)

```json
{
  "success": true,
  "message": "Resume uploaded and indexed successfully",
  "file_name": "John_Doe_Resume.pdf",
  "chunks_created": 8,
  "metadata": {
    "candidate_name": "John Doe",
    "skills": [],
    "years_experience": null,
    "file_name": "John_Doe_Resume.pdf"
  }
}
```

### Python Example

```python
import requests

url = "http://localhost:8000/api/upload-resume"
files = {"file": open("John_Doe_Resume.pdf", "rb")}

response = requests.post(url, files=files)
print(response.json())
```

### JavaScript Example

```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);

const response = await fetch('http://localhost:8000/api/upload-resume', {
  method: 'POST',
  body: formData
});

const data = await response.json();
console.log(data);
```

---

## 2. Search Resumes

Search for candidates using natural language queries.

### Request

```bash
curl -X POST "http://localhost:8000/api/search-resumes" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Find candidates with 5 years of Python and FastAPI experience",
    "top_k": 5
  }'
```

### Response (200 OK)

```json
{
  "query": "Find candidates with 5 years of Python and FastAPI experience",
  "results": [
    {
      "candidate_name": "John Doe",
      "file_name": "John_Doe_Resume.pdf",
      "skills": ["Python", "FastAPI", "Docker"],
      "years_experience": 6,
      "relevance_score": 0.89,
      "resume_snippet": "Senior Python Developer with 6 years of experience..."
    },
    {
      "candidate_name": "Jane Smith",
      "file_name": "Jane_Smith_Resume.pdf",
      "skills": ["Python", "Django", "AWS"],
      "years_experience": 5,
      "relevance_score": 0.82,
      "resume_snippet": "Full-stack developer specializing in Python..."
    }
  ],
  "total_results": 2
}
```

### Python Example

```python
import requests

url = "http://localhost:8000/api/search-resumes"
payload = {
    "query": "Find senior .NET developers",
    "top_k": 3
}

response = requests.post(url, json=payload)
results = response.json()

for candidate in results["results"]:
    print(f"{candidate['candidate_name']}: {candidate['relevance_score']:.2%}")
```

### JavaScript Example

```javascript
const response = await fetch('http://localhost:8000/api/search-resumes', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    query: 'Find machine learning engineers',
    top_k: 5
  })
});

const data = await response.json();
console.log(`Found ${data.total_results} candidates`);
```

---

## 3. Score Resume

Score a resume against a job description.

### Request

```bash
curl -X POST "http://localhost:8000/api/score-resume" \
  -H "Content-Type: application/json" \
  -d '{
    "resume_text": "Senior Software Engineer with 8 years of experience in Python, FastAPI, and AWS. Strong background in building scalable microservices...",
    "job_description": "We are seeking a Senior Backend Engineer with 5+ years of Python experience. Must have expertise in FastAPI, microservices architecture, and cloud platforms (AWS/GCP)."
  }'
```

### Response (200 OK)

```json
{
  "score_result": {
    "match_score": 92,
    "matching_skills": [
      "Python",
      "FastAPI",
      "Microservices",
      "AWS",
      "Backend Development"
    ],
    "missing_skills": [
      "GCP"
    ],
    "experience_match": true,
    "summary": "Excellent match for the role. Candidate has 8 years of experience exceeding the 5+ year requirement. Strong alignment with all core technical skills including Python, FastAPI, and microservices. Only minor gap is GCP experience, but has equivalent AWS expertise."
  },
  "resume_file": null
}
```

### Python Example

```python
import requests

url = "http://localhost:8000/api/score-resume"

# Read resume text from file or variable
resume_text = "..."
job_description = """
Senior Full-Stack Developer
Required: React, Node.js, PostgreSQL, AWS
5+ years experience
"""

payload = {
    "resume_text": resume_text,
    "job_description": job_description
}

response = requests.post(url, json=payload)
score = response.json()["score_result"]

print(f"Match Score: {score['match_score']}/100")
print(f"Matching Skills: {', '.join(score['matching_skills'])}")
print(f"Missing Skills: {', '.join(score['missing_skills'])}")
```

---

## 4. Rank Candidates

Rank multiple candidates for a job position.

### Request

```bash
curl -X POST "http://localhost:8000/api/rank-candidates" \
  -H "Content-Type: application/json" \
  -d '{
    "job_description": "Senior Python Developer with 5+ years experience. Must have FastAPI, Docker, and AWS expertise.",
    "query": "Python FastAPI developers",
    "top_k": 5
  }'
```

### Response (200 OK)

```json
{
  "job_description": "Senior Python Developer with 5+ years experience...",
  "ranked_candidates": [
    {
      "rank": 1,
      "candidate_name": "John Doe",
      "file_name": "John_Doe_Resume.pdf",
      "match_score": 95,
      "matching_skills": ["Python", "FastAPI", "Docker", "AWS", "CI/CD"],
      "missing_skills": [],
      "summary": "Perfect match. 8 years Python experience with extensive FastAPI and AWS background. Strong Docker expertise."
    },
    {
      "rank": 2,
      "candidate_name": "Jane Smith",
      "file_name": "Jane_Smith_Resume.pdf",
      "match_score": 88,
      "matching_skills": ["Python", "Flask", "Docker", "AWS"],
      "missing_skills": ["FastAPI"],
      "summary": "Strong candidate. 6 years Python with Flask. Has AWS and Docker skills but lacks FastAPI experience."
    }
  ],
  "total_evaluated": 2
}
```

### Python Example

```python
import requests

url = "http://localhost:8000/api/rank-candidates"
payload = {
    "job_description": "Machine Learning Engineer with TensorFlow and PyTorch experience",
    "top_k": 10
}

response = requests.post(url, json=payload)
rankings = response.json()

print(f"Evaluated {rankings['total_evaluated']} candidates\n")

for candidate in rankings["ranked_candidates"][:3]:
    print(f"#{candidate['rank']} - {candidate['candidate_name']}")
    print(f"   Score: {candidate['match_score']}/100")
    print(f"   Summary: {candidate['summary']}\n")
```

---

## 5. Chat

Interactive chat interface for conversational queries.

### Request

```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Find me the best Python developers",
    "chat_history": []
  }'
```

### Response (200 OK)

```json
{
  "message": "Find me the best Python developers",
  "response": "I found 3 matching candidates:\n\n1. John Doe (John_Doe_Resume.pdf) - Relevance: 92%\n2. Jane Smith (Jane_Smith_Resume.pdf) - Relevance: 87%\n3. Bob Johnson (Bob_Johnson_Resume.pdf) - Relevance: 81%",
  "data": {
    "candidates": [
      {
        "candidate_name": "John Doe",
        "file_name": "John_Doe_Resume.pdf",
        "relevance_score": 0.92
      }
    ]
  }
}
```

### Python Example with Conversation History

```python
import requests

url = "http://localhost:8000/api/chat"
chat_history = []

def send_message(message):
    global chat_history
    
    payload = {
        "message": message,
        "chat_history": chat_history
    }
    
    response = requests.post(url, json=payload)
    data = response.json()
    
    # Update history
    chat_history.append({"role": "user", "content": message})
    chat_history.append({"role": "assistant", "content": data["response"]})
    
    return data

# Conversation
response1 = send_message("Find Python developers")
print(response1["response"])

response2 = send_message("Show me their experience levels")
print(response2["response"])
```

---

## 6. List Resumes

Get all uploaded resumes.

### Request

```bash
curl -X GET "http://localhost:8000/api/resumes/list"
```

### Response (200 OK)

```json
{
  "resumes": [
    {
      "file_name": "John_Doe_Resume.pdf",
      "candidate_name": "John Doe"
    },
    {
      "file_name": "Jane_Smith_Resume.pdf",
      "candidate_name": "Jane Smith"
    }
  ],
  "total_resumes": 2
}
```

---

## 7. Get Resume Count

Get total count of indexed documents.

### Request

```bash
curl -X GET "http://localhost:8000/api/resumes/count"
```

### Response (200 OK)

```json
{
  "total_documents": 47
}
```

---

## Error Responses

### 400 Bad Request

```json
{
  "detail": "Only PDF files are allowed"
}
```

### 500 Internal Server Error

```json
{
  "detail": "Failed to generate embeddings: OpenAI API error"
}
```

---

## Rate Limiting Considerations

OpenAI API has rate limits. For production:

- Implement request queuing
- Add caching for common queries
- Use batch processing for multiple resumes
- Monitor API usage

---

## Best Practices

1. **Resume Upload**: Name files as `Firstname_Lastname_Resume.pdf`
2. **Search Queries**: Be specific (e.g., "5 years Python" vs "Python dev")
3. **Scoring**: Provide detailed job descriptions for better results
4. **Ranking**: Use `top_k` to limit results and reduce API costs
5. **Error Handling**: Always check status codes and handle errors

---

## Testing with Postman

Import this collection to Postman:

1. Create new collection "Resume Screening API"
2. Add requests using examples above
3. Set environment variable: `base_url = http://localhost:8000/api`
4. Use `{{base_url}}/endpoint` in requests

---

For more examples, visit http://localhost:8000/docs for interactive API documentation.
