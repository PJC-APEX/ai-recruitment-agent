"""Deterministic resume context extraction with bounded field output.

The comparison path should not require an LLM for every resume.  This module
extracts common resume sections using headings and conservative text rules;
the graph invokes an LLM only when one or more important sections are absent.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Tuple


SECTION_PATTERNS: Tuple[Tuple[str, str], ...] = (
    (
        "education",
        r"教育背景|教育经历|教育信息|学历背景|education(?:\s+background)?",
    ),
    (
        "experience",
        r"工作经历|工作经验|实习经历|实习经验|职业经历|工作履历|"
        r"experience|work\s+experience|professional\s+experience|internship(?:\s+experience)?",
    ),
    (
        "projects",
        r"项目经历|项目经验|项目实践|项目作品|projects?|project\s+experience",
    ),
    (
        "skills",
        r"专业技能|技术技能|技能特长|技能|技术栈|核心技能|"
        r"technical\s+skills?|skills?|technologies",
    ),
    ("awards", r"荣誉奖项|获奖经历|奖项|awards?|honors?"),
)

_HEADING_RE = re.compile(
    r"(?P<heading>"
    + "|".join(pattern for _, pattern in SECTION_PATTERNS)
    + r")\s*(?:[:：]|\|｜)?",
    flags=re.IGNORECASE,
)
_DATE_RE = re.compile(r"(?:19|20)\d{2}\s*[./年-]\s*(?:\d{1,2})?")
_BULLET_RE = re.compile(r"^[\s\-*•·▪◦]+|^\d+[.)、．]\s*")


def _clean_text(value: Any) -> str:
    value = str(value or "")
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = re.sub(r"[ \t]+", " ", value)
    return value.strip()


def _dedupe(items: Iterable[str], *, max_items: int, max_chars: int) -> List[str]:
    result: List[str] = []
    seen: set[str] = set()
    for raw in items:
        value = _BULLET_RE.sub("", _clean_text(raw)).strip("|｜:：;；，,")
        if not value:
            continue
        value = value[:max_chars].rstrip()
        key = re.sub(r"\s+", " ", value).casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
        if len(result) >= max_items:
            break
    return result


def _section_blocks(text: str) -> Dict[str, str]:
    """Return text between known section headings."""
    matches = list(_HEADING_RE.finditer(text))
    blocks: Dict[str, str] = {}
    for index, match in enumerate(matches):
        heading = match.group("heading").casefold()
        canonical = next(
            name
            for name, pattern in SECTION_PATTERNS
            if re.fullmatch(pattern, heading, flags=re.IGNORECASE)
        )
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[match.end():end].strip(" \t\n:：|｜")
        if body:
            blocks[canonical] = f"{blocks.get(canonical, '')}\n{body}".strip()
    return blocks


def _items_from_block(block: str, *, skills: bool = False) -> List[str]:
    separators = r"[,，、;；/|｜\n]" if skills else r"[\n|｜]"
    pieces = re.split(separators, block)
    if len(pieces) == 1:
        pieces = re.split(r"(?<=[。！？；;])\s*", block)
    return _dedupe(pieces, max_items=12, max_chars=420)


def extract_resume_comparison_fields(
    resume_text: str,
    *,
    candidate_name: str,
    file_name: str,
) -> tuple[Dict[str, Any], List[str]]:
    """Extract bounded comparison fields and report fields needing fallback."""
    text = _clean_text(resume_text)
    sections = _section_blocks(text)

    education = _dedupe(
        _items_from_block(sections.get("education", "")),
        max_items=4,
        max_chars=500,
    )
    experience = _items_from_block(sections.get("experience", ""))
    projects = _items_from_block(sections.get("projects", ""))
    skills = _items_from_block(sections.get("skills", ""), skills=True)

    # Some resumes have no headings but contain dated lines. Keep a small,
    # deterministic evidence fallback instead of sending the full text.
    if not education:
        education = _dedupe(
            [line for line in text.splitlines() if any(token in line for token in ("大学", "学院", "本科", "硕士", "Bachelor", "Master"))],
            max_items=3,
            max_chars=500,
        )
    if not experience:
        experience = _dedupe(
            [line for line in text.splitlines() if _DATE_RE.search(line) and any(token in line.lower() for token in ("公司", "实习", "工作", "engineer", "developer"))],
            max_items=6,
            max_chars=420,
        )
    if not skills:
        known = (
            "Python", "Java", "JavaScript", "FastAPI", "Django", "LangChain",
            "LangGraph", "LLM", "Docker", "MySQL", "Redis", "Chroma", "FAISS",
            "Git", "pytest", "SQL", "C++", "React",
        )
        skills = [item for item in known if re.search(rf"(?<!\w){re.escape(item)}(?!\w)", text, re.IGNORECASE)]

    evidence = _dedupe(
        [*education[:2], *experience[:2], *projects[:2]],
        max_items=6,
        max_chars=360,
    )
    summary_parts = []
    if education:
        summary_parts.append(education[0])
    if skills:
        summary_parts.append("Skills: " + ", ".join(skills[:8]))
    if experience:
        summary_parts.append("Experience: " + experience[0])
    if projects:
        summary_parts.append("Project: " + projects[0])

    fields: Dict[str, Any] = {
        "candidate_name": candidate_name,
        "file_name": file_name,
        "education": education,
        "years_experience": None,
        "skills": skills,
        "experience": experience,
        "projects": projects,
        "evidence": evidence,
        "summary": "；".join(summary_parts)[:900],
    }
    required = ("education", "skills", "experience", "projects")
    missing = [field for field in required if not fields[field]]
    return fields, missing
