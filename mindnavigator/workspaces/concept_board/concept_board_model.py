"""Unified entity model for the ConceptBoard workspace."""

from __future__ import annotations

import sys
from typing import Iterable

from mindnavigator.storage import (
    CloudFileData,
    IdeaData,
    IdeaRelationData,
    MapData,
    MapMarkerData,
    NoteData,
    ObjectData,
    ProjectData,
    TaskAttachmentData,
    TaskData,
    get_database as _storage_get_database,
)

from .concept_board_card import (
    CONCEPT_BOARD_KIND_FILE,
    CONCEPT_BOARD_KIND_LINK,
    CONCEPT_BOARD_KIND_SOLUTION,
    CONCEPT_BOARD_KIND_VERSION,
    CONCEPT_BOARD_KIND_IDEA,
    CONCEPT_BOARD_KIND_IMAGE,
    CONCEPT_BOARD_KIND_MAP,
    CONCEPT_BOARD_KIND_MARKER,
    CONCEPT_BOARD_KIND_NOTE,
    CONCEPT_BOARD_KIND_OBJECT,
    CONCEPT_BOARD_KIND_PROJECT,
    CONCEPT_BOARD_KIND_TASK,
    ConceptBoardCard,
)

_KIND_ORDER = {
    CONCEPT_BOARD_KIND_TASK: 0,
    CONCEPT_BOARD_KIND_IDEA: 1,
    CONCEPT_BOARD_KIND_IMAGE: 2,
    CONCEPT_BOARD_KIND_MAP: 3,
    CONCEPT_BOARD_KIND_MARKER: 4,
    CONCEPT_BOARD_KIND_NOTE: 5,
    CONCEPT_BOARD_KIND_PROJECT: 6,
    CONCEPT_BOARD_KIND_OBJECT: 7,
    CONCEPT_BOARD_KIND_VERSION: 8,
    CONCEPT_BOARD_KIND_SOLUTION: 9,
    CONCEPT_BOARD_KIND_FILE: 10,
    CONCEPT_BOARD_KIND_LINK: 11,
}
_ACCENTS = {
    CONCEPT_BOARD_KIND_TASK: "#6f8cff",
    CONCEPT_BOARD_KIND_IDEA: "#6ad56f",
    CONCEPT_BOARD_KIND_IMAGE: "#ffd56a",
    CONCEPT_BOARD_KIND_MAP: "#73d0ff",
    CONCEPT_BOARD_KIND_MARKER: "#f58bff",
    CONCEPT_BOARD_KIND_NOTE: "#ffb56f",
    CONCEPT_BOARD_KIND_PROJECT: "#8da2ff",
    CONCEPT_BOARD_KIND_OBJECT: "#9ad26b",
    CONCEPT_BOARD_KIND_VERSION: "#a88cff",
    CONCEPT_BOARD_KIND_SOLUTION: "#49c36b",
    CONCEPT_BOARD_KIND_FILE: "#87b6ff",
    CONCEPT_BOARD_KIND_LINK: "#7ad7d2",
}


def get_database():
    for module_name in ("mindnavigator.workspaces.concept_board", "mindnavigator.workspaces.concept_board.module_impl"):
        module = sys.modules.get(module_name)
        if module is None:
            continue
        override = getattr(module, "get_database", None)
        if override is not None and override is not get_database:
            return override()
    return _storage_get_database()


