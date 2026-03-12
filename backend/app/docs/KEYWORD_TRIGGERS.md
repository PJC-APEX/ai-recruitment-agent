# Chat Keyword Triggers - Resume Builder System

## Overview

The `/chat` endpoint automatically detects what action to perform based on keywords in the user's message.

---

## Keyword Detection Logic

```python
# Priority Order (highest to lowest):
1. RANK keywords + job-related words
2. SCORE keywords
3. SEARCH keywords
4. GENERAL conversation (default)
```

---

## Action 1: SEARCH RESUMES 🔍

### Keywords Detected:
```
"find"
"search"
"looking for"
"candidates"
"with"
"experience in"
"show me"
"get me"
```

### Example Queries:
```
✅ "Find Python developers"
✅ "Search for .NET candidates with 5 years experience"
✅ "Looking for senior engineers"
✅ "Show me candidates with React skills"
✅ "Get me Java developers"
✅ "I need someone with AWS experience"
```

### What Happens:
```
User: "Find Python developers"
   ↓
Keyword "find" detected → SEARCH action
   ↓
Internal call: retrieval_pipeline.search_resumes()
   ↓
1. Convert query to embedding (Azure OpenAI)
2. Search ChromaDB for similar vectors
3. Return top 5 matching candidates
   ↓
Response: List of candidates with:
   • Name and filename
   • Relevance score
   • Years of experience
   • Key skills
   ↓
Frontend displays candidates in right panel
```

### Response Example:
```
I found 3 matching candidates:

1. John Doe (john_doe_resume.pdf)
   • Relevance: 95%
   • Experience: 5 years
   • Key Skills: Python, FastAPI, Django, PostgreSQL, Docker

2. Jane Smith (jane_smith_resume.pdf)
   • Relevance: 88%
   • Experience: 6 years
   • Key Skills: Python, Flask, AWS, MongoDB, React

3. Bob Wilson (bob_wilson_resume.pdf)
   • Relevance: 82%
   • Experience: 4 years
   • Key Skills: Python, Django, Redis, Celery, Docker
```

---

## Action 2: SCORE RESUME ⭐

### Keywords Detected:
```
"score"
"rate"
"evaluate"
"assess"
"how good"
"match"
```

### Example Queries:
```
✅ "Score this resume"
✅ "Rate the first candidate"
✅ "Evaluate John Doe's resume"
✅ "Assess how good this match is"
✅ "How does this candidate match the job?"
```

### What Happens:
```
User: "Score this resume against Senior Python Developer role"
   ↓
Keyword "score" detected → SCORE action
   ↓
GPT-4 uses conversation history to understand context
   ↓
Response: GPT-4 provides scoring with tips
   ↓
💡 Tip shown: "Provide resume text and job description 
              for detailed scoring via the score-resume API"
```

### Direct API Call (More Detailed):
```javascript
// For detailed scoring, frontend calls:
await scoreResume(resumeText, jobDescription)

Backend does:
1. Send both resume and job description to GPT-4
2. GPT-4 analyzes and returns:
   {
     "score": 95,
     "matching_skills": ["Python", "FastAPI", "Docker"],
     "missing_skills": ["Kubernetes"],
     "summary": "Excellent candidate with strong match...",
     "recommendation": "Highly recommend for interview"
   }
```

---

## Action 3: RANK CANDIDATES 🏆

### Keywords Detected:
```
"rank"
"compare"
"best"
"top"
"order"
"sort"
```

**PLUS job-related keywords:**
```
"job"
"position"
"role"
```

### Example Queries:
```
✅ "Rank candidates for this job"
✅ "Compare these candidates for the Python role"
✅ "Who is the best match for this position?"
✅ "Order candidates by how well they fit the role"
✅ "Show me top candidates for Senior Developer job"
```

### What Happens:
```
User: "Rank candidates for Senior Python Developer job"
   ↓
Keywords "rank" + "job" detected → RANK action
   ↓
GPT-4 uses conversation history to understand context
   ↓
Response: GPT-4 provides ranking guidance with tips
   ↓
💡 Tip shown: "Use the rank-candidates API with a job
              description for detailed scoring"
```

### Direct API Call (Most Comprehensive):
```javascript
// For detailed ranking, frontend calls:
await rankCandidates(jobDescription, "Python developers", 10)

Backend does:
1. Search ChromaDB → Find top 10 matching candidates
2. For EACH candidate:
   - Call GPT-4 → Score against job description
   - Get detailed analysis
3. Sort by score (highest to lowest)
4. Return ranked list

Result:
[
  {candidate: "John Doe", score: 95, analysis: "..."},
  {candidate: "Jane Smith", score: 88, analysis: "..."},
  {candidate: "Bob Wilson", score: 82, analysis: "..."}
]
```

---

## Action 4: GENERAL CONVERSATION 💬

### When Triggered:
- No keywords detected
- General questions
- Follow-up questions

### Example Queries:
```
✅ "What can you do?"
✅ "How does this system work?"
✅ "Thank you!"
✅ "Can you help me find developers?"
✅ "What skills should I look for?"
```

### What Happens:
```
User: "How does resume scoring work?"
   ↓
No action keywords detected → GENERAL CONVERSATION
   ↓
GPT-4 called with conversation history
   ↓
Response: Contextual answer based on conversation
```

---

## Priority Order Explained

