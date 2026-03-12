# How to Enable Verbose Mode & View Agent Logs

## Quick Answer

**Verbose mode is ALREADY ENABLED by default!** 

The logs appear in the **terminal/console where you run the backend server**.

---

## How Verbose Mode Works

### Current Configuration

```python
# File: app/dependencies.py (line 120)

@lru_cache()
def get_recruitment_agent() -> RecruitmentAgent:
    settings = get_settings()
    
    return RecruitmentAgent(
        llm_client=llm_client,
        tools=tools,
        verbose=settings.debug  # ← Controlled by DEBUG setting
    )
```

```python
# File: app/config.py (line 17)

class Settings(BaseSettings):
    debug: bool = True  # ← Default is True (verbose enabled)
```

---

## Method 1: Using .env File (Recommended)

### Step 1: Create `.env` File

Create a file named `.env` in the `backend/` folder:

```bash
# Location: C:\Learning_Lab\ResumeBuilder\backend\.env

# Azure OpenAI Configuration (REQUIRED)
AZURE_OPENAI_ENDPOINT=your_endpoint_here
AZURE_OPENAI_API_KEY=your_api_key_here
AZURE_OPENAI_MODEL=gpt-4
AZURE_OPENAI_EMBEDDING_MODEL=text-embedding-ada-002
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# Verbose Mode Control
DEBUG=true  # ← Set to 'true' for verbose logs, 'false' to disable
```

### Step 2: Enable/Disable Verbose Mode

**To ENABLE verbose mode** (see all agent reasoning steps):
```env
DEBUG=true
```

**To DISABLE verbose mode** (minimal logging):
```env
DEBUG=false
```

### Step 3: Restart Backend Server

```powershell
# Stop current server (Ctrl+C)
# Then restart:
cd backend
.\start_server.ps1
```

---

## Method 2: Modify config.py Directly

If you don't want to use `.env` file:

```python
# File: app/config.py

class Settings(BaseSettings):
    debug: bool = True  # ← Change to False to disable verbose mode
```

Then restart the server.

---

## Where to See the Logs

### 1. Terminal Output (Main Location)

Logs appear in the **same terminal/PowerShell window** where you run `start_server.ps1`.

**Example Terminal Output with Verbose Mode:**

```powershell
PS C:\Learning_Lab\ResumeBuilder\backend> .\start_server.ps1

INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000

# ← User sends chat request: "How many Python developers?"

2026-03-10 10:30:15 - app.agents.recruitment_agent - INFO - Agent processing query: How many Python developers are there?

# ═══════════════════════════════════════════════════════════
# VERBOSE MODE OUTPUT STARTS HERE
# ═══════════════════════════════════════════════════════════

[chain/start] [1:chain:AgentExecutor] Entering Chain run with input:
{
  "input": "How many Python developers are there?"
}

[llm/start] [1:chain:AgentExecutor > 2:llm:ChatOpenAI] Entering LLM run with input:
{
  "messages": [
    System: You are an intelligent recruitment assistant...
    Human: How many Python developers are there?
  ]
}

[llm/end] [1:chain:AgentExecutor > 2:llm:ChatOpenAI] [2.5s] Exiting LLM run with output:
{
  "generations": [[
    {
      "message": {
        "function_call": {
          "name": "search_candidates",
          "arguments": "{\"query\": \"Python developers\"}"
        }
      }
    }
  ]]
}

[tool/start] [1:chain:AgentExecutor > 3:tool:search_candidates] Entering Tool run with input:
"Python developers"

2026-03-10 10:30:17 - app.agents.tools - INFO - 🔧 Tool executed: search_candidates(query='Python developers')

[tool/end] [1:chain:AgentExecutor > 3:tool:search_candidates] [1.2s] Exiting Tool run with output:
"Found 3 matching candidates:

1. John Doe (File: john_doe.pdf)
   Relevance Score: 95.3%
   Experience: 7 years
   Key Skills: Python, Django, PostgreSQL, AWS
   Snippet: Senior Python developer with extensive experience...

2. Jane Smith (File: jane_smith.pdf)
   Relevance Score: 89.1%
   Experience: 5 years
   Key Skills: Python, Flask, React, Docker
   Snippet: Full-stack developer specializing in Python...

3. Bob Wilson (File: bob_wilson.pdf)
   Relevance Score: 85.7%
   Experience: 6 years
   Key Skills: Python, FastAPI, MongoDB, Kubernetes
   Snippet: Backend engineer with strong Python skills..."

[llm/start] [1:chain:AgentExecutor > 4:llm:ChatOpenAI] Entering LLM run with input:
{
  "messages": [
    System: You are an intelligent recruitment assistant...
    Human: How many Python developers are there?
    AI: [function_call: search_candidates]
    Function: Found 3 matching candidates...
  ]
}

[llm/end] [1:chain:AgentExecutor > 4:llm:ChatOpenAI] [1.8s] Exiting LLM run with output:
{
  "generations": [[
    {
      "message": {
        "content": "I found 3 Python developers in the database. Here's a summary:\n\n1. **John Doe** (7 years experience) - 95.3% match..."
      }
    }
  ]]
}

[chain/end] [1:chain:AgentExecutor] [5.5s] Exiting Chain run with output:
{
  "output": "I found 3 Python developers in the database..."
}

# ═══════════════════════════════════════════════════════════
# VERBOSE MODE OUTPUT ENDS HERE
# ═══════════════════════════════════════════════════════════

2026-03-10 10:30:20 - app.agents.recruitment_agent - INFO - Agent completed successfully

INFO:     127.0.0.1:50234 - "POST /api/chat HTTP/1.1" 200 OK
```

