from __future__ import annotations

from datetime import date, datetime, timezone

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

import mindnavigator.workspaces.mutaboard.module_impl as mutaboard_module
from mindnavigator.storage import (
    BOARD_COLUMN_COMPLETED,
    BOARD_COLUMN_DEFERRED,
    BOARD_COLUMN_IN_PROGRESS,
    BOARD_COLUMN_QUEUE,
    IdeaData,
    IdeaRelationData,
    ObjectData,
    TaskData,
    TaskAttachmentData,
)


class _MutaBoardWorkspaceDbStub:
    def __init__(self) -> None:
        self._now = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)
        self._tasks = [
            TaskData(
                id=101,
                day=date(2026, 5, 14),
                time_text="09:30",
                title="Task board item",
                description="Workspace task description",
                priority="Medium",
                done=False,
                board_column=BOARD_COLUMN_QUEUE,
                project_id=5,
                project_title="Workspace Project",
            )
        ]
        self._ideas_active = [
            IdeaData(
                id=202,
                project_id=5,
                title="Idea board item",
                summary="Idea summary text",
                body_md="",
                type="feature",
                status="ripe",
                value_score=4,
                effort_score=2,
                source="",
                created_at=self._now,
                updated_at=self._now,
                archived_at=None,
                project_title="Workspace Project",
            )
        ]
        self._ideas_archived: list[IdeaData] = []
        self._objects = [
            ObjectData(
                id=303,
                title="Object board item",
                catalog="Infra",
                object_type="service",
                status="active",
                description="Object summary text",
                created_at="2026-05-14T10:00:00+00:00",
                updated_at="2026-05-14T11:00:00+00:00",
            )
        ]
        self.task_move_calls: list[tuple[int, str]] = []
        self.idea_update_calls: list[tuple[int, str]] = []
        self.idea_archive_calls: list[tuple[int, bool]] = []
        self.created_task_ids: list[int] = []
        self.created_idea_ids: list[int] = []
        self.created_object_ids: list[int] = []
        self.idea_relation_calls: list[tuple[int, str, int]] = []
        self.task_attachment_calls: list[tuple[int, str, int]] = []
        self._idea_relations: dict[int, list[IdeaRelationData]] = {}
        self._task_attachments: dict[int, list[TaskAttachmentData]] = {}
        self._next_task_id = 1000
        self._next_idea_id = 2000
        self._next_object_id = 3000

    def fetch_tasks(self):
        return list(self._tasks)

    def fetch_ideas(self, archived=True):
        return list(self._ideas_archived if archived else self._ideas_active)

    def fetch_objects(self):
        return list(self._objects)

    def fetch_task_attachments(self, task_id: int):
        return list(self._task_attachments.get(task_id, []))

    def fetch_idea_relations(self, idea_id: int):
        return list(self._idea_relations.get(idea_id, []))

    def set_task_board_column(self, task_id: int, board_column: str) -> None:
        self.task_move_calls.append((task_id, board_column))
        updated_tasks = []
        for task in self._tasks:
            if task.id != task_id:
                updated_tasks.append(task)
                continue
            next_priority = "Medium"
            if board_column == BOARD_COLUMN_DEFERRED:
                next_priority = "Отложенная"
            updated_tasks.append(
                TaskData(
                    id=task.id,
                    day=task.day,
                    time_text=task.time_text,
                    title=task.title,
                    description=task.description,
                    priority=next_priority,
                    done=task.done,
                    board_column=board_column,
                    project_id=task.project_id,
                    project_title=task.project_title,
                )
            )
        self._tasks = updated_tasks

    def update_idea(
        self,
        idea_id: int,
        title: str,
        summary: str,
        body_md: str,
        idea_type: str,
        status: str,
        value_score: int,
        effort_score: int,
        project_id=None,
        source: str = "",
    ) -> IdeaData:
        self.idea_update_calls.append((idea_id, status))
        current = next((idea for idea in self._ideas_active + self._ideas_archived if idea.id == idea_id), None)
        assert current is not None
        updated = IdeaData(
            id=idea_id,
            project_id=project_id,
            title=title,
            summary=summary,
            body_md=body_md,
            type=idea_type,
            status=status,
            value_score=value_score,
            effort_score=effort_score,
            source=source,
            created_at=current.created_at,
            updated_at=current.updated_at,
            archived_at=current.archived_at,
            project_title=current.project_title,
        )
        target = self._ideas_archived if updated.archived_at is not None else self._ideas_active
        replacement = []
        for idea in target:
            replacement.append(updated if idea.id == idea_id else idea)
        if updated.archived_at is None and not any(idea.id == idea_id for idea in replacement):
            replacement.append(updated)
        if updated.archived_at is not None:
            self._ideas_archived = replacement
        else:
            self._ideas_active = replacement
            self._ideas_archived = [idea for idea in self._ideas_archived if idea.id != idea_id]
        return updated

    def set_idea_archived(self, idea_id: int, archived: bool) -> None:
        self.idea_archive_calls.append((idea_id, archived))
        source = self._ideas_active if archived else self._ideas_archived
        target = self._ideas_archived if archived else self._ideas_active
        next_source = []
        for idea in source:
            if idea.id != idea_id:
                next_source.append(idea)
                continue
            updated = IdeaData(
                id=idea.id,
                project_id=idea.project_id,
                title=idea.title,
                summary=idea.summary,
                body_md=idea.body_md,
                type=idea.type,
                status=idea.status,
                value_score=idea.value_score,
                effort_score=idea.effort_score,
                source=idea.source,
                created_at=idea.created_at,
                updated_at=idea.updated_at,
                archived_at=idea.updated_at if archived else None,
                project_title=idea.project_title,
            )
            target.append(updated)
        if archived:
            self._ideas_active = next_source
        else:
            self._ideas_archived = next_source

    def create_task(
        self,
        title: str,
        description: str,
        day,
        time_text: str,
        priority: str,
        project_id=None,
        **_kwargs,
    ) -> TaskData:
        task = TaskData(
            id=self._next_task_id,
            day=day,
            time_text=time_text,
            title=title,
            description=description,
            priority=priority,
            done=False,
            board_column=BOARD_COLUMN_QUEUE,
            project_id=project_id,
            project_title="Workspace Project" if project_id == 5 else "",
        )
        self._next_task_id += 1
        self.created_task_ids.append(task.id)
        self._tasks.append(task)
        return task

    def create_idea(
        self,
        title: str,
        summary: str = "",
        body_md: str = "",
        idea_type: str = "other",
        status: str = "inbox",
        value_score: int = 3,
        effort_score: int = 3,
        project_id=None,
        source: str = "",
    ) -> IdeaData:
        idea = IdeaData(
            id=self._next_idea_id,
            project_id=project_id,
            title=title,
            summary=summary,
            body_md=body_md,
            type=idea_type,
            status=status,
            value_score=value_score,
            effort_score=effort_score,
            source=source,
            created_at=self._now,
            updated_at=self._now,
            archived_at=None,
            project_title="Workspace Project" if project_id == 5 else "",
        )
        self._next_idea_id += 1
        self.created_idea_ids.append(idea.id)
        self._ideas_active.append(idea)
        return idea

    def create_object(
        self,
        title: str,
        catalog: str,
        object_type: str,
        status: str,
        description: str,
    ) -> ObjectData:
        obj = ObjectData(
            id=self._next_object_id,
            title=title,
            catalog=catalog,
            object_type=object_type,
            status=status,
            description=description,
            created_at="2026-05-14T12:00:00+00:00",
            updated_at="2026-05-14T12:00:00+00:00",
        )
        self._next_object_id += 1
        self.created_object_ids.append(obj.id)
        self._objects.append(obj)
        return obj

    def add_idea_relation(self, idea_id: int, entity_type: str, entity_id: int) -> None:
        self.idea_relation_calls.append((idea_id, entity_type, entity_id))
        relation = IdeaRelationData(
            id=len(self.idea_relation_calls) + 600,
            idea_id=idea_id,
            entity_type=entity_type,
            entity_id=entity_id,
            created_at=self._now,
        )
        self._idea_relations.setdefault(idea_id, []).append(relation)

    def add_task_attachment(self, task_id: int, kind: str, ref_id: int) -> None:
        self.task_attachment_calls.append((task_id, kind, ref_id))
        attachment = TaskAttachmentData(
            id=len(self.task_attachment_calls) + 700,
            task_id=task_id,
            kind=kind,
            ref_id=ref_id,
            created_at="2026-05-14T12:00:00+00:00",
        )
        self._task_attachments.setdefault(task_id, []).append(attachment)


