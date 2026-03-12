# Agent Flow Explained: Tool Selection & Orchestration

## Overview

This document explains **exactly** how your LangChain Agent decides which tools to call, how many times it can call tools, and how the complete orchestration flow works.

---

## Quick Answer to Your Questions

### Q1: Based on LLM response, how do we call a tool?
**Answer**: The LLM returns a **function call** in its response (using OpenAI's function calling feature). LangChain's agent automatically detects this and executes the specified tool.

### Q2: If another tool is needed, will we call it again?
**Answer**: **YES!** The agent can make **multiple tool calls** in sequence (up to `max_iterations=5` by default). It follows this pattern:
1. LLM decides: "I need tool A"
2. Execute tool A → Get result
3. LLM sees result, decides: "I need tool B too"
4. Execute tool B → Get result
5. LLM generates final answer

### Q3: Or only one call to tool is made?
**Answer**: **Multiple calls are possible!** The agent can iterate up to 5 times (configurable). Each iteration can call a different tool or the same tool with different parameters.

---

## Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          USER SENDS QUERY                                │
│                "How many Python developers are there?"                   │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 1: FastAPI Endpoint (/chat)                                       │
│  File: routes_query.py                                                   │
├─────────────────────────────────────────────────────────────────────────┤
│  async def chat(request, agent):                                         │
│      # Convert chat history to LangChain format                          │
│      chat_history = [(msg.role, msg.content) for msg in history]        │
│                                                                          │
│      # Call agent - THIS IS WHERE THE MAGIC HAPPENS                      │
│      result = await agent.process_query(                                 │
│          query=request.message,                                          │
│          chat_history=chat_history                                       │
│      )                                                                   │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 2: Agent Receives Query                                            │
│  File: recruitment_agent.py                                              │
├─────────────────────────────────────────────────────────────────────────┤
│  async def process_query(self, query, chat_history):                    │
│      agent_input = {                                                     │
│          "input": query,                                                 │
│          "chat_history": chat_history                                    │
│      }                                                                   │
│                                                                          │
│      # CRITICAL LINE: Agent executor starts autonomous loop              │
│      result = await self.agent_executor.ainvoke(agent_input)            │
│      #                    ▲                                              │
│      #                    │                                              │
│      #         This is where the LOOP happens!                           │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 3: AgentExecutor Loop (ITERATION 1)                                │
│  Component: LangChain's AgentExecutor                                    │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────────────────────┐         │
│  │ 3.1: Send to LLM (OpenAI Function Calling)                 │         │
│  ├────────────────────────────────────────────────────────────┤         │
│  │ System Prompt:                                             │         │
│  │   "You are an intelligent recruitment assistant.           │         │
│  │    You have access to these tools:                         │         │
│  │    - list_all_candidates: List ALL candidates              │         │
│  │    - search_candidates: Search by skills                   │         │
│  │    - get_candidate_details: Get full resume"               │         │
│  │                                                             │         │
│  │ User Query: "How many Python developers are there?"        │         │
│  │                                                             │         │
│  │ Available Functions (sent to OpenAI):                      │         │
│  │   {                                                         │         │
│  │     "name": "search_candidates",                           │         │
│  │     "description": "Search for candidates who match..."    │         │
│  │     "parameters": {"query": "string"}                      │         │
│  │   }                                                         │         │
│  └────────────────────────────────────────────────────────────┘         │
│                                                                          │
│                              ▼                                           │
│  ┌────────────────────────────────────────────────────────────┐         │
│  │ 3.2: LLM Decides (OpenAI Response)                         │         │
│  ├────────────────────────────────────────────────────────────┤         │
│  │ LLM Analysis:                                              │         │
│  │   "User wants Python developers with count.                │         │
│  │    I should search for 'Python developers' first."         │         │
│  │                                                             │         │
│  │ LLM Response (function call format):                       │         │
│  │   {                                                         │         │
│  │     "function_call": {                                     │         │
│  │       "name": "search_candidates",                         │         │
│  │       "arguments": "{\"query\": \"Python developers\"}"    │         │
│  │     }                                                       │         │
│  │   }                                                         │         │
│  └────────────────────────────────────────────────────────────┘         │
│                                                                          │
│                              ▼                                           │
│  ┌────────────────────────────────────────────────────────────┐         │
│  │ 3.3: Agent Detects Function Call                           │         │
│  ├────────────────────────────────────────────────────────────┤         │
│  │ AgentExecutor sees: "LLM wants to call search_candidates"  │         │
│  │                                                             │         │
│  │ AgentExecutor finds tool: search_candidates                │         │
│  └────────────────────────────────────────────────────────────┘         │
│                                                                          │
│                              ▼                                           │
│  ┌────────────────────────────────────────────────────────────┐         │
│  │ 3.4: Execute Tool                                          │         │
│  ├────────────────────────────────────────────────────────────┤         │
│  │ File: tools.py                                             │         │
│  │                                                             │         │
│  │ async def search_candidates(query):                        │         │
│  │     results = await retrieval_pipeline.search_resumes(     │         │
│  │         query="Python developers",                         │         │
│  │         top_k=5                                             │         │
│  │     )                                                       │         │
│  │     return format_results(results)  # Returns string       │         │
│  │                                                             │         │
│  │ Tool Result:                                               │         │
│  │   "Found 3 matching candidates:                            │         │
│  │    1. John Doe - 5 years Python, Django...                 │         │
│  │    2. Jane Smith - 3 years Python, Flask...                │         │
│  │    3. Bob Wilson - 7 years Python, FastAPI..."             │         │
│  └────────────────────────────────────────────────────────────┘         │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 4: AgentExecutor Loop (ITERATION 2 - Optional)                    │
│  Component: LangChain's AgentExecutor                                    │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────────────────────┐         │
│  │ 4.1: Send Tool Result Back to LLM                          │         │
│  ├────────────────────────────────────────────────────────────┤         │
│  │ Updated Context for LLM:                                   │         │
│  │   System: "You are a recruitment assistant..."             │         │
│  │   User: "How many Python developers are there?"            │         │
│  │   Assistant: [Called search_candidates]                    │         │
│  │   Tool Result: "Found 3 matching candidates: ..."          │         │
│  │                                                             │         │
│  │ Question to LLM: "What do you want to do next?"            │         │
│  └────────────────────────────────────────────────────────────┘         │
│                                                                          │
│                              ▼                                           │
│  ┌────────────────────────────────────────────────────────────┐         │
│  │ 4.2: LLM Decides Next Action                               │         │
│  ├────────────────────────────────────────────────────────────┤         │
│  │ Option A: LLM calls another tool                           │         │
│  │   {                                                         │         │
│  │     "function_call": {                                     │         │
│  │       "name": "get_candidate_details",                     │         │
│  │       "arguments": "{\"file_name\": \"john_doe.pdf\"}"     │         │
│  │     }                                                       │         │
│  │   }                                                         │         │
│  │   → Loop continues (ITERATION 3)                            │         │
│  │                                                             │         │
│  │ Option B: LLM generates final answer (NO function call)    │         │
│  │   {                                                         │         │
│  │     "content": "I found 3 Python developers in the         │         │
│  │                database: John Doe (5 years), ..."          │         │
│  │   }                                                         │         │
│  │   → Loop STOPS, return response                             │         │
│  └────────────────────────────────────────────────────────────┘         │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 5: Return Final Response                                           │
│  File: recruitment_agent.py                                              │
├─────────────────────────────────────────────────────────────────────────┤
│  return {                                                                │
│      "response": "I found 3 Python developers in the database...",      │
│      "tools_used": ["search_candidates"],                               │
│      "success": True                                                     │
│  }                                                                       │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 6: FastAPI Returns to User                                         │
│  File: routes_query.py                                                   │
├─────────────────────────────────────────────────────────────────────────┤
│  return ChatResponse(                                                    │
│      response=result["response"],                                        │
│      tools_used=result["tools_used"]                                     │
│  )                                                                       │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Real Code Flow with Annotations

### 1. Entry Point: `/chat` Endpoint

```python
# File: routes_query.py

@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    agent: RecruitmentAgent = Depends(get_recruitment_agent)  # ← Agent injected
):
    """AI Agent decides which tool to call autonomously."""
    
    # Convert chat history to LangChain format
    chat_history = []
    if request.chat_history:
        for msg in request.chat_history:
            role = "human" if msg.role == "user" else "ai"
            chat_history.append((role, msg.content))
    
    # 🚀 MAIN CALL: Agent processes query autonomously
    result = await agent.process_query(
        query=request.message,
        chat_history=chat_history
    )
    # ↑ This ONE call can trigger MULTIPLE tool executions!
    
    return ChatResponse(
        response=result["response"],
        tools_used=result.get("tools_used", [])  # ← Shows which tools were used
    )
```

### 2. Agent Processing: The Loop

```python
# File: recruitment_agent.py

class RecruitmentAgent:
    def __init__(self, llm_client, tools, max_iterations=5, verbose=False):
        # Create agent with OpenAI function calling
        self.agent = create_openai_functions_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=self.prompt
        )
        
        # Create executor with max iterations
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            max_iterations=5,  # ← Agent can loop up to 5 times!
            verbose=verbose,   # ← Set True to see each iteration
            handle_parsing_errors=True,
            return_intermediate_steps=False
        )
    
    async def process_query(self, query: str, chat_history=None):
        """Main entry point - handles ENTIRE loop internally."""
        
        # Prepare input
        agent_input = {
            "input": query,
            "chat_history": chat_history or []
        }
        
        # 🔄 THE LOOP HAPPENS HERE (inside ainvoke):
        # - Iteration 1: LLM decides tool → Execute tool
        # - Iteration 2: LLM sees result, decides next action → Execute or finish
        # - Iteration 3-5: Continue until LLM generates final answer
        result = await self.agent_executor.ainvoke(agent_input)
        
        return {
            "response": result.get("output", ""),
            "tools_used": self._extract_tools_used(result),
            "success": True
        }
```

### 3. Tool Execution: What Happens Inside

```python
# File: tools.py

def create_search_candidates_tool(retrieval_pipeline) -> Tool:
    """Creates a tool that the agent can call."""
    
    async def search_candidates(query: str) -> str:
        """This function is called by the agent when it decides to search."""
        
        logger.info(f"🔧 Tool executed: search_candidates(query='{query}')")
        
        # Execute actual search in database
        results = await retrieval_pipeline.search_resumes(query=query, top_k=5)
        
        # Format results as string (LLM will read this)
        output = f"Found {len(results)} matching candidates:\n\n"
        for candidate in results:
            output += f"- {candidate.candidate_name}: {candidate.skills}\n"
        
        logger.info(f"✅ Tool returned: {len(results)} candidates")
        
        return output  # ← This goes back to the LLM
    
    # Return Tool wrapper (makes function available to agent)
    return Tool(
        name="search_candidates",
        func=search_candidates,
        description="Search for candidates who match specific skills...",  # ← LLM reads this
        coroutine=search_candidates  # Mark as async
    )
```

---

## Example: Multi-Tool Call Scenario

### User Query: "Find Python developers with 5+ years and show me the best one's full resume"

```
📍 ITERATION 1:
┌─────────────────────────────────────────────────────────┐
│ LLM Reasoning:                                          │
│   "User wants Python developers with 5+ years.         │
│    I should search first."                              │
├─────────────────────────────────────────────────────────┤
│ LLM Action: CALL TOOL                                   │
│   Tool: search_candidates                               │
│   Args: {"query": "Python developers 5+ years"}        │
└─────────────────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────────────────┐
│ Tool Execution:                                         │
│   search_candidates("Python developers 5+ years")      │
├─────────────────────────────────────────────────────────┤
│ Tool Result:                                            │
│   "Found 3 matching candidates:                         │
│    1. John Doe (john_doe.pdf) - 7 years Python          │
│    2. Jane Smith (jane.pdf) - 5 years Python            │
│    3. Bob Wilson (bob.pdf) - 6 years Python"            │
└─────────────────────────────────────────────────────────┘

📍 ITERATION 2:
┌─────────────────────────────────────────────────────────┐
│ LLM Reasoning:                                          │
│   "I found 3 candidates. User asked for 'best one'.    │
│    John Doe has most experience (7 years).             │
│    User wants full resume - I should call              │
│    get_candidate_details for john_doe.pdf."            │
├─────────────────────────────────────────────────────────┤
│ LLM Action: CALL TOOL                                   │
│   Tool: get_candidate_details                           │
│   Args: {"file_name": "john_doe.pdf"}                  │
└─────────────────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────────────────┐
│ Tool Execution:                                         │
│   get_candidate_details("john_doe.pdf")                │
├─────────────────────────────────────────────────────────┤
│ Tool Result:                                            │
│   "JOHN DOE                                             │
│    Email: john@example.com                              │
│    Experience: 7 years Python development               │
│    Skills: Python, Django, PostgreSQL, AWS...           │
│    [Full resume text...]"                               │
└─────────────────────────────────────────────────────────┘

📍 ITERATION 3:
┌─────────────────────────────────────────────────────────┐
│ LLM Reasoning:                                          │
│   "I have all the information needed. Time to           │
│    generate final answer for the user."                 │
├─────────────────────────────────────────────────────────┤
│ LLM Action: FINISH (NO TOOL CALL)                       │
│   Content: "I found 3 Python developers with 5+ years  │
│             experience. John Doe has the most           │
│             experience (7 years). Here's his full       │
│             resume: [resume details]..."                │
└─────────────────────────────────────────────────────────┘

✅ FINAL RESPONSE:
{
  "response": "I found 3 Python developers...",
  "tools_used": ["search_candidates", "get_candidate_details"],
  "success": true
}
```

---

## How the LLM Decides Which Tool to Call

### OpenAI Function Calling Format

When you call the LLM, LangChain sends this structure:

```json
{
  "messages": [
    {
      "role": "system",
      "content": "You are an intelligent recruitment assistant..."
    },
    {
      "role": "user",
      "content": "How many Python developers are there?"
    }
  ],
  "functions": [
    {
      "name": "search_candidates",
      "description": "Search for candidates who match specific skills or experience",
      "parameters": {
        "type": "object",
        "properties": {
          "query": {
            "type": "string",
            "description": "Natural language search query"
          }
        },
        "required": ["query"]
      }
    },
    {
      "name": "list_all_candidates",
      "description": "List ALL candidates in database - use when user asks 'how many' or 'list all'",
      "parameters": {
        "type": "object",
        "properties": {}
      }
    }
  ]
}
```

### LLM Response Options

**Option A: Call a tool (function call)**
```json
{
  "role": "assistant",
  "content": null,
  "function_call": {
    "name": "search_candidates",
    "arguments": "{\"query\": \"Python developers\"}"
  }
}
```
→ Agent detects function_call → Executes tool → Loop continues

**Option B: Finish with answer (no function call)**
```json
{
  "role": "assistant",
  "content": "I found 3 Python developers in the database...",
  "function_call": null
}
```
→ Agent detects no function_call → Loop ends → Return final response

---

## Key Configuration: `max_iterations`

```python
# File: recruitment_agent.py

self.agent_executor = AgentExecutor(
    agent=self.agent,
    tools=self.tools,
    max_iterations=5,  # ← Maximum tool calls allowed
    verbose=False
)
```

### What Happens at Each Value?

| `max_iterations` | Behavior |
|------------------|----------|
| `1` | Agent can call **ONE tool only**, then must finish |
| `3` | Agent can call up to **3 tools** (e.g., search → get_details → list_all) |
| `5` (default) | Agent can call up to **5 tools** - good for complex queries |
| `10` | Agent can call up to **10 tools** - rarely needed, increases latency |

### Real Iteration Examples

**Query: "Find Python developers"**
- Iteration 1: Call `search_candidates("Python developers")` → Done (1 tool call)

**Query: "Find Python devs and show me John's resume"**
- Iteration 1: Call `search_candidates("Python developers")` → Get results
- Iteration 2: Call `get_candidate_details("john_doe.pdf")` → Done (2 tool calls)

**Query: "How many candidates are there and who has Python skills?"**
- Iteration 1: Call `list_all_candidates()` → Get all 9 candidates
- Iteration 2: Call `search_candidates("Python skills")` → Get Python devs
- Iteration 3: Generate answer combining both results → Done (2 tool calls)

---

## Verbose Mode: See the Magic Happen

```python
# File: dependencies.py

def get_recruitment_agent() -> RecruitmentAgent:
    return RecruitmentAgent(
        llm_client=llm_client,
        tools=tools,
        verbose=True  # ← Enable to see agent reasoning!
    )
```

### Output with `verbose=True`:

```
[Agent] Entering agent executor chain...
[Agent] User: "How many Python developers are there?"

[Agent] Iteration 1:
[Agent] - LLM thinking...
[Agent] - LLM response: CALL TOOL search_candidates
[Agent] - Arguments: {"query": "Python developers"}
[Agent] - Executing tool: search_candidates
[Agent] - Tool result: "Found 3 matching candidates: John Doe..."

[Agent] Iteration 2:
[Agent] - LLM thinking with tool result...
[Agent] - LLM response: FINISH
[Agent] - Final answer: "I found 3 Python developers in the database..."

[Agent] Exiting agent executor chain.
[Agent] Total tool calls: 1
[Agent] Tools used: ['search_candidates']
```

---

## Summary: Key Takeaways

### 1. ✅ Multiple Tool Calls ARE Possible
The agent can call multiple tools in sequence (up to `max_iterations=5`). Each iteration:
1. LLM decides what to do next
2. Calls a tool OR generates final answer
3. If tool called → Loop continues with tool result
4. If final answer → Loop stops

### 2. 🤖 LLM Decides Autonomously
No manual routing! The LLM uses:
- System prompt (guidelines)
- Tool descriptions (what each tool does)
- User query (intent)
- Previous tool results (context)
→ Decides best action autonomously using OpenAI function calling

### 3. 🔄 The Loop is Automatic
You call `agent.process_query()` ONCE.
Inside, AgentExecutor handles ENTIRE loop:
```python
result = await agent.process_query("your query")
# ↑ This ONE call can trigger 1-5 tool executions!
```

### 4. 🎯 When Does the Loop Stop?
- LLM generates text response (no function call)
- OR `max_iterations` reached (safety limit)
- OR error occurs

### 5. 📊 Tracking Tool Usage
```python
result = await agent.process_query("find Python devs")
print(result["tools_used"])
# Output: ["search_candidates"]

result = await agent.process_query("find Python devs and show John's resume")
print(result["tools_used"])
# Output: ["search_candidates", "get_candidate_details"]
```

---

## Comparison: Your Agent vs Manual Routing

### Old System (Keywords)
```python
# Manual routing - ONE tool per query
if "list all" in query:
    call_list_all_tool()
elif "search" in query:
    call_search_tool()
else:
    generic_response()  # Hallucination risk!
```
**Limitations:**
- ❌ Only ONE tool per query
- ❌ Can't combine tools
- ❌ Brittle keyword matching

### New System (Agent)
```python
# Agent decides - MULTIPLE tools possible
result = await agent.process_query(query)
# Agent can:
# 1. Call search_candidates
# 2. See results
# 3. Call get_candidate_details for best match
# 4. Generate comprehensive answer
```
**Benefits:**
- ✅ Multiple tools in sequence
- ✅ Intelligent chaining
- ✅ Natural language understanding

---

## Testing Multi-Tool Scenarios

### Test Case 1: Single Tool
```
User: "List all candidates"
Expected Flow:
  1. LLM: Call list_all_candidates
  2. LLM: Generate answer
Tools Used: ["list_all_candidates"]
```

### Test Case 2: Two Tools
```
User: "Find Java developers and show me the top candidate's resume"
Expected Flow:
  1. LLM: Call search_candidates("Java")
  2. LLM: Identifies top candidate (e.g., john_doe.pdf)
  3. LLM: Call get_candidate_details("john_doe.pdf")
  4. LLM: Generate answer with resume details
Tools Used: ["search_candidates", "get_candidate_details"]
```

### Test Case 3: Complex Query
```
User: "How many candidates do we have and which ones know Python?"
Expected Flow:
  1. LLM: Call list_all_candidates (to count)
  2. LLM: Call search_candidates("Python")
  3. LLM: Generate answer: "We have 9 candidates total, 3 know Python..."
Tools Used: ["list_all_candidates", "search_candidates"]
```

---

## Debugging Tips

### 1. Enable Verbose Mode
```python
agent = RecruitmentAgent(llm_client, tools, verbose=True)
```
See each iteration in console output.

### 2. Check Tools Used
```python
result = await agent.process_query("your query")
print(f"Tools called: {result['tools_used']}")
```

### 3. Increase Max Iterations (if needed)
```python
agent = RecruitmentAgent(llm_client, tools, max_iterations=10)
```
For very complex queries requiring many tools.

### 4. Review Agent Prompt
```python
# File: recruitment_agent.py
def _create_agent_prompt(self):
    system_message = """
    ...
    Guidelines:
    1. When users ask about counting or listing ALL candidates, 
       use the list_all_candidates tool  # ← Guides LLM decision
    ...
    """
```
Tweak guidelines to improve tool selection.

---

## Cost Implications

### Token Usage per Query

**Simple Query (1 tool call):**
```
Iteration 1: ~500 tokens (query + tool descriptions)
Iteration 2: ~300 tokens (tool result + final answer)
Total: ~800 tokens
```

**Complex Query (3 tool calls):**
```
Iteration 1: ~500 tokens
Iteration 2: ~400 tokens (+ first tool result)
Iteration 3: ~400 tokens (+ second tool result)
Iteration 4: ~300 tokens (+ third tool result + final answer)
Total: ~1600 tokens
```

**Cost: ~$0.002 per complex query** (with GPT-4)

---

## Conclusion

Your LangChain Agent implements a **fully autonomous loop** that:
1. ✅ Can call **multiple tools** in sequence (not just one)
2. ✅ **LLM decides** which tools to use (no manual routing)
3. ✅ **Iterates automatically** until answer is complete
4. ✅ **Tracks tools used** for transparency
5. ✅ **Handles errors** gracefully with retry logic

You call `agent.process_query()` **once**, and the agent handles the entire multi-step workflow internally! 🎉
