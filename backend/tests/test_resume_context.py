"""Checks for separating full resume payloads from model ToolMessages."""

import asyncio
import json
from types import SimpleNamespace

from langchain_core.messages import ToolMessage

from app.agents.graph_nodes import GraphNodes
from app.agents.graph_state import create_initial_state
from app.agents.resume_context import extract_resume_comparison_fields


class CompressionLLM:
    def bind_tools(self, tools):
        return self

    async def ainvoke(self, messages):
        return SimpleNamespace(
            content=json.dumps(
                {
                    "candidate_name": "Candidate",
                    "file_name": "candidate.pdf",
                    "education": "N/A",
                    "years_experience": 1,
                    "skills": ["Python"],
                    "experience": ["API"],
                    "projects": ["Project"],
                    "evidence": ["Python API"],
                    "summary": "Compact comparison context",
                }
            ),
            tool_calls=[],
            additional_kwargs={},
        )


class CountingFallbackLLM(CompressionLLM):
    def __init__(self):
        self.calls = 0

    async def ainvoke(self, messages):
        self.calls += 1
        return await super().ainvoke(messages)


class NoCallLLM(CompressionLLM):
    async def ainvoke(self, messages):
        raise AssertionError("rule-complete resume should not call the LLM")


class ResumeTool:
    name = "get_candidate_details"
    args_schema = object()
    func = None

    async def coroutine(self, identifier):
        resume_text = f"Name: {identifier}\n" + ("Project: Python API\n" * 200)
        return json.dumps(
            {
                "kind": "candidate_resume",
                "candidate_id": identifier,
                "candidate_name": identifier,
                "file_name": f"{identifier}.pdf",
                "resume_text": resume_text,
                "content_chars": len(resume_text),
            },
            ensure_ascii=False,
        )


def _state_for_calls(*identifiers):
    state = create_initial_state("compare candidates")
    state["needs_tool"] = True
    state["pending_tool_calls"] = [
        {
            "name": "get_candidate_details",
            "args": {"identifier": identifier},
            "id": identifier,
        }
        for identifier in identifiers
    ]
    state["messages"] = [
        SimpleNamespace(
            content="",
            tool_calls=[{"name": "get_candidate_details"} for _ in identifiers],
        )
    ]
    return state


def test_multiple_full_resumes_are_not_replayed_in_tool_messages():
    async def run():
        nodes = GraphNodes(CompressionLLM(), {"get_candidate_details": ResumeTool()})
        return await nodes.tool_execution_node(_state_for_calls("A", "B"))

    result = asyncio.run(run())
    documents = result["resume_documents"]
    tool_messages = [message for message in result["messages"] if isinstance(message, ToolMessage)]

    assert len(documents) == 2
    assert all(len(document["resume_text"]) > 1000 for document in documents)
    assert len(tool_messages) == 2
    assert all(message.content.count("Project: Python API") <= 1 for message in tool_messages)
    assert all(len(message.content) < len(documents[0]["resume_text"]) // 5 for message in tool_messages)
    assert all("candidate_comparison_context" in message.content for message in tool_messages)


def test_single_full_resume_remains_available_to_reasoning():
    async def run():
        nodes = GraphNodes(CompressionLLM(), {"get_candidate_details": ResumeTool()})
        return await nodes.tool_execution_node(_state_for_calls("A"))

    result = asyncio.run(run())
    tool_messages = [message for message in result["messages"] if isinstance(message, ToolMessage)]

    assert len(result["resume_documents"]) == 1
    assert "Project: Python API" in tool_messages[0].content


def test_rule_extraction_covers_normal_structured_resume():
    fields, missing = extract_resume_comparison_fields(
        "Education: Computer Science, 2022\n"
        "Skills: Python, FastAPI, Redis\n"
        "Experience: Backend developer at Example Co, 2024\n"
        "Projects: Resume assistant built with LangGraph",
        candidate_name="Candidate",
        file_name="candidate.pdf",
    )

    assert not missing
    assert "Python" in fields["skills"]
    assert fields["experience"]
    assert fields["projects"]


def test_rule_complete_resume_skips_compression_llm():
    async def run():
        nodes = GraphNodes(NoCallLLM(), {})
        return await nodes._summarize_resume_for_comparison(
            {
                "candidate_id": "A.pdf",
                "candidate_name": "Candidate A",
                "file_name": "A.pdf",
                "resume_text": (
                    "Education: Computer Science\n"
                    "Skills: Python, FastAPI\n"
                    "Experience: Backend developer at Example Co\n"
                    "Projects: Resume assistant built with LangGraph"
                ),
            }
        )

    result = json.loads(asyncio.run(run()))
    assert result["extraction"] == "rules"
    assert result["comparison"]["skills"]


def test_missing_rule_fields_use_one_llm_fallback():
    async def run():
        llm = CountingFallbackLLM()
        nodes = GraphNodes(llm, {})
        context = await nodes._summarize_resume_for_comparison(
            {
                "candidate_id": "A.pdf",
                "candidate_name": "Candidate A",
                "file_name": "A.pdf",
                "resume_text": "Skills: Python, FastAPI",
            }
        )
        return llm.calls, json.loads(context)

    calls, result = asyncio.run(run())
    assert calls == 1
    assert result["extraction"] == "rules+llm_fallback"