### 2. What You See in Verbose Mode

The verbose output shows:

- **[chain/start]** - Agent executor starts
- **[llm/start]** - LLM is called (with full prompt)
- **[llm/end]** - LLM responds (shows function call decision)
- **[tool/start]** - Tool execution begins
- **[tool/end]** - Tool returns result
- **[llm/start]** (again) - LLM called with tool result
- **[llm/end]** (again) - LLM generates final answer
- **[chain/end]** - Agent executor completes

### 3. What You See WITHOUT Verbose Mode (DEBUG=false)

```powershell
2026-03-10 10:30:15 - app.agents.recruitment_agent - INFO - Agent processing query: How many Python developers are there?
2026-03-10 10:30:17 - app.agents.tools - INFO - 🔧 Tool executed: search_candidates(query='Python developers')
2026-03-10 10:30:20 - app.agents.recruitment_agent - INFO - Agent completed successfully
INFO:     127.0.0.1:50234 - "POST /api/chat HTTP/1.1" 200 OK
```

**Much shorter!** Only essential logs, no detailed agent reasoning.

---

## How to Test Verbose Mode

### 1. Start the Backend Server

```powershell
cd C:\Learning_Lab\ResumeBuilder\backend
.\start_server.ps1
```

**Watch the terminal output** - this is where all logs appear!

### 2. Send a Chat Request

**Option A: Using Frontend**
- Open the chat interface
- Type: "How many candidates are there?"
- Watch the backend terminal for verbose output

**Option B: Using API Directly**

```powershell
# In a NEW PowerShell window:
curl -X POST http://localhost:8000/api/chat `
  -H "Content-Type: application/json" `
  -d '{
    "message": "How many Python developers are there?",
    "chat_history": []
  }'
```

**Then check the original terminal** where backend is running for logs.

### 3. Observe the Output

With `DEBUG=true`, you'll see detailed agent reasoning showing:
- Which tool the LLM decided to call
- The arguments passed to the tool
- The tool's return value
- How the LLM used that result to generate the final answer

---

## Verbose Output Breakdown

### Example: Multi-Tool Call

**User Query:** "Find Python developers and show me John's resume"

```
[Iteration 1]
├─ LLM Decision: Call search_candidates
├─ Tool Execution: search_candidates("Python developers")
└─ Tool Result: "Found 3 candidates: John Doe, Jane Smith..."

[Iteration 2]
├─ LLM Sees: Previous tool result
├─ LLM Decision: Call get_candidate_details
├─ Tool Execution: get_candidate_details("john_doe.pdf")
└─ Tool Result: "JOHN DOE\nEmail: john@example.com..."

[Iteration 3]
├─ LLM Sees: Both tool results
├─ LLM Decision: FINISH (no more tools needed)
└─ Final Response: "I found 3 Python developers. Here's John's resume..."
```

---

## Logging Levels Explained

### Current Logging Configuration

```python
# File: app/main.py

logging.basicConfig(
    level=logging.INFO,  # ← Controls log verbosity
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
```

### Available Log Levels (from most to least verbose)

| Level | What You See |
|-------|-------------|
| `DEBUG` | Everything (very detailed, rarely needed) |
| `INFO` | Standard operational messages ✅ **Currently active** |
| `WARNING` | Warnings only (when something unexpected happens) |
| `ERROR` | Errors only (when something fails) |

