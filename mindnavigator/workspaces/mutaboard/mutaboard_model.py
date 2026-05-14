"""Derived mixed-entity model for the MutaBoard workspace."""

from __future__ import annotations

import sys
from typing import Iterable

from mindnavigator.storage import (
    BOARD_COLUMN_COMPLETED,
    BOARD_COLUMN_DEFERRED,
    BOARD_COLUMN_IN_PROGRESS,
    DEFERRED_PRIORITY,
    IdeaData,
    ObjectData,
    TaskData,
    get_database as _storage_get_database,
)

from .mutaboard_card import (
    MUTABOARD_KIND_IDEA,
    MUTABOARD_KIND_OBJECT,
    MUTABOARD_KIND_TASK,
    MUTABOARD_STAGE_ACTIVE,
    MUTABOARD_STAGE_DONE,
    MUTABOARD_STAGE_FROZEN,
    MUTABOARD_STAGE_INBOX,
    MUTABOARD_STAGE_PREP,
    MUTABOARD_STAGE_REVIEW,
    MUTABOARD_STAGE_THINKING,
    MUTABOARD_STAGES,
    MutaBoardCard,
)

_STAGE_ORDER = {stage: index for index, stage in enumerate(MUTABOARD_STAGES)}
_KIND_ORDER = {
    MUTABOARD_KIND_TASK: 0,
    MUTABOARD_KIND_IDEA: 1,
    MUTABOARD_KIND_OBJECT: 2,
}
_TASK_ACCENT = "#c78118"
_IDEA_ACCENT = "#c1456d"
_OBJECT_ACCENT = "#6b8f3d"
_OBJECT_ACTIVE_TOKENS = {
    "active",
    "in_progress",
    "planned",
    "ready",
    "todo",
    "work",
    "working",
    "queued",
    "queue",
}
_OBJECT_DONE_TOKENS = {"done", "completed", "complete", "finished", "resolved", "closed"}
_OBJECT_FROZEN_TOKENS = {"archived", "archive", "frozen", "paused", "deferred", "on_hold"}


def get_database():
    for module_name in ("mindnavigator.workspaces.mutaboard", "mindnavigator.workspaces.mutaboard.module_impl"):
        module = sys.modules.get(module_name)
        if module is None:
            continue
        override = getattr(module, "get_database", None)
        if override is not None and override is not get_database:
            return override()
    return _storage_get_database()