```
┌─────────────────────────────────────────────────────────┐
│  User Message: "Rank candidates for Python job"         │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │ Check RANK keywords?  │
         │ + job keywords?       │
         └───────┬───────────────┘
                 │ YES → "rank" + "job" found
                 ▼
         ┌───────────────────────┐
         │ Execute RANK action   │
         └───────────────────────┘


┌─────────────────────────────────────────────────────────┐
│  User Message: "Score this resume"                       │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │ Check RANK keywords?  │
         └───────┬───────────────┘
                 │ NO
                 ▼
         ┌───────────────────────┐
         │ Check SCORE keywords? │
         └───────┬───────────────┘
                 │ YES → "score" found
                 ▼
         ┌───────────────────────┐
         │ Execute SCORE action  │
         └───────────────────────┘


┌─────────────────────────────────────────────────────────┐
│  User Message: "Find Python developers"                 │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │ Check RANK keywords?  │
         └───────┬───────────────┘
                 │ NO
                 ▼
         ┌───────────────────────┐
         │ Check SCORE keywords? │
         └───────┬───────────────┘
                 │ NO
                 ▼
         ┌───────────────────────┐
         │ Check SEARCH keywords?│
         └───────┬───────────────┘
                 │ YES → "find" found
                 ▼
         ┌───────────────────────┐
         │ Execute SEARCH action │
         └───────────────────────┘


┌─────────────────────────────────────────────────────────┐
│  User Message: "How does this work?"                    │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │ Check RANK keywords?  │
         └───────┬───────────────┘
                 │ NO
                 ▼
         ┌───────────────────────┐
         │ Check SCORE keywords? │
         └───────┬───────────────┘
                 │ NO
                 ▼
         ┌───────────────────────┐
         │ Check SEARCH keywords?│
         └───────┬───────────────┘
                 │ NO
                 ▼
         ┌───────────────────────┐
         │ GENERAL conversation  │
         └───────────────────────┘
```

---

## Complete Keyword Reference

### Search Keywords:
```
find          → "Find Python developers"
search        → "Search for candidates"
looking for   → "Looking for engineers"
candidates    → "I need candidates with React"
with          → "Developers with 5 years experience"
experience in → "Someone with experience in AWS"
show me       → "Show me .NET developers"
get me        → "Get me Java candidates"
```

### Score Keywords:
```
score      → "Score this resume"
rate       → "Rate John Doe's profile"
evaluate   → "Evaluate this candidate"
assess     → "Assess how good this match is"
how good   → "How good is this candidate?"
match      → "Does this resume match the job?"
```

### Rank Keywords (requires "job" words too):
```
rank     + job/position/role → "Rank candidates for this job"
compare  + job/position/role → "Compare candidates for the role"
best     + job/position/role → "Best match for this position"
top      + job/position/role → "Top candidates for the job"
order    + job/position/role → "Order candidates for this role"
sort     + job/position/role → "Sort by fit for this position"
```

---

## Special Cases

### Case 1: Multiple Keywords
```
Query: "Find and score Python developers"

Result: SEARCH wins (higher priority than SCORE in else-if chain)
```

### Case 2: Context from History
```
User: "Find Python developers"
AI: [Returns 3 candidates]

User: "Score the first one"

Result: SCORE action uses conversation history to know 
        "first one" = John Doe from previous search
```

### Case 3: Ambiguous Query
```
Query: "Python developers"

Result: No keywords → GENERAL conversation
GPT-4 will ask: "Are you looking to search for Python developers, 
                 or would you like me to help you with something else?"
```

---

## Adding New Keywords

To add new keywords, edit `routes_query.py`:

```python
# Add to appropriate list:
search_keywords = ["find", "search", ..., "YOUR_NEW_KEYWORD"]
score_keywords = ["score", "rate", ..., "YOUR_NEW_KEYWORD"]
rank_keywords = ["rank", "compare", ..., "YOUR_NEW_KEYWORD"]
```

---

## Testing Keywords

### Test Search:
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Find Python developers", "chat_history": []}'
```

### Test Score:
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Score this resume against Python role", "chat_history": []}'
```

### Test Rank:
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Rank candidates for Python job", "chat_history": []}'
```

---

## Summary

```
┌──────────────────────────────────────────────────────────────┐
│                    Keyword Trigger Summary                    │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  🔍 SEARCH (Most Common)                                      │
│     Keywords: find, search, looking for, show me, get me      │
│     Action: Vector search in ChromaDB                         │
│     Returns: List of matching candidates                      │
│                                                               │
│  ⭐ SCORE (Detailed Analysis)                                 │
│     Keywords: score, rate, evaluate, assess, match            │
│     Action: GPT-4 conversation with tips                      │
│     Returns: Contextual response + API tip                    │
│                                                               │
│  🏆 RANK (Batch Scoring)                                      │
│     Keywords: rank, compare, best, top + job/role/position    │
│     Action: GPT-4 conversation with tips                      │
│     Returns: Contextual response + API tip                    │
│                                                               │
│  💬 GENERAL (Default)                                         │
│     Keywords: None (fallback)                                 │
│     Action: GPT-4 conversation                                │
│     Returns: Contextual answer                                │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

**Key Insight**: Only SEARCH is fully automated. SCORE and RANK currently provide guidance and require direct API calls for detailed analysis. This can be enhanced to automatically extract context and call the appropriate APIs!