### To Change Log Level

Edit [app/main.py](backend/app/main.py):

```python
# For MORE detail:
logging.basicConfig(level=logging.DEBUG)  # Shows everything

# For LESS detail:
logging.basicConfig(level=logging.WARNING)  # Only warnings and errors
```

---

## Environment Variable Options

### Complete .env Template

```env
# ============================================================
# Azure OpenAI Configuration (REQUIRED)
# ============================================================
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your_api_key_here
AZURE_OPENAI_MODEL=gpt-4
AZURE_OPENAI_EMBEDDING_MODEL=text-embedding-ada-002
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# ============================================================
# Agent Configuration
# ============================================================
DEBUG=true  # Show verbose agent reasoning (true/false)

# ============================================================
# Application Settings
# ============================================================
APP_NAME=Resume Screening System
APP_VERSION=1.0.0

# ============================================================
# Vector Database
# ============================================================
CHROMA_PERSIST_DIRECTORY=./chroma_db

# ============================================================
# File Upload
# ============================================================
MAX_UPLOAD_SIZE=10485760  # 10MB
ALLOWED_EXTENSIONS=pdf

# ============================================================
# Chunking Configuration
# ============================================================
CHUNK_SIZE=500
CHUNK_OVERLAP=50

# ============================================================
# Retrieval Configuration
# ============================================================
TOP_K_RESULTS=5
```

---

## Troubleshooting

### Issue 1: Not Seeing Verbose Output

**Symptom:** Backend runs but no detailed logs appear

**Solution:**
1. Check `.env` file: `DEBUG=true` (not "True" or "TRUE")
2. Restart backend server after changing .env
3. Make sure you're watching the correct terminal window

### Issue 2: Too Much Output (Hard to Read)

**Solution:**
```env
DEBUG=false  # Disable verbose mode
```

Or increase logging level:
```python
# app/main.py
logging.basicConfig(level=logging.WARNING)
```

### Issue 3: Want to Save Logs to File

**Solution:** Redirect output when starting server

```powershell
# Save logs to file
.\start_server.ps1 *> logs.txt

# View logs in real-time while saving
.\start_server.ps1 | Tee-Object -FilePath logs.txt
```

Now logs appear both in terminal AND in `logs.txt`.

### Issue 4: Check Current Settings

Add a debug endpoint to see current configuration:

```python
# Add to app/main.py

@app.get("/debug/settings")
async def debug_settings():
    """Show current settings (for debugging)."""
    settings = get_settings()
    return {
        "debug": settings.debug,
        "verbose_mode": settings.debug,  # Same thing
        "app_name": settings.app_name,
        "app_version": settings.app_version
    }
```

Then visit: http://localhost:8000/debug/settings

---

## Best Practices

### 1. **Development Mode**
```env
DEBUG=true  # See what the agent is doing
```
✅ Good for debugging and understanding agent behavior

### 2. **Production Mode**
```env
DEBUG=false  # Reduce log clutter
```
✅ Better performance, cleaner logs

### 3. **Investigate Issues**
```env
DEBUG=true  # Temporarily enable to see what went wrong
```
✅ Enable only when troubleshooting

---

## Summary

### ✅ Quick Checklist

1. **Create `.env` file** in `backend/` folder
2. **Add `DEBUG=true`** to enable verbose mode
3. **Restart backend server**: `.\start_server.ps1`
4. **Watch the terminal** where server is running
5. **Send a chat request** via frontend or API
6. **Observe detailed logs** showing agent reasoning

### 📍 Where Logs Appear

**Terminal/Console** where you run `start_server.ps1`

**NOT** in:
- Frontend console (browser DevTools)
- Separate log files (unless you redirect output)
- VS Code Output panel (unless you use VS Code terminal)

### 🎯 What Verbose Mode Shows

- Which tool the agent decided to call
- Why the agent made that decision
- Tool input parameters
- Tool output results
- How many iterations occurred
- Final response generation

---

## Example Session

```powershell
# Terminal 1: Start backend with verbose mode
PS C:\Learning_Lab\ResumeBuilder\backend> $env:DEBUG="true"
PS C:\Learning_Lab\ResumeBuilder\backend> .\start_server.ps1

INFO:     Started server process [12345]
INFO:     Uvicorn running on http://0.0.0.0:8000

# ← Now send requests and watch THIS terminal for logs! ←
```

You're all set! Verbose mode is enabled by default (`debug: bool = True`), so you just need to watch the backend terminal when testing the agent! 🎉
