"""Run the small, deterministic RAG evaluation set against the chat API.

This first evaluator intentionally does not use an LLM judge.  It records the
actual response and performs only simple checks, so every failed case can be
reviewed by a person.

Usage (backend server must already be running):

    python -m evals.run_rag_eval
    python -m evals.run_rag_eval --base-url http://localhost:8000/api
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, List

import httpx


DEFAULT_BASE_URL = "http://localhost:8000/api"
DEFAULT_CASES = Path(__file__).with_name("rag_cases.jsonl")


def load_cases(path: Path) -> List[Dict[str, Any]]:
    cases: List[Dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            case = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON on line {line_number}: {exc}") from exc
        if not isinstance(case, dict) or not case.get("id") or not case.get("query"):
            raise ValueError(f"Case on line {line_number} needs id and query")
        cases.append(case)
    return cases


def _returned_files(response: Dict[str, Any]) -> List[str]:
    data = response.get("data") or {}
    documents = data.get("resume_documents") or []
    return [
        str(item.get("file_name"))
        for item in documents
        if isinstance(item, dict) and item.get("file_name")
    ]


def _contains_any(text: str, values: Iterable[str]) -> bool:
    lowered = text.casefold()
    return any(str(value).casefold() in lowered for value in values if value)


def evaluate_case(case: Dict[str, Any], response: Dict[str, Any]) -> Dict[str, Any]:
    answer = str(response.get("response") or "")
    returned_files = _returned_files(response)
    expected_file = case.get("expected_file")
    expected_files = [str(item) for item in case.get("expected_files") or []]
    forbidden = [str(item) for item in case.get("forbidden_candidates") or []]
    facts = [str(item) for item in case.get("expected_facts") or []]
    expected_no_documents = bool(case.get("expected_no_documents", False))

    identity_ok = True
    if expected_no_documents:
        identity_ok = not returned_files
    if expected_file:
        # Detail lookups expose exact files in resume_documents.  If the tool
        # was search_candidates, fall back to checking the answer text.
        identity_ok = expected_file in returned_files or expected_file in answer
    if expected_files:
        identity_ok = all(
            item in returned_files or item in answer for item in expected_files
        )

    forbidden_ok = not any(
        forbidden_name in returned_files for forbidden_name in forbidden
    )
    duplicate_ok = len(returned_files) == len(set(returned_files))
    facts_found = [fact for fact in facts if fact.casefold() in answer.casefold()]
    facts_ok = len(facts_found) == len(facts) if facts else True

    # Hallucination/groundedness still need manual review in this first step.
    return {
        "id": case["id"],
        "category": case.get("category"),
        "query": case["query"],
        "identity_ok": identity_ok,
        "forbidden_ok": forbidden_ok,
        "facts_ok": facts_ok,
        "duplicate_ok": duplicate_ok,
        "expected_no_documents": expected_no_documents,
        "facts_found": facts_found,
        "returned_files": returned_files,
        "tools_used": (response.get("data") or {}).get("agent_tools_used", []),
        "manual_review_required": True,
        "answer": answer,
    }


def _percentage(results: List[Dict[str, Any]], field: str, predicate=None) -> Dict[str, Any]:
    """Aggregate a boolean result field into a percentage and counts."""
    eligible = [
        result
        for result in results
        if "error" not in result and (predicate(result) if predicate else True)
    ]
    passed = sum(1 for result in eligible if result.get(field) is True)
    total = len(eligible)
    return {
        "passed": passed,
        "total": total,
        "percentage": round((passed / total) * 100, 2) if total else None,
    }


def aggregate_results(cases: List[Dict[str, Any]], results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build the dashboard-style percentages shown by the evaluation summary."""
    case_by_id = {case["id"]: case for case in cases}

    def category_in(*categories: str):
        return lambda result: case_by_id.get(result.get("id"), {}).get("category") in categories

    metrics = {
        # Exact/similar names, filenames, ambiguity and not-found behavior.
        "identity_accuracy": _percentage(
            results,
            "identity_ok",
            category_in(
                "exact_name",
                "similar_name",
                "ambiguous_name",
                "filename",
                "missing_filename",
                "name_and_filename",
                "nonexistent_candidate",
            ),
        ),
        "retrieval_fact_accuracy": _percentage(
            results,
            "facts_ok",
            lambda result: bool(case_by_id.get(result.get("id"), {}).get("expected_facts")),
        ),
        "forbidden_candidate_accuracy": _percentage(results, "forbidden_ok"),
        "duplicate_free_rate": _percentage(results, "duplicate_ok"),
    }

    automated_pass = [
        result
        for result in results
        if "error" not in result
        and result.get("identity_ok") is True
        and result.get("forbidden_ok") is True
        and result.get("facts_ok") is True
        and result.get("duplicate_ok") is True
    ]
    valid_results = [result for result in results if "error" not in result]
    metrics["overall_automated_pass_rate"] = {
        "passed": len(automated_pass),
        "total": len(valid_results),
        "percentage": round((len(automated_pass) / len(valid_results)) * 100, 2)
        if valid_results
        else None,
    }

    return {
        "case_count": len(cases),
        "valid_case_count": len(valid_results),
        "failed_request_count": len(results) - len(valid_results),
        "manual_review_count": sum(
            1 for result in results if result.get("manual_review_required")
        ),
        "metrics": metrics,
        "notes": {
            "groundedness": "Requires manual review in rag_eval_results.json",
            "hallucination_rate": "Requires manual review in rag_eval_results.json",
            "percentage_scale": "Summary metric values are percentages from 0 to 100",
        },
    }


