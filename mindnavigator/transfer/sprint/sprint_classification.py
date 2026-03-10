"""Keyword classification helpers for sprint task routing."""

from __future__ import annotations

from dataclasses import dataclass

from .sprint_composer import extract_semantic_token
from .sprint_parser import normalize_keyword, parse_sprint_header


@dataclass(frozen=True)
class TaskClassification:
    keyword: str
    route: str
    description: str
    parity_candidate: bool
    parity_handoff: bool = False


_CLASSIFICATION_MAP: dict[str, TaskClassification] = {
    "FIX": TaskClassification(
        keyword="FIX",
        route="fix",
        description="Bugfix or problem-resolution workflow.",
        parity_candidate=True,
    ),
    "FEAT": TaskClassification(
        keyword="FEAT",
        route="feat",
        description="Feature delivery or functional rework workflow.",
        parity_candidate=True,
    ),
    "INTEGRATION": TaskClassification(
        keyword="INTEGRATION",
        route="integration",
        description="Integration workflow with dependency and compatibility checks.",
        parity_candidate=True,
    ),
    "DESIGN": TaskClassification(
        keyword="DESIGN",
        route="design",
        description="Visual or interaction behavior workflow.",
        parity_candidate=True,
    ),
    "WORKSPACE": TaskClassification(
        keyword="WORKSPACE",
        route="workspace",
        description="Workspace-level workflow (new mode or nested mode changes).",
        parity_candidate=True,
    ),
    "REFACTOR": TaskClassification(
        keyword="REFACTOR",
        route="refactor",
        description="Refactor or regression-restoration workflow.",
        parity_candidate=True,
    ),
    "ФИЧИ": TaskClassification(
        keyword="ФИЧИ",
        route="feature-adjacent",
        description="Adjacent feature abstraction; author-specific specifics should move to parity.",
        parity_candidate=True,
        parity_handoff=True,
    ),
    "ПРОРАБОТКА": TaskClassification(
        keyword="ПРОРАБОТКА",
        route="enhancement",
        description="Enhancement of existing functionality.",
        parity_candidate=True,
    ),
}


def classify_keyword(keyword: str) -> TaskClassification | None:
    normalized = normalize_keyword(keyword)
    if not normalized:
        return None
    return _CLASSIFICATION_MAP.get(normalized)


def classify_mindnavigator_title(title: str) -> TaskClassification | None:
    parsed = parse_sprint_header(title)
    if parsed is None:
        return None

    if parsed.keyword == "TASK" and parsed.section:
        section_classification = classify_keyword(parsed.section)
        if section_classification is not None:
            return section_classification

    semantic = extract_semantic_token(parsed.title)
    if semantic:
        semantic_classification = classify_keyword(semantic)
        if semantic_classification is not None:
            return semantic_classification

    direct = classify_keyword(parsed.keyword)
    if direct is not None:
        return direct
    return None


__all__ = ["TaskClassification", "classify_keyword", "classify_mindnavigator_title"]
