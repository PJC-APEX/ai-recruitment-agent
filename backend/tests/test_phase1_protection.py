"""Local, network-free checks for the first-phase tool-loop protection."""

import asyncio
import unittest
from types import SimpleNamespace

from langchain_core.tools import Tool

from app.agents.graph_nodes import GraphNodes
from app.agents.graph_state import create_initial_state
from app.agents.workflow import create_recruitment_workflow


class FakeLLM:
    """Return two identical tool calls, then a normal final answer."""

    def __init__(self):
        self.calls = 0

    def bind_tools(self, tools):
        return self

    async def ainvoke(self, messages):
        self.calls += 1
        if self.calls in (1, 2):
            return SimpleNamespace(
                tool_calls=[{"name": "list_all_candidates", "args": {}}],
                additional_kwargs={},
                content="",
            )
        return SimpleNamespace(tool_calls=[], additional_kwargs={}, content="FINAL_ANSWER")


class FinalLLM:
    def bind_tools(self, tools):
        return self

    async def ainvoke(self, messages):
        return SimpleNamespace(tool_calls=[], additional_kwargs={}, content="FINAL_ANSWER")


class Phase1ProtectionTests(unittest.IsolatedAsyncioTestCase):
    async def test_duplicate_tool_call_is_blocked(self):
        calls = 0

        async def list_all_candidates():
            nonlocal calls
            calls += 1
            return "Total candidates in database: 1"

        tool = Tool(
            name="list_all_candidates",
            func=lambda: "unused",
            coroutine=list_all_candidates,
            description="list candidates",
        )
        llm = FakeLLM()
        graph = create_recruitment_workflow(llm, {tool.name: tool})

        result = await graph.ainvoke(
            create_initial_state("List all candidates", max_iterations=5)
        )

        self.assertEqual(calls, 1)
        self.assertEqual(result["tool_calls_made"], ["list_all_candidates"])
        self.assertTrue(result["duplicate_tool_call"])
        self.assertEqual(result["final_answer"], "FINAL_ANSWER")

    async def test_async_tool_timeout_stops_execution(self):
        async def slow_tool():
            await asyncio.sleep(0.05)
            return "should not be returned"

        tool = Tool(
            name="slow_tool",
            func=lambda: "unused",
            coroutine=slow_tool,
            description="slow test tool",
        )
        nodes = GraphNodes(
            llm=FakeLLM(),
            tools_dict={tool.name: tool},
            tool_timeout_seconds=0.001,
        )
        state = create_initial_state("run slow tool")
        state["needs_tool"] = True
        state["tool_name"] = "slow_tool"
        state["tool_arguments"] = {}

        result = await nodes.tool_execution_node(state)

        self.assertIsNotNone(result.get("error"))
        self.assertIn("timed out", result["error"])

    async def test_reasoning_increments_iteration_once(self):
        nodes = GraphNodes(llm=FinalLLM(), tools_dict={})
        state = create_initial_state("say hello", max_iterations=5)

        result = await nodes.reasoning_node(state)

        self.assertEqual(result["iteration_count"], 1)
        self.assertFalse(result["needs_tool"])
        self.assertEqual(result["final_answer"], "FINAL_ANSWER")


if __name__ == "__main__":
    unittest.main()