def _card_from_column(workspace, stage: str, row: int = 0):
    return workspace.board_columns[stage].item(row).data(Qt.ItemDataRole.UserRole)


def test_mutaboard_workspace_builds_board_and_counts(monkeypatch) -> None:
    _app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(mutaboard_module, "get_database", lambda: _MutaBoardWorkspaceDbStub())

    workspace = mutaboard_module.MutaBoardWorkspace()
    try:
        assert workspace.objectName() == "MutaBoardWorkspace"
        assert len(workspace.board_columns) == 7
        assert workspace.board_columns["prep"].count() == 1
        assert workspace.board_columns["thinking"].count() == 1
        assert workspace.board_columns["active"].count() == 1
        assert workspace.project_filter.count() == 2
        assert workspace.status_row.text() == "Мутаборд: карточек 3."
    finally:
        workspace.deleteLater()


def test_mutaboard_workspace_selection_updates_inspector(monkeypatch) -> None:
    _app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(mutaboard_module, "get_database", lambda: _MutaBoardWorkspaceDbStub())

    workspace = mutaboard_module.MutaBoardWorkspace()
    try:
        column = workspace.board_columns["thinking"]
        column.setCurrentRow(0)
        QApplication.processEvents()

        assert workspace.inspector_empty.isHidden()
        assert workspace.inspector_kind_value.text() == "Идеи"
        assert workspace.inspector_title_value.text() == "Idea board item"
        assert workspace.inspector_stage_value.text() == "Осмысление"
        assert workspace.inspector_project_value.text() == "Workspace Project"
        assert "ripe" in workspace.inspector_meta_value.text()
    finally:
        workspace.deleteLater()


