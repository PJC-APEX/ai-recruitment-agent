"""State schema for LangGraph workflow.

This module defines the shared state that flows through the agent graph.
Following the Single Responsibility Principle, it only handles state definition.
"""

from typing import List, Dict, Any, Optional, TypedDict, Annotated
from operator import add


class AgentState(TypedDict):
    """State object that flows through the LangGraph workflow.
    
    This state is shared across all nodes and contains:
    - User input and context
    - Retrieved information from RAG
    - Tool execution results
    - Final response to user
    
    The state follows the Open/Closed Principle - new fields can be added
    without modifying existing nodes (as long as they handle missing keys gracefully).
    """
    
    # User input
    user_question: str
    user_id: Optional[str]
    session_id: Optional[str]
    retrieved_memories: Optional[List[Dict[str, Any]]]
    """The user's original question or query"""
    
    chat_history: Optional[List[tuple[str, str]]]
    """Conversation history as list of (role, content) tuples"""

    context_facts: List[str]
    """Deterministic key facts retained when older chat messages are dropped."""

    memory_extraction_skipped: bool
    """Whether long-term extraction should be skipped for this failed turn."""

    memory_candidates: Optional[List[Dict[str, Any]]]
    """Long-term memories created from the completed turn, if any."""
    
    # Retrieval context
    retrieved_chunks: Optional[List[Dict[str, Any]]]
    """Resume chunks retrieved from ChromaDB vector store"""
    
    retrieval_context: Optional[str]
    """Formatted string of retrieved context for LLM"""
    
    # LLM reasoning
    llm_reasoning: Optional[str]
    """The LLM's reasoning or thought process"""
    
    # Tool decision
    needs_tool: bool
    """Whether the LLM decided a tool call is needed"""
    
    tool_name: Optional[str]
    """Name of the tool to execute"""
    
    tool_arguments: Optional[Dict[str, Any]]
    """Arguments for the tool"""

    pending_tool_calls: List[Dict[str, Any]]
    """All tool calls returned by the latest AI message."""
    
    # Tool execution
    tool_result: Optional[str]
    """Result from tool execution"""

    last_tool_name: Optional[str]
    """Name of the most recently executed tool, retained for context."""

    last_tool_arguments: Optional[Dict[str, Any]]
    """Arguments of the most recently executed tool."""

    last_tool_call_id: Optional[str]
    """Provider call id paired with the most recent tool result."""

    executed_tool_calls: List[str]
    """Canonical tool-call signatures already executed in this workflow."""

    duplicate_tool_call: bool
    """Whether the pending tool call was rejected as a duplicate."""
    
    tool_calls_made: List[str]
    """List of tools called during this workflow (accumulated via add operator)"""
    
    failed_identifiers: List[str]
    """Candidate identifiers that failed lookup during the current request."""
    
    # Error handling
    error: Optional[str]
    """Error message if something went wrong"""
    
    # Final output
    final_answer: Optional[str]
    """The final response to return to the user"""
    
    # Workflow control
    iteration_count: int
    """Number of iterations through the workflow (prevent infinite loops)"""
    
    max_iterations: int
    """Maximum allowed iterations"""

    tool_call_counts: Dict[str, int]
    """Per-tool invocation counts for the current workflow run."""

    max_tool_calls_per_tool: int
    """Maximum invocations allowed for one tool in the current run."""

    messages: List[Any]
    """Standard AI/tool messages retained for the next reasoning turn."""


def create_initial_state(
    user_question: str,
    chat_history: Optional[List[tuple[str, str]]] = None,
    max_iterations: int = 5
) -> AgentState:
    """Create initial state for a new workflow run.
    
    Args:
        user_question: The user's query
        chat_history: Optional conversation history
        max_iterations: Maximum iterations allowed
        
    Returns:
        Initial AgentState
    """
    return AgentState(
        user_question=user_question,
        user_id=None,
        session_id=None,
        retrieved_memories=[],
        chat_history=chat_history or [],
        context_facts=[],
        memory_extraction_skipped=False,
        memory_candidates=[],
        retrieved_chunks=None,
        retrieval_context=None,
        llm_reasoning=None,
        needs_tool=False,
        tool_name=None,
        tool_arguments=None,
        pending_tool_calls=[],
        tool_result=None,
        last_tool_name=None,
        last_tool_arguments=None,
        last_tool_call_id=None,
        executed_tool_calls=[],
        duplicate_tool_call=False,
        tool_calls_made=[],
        failed_identifiers=[],
        error=None,
        final_answer=None,
        iteration_count=0,
        max_iterations=max_iterations
        ,tool_call_counts={}
        ,max_tool_calls_per_tool=2
        ,messages=[]
    )
