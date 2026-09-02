"""Graph nodes for LangGraph recruitment agent workflow.

This module implements individual nodes in the agent workflow graph.
Each node is a pure function that takes state and returns updated state.

Follows SOLID principles:
- Single Responsibility: Each node does ONE specific task
- Open/Closed: Easy to add new nodes without modifying existing ones
- Dependency Inversion: Nodes depend on state abstraction, not concrete implementations
"""

import logging
import json
from typing import Dict, Any
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from app.agents.graph_state import AgentState

logger = logging.getLogger(__name__)


class GraphNodes:
    """Container for all graph node implementations.
    
    This class holds node functions and their dependencies, following
    Dependency Injection principles for testability.
    """
    
    def __init__(self, llm, tools_dict: Dict[str, Any], verbose: bool = False):
        """Initialize graph nodes with dependencies.
        
        Args:
            llm: LangChain LLM instance (with tool binding)
            tools_dict: Dictionary mapping tool names to tool instances
            verbose: Whether to log detailed information
        """
        self.llm = llm
        self.tools_dict = tools_dict
        self.verbose = verbose
        self.logger = logger
        # Use LangChain's modern tool-calling interface. This maps to the
        # OpenAI-compatible `tools` payload supported by DeepSeek.
        self.llm_with_tools = self.llm.bind_tools(list(tools_dict.values()))
    
    def _get_system_message(self) -> str:
        """Get the system message for the agent.
        
        Returns:
            System message string
        """
        return """You are an intelligent recruitment assistant with access to a resume database.

Your role is to help users find, evaluate, and manage candidate information.

Key capabilities:
- Search for candidates matching specific skills or criteria
- List all candidates in the database
- Get detailed information about specific candidates
- Answer questions about candidate qualifications

Guidelines:
1. When users ask to compare, rank, or analyze MULTIPLE candidates:
   - FIRST call list_all_candidates to see what candidates are available
   - The list shows EXACT filenames like "SSE-SivaramakrishnanG-Connectrz.pdf"
   - ALWAYS use the EXACT filename from the File: field in the list
   - DO NOT modify, shorten, or reformat the filename
   - DO NOT try to parse or reconstruct candidate names

2. When users ask about counting or listing ALL candidates, use list_all_candidates

3. When users want to find candidates with specific skills, use search_candidates

4. CRITICAL - If get_candidate_details fails (returns "Could not find"):
   - STOP trying that identifier immediately
   - DO NOT retry with any variation of that name
   - DO NOT call list_all_candidates and try again
   - SKIP to the next candidate or generate a response with available data

5. CRITICAL - Using correct identifiers:
   - ALWAYS copy the EXACT filename from "File: " field in list_all_candidates result
   - Example: If you see "File: SSE-SivaramakrishnanG-Connectrz.pdf" use exactly "SSE-SivaramakrishnanG-Connectrz.pdf"
   - DO NOT use parsed names like "Sivaramakrishnan G" or "SSE, Connectrz"
   - The filename is the ONLY reliable identifier

6. Be efficient:
   - Never call the same tool with the same parameters more than once
   - If a lookup fails, move on immediately
   - Generate a response with whatever data you successfully obtained

7. Always provide accurate information from the database - never guess or make up details

8. If some candidates cannot be found, acknowledge this briefly and provide analysis for the candidates you successfully retrieved

Remember: The EXACT filename from list_all_candidates is the ONLY correct identifier. Use it exactly as shown in the "File: " field."""
    
    
    async def reasoning_node(self, state: AgentState) -> AgentState:
        """LLM reasoning node - decides what to do next.
        
        This node:
        1. Builds context from chat history and state
        2. Calls LLM with tool binding
        3. Determines if a tool call is needed
        4. Updates state with decision
        
        Args:
            state: Current agent state
            
        Returns:
            Updated state with LLM decision
        """
        try:
            self.logger.info("[ReasoningNode] LLM analyzing query and deciding action")
            
            # Increment iteration counter
            state["iteration_count"] = state.get("iteration_count", 0) + 1
            
            # Check max iterations
            if state["iteration_count"] > state.get("max_iterations", 5):
                self.logger.warning("[ReasoningNode] Max iterations reached")
                state["error"] = "Max iterations reached"
                state["final_answer"] = "I apologize, but I need to stop processing to prevent an infinite loop. Please try rephrasing your question."
                state["needs_tool"] = False
                return state
            
            # Build message history
            messages = [SystemMessage(content=self._get_system_message())]
            
            # Add chat history
            if state.get("chat_history"):
                for role, content in state["chat_history"]:
                    if role == "human":
                        messages.append(HumanMessage(content=content))
                    else:
                        messages.append(AIMessage(content=content))
            
            # Add current question
            messages.append(HumanMessage(content=state["user_question"]))
            
            # Add tool result if available (from previous iteration)
            if state.get("tool_result"):
                messages.append(HumanMessage(
                    content=f"Tool '{state.get('tool_name')}' returned: {state['tool_result']}"
                ))
            
            if self.verbose:
                self.logger.info(f"[ReasoningNode] Calling LLM with {len(messages)} messages")

            # Call the model with native tool schemas. The old `functions`
            # parameter is not reliably interpreted by DeepSeek-compatible APIs.
            response = await self.llm_with_tools.ainvoke(messages)

            # Check if LLM wants to call a tool. Keep a legacy fallback for
            # providers that still return an OpenAI `function_call` payload.
            tool_calls = getattr(response, "tool_calls", None) or []
            legacy_call = getattr(response, "additional_kwargs", {}).get("function_call")
            if tool_calls:
                tool_call = tool_calls[0]
                tool_name = tool_call["name"]
                tool_args = tool_call.get("args", {})
            elif legacy_call:
                tool_name = legacy_call["name"]
                raw_arguments = legacy_call.get("arguments", {})
                tool_args = json.loads(raw_arguments) if isinstance(raw_arguments, str) else raw_arguments
            else:
                tool_name = None
                tool_args = {}

            if tool_name:
                
                # Prevent retry of previously failed get_candidate_details calls
                if tool_name == 'get_candidate_details':
                    identifier = tool_args.get('identifier', '')
                    failed_ids = state.get('failed_identifiers', [])
                    
                    # Check if this identifier already failed
                    if identifier and identifier in failed_ids:
                        # This identifier already failed - force skip and generate response
                        self.logger.warning(f"[ReasoningNode] Preventing retry of failed identifier: {identifier}")
                        state["needs_tool"] = False
                        state["final_answer"] = f"I apologize, but I couldn't find complete information for all requested candidates. Some candidates like '{identifier}' could not be located in the database. I can only provide information for the candidates I successfully retrieved."
                        return state
                
                if self.verbose:
                    self.logger.info(f"[ReasoningNode] LLM decided to call tool: {tool_name}")
                    self.logger.info(f"[ReasoningNode] Tool arguments: {tool_args}")
                
                state["needs_tool"] = True
                state["tool_name"] = tool_name
                state["tool_arguments"] = tool_args
                state["llm_reasoning"] = f"Calling tool: {tool_name}"
            else:
                # LLM provided final answer
                final_answer = response.content
                
                if self.verbose:
                    self.logger.info("[ReasoningNode] LLM provided final answer")
                
                state["needs_tool"] = False
                state["final_answer"] = final_answer
                state["llm_reasoning"] = "Generated final response"
            
            # Return state WITHOUT tool_calls_made
            # Only tool_execution_node should return tool_calls_made (add operator handles accumulation)
            return {
                "user_question": state["user_question"],
                "chat_history": state["chat_history"],
                "retrieved_chunks": state.get("retrieved_chunks"),
                "retrieval_context": state.get("retrieval_context"),
                "llm_reasoning": state["llm_reasoning"],
                "needs_tool": state["needs_tool"],
                "tool_name": state.get("tool_name"),
                "tool_arguments": state.get("tool_arguments"),
                "tool_result": state.get("tool_result"),
                "error": state.get("error"),
                "final_answer": state.get("final_answer"),
                "iteration_count": state.get("iteration_count", 0) + 1,
                "max_iterations": state["max_iterations"]
            }
            
        except Exception as e:
            self.logger.error(f"[ReasoningNode] Error: {str(e)}", exc_info=True)
            return {
                "error": str(e),
                "final_answer": f"I encountered an error while processing: {str(e)}",
                "needs_tool": False
            }
    
    async def tool_execution_node(self, state: AgentState) -> AgentState:
        """Tool execution node - executes the decided tool.
        
        Args:
            state: Current agent state with tool decision
            
        Returns:
            Updated state with tool result
        """
        try:
            tool_name = state.get("tool_name")
            tool_args = state.get("tool_arguments", {})
            
            if not tool_name:
                self.logger.error("[ToolExecutionNode] No tool name provided")
                state["error"] = "No tool specified"
                return state
            
            self.logger.info(f"[ToolExecutionNode] Executing tool: {tool_name}")
            
            # Get tool from dictionary
            if tool_name not in self.tools_dict:
                self.logger.error(f"[ToolExecutionNode] Tool not found: {tool_name}")
                state["error"] = f"Tool '{tool_name}' not found"
                state["tool_result"] = f"Error: Tool '{tool_name}' is not available"
                return state
            
            tool = self.tools_dict[tool_name]
            # Some OpenAI-compatible models emit a placeholder argument for
            # zero-argument tools. Do not pass it to the Python function.
            if getattr(tool, "args_schema", None) is None and tool_args == {"__arg1": ""}:
                tool_args = {}
            
            # Execute tool (handle both sync and async)
            failed_identifier = None
            try:
                if tool.coroutine:
                    result = await tool.coroutine(**tool_args)
                elif hasattr(tool, 'afunc'):
                    result = await tool.afunc(**tool_args)
                else:
                    result = tool.func(**tool_args)
                
                if self.verbose:
                    self.logger.info(f"[ToolExecutionNode] Tool result: {result[:200]}...")
                
                # Update state
                state["tool_result"] = result
                
                # Track failed candidate lookups to prevent retries
                if tool_name == 'get_candidate_details' and ("Could not find resume" in result or "Could not find" in result):
                    failed_identifier = tool_args.get('identifier')
                    if failed_identifier:
                        self.logger.info(f"[ToolExecutionNode] Tracking failed identifier: {failed_identifier}")
                        state["tool_result"] += "\n\nSuggestion: Use list_all_candidates to see available candidates and their exact filenames."
                
                # Clear tool decision for next iteration
                state["needs_tool"] = False
                state["tool_name"] = None
                state["tool_arguments"] = None
                
            except Exception as te:
                error_msg = f"Error executing tool {tool_name}: {str(te)}"
                self.logger.error(f"[ToolExecutionNode] {error_msg}", exc_info=True)
                state["error"] = error_msg
                state["tool_result"] = f"Error: {error_msg}"
            
            # Return updated state - ONLY return the new tool_name and optionally failed_identifier
            # Let LangGraph's add operator handle the accumulation
            return_state = {
                "user_question": state["user_question"],
                "chat_history": state["chat_history"],
                "retrieved_chunks": state.get("retrieved_chunks"),
                "retrieval_context": state.get("retrieval_context"),
                "llm_reasoning": state.get("llm_reasoning"),
                "needs_tool": state["needs_tool"],
                "tool_name": state.get("tool_name"),
                "tool_arguments": state.get("tool_arguments"),
                "tool_result": state["tool_result"],
                "tool_calls_made": [tool_name],  # Just the new tool - add operator will accumulate
                "error": state.get("error"),
                "final_answer": state.get("final_answer"),
                "iteration_count": state.get("iteration_count", 0),
                "max_iterations": state["max_iterations"]
            }
            
            # Add failed identifier if lookup failed (add operator will accumulate)
            if failed_identifier:
                return_state["failed_identifiers"] = [failed_identifier]
            
            return return_state
            
        except Exception as e:
            self.logger.error(f"[ToolExecutionNode] Unexpected error: {str(e)}", exc_info=True)
            return {
                "error": str(e),
                "tool_result": f"Error: {str(e)}",
                "needs_tool": False,
                "final_answer": f"I encountered an error while executing the requested tool: {str(e)}"
            }
    
    async def response_generation_node(self, state: AgentState) -> AgentState:
        """Response generation node - creates final user-facing response.
        
        This node is called when no tools are needed and generates
        the final answer based on available context.
        
        Args:
            state: Current agent state
            
        Returns:
            Updated state with final answer
        """
        try:
            self.logger.info("[ResponseGenerationNode] Generating final response")
            
            # If we already have a final answer, return it
            if state.get("final_answer"):
                return state
            
            # If we have an error, return error message
            if state.get("error"):
                state["final_answer"] = f"I encountered an error: {state['error']}"
                return state
            
            # Otherwise, ask LLM to generate response
            messages = [SystemMessage(content=self._get_system_message())]
            
            # Add chat history
            if state.get("chat_history"):
                for role, content in state["chat_history"]:
                    if role == "human":
                        messages.append(HumanMessage(content=content))
                    else:
                        messages.append(AIMessage(content=content))
            
            # Add user question
            messages.append(HumanMessage(content=state["user_question"]))
            
            # Add any tool results
            if state.get("tool_result"):
                messages.append(HumanMessage(
                    content=f"Based on this information: {state['tool_result']}\n\nPlease provide a helpful response."
                ))
            
            # Call LLM without function calling
            response = await self.llm.ainvoke(messages)
            
            state["final_answer"] = response.content
            
            if self.verbose:
                self.logger.info("[ResponseGenerationNode] Generated final answer")
            
            # Return state WITHOUT tool_calls_made
            # Only tool_execution_node should return tool_calls_made (add operator handles accumulation)
            return {
                "user_question": state["user_question"],
                "chat_history": state["chat_history"],
                "retrieved_chunks": state.get("retrieved_chunks"),
                "retrieval_context": state.get("retrieval_context"),
                "llm_reasoning": state.get("llm_reasoning"),
                "needs_tool": state["needs_tool"],
                "tool_name": state.get("tool_name"),
                "tool_arguments": state.get("tool_arguments"),
                "tool_result": state.get("tool_result"),
                "error": state.get("error"),
                "final_answer": state["final_answer"],
                "iteration_count": state["iteration_count"],
                "max_iterations": state["max_iterations"]
            }
            
        except Exception as e:
            self.logger.error(f"[ResponseGenerationNode] Error: {str(e)}", exc_info=True)
            # Return error WITHOUT tool_calls_made
            return {
                "error": str(e),
                "final_answer": f"I encountered an error generating the response: {str(e)}"
            }
    
    def _get_tool_schemas(self):
        """Get OpenAI function schemas for all tools.
        
        Returns:
            List of function schemas
        """
        schemas = []
        for tool_name, tool in self.tools_dict.items():
            schema = {
                "name": tool.name,
                "description": tool.description,
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
            
            if hasattr(tool, 'args_schema') and tool.args_schema:
                if hasattr(tool.args_schema, 'schema'):
                    tool_schema = tool.args_schema.schema()
                    if 'properties' in tool_schema:
                        schema["parameters"]["properties"] = tool_schema['properties']
                    if 'required' in tool_schema:
                        schema["parameters"]["required"] = tool_schema['required']
            
            schemas.append(schema)
        
        return schemas


# Conditional routing functions
def should_use_tool(state: AgentState) -> str:
    """Determine if we should execute a tool or generate response.
    
    This is a conditional edge function for the graph.
    
    Args:
        state: Current agent state
        
    Returns:
        "execute_tool" if tool is needed, "generate_response" otherwise
    """
    if state.get("needs_tool", False) and state.get("tool_name"):
        return "execute_tool"
    return "generate_response"


def should_continue_loop(state: AgentState) -> str:
    """Determine if we should continue the agent loop or end.
    
    This is a conditional edge function for the graph.
    
    Args:
        state: Current agent state
        
    Returns:
        "continue" to loop back to reasoning, "end" to finish
    """
    # If we have a final answer, end
    if state.get("final_answer"):
        return "end"
    
    # If we have an error, end
    if state.get("error"):
        return "end"
    
    # If we've executed a tool, continue to reasoning
    if state.get("tool_result"):
        return "continue"
    
    # Default: end
    return "end"
