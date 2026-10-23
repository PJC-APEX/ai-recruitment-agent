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
import uuid
import asyncio
from pathlib import Path
import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from typing import List, Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.tools import Tool

from app.agents.graph_state import AgentState, create_initial_state
from app.agents.context_manager import count_tokens, fit_history, merge_key_facts, trim_text_to_tokens
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
        verbose: bool = False,
        checkpointer=None,
        checkpoint_db_path: Optional[str] = None,
        max_short_term_messages: int = 20,
        context_window_tokens: int = 32768,
        context_output_reserve_tokens: int = 2000,
        max_user_message_tokens: int = 8000,
        memory_service=None,
        memory_top_k: int = 5,
        memory_min_confidence: float = 0.7,
        observability=None,
    ):
        """Initialize the recruitment agent with LangGraph workflow.
        
        Args:
            llm_client: LLM client instance with OpenAI-compatible credentials
            tools: List of LangChain tools available to the agent
            max_iterations: Maximum number of workflow iterations
            verbose: Whether to log detailed workflow steps
            context_window_tokens: Maximum estimated input context size
            context_output_reserve_tokens: Tokens reserved for model output
            max_user_message_tokens: Hard limit for one user turn
        """
        self.llm_client = llm_client
        self.tools = tools
        self.tools_dict = {tool.name: tool for tool in tools}
        self.max_iterations = max_iterations
        self.verbose = verbose
        self.max_short_term_messages = max_short_term_messages
        self.context_window_tokens = context_window_tokens
        self.context_output_reserve_tokens = context_output_reserve_tokens
        self.max_user_message_tokens = max_user_message_tokens
        self.checkpointer = checkpointer
        self.checkpoint_db_path = checkpoint_db_path
        self.memory_service = memory_service
        self.memory_top_k = memory_top_k
        self.memory_min_confidence = memory_min_confidence
        self.observability = observability
        self._checkpoint_lock = asyncio.Lock()
        self.logger = logger
        
        # Create LangChain-compatible LLM wrapper
        self.llm = self._create_langchain_llm()
        
        # Create the LangGraph workflow
        self.workflow = create_recruitment_workflow(
            llm=self.llm, tools_dict=self.tools_dict, verbose=verbose,
            checkpointer=checkpointer, memory_service=memory_service,
            memory_top_k=memory_top_k, memory_min_confidence=memory_min_confidence,
            context_window_tokens=context_window_tokens,
            context_output_reserve_tokens=context_output_reserve_tokens,
            observability=observability,
        ) if checkpointer is not None or not checkpoint_db_path else None
        
        self.logger.info(f"Initialized RecruitmentAgent with LangGraph workflow and {len(tools)} tools")
    
    def _create_langchain_llm(self) -> ChatOpenAI:
        """Create a LangChain-compatible OpenAI API LLM.
        
        Returns:
            ChatOpenAI instance
        """
        return ChatOpenAI(
            base_url=self.llm_client.endpoint,
            api_key=self.llm_client.api_key,
            model=self.llm_client.model,
            temperature=0.7,
            max_tokens=1000
        )
    
    async def process_query(
        self,
        query: str,
        chat_history: Optional[List[tuple[str, str]]] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process a user query using the LangGraph workflow.
        
        This method:
        1. Creates initial state from query
        2. Executes the LangGraph workflow
        3. Returns structured response
        
        Args:
            query: User's natural language query
            chat_history: Optional conversation history as list of (role, content) tuples
            session_id: Stable id used to restore checkpointed short-term context
            user_id: Optional id used for long-term memory retrieval
            
        Returns:
            Dict with 'response', 'tools_used', and 'success' keys
        """
        try:
            self.logger.info(f"Agent processing query with LangGraph: {query}")

            query_tokens = self._count_tokens(query)
            if query_tokens > self.max_user_message_tokens:
                message = (
                    f"Your message is too long (about {query_tokens} tokens). "
                    f"Please shorten it to at most {self.max_user_message_tokens} tokens and try again."
                )
                return {"response": message, "tools_used": [], "success": False, "error": "user_message_too_long"}

            # AsyncSqliteSaver must be created inside a running event loop.
            if self.workflow is None and self.checkpoint_db_path:
                async with self._checkpoint_lock:
                    if self.workflow is None:
                        db_path = Path(self.checkpoint_db_path)
                        if not db_path.is_absolute():
                            db_path = Path.cwd() / db_path
                        db_path.parent.mkdir(parents=True, exist_ok=True)
                        connection = await aiosqlite.connect(str(db_path))
                        self.checkpointer = AsyncSqliteSaver(connection)
                        await self.checkpointer.setup()
                        self.workflow = create_recruitment_workflow(
                            llm=self.llm, tools_dict=self.tools_dict,
                            verbose=self.verbose, checkpointer=self.checkpointer,
                            memory_service=self.memory_service,
                            memory_top_k=self.memory_top_k,
                            memory_min_confidence=self.memory_min_confidence,
                            context_window_tokens=self.context_window_tokens,
                            context_output_reserve_tokens=self.context_output_reserve_tokens,
                            observability=self.observability,
                        )
            
            # A caller-provided session id enables persistent checkpoints. If
            # omitted, retain legacy one-shot behavior with an isolated thread.
            session_id = session_id or str(uuid.uuid4())
            checkpoint_config = {"configurable": {"thread_id": session_id}}

            if self.checkpointer is not None:
                await self.checkpointer.setup()

            # Restore history for this thread, falling back to legacy history
            # supplied by older clients.
            previous_state = await self.workflow.aget_state(checkpoint_config) if self.checkpointer is not None else None
            persisted_history = previous_state.values.get("chat_history", []) if previous_state else []
            persisted_facts = previous_state.values.get("context_facts", []) if previous_state else []
            base_history = persisted_history or (chat_history or [])
            # The current user turn is part of the context seen by every node.
            merged_history = self._fit_history(base_history, query)
            user_fact_sources = []
            for item in base_history:
                if not isinstance(item, (tuple, list)) or len(item) != 2:
                    continue
                role, content = item
                if str(role).lower() in {"human", "user"}:
                    user_fact_sources.append(str(content or ""))
            user_fact_sources.append(query)
            context_facts = merge_key_facts(persisted_facts, user_fact_sources)

            initial_state = create_initial_state(
                user_question=query,
                chat_history=merged_history,
                max_iterations=self.max_iterations
            )
            initial_state["user_id"] = user_id
            initial_state["session_id"] = session_id
            initial_state["context_facts"] = context_facts
            
            if self.verbose:
                self.logger.info("[Agent] Starting LangGraph workflow execution")
            
            # Execute the workflow - LangGraph handles the entire flow. The
            # observability callback is attached only to the execution config;
            # checkpoint reads/writes remain free of tracing callbacks.
            run_config = dict(checkpoint_config)
            if self.observability is not None:
                run_config.update(
                    self.observability.runnable_config(
                        session_id=session_id,
                        user_id=user_id,
                    )
                )
            with self._agent_observation(
                session_id=session_id,
                user_id=user_id,
                query=query,
            ) as agent_span:
                final_state = await self.workflow.ainvoke(initial_state, config=run_config)
                if self.observability is not None:
                    self.observability.update(
                        agent_span,
                        metadata={
                            "success": final_state.get("error") is None,
                            "error": final_state.get("error"),
                            "iteration_count": final_state.get("iteration_count", 0),
                            "tools_used": final_state.get("tool_calls_made", []),
                        },
                    )
            
            # Extract results from final state
            final_answer = final_state.get("final_answer", "I couldn't generate a response.")
            tools_used = final_state.get("tool_calls_made", [])
            error = final_state.get("error")

            # Checkpointing stores node outputs. Persist the assistant turn as
            # part of chat_history so the next request can restore it.
            checkpoint_cleanup = {
                # Full documents are response payloads, not durable
                # conversation history. Keep the latest checkpoint compact so
                # the next request cannot restore transient tool payloads.
                "resume_documents": [],
                "resume_comparison_contexts": {},
                "tool_context": None,
                "tool_context_by_call_id": {},
                "tool_result": None,
                "messages": [],
                "pending_tool_calls": [],
                "tool_name": None,
                "tool_arguments": None,
                "tool_calls_made": [],
                "executed_tool_calls": [],
                "tool_call_counts": {},
                "duplicate_tool_call": False,
                "last_tool_call_id": None,
                "last_tool_name": None,
                "last_tool_arguments": None,
                "needs_tool": False,
            }
            if final_answer and error is None and self.checkpointer is not None:
                history_answer = self._history_answer(
                    final_answer,
                    final_state.get("resume_documents", []),
                )
                history_to_persist = [
                    *final_state.get("chat_history", merged_history),
                    ("ai", history_answer),
                ]
                updated_history = fit_history(
                    history_to_persist,
                    "",
                    max_messages=self.max_short_term_messages,
                    context_window_tokens=self.context_window_tokens,
                    output_reserve_tokens=self.context_output_reserve_tokens,
                    include_query=False,
                )
                updated_facts = final_state.get("context_facts", context_facts)
                # Update the persisted thread with the assistant turn. This
                # creates a new checkpoint without rerunning the workflow.
                await self.workflow.aupdate_state(
                    checkpoint_config,
                    {
                        "chat_history": updated_history,
                        "context_facts": updated_facts,
                        **checkpoint_cleanup,
                    },
                )
            elif self.checkpointer is not None:
                # Also remove transient tool payloads after failed turns.
                await self.workflow.aupdate_state(
                    checkpoint_config,
                    checkpoint_cleanup,
                )
            
            if self.verbose:
                self.logger.info(f"[Agent] Workflow completed. Tools used: {tools_used}")
            
            # Check if workflow succeeded
            success = final_answer is not None and error is None
            
            result = {
                "response": final_answer,
                "tools_used": tools_used,
                "success": success,
                "resume_documents": self._public_resume_documents(
                    final_state.get("resume_documents", [])
                ),
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

    def _agent_observation(self, *, session_id: str, user_id: Optional[str], query: str):
        """Create a redacted top-level Agent span when observability is enabled."""
        if self.observability is None:
            from contextlib import nullcontext

            return nullcontext(None)
        return self.observability.observation(
            "recruitment_agent.process_query",
            as_type="span",
            session_id=session_id,
            user_id=user_id,
            metadata={
                "query_chars": len(query or ""),
                "query_tokens_estimate": self._count_tokens(query),
            },
        )

    @staticmethod
    def _public_resume_documents(documents: Any) -> List[Dict[str, Any]]:
        """Expose full documents to the client without internal tool ids."""
        public: List[Dict[str, Any]] = []
        for document in documents or []:
            if not isinstance(document, dict):
                continue
            item = dict(document)
            item.pop("tool_call_id", None)
            public.append(item)
        return public

    @staticmethod
    def _history_answer(final_answer: str, documents: Any) -> str:
        """Persist a compact reference instead of a complete resume answer."""
        references = []
        seen = set()
        for document in documents or []:
            if not isinstance(document, dict):
                continue
            file_name = str(document.get("file_name") or "").strip()
            if not file_name or file_name in seen:
                continue
            seen.add(file_name)
            name = str(document.get("candidate_name") or file_name).strip()
            references.append(f"{name} ({file_name})")

        concise_answer = trim_text_to_tokens(final_answer or "", 600)
        if references:
            return (
                "Candidates loaded for this turn: "
                + ", ".join(references)
                + "\nAssistant conclusion: "
                + concise_answer
            )
        return concise_answer

    def _count_tokens(self, text: str) -> int:
        """Count tokens using a conservative OpenAI-compatible encoding.

        The configured chat provider may use a different tokenizer, so this
        count is intentionally treated as an upper-bound estimate for deciding
        whether a request is safe to send.
        """
        return count_tokens(text)

    def _fit_history(
        self,
        history: List[tuple[str, str]],
        query: str,
    ) -> List[tuple[str, str]]:
        """Apply message-count and token-based sliding-window limits.

        The newest messages are retained first. Older messages are dropped
        deterministically; no summarization LLM call is made. A conservative
        allowance is reserved for system instructions, long-term memories,
        tool schemas/results, and message framing assembled by graph nodes.
        The current user turn is always retained (and is still represented in
        ``chat_history`` for checkpoint compatibility with the existing flow).
        """
        selected = fit_history(
            history,
            query,
            max_messages=self.max_short_term_messages,
            context_window_tokens=self.context_window_tokens,
            output_reserve_tokens=self.context_output_reserve_tokens,
        )
        if self.verbose and len(selected) < len(history or []) + 1:
            self.logger.info(
                "[Context] Applied message/token sliding window: %d -> %d messages",
                len(history or []) + 1,
                len(selected),
            )
        return selected
    
    def add_tool(self, tool: Tool) -> None:
        """Add a new tool to the agent (following Open/Closed Principle).
        
        Note: After adding tools, the workflow needs to be recreated to include them.
        
        Args:
            tool: LangChain Tool to add
        """
        self.tools.append(tool)
        self.tools_dict[tool.name] = tool
        self.logger.info(f"Added tool: {tool.name}")