def create_langfuse_client() -> Any:
    """Create a Langfuse client from the backend .env, if configured."""
    try:
        from dotenv import load_dotenv
        from langfuse import Langfuse

        load_dotenv(Path(__file__).resolve().parents[1] / ".env")
        public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
        secret_key = os.getenv("LANGFUSE_SECRET_KEY")
        host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
        if not public_key or not secret_key:
            print("Langfuse skipped: LANGFUSE_PUBLIC_KEY/SECRET_KEY not configured")
            return None
        return Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            host=host,
            sample_rate=1.0,
        )
    except Exception as exc:
        print(f"Langfuse skipped: {exc}")
        return None


def write_langfuse_scores(client: Any, case: Dict[str, Any], result: Dict[str, Any]) -> str | None:
    """Write objective evaluator scores to a dedicated Langfuse trace.

    Each case creates one evaluator trace.  Scores are attached to that trace
    with ``client.create_score(trace_id=...)``; the API call is intentionally
    explicit so the score-writing flow is easy to inspect and learn from.
    """
    if client is None:
        return None
    trace_id = None
    try:
        with client.start_as_current_observation(
            name=f"rag_eval.{case['id']}",
            as_type="evaluator",
            input={
                "query": case["query"],
                "expected_file": case.get("expected_file"),
                "expected_files": case.get("expected_files", []),
                "expected_facts": case.get("expected_facts", []),
            },
            metadata={"category": case.get("category"), "eval_case_id": case["id"]},
        ) as observation:
            trace_id = getattr(observation, "trace_id", None)
            observation.update(
                output={
                    "returned_files": result.get("returned_files", []),
                    "facts_found": result.get("facts_found", []),
                    "answer": str(result.get("answer", ""))[:4000],
                }
            )
            score_values = {
                "identity_accuracy": result.get("identity_ok", False),
                "forbidden_candidate_accuracy": result.get("forbidden_ok", False),
                "retrieval_fact_accuracy": result.get("facts_ok", False),
                "duplicate_free": result.get("duplicate_ok", False),
            }
            for name, passed in score_values.items():
                if trace_id:
                    client.create_score(
                        name=name,
                        value=1.0 if passed else 0.0,
                        trace_id=trace_id,
                        data_type="NUMERIC",
                        comment=f"Automated RAG evaluator score for {case['id']}",
                    )
        return trace_id
    except Exception as exc:
        print(f"Langfuse write failed for {case['id']}: {exc}")
        return None


