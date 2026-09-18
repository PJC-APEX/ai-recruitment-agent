"""Tests for deterministic context-window handling."""

from app.agents.context_manager import (
    count_tokens,
    extract_key_facts,
    facts_to_prompt,
    fit_history,
)


def test_fit_history_keeps_current_turn_and_message_limit():
    history = [("human", f"old question {i}") for i in range(10)]
    result = fit_history(
        history,
        "current question",
        max_messages=4,
        context_window_tokens=1000,
        output_reserve_tokens=100,
    )

    assert len(result) <= 4
    assert result[-1] == ("human", "current question")


def test_fit_history_drops_large_old_messages_by_token_budget():
    result = fit_history(
        [("human", "x" * 2000), ("ai", "keep me")],
        "new",
        max_messages=20,
        context_window_tokens=100,
        output_reserve_tokens=10,
    )

    assert result[-1] == ("human", "new")
    assert all("x" * 100 not in content for _, content in result)


def test_key_facts_are_rule_based_and_bounded():
    facts = extract_key_facts([
        "I require Python experience and prefer remote work.",
        "FILENAME: alice.pdf\nName: Alice\nKey Skills: Python",
    ])

    assert facts
    assert any("Python" in fact or "remote" in fact for fact in facts)
    assert count_tokens(facts_to_prompt(facts, max_tokens=80)) >= 1