def test_mutaboard_workspace_kind_filter_rebuilds_visible_cards(monkeypatch) -> None:
    _app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(mutaboard_module, "get_database", lambda: _MutaBoardWorkspaceDbStub())

    workspace = mutaboard_module.MutaBoardWorkspace()
    try:
        workspace.kind_filter.setCurrentIndex(workspace.kind_filter.findData("task"))
        QApplication.processEvents()

        assert workspace.board_columns["prep"].count() == 1
        assert workspace.board_columns["thinking"].count() == 0
        assert workspace.board_columns["active"].count() == 0
        assert workspace.status_row.text() == "Мутаборд: карточек 1 из 3."
    finally:
        workspace.deleteLater()


def test_mutaboard_workspace_moves_task_card_to_supported_stage(monkeypatch) -> None:
    _app = QApplication.instance() or QApplication([])
    stub = _MutaBoardWorkspaceDbStub()
    monkeypatch.setattr(mutaboard_module, "get_database", lambda: stub)

    workspace = mutaboard_module.MutaBoardWorkspace()
    try:
        task_card = _card_from_column(workspace, "prep")
        workspace._move_card_to_stage(task_card, "active")

        assert stub.task_move_calls == [(101, BOARD_COLUMN_IN_PROGRESS)]
        assert workspace.board_columns["prep"].count() == 0
        assert workspace.board_columns["active"].count() == 2
        assert {
            _card_from_column(workspace, "active", row).title
            for row in range(workspace.board_columns["active"].count())
        } == {"Task board item", "Object board item"}
        assert "задача перенесена" in workspace.status_row.text().lower()
    finally:
        workspace.deleteLater()


def test_mutaboard_workspace_moves_idea_card_to_frozen(monkeypatch) -> None:
    _app = QApplication.instance() or QApplication([])
    stub = _MutaBoardWorkspaceDbStub()
    monkeypatch.setattr(mutaboard_module, "get_database", lambda: stub)

    workspace = mutaboard_module.MutaBoardWorkspace()
    try:
        idea_card = _card_from_column(workspace, "thinking")
        workspace._move_card_to_stage(idea_card, "frozen")

        assert stub.idea_update_calls == [(202, "archived")]
        assert stub.idea_archive_calls == [(202, True)]
        assert workspace.board_columns["thinking"].count() == 0
        assert workspace.board_columns["frozen"].count() == 1
        frozen_card = _card_from_column(workspace, "frozen")
        assert frozen_card.entity_kind == "idea"
        assert frozen_card.title == "Idea board item"
        assert "идея перенесена" in workspace.status_row.text().lower()
    finally:
        workspace.deleteLater()