def write_langfuse_summary(client: Any, summary: Dict[str, Any]) -> str | None:
    """Write aggregate percentage scores to one Langfuse evaluator trace."""
    if client is None:
        return None

    try:
        with client.start_as_current_observation(
            name="rag_eval.summary",
            as_type="evaluator",
            input={"case_count": summary["case_count"]},
            output=summary,
            metadata={"type": "aggregate", "scale": "percentage_0_to_100"},
        ) as observation:
            trace_id = getattr(observation, "trace_id", None)
            if trace_id:
                for name, metric in summary["metrics"].items():
                    percentage = metric.get("percentage")
                    if percentage is None:
                        continue
                    client.create_score(
                        name=name,
                        value=percentage,
                        trace_id=trace_id,
                        data_type="NUMERIC",
                        comment=(
                            f"Aggregate percentage: {metric['passed']}/{metric['total']} "
                            f"valid cases"
                        ),
                    )
            return trace_id
    except Exception as exc:
        print(f"Langfuse summary write failed: {exc}")
        return None


async def run(base_url: str, cases: List[Dict[str, Any]], langfuse_client: Any = None) -> List[Dict[str, Any]]:
    timeout = httpx.Timeout(120.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        results: List[Dict[str, Any]] = []
        for case in cases:
            try:
                response = await client.post(
                    f"{base_url.rstrip('/')}/chat",
                    json={
                        "message": case["query"],
                        "session_id": f"rag-eval-{case['id']}-{uuid.uuid4().hex[:8]}",
                        "chat_history": [],
                    },
                )
                response.raise_for_status()
                payload = response.json()
                result = evaluate_case(case, payload)
            except Exception as exc:
                result = {
                    "id": case["id"],
                    "category": case.get("category"),
                    "query": case["query"],
                    "error": str(exc),
                    "identity_ok": False,
                    "forbidden_ok": False,
                    "facts_ok": False,
                    "manual_review_required": True,
                }
            results.append(result)
            if langfuse_client is not None and "error" not in result:
                result["langfuse_trace_id"] = write_langfuse_scores(
                    langfuse_client,
                    case,
                    result,
                )
            status = (
                "PASS"
                if result.get("identity_ok")
                and result.get("forbidden_ok")
                and result.get("facts_ok")
                and result.get("duplicate_ok")
                else "CHECK"
            )
            print(f"[{status}] {case['id']} - {case['query']}")
            print(f"       files={result.get('returned_files', [])} facts={result.get('facts_found', [])}")
        return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--output", type=Path, default=Path("rag_eval_results.json"))
    parser.add_argument(
        "--summary-output",
        type=Path,
        default=Path("rag_eval_summary.json"),
    )
    parser.add_argument(
        "--langfuse",
        action="store_true",
        help="Write one evaluator trace and objective scores per case",
    )
    args = parser.parse_args()

    cases = load_cases(args.cases)
    langfuse_client = create_langfuse_client() if args.langfuse else None
    results = asyncio.run(run(args.base_url, cases, langfuse_client))
    summary = aggregate_results(cases, results)
    args.summary_output.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print("\nAggregate percentages:")
    for name, metric in summary["metrics"].items():
        print(
            f"  {name}: {metric['percentage']}% "
            f"({metric['passed']}/{metric['total']})"
        )
    if langfuse_client is not None:
        summary_trace_id = write_langfuse_summary(langfuse_client, summary)
        print(f"Langfuse summary trace: {summary_trace_id or 'not written'}")
        langfuse_client.flush()
    args.output.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nSaved detailed results to {args.output}")
    print("Review each result's answer for groundedness and hallucination.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
