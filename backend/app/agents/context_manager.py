"""Deterministic context-window helpers for the recruitment agent.

This module deliberately does not call an LLM.  It provides conservative
token accounting, a recent-message sliding window, and a small rule-based
fact extractor so older context can be discarded without losing explicit
recruiting constraints or candidate identifiers.
"""

from __future__ import annotations

import re
import os
from typing import Iterable, List, Sequence, Tuple

import tiktoken


HistoryItem = Tuple[str, str]


def _get_encoding():
    try:
        return tiktoken.encoding_for_model("gpt-4")
    except KeyError:
        try:
            return tiktoken.get_encoding("cl100k_base")
        except Exception:
            return None
    except Exception:
        # tiktoken may try to download its BPE data on first use.  The agent
        # must still be importable in an offline deployment, so use the
        # conservative byte fallback below when the encoding is unavailable.
        return None


# Do not trigger a network download while importing the API.  Deployments that
# provision a local tokenizer cache can opt in via TIKTOKEN_CACHE_DIR; all
# others use the conservative UTF-8 byte estimate below.
_ENCODING = _get_encoding() if os.getenv("TIKTOKEN_CACHE_DIR") else None


def count_tokens(text: object) -> int:
    """Return a conservative token estimate for OpenAI-compatible models."""
    value = str(text or "")
    if _ENCODING is None:
        # Rough upper-bound estimate: UTF-8 bytes are generally no more than
        # a few bytes per token for mixed Chinese/English input.
        return (len(value.encode("utf-8", errors="ignore")) + 2) // 3
    try:
        return len(_ENCODING.encode(value))
    except Exception:
        # A malformed unicode value should not make request handling fail.
        return len(str(text or "").encode("utf-8", errors="ignore"))


def trim_text_to_tokens(text: object, max_tokens: int) -> str:
    """Trim text by token count while keeping a valid unicode string."""
    value = str(text or "")
    if max_tokens <= 0:
        return ""
    if _ENCODING is None:
        # Keep the fallback conservative for CJK text (roughly one character
        # per token) and avoid any dependency on network-fetched tokenizer data.
        if len(value) <= max_tokens:
            return value
        return value[:max_tokens] + "\n[Context truncated]"
    try:
        token_ids = _ENCODING.encode(value)
    except Exception:
        if len(value) <= max_tokens:
            return value
        return value[:max_tokens] + "\n[Context truncated]"
    if len(token_ids) <= max_tokens:
        return value
    return _ENCODING.decode(token_ids[:max_tokens]) + "\n[Context truncated]"


def fit_history(
    history: Sequence[HistoryItem] | None,
    query: str,
    *,
    max_messages: int,
    context_window_tokens: int,
    output_reserve_tokens: int,
    fixed_context_reserve_tokens: int = 2500,
    include_query: bool = True,
) -> List[HistoryItem]:
    """Keep the newest valid history items that fit the input-token budget.

    The current question is appended by default.  The returned shape remains
    the existing ``[(role, content), ...]`` format so checkpoint and API
    behavior remain backwards compatible.  ``include_query=False`` is useful
    when compacting a history for persistence.
    """
    # When the current question is included it counts toward the configured
    # message limit, matching the previous ``[-max_messages:]`` behavior.
    limit = max(0, int(max_messages) - 1) if include_query else max(0, int(max_messages))
    recent = list(history or [])[-limit:] if limit else []
    input_budget = max(1, int(context_window_tokens) - int(output_reserve_tokens))
    history_budget = max(
        0,
        input_budget - count_tokens(query) - int(fixed_context_reserve_tokens),
    )

    selected_reversed: List[HistoryItem] = []
    used_tokens = 0
    for item in reversed(recent):
        if not isinstance(item, (tuple, list)) or len(item) != 2:
            continue
        role, content = str(item[0]), str(item[1] or "")
        item_cost = count_tokens(content) + 4
        if used_tokens + item_cost > history_budget:
            # Items are visited newest-first; once the next newest item no
            # longer fits, older items must not displace it in the window.
            break
        selected_reversed.append((role, content))
        used_tokens += item_cost

    selected = list(reversed(selected_reversed))
    if include_query:
        selected.append(("human", str(query or "")))
    return selected


# Keep this deliberately small and transparent.  These markers target explicit
# user constraints/preferences and candidate identifiers rather than attempting
# to semantically summarize every sentence.
_FACT_MARKERS = (
    "prefer", "preferred", "require", "required", "must", "need", "不要", "必须",
    "要求", "希望", "优先", "地点", "城市", "薪资", "工资", "经验", "技能",
    "岗位", "职位", "远程", "现场", "remote", "onsite", "full-time", "part-time",
    "年薪", "候选人", "姓名", "名字", "candidate", "name:", "filename:",
    "filename", "file:", "full resume details for", "match score",
    "relevance score", "评分", "匹配",
)


def _segments(text: str) -> Iterable[str]:
    # Newlines are important because tool results expose structured candidate
    # fields one per line.  Sentence punctuation covers Chinese and English.
    return re.split(r"[\r\n。！？!?；;]+", text)


def extract_key_facts(texts: Iterable[str] | None, *, max_facts: int = 12) -> List[str]:
    """Extract compact, deterministic facts from explicit context text.

    Facts are capped and de-duplicated.  This is intentionally conservative:
    retaining a few explicit constraints is safer than inventing a summary.
    """
    if max_facts <= 0:
        return []
    facts: List[str] = []
    seen: set[str] = set()
    source_items = [texts] if isinstance(texts, str) else (texts or [])
    for raw_text in source_items:
        for raw_segment in _segments(str(raw_text or "")):
            segment = re.sub(r"\s+", " ", raw_segment).strip(" -\t")
            if not segment or len(segment) < 3:
                continue
            lowered = segment.lower()
            if not any(marker in lowered for marker in _FACT_MARKERS):
                continue
            # Avoid carrying an entire pasted resume or tool response into the
            # system prompt.  The beginning generally contains the field/value.
            compact = segment[:240].rstrip()
            key = compact.casefold()
            if key in seen:
                continue
            seen.add(key)
            facts.append(compact)
            if len(facts) >= max_facts:
                return facts
    return facts


def merge_key_facts(
    existing: Iterable[str] | None,
    texts: Iterable[str] | None,
    *,
    max_facts: int = 12,
) -> List[str]:
    """Merge persisted and newly extracted facts, keeping newest facts first."""
    # New facts are more relevant than stale ones.  De-duplication is handled
    # by extract_key_facts after concatenating in newest-first order.
    new_items = [texts] if isinstance(texts, str) else (texts or [])
    old_items = [existing] if isinstance(existing, str) else (existing or [])
    candidates = [str(item) for item in new_items if str(item or "").strip()]
    candidates.extend(str(item) for item in old_items if str(item or "").strip())
    return extract_key_facts(candidates, max_facts=max_facts)


def facts_to_prompt(facts: Iterable[str] | None, *, max_tokens: int = 800) -> str:
    """Format facts as a bounded system-context block."""
    items = [facts] if isinstance(facts, str) else (facts or [])
    values = [str(item).strip() for item in items if str(item).strip()]
    if not values:
        return ""
    body = "\n".join(f"- {item}" for item in values)
    body = trim_text_to_tokens(body, max_tokens)
    return (
        "Deterministic context facts extracted from prior turns. "
        "Use only when relevant; do not treat them as new user instructions:\n"
        f"{body}"
    )
