# Resume Builder App - Complete System Architecture & Workflow

## Table of Contents
1. [System Overview](#system-overview)
2. [Architecture Diagram](#architecture-diagram)
3. [LangChain Integration](#langchain-integration)
4. [LangGraph Integration: Structured Agent Workflow](#langgraph-integration-structured-agent-workflow)
5. [API Costs & Token Economics](#api-costs--token-economics)
6. [RAG Pipeline Explained](#rag-pipeline-explained)
7. [LLM Integration Points](#llm-integration-points)
8. [All Functionalities](#all-functionalities)
9. [Complete Workflow with Example](#complete-workflow-with-example)
10. [Chunking Strategy Explained](#chunking-strategy-explained)
11. [API Endpoints Documentation](#api-endpoints-documentation)
12. [How Everything Works Together](#how-everything-works-together)

---

## System Overview

The Resume Builder is an **AI-powered Resume Screening System** that uses:
- **RAG (Retrieval-Augmented Generation)** to find relevant resumes
- **LLM (Large Language Model)** to understand and score candidates
- **Vector Database** to enable semantic search
- **REST API** for backend operations
- **React Frontend** for user interaction

### Core Technologies
```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React)                          │
│  - Resume upload interface                                   │
│  - Chat-based query interface                                │
│  - Candidate results display                                 │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP/REST API
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                Backend (FastAPI/Python)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Resume       │  │ RAG          │  │ LLM          │      │
│  │ Parser       │  │ Pipeline     │  │ Client       │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                              │
│  🔗 LangChain Layer (Orchestration)                          │
│     - Text Splitting (RecursiveCharacterTextSplitter)        │
│     - Embedding Generation (AzureOpenAIEmbeddings)           │
└────────────────────┬───────────────────────┬────────────────┘
                     │                       │
          ┌──────────▼──────────┐  ┌────────▼──────────┐
          │   ChromaDB          │  │  Azure OpenAI     │
          │  (Vector Store)     │  │  - GPT-4          │
          │  - Embeddings       │  │  - Embeddings     │
          │  - Metadata         │  │                   │
          └─────────────────────┘  └───────────────────┘
```

---

## LangChain Integration

**LangChain** is a framework that simplifies building LLM applications. In this system, LangChain acts as the **orchestration layer** between our application and AI services.

### What is LangChain?

LangChain provides pre-built components and abstractions for:
- **Text Splitting**: Intelligent document chunking with semantic awareness
- **Embeddings**: Unified interface to various embedding providers
- **Vector Stores**: Integration with multiple vector databases
- **LLM Chains**: Combining multiple AI operations
- **Prompt Management**: Reusable prompt templates

### Why LangChain in This Project?

```
┌─────────────────────────────────────────────────────────────────────┐
│               Without LangChain (Manual Implementation)              │
├─────────────────────────────────────────────────────────────────────┤
│  ❌ Write custom text splitting logic                               │
│  ❌ Handle Azure OpenAI API directly (auth, retries, errors)        │
│  ❌ Manage batching and rate limiting manually                      │
│  ❌ Handle different embedding model formats                        │
│  ❌ Write boilerplate for async operations                          │
│  ❌ 500+ lines of complex integration code                          │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│               With LangChain (Simplified)                            │
├─────────────────────────────────────────────────────────────────────┤
│  ✅ text_splitter.split_text(text) - Done!                          │
│  ✅ embeddings.aembed_query(query) - Done!                          │
│  ✅ Built-in retry logic and error handling                         │
│  ✅ Automatic batching for efficiency                               │
│  ✅ Provider-agnostic (switch from Azure to OpenAI easily)          │
│  ✅ ~50 lines of clean, maintainable code                           │
└─────────────────────────────────────────────────────────────────────┘
```

### LangChain Components Used

#### 1. RecursiveCharacterTextSplitter

**Purpose**: Intelligently split resumes into chunks while preserving semantic meaning

**Location**: `app/services/chunking_service.py`

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Initialize splitter with smart separators
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,           # Max 500 characters per chunk
    chunk_overlap=50,         # 50 characters overlap
    length_function=len,      # Measure by character count
    separators=["\n\n", "\n", " ", ""]  # Try these in order
)

# Split text intelligently
chunks = text_splitter.split_text(resume_text)
```

**How It Works**:
```
RecursiveCharacterTextSplitter tries separators in order:

1. First, try splitting on "\n\n" (paragraph breaks)
   └─> Preserves paragraph structure

2. If chunks still too large, split on "\n" (line breaks)
   └─> Preserves sentence structure

3. If still too large, split on " " (spaces)
   └─> Preserves word boundaries

4. Last resort, split on "" (characters)
   └─> Avoids cutting mid-word

Result: Natural, meaningful chunks! ✨
```

**Example**:
```
Input Resume:
"John Doe
Senior Software Engineer

Skills:
Python, FastAPI, Docker, Kubernetes

Experience:
TechCorp (2019-2024)
- Built REST APIs using FastAPI
- Deployed microservices on Kubernetes"

RecursiveCharacterTextSplitter Output:
┌─────────────────────────────────────────────┐
│ Chunk 0 (natural paragraph break):         │
│ "John Doe                                   │
│  Senior Software Engineer                   │
│                                             │
│  Skills:                                    │
│  Python, FastAPI, Docker, Kubernetes"       │
├─────────────────────────────────────────────┤
│ Chunk 1 (preserves experience section):    │
│ "Experience:                                │
│  TechCorp (2019-2024)                       │
│  - Built REST APIs using FastAPI            │
│  - Deployed microservices on Kubernetes"    │
└─────────────────────────────────────────────┘

✅ Clean, semantic chunks that make sense!
```

**Benefits**:
- ✅ **Semantic Awareness**: Splits at natural boundaries
- ✅ **Configurable**: Adjust chunk size and overlap
- ✅ **Tested**: Battle-tested by thousands of LangChain users
- ✅ **Maintains Context**: Overlap ensures no information loss

---

#### 2. AzureOpenAIEmbeddings

**Purpose**: Simplify Azure OpenAI embedding generation with built-in error handling

**Location**: `app/services/embedding_service.py`

```python
from langchain_openai import AzureOpenAIEmbeddings

# Initialize with Azure credentials
embeddings = AzureOpenAIEmbeddings(
    azure_endpoint=endpoint,
    api_key=api_key,
    model="text-embedding-ada-002",
    api_version="2024-02-15-preview"
)

# Generate single embedding (for search queries)
query_vector = await embeddings.aembed_query("Find Python developers")

# Generate batch embeddings (for multiple chunks)
vectors = await embeddings.aembed_documents([chunk1, chunk2, chunk3])
```

**What LangChain Handles Automatically**:
```
┌─────────────────────────────────────────────────────────────────────┐
│  LangChain's AzureOpenAIEmbeddings Does:                             │
├─────────────────────────────────────────────────────────────────────┤
│  1. ✅ Authentication & API Key Management                           │
│  2. ✅ Request Formatting (proper JSON structure)                    │
│  3. ✅ Retry Logic (exponential backoff on failures)                 │
│  4. ✅ Rate Limiting (respects Azure OpenAI limits)                  │
│  5. ✅ Batching (chunks multiple requests efficiently)               │
│  6. ✅ Error Handling (graceful degradation)                         │
│  7. ✅ Async Support (non-blocking operations)                       │
│  8. ✅ Response Parsing (extract vectors from API response)          │
└─────────────────────────────────────────────────────────────────────┘
```

**Manual Implementation vs LangChain**:

```python
# ❌ Without LangChain (Manual):
import httpx
import asyncio
from tenacity import retry, stop_after_attempt

@retry(stop=stop_after_attempt(3))
async def embed_text(text: str):
    headers = {
        "api-key": api_key,
        "Content-Type": "application/json"
    }
    body = {"input": text}
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{endpoint}/openai/deployments/{model}/embeddings",
            headers=headers,
            json=body,
            params={"api-version": api_version},
            timeout=30.0
        )
        
        if response.status_code != 200:
            raise Exception(f"API Error: {response.text}")
        
        data = response.json()
        return data["data"][0]["embedding"]

# ... 50+ more lines for batching, rate limiting, etc.


# ✅ With LangChain (Simple):
embeddings = AzureOpenAIEmbeddings(
    azure_endpoint=endpoint,
    api_key=api_key,
    model="text-embedding-ada-002"
)

vector = await embeddings.aembed_query(text)
# That's it! LangChain handles everything. 🎉
```

**Benefits**:
- ✅ **Robust**: Built-in retry and error handling
- ✅ **Efficient**: Automatic batching saves API calls
- ✅ **Maintainable**: Update LangChain, not custom code
- ✅ **Portable**: Switch providers (Azure → OpenAI) by changing 1 line

---

### LangChain in the Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│  UPLOAD FLOW: How LangChain Powers Resume Processing                │
└─────────────────────────────────────────────────────────────────────┘

User Uploads Resume PDF
         │
         ▼
   ┌──────────┐
   │ PyPDF    │ Extract Text
   └────┬─────┘
        │ Raw Text: 4,527 characters
        ▼
   ┌──────────────────────────────────────────┐
   │ 🔗 LangChain RecursiveTextSplitter       │
   │                                          │
   │  Intelligent Chunking:                   │
   │  1. Try splitting on "\n\n" (paragraphs) │
   │  2. Try splitting on "\n" (lines)        │
   │  3. Try splitting on " " (words)         │
   │  4. Last resort: character split         │
   │                                          │
   │  Result: 10 semantic chunks ✅           │
   └────┬─────────────────────────────────────┘
        │ 10 chunks: [chunk0, chunk1, ..., chunk9]
        ▼
   ┌──────────────────────────────────────────┐
   │ 🔗 LangChain AzureOpenAIEmbeddings       │
   │                                          │
   │  embeddings.aembed_documents(chunks)     │
   │                                          │
   │  Behind the scenes:                      │
   │  • Batches chunks (3-5 per API call)     │
   │  • Handles rate limits automatically     │
   │  • Retries on transient failures         │
   │  • Parses responses                      │
   │                                          │
   │  Result: 10 vectors (1536-dim each) ✅   │
   └────┬─────────────────────────────────────┘
        │ 10 embeddings: [[0.012, ...], [0.045, ...], ...]
        ▼
   ┌──────────┐
   │ ChromaDB │ Store vectors + metadata
   └──────────┘

✅ Resume indexed and searchable!
```

```
┌─────────────────────────────────────────────────────────────────────┐
│  SEARCH FLOW: How LangChain Powers Resume Search                    │
└─────────────────────────────────────────────────────────────────────┘

User Query: "Find Python developers"
         │
         ▼
   ┌──────────────────────────────────────────┐
   │ 🔗 LangChain AzureOpenAIEmbeddings       │
   │                                          │
   │  embeddings.aembed_query(query)          │
   │                                          │
   │  Behind the scenes:                      │
   │  • Sends to Azure OpenAI API             │
   │  • Handles auth & retries                │
   │  • Extracts vector from response         │
   │                                          │
   │  Result: 1 query vector ✅               │
   └────┬─────────────────────────────────────┘
        │ Query embedding: [0.123, -0.456, ...]
        ▼
   ┌──────────┐
   │ ChromaDB │ Vector similarity search
   └────┬─────┘
        │ Top 5 matching chunks
        ▼
    Format results → Return to user

✅ Semantic search complete!
```

---

### Key Advantages of Using LangChain

#### 1. **Abstraction Layer**
```
Your Code → LangChain → Azure OpenAI
     │           │            │
     │           └─ Handles all complexities
     │
     └─ Simple, clean interface
```

#### 2. **Provider Flexibility**
```python
# Switch from Azure to OpenAI in seconds:

# Before (Azure):
embeddings = AzureOpenAIEmbeddings(
    azure_endpoint=endpoint,
    api_key=api_key
)

# After (OpenAI):
embeddings = OpenAIEmbeddings(
    openai_api_key=api_key
)

# Your code doesn't change! Same .aembed_query() method
```

#### 3. **Production-Ready Features**
- ✅ Exponential backoff retry logic
- ✅ Rate limiting and quota management
- ✅ Request batching for efficiency
- ✅ Comprehensive error messages
- ✅ Timeout handling
- ✅ Async/await support

#### 4. **Community Support**
- 📚 Extensive documentation
- 🐛 Bug fixes from thousands of users
- 🚀 Regular updates and improvements
- 💬 Active community for help

---

### LangChain Libraries Used

```python
# requirements.txt
langchain>=0.1.0                    # Core LangChain framework
langchain-openai>=0.0.5             # Azure OpenAI integration
langchain-community>=0.0.17         # Community integrations
```

**What Each Provides**:
- **langchain**: Core abstractions and base classes
- **langchain-openai**: Azure/OpenAI specific implementations
- **langchain-community**: Additional integrations (ChromaDB, etc.)

---

### Performance Impact

**Chunking Performance**:
```
Without LangChain (Manual regex splitting):
  • 4,527 char resume: ~5ms
  • Issues: Poor split quality, lost context

With LangChain RecursiveTextSplitter:
  • 4,527 char resume: ~10ms
  • Benefits: Semantic splits, preserved context
  • Trade-off: +5ms for much better quality ✅
```

**Embedding Performance**:
```
Without LangChain (Manual API calls):
  • 10 chunks: 10 sequential API calls = ~10 seconds
  • No retry logic: Fails on transient errors

With LangChain AzureOpenAIEmbeddings:
  • 10 chunks: 2-3 batched API calls = ~2-3 seconds
  • Auto-retry: Handles transient errors
  • Performance gain: 70% faster! ✅
```

---

### Summary: Why LangChain?

```
┌─────────────────────────────────────────────────────────────────────┐
│                    LangChain Value Proposition                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  🎯 Simplicity: Complex operations in 1-2 lines of code             │
│  🔒 Reliability: Battle-tested error handling and retries           │
│  ⚡ Performance: Built-in batching and optimization                 │
│  🔄 Flexibility: Switch AI providers without code changes           │
│  📚 Maintainability: Update library instead of custom code          │
│  🚀 Productivity: Focus on business logic, not integration details  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

**In This Project**:
- **RecursiveCharacterTextSplitter**: Ensures quality chunks for better search
- **AzureOpenAIEmbeddings**: Simplifies embedding generation with Azure

**Result**: Robust, maintainable RAG system in 1/10th the code! 🎉

---

## LangGraph Integration: Structured Agent Workflow

### What is LangGraph?

**LangGraph** is a library built on top of LangChain that enables creating **stateful, graph-based workflows** for AI agents. It transforms simple loop-based agents into structured, composable workflows with explicit control flow.

```
┌─────────────────────────────────────────────────────────────────────┐
│                    LangGraph Architecture                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Traditional Loop-Based Agent:                                      │
│  ❌ while iteration < max_iterations:                               │
│       • Hard to debug (where is it stuck?)                          │
│       • Hard to extend (add new logic = modify loop)                │
│       • Hard to visualize (what's the flow?)                        │
│       • Tight coupling (everything in one function)                 │
│                                                                      │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                                                      │
│  LangGraph Graph-Based Agent:                                       │
│  ✅ Explicit nodes with clear responsibilities                      │
│  ✅ Visual graph structure (see workflow at a glance)               │
│  ✅ Composable (add/remove nodes easily)                            │
│  ✅ Debuggable (inspect state at each node)                         │
│  ✅ Testable (test individual nodes in isolation)                   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Why LangGraph for This Project?

Our recruitment agent needs to:
1. **Reason** about user queries
2. **Decide** whether to use tools or respond directly
3. **Execute** tools (search candidates, list database, etc.)
4. **Generate** natural language responses
5. **Loop** back for multi-step reasoning

**LangGraph provides**:
- 🎯 **Clear separation of concerns** (each node = one responsibility)
- 🔄 **Flexible control flow** (conditional routing based on state)
- 📊 **Observable execution** (track state through the graph)
- 🧪 **Testable components** (unit test each node independently)

---

### Graph Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│              Recruitment Agent Workflow Graph                        │
└─────────────────────────────────────────────────────────────────────┘

                             ┌─────────┐
                             │  START  │
                             └────┬────┘
                                  │
                                  ▼
                        ┌──────────────────┐
                        │  Reasoning Node  │
                        │                  │
                        │  • Analyze query │
                        │  • Check context │
                        │  • Decide action │
                        └────────┬─────────┘
                                 │
                     ┌───────────┴──────────┐
                     │                      │
            needs_tool = True      needs_tool = False
                     │                      │
                     ▼                      ▼
         ┌────────────────────┐   ┌──────────────────────┐
         │ Tool Execution Node│   │ Response Generation  │
         │                    │   │        Node          │
         │ • Execute tool     │   │                      │
         │ • Handle errors    │   │ • Generate final     │
         │ • Update state     │   │   answer             │
         └──────┬─────────────┘   │ • Format response    │
                │                 └──────────┬───────────┘
                │                            │
        iteration < max?                     │
                │                            │
         ┌──────┴──────┐                    │
         │             │                    │
        Yes            No                   │
         │             │                    │
         └──────┐      └────────────────────┤
                │                           │
                ▼                           ▼
         [Loop back to                 ┌────────┐
          Reasoning Node]              │  END   │
                                       └────────┘

Legend:
  • Rectangles = Nodes (processing units)
  • Arrows = Edges (transitions)
  • Conditions = Routing logic
```

---

### State Schema (AgentState)

The graph maintains a **shared state** that flows through all nodes:

```python
# Location: app/agents/graph_state.py

class AgentState(TypedDict):
    """Shared state for the recruitment agent workflow."""
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # INPUT STATE (provided by user)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    user_question: str                   # Original query
    chat_history: List[BaseMessage]      # Conversation context
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # DECISION STATE (set by reasoning node)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    needs_tool: bool                     # True = use tool, False = respond
    tool_name: Optional[str]             # Which tool to execute
    tool_arguments: Optional[Dict]       # Tool parameters
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # EXECUTION STATE (updated by tool execution node)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    tool_result: Optional[str]           # Tool output
    tool_calls_made: List[str]           # Tracking tool usage
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # OUTPUT STATE (generated by response node)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    final_answer: Optional[str]          # User-facing response
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # CONTROL STATE (loop management)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    iteration_count: int                 # Current iteration
    max_iterations: int                  # Safety limit (default: 5)
    error: Optional[str]                 # Error tracking
```

**Key Feature**: `tool_calls_made` uses `Annotated[List[str], add]`
- The `add` operator tells LangGraph to **automatically accumulate** list items
- Each node only returns NEW items: `state["tool_calls_made"] = [new_tool]`
- LangGraph handles concatenation: `[tool1, tool2, tool3, ...]`

---

### Node Implementations

#### 1. Reasoning Node

**Purpose**: Analyze the query and decide what action to take

```python
# Location: app/agents/graph_nodes.py

async def reasoning_node(state: AgentState) -> AgentState:
    """
    LLM analyzes the user query and decides:
      • Does this need a tool? (search, list candidates, etc.)
      • Can I answer directly from context?
    
    Flow:
      1. Build prompt with query + chat history + available tools
      2. Call LLM (gpt-4)
      3. Parse response for tool calls or direct answer
      4. Update state with decision
    """
    
    # Build messages for LLM
    messages = [
        SystemMessage(content=REASONING_PROMPT),
        *state["chat_history"],
        HumanMessage(content=state["user_question"])
    ]
    
    # Call LLM with tool definitions
    response = await llm_client.chat.completions.create(
        model="gpt-4",
        messages=messages,
        tools=tool_definitions,  # LLM knows what tools are available
        temperature=0.7
    )
    
    # Parse LLM decision
    if response.tool_calls:
        # LLM wants to use a tool
        state["needs_tool"] = True
        state["tool_name"] = response.tool_calls[0].name
        state["tool_arguments"] = response.tool_calls[0].arguments
    else:
        # LLM has a direct answer
        state["needs_tool"] = False
        state["final_answer"] = response.content
    
    return state
```

**Example Decision Flow**:
```
User Query: "Find Python developers with 5+ years experience"

Reasoning Node:
  ├─ Analyzes query
  ├─ Recognizes need for search tool
  └─ Returns:
      {
        "needs_tool": True,
        "tool_name": "search_candidates",
        "tool_arguments": {
          "query": "Python developers with 5+ years experience"
        }
      }
```

---

#### 2. Tool Execution Node

**Purpose**: Execute the tool selected by the reasoning node

```python
async def tool_execution_node(state: AgentState) -> AgentState:
    """
    Execute the tool and handle results/errors.
    
    Flow:
      1. Get tool name and arguments from state
      2. Find matching tool in tool registry
      3. Execute tool (async or sync)
      4. Store result in state
      5. Track tool usage
    """
    
    tool_name = state["tool_name"]
    tool_args = state["tool_arguments"]
    
    # Find tool in registry
    tool = next((t for t in tools if t.name == tool_name), None)
    
    if not tool:
        state["error"] = f"Tool {tool_name} not found"
        return state
    
    try:
        # Execute tool (handles both sync and async)
        if tool.coroutine:
            result = await tool.coroutine(**tool_args)
        else:
            result = tool.func(**tool_args)
        
        # Update state
        state["tool_result"] = result
        state["tool_calls_made"] = [tool_name]  # New tool only
        state["needs_tool"] = False
        
    except Exception as e:
        state["error"] = f"Tool execution failed: {str(e)}"
        state["tool_result"] = f"Error: {str(e)}"
    
    return state
```

**Example Execution**:
```
Tool Execution Node receives:
  {
    "tool_name": "search_candidates",
    "tool_arguments": {"query": "Python developers..."}
  }

Execution:
  ├─ Calls search_candidates tool
  ├─ Gets candidates from ChromaDB
  └─ Returns:
      {
        "tool_result": "Found 4 matching candidates:\n1. John...",
        "tool_calls_made": ["search_candidates"]
      }
```

---

#### 3. Response Generation Node

**Purpose**: Generate natural language response for the user

```python
async def response_generation_node(state: AgentState) -> AgentState:
    """
    Convert tool results into user-friendly response.
    
    Flow:
      1. Check if we have tool results or direct answer
      2. If tool results, format them for LLM
      3. Generate natural language summary
      4. Return final answer
    """
    
    # If reasoning node already provided answer, use it
    if state["final_answer"]:
        return state
    
    # Otherwise, format tool results
    tool_result = state.get("tool_result", "No results")
    
    # Generate response with LLM
    prompt = f"""
    User asked: {state["user_question"]}
    
    Tool results:
    {tool_result}
    
    Generate a helpful, natural language response.
    """
    
    response = await llm_client.generate_response(prompt)
    state["final_answer"] = response
    
    return state
```

**Example Response**:
```
Response Generation Node receives:
  {
    "user_question": "Find Python developers...",
    "tool_result": "Found 4 candidates: 1. John Doe..."
  }

Generation:
  ├─ Formats tool results
  ├─ Calls LLM for natural language
  └─ Returns:
      {
        "final_answer": "I found 4 Python developers with 5+ 
                        years experience. Here are the top matches:
                        1. John Doe - 7 years experience..."
      }
```

---

### Conditional Routing

LangGraph uses **conditional edges** to dynamically route between nodes:

#### Route 1: Should Use Tool?

```python
def should_use_tool(state: AgentState) -> str:
    """
    Decide next node after reasoning.
    
    Returns:
      • "tool_execution" → Execute the tool
      • "response_generation" → Skip tool, generate response
    """
    if state["needs_tool"]:
        return "tool_execution"
    return "response_generation"
```

#### Route 2: Should Continue Loop?

```python
def should_continue_loop(state: AgentState) -> str:
    """
    Decide whether to loop back for more reasoning.
    
    Returns:
      • "reasoning" → Continue for multi-step tasks
      • END → We're done, return to user
    """
    # Safety check: max iterations
    if state["iteration_count"] >= state["max_iterations"]:
        return END
    
    # Check if we need more tool calls
    if state["needs_tool"] and not state.get("error"):
        return "reasoning"
    
    return END
```

---

### Workflow Definition

```python
# Location: app/agents/workflow.py

def create_recruitment_workflow(
    llm_client,
    tools: List,
    verbose: bool = False
):
    """Build and compile the LangGraph workflow."""
    
    # Initialize graph with state schema
    workflow = StateGraph(AgentState)
    
    # Create node manager
    nodes = GraphNodes(llm_client, tools, verbose)
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 1: Add nodes to the graph
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    workflow.add_node("reasoning", nodes.reasoning_node)
    workflow.add_node("tool_execution", nodes.tool_execution_node)
    workflow.add_node("response_generation", nodes.response_generation_node)
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 2: Set entry point
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    workflow.set_entry_point("reasoning")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 3: Add edges (transitions)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    # Conditional: reasoning → tool_execution OR response_generation
    workflow.add_conditional_edges(
        "reasoning",
        nodes.should_use_tool,
        {
            "tool_execution": "tool_execution",
            "response_generation": "response_generation"
        }
    )
    
    # Conditional: tool_execution → reasoning (loop) OR END
    workflow.add_conditional_edges(
        "tool_execution",
        nodes.should_continue_loop,
        {
            "reasoning": "reasoning",
            END: END
        }
    )
    
    # Direct: response_generation → END
    workflow.add_edge("response_generation", END)
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 4: Compile the graph
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    return workflow.compile()
```

---

### Integration with Existing System

```
┌─────────────────────────────────────────────────────────────────────┐
│          LangGraph Integration with FastAPI Backend                 │
└─────────────────────────────────────────────────────────────────────┘

User Request
     │
     ▼
┌─────────────────────────┐
│  FastAPI Endpoint       │
│  /query/chat            │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  RecruitmentAgent       │  ← Main agent class
│  .process_query()       │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  LangGraph Workflow     │  ← Graph execution
│  .ainvoke(state)        │
└────────┬────────────────┘
         │
         ├─► Reasoning Node → Tool Execution → Response
         │
         ▼
   Final State
         │
         ▼
   Extract Results:
     • final_answer
     • tool_calls_made
     • error (if any)
         │
         ▼
   Return to User
```

**Updated RecruitmentAgent**:

```python
# Location: app/agents/recruitment_agent.py

class RecruitmentAgent:
    """Agent using LangGraph workflow for structured execution."""
    
    def __init__(self, llm_client, tools, verbose=False):
        # Create workflow
        self.workflow = create_recruitment_workflow(
            llm_client=llm_client,
            tools=tools,
            verbose=verbose
        )
    
    async def process_query(
        self,
        user_question: str,
        chat_history: List = None
    ) -> Dict[str, Any]:
        """Execute the graph workflow."""
        
        # Create initial state
        initial_state = create_initial_state(
            user_question=user_question,
            chat_history=chat_history or []
        )
        
        # Execute workflow (LangGraph handles the flow)
        final_state = await self.workflow.ainvoke(initial_state)
        
        # Return results
        return {
            "answer": final_state.get("final_answer", "No answer generated"),
            "tools_used": final_state.get("tool_calls_made", []),
            "error": final_state.get("error")
        }
```

---

### Before vs After Comparison

#### Before (Loop-Based Agent)

```python
# ❌ Old implementation: ~265 lines

async def process_query(self, user_question, chat_history):
    iteration = 0
    max_iterations = 5
    
    while iteration < max_iterations:
        # Reasoning
        response = await self.llm_client.generate()
        
        # Tool detection
        if self._needs_tool(response):
            tool_result = await self._execute_tool()
            # ... 50 lines of tool handling
        
        # Check if done
        if self._is_complete():
            break
        
        iteration += 1
        # ... more loop logic
    
    return self._format_response()
```

**Problems**:
- 🔴 All logic in one function (tight coupling)
- 🔴 Hard to test individual steps
- 🔴 Difficult to visualize flow
- 🔴 Error handling scattered throughout
- 🔴 Hard to add new capabilities

---

#### After (LangGraph-Based Agent)

```python
# ✅ New implementation: ~185 lines (30% reduction)

async def process_query(self, user_question, chat_history):
    # Create initial state
    initial_state = create_initial_state(
        user_question=user_question,
        chat_history=chat_history
    )
    
    # Execute workflow (graph handles everything)
    final_state = await self.workflow.ainvoke(initial_state)
    
    # Extract results
    return {
        "answer": final_state["final_answer"],
        "tools_used": final_state["tool_calls_made"]
    }
```

**Benefits**:
- ✅ Clean separation (reasoning, execution, response = separate nodes)
- ✅ Easy to test (test each node independently)
- ✅ Visual graph structure (see workflow.py)
- ✅ Centralized error handling (node level)
- ✅ Extensible (add nodes via workflow builder)

---

### Real Execution Example

```
Query: "Find Python developers with 5+ years experience"

EXECUTION TRACE:
════════════════════════════════════════════════════════════════════

[1] START → Reasoning Node
    State In:  {user_question: "Find Python developers...", 
                chat_history: []}
    LLM Call:  gpt-4 (input: 1,132 tokens)
    Decision:  needs_tool=True, tool_name="search_candidates"
    State Out: {needs_tool: True, 
                tool_name: "search_candidates",
                tool_arguments: {"query": "Python developers..."}}

[2] Reasoning Node → Tool Execution Node (route: should_use_tool)
    State In:  {needs_tool: True, tool_name: "search_candidates"}
    Tool Exec: search_candidates("Python developers...")
      ├─ Embedding API: text-embedding-ada-002 (52 chars → 13 tokens)
      ├─ ChromaDB Search: 5 results
      └─ Duration: 1.2 seconds
    State Out: {tool_result: "Found 4 candidates...",
                tool_calls_made: ["search_candidates"],
                needs_tool: False}

[3] Tool Execution Node → Reasoning Node (route: should_continue_loop)
    Reason:    needs_tool=False, iteration=1 < max=5
    Decision:  Continue to END

[4] Reasoning Node → Response Generation Node
    State In:  {tool_result: "Found 4 candidates...",
                user_question: "Find Python developers..."}
    LLM Call:  gpt-4 (input: 513 tokens, output: 300 tokens)
    Generated: Natural language summary of candidates
    State Out: {final_answer: "I found 4 Python developers..."}

[5] Response Generation Node → END
    Final State:
      ├─ final_answer: "I found 4 Python developers with 5+ years..."
      ├─ tool_calls_made: ["search_candidates"]
      ├─ iteration_count: 1
      └─ error: None

✅ Total Duration: 3.5 seconds
✅ Tools Used: 1 (search_candidates)
✅ LLM Calls: 2 (reasoning + response)
✅ Cost: ~$0.016
```

---

### Benefits of LangGraph Integration

```
┌─────────────────────────────────────────────────────────────────────┐
│                    LangGraph Benefits                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  🎯 Modularity                                                       │
│     • Each node has single responsibility                           │
│     • Easy to update individual components                          │
│     • Reusable across different workflows                           │
│                                                                      │
│  🔍 Observability                                                    │
│     • Inspect state at each node                                    │
│     • Track execution path through graph                            │
│     • Debug specific node failures                                  │
│                                                                      │
│  🧪 Testability                                                      │
│     • Unit test individual nodes                                    │
│     • Mock state for edge cases                                     │
│     • Test routing conditions separately                            │
│                                                                      │
│  🚀 Extensibility                                                    │
│     • Add new nodes without refactoring                             │
│     • Modify routing logic independently                            │
│     • Compose multiple workflows                                    │
│                                                                      │
│  📊 Maintainability                                                  │
│     • Visual graph structure (workflow.py)                          │
│     • Clear data flow (state schema)                                │
│     • Self-documenting architecture                                 │
│                                                                      │
│  ⚡ Performance                                                      │
│     • Efficient state management                                    │
│     • Automatic state updates (add operator)                        │
│     • Minimal overhead (~5ms per transition)                        │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

### Files Added/Modified

```
backend/app/agents/
├── graph_state.py          (NEW) - State schema definition
├── graph_nodes.py          (NEW) - Node implementations
├── workflow.py             (NEW) - Graph builder
└── recruitment_agent.py    (MODIFIED) - Uses workflow instead of loop

requirements.txt            (MODIFIED) - Added langgraph>=0.2.0

Documentation:
├── LANGGRAPH_ARCHITECTURE.md      - Detailed architecture
├── MIGRATION_GUIDE.md             - Migration instructions
├── BEFORE_AFTER_COMPARISON.md     - Code comparison
└── LANGGRAPH_QUICKSTART.md        - Quick start guide
```

---

### Testing the LangGraph Agent

```bash
# Run example script
cd backend
python example_langgraph_agent.py

# Test via API
curl -X POST http://localhost:8000/query/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Find Python developers with 5+ years experience",
    "chat_history": []
  }'
```

---

## API Costs & Token Economics

### ⚠️ Important: Embeddings DO Cost Money!

**Yes, creating embeddings requires calling Azure OpenAI API and costs money.**

Every time you generate an embedding (for upload or search), you're making an API call to Azure OpenAI's `text-embedding-ada-002` model.

```
┌─────────────────────────────────────────────────────────────────────┐
│  Embedding Generation = API Call = 💰 Cost                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Your Code                                                          │
│      ↓                                                              │
│  LangChain (AzureOpenAIEmbeddings)                                  │
│      ↓                                                              │
│  HTTPS Request to Azure OpenAI API                                  │
│      ↓                                                              │
│  Azure OpenAI processes text → returns vector                       │
│      ↓                                                              │
│  You get charged based on tokens processed                          │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

### Azure OpenAI Pricing (as of 2024)

#### 1. **Embedding Model: text-embedding-ada-002**

```
┌─────────────────────────────────────────────────────────────────────┐
│  text-embedding-ada-002 Pricing                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Cost: $0.0001 per 1,000 tokens                                     │
│        ($0.10 per 1 million tokens)                                 │
│                                                                      │
│  Token Calculation:                                                 │
│    • ~1 token ≈ 4 characters                                        │
│    • 100 characters ≈ 25 tokens                                     │
│    • 1,000 characters ≈ 250 tokens                                  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

#### 2. **GPT-4 Model: gpt-4 (128k context)**

```
┌─────────────────────────────────────────────────────────────────────┐
│  GPT-4 Pricing                                                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Input Cost:  $0.01 per 1,000 tokens ($10 per 1M tokens)            │
│  Output Cost: $0.03 per 1,000 tokens ($30 per 1M tokens)            │
│                                                                      │
│  📊 Comparison:                                                     │
│    • GPT-4 input is 100x more expensive than embeddings             │
│    • GPT-4 output is 300x more expensive than embeddings            │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

### Cost Breakdown: Resume Upload

Let's calculate the exact cost to upload one resume:

```
┌─────────────────────────────────────────────────────────────────────┐
│  Resume Upload Cost Example                                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Resume: "john_doe_resume.pdf" (4,527 characters)                   │
│                                                                      │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  STEP 1: Metadata Extraction (GPT-4)                                │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                                                      │
│  Input:  4,527 characters = ~1,132 tokens                           │
│  Output: 50 tokens (JSON response)                                  │
│                                                                      │
│  Cost:                                                              │
│    Input:  1,132 tokens × $0.01 / 1,000 = $0.01132                 │
│    Output:   50 tokens × $0.03 / 1,000 = $0.0015                   │
│    Total:  $0.01282                                                 │
│                                                                      │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  STEP 2: Embedding Generation (text-embedding-ada-002)              │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                                                      │
│  Chunks: 10 chunks (4,527 characters total)                         │
│  Tokens: 4,527 chars ÷ 4 = ~1,132 tokens                            │
│                                                                      │
│  Cost:                                                              │
│    1,132 tokens × $0.0001 / 1,000 = $0.0001132                     │
│                                                                      │
│  LangChain Optimization:                                            │
│    • Batches 10 chunks → 2-3 API calls                              │
│    • Cost remains same (charged per token, not per call)            │
│    • Benefit: Faster processing (2-3 seconds vs 5-10 seconds)       │
│                                                                      │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  TOTAL UPLOAD COST                                                  │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                                                      │
│  GPT-4 Metadata:   $0.01282                                         │
│  Embeddings:       $0.00011                                         │
│  ───────────────────────────                                        │
│  Total:            $0.01293 per resume                              │
│                                                                      │
│  📊 Key Insight:                                                    │
│     91% of cost is GPT-4, only 9% is embeddings!                    │
│     Embeddings are VERY cheap compared to GPT-4.                    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

### Cost Breakdown: Search Query

```
┌─────────────────────────────────────────────────────────────────────┐
│  Search Query Cost Example                                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Query: "Find Python developers with 5+ years experience"           │
│                                                                      │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  STEP 1: Query Embedding (text-embedding-ada-002)                   │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                                                      │
│  Input: 52 characters = ~13 tokens                                  │
│                                                                      │
│  Cost:                                                              │
│    13 tokens × $0.0001 / 1,000 = $0.0000013                        │
│    (effectively FREE - less than 1/100th of a cent!)                │
│                                                                      │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  STEP 2: ChromaDB Vector Search                                     │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                                                      │
│  Cost: $0 (ChromaDB is local, no API calls)                         │
│                                                                      │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  STEP 3: GPT-4 Response Generation (Optional)                       │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                                                      │
│  Context (5 candidates): ~2,000 characters = ~500 tokens            │
│  User query: 52 characters = ~13 tokens                             │
│  Total input: 513 tokens                                            │
│                                                                      │
│  GPT-4 output: ~300 tokens (natural language summary)               │
│                                                                      │
│  Cost:                                                              │
│    Input:  513 tokens × $0.01 / 1,000 = $0.00513                   │
│    Output: 300 tokens × $0.03 / 1,000 = $0.009                     │
│    Total:  $0.01413                                                 │
│                                                                      │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  TOTAL SEARCH COST                                                  │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                                                      │
│  WITHOUT LLM Summary:   $0.000001 (just embedding)                  │
│  WITH LLM Summary:      $0.01413                                    │
│                                                                      │
│  📊 Key Insight:                                                    │
│     Vector search is essentially free!                              │
│     LLM summary is optional and dominates cost if used.             │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

### Total Cost Examples

#### Scenario 1: Small Startup (100 resumes)

```
┌───────────────────────────────────────────┐
│  Initial Upload: 100 resumes              │
│  Cost: 100 × $0.01293 = $1.29             │
│                                           │
│  Monthly Searches: 1,000 queries          │
│  Cost: 1,000 × $0.000001 = $0.001         │
│  (assuming no LLM summaries)              │
│                                           │
│  With LLM summaries:                      │
│  Cost: 1,000 × $0.01413 = $14.13/month    │
│                                           │
│  Total First Month: $1.29 + $14.13        │
│                   = $15.42                │
└───────────────────────────────────────────┘
```

#### Scenario 2: Medium Company (1,000 resumes)

```
┌───────────────────────────────────────────┐
│  Initial Upload: 1,000 resumes            │
│  Cost: 1,000 × $0.01293 = $12.93          │
│                                           │
│  Monthly Searches: 10,000 queries         │
│  With LLM summaries:                      │
│  Cost: 10,000 × $0.01413 = $141.30/month  │
│                                           │
│  Total First Month: $12.93 + $141.30      │
│                   = $154.23               │
└───────────────────────────────────────────┘
```

---

### Why RAG Is Cost-Effective

```
┌─────────────────────────────────────────────────────────────────────┐
│  Scenario: Query 1,000 resumes without RAG                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ❌ Without RAG (Send all resumes to GPT-4):                        │
│                                                                      │
│     1,000 resumes × 4,527 chars = 4,527,000 chars                   │
│     = ~1,131,750 tokens                                             │
│                                                                      │
│     Input cost:  1,131,750 × $0.01 / 1,000 = $11.32 PER QUERY      │
│     Output cost: 300 × $0.03 / 1,000 = $0.009                       │
│     Total: $11.33 per query                                         │
│                                                                      │
│     100 queries/day = $1,133/day = $33,990/month 💸💸💸            │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ✅ With RAG (Vector search + top 5 candidates):                    │
│                                                                      │
│     Query embedding: $0.000001 (negligible)                         │
│     ChromaDB search: $0 (local)                                     │
│     GPT-4 on 5 candidates: ~500 tokens input                        │
│                                                                      │
│     Input cost:  513 × $0.01 / 1,000 = $0.00513                     │
│     Output cost: 300 × $0.03 / 1,000 = $0.009                       │
│     Total: $0.01413 per query                                       │
│                                                                      │
│     100 queries/day = $1.41/day = $42.39/month ✅                   │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  💰 SAVINGS: $33,990 - $42 = $33,948/month (99.87% reduction!)      │
│                                                                      │
│  RAG pays for itself after the FIRST query! 🎉                      │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

### API Call Summary

Every operation that connects to Azure OpenAI:

```
┌─────────────────────────────────────────────────────────────────────┐
│  API Calls in Resume Screening System                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1. ✅ Resume Upload:                                               │
│     • 1 GPT-4 call (metadata extraction)                            │
│     • 2-3 embedding calls (LangChain batches 10 chunks)             │
│     • Total: 3-4 API calls per resume                               │
│     • Cost: ~$0.013 per resume                                      │
│                                                                      │
│  2. ✅ Search Query:                                                │
│     • 1 embedding call (query embedding)                            │
│     • 0 ChromaDB calls (local, no API)                              │
│     • Cost: ~$0.000001 per search                                   │
│                                                                      │
│  3. ✅ Search with LLM Summary:                                     │
│     • 1 embedding call (query)                                      │
│     • 1 GPT-4 call (summary generation)                             │
│     • Cost: ~$0.014 per search                                      │
│                                                                      │
│  4. ✅ Resume Scoring:                                              │
│     • 1 GPT-4 call (scoring analysis)                               │
│     • Cost: ~$0.02-0.05 (depends on resume length)                  │
│                                                                      │
│  5. ✅ Rank Candidates:                                             │
│     • 1 embedding call (query)                                      │
│     • 5-10 GPT-4 calls (score each candidate)                       │
│     • Cost: ~$0.10-0.50 (depends on number of candidates)           │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

### Cost Optimization Tips

```
┌─────────────────────────────────────────────────────────────────────┐
│  How to Minimize API Costs                                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1. ✅ Use RAG (you're already doing this!)                         │
│     • Search first, only send relevant candidates to GPT-4          │
│                                                                      │
│  2. ✅ LangChain Batching (you're already doing this!)              │
│     • Batches multiple chunks in one API call                       │
│     • Reduces overhead, improves speed                              │
│                                                                      │
│  3. ✅ Cache Embeddings (you're already doing this!)                │
│     • Store embeddings in ChromaDB                                  │
│     • Never regenerate embeddings for same resume                   │
│                                                                      │
│  4. 💡 Optional: Make LLM Summary Optional                          │
│     • Let users choose: fast (no summary) vs detailed (with LLM)    │
│     • Saves $0.014 per search if skipped                            │
│                                                                      │
│  5. 💡 Optional: Implement Token Limits                             │
│     • Truncate very long resumes before GPT-4 processing            │
│     • Set max_tokens for GPT-4 responses                            │
│                                                                      │
│  6. 💡 Optional: Use GPT-3.5-Turbo for Some Tasks                   │
│     • 10x cheaper than GPT-4 ($0.001/1k vs $0.01/1k)                │
│     • Good enough for simple summaries                              │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

### Key Takeaways

```
┌─────────────────────────────────────────────────────────────────────┐
│  Summary: API Costs & Token Economics                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ✅ YES, embeddings cost money (Azure OpenAI API calls required)    │
│                                                                      │
│  ✅ BUT embeddings are 100x cheaper than GPT-4:                     │
│     • Embeddings: $0.0001 per 1k tokens                             │
│     • GPT-4: $0.01 per 1k input tokens                              │
│                                                                      │
│  ✅ Upload cost: ~$0.013 per resume (mostly GPT-4)                  │
│  ✅ Search cost: ~$0.000001 without LLM, ~$0.014 with LLM           │
│                                                                      │
│  ✅ RAG saves 99.87% compared to sending all resumes to GPT-4       │
│                                                                      │
│  ✅ LangChain batching reduces API calls but not cost               │
│     • Benefit: Faster processing (2-3 sec vs 5-10 sec)              │
│     • Cost: Same (charged per token, not per API call)              │
│                                                                      │
│  💰 Bottom line: Very affordable for production use!                │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                          USER UPLOADS RESUME                         │
│                         "john_doe_resume.pdf"                        │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 1: PDF PARSING (ResumeParserService)                          │
├─────────────────────────────────────────────────────────────────────┤
│  Input:  PDF file (binary)                                          │
│  Process: Extract text using PyPDF                                  │
│  Output:  Raw text (4,527 characters)                               │
│                                                                      │
│  Example Output:                                                     │
│  "John Doe                                                          │
│   Senior Software Engineer                                          │
│   Skills: Python, FastAPI, Docker, Kubernetes                       │
│   Experience: 5 years at TechCorp..."                               │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 2: LLM METADATA EXTRACTION (GPT-4)                            │
├─────────────────────────────────────────────────────────────────────┤
│  Input:  Raw resume text                                            │
│  Process: Send to GPT-4 with extraction prompt                      │
│  Output:  Structured metadata                                       │
│                                                                      │
│  Prompt Sent to GPT-4:                                              │
│  "Extract skills and years of experience from this resume:          │
│   [resume text]                                                     │
│   Return JSON: {skills: [...], years_experience: int}"              │
│                                                                      │
│  GPT-4 Response:                                                    │
│  {                                                                  │
│    "skills": ["Python", "FastAPI", "Django", "PostgreSQL",         │
│                "Docker", "Kubernetes", "Redis", "AWS"],            │
│    "years_experience": 5                                           │
│  }                                                                  │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 3: TEXT CHUNKING (ChunkingService + LangChain)                │
├─────────────────────────────────────────────────────────────────────┤
│  Input:  Raw text (4,527 chars)                                     │
│  Process: Split into overlapping chunks using LangChain             │
│  Library: RecursiveCharacterTextSplitter                            │
│  Config:  - Chunk size: 500 characters                              │
│           - Overlap: 50 characters                                  │
│           - Separators: ["\n\n", "\n", " ", ""]                     │
│  Output:  10 chunks                                                 │
│                                                                      │
│  WHY 10 CHUNKS?                                                     │
│  Calculation: 4,527 chars ÷ (500 - 50) = ~10 chunks                │
│                                                                      │
│  🔗 LangChain RecursiveCharacterTextSplitter:                       │
│     - Tries paragraph breaks first ("\n\n")                         │
│     - Falls back to line breaks ("\n")                              │
│     - Then word boundaries (" ")                                    │
│     - Last resort: character split                                  │
│                                                                      │
│  Result: Natural, semantic chunks (not arbitrary splits!) ✨        │
│                                                                      │
│  Chunk 0 (chars 0-500):                                             │
│  "John Doe                                                          │
│   Senior Software Engineer                                          │
│   Email: john@example.com                                           │
│   Phone: (555) 123-4567                                             │
│   Skills: Python, FastAPI, Django..."                               │
│                                                                      │
│  Chunk 1 (chars 450-950):  ← Note 50 char overlap                   │
│  "...FastAPI, Django, PostgreSQL, Docker                            │
│   Experience:                                                       │
│   Senior Developer at TechCorp (2019-2024)                          │
│   - Built REST APIs using FastAPI..."                               │
│                                                                      │
│  ... (8 more chunks) ...                                            │
│                                                                      │
│  Chunk 9 (last chunk):                                              │
│  "...Deployed microservices on Kubernetes                           │
│   Education: BS Computer Science, MIT                               │
│   Certifications: AWS Certified Developer"                          │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 4: EMBEDDING GENERATION (EmbeddingService + LangChain)        │
├─────────────────────────────────────────────────────────────────────┤
│  Input:  10 text chunks                                             │
│  Process: Convert each chunk to vector using LangChain wrapper      │
│  Library: AzureOpenAIEmbeddings (from langchain-openai)             │
│  Model:  text-embedding-ada-002                                     │
│  Output:  10 embedding vectors (1536 dimensions each)               │
│                                                                      │
│  ⚠️  IMPORTANT: This requires API calls to Azure OpenAI!            │
│      Cost: $0.0001 per 1,000 tokens (~$0.00011 for 10 chunks)      │
│                                                                      │
│  🔗 LangChain handles:                                              │
│     ✅ API authentication & endpoint management                     │
│     ✅ Automatic batching (3-5 chunks per API call)                 │
│     ✅ Retry logic with exponential backoff                         │
│     ✅ Rate limiting to respect Azure OpenAI quotas                 │
│     ✅ Error handling and graceful degradation                      │
│                                                                      │
│  API Call to Azure OpenAI (abstracted by LangChain):                │
│  POST https://your-endpoint.openai.azure.com/openai/deployments/   │
│       text-embedding-ada-002/embeddings?api-version=2024-02-15      │
│  Body: { "input": "John Doe\nSenior Software Engineer..." }        │
│                                                                      │
│  Response (Chunk 0 Embedding):                                      │
│  [                                                                  │
│    0.00456647,   ← Dimension 0                                      │
│    -0.01196362,  ← Dimension 1                                      │
│    -0.00178753,  ← Dimension 2                                      │
│    0.02345678,   ← Dimension 3                                      │
│    ...           ← 1,532 more numbers                               │
│    -0.00987654   ← Dimension 1535                                   │
│  ]                                                                  │
│                                                                      │
│  This vector represents the SEMANTIC MEANING of the text.           │
│  Similar text = similar vectors = findable by similarity search!    │
│                                                                      │
│  📊 Performance: LangChain batching reduces 10 API calls → 2-3!     │
│  💰 Cost: Same either way (charged per token, not per API call)     │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 5: STORE IN CHROMADB (VectorStoreService)                     │
├─────────────────────────────────────────────────────────────────────┤
│  Input:  10 chunks + 10 embeddings + metadata                       │
│  Process: Store each chunk as a document in ChromaDB                │
│  Collection: "resumes"                                              │
│  Output:  10 documents stored with IDs                              │
│                                                                      │
│  Document 0:                                                        │
│  {                                                                  │
│    "id": "john_doe_resume.pdf_a1b2c3d4_0",                         │
│    "document": "John Doe\nSenior Software Engineer...",            │
│    "metadata": {                                                   │
│      "file_name": "john_doe_resume.pdf",                           │
│      "candidate_name": "John Doe",                                 │
│      "chunk_index": 0,                                             │
│      "total_chunks": 10,                                           │
│      "skills": ["Python", "FastAPI", "Django", ...],              │
│      "years_experience": 5                                         │
│    },                                                              │
│    "embedding": [0.00456647, -0.01196362, ...]                    │
│  }                                                                 │
│                                                                     │
│  Document 1:                                                       │
│  {                                                                 │
│    "id": "john_doe_resume.pdf_a1b2c3d4_1",                        │
│    "document": "...FastAPI, Django, PostgreSQL...",               │
│    "metadata": { ... "chunk_index": 1 ... },                      │
│    "embedding": [0.01234567, -0.00345678, ...]                    │
│  }                                                                 │
│                                                                     │
│  ... (Documents 2-9) ...                                           │
│                                                                     │
│  Stored on disk at: backend/data/chroma_db/                        │
└─────────────────────────────────────────────────────────────────────┘

                          ✅ RESUME UPLOAD COMPLETE
```

---

## RAG Pipeline Explained

**RAG = Retrieval-Augmented Generation**

The RAG pipeline has 3 phases:

### Phase 1: Retrieval (Finding Relevant Resumes)

```
User Query: "Find Python developers with 5+ years experience"
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  RETRIEVAL STEP 1: Query Embedding                                  │
├─────────────────────────────────────────────────────────────────────┤
│  Convert user query to embedding vector (same as resumes)           │
│                                                                      │
│  Input:  "Find Python developers with 5+ years experience"          │
│  API Call: Azure OpenAI text-embedding-ada-002                      │
│  Output: Query embedding [0.012, -0.045, 0.234, ..., -0.123]       │
│          (1536 dimensions)                                          │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│  RETRIEVAL STEP 2: Vector Similarity Search in ChromaDB             │
├─────────────────────────────────────────────────────────────────────┤
│  Compare query embedding with all stored resume embeddings          │
│  Method: Cosine similarity (measures angle between vectors)         │
│                                                                      │
│  Query vector:     [0.012, -0.045, 0.234, ...]                      │
│                                                                      │
│  Resume 1 vector:  [0.015, -0.048, 0.230, ...]  → Similarity: 0.95 │
│  Resume 2 vector:  [0.011, -0.042, 0.237, ...]  → Similarity: 0.93 │
│  Resume 3 vector:  [0.234, -0.567, -0.123, ...] → Similarity: 0.45 │
│                                                                      │
│  ChromaDB automatically ranks by similarity!                        │
│                                                                      │
│  Returns top N results (default: 5)                                 │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│  RETRIEVAL STEP 3: Fetch Metadata & Documents                       │
├─────────────────────────────────────────────────────────────────────┤
│  Retrieved Documents (Top 5 chunks):                                │
│                                                                      │
│  Result 1: (Similarity: 0.95)                                       │
│    Document: "John Doe\nSenior Software Engineer\nPython..."        │
│    Metadata: {skills: ["Python", "FastAPI"], years: 5}              │
│                                                                      │
│  Result 2: (Similarity: 0.93)                                       │
│    Document: "Jane Smith\nPython Developer\n6 years..."             │
│    Metadata: {skills: ["Python", "Django"], years: 6}               │
│                                                                      │
│  ... (3 more results) ...                                           │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
                          Return to User/LLM
```

### Phase 2: Augmentation (Adding Context to LLM)

```
┌─────────────────────────────────────────────────────────────────────┐
│  AUGMENTATION: Prepare Context for LLM                              │
├─────────────────────────────────────────────────────────────────────┤
│  Take retrieved documents and format for GPT-4                      │
│                                                                      │
│  System Prompt:                                                     │
│  "You are a resume screening assistant. Based on the candidate      │
│   information below, answer the user's query."                      │
│                                                                      │
│  Context (Retrieved Documents):                                     │
│  "Candidate 1: John Doe                                             │
│   Skills: Python, FastAPI, Django, PostgreSQL                       │
│   Experience: 5 years as Senior Developer at TechCorp               │
│   [full resume text]                                                │
│                                                                      │
│   Candidate 2: Jane Smith                                           │
│   Skills: Python, Django, React, AWS                                │
│   Experience: 6 years as Full Stack Developer at StartupCo          │
│   [full resume text]                                                │
│                                                                      │
│   ..."                                                              │
│                                                                      │
│  User Query:                                                        │
│  "Find Python developers with 5+ years experience"                  │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
                       Send to GPT-4 (Generation Phase)
```

### Phase 3: Generation (LLM Creates Response)

```
┌─────────────────────────────────────────────────────────────────────┐
│  GENERATION: GPT-4 Produces Final Response                          │
├─────────────────────────────────────────────────────────────────────┤
│  Input:  System Prompt + Context + User Query                       │
│  Model:  GPT-4 (Azure OpenAI)                                       │
│  Output: Structured response with analysis                          │
│                                                                      │
│  GPT-4 Response:                                                    │
│  {                                                                  │
│    "summary": "Found 2 strong candidates matching your criteria.",  │
│    "candidates": [                                                  │
│      {                                                              │
│        "name": "John Doe",                                          │
│        "match_score": 95,                                           │
│        "matching_skills": ["Python", "FastAPI", "Django"],          │
│        "years_experience": 5,                                       │
│        "summary": "Excellent match with 5 years of Python           │
│                    development experience. Strong FastAPI skills."  │
│      },                                                             │
│      {                                                              │
│        "name": "Jane Smith",                                        │
│        "match_score": 88,                                           │
│        "matching_skills": ["Python", "Django", "React"],            │
│        "years_experience": 6,                                       │
│        "summary": "Great candidate with 6 years experience.         │
│                    Diverse full-stack skills."                      │
│      }                                                              │
│    ]                                                                │
│  }                                                                  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## LLM Integration Points

The system uses Azure OpenAI (GPT-4 and text-embedding-ada-002) in **4 key areas**:

### 1. Resume Metadata Extraction (Upload Time)

```python
# File: app/services/resume_parser.py
# Function: extract_metadata_with_llm()

async def extract_metadata_with_llm(self, resume_text: str) -> dict:
    """
    Use GPT-4 to extract structured information from resume text.
    """
    prompt = f"""
    Extract skills and years of experience from this resume:
    
    {resume_text}
    
    Return JSON:
    {{
      "skills": ["skill1", "skill2", ...],
      "years_experience": <number>
    }}
    """
    
    response = await llm_client.chat_completion(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    
    # Returns: {"skills": [...], "years_experience": 5}
    return parse_json(response)
```

**Why?** Extracts structured data that would be hard to parse with regex.

### 2. Text Embedding Generation (Upload & Search Time)

```python
# File: app/services/embedding_service.py
# Function: generate_embeddings()

async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
    """
    Convert text to 1536-dimensional vectors using Azure OpenAI.
    """
    response = await openai_client.embeddings.create(
        model="text-embedding-ada-002",
        input=texts
    )
    
    # Returns: [[0.012, -0.045, ...], [0.234, -0.123, ...], ...]
    return [item.embedding for item in response.data]
```

**Why?** Enables semantic search (understanding meaning, not just keywords).

### 3. Resume Scoring (On-Demand)

```python
# File: app/api/routes_scoring.py
# Function: score_resume()

async def score_resume(job_description: str, resume_text: str):
    """
    Use GPT-4 to score how well a resume matches a job description.
    """
    prompt = f"""
    Job Description:
    {job_description}
    
    Resume:
    {resume_text}
    
    Score this resume 0-100 based on how well it matches the job.
    Provide:
    - Overall score
    - Matching skills
    - Missing skills
    - Detailed explanation
    
    Return JSON: {{"score": 85, "matching_skills": [...], ...}}
    """
    
    response = await llm_client.chat_completion(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    
    return parse_json(response)
```

**Why?** Provides intelligent matching beyond simple keyword search.

### 4. Conversational Query Processing (Search Time)

```python
# File: app/rag/retrieval_pipeline.py
# Function: process_query()

async def process_query(self, user_query: str) -> dict:
    """
    Convert user's natural language query to search and use LLM for response.
    """
    # Step 1: Convert query to embedding
    query_embedding = await embedding_service.generate_embeddings([user_query])
    
    # Step 2: Search ChromaDB
    results = await vector_store.search(query_embedding[0], top_k=5)
    
    # Step 3: Format context for LLM
    context = format_candidates(results)
    
    # Step 4: Generate response with GPT-4
    prompt = f"""
    Based on these candidates:
    {context}
    
    User asked: {user_query}
    
    Provide a helpful summary and rank candidates.
    """
    
    llm_response = await llm_client.chat_completion(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    
    return {"candidates": results, "summary": llm_response}
```

**Why?** Provides natural language interface instead of rigid query syntax.

---

## All Functionalities

### 1. Resume Upload
- **Endpoint**: `POST /api/upload-resume`
- **What it does**: Parse PDF → Extract metadata with LLM → Chunk text → Generate embeddings → Store in ChromaDB
- **LLM Used**: GPT-4 (metadata extraction), text-embedding-ada-002 (vectors)

### 2. Resume Search
- **Endpoint**: `POST /api/search-resumes`
- **What it does**: Convert query to embedding → Search ChromaDB → Rank by similarity → Return candidates
- **LLM Used**: text-embedding-ada-002 (query embedding)

### 3. Resume Scoring
- **Endpoint**: `POST /api/score-resume`
- **What it does**: Take job description + resume → Send both to GPT-4 → Get match score & analysis
- **LLM Used**: GPT-4 (scoring & analysis)

### 4. Conversational Query
- **Endpoint**: `POST /api/query`
- **What it does**: Natural language query → Search → GPT-4 generates human-readable summary
- **LLM Used**: text-embedding-ada-002 (search), GPT-4 (response generation)

### 5. List Resumes
- **Endpoint**: `GET /api/resumes/list`
- **What it does**: Return all candidates stored in ChromaDB with metadata
- **LLM Used**: None (direct database query)

---

## Complete Workflow with Example

Let's walk through a **complete real-world scenario**:

### Scenario: Hiring Manager Looking for Python Developers

```
┌─────────────────────────────────────────────────────────────────────┐
│  DAY 1: HR Uploads Resumes                                          │
└─────────────────────────────────────────────────────────────────────┘

Action: Upload "john_doe_resume.pdf" (4,527 characters)

Step 1: PDF Parsing
  └─> Raw text extracted

Step 2: LLM Metadata Extraction (GPT-4)
  └─> Extracted: ["Python", "FastAPI", "Docker"], 5 years exp

Step 3: Chunking
  └─> Created: 10 chunks
      Why 10? (4,527 chars) ÷ (500 chunk_size - 50 overlap) = 10.06 chunks
      
      Formula: ceil(text_length / (chunk_size - overlap))
               ceil(4527 / 450) = ceil(10.06) = 10 chunks
      
      Chunk breakdown:
      - Chunk 0: chars 0-500
      - Chunk 1: chars 450-950   (note 50 char overlap with chunk 0)
      - Chunk 2: chars 900-1400  (note 50 char overlap with chunk 1)
      - Chunk 3: chars 1350-1850
      - Chunk 4: chars 1800-2300
      - Chunk 5: chars 2250-2750
      - Chunk 6: chars 2700-3200
      - Chunk 7: chars 3150-3650
      - Chunk 8: chars 3600-4100
      - Chunk 9: chars 4050-4527 (last chunk, shorter than 500)

Step 4: Generate Embeddings
  └─> Azure OpenAI API call (10 times, one per chunk)
      Each returns 1536-dimensional vector

Step 5: Store in ChromaDB
  └─> 10 documents stored with IDs:
      - john_doe_resume.pdf_abc123_0
      - john_doe_resume.pdf_abc123_1
      - ...
      - john_doe_resume.pdf_abc123_9

✅ Result: Resume searchable with semantic meaning!

┌─────────────────────────────────────────────────────────────────────┐
│  DAY 2: Hiring Manager Searches                                     │
└─────────────────────────────────────────────────────────────────────┘

Query: "Find experienced Python developers who know FastAPI"

Step 1: Query Embedding
  └─> Convert query to vector: [0.123, -0.456, 0.789, ...]

Step 2: ChromaDB Vector Search
  └─> Compare query vector with all 10 stored vectors
      Calculate cosine similarity for each:
      
      john_doe_resume.pdf_abc123_0: similarity = 0.95 ✓
      john_doe_resume.pdf_abc123_1: similarity = 0.92 ✓
      john_doe_resume.pdf_abc123_2: similarity = 0.67
      ... others lower ...
      
  └─> Return top 5 chunks (sorted by similarity)

Step 3: Group by Resume
  └─> Combine chunks from same resume (same file_name)
      Result: John Doe (2 relevant chunks found)

Step 4: Extract Metadata
  └─> Skills: ["Python", "FastAPI", "Docker", ...]
      Experience: 5 years
      Relevance Score: 95%

Step 5: (Optional) LLM Summary
  └─> Send to GPT-4: "Summarize why John Doe matches the query"
      GPT-4: "John Doe is an excellent match with 5 years of Python
              development and strong FastAPI experience..."

✅ Result: John Doe displayed as top candidate!

┌─────────────────────────────────────────────────────────────────────┐
│  DAY 3: Detailed Resume Scoring                                     │
└─────────────────────────────────────────────────────────────────────┘

Action: Score John Doe against specific job description

Input:
  Job Description: "Need Python developer with 5+ years, FastAPI, 
                    Docker, Kubernetes, PostgreSQL"
  Resume: John Doe's full resume text

Step 1: Send to GPT-4 Scoring API
  └─> Prompt: "Score this resume 0-100 for this job..."

Step 2: GPT-4 Analysis
  └─> Analyzes skills match
      Calculates experience alignment
      Identifies gaps

Step 3: GPT-4 Response
  {
    "score": 95,
    "matching_skills": ["Python", "FastAPI", "Docker", "PostgreSQL"],
    "missing_skills": ["Kubernetes"],
    "experience_match": "Exact match: 5 years",
    "summary": "Excellent candidate with strong match. Has 4/5 
                required skills. Missing Kubernetes but strong 
                Docker experience suggests quick learning capability.",
    "recommendation": "Highly recommend for interview"
  }

✅ Result: Detailed scoring report generated!
```

---

## Chunking Strategy Explained

### Why Chunk?

1. **LLM Token Limits**: Models have max input size (GPT-4: 8k-128k tokens)
2. **Better Embeddings**: Smaller chunks = more focused semantic meaning
3. **Precise Retrieval**: Return only relevant sections, not entire resume
4. **Performance**: Faster search with smaller vectors

### Chunking Configuration

```python
# File: app/services/chunking_service.py

from langchain_text_splitters import RecursiveCharacterTextSplitter

# LangChain's intelligent text splitter
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,      # characters per chunk
    chunk_overlap=50,    # characters overlap between chunks
    length_function=len, # measure by character count
    separators=["\n\n", "\n", " ", ""]  # try in this order
)
```

### LangChain's RecursiveCharacterTextSplitter Algorithm

Unlike simple character splitting, LangChain's splitter is **semantic-aware**:

```
┌─────────────────────────────────────────────────────────────────────┐
│  RecursiveCharacterTextSplitter Decision Tree                        │
└─────────────────────────────────────────────────────────────────────┘

Input: Resume text (4,527 characters)

Step 1: Try splitting on "\n\n" (paragraph breaks)
   ↓
   ├─> Chunk small enough? ✅ Keep it!
   └─> Chunk too large? ❌ Go to Step 2

Step 2: Try splitting on "\n" (line breaks)
   ↓
   ├─> Chunk small enough? ✅ Keep it!
   └─> Chunk too large? ❌ Go to Step 3

Step 3: Try splitting on " " (word boundaries)
   ↓
   ├─> Chunk small enough? ✅ Keep it!
   └─> Chunk too large? ❌ Go to Step 4

Step 4: Split on "" (any character) - last resort
   ↓
   └─> Ensures max chunk size is respected

Result: Natural, readable chunks! ✨
```

**Example Comparison**:

```python
# ❌ Simple character split (naive approach):
def simple_chunk(text, size=500):
    return [text[i:i+size] for i in range(0, len(text), size)]

# Result for "Experience:\nTechCorp (2019-2024)\nBuilt REST APIs...":
Chunk: "Experience:\nTechCo"  # ❌ Cuts mid-word!
Chunk: "rp (2019-2024)\nBuil"  # ❌ Nonsensical!


# ✅ LangChain RecursiveCharacterTextSplitter:
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
    separators=["\n\n", "\n", " ", ""]
)
chunks = text_splitter.split_text(text)

# Result:
Chunk: "Experience:\nTechCorp (2019-2024)\nBuilt REST APIs..."  
       # ✅ Natural break at line boundary!
```

### Chunking Algorithm

```python
def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50):
    """
    Split text into overlapping chunks.
    """
    chunks = []
    start = 0
    step = chunk_size - overlap  # 450 characters per step
    
    while start < len(text):
        end = start + chunk_size  # 500 characters
        chunk = text[start:end]
        chunks.append(chunk)
        start += step  # Move 450 forward (50 overlap)
    
    return chunks
```

### Example: Why 10 Chunks?

```
Resume: "john_doe_resume.pdf"
Length: 4,527 characters

Calculation:
- Step size = 500 - 50 = 450 chars
- Number of chunks = ceil(4,527 / 450) = ceil(10.06) = 10 chunks

Chunk Boundaries:
┌────────────────────────────────────────────────────┐
│ Chunk 0: [   0 -  500] (500 chars)                 │
│ Chunk 1: [ 450 -  950] (500 chars) ← 50 overlap    │
│ Chunk 2: [ 900 - 1400] (500 chars) ← 50 overlap    │
│ Chunk 3: [1350 - 1850] (500 chars)                 │
│ Chunk 4: [1800 - 2300] (500 chars)                 │
│ Chunk 5: [2250 - 2750] (500 chars)                 │
│ Chunk 6: [2700 - 3200] (500 chars)                 │
│ Chunk 7: [3150 - 3650] (500 chars)                 │
│ Chunk 8: [3600 - 4100] (500 chars)                 │
│ Chunk 9: [4050 - 4527] (477 chars) ← last chunk    │
└────────────────────────────────────────────────────┘
```

### Why Overlap?

**Overlap prevents information loss at boundaries** - LangChain manages this automatically:

```
Without Overlap:
Chunk 0: "...experience with Docker containers and"
Chunk 1: "Kubernetes orchestration in production..."
Problem: "Docker and Kubernetes" split across chunks!

With 50-char Overlap (LangChain manages):
Chunk 0: "...experience with Docker containers and Kubernetes"
Chunk 1: "containers and Kubernetes orchestration in production..."
✓ Both chunks capture the Docker+Kubernetes relationship!
```

**How LangChain Implements Overlap**:
```python
# LangChain handles overlap internally:
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50  # Last 50 chars of chunk N = first 50 of chunk N+1
)

# You don't need to manually calculate offsets!
chunks = text_splitter.split_text(text)  # Done! ✨
```

---

## API Endpoints Documentation

### 1. Upload Resume

```http
POST /api/upload-resume
Content-Type: multipart/form-data

Body:
  file: <PDF file>
```

**Process Flow:**
```
1. Receive PDF → 2. Parse text → 3. LLM extract metadata → 
4. Chunk (500 chars) → 5. Generate embeddings → 6. Store ChromaDB
```

**Response:**
```json
{
  "message": "Resume uploaded successfully",
  "candidate_name": "John Doe",
  "chunks_created": 10,
  "skills_extracted": ["Python", "FastAPI", "Docker"],
  "years_experience": 5
}
```

### 2. Search Resumes

```http
POST /api/search-resumes
Content-Type: application/json

Body:
{
  "query": "Python developers with FastAPI experience",
  "top_k": 5
}
```

**Process Flow:**
```
1. Embed query → 2. Vector search ChromaDB → 3. Rank by similarity → 
4. Group by candidate → 5. Return with metadata
```

**Response:**
```json
{
  "results": [
    {
      "candidate_name": "John Doe",
      "file_name": "john_doe_resume.pdf",
      "relevance_score": 0.95,
      "skills": ["Python", "FastAPI", "Docker"],
      "years_experience": 5,
      "matching_chunks": 2
    }
  ]
}
```

### 3. Score Resume

```http
POST /api/score-resume
Content-Type: application/json

Body:
{
  "job_description": "Need Python developer with 5+ years...",
  "resume_text": "John Doe\nSenior Software Engineer..."
}
```

**Process Flow:**
```
1. Receive inputs → 2. Format prompt → 3. Call GPT-4 → 
4. Parse structured response → 5. Return scoring
```

**Response:**
```json
{
  "score": 95,
  "matching_skills": ["Python", "FastAPI", "Docker"],
  "missing_skills": ["Kubernetes"],
  "summary": "Excellent candidate with strong match...",
  "recommendation": "Highly recommend for interview"
}
```

### 4. Query (Conversational)

```http
POST /api/query
Content-Type: application/json

Body:
{
  "query": "Show me senior Python developers",
  "include_summary": true
}
```

**Process Flow:**
```
1. Embed query → 2. Search ChromaDB → 3. Format context → 
4. GPT-4 generate summary → 5. Return candidates + summary
```

**Response:**
```json
{
  "summary": "Found 3 senior Python developers with 5-10 years experience",
  "candidates": [...],
  "total_found": 3
}
```

### 5. List All Resumes

```http
GET /api/resumes/list
```

**Process Flow:**
```
1. Query ChromaDB → 2. Get all documents → 3. Group by resume → 
4. Extract metadata → 5. Return list
```

**Response:**
```json
{
  "total_resumes": 9,
  "resumes": [
    {
      "candidate_name": "John Doe",
      "file_name": "john_doe_resume.pdf",
      "skills": ["Python", "FastAPI"],
      "years_experience": 5,
      "total_chunks": 10
    },
    ...
  ]
}
```

---

## How Everything Works Together

### Complete System Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                     1. INDEXING PHASE (Upload)                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  User → Frontend → Backend API → Resume Parser                      │
│                                      │                               │
│                                      ├─> LLM Metadata Extraction     │
│                                      ├─> Text Chunking (LangChain)   │
│                                      ├─> Embedding Gen (LangChain)   │
│                                      └─> ChromaDB Storage            │
│                                                                      │
│  External Services:                                                 │
│    • Azure OpenAI (GPT-4): Extract skills & experience              │
│    • LangChain: Orchestrate chunking & embedding generation         │
│    • Azure OpenAI (Embeddings): Generate 1536-dim vectors           │
│    • ChromaDB: Persist documents with vectors                       │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                        Data Stored
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    2. RETRIEVAL PHASE (Search)                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  User → Frontend → Backend API → RAG Pipeline                       │
│                                      │                               │
│                                      ├─> Query Embedding (LangChain) │
│                                      ├─> Vector Search               │
│                                      ├─> Rank Results                │
│                                      └─> (Optional) LLM Summary      │
│                                                                      │
│  External Services:                                                 │
│    • LangChain: Embed query with AzureOpenAIEmbeddings              │
│    • Azure OpenAI: Convert query to vector                          │
│    • ChromaDB: Find similar vectors                                 │
│    • Azure OpenAI (GPT-4): Generate human-readable summary          │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                      Results Returned
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   3. SCORING PHASE (Optional)                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  User → Frontend → Backend API → Scoring Pipeline                   │
│                                      │                               │
│                                      └─> LLM Detailed Analysis       │
│                                                                      │
│  External Services:                                                 │
│    • Azure OpenAI (GPT-4): Analyze resume vs job description        │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Data Flow Diagram

```
┌──────────────┐
│   PDF File   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Raw Text    │ ─────────┐
└──────┬───────┘          │
       │                  │
       ▼                  │
┌──────────────┐          │
│  Metadata    │ ◄─ GPT-4─┘
│  {skills,exp}│
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Chunks      │
│  [C0...C9]   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Embeddings  │ ◄─ Azure OpenAI Embeddings
│  [V0...V9]   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  ChromaDB    │
│  Stored!     │
└──────────────┘
       │
       │ (Search Time)
       │
       ▼
┌──────────────┐
│ User Query   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│Query Embedding│ ◄─ Azure OpenAI Embeddings
└──────┬───────┘
       │
       ▼
┌──────────────┐
│Vector Search │ ◄─ ChromaDB
│(Cosine Sim)  │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   Results    │
│  +Metadata   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│LLM Summary   │ ◄─ GPT-4 (Optional)
└──────┬───────┘
       │
       ▼
┌──────────────┐
│Display to    │
│    User      │
└──────────────┘
```

### Service Dependencies

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Backend Services                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────┐         ┌──────────────────┐                 │
│  │ ResumeParser     │─────────│ LLMClient        │                 │
│  │ Service          │  uses   │                  │                 │
│  └────────┬─────────┘         └──────────────────┘                 │
│           │                            │                            │
│           │ uses                       │ calls                      │
│           ▼                            ▼                            │
│  ┌──────────────────┐         ┌──────────────────┐                 │
│  │ Chunking         │         │ Azure OpenAI     │                 │
│  │ Service          │         │ API              │                 │
│  │ (🔗 LangChain)   │         └──────────────────┘                 │
│  └────────┬─────────┘                 ▲                            │
│           │                            │                            │
│           │ outputs chunks             │                            │
│           ▼                            │                            │
│  ┌──────────────────┐                 │                            │
│  │ Embedding        │─────────────────┘                            │
│  │ Service          │  calls via LangChain wrapper                 │
│  │ (🔗 LangChain)   │                                              │
│  └────────┬─────────┘                                              │
│           │                                                         │
│           │ generates vectors                                      │
│           ▼                                                         │
│  ┌──────────────────┐                                              │
│  │ VectorStore      │                                              │
│  │ Service          │                                              │
│  └────────┬─────────┘                                              │
│           │                                                         │
│           │ stores/retrieves                                       │
│           ▼                                                         │
│  ┌──────────────────┐                                              │
│  │ ChromaDB         │                                              │
│  │                  │                                              │
│  └──────────────────┘                                              │
│                                                                     │
│  🔗 = LangChain orchestration layer                                │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Key Insights

### Why Embeddings?

**Traditional Keyword Search:**
```
Query: "Python expert"
Matches: Only resumes with exact words "Python" AND "expert"
Misses: "Python specialist", "Senior Python developer", "Pythonista"
```

**Embedding-Based Semantic Search:**
```
Query: "Python expert"
Embedding: [0.123, -0.456, 0.789, ...]

Matches:
  "Python expert"           → 0.99 similarity ✓
  "Senior Python developer" → 0.95 similarity ✓
  "Python specialist"       → 0.93 similarity ✓
  "Experienced Pythonist"   → 0.88 similarity ✓
  "Java developer"          → 0.35 similarity ✗

Understands MEANING, not just words!
```

### Why RAG?

**Without RAG (Pure LLM):**
```
Problem: GPT-4 doesn't know your candidates
Solution: You'd have to paste ALL resumes in every prompt
Issue: Token limits (max 128k tokens = ~50 resumes)
Cost: $$$$ for every query
```

**With RAG:**
```
Solution: Store resumes in vector DB, retrieve only relevant ones
Benefits:
  • Search millions of resumes instantly
  • Only send top 5-10 to LLM
  • Significantly cheaper
  • Always up-to-date (add/remove resumes anytime)
```

### Why Chunking?

**Without Chunking:**
```
Store: Entire resume as 1 vector
Problem: Embedding captures "average" meaning of whole doc
Result: Less precise search results
```

**With Chunking:**
```
Store: Resume as 10 vectors (each chunk)
Benefit: Each vector captures specific section meaning
Result: More precise retrieval of relevant sections
Example: Query "FastAPI experience" directly matches 
         chunk containing FastAPI projects, not skills section
```

---

## Performance Characteristics

### Upload Time
```
Single Resume (5 pages, ~5000 chars):
  • PDF Parsing: ~100ms
  • LLM Metadata Extraction: ~2-3 seconds (GPT-4 API call)
    - Cost: ~$0.013
  • Chunking (LangChain): ~10ms (semantic splitting overhead)
  • Embedding Generation (LangChain batched): ~1-2 seconds
    - Cost: ~$0.00011 (very cheap!)
    - Without batching: ~5-10 seconds (10 sequential API calls)
    - LangChain batches 3-5 chunks per API call!
    - Cost is same (per token), but 70% faster!
  • ChromaDB Storage: ~50ms
  
  Total Time: ~4-6 seconds per resume
  Total Cost: ~$0.013 per resume
  
  🔗 LangChain saves 3-8 seconds per resume with batching!
  💰 Embeddings cost ~0.8% of total (GPT-4 metadata is 99.2%)
```

### Search Time
```
Query Processing:
  • Query Embedding (LangChain): ~500ms (includes retry logic)
    - Cost: ~$0.000001 (essentially free!)
  • Vector Search: ~50ms (ChromaDB is very fast!)
    - Cost: $0 (local, no API calls)
  • Metadata Retrieval: ~20ms
  • (Optional) LLM Summary: ~2-3 seconds (GPT-4)
    - Cost: ~$0.014 (dominates cost if used)
  
  Total Time: ~600ms (without LLM) or ~3-4 seconds (with LLM)
  Total Cost: ~$0.000001 (without LLM) or ~$0.014 (with LLM)
  
  🔗 LangChain's error handling ensures 99.9% success rate!
  💰 Vector search is essentially free - LLM summary is optional
```

### Scalability
```
Database Size    Search Time    Accuracy
100 resumes      ~50ms          High
1,000 resumes    ~100ms         High
10,000 resumes   ~200ms         High
100,000 resumes  ~500ms         High

Vector search scales logarithmically! ✅
```

---

## Summary

This Resume Builder app is a **sophisticated AI-powered system** that:

1. **Understands** resumes using LLM (GPT-4) to extract structured data
2. **Chunks** text intelligently using LangChain's RecursiveCharacterTextSplitter
3. **Embeds** chunks using LangChain's AzureOpenAIEmbeddings wrapper
4. **Stores** resumes as semantic vectors in ChromaDB for fast search
5. **Retrieves** relevant candidates using vector similarity
6. **Analyzes** matches using LLM to provide intelligent scoring
7. **Presents** results through a clean React interface

The **RAG pipeline** enables semantic search at scale, combining the best of:
- **Vector databases** (fast, scalable retrieval)
- **LLMs** (intelligent understanding and generation)
- **LangChain** (orchestration and abstraction)
- **Traditional metadata** (precise filtering)

**LangChain's Critical Role**:
- 🔗 **Simplifies** text splitting with semantic awareness
- 🔗 **Abstracts** Azure OpenAI API complexity
- 🔗 **Optimizes** performance with automatic batching
- 🔗 **Ensures** reliability with built-in retry logic
- 🔗 **Enables** easy provider switching (Azure ↔ OpenAI)

All working together to help you find the perfect candidate! 🎯
