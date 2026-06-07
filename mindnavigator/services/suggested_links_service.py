"""Deterministic read-only suggestions for entity links."""

from __future__ import annotations

from dataclasses import dataclass
import re

from mindnavigator.storage import EntityRef


_WORD_RE = re.compile(r"[\w-]+", re.UNICODE)


@dataclass(frozen=True)
class SuggestedEntityLink:
    target: EntityRef
    score: int
    reason: str


class SuggestedLinksService:
    def __init__(self, database) -> None:
        self._db = database

    @staticmethod
    def _keywords(*values: str) -> set[str]:
        return {
            word.casefold()
            for value in values
            for word in _WORD_RE.findall(value or "")
            if len(word) >= 4 and not word.isdigit()
        }

    def for_idea(self, idea_id: int, *, limit: int = 5) -> list[SuggestedEntityLink]:
        idea = self._db.get_idea(int(idea_id))
        if idea is None or idea.project_id is None or limit <= 0:
            return []
        idea_keywords = self._keywords(idea.title, idea.summary, idea.body_md)
        if not idea_keywords:
            return []

        linked_tasks = {
            link.other_entity.id
            for link in self._db.fetch_entity_links("idea", idea.id)
            if link.other_entity.kind == "task"
        }
        suggestions = []
        for task in self._db.fetch_tasks():
            if task.done or task.project_id != idea.project_id or task.id in linked_tasks:
                continue
            shared_keywords = sorted(idea_keywords & self._keywords(task.title, task.description))
            if not shared_keywords:
                continue
            suggestions.append(
                SuggestedEntityLink(
                    target=EntityRef("task", task.id),
                    score=len(shared_keywords),
                    reason=", ".join(shared_keywords[:3]),
                )
            )
        suggestions.sort(key=lambda item: (-item.score, item.reason, item.target.id))
        return suggestions[:limit]


__all__ = ["SuggestedEntityLink", "SuggestedLinksService"]