def test_mutaboard_workspace_rejects_idea_move_to_unmapped_stage(monkeypatch) -> None:
    _app = QApplication.instance() or QApplication([])
    stub = _MutaBoardWorkspaceDbStub()
    monkeypatch.setattr(mutaboard_module, "get_database", lambda: stub)

    workspace = mutaboard_module.MutaBoardWorkspace()
    try:
        idea_card = _card_from_column(workspace, "thinking")
        workspace._move_card_to_stage(idea_card, "active")

        assert stub.idea_update_calls == []
        assert stub.idea_archive_calls == []
        assert workspace.board_columns["thinking"].count() == 1
        assert "перенос для этой карточки недоступен" in workspace.status_row.text().lower()
    finally:
        workspace.deleteLater()


def test_mutaboard_workspace_inspector_action_creates_task_from_idea(monkeypatch) -> None:
    _app = QApplication.instance() or QApplication([])
    stub = _MutaBoardWorkspaceDbStub()
    monkeypatch.setattr(mutaboard_module, "get_database", lambda: stub)

    workspace = mutaboard_module.MutaBoardWorkspace()
    try:
        workspace.board_columns["thinking"].setCurrentRow(0)
        QApplication.processEvents()
        workspace.inspector_primary_action.click()
        QApplication.processEvents()

        assert stub.created_task_ids == [1000]
        assert stub.idea_relation_calls == [(202, "task", 1000)]
        assert stub.idea_update_calls[-1] == (202, "ripe")
        assert workspace.status_row.text() == "Мутаборд: из идеи создана задача."
        assert any(
            _card_from_column(workspace, "prep", row).entity_id == 1000
            for row in range(workspace.board_columns["prep"].count())
        )
    finally:
        workspace.deleteLater()


def test_mutaboard_workspace_inspector_action_creates_idea_from_object(monkeypatch) -> None:
    _app = QApplication.instance() or QApplication([])
    stub = _MutaBoardWorkspaceDbStub()
    monkeypatch.setattr(mutaboard_module, "get_database", lambda: stub)

    workspace = mutaboard_module.MutaBoardWorkspace()
    try:
        workspace.board_columns["active"].setCurrentRow(0)
        QApplication.processEvents()
        assert workspace.inspector_secondary_action.text() == "Создать идею"
        workspace.inspector_secondary_action.click()
        QApplication.processEvents()

        assert stub.created_idea_ids == [2000]
        assert stub.idea_relation_calls == [(2000, "object", 303)]
        assert workspace.status_row.text() == "Мутаборд: из объекта создана идея."
        assert any(
            _card_from_column(workspace, "inbox", row).entity_id == 2000
            for row in range(workspace.board_columns["inbox"].count())
        )
    finally:
        workspace.deleteLater()


def test_mutaboard_workspace_linked_filter_tracks_new_relations(monkeypatch) -> None:
    _app = QApplication.instance() or QApplication([])
    stub = _MutaBoardWorkspaceDbStub()
    monkeypatch.setattr(mutaboard_module, "get_database", lambda: stub)

    workspace = mutaboard_module.MutaBoardWorkspace()
    try:
        workspace.board_columns["active"].setCurrentRow(0)
        QApplication.processEvents()
        workspace.inspector_secondary_action.click()
        QApplication.processEvents()

        workspace.linked_filter.setCurrentIndex(workspace.linked_filter.findData("linked"))
        QApplication.processEvents()

        assert workspace.board_columns["inbox"].count() == 1
        linked_idea_card = _card_from_column(workspace, "inbox")
        assert linked_idea_card.linked_object_count == 1
        assert workspace.board_columns["active"].count() == 1
        assert workspace.status_row.text() == "Мутаборд: карточек 2 из 4."

        workspace.linked_filter.setCurrentIndex(workspace.linked_filter.findData("unlinked"))
        QApplication.processEvents()
        assert workspace.board_columns["inbox"].count() == 0
        assert workspace.board_columns["thinking"].count() == 1
        assert workspace.board_columns["prep"].count() == 1
    finally:
        workspace.deleteLater()