class MutaBoardModel:
    """Builds unified read-only cards from tasks, ideas, and objects."""

    def __init__(self, db=None) -> None:
        self._db = db or get_database()
        self._cards: list[MutaBoardCard] = []

    def reload(self) -> list[MutaBoardCard]:
        cards: list[MutaBoardCard] = []
        cards.extend(self._build_task_card(task) for task in self._db.fetch_tasks())
        cards.extend(self._build_idea_card(idea) for idea in self._db.fetch_ideas(archived=False))
        cards.extend(self._build_idea_card(idea) for idea in self._db.fetch_ideas(archived=True))
        cards.extend(self._build_object_card(obj) for obj in self._db.fetch_objects())
        self._cards = sorted(cards, key=self._sort_key)
        return self.cards()

    def cards(self) -> list[MutaBoardCard]:
        return list(self._cards)

    def filtered_cards(
        self,
        *,
        query: str = "",
        entity_kind: str | None = None,
        project_id: int | None = None,
        actionable_only: bool = False,
        linked_only: bool | None = None,
    ) -> list[MutaBoardCard]:
        normalized_query = query.strip().lower()
        normalized_kind = self._normalize_kind(entity_kind)
        result: list[MutaBoardCard] = []
        for card in self._cards:
            if normalized_kind is not None and card.entity_kind != normalized_kind:
                continue
            if project_id is not None and card.project_id != project_id:
                continue
            if actionable_only and not card.is_actionable:
                continue
            if linked_only is True and card.total_linked_count <= 0:
                continue
            if linked_only is False and card.total_linked_count > 0:
                continue
            if normalized_query and normalized_query not in self._search_blob(card):
                continue
            result.append(card)
        return result

    def grouped_cards(self, cards: Iterable[MutaBoardCard] | None = None) -> dict[str, list[MutaBoardCard]]:
        grouped = {stage: [] for stage in MUTABOARD_STAGES}
        for card in cards if cards is not None else self._cards:
            grouped.setdefault(card.stage, []).append(card)
        return grouped

    @staticmethod
    def _normalize_kind(entity_kind: str | None) -> str | None:
        normalized = (entity_kind or "").strip().lower()
        if not normalized or normalized == "all":
            return None
        return normalized

    @staticmethod
    def _search_blob(card: MutaBoardCard) -> str:
        return " ".join(
            part.strip().lower()
            for part in (
                card.title,
                card.subtitle,
                card.project_title,
                card.meta_text,
                card.entity_kind,
                card.stage,
            )
            if part
        )

    @staticmethod
    def _sort_key(card: MutaBoardCard) -> tuple[int, int, str, str, int]:
        return (
            _STAGE_ORDER.get(card.stage, len(_STAGE_ORDER)),
            _KIND_ORDER.get(card.entity_kind, len(_KIND_ORDER)),
            (card.project_title or "").casefold(),
            (card.title or "").casefold(),
            card.entity_id,
        )

    def _build_task_card(self, task: TaskData) -> MutaBoardCard:
        stage = self._task_stage(task)
        subtitle = self._trim_excerpt(task.description)
        meta_parts = [task.project_title, task.day.isoformat(), task.priority]
        return MutaBoardCard(
            entity_kind=MUTABOARD_KIND_TASK,
            entity_id=task.id,
            title=task.title,
            subtitle=subtitle,
            stage=stage,
            project_id=task.project_id,
            project_title=task.project_title,
            accent_color=_TASK_ACCENT,
            meta_text=self._join_meta(meta_parts),
            can_drag=stage not in {MUTABOARD_STAGE_DONE, MUTABOARD_STAGE_FROZEN},
            can_mutate=True,
            is_actionable=stage not in {MUTABOARD_STAGE_DONE, MUTABOARD_STAGE_FROZEN},
            source_payload=task,
        )

    def _build_idea_card(self, idea: IdeaData) -> MutaBoardCard:
        stage = self._idea_stage(idea)
        subtitle = self._trim_excerpt(idea.summary or idea.body_md or idea.source)
        meta_parts = [idea.project_title, idea.status, idea.type]
        return MutaBoardCard(
            entity_kind=MUTABOARD_KIND_IDEA,
            entity_id=idea.id,
            title=idea.title,
            subtitle=subtitle,
            stage=stage,
            project_id=idea.project_id,
            project_title=idea.project_title,
            accent_color=_IDEA_ACCENT,
            meta_text=self._join_meta(meta_parts),
            can_drag=idea.status in {"inbox", "ripe", "work"},
            can_mutate=True,
            is_actionable=stage not in {MUTABOARD_STAGE_DONE, MUTABOARD_STAGE_FROZEN},
            source_payload=idea,
        )

    def _build_object_card(self, obj: ObjectData) -> MutaBoardCard:
        stage = self._object_stage(obj)
        subtitle = self._trim_excerpt(obj.description or self._join_meta((obj.catalog, obj.object_type)))
        meta_parts = [obj.catalog, obj.object_type, obj.status]
        return MutaBoardCard(
            entity_kind=MUTABOARD_KIND_OBJECT,
            entity_id=obj.id,
            title=obj.title,
            subtitle=subtitle,
            stage=stage,
            project_id=None,
            project_title="",
            accent_color=_OBJECT_ACCENT,
            meta_text=self._join_meta(meta_parts),
            can_drag=False,
            can_mutate=True,
            is_actionable=stage not in {MUTABOARD_STAGE_DONE, MUTABOARD_STAGE_FROZEN},
            source_payload=obj,
        )

    @staticmethod
    def _task_stage(task: TaskData) -> str:
        if task.done or task.board_column == BOARD_COLUMN_COMPLETED:
            return MUTABOARD_STAGE_DONE
        if task.priority == DEFERRED_PRIORITY or task.board_column == BOARD_COLUMN_DEFERRED:
            return MUTABOARD_STAGE_FROZEN
        if task.board_column == BOARD_COLUMN_IN_PROGRESS:
            return MUTABOARD_STAGE_ACTIVE
        return MUTABOARD_STAGE_PREP

    @staticmethod
    def _idea_stage(idea: IdeaData) -> str:
        status = (idea.status or "").strip().lower()
        if idea.archived_at is not None or status == "archived":
            return MUTABOARD_STAGE_FROZEN
        if status == "done":
            return MUTABOARD_STAGE_DONE
        if status == "work":
            return MUTABOARD_STAGE_PREP
        if status == "ripe":
            return MUTABOARD_STAGE_THINKING
        if status == "inbox":
            return MUTABOARD_STAGE_INBOX
        if status == "review":
            return MUTABOARD_STAGE_REVIEW
        return MUTABOARD_STAGE_THINKING

    @staticmethod
    def _object_stage(obj: ObjectData) -> str:
        status = (obj.status or "").strip().lower().replace("-", "_").replace(" ", "_")
        if not status:
            return MUTABOARD_STAGE_THINKING
        if status in _OBJECT_FROZEN_TOKENS:
            return MUTABOARD_STAGE_FROZEN
        if status in _OBJECT_DONE_TOKENS:
            return MUTABOARD_STAGE_DONE
        if status in _OBJECT_ACTIVE_TOKENS:
            return MUTABOARD_STAGE_ACTIVE if status in {"active", "in_progress", "work", "working"} else MUTABOARD_STAGE_PREP
        return MUTABOARD_STAGE_THINKING

    @staticmethod
    def _join_meta(parts: Iterable[str]) -> str:
        return " · ".join(part.strip() for part in parts if part and part.strip())

    @staticmethod
    def _trim_excerpt(text: str, limit: int = 120) -> str:
        normalized = " ".join((text or "").split())
        if len(normalized) <= limit:
            return normalized
        return normalized[: max(0, limit - 1)].rstrip() + "…"


__all__ = ["MutaBoardModel", "get_database"]
