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
import re
import asyncio
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from app.agents.graph_state import AgentState
from app.agents.context_manager import (
    count_tokens,
    facts_to_prompt,
    merge_key_facts,
    trim_text_to_tokens,
)

logger = logging.getLogger(__name__)


class MemoryExtractionDecision(BaseModel):
    """Validated result returned by the memory extraction model."""

    action: str = "ignore"
    memory_type: str = "fact"
    content: str = ""
    confidence: float = Field(default=0.0, ge=0, le=1)
    importance: float = Field(default=0.5, ge=0, le=1)


class GraphNodes:
    """Container for all graph node implementations.
    
    This class holds node functions and their dependencies, following
    Dependency Injection principles for testability.
    """
    
    def __init__(
        self,
        llm,
        tools_dict: Dict[str, Any],
        verbose: bool = False,
        memory_service=None,
        memory_top_k: int = 5,
        memory_min_confidence: float = 0.7,
        tool_timeout_seconds: float = 15.0,
        context_window_tokens: int = 32768,
        context_output_reserve_tokens: int = 2000,
    ):
        """Initialize graph nodes with dependencies.
        
        Args:
            llm: LangChain LLM instance (with tool binding)
            tools_dict: Dictionary mapping tool names to tool instances
            verbose: Whether to log detailed information
        """
        self.llm = llm
        self.tools_dict = tools_dict
        self.verbose = verbose
        self.memory_service = memory_service
        self.memory_top_k = memory_top_k
        self.memory_min_confidence = memory_min_confidence
        self.tool_timeout_seconds = tool_timeout_seconds
        self.context_window_tokens = context_window_tokens
        self.context_output_reserve_tokens = context_output_reserve_tokens
        self.logger = logger
        # Use LangChain's modern tool-calling interface. This maps to the
        # OpenAI-compatible `tools` payload supported by DeepSeek.
        self.llm_with_tools = self.llm.bind_tools(list(tools_dict.values()))

    def _normalize_tool_args(self, tool_name: str, tool_args: Any) -> Dict[str, Any]:
        """Normalize provider-specific arguments before execution/deduplication."""
        if not isinstance(tool_args, dict):
            tool_args = {}
        args = dict(tool_args)
        tool = self.tools_dict.get(tool_name)
        if tool is not None and getattr(tool, "args_schema", None) is None:
            return {}
        args.pop("__arg1", None)
        return args

    @staticmethod
    def _tool_call_signature(tool_name: str, tool_args: Dict[str, Any]) -> str:
        return f"{tool_name}:{json.dumps(tool_args, sort_keys=True, ensure_ascii=True)}"

    @staticmethod
    def _message_token_cost(message: Any) -> int:
        """Estimate a LangChain message's input-token cost."""
        content = getattr(message, "content", "")
        if not isinstance(content, str):
            content = json.dumps(content, ensure_ascii=False, default=str)
        # Tool calls often have an empty content field; include their arguments
        # in the estimate so a long call cannot silently exhaust the budget.
        tool_calls = getattr(message, "tool_calls", None)
        if tool_calls:
            content = f"{content}\n{json.dumps(tool_calls, ensure_ascii=False, default=str)}"
        return count_tokens(content) + 4

    def _fit_messages(
        self,
        messages: List[Any],
        required_user_content: str | None = None,
    ) -> List[Any] | None:
        """Trim old conversational/tool exchanges to the model input budget.

        System messages and the newest user turn are mandatory. Older turns
        and older tool exchanges are dropped as units, which avoids leaving an
        orphan ``ToolMessage`` without its assistant tool call. Returning None
        means even the mandatory context cannot fit and the caller should
        return a friendly error without making an LLM request.
        """
        input_budget = max(1, self.context_window_tokens - self.context_output_reserve_tokens)
        total = sum(self._message_token_cost(message) for message in messages)
        if total <= input_budget:
            return messages

        # Group each assistant tool call with the following tool result(s).
        # System messages remain fixed and are never removed.
        units: List[List[Any]] = []
        for message in messages:
            if isinstance(message, SystemMessage):
                units.append([message])
            elif (
                isinstance(message, ToolMessage)
                and units
                and getattr(units[-1][0], "tool_calls", None)
            ):
                units[-1].append(message)
            else:
                units.append([message])

        fixed_cost = sum(
            self._message_token_cost(unit[0])
            for unit in units
            if isinstance(unit[0], SystemMessage)
        )
        selected: set[int] = {
            index for index, unit in enumerate(units)
            if isinstance(unit[0], SystemMessage)
        }

        # Always retain the current question.  Response generation represents
        # a tool result as a HumanMessage for provider compatibility, so do not
        # blindly choose the last HumanMessage here.
        newest_human = None
        required_content = str(required_user_content or "")
        if required_user_content is not None:
            for index in range(len(units) - 1, -1, -1):
                if any(
                    isinstance(item, HumanMessage)
                    and str(getattr(item, "content", "")) == required_content
                    for item in units[index]
                ):
                    newest_human = index
                    break
        for index in range(len(units) - 1, -1, -1):
            if newest_human is not None:
                break
            if any(isinstance(item, HumanMessage) for item in units[index]):
                newest_human = index
                break
        if newest_human is not None:
            selected.add(newest_human)

        used = fixed_cost
        if newest_human is not None:
            used += sum(self._message_token_cost(item) for item in units[newest_human])

        # Newest non-system exchanges have priority over older exchanges.
        for index in range(len(units) - 1, -1, -1):
            if index in selected:
                continue
            unit_cost = sum(self._message_token_cost(item) for item in units[index])
            if used + unit_cost > input_budget:
                # Units are visited newest-first; older context must not
                # displace a newer exchange that cannot fit.
                break
            selected.add(index)
            used += unit_cost

        if used > input_budget:
            return None

        limited = [item for index, unit in enumerate(units) if index in selected for item in unit]
        if self.verbose:
            self.logger.info(
                "[Context] Trimmed assembled prompt from %d to %d estimated tokens",
                total,
                used,
            )
        return limited

    async def memory_retrieval_node(self, state: AgentState) -> AgentState:
        """Load relevant long-term memories for this user into workflow state."""
        user_id = state.get("user_id")
        if not user_id or not self.memory_service:
            self.logger.info("[MemoryRetrievalNode] Skipped: user_id or memory service is unavailable")
            return {"retrieved_memories": []}
        memories = await self.memory_service.retrieve_relevant(
            user_id, state["user_question"], top_k=self.memory_top_k
        )
        self.logger.info("[MemoryRetrievalNode] Retrieved %d memories for user %s", len(memories), user_id)
        return {"retrieved_memories": memories}

    async def memory_extraction_node(self, state: AgentState) -> AgentState:
        user_id, answer = state.get("user_id"), state.get("final_answer")
        if state.get("memory_extraction_skipped"):
            self.logger.info("[MemoryExtractionNode] Skipped after context-window rejection")
            return {"memory_candidates": []}
        if not user_id or not answer or not self.memory_service:
            self.logger.info("[MemoryExtractionNode] Skipped: missing user_id, final answer, or memory service")
            return {"memory_candidates": []}
        self.logger.info("[MemoryExtractionNode] Starting extraction for user %s", user_id)
        explicit_remember = any(marker in state["user_question"].lower() for marker in (
            "请记住", "记住", "保存这个", "以后", "remember", "save this"
        ))
        instruction = """Extract long-term memory from this recruitment conversation.
Return exactly one JSON object and no other text. The object must contain:
action (create or ignore), memory_type (preference, constraint, fact, decision, or candidate_note),
content (a concise standalone memory), confidence (0-1), and importance (0-1).
Save only durable user preferences, constraints, decisions, or facts explicitly requested for memory.
Ignore one-off searches. If the user explicitly asks you to remember something, return action=create when a valid memory can be extracted."""
        try:
            response = await self.llm.ainvoke([SystemMessage(content=f"{instruction}\nUser: {state['user_question']}\nAssistant: {answer}")])
            item = self._parse_memory_decision(response.content)
            decision = MemoryExtractionDecision.model_validate(item)
            action = decision.action.lower()
            confidence = decision.confidence
            if explicit_remember and decision.content:
                action = "create"
                confidence = max(confidence, self.memory_min_confidence)
                self.logger.info("[MemoryExtractionNode] Explicit remember request promoted to create")
            self.logger.info("[MemoryExtractionNode] Model decision: action=%s confidence=%.2f", action, confidence)
            if action != "create" or confidence < self.memory_min_confidence or not decision.content:
                self.logger.info("[MemoryExtractionNode] No memory saved: action, confidence, or content did not meet requirements")
                return {"memory_candidates": []}
            saved = await self.memory_service.save_extracted(user_id=user_id, content=decision.content, memory_type=decision.memory_type, importance=decision.importance, confidence=confidence, source_session_id=state.get("session_id"))
            self.logger.info("[MemoryExtractionNode] Saved memory id %s for user %s", saved["id"], user_id)
            return {"memory_candidates": [saved]}
        except Exception as exc:
            self.logger.warning("[MemoryExtractionNode] Failed to extract or save memory: %s", exc, exc_info=True)
            return {"memory_candidates": []}

    @staticmethod
    def _parse_memory_decision(content: str) -> dict:
        """Parse a JSON response even when a provider appends explanatory text."""
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip()).strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError as first_error:
            start = raw.find("{")
            if start < 0:
                raise first_error

            depth = 0
            in_string = False
            escaped = False
            for index, char in enumerate(raw[start:], start):
                if in_string:
                    if escaped:
                        escaped = False
                    elif char == "\\":
                        escaped = True
                    elif char == '"':
                        in_string = False
                elif char == '"':
                    in_string = True
                elif char == "{":
                    depth += 1
                elif char == "}":
                    depth -= 1
                    if depth == 0:
                        logger.info("[MemoryExtractionNode] Parsed JSON object with trailing model text removed")
                        return json.loads(raw[start:index + 1])
            raise first_error

    @staticmethod
    def _memory_context(state: AgentState) -> str:
        memories = state.get("retrieved_memories") or []
        if not memories:
            return ""
        lines = ["Relevant long-term memories (use only when applicable):"]
        lines.extend(f"- {m['content']}" for m in memories)
        # Long-term memories are useful context, but must not crowd out the
        # current request and recent conversation.
        return trim_text_to_tokens("\n".join(lines), 800)

    @staticmethod
    def _history_messages(state: AgentState) -> List[Any]:
        """Convert tuple history to messages without duplicating this turn."""
        history = state.get("chat_history") or []
        current_question = str(state.get("user_question") or "")
        result: List[Any] = []
        for index, item in enumerate(history):
            if not isinstance(item, (tuple, list)) or len(item) != 2:
                continue
            role, content = str(item[0]).lower(), str(item[1] or "")
            # RecruitmentAgent stores the current user turn in chat_history for
            # checkpoint compatibility and then adds it below. Avoid sending it
            # twice to the provider while preserving older duplicate turns.
            if index == len(history) - 1 and role in {"human", "user"} and content == current_question:
                continue
            if role in {"human", "user"}:
                result.append(HumanMessage(content=content))
            else:
                result.append(AIMessage(content=content))
        return result

    @staticmethod
    def _facts_context(state: AgentState) -> str:
        return facts_to_prompt(state.get("context_facts") or [], max_tokens=800)
    
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
1. When users ask to view one candidate's resume, detailed information, or qualifications:
   - Use get_candidate_details.
   - Pass only the candidate's name or a complete filename as the identifier.
   - Extract the name from natural language. For example, from "show me Chen Kai's resume", pass "Chen Kai"; do not pass the whole sentence.
   - The backend resolves a candidate name to the database filename before retrieving the resume.