class ConceptBoardModel:
    """Builds a unified catalog of entities available for concept board columns."""

    def __init__(self, db=None) -> None:
        self._db = db or get_database()
        self._cards: list[ConceptBoardCard] = []
        self._cards_by_key: dict[tuple[str, int], ConceptBoardCard] = {}
        self._map_titles: dict[int, str] = {}
        self._markers_by_map_id: dict[int, list[MapMarkerData]] = {}

    def reload(self) -> list[ConceptBoardCard]:
        tasks = self._db.fetch_tasks()
        active_ideas = self._db.fetch_ideas(archived=False)
        archived_ideas = self._db.fetch_ideas(archived=True)
        ideas = [*active_ideas, *archived_ideas]
        objects = self._db.fetch_objects()
        notes = self._db.fetch_notes()
        projects = self._db.fetch_projects()
        maps = self._db.fetch_maps()
        markers = self._db.fetch_map_markers()
        images = [item for item in self._db.fetch_cloud_files() if getattr(item, "is_image", False)]

        task_attachments = {task.id: self._db.fetch_task_attachments(task.id) for task in tasks}
        idea_relations = {idea.id: self._db.fetch_idea_relations(idea.id) for idea in ideas}
        object_counts = self._collect_object_link_counts(task_attachments, idea_relations)
        self._map_titles = {item.id: item.title for item in maps}
        self._markers_by_map_id = {}
        for marker in markers:
            self._markers_by_map_id.setdefault(marker.map_id, []).append(marker)

        cards: list[ConceptBoardCard] = []
        cards.extend(self._build_task_card(task, task_attachments.get(task.id, [])) for task in tasks)
        cards.extend(self._build_idea_card(idea, idea_relations.get(idea.id, [])) for idea in ideas)
        cards.extend(self._build_object_card(obj, object_counts.get(obj.id, {})) for obj in objects)
        cards.extend(self._build_note_card(note) for note in notes)
        cards.extend(self._build_project_card(project) for project in projects)
        cards.extend(self._build_map_card(map_item) for map_item in maps)
        cards.extend(self._build_marker_card(marker) for marker in markers)
        cards.extend(self._build_image_card(item) for item in images)

        self._cards = sorted(cards, key=self._sort_key)
        self._cards_by_key = {(card.entity_kind, card.entity_id): card for card in self._cards}
        return self.cards()

    def cards(self) -> list[ConceptBoardCard]:
        return list(self._cards)

    def get_card(self, entity_kind: str, entity_id: int) -> ConceptBoardCard | None:
        return self._cards_by_key.get((entity_kind, entity_id))

    def map_marker_count(self, map_id: int) -> int:
        return len(self._markers_by_map_id.get(map_id, []))

    def filtered_cards(
        self,
        *,
        query: str = "",
        entity_kind: str | None = None,
        project_id: int | None = None,
        actionable_only: bool = False,
        linked_only: bool | None = None,
    ) -> list[ConceptBoardCard]:
        normalized_query = query.strip().lower()
        normalized_kind = self._normalize_kind(entity_kind)
        result: list[ConceptBoardCard] = []
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

    def grouped_cards_by_kind(
        self,
        column_kinds: Iterable[str],
        cards: Iterable[ConceptBoardCard] | None = None,
    ) -> dict[str, list[ConceptBoardCard]]:
        grouped = {kind: [] for kind in column_kinds}
        for card in cards if cards is not None else self._cards:
            grouped.setdefault(card.entity_kind, []).append(card)
        return grouped

    @staticmethod
    def _normalize_kind(entity_kind: str | None) -> str | None:
        normalized = (entity_kind or "").strip().lower()
        return normalized or None

    @staticmethod
    def _search_blob(card: ConceptBoardCard) -> str:
        return " ".join(
            part.strip().lower()
            for part in (
                card.title,
                card.subtitle,
                card.project_title,
                card.meta_text,
                card.entity_kind,
                card.link_summary,
            )
            if part
        )

    @staticmethod
    def _sort_key(card: ConceptBoardCard) -> tuple[int, str, str, int]:
        return (
            _KIND_ORDER.get(card.entity_kind, len(_KIND_ORDER)),
            (card.project_title or "").casefold(),
            (card.title or "").casefold(),
            card.entity_id,
        )

    def _build_task_card(self, task: TaskData, attachments: list[TaskAttachmentData]) -> ConceptBoardCard:
        linked_task_count = sum(1 for attachment in attachments if attachment.kind == "task")
        linked_idea_count = sum(1 for attachment in attachments if attachment.kind == "idea")
        linked_object_count = sum(1 for attachment in attachments if attachment.kind == "object")
        return ConceptBoardCard(
            entity_kind=CONCEPT_BOARD_KIND_TASK,
            entity_id=task.id,
            title=task.title,
            subtitle=self._trim_excerpt(task.description),
            project_id=task.project_id,
            project_title=task.project_title,
            accent_color=_ACCENTS[CONCEPT_BOARD_KIND_TASK],
            meta_text=self._join_meta((task.project_title, task.day.isoformat(), task.priority)),
            relation_count=linked_task_count + linked_idea_count + linked_object_count,
            relation_summary=f"Связи · {linked_task_count + linked_idea_count + linked_object_count}",
            linked_task_count=linked_task_count,
            linked_idea_count=linked_idea_count,
            linked_object_count=linked_object_count,
            is_actionable=not task.done,
            source_payload=task,
        )

    def _build_idea_card(self, idea: IdeaData, relations: list[IdeaRelationData]) -> ConceptBoardCard:
        linked_task_count = sum(1 for relation in relations if relation.entity_type == "task")
        linked_idea_count = sum(1 for relation in relations if relation.entity_type == "idea")
        linked_object_count = sum(1 for relation in relations if relation.entity_type == "object")
        relation_count = len(relations)
        return ConceptBoardCard(
            entity_kind=CONCEPT_BOARD_KIND_IDEA,
            entity_id=idea.id,
            title=idea.title,
            subtitle=self._trim_excerpt(idea.summary or idea.body_md or idea.source),
            project_id=idea.project_id,
            project_title=idea.project_title,
            accent_color=_ACCENTS[CONCEPT_BOARD_KIND_IDEA],
            meta_text=self._join_meta((idea.project_title, idea.status, idea.type)),
            relation_count=relation_count,
            relation_summary=f"Связи · {relation_count}",
            linked_task_count=linked_task_count,
            linked_idea_count=linked_idea_count,
            linked_object_count=linked_object_count,
            is_actionable=idea.archived_at is None and idea.status != "done",
            source_payload=idea,
        )

    def _build_object_card(self, obj: ObjectData, object_counts: dict[str, int]) -> ConceptBoardCard:
        linked_task_count = max(0, int(object_counts.get("task", 0)))
        linked_idea_count = max(0, int(object_counts.get("idea", 0)))
        linked_object_count = max(0, int(object_counts.get("object", 0)))
        relation_count = linked_task_count + linked_idea_count + linked_object_count
        return ConceptBoardCard(
            entity_kind=CONCEPT_BOARD_KIND_OBJECT,
            entity_id=obj.id,
            title=obj.title,
            subtitle=self._trim_excerpt(obj.description or self._join_meta((obj.catalog, obj.object_type))),
            project_id=None,
            project_title="",
            accent_color=_ACCENTS[CONCEPT_BOARD_KIND_OBJECT],
            meta_text=self._join_meta((obj.catalog, obj.object_type, obj.status)),
            relation_count=relation_count,
            relation_summary=f"Связи · {relation_count}",
            linked_task_count=linked_task_count,
            linked_idea_count=linked_idea_count,
            linked_object_count=linked_object_count,
            is_actionable=str(obj.status or "").strip().lower() not in {"archived", "done", "completed"},
            source_payload=obj,
        )

    def _build_note_card(self, note: NoteData) -> ConceptBoardCard:
        tag_text = f"Теги {len(note.tags)}" if note.tags else ""
        return ConceptBoardCard(
            entity_kind=CONCEPT_BOARD_KIND_NOTE,
            entity_id=note.id,
            title=note.title,
            subtitle=self._trim_excerpt(note.preview),
            project_id=None,
            project_title=note.project,
            accent_color=_ACCENTS[CONCEPT_BOARD_KIND_NOTE],
            meta_text=self._join_meta((note.project, tag_text)),
            relation_summary="Связи · 0",
            is_actionable=not note.locked,
            source_payload=note,
        )

    def _build_project_card(self, project: ProjectData) -> ConceptBoardCard:
        relation_count = sum(
            1
            for value in (project.linked_map_id, project.linked_note_id, project.linked_object_id)
            if value is not None
        )
        return ConceptBoardCard(
            entity_kind=CONCEPT_BOARD_KIND_PROJECT,
            entity_id=project.id,
            title=project.title,
            subtitle=self._trim_excerpt(project.area),
            project_id=project.id,
            project_title=project.title,
            accent_color=_ACCENTS[CONCEPT_BOARD_KIND_PROJECT],
            meta_text=self._join_meta((project.area, project.priority)),
            relation_count=relation_count,
            relation_summary=f"Связи · {relation_count}",
            is_actionable=not project.archived,
            source_payload=project,
        )

    def _build_map_card(self, map_item: MapData) -> ConceptBoardCard:
        marker_count = self.map_marker_count(map_item.id)
        return ConceptBoardCard(
            entity_kind=CONCEPT_BOARD_KIND_MAP,
            entity_id=map_item.id,
            title=map_item.title,
            subtitle=self._trim_excerpt(map_item.description),
            project_id=None,
            project_title=map_item.project,
            accent_color=_ACCENTS[CONCEPT_BOARD_KIND_MAP],
            meta_text=self._join_meta((map_item.project, f"Метки {marker_count}")),
            relation_count=marker_count,
            relation_summary=f"Метки · {marker_count}",
            source_payload=map_item,
        )

    def _build_marker_card(self, marker: MapMarkerData) -> ConceptBoardCard:
        relation_count = (
            len(marker.task_ids)
            + len(marker.project_ids)
            + len(marker.note_ids)
            + len(marker.object_ids)
            + len(marker.file_ids)
            + len(marker.map_ids)
            + len(marker.marker_ids)
        )
        return ConceptBoardCard(
            entity_kind=CONCEPT_BOARD_KIND_MARKER,
            entity_id=marker.id,
            title=marker.name,
            subtitle=self._trim_excerpt(marker.description or marker.parent_path),
            project_id=None,
            project_title=self._map_titles.get(marker.map_id, ""),
            accent_color=_ACCENTS[CONCEPT_BOARD_KIND_MARKER],
            meta_text=self._join_meta((self._map_titles.get(marker.map_id, ""), marker.type)),
            relation_count=relation_count,
            relation_summary=f"Связи · {relation_count}",
            linked_task_count=len(marker.task_ids),
            linked_object_count=len(marker.object_ids),
            source_payload=marker,
        )

    def _build_image_card(self, cloud_file: CloudFileData) -> ConceptBoardCard:
        return ConceptBoardCard(
            entity_kind=CONCEPT_BOARD_KIND_IMAGE,
            entity_id=cloud_file.id,
            title=cloud_file.name or cloud_file.rel_path,
            subtitle=self._trim_excerpt(cloud_file.description or cloud_file.rel_path),
            project_id=None,
            project_title="",
            accent_color=_ACCENTS[CONCEPT_BOARD_KIND_IMAGE],
            meta_text=self._join_meta((cloud_file.rel_path, f"{cloud_file.size} B" if cloud_file.size else "")),
            relation_summary="Связи · 0",
            source_payload=cloud_file,
        )

    @staticmethod
    def _collect_object_link_counts(
        task_attachments: dict[int, list[TaskAttachmentData]],
        idea_relations: dict[int, list[IdeaRelationData]],
    ) -> dict[int, dict[str, int]]:
        counts: dict[int, dict[str, int]] = {}
        for attachments in task_attachments.values():
            for attachment in attachments:
                if attachment.kind != "object":
                    continue
                payload = counts.setdefault(attachment.ref_id, {"task": 0, "idea": 0, "object": 0})
                payload["task"] += 1
        for relations in idea_relations.values():
            for relation in relations:
                if relation.entity_type != "object":
                    continue
                payload = counts.setdefault(relation.entity_id, {"task": 0, "idea": 0, "object": 0})
                payload["idea"] += 1
        return counts

    @staticmethod
    def _join_meta(parts: Iterable[str]) -> str:
        return " · ".join(str(part).strip() for part in parts if str(part or "").strip())

    @staticmethod
    def _trim_excerpt(text: str, limit: int = 120) -> str:
        normalized = " ".join(str(text or "").split())
        if len(normalized) <= limit:
            return normalized
        return normalized[: limit - 1].rstrip() + "…"


ConceptBoardModel = ConceptBoardModel

__all__ = ["ConceptBoardModel", "ConceptBoardModel", "get_database"]
