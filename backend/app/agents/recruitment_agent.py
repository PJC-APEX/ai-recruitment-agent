"""Recruitment Agent orchestrator using LangGraph.

This module implements the agent using LangGraph for structured workflows.
Replaces the loop-based approach with a stateful graph for better control.

Key improvements over loop-based approach:
- Structured workflow instead of uncontrolled loops
- Explicit state management
- Better debugging and visualization
- Modular node design
- Follows SOLID principles

Architecture follows SOLID principles:
- Single Responsibility: Only handles agent orchestration
- Dependency Inversion: Depends on abstractions (tools, LLM interface)
- Open/Closed: Easy to add new nodes/tools without modifying core logic
"""

import logging
from typing import List, Dict, Any, Optional
from langchain_openai import AzureChatOpenAI
from langchain_core.tools import Tool

from app.agents.graph_state import AgentState, create_initial_state
from app.agents.workflow import create_recruitment_workflow

logger = logging.getLogger(__name__)


class RecruitmentAgent:
    """AI Agent for autonomous recruitment assistance using LangGraph.
    
    This agent uses LangGraph's workflow graphs to autonomously:
    1. Understand user intent
    2. Decide which tool(s) to use through structured workflow
    3. Execute tools to gather information
    4. Generate natural language responses
    
    Key improvements over loop-based approach:
    - Structured workflow with explicit state transitions
    - No uncontrolled loops - max iterations built into graph
    - Better debugging through graph visualization
    - Modular design - easy to add new workflow nodes
    
    Follows SOLID principles:
    - SRP: Only orchestrates workflow execution
    - DIP: Depends on Tool abstractions, not concrete implementations
    - OCP: New nodes/tools can be added without modifying this class
    """
    
    def __init__(
        self,
        llm_client,
        tools: List[Tool],
        max_iterations: int = 5,
        verbose: bool = False
    ):
        """Initialize the recruitment agent with LangGraph workflow.
        
        Args:
            llm_client: LLM client instance (must have Azure OpenAI credentials)
            tools: List of LangChain tools available to the agent
            max_iterations: Maximum number of workflow iterations
            verbose: Whether to log detailed workflow steps
        """
        self.llm_client = llm_client
        self.tools = tools
        self.tools_dict = {tool.name: tool for tool in tools}
        self.max_iterations = max_iterations
        self.verbose = verbose
        self.logger = logger
        
        # Create LangChain-compatible LLM wrapper
        self.llm = self._create_langchain_llm()
        
        # Create the LangGraph workflow
        self.workflow = create_recruitment_workflow(
            llm=self.llm,
            tools_dict=self.tools_dict,
            verbose=verbose
        )
        
        self.logger.info(f"Initialized RecruitmentAgent with LangGraph workflow and {len(tools)} tools")
    
    def _create_langchain_llm(self) -> AzureChatOpenAI:
        """Create LangChain-compatible Azure OpenAI LLM.
        
        Returns:
            AzureChatOpenAI instance
        """
        return AzureChatOpenAI(
            azure_endpoint=self.llm_client.endpoint,
            api_key=self.llm_client.api_key,
            api_version=self.llm_client.api_version,
            azure_deployment=self.llm_client.model,
            temperature=0.7,
            max_tokens=1000
        )
    
    async def process_query(
        self,
        query: str,
        chat_history: Optional[List[tuple[str, str]]] = None
    ) -> Dict[str, Any]:
        """Process a user query using the LangGraph workflow.
        
        This method:
        1. Creates initial state from query
        2. Executes the LangGraph workflow
        3. Returns structured response
        
        Args:
            query: User's natural language query
            chat_history: Optional conversation history as list of (role, content) tuples
            
        Returns:
            Dict with 'response', 'tools_used', and 'success' keys
        """
        try:
            self.logger.info(f"Agent processing query with LangGraph: {query}")
            
            # Create initial state
            initial_state = create_initial_state(
                user_question=query,
                chat_history=chat_history,
                max_iterations=self.max_iterations
            )
            
            if self.verbose:
                self.logger.info("[Agent] Starting LangGraph workflow execution")
            
            # Execute the workflow - LangGraph handles the entire flow
            final_state = await self.workflow.ainvoke(initial_state)
            
            # Extract results from final state
            final_answer = final_state.get("final_answer", "I couldn't generate a response.")
            tools_used = final_state.get("tool_calls_made", [])
            error = final_state.get("error")
            
            if self.verbose:
                self.logger.info(f"[Agent] Workflow completed. Tools used: {tools_used}")
            
            # Check if workflow succeeded
            success = final_answer is not None and error is None
            
            result = {
                "response": final_answer,
                "tools_used": tools_used,
                "success": success
            }
            
            if error:
                result["error"] = error
                self.logger.error(f"Agent workflow error: {error}")
            else:
                self.logger.info("Agent workflow completed successfully")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in agent workflow execution: {str(e)}", exc_info=True)
            return {
                "response": f"I encountered an error while processing your request: {str(e)}",
                "tools_used": [],
                "success": False,
                "error": str(e)
            }
    
    def add_tool(self, tool: Tool) -> None:
        """Add a new tool to the agent (following Open/Closed Principle).
        
        Note: After adding tools, the workflow needs to be recreated to include them.
        
        Args:
            tool: LangChain Tool to add
        """
        self.tools.append(tool)
        self.tools_dict[tool.name] = tool
        self.logger.info(f"Added tool: {tool.name}")