2. When users ask to compare, rank, or analyze MULTIPLE candidates:
   - FIRST call list_all_candidates to see which candidates are available.
   - For follow-up detail lookups from that list, copy the exact filename from the File field.
   - Do not modify or reformat a filename copied from the list.

3. When users ask about counting or listing ALL candidates, use list_all_candidates.

4. When users want to find candidates with specific skills, experience, or requirements, use search_candidates.

5. If get_candidate_details fails (returns "Could not find"):
   - Stop trying that identifier immediately.
   - Do not retry with variations of the name or filename.
   - Do not call list_all_candidates just to retry the failed lookup.
   - Ask for a clearer name or provide a response using successfully retrieved data.

6. Be efficient:
   - Never call the same tool with the same parameters more than once.
   - If a lookup fails, move on immediately.
   - Generate a response with whatever data you successfully obtained.

7. Always provide accurate information from the database. Never guess or invent candidate details.

8. If multiple candidates have the same name, ask the user for a distinguishing detail such as company, role, or filename."""
    
    
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
            iteration_count = state.get("iteration_count", 0) + 1
            state["iteration_count"] = iteration_count
            
            # Check max iterations
            if iteration_count > state.get("max_iterations", 5):
                self.logger.warning("[ReasoningNode] Max iterations reached")
                state["error"] = "Max iterations reached"
                state["final_answer"] = "I apologize, but I need to stop processing to prevent an infinite loop. Please try rephrasing your question."
                state["needs_tool"] = False
                return state
            
            # Build message history
            messages = [SystemMessage(content=self._get_system_message())]

            memory_context = self._memory_context(state)
            if memory_context:
                messages.append(SystemMessage(content=memory_context))

            facts_context = self._facts_context(state)
            if facts_context:
                messages.append(SystemMessage(content=facts_context))
            
            # Add chat history
            messages.extend(self._history_messages(state))
            
            # Add current question
            messages.append(HumanMessage(content=state["user_question"]))
            
            # Replay the standard tool exchange when available. This preserves
            # the assistant tool call and its matching ToolMessage.
            if state.get("messages"):
                messages.extend(state["messages"])
            elif state.get("tool_result"):
                messages.append(ToolMessage(
                    content=state["tool_result"],
                    tool_call_id=state.get("last_tool_call_id", "legacy-tool-call"),
                ))

            limited_messages = self._fit_messages(
                messages,
                required_user_content=state["user_question"],
            )
            if limited_messages is None:
                state["error"] = "context_window_exceeded"
                state["final_answer"] = (
                    "The conversation context is too long to process safely. "
                    "Please shorten your message or start a new conversation."
                )
                state["memory_extraction_skipped"] = True
                state["needs_tool"] = False
                return state
            
            if self.verbose:
                self.logger.info(f"[ReasoningNode] Calling LLM with {len(limited_messages)} messages")

            # Call the model with native tool schemas. The old `functions`
            # parameter is not reliably interpreted by DeepSeek-compatible APIs.
            response = await self.llm_with_tools.ainvoke(limited_messages)

            # Check if LLM wants to call a tool. Keep a legacy fallback for
            # providers that still return an OpenAI `function_call` payload.
            tool_calls = getattr(response, "tool_calls", None) or []
            legacy_call = getattr(response, "additional_kwargs", {}).get("function_call")
            if tool_calls:
                normalized_calls = []
                for index, tool_call in enumerate(tool_calls):
                    name = tool_call["name"]
                    normalized_calls.append({
                        "name": name,
                        "args": self._normalize_tool_args(name, tool_call.get("args", {})),
                        "id": tool_call.get("id") or f"{name}-{iteration_count}-{index}",
                    })
                tool_call = normalized_calls[0]
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_call_id = tool_call["id"]
            elif legacy_call:
                tool_name = legacy_call["name"]
                raw_arguments = legacy_call.get("arguments", {})
                tool_args = self._normalize_tool_args(tool_name, json.loads(raw_arguments) if isinstance(raw_arguments, str) else raw_arguments)
                tool_call_id = legacy_call.get("id", "legacy-tool-call")
            else:
                tool_name = None
                tool_args = {}
                tool_call_id = None
                normalized_calls = []

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
                state["last_tool_call_id"] = tool_call_id
                state["pending_tool_calls"] = normalized_calls or [{"name": tool_name, "args": tool_args, "id": tool_call_id or f"{tool_name}-{iteration_count}"}]
                state["llm_reasoning"] = f"Calling tool: {tool_name}"
                state["messages"] = [*state.get("messages", []), response]
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
                "context_facts": state.get("context_facts", []),
                "memory_extraction_skipped": state.get("memory_extraction_skipped", False),
                "retrieved_chunks": state.get("retrieved_chunks"),
                "retrieval_context": state.get("retrieval_context"),
                "llm_reasoning": state["llm_reasoning"],
                "needs_tool": state["needs_tool"],
                "tool_name": state.get("tool_name"),
                "tool_arguments": state.get("tool_arguments"),
                "tool_result": state.get("tool_result"),
                "error": state.get("error"),
                "final_answer": state.get("final_answer"),
                "iteration_count": iteration_count,
                "max_iterations": state["max_iterations"]
                ,"messages": state.get("messages", [])
                ,"tool_call_counts": state.get("tool_call_counts", {})
                ,"max_tool_calls_per_tool": state.get("max_tool_calls_per_tool", 2)
                ,"last_tool_call_id": state.get("last_tool_call_id")
                ,"pending_tool_calls": state.get("pending_tool_calls", [])
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
            pending = state.get("pending_tool_calls") or []
            if not pending and state.get("tool_name"):
                pending = [{"name": state["tool_name"], "args": state.get("tool_arguments") or {}, "id": state.get("last_tool_call_id") or "legacy-tool-call"}]
            if not pending:
                return {"error": "No tool specified", "needs_tool": False, "final_answer": "No tool was specified."}

            call_counts = dict(state.get("tool_call_counts", {}))
            executed = list(state.get("executed_tool_calls", []))
            messages = list(state.get("messages", []))
            results = []
            used = []
            failed_ids = []
            duplicate = False

            for call in pending:
                tool_name = call["name"]
                tool_args = self._normalize_tool_args(tool_name, call.get("args", {}))
                call_id = call.get("id") or f"{tool_name}-{state.get('iteration_count', 0)}-{len(results)}"
                signature = self._tool_call_signature(tool_name, tool_args)
                if signature in executed or call_counts.get(tool_name, 0) >= state.get("max_tool_calls_per_tool", 2):
                    self.logger.warning("[ToolExecutionNode] Blocking duplicate/limited tool call: %s", signature)
                    duplicate = True
                    continue
                if tool_name not in self.tools_dict:
                    result = f"Error: Tool '{tool_name}' is not available"
                    state["error"] = result
                else:
                    self.logger.info("[ToolExecutionNode] Executing tool: %s", tool_name)
                    tool = self.tools_dict[tool_name]
                    try:
                        if tool.coroutine:
                            result = await asyncio.wait_for(tool.coroutine(**tool_args), timeout=self.tool_timeout_seconds)
                        elif hasattr(tool, "afunc"):
                            result = await asyncio.wait_for(tool.afunc(**tool_args), timeout=self.tool_timeout_seconds)
                        else:
                            result = await asyncio.wait_for(asyncio.to_thread(tool.func, **tool_args), timeout=self.tool_timeout_seconds)
                    except asyncio.TimeoutError:
                        result = f"Error: Tool execution timed out after {self.tool_timeout_seconds:g}s: {tool_name}"
                        state["error"] = result
                    except Exception as exc:
                        result = f"Error executing tool {tool_name}: {exc}"
                        state["error"] = result
                if tool_name == "get_candidate_details" and "Could not find" in result:
                    failed_ids.append(tool_args.get("identifier"))
                results.append(result)
                used.append(tool_name)
                executed.append(signature)
                call_counts[tool_name] = call_counts.get(tool_name, 0) + 1
                messages.append(ToolMessage(content=result, tool_call_id=call_id))

            state["tool_result"] = "\n\n".join(results) if results else state.get("tool_result")
            state["messages"] = messages
            state["tool_calls_made"] = [*state.get("tool_calls_made", []), *used]
            state["executed_tool_calls"] = executed
            state["tool_call_counts"] = call_counts
            # Only retain structured candidate fields from tool output.  Do
            # not copy arbitrary resume prose into the system fact block, both
            # to keep it compact and to avoid treating untrusted text as an
            # instruction.
            structured_facts = []
            for result in results:
                for line in str(result or "").splitlines():
                    if re.match(
                        r"^\s*(?:FILENAME|File|Name|Experience|Skills|Key Skills|"
                        r"Relevance Score|Match Score|Full resume details for)\s*:",
                        line,
                        re.IGNORECASE,
                    ):
                        structured_facts.append(line)
            state["context_facts"] = merge_key_facts(
                state.get("context_facts", []),
                structured_facts,
            )
            state["needs_tool"] = False
            state["tool_name"] = None
            state["tool_arguments"] = None
            state["pending_tool_calls"] = []
            state["duplicate_tool_call"] = duplicate
            return {
                "needs_tool": False, "tool_name": None, "tool_arguments": None,
                "pending_tool_calls": [], "tool_result": state.get("tool_result"),
                "context_facts": state.get("context_facts", []),
                "memory_extraction_skipped": state.get("memory_extraction_skipped", False),
                "tool_calls_made": state.get("tool_calls_made", []),
                "executed_tool_calls": executed, "tool_call_counts": call_counts,
                "messages": messages, "duplicate_tool_call": duplicate,
                "failed_identifiers": failed_ids,
                "error": state.get("error"), "final_answer": state.get("final_answer"),
                "iteration_count": state.get("iteration_count", 0), "max_iterations": state["max_iterations"],
            }
        except Exception as e:
            self.logger.error("[ToolExecutionNode] Unexpected error: %s", e, exc_info=True)
            return {"error": str(e), "tool_result": f"Error: {e}", "needs_tool": False, "final_answer": f"I encountered an error while executing the requested tools: {e}"}
    
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

            memory_context = self._memory_context(state)
            if memory_context:
                messages.append(SystemMessage(content=memory_context))

            facts_context = self._facts_context(state)
            if facts_context:
                messages.append(SystemMessage(content=facts_context))
            
            # Add chat history
            messages.extend(self._history_messages(state))
            
            # Add user question
            messages.append(HumanMessage(content=state["user_question"]))
            
            # Add any tool results
            if state.get("tool_result"):
                messages.append(HumanMessage(
                    content=f"Based on this information: {state['tool_result']}\n\nPlease provide a helpful response."
                ))

            limited_messages = self._fit_messages(
                messages,
                required_user_content=state["user_question"],
            )
            if limited_messages is None:
                state["error"] = "context_window_exceeded"
                state["final_answer"] = (
                    "The conversation context is too long to process safely. "
                    "Please shorten your message or start a new conversation."
                )
                state["memory_extraction_skipped"] = True
                return state
            
            # Call LLM without function calling
            response = await self.llm.ainvoke(limited_messages)
            
            state["final_answer"] = response.content
            
            if self.verbose:
                self.logger.info("[ResponseGenerationNode] Generated final answer")
            
            # Return state WITHOUT tool_calls_made
            # Only tool_execution_node should return tool_calls_made (add operator handles accumulation)
            return {
                "user_question": state["user_question"],
                "chat_history": state["chat_history"],
                "context_facts": state.get("context_facts", []),
                "memory_extraction_skipped": state.get("memory_extraction_skipped", False),
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
        logger.info("[Workflow] Ending after tool execution because a final answer exists; memory extraction is bypassed")
        return "end"
    
    # If we have an error, end
    if state.get("error"):
        logger.info("[Workflow] Ending after tool execution because of an error; memory extraction is bypassed")
        return "end"
    
    # A repeated call has no new information; generate an answer from the
    # result already available instead of sending the graph around again.
    if state.get("duplicate_tool_call"):
        return "respond"

    # If we've executed a tool, continue to reasoning.
    if state.get("tool_result"):
        return "continue"
    
    # Default: end
    return "end"
