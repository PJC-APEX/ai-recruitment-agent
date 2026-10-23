"""LangGraph workflow definition for recruitment agent.

This module creates and configures the agent workflow graph.
The graph implements a structured, stateful workflow instead of a simple loop.

Workflow Structure:
    START → Reasoning → Tool Decision → [Tool Execution → Reasoning] → Response Generation → END
    
Key Benefits:
- No uncontrolled loops - structured flow through graph
- Explicit state management
- Easy to visualize and debug
- Modular - easy to add new nodes
- Follows SOLID principles
"""

import logging
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from app.agents.graph_state import AgentState
from app.agents.graph_nodes import GraphNodes, should_use_tool, should_continue_loop

logger = logging.getLogger(__name__)


def create_recruitment_workflow(
    llm,
    tools_dict: Dict[str, Any],
    verbose: bool = False,
    checkpointer=None,
    memory_service=None,
    memory_top_k: int = 5,
    memory_min_confidence: float = 0.7,
    context_window_tokens: int = 32768,
    context_output_reserve_tokens: int = 2000,
    observability=None,
) -> StateGraph:
    """Create the LangGraph workflow for recruitment agent.
    
    Graph Structure:
        START
          ↓
        reasoning_node (LLM decides action)
          ↓
        [Conditional: Tool needed?]
          ↓                    ↓
        tool_execution    response_generation
          ↓                    ↓
        [Back to reasoning]   END
    
    Args:
        llm: LangChain LLM instance
        tools_dict: Dictionary of available tools
        verbose: Enable verbose logging
        
    Returns:
        Compiled StateGraph workflow
    """
    logger.info("Creating LangGraph recruitment workflow")
    
    # Initialize nodes with dependencies
    nodes = GraphNodes(
        llm=llm,
        tools_dict=tools_dict,
        verbose=verbose,
        memory_service=memory_service,
        memory_top_k=memory_top_k,
        memory_min_confidence=memory_min_confidence,
        context_window_tokens=context_window_tokens,
        context_output_reserve_tokens=context_output_reserve_tokens,
        observability=observability,
    )
    
    # Create the graph
    workflow = StateGraph(AgentState)
    
    # Add nodes to the graph
    workflow.add_node("reasoning", nodes.reasoning_node)
    workflow.add_node("memory_retrieval", nodes.memory_retrieval_node)
    workflow.add_node("tool_execution", nodes.tool_execution_node)
    workflow.add_node("response_generation", nodes.response_generation_node)
    workflow.add_node("memory_extraction", nodes.memory_extraction_node)
    
    # Set entry point
    workflow.set_entry_point("memory_retrieval")
    workflow.add_edge("memory_retrieval", "reasoning")
    
    # Add conditional edges from reasoning node
    workflow.add_conditional_edges(
        "reasoning",
        should_use_tool,
        {
            "execute_tool": "tool_execution",
            "generate_response": "response_generation"
        }
    )
    
    # After tool execution, loop back to reasoning (so LLM can see result)
    workflow.add_conditional_edges(
        "tool_execution",
        should_continue_loop,
        {
            "continue": "reasoning",
            "respond": "response_generation",
            "end": END
        }
    )
    
    # Response generation ends the workflow
    workflow.add_edge("response_generation", "memory_extraction")
    workflow.add_edge("memory_extraction", END)
    
    # Compile the graph
    compiled_workflow = workflow.compile(checkpointer=checkpointer)
    
    logger.info("LangGraph workflow created successfully")
    
    return compiled_workflow


def visualize_workflow_mermaid() -> str:
    """Generate Mermaid diagram for the workflow.
    
    Returns:
        Mermaid diagram string
    """
    return """
```mermaid
graph TD
    START([START]) --> reasoning[Reasoning Node<br/>LLM Decides Action]
    
    reasoning --> decision{Tool Needed?}
    
    decision -->|Yes| tool_execution[Tool Execution Node<br/>Execute Tool]
    decision -->|No| response_generation[Response Generation Node<br/>Generate Final Answer]
    
    tool_execution --> loop_check{Continue Loop?}
    loop_check -->|Yes - Process Result| reasoning
    loop_check -->|No - Error/Max Iterations| END([END])
    
    response_generation --> END
    
    style START fill:#90EE90
    style END fill:#FFB6C1
    style reasoning fill:#87CEEB
    style tool_execution fill:#FFD700
    style response_generation fill:#DDA0DD
    style decision fill:#FFA500
    style loop_check fill:#FFA500
```
"""


def get_workflow_description() -> str:
    """Get detailed description of the workflow.
    
    Returns:
        Description string
    """
    return """
LangGraph Recruitment Agent Workflow
====================================

This workflow implements a structured, stateful agent using LangGraph.

Nodes:
------
1. **Reasoning Node**: 
   - LLM analyzes user query and context
   - Decides if a tool call is needed
   - If tool needed: specifies tool name and arguments
   - If no tool: generates final answer

2. **Tool Execution Node**:
   - Executes the specified tool
   - Stores result in state
   - Handles errors gracefully

3. **Response Generation Node**:
   - Generates final user-facing response
   - Uses LLM to format answer naturally

Conditional Routing:
-------------------
- **should_use_tool**: Routes from Reasoning to either Tool Execution or Response Generation
- **should_continue_loop**: Routes from Tool Execution back to Reasoning or to END

State Management:
----------------
The workflow maintains a shared AgentState with:
- user_question: Original query
- chat_history: Conversation context
- tool_result: Results from tool execution
- tool_calls_made: List of tools used (for tracking)
- final_answer: Final response to user
- iteration_count: Loop counter (prevents infinite loops)

Benefits over Loop-Based Approach:
----------------------------------
✓ Structured flow - no uncontrolled loops
✓ Explicit state transitions
✓ Easy to visualize and debug
✓ Modular - add new nodes without changing existing code
✓ Better error handling
✓ Supports complex multi-step workflows

Example Flow:
------------
User: "Find Python developers"
  → Reasoning: LLM decides to use search_candidates tool
  → Tool Execution: Executes search_candidates("Python developers")
  → Reasoning: LLM sees results, generates response
  → Response Generation: Formats final answer
  → END
"""


# Export main functions
__all__ = [
    'create_recruitment_workflow',
    'visualize_workflow_mermaid',
    'get_workflow_description'
]
