"""Helpers for parsing MindNavigator sprint task headers."""

from __future__ import annotations

from dataclasses import dataclass


_CANONICAL_KEYWORDS: dict[str, str] = {
    "SPRINT": "SPRINT",
    "PARTITION": "PARTITION",
    "TASK": "TASK",
    "ADDON": "ADDON",
    "FIX": "FIX",
    "FEAT": "FEAT",
    "INTEGRATION": "INTEGRATION",
    "DESIGN": "DESIGN",
    "WORKSPACE": "WORKSPACE",
    "REFACTOR": "REFACTOR",
    "ФИЧИ": "ФИЧИ",
    "ПРОРАБОТКА": "ПРОРАБОТКА",
}

_KEYWORD_ALIASES: dict[str, str] = {
    "SPTRINT": "SPRINT",
    "PARTIOTION": "PARTITION",
    "REAFACTOR": "REFACTOR",
}


@dataclass(frozen=True)
class ParsedSprintHeader:
    keyword: str
    section: str
    title: str
    source_format: str
    raw_title: str


def normalize_keyword(raw_keyword: str) -> str | None:
    cleaned = (raw_keyword or "").strip().lstrip("#").strip()
    if not cleaned:
        return None
    upper = cleaned.upper()
    if upper in _CANONICAL_KEYWORDS:
        return _CANONICAL_KEYWORDS[upper]
    alias_target = _KEYWORD_ALIASES.get(upper)
    if alias_target:
        return _CANONICAL_KEYWORDS.get(alias_target)
    return None


def parse_sprint_header(title: str) -> ParsedSprintHeader | None:
    raw_title = (title or "").strip()
    if not raw_title:
        return None
    parts = [part.strip() for part in raw_title.split("::")]
    if len(parts) < 2:
        return None

    keyword = normalize_keyword(parts[0])
    if not keyword:
        return None

    if len(parts) >= 3:
        section = parts[1]
        parsed_title = "::".join(parts[2:]).strip()
        source_format = "extended"
    else:
        section = ""
        parsed_title = parts[1]
        source_format = "short"

    if not parsed_title:
        return None

    return ParsedSprintHeader(
        keyword=keyword,
        section=section,
        title=parsed_title,
        source_format=source_format,
        raw_title=raw_title,
    )

