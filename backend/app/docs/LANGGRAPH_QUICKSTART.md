# LangGraph Quick Reference

## Installation

```bash
cd backend
pip install -r requirements.txt
```

## Basic Usage

```python
from app.agents.recruitment_agent import RecruitmentAgent

agent = RecruitmentAgent(
    llm_client=llm_client,
    tools=tools,
    max_iterations=5,
    verbose=True
)

result = await agent.process_query("Find Python developers")
print(result["response"])
```

## Workflow Graph

```
START → Reasoning → [Tool?] → Tool Execution → [Continue?] → END
                      ↓                          ↓
                    Response ──────────────────> END
```

## Key Files

- **`graph_state.py`** - State schema (AgentState)
- **`graph_nodes.py`** - Node implementations (Reasoning, Tool Execution, Response)
- **`workflow.py`** - Workflow definition and compilation
- **`recruitment_agent.py`** - Main agent orchestrator

## State Object

```python
AgentState = {
    "user_question": str,
    "chat_history": List[tuple[str, str]],
    "needs_tool": bool,
    "tool_name": Optional[str],
    "tool_arguments": Optional[Dict],
    "tool_result": Optional[str],
    "tool_calls_made": List[str],
    "final_answer": Optional[str],
    "error": Optional[str],
    "iteration_count": int,
    "max_iterations": int
}
```

## Adding a New Node

```python
# 1. Define node in graph_nodes.py
async def my_new_node(self, state: AgentState) -> AgentState:
    # Process state
    state["my_result"] = await do_something()
    return state

# 2. Add to workflow in workflow.py
workflow.add_node("my_node", nodes.my_new_node)
workflow.add_edge("some_node", "my_node")
workflow.add_edge("my_node", "next_node")

# 3. Update state schema in graph_state.py
class AgentState(TypedDict):
    # ... existing fields ...
    my_result: Optional[str]
```

## Adding a New Tool

```python
# 1. Create tool in tools.py
def create_my_tool(retrieval_pipeline):
    async def my_tool(arg: str) -> str:
        return f"Result for {arg}"
    
    return Tool(
        name="my_tool",
        func=my_tool,
        description="Does something useful",
        coroutine=my_tool
    )

# 2. Register tool
tools = [
    create_search_candidates_tool(retrieval_pipeline),
    create_my_tool(retrieval_pipeline)  # Add here
]

# 3. Agent will automatically use it!
```

## Debugging

```python
# Enable verbose logging
agent = RecruitmentAgent(verbose=True)

# Logs show:
# [ReasoningNode] LLM analyzing query
# [ReasoningNode] LLM decided to call tool: search_candidates
# [ToolExecutionNode] Executing tool: search_candidates
# [Agent] Workflow completed. Tools used: ['search_candidates']

# Inspect final state
final_state = await workflow.ainvoke(initial_state)
print(final_state)
```

## Testing

```bash
# Run example
python example_langgraph_agent.py

# Start server
python -m uvicorn app.main:app --reload

# Test API
curl -X POST http://localhost:8000/query/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Find Python developers", "chat_history": []}'
```

## Common Issues

**Max iterations reached:**
```python
agent = RecruitmentAgent(max_iterations=10)  # Increase limit
```

**Tool not found:**
```python
tools = [tool1, tool2, tool3]  # Ensure tool is in list
```

**LLM not calling tools:**
- Check tool descriptions are clear
- Enable verbose mode
- Verify tool schemas

## Performance

- Simple query: ~1-2s
- With tools: ~3-4s
- Multiple tools: ~5-8s

## Documentation

- **Full docs:** `LANGGRAPH_ARCHITECTURE.md`
- **Migration guide:** `MIGRATION_GUIDE.md`
- **Comparison:** `BEFORE_AFTER_COMPARISON.md`
- **Example:** `example_langgraph_agent.py`

## API Response Format

```json
{
  "message": "Find Python developers",
  "response": "I found 3 Python developers...",
  "data": {
    "agent_tools_used": ["search_candidates"]
  }
}
```

## Workflow Nodes

1. **Reasoning Node**: LLM decides action
2. **Tool Execution Node**: Executes tools
3. **Response Generation Node**: Generates final answer

## Conditional Routing

- **should_use_tool**: Reasoning → Tool or Response
- **should_continue_loop**: Tool → Reasoning or END

## Benefits

✅ Structured workflow
✅ Easy debugging
✅ Modular design
✅ Production-ready
✅ Backward compatible

## Next Steps

1. Test the `/chat` endpoint
2. Run example: `python example_langgraph_agent.py`
3. Read full docs: `LANGGRAPH_ARCHITECTURE.md`
4. Add custom nodes for your needs
5. Deploy!
