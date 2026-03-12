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
    """The user's original question or query"""
    
    chat_history: Optional[List[tuple[str, str]]]
    """Conversation history as list of (role, content) tuples"""
    
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
    
    # Tool execution
    tool_result: Optional[str]
    """Result from tool execution"""
    
    tool_calls_made: Annotated[List[str], add]
    """List of tools called during this workflow (accumulated via add operator)"""
    
    failed_identifiers: Annotated[List[str], add]
    """List of candidate identifiers that failed lookup (accumulated to prevent retries)"""
    
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
        chat_history=chat_history or [],
        retrieved_chunks=None,
        retrieval_context=None,
        llm_reasoning=None,
        needs_tool=False,
        tool_name=None,
        tool_arguments=None,
        tool_result=None,
        tool_calls_made=[],
        failed_identifiers=[],
        error=None,
        final_answer=None,
        iteration_count=0,
        max_iterations=max_iterations
    )
