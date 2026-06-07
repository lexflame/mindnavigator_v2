"""Declarative quick actions available for global search results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class SearchResultAction:
    id: str
    title: str


class SearchResultActionRegistry:
    """Returns supported actions without executing UI or domain operations."""

    _OPEN_ACTION = SearchResultAction("open", "Перейти")
    _TASK_ACTIONS = (
        SearchResultAction("task.view", "Просмотреть карточку"),
        SearchResultAction("task.edit", "Редактировать"),
    )
    _SUPPORTED_ENTITIES = {
        "task",
        "project",
        "map",
        "marker",
        "note",
        "idea",
        "file",
        "object",
        "collection",
        "character",
    }

    def actions_for(self, payload: Mapping[str, object]) -> tuple[SearchResultAction, ...]:
        entity = str(payload.get("entity") or "")
        if entity not in self._SUPPORTED_ENTITIES or payload.get("id") is None:
            return ()
        if entity == "task":
            return (self._OPEN_ACTION, *self._TASK_ACTIONS)
        return (self._OPEN_ACTION,)


__all__ = ["SearchResultAction", "SearchResultActionRegistry"]
