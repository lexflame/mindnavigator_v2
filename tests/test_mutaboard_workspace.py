from __future__ import annotations

from datetime import date, datetime, timezone

from PySide6.QtWidgets import QApplication

import mindnavigator.workspaces.mutaboard.module_impl as mutaboard_module
from mindnavigator.storage import BOARD_COLUMN_QUEUE, IdeaData, ObjectData, TaskData


class _MutaBoardWorkspaceDbStub:
    def fetch_tasks(self):
        return [
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

    def fetch_ideas(self, archived=True):
        now = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)
        if archived:
            return []
        return [
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
                created_at=now,
                updated_at=now,
                archived_at=None,
                project_title="Workspace Project",
            )
        ]

    def fetch_objects(self):
        return [
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
