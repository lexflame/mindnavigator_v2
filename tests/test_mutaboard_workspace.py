from __future__ import annotations

from datetime import date, datetime, timezone

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

import mindnavigator.workspaces.mutaboard.module_impl as mutaboard_module
from mindnavigator.storage import (
    CloudFileData,
    IdeaData,
    IdeaRelationData,
    MapData,
    MapMarkerData,
    MutaBoardColumnData,
    MutaBoardData,
    MutaBoardItemData,
    NoteData,
    ObjectData,
    ProjectData,
    TaskAttachmentData,
    TaskData,
)


class _MutaBoardWorkspaceDbStub:
    def __init__(self) -> None:
        self._now = datetime(2026, 5, 17, 12, 0, tzinfo=timezone.utc)
        self._tasks = [
            TaskData(
                id=101,
                day=date(2026, 5, 17),
                time_text="09:30",
                title="Task board item",
                description="Workspace task description",
                priority="Medium",
                done=False,
                board_column="queue",
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
                created_at="2026-05-17T10:00:00+00:00",
                updated_at="2026-05-17T11:00:00+00:00",
            )
        ]
        self._notes = [
            NoteData(
                id=404,
                title="Note board item",
                preview="Note preview",
                tags=["one"],
                updated=self._now,
                project="Workspace Project",
            )
        ]
        self._projects = [
            ProjectData(
                id=5,
                area="Workspace",
                title="Workspace Project",
                updated=date(2026, 5, 17),
                priority="High",
                archived=False,
                linked_map_id=505,
                linked_note_id=404,
                linked_object_id=303,
            )
        ]
        self._maps = [
            MapData(
                id=505,
                title="Map board item",
                description="Map preview",
                project="Workspace Project",
                tiles_path="",
                tiles_h=4,
                tiles_w=4,
            )
        ]
        self._markers = [
            MapMarkerData(
                id=606,
                map_id=505,
                name="Marker board item",
                x=10.0,
                y=20.0,
                color="#fff",
                type="poi",
                size=1.0,
                description="Marker preview",
                properties="",
                task_ids=[101],
                project_ids=[5],
                note_ids=[],
                object_ids=[303],
                file_ids=[],
                map_ids=[],
                marker_ids=[],
                parent_path="",
                image_path="",
                created_at="2026-05-17T10:00:00+00:00",
                updated_at="2026-05-17T11:00:00+00:00",
            )
        ]
        self._images = [
            CloudFileData(
                id=707,
                rel_path="gallery/scene.png",
                name="Image board item",
                description="Image preview",
                checksum="",
                hash_value="",
                size=512,
                is_image=True,
                valid=True,
                updated_at="2026-05-17T11:00:00+00:00",
            )
        ]
        self._task_attachments = {
            101: [TaskAttachmentData(id=801, task_id=101, kind="idea", ref_id=202, created_at="2026-05-17T12:00:00+00:00")]
        }
        self._idea_relations = {
            202: [IdeaRelationData(id=901, idea_id=202, entity_type="object", entity_id=303, created_at=self._now)]
        }
        self._mutaboards = {
            1: MutaBoardData(
                id=1,
                title="Основной мутборд",
                description="Описание доски",
                capture_text="Capture start",
                planning_text="Planning start",
                links_text="Links start",
                created_at=self._now,
                updated_at=self._now,
            )
        }
        self._columns = {
            1: [
                MutaBoardColumnData(id=1, mutaboard_id=1, kind="task", title="", position=0, created_at=self._now, updated_at=self._now),
                MutaBoardColumnData(id=2, mutaboard_id=1, kind="idea", title="", position=1, created_at=self._now, updated_at=self._now),
                MutaBoardColumnData(id=3, mutaboard_id=1, kind="image", title="", position=2, created_at=self._now, updated_at=self._now),
            ]
        }
        self._items = {1: []}
        self.updated_mutaboards: list[tuple[int, str, str, str, str, str]] = []
        self.attached_items: list[tuple[int, str, int]] = []
        self._next_board_id = 2
        self._next_column_id = 4
        self._next_item_id = 1000

    def fetch_tasks(self):
        return list(self._tasks)

    def fetch_ideas(self, archived=True):
        return list(self._ideas_archived if archived else self._ideas_active)

    def fetch_objects(self):
        return list(self._objects)

    def fetch_notes(self):
        return list(self._notes)

    def fetch_projects(self):
        return list(self._projects)

    def fetch_maps(self):
        return list(self._maps)

    def fetch_map_markers(self, map_id=None):
        if map_id is None:
            return list(self._markers)
        return [marker for marker in self._markers if marker.map_id == map_id]

    def fetch_cloud_files(self):
        return list(self._images)

    def fetch_task_attachments(self, task_id: int):
        return list(self._task_attachments.get(task_id, []))

    def fetch_idea_relations(self, idea_id: int):
        return list(self._idea_relations.get(idea_id, []))

    def fetch_mutaboards(self):
        return sorted(self._mutaboards.values(), key=lambda item: item.id)

    def create_mutaboard(self, title: str, description: str = "", capture_text: str = "", planning_text: str = "", links_text: str = "", column_kinds=None):
        created = MutaBoardData(
            id=self._next_board_id,
            title=title,
            description=description,
            capture_text=capture_text,
            planning_text=planning_text,
            links_text=links_text,
            created_at=self._now,
            updated_at=self._now,
        )
        self._mutaboards[created.id] = created
        kinds = list(column_kinds or ("task", "idea", "image"))
        columns = []
        for position, kind in enumerate(kinds):
            columns.append(
                MutaBoardColumnData(
                    id=self._next_column_id + position,
                    mutaboard_id=created.id,
                    kind=kind,
                    title="",
                    position=position,
                    created_at=self._now,
                    updated_at=self._now,
                )
            )
        self._next_column_id += len(columns)
        self._columns[created.id] = columns
        self._items[created.id] = []
        self._next_board_id += 1
        return created

    def update_mutaboard(self, mutaboard_id: int, *, title: str, description: str, capture_text: str, planning_text: str, links_text: str):
        updated = MutaBoardData(
            id=mutaboard_id,
            title=title,
            description=description,
            capture_text=capture_text,
            planning_text=planning_text,
            links_text=links_text,
            created_at=self._mutaboards[mutaboard_id].created_at,
            updated_at=self._now,
        )
        self._mutaboards[mutaboard_id] = updated
        self.updated_mutaboards.append((mutaboard_id, title, description, capture_text, planning_text, links_text))
        return updated

    def fetch_mutaboard_columns(self, mutaboard_id: int):
        return list(self._columns.get(mutaboard_id, []))

    def replace_mutaboard_columns(self, mutaboard_id: int, columns):
        payload = []
        for position, (kind, title) in enumerate(columns):
            payload.append(
                MutaBoardColumnData(
                    id=self._next_column_id + position,
                    mutaboard_id=mutaboard_id,
                    kind=kind,
                    title=title,
                    position=position,
                    created_at=self._now,
                    updated_at=self._now,
                )
            )
        self._next_column_id += len(payload)
        self._columns[mutaboard_id] = payload
        return list(payload)

    def add_mutaboard_column(self, mutaboard_id: int, kind: str, title: str = ""):
        column = MutaBoardColumnData(
            id=self._next_column_id,
            mutaboard_id=mutaboard_id,
            kind=kind,
            title=title,
            position=len(self._columns.get(mutaboard_id, [])),
            created_at=self._now,
            updated_at=self._now,
        )
        self._next_column_id += 1
        self._columns.setdefault(mutaboard_id, []).append(column)
        return column

    def update_mutaboard_column(self, column_id: int, *, kind: str, title: str, position: int | None = None):
        for mutaboard_id, columns in self._columns.items():
            for index, column in enumerate(columns):
                if column.id != column_id:
                    continue
                updated = MutaBoardColumnData(
                    id=column.id,
                    mutaboard_id=column.mutaboard_id,
                    kind=kind,
                    title=title,
                    position=column.position if position is None else position,
                    created_at=column.created_at,
                    updated_at=self._now,
                )
                columns[index] = updated
                return updated
        raise AssertionError("column not found")

    def fetch_mutaboard_items(self, mutaboard_id: int):
        return list(self._items.get(mutaboard_id, []))

    def attach_mutaboard_item(self, mutaboard_id: int, entity_kind: str, entity_id: int):
        item = MutaBoardItemData(
            id=self._next_item_id,
            mutaboard_id=mutaboard_id,
            entity_kind=entity_kind,
            entity_id=entity_id,
            created_at=self._now,
        )
        self._next_item_id += 1
        self._items.setdefault(mutaboard_id, []).append(item)
        self.attached_items.append((mutaboard_id, entity_kind, entity_id))
        return item


def _column_widget_by_kind(workspace, kind: str):
    for column_id, column_kind in workspace._column_kinds.items():
        if column_kind == kind:
            return workspace.board_columns[column_id]
    raise AssertionError(f"column kind not found: {kind}")


def test_mutaboard_workspace_builds_board_list_and_default_columns(monkeypatch) -> None:
    _app = QApplication.instance() or QApplication([])
    stub = _MutaBoardWorkspaceDbStub()
    monkeypatch.setattr(mutaboard_module, "get_database", lambda: stub)

    workspace = mutaboard_module.MutaBoardWorkspace()
    try:
        assert workspace.objectName() == "ConceptBoardWorkspace"
        assert workspace.mutaboard_list.count() == 1
        assert workspace.mutaboard_list.item(0).text().startswith("Основной мутборд\n")
        assert "Решение принято" in workspace.mutaboard_list.item(0).text()
        assert workspace.focus_title_input.text() == "Основной мутборд"
        assert "Статус: Решение принято" in workspace.focus_caption_label.text()
        assert list(workspace._column_kinds.values()) == ["task", "idea", "image"]
        assert _column_widget_by_kind(workspace, "task").count() == 1
        assert _column_widget_by_kind(workspace, "idea").count() == 1
        assert _column_widget_by_kind(workspace, "image").count() == 1
        assert "связано 0" in workspace.status_row.text().lower()
    finally:
        workspace.deleteLater()


def test_mutaboard_workspace_selection_updates_structure_from_active_card(monkeypatch) -> None:
    _app = QApplication.instance() or QApplication([])
    stub = _MutaBoardWorkspaceDbStub()
    monkeypatch.setattr(mutaboard_module, "get_database", lambda: stub)

    workspace = mutaboard_module.MutaBoardWorkspace()
    try:
        idea_column = _column_widget_by_kind(workspace, "idea")
        idea_column.setCurrentRow(0)
        QApplication.processEvents()

        assert workspace.structure_hub_label.text() == "Idea board item"
        assert workspace.structure_ideas_label.text() == "Идеи · 1"
        assert workspace.structure_objects_label.text() == "Объекты · 1"
        assert workspace.structure_tasks_label.text() == "Задачи · 0"
        assert workspace.structure_links_label.text() == "Связи · 1"
    finally:
        workspace.deleteLater()


def test_mutaboard_workspace_saves_focus_and_scenarios(monkeypatch) -> None:
    _app = QApplication.instance() or QApplication([])
    stub = _MutaBoardWorkspaceDbStub()
    monkeypatch.setattr(mutaboard_module, "get_database", lambda: stub)

    workspace = mutaboard_module.MutaBoardWorkspace()
    try:
        workspace.focus_title_input.setText("Переименованный мутборд")
        workspace.focus_description_input.setPlainText("Новое описание")
        workspace._scenario_editors["capture"].setPlainText("Новый захват")
        workspace._scenario_editors["planning"].setPlainText("Новое планирование")
        workspace._scenario_editors["links"].setPlainText("Новые связи")
        workspace.focus_save_button.click()
        QApplication.processEvents()

        assert stub.updated_mutaboards == [
            (1, "Переименованный мутборд", "Новое описание", "Новый захват", "Новое планирование", "Новые связи")
        ]
        assert workspace.mutaboard_list.item(0).text().startswith("Переименованный мутборд\n")
    finally:
        workspace.deleteLater()


def test_mutaboard_workspace_adds_columns_and_attaches_items(monkeypatch) -> None:
    _app = QApplication.instance() or QApplication([])
    stub = _MutaBoardWorkspaceDbStub()
    monkeypatch.setattr(mutaboard_module, "get_database", lambda: stub)

    workspace = mutaboard_module.MutaBoardWorkspace()
    try:
        workspace.add_column_button.click()
        QApplication.processEvents()
        assert len(workspace.board_columns) == 4

        workspace._db.attach_mutaboard_item(1, "task", 101)
        workspace._populate_board()
        QApplication.processEvents()

        assert stub.attached_items == [(1, "task", 101)]
        refreshed_card = _column_widget_by_kind(workspace, "task").item(0).data(Qt.ItemDataRole.UserRole)
        assert refreshed_card.is_attached is True
        assert workspace.focus_attached_value.text() == "1"
    finally:
        workspace.deleteLater()


def test_mutaboard_workspace_creates_new_board_with_solution_flow_columns(monkeypatch) -> None:
    _app = QApplication.instance() or QApplication([])
    stub = _MutaBoardWorkspaceDbStub()
    monkeypatch.setattr(mutaboard_module, "get_database", lambda: stub)

    workspace = mutaboard_module.MutaBoardWorkspace()
    try:
        workspace.add_mutaboard_button.click()
        QApplication.processEvents()

        assert workspace.mutaboard_list.count() == 2
        assert len(workspace.board_columns) == 6
        assert [label.text() for label in workspace._column_title_labels.values()] == [
            "Входящие",
            "Идеи",
            "Материалы",
            "Версии",
            "Задачи",
            "Решение",
        ]
    finally:
        workspace.deleteLater()


def test_mutaboard_workspace_column_kind_filter_switches_catalog(monkeypatch) -> None:
    _app = QApplication.instance() or QApplication([])
    stub = _MutaBoardWorkspaceDbStub()
    monkeypatch.setattr(mutaboard_module, "get_database", lambda: stub)

    workspace = mutaboard_module.MutaBoardWorkspace()
    try:
        first_column_id = next(iter(workspace._column_kinds))
        workspace._on_column_kind_changed(first_column_id, "note")
        QApplication.processEvents()

        assert workspace._column_kinds[first_column_id] == "note"
        assert workspace.board_columns[first_column_id].count() == 1
        note_card = workspace.board_columns[first_column_id].item(0).data(Qt.ItemDataRole.UserRole)
        assert note_card.title == "Note board item"
    finally:
        workspace.deleteLater()


def test_mutaboard_workspace_builds_synthetic_version_and_solution_cards(monkeypatch) -> None:
    _app = QApplication.instance() or QApplication([])
    stub = _MutaBoardWorkspaceDbStub()
    monkeypatch.setattr(mutaboard_module, "get_database", lambda: stub)

    workspace = mutaboard_module.MutaBoardWorkspace()
    try:
        first_column_id = next(iter(workspace._column_kinds))
        second_column_id = list(workspace._column_kinds)[1]

        workspace._on_column_kind_changed(first_column_id, "version")
        workspace._on_column_kind_changed(second_column_id, "solution")
        QApplication.processEvents()

        version_card = workspace.board_columns[first_column_id].item(0).data(Qt.ItemDataRole.UserRole)
        solution_card = workspace.board_columns[second_column_id].item(0).data(Qt.ItemDataRole.UserRole)

        assert version_card is not None
        assert version_card.entity_kind == "version"
        assert version_card.title.startswith("Версия:")
        assert solution_card is not None
        assert solution_card.entity_kind == "solution"
        assert solution_card.title == "Capture start"
    finally:
        workspace.deleteLater()


def test_mutaboard_workspace_shows_empty_state_for_missing_column_kind(monkeypatch) -> None:
    _app = QApplication.instance() or QApplication([])
    stub = _MutaBoardWorkspaceDbStub()
    monkeypatch.setattr(mutaboard_module, "get_database", lambda: stub)

    workspace = mutaboard_module.MutaBoardWorkspace()
    try:
        first_column_id = next(iter(workspace._column_kinds))
        workspace._on_column_kind_changed(first_column_id, "file")
        QApplication.processEvents()

        empty_item = workspace.board_columns[first_column_id].item(0)
        assert empty_item.text() == "Нет файлов"
        assert empty_item.data(Qt.ItemDataRole.UserRole) is None
    finally:
        workspace.deleteLater()


def test_mutaboard_workspace_accepts_version_into_solution(monkeypatch) -> None:
    _app = QApplication.instance() or QApplication([])
    stub = _MutaBoardWorkspaceDbStub()
    monkeypatch.setattr(mutaboard_module, "get_database", lambda: stub)

    workspace = mutaboard_module.MutaBoardWorkspace()
    try:
        first_column_id = next(iter(workspace._column_kinds))
        workspace._on_column_kind_changed(first_column_id, "version")
        QApplication.processEvents()

        version_column = workspace.board_columns[first_column_id]
        version_column.setCurrentRow(0)
        QApplication.processEvents()
        workspace.focus_card_primary_button.click()
        QApplication.processEvents()

        capture_text = workspace._scenario_editors["capture"].toPlainText()
        assert "Capture start" in capture_text
        assert "Описание доски" in capture_text
        assert workspace.board_tabs.currentWidget() is workspace.scenarios_panel
    finally:
        workspace.deleteLater()


def test_mutaboard_workspace_creates_next_task_from_focus_card(monkeypatch) -> None:
    _app = QApplication.instance() or QApplication([])
    stub = _MutaBoardWorkspaceDbStub()
    monkeypatch.setattr(mutaboard_module, "get_database", lambda: stub)

    workspace = mutaboard_module.MutaBoardWorkspace()
    try:
        first_column_id = next(iter(workspace._column_kinds))
        workspace._on_column_kind_changed(first_column_id, "version")
        QApplication.processEvents()

        idea_column = _column_widget_by_kind(workspace, "idea")
        idea_column.setCurrentRow(0)
        QApplication.processEvents()
        workspace.focus_card_secondary_button.click()
        QApplication.processEvents()

        assert "Проверить: Idea board item" in workspace._scenario_editors["links"].toPlainText()
        assert workspace.board_tabs.currentWidget() is workspace.scenarios_panel
    finally:
        workspace.deleteLater()


def test_mutaboard_workspace_quick_actions_seed_concept_flow(monkeypatch) -> None:
    _app = QApplication.instance() or QApplication([])
    stub = _MutaBoardWorkspaceDbStub()
    monkeypatch.setattr(mutaboard_module, "get_database", lambda: stub)

    workspace = mutaboard_module.MutaBoardWorkspace()
    try:
        workspace.quick_add_idea_button.click()
        workspace.quick_add_version_button.click()
        workspace.quick_add_task_button.click()
        QApplication.processEvents()

        assert "Идея:" in workspace.focus_description_input.toPlainText()
        assert "Проверить версию:" in workspace._scenario_editors["planning"].toPlainText()
        assert "Следующая задача:" in workspace._scenario_editors["links"].toPlainText()
    finally:
        workspace.deleteLater()


def test_mutaboard_workspace_creates_tasks_from_solution_summary(monkeypatch) -> None:
    _app = QApplication.instance() or QApplication([])
    stub = _MutaBoardWorkspaceDbStub()
    monkeypatch.setattr(mutaboard_module, "get_database", lambda: stub)

    workspace = mutaboard_module.MutaBoardWorkspace()
    try:
        workspace._scenario_editors["capture"].setPlainText("Собрать концептборд вокруг решения")
        QApplication.processEvents()
        workspace.create_tasks_button.click()
        QApplication.processEvents()

        links_text = workspace._scenario_editors["links"].toPlainText()
        assert "Подготовить реализацию: Собрать концептборд вокруг решения" in links_text
        assert "Проверить риски: Собрать концептборд вокруг решения" in links_text
    finally:
        workspace.deleteLater()


def test_mutaboard_workspace_styles_darken_all_shell_areas(monkeypatch) -> None:
    _app = QApplication.instance() or QApplication([])
    stub = _MutaBoardWorkspaceDbStub()
    monkeypatch.setattr(mutaboard_module, "get_database", lambda: stub)

    workspace = mutaboard_module.MutaBoardWorkspace()
    try:
        stylesheet = workspace.styleSheet()

        assert "QFrame#MutaBoardScenarioCard" in stylesheet
        assert "QScrollArea#MutaBoardScroll" in stylesheet
        assert "QComboBox#MutaBoardColumnKindFilter QAbstractItemView" in stylesheet
        assert "QComboBox#MutaBoardFilterCombo QAbstractItemView" in stylesheet
        assert "QLineEdit#WorkspaceSearchInput" in stylesheet
        assert "QToolButton#WorkspaceSearchClear" in stylesheet
        assert workspace.link_scope_filter.objectName() == "MutaBoardFilterCombo"
        assert workspace.action_scope_filter.objectName() == "MutaBoardFilterCombo"
        assert "QMenu {" in stylesheet
        assert "QListWidget#MutaBoardColumnList::viewport" in stylesheet
    finally:
        workspace.deleteLater()


def test_mutaboard_workspace_places_filters_before_search(monkeypatch) -> None:
    _app = QApplication.instance() or QApplication([])
    stub = _MutaBoardWorkspaceDbStub()
    monkeypatch.setattr(mutaboard_module, "get_database", lambda: stub)

    workspace = mutaboard_module.MutaBoardWorkspace()
    try:
        search_layout = workspace.search_row.layout()
        widgets = [search_layout.itemAt(index).widget() for index in range(search_layout.count())]

        assert workspace.toolbar_row.isHidden()
        assert workspace.filter_row.isHidden()
        assert widgets[0] is workspace.link_scope_label
        assert widgets[1] is workspace.link_scope_filter
        assert widgets[2] is workspace.action_scope_label
        assert widgets[3] is workspace.action_scope_filter
        assert widgets[4] is workspace.search_input
    finally:
        workspace.deleteLater()


def test_mutaboard_workspace_columns_use_resizable_splitter(monkeypatch) -> None:
    _app = QApplication.instance() or QApplication([])
    stub = _MutaBoardWorkspaceDbStub()
    monkeypatch.setattr(mutaboard_module, "get_database", lambda: stub)

    workspace = mutaboard_module.MutaBoardWorkspace()
    try:
        workspace.resize(1600, 900)
        workspace.show()
        QApplication.processEvents()
        assert workspace.columns_splitter.count() == len(workspace.board_columns)
        workspace.columns_splitter.setSizes([320, 260, 280])
        QApplication.processEvents()

        sizes = workspace.columns_splitter.sizes()
        assert len(sizes) == workspace.columns_splitter.count()
        assert max(sizes) >= 280
        assert min(sizes) >= 200
    finally:
        workspace.deleteLater()


def test_mutaboard_workspace_builds_semantic_overview_relations(monkeypatch) -> None:
    _app = QApplication.instance() or QApplication([])
    stub = _MutaBoardWorkspaceDbStub()
    monkeypatch.setattr(mutaboard_module, "get_database", lambda: stub)

    workspace = mutaboard_module.MutaBoardWorkspace()
    try:
        relations = [workspace.structure_relations_list.item(index).text() for index in range(workspace.structure_relations_list.count())]

        assert any("вдохновляет" in relation for relation in relations)
        assert any("превращается в" in relation for relation in relations)
    finally:
        workspace.deleteLater()


def test_mutaboard_workspace_builds_semantic_relations_for_selected_idea(monkeypatch) -> None:
    _app = QApplication.instance() or QApplication([])
    stub = _MutaBoardWorkspaceDbStub()
    monkeypatch.setattr(mutaboard_module, "get_database", lambda: stub)

    workspace = mutaboard_module.MutaBoardWorkspace()
    try:
        first_column_id = next(iter(workspace._column_kinds))
        workspace._on_column_kind_changed(first_column_id, "version")
        QApplication.processEvents()

        idea_column = _column_widget_by_kind(workspace, "idea")
        idea_column.setCurrentRow(0)
        QApplication.processEvents()

        relations = [workspace.structure_relations_list.item(index).text() for index in range(workspace.structure_relations_list.count())]
        assert any("относится к" in relation for relation in relations)
        assert any("развивает" in relation for relation in relations)
    finally:
        workspace.deleteLater()


def test_mutaboard_workspace_filters_only_linked_items(monkeypatch) -> None:
    _app = QApplication.instance() or QApplication([])
    stub = _MutaBoardWorkspaceDbStub()
    monkeypatch.setattr(mutaboard_module, "get_database", lambda: stub)

    workspace = mutaboard_module.MutaBoardWorkspace()
    try:
        workspace.link_scope_filter.setCurrentIndex(workspace.link_scope_filter.findData("linked"))
        QApplication.processEvents()

        image_column = _column_widget_by_kind(workspace, "image")
        first_item = image_column.item(0)
        assert first_item.data(Qt.ItemDataRole.UserRole) is None
        assert "из" in workspace.status_row.text().lower()
    finally:
        workspace.deleteLater()


def test_mutaboard_workspace_filters_only_actionable_items(monkeypatch) -> None:
    _app = QApplication.instance() or QApplication([])
    stub = _MutaBoardWorkspaceDbStub()
    stub._tasks.append(
        TaskData(
            id=102,
            day=date(2026, 5, 17),
            time_text="10:30",
            title="Completed task",
            description="Already done",
            priority="Low",
            done=True,
            board_column="queue",
            project_id=5,
            project_title="Workspace Project",
        )
    )
    monkeypatch.setattr(mutaboard_module, "get_database", lambda: stub)

    workspace = mutaboard_module.MutaBoardWorkspace()
    try:
        task_column = _column_widget_by_kind(workspace, "task")
        assert task_column.count() == 2

        workspace.action_scope_filter.setCurrentIndex(workspace.action_scope_filter.findData("actionable"))
        QApplication.processEvents()

        visible_titles = [
            task_column.item(index).data(Qt.ItemDataRole.UserRole).title
            for index in range(task_column.count())
            if task_column.item(index).data(Qt.ItemDataRole.UserRole) is not None
        ]
        assert visible_titles == ["Task board item"]
    finally:
        workspace.deleteLater()


def test_mutaboard_workspace_relation_click_focuses_idea_from_overview(monkeypatch) -> None:
    _app = QApplication.instance() or QApplication([])
    stub = _MutaBoardWorkspaceDbStub()
    monkeypatch.setattr(mutaboard_module, "get_database", lambda: stub)

    workspace = mutaboard_module.MutaBoardWorkspace()
    try:
        first_relation = workspace.structure_relations_list.item(0)

        workspace._on_structure_relation_clicked(first_relation)
        QApplication.processEvents()

        assert workspace._selected_card_key == ("idea", 202)
        assert workspace.structure_hub_label.text() == "Idea board item"
    finally:
        workspace.deleteLater()


def test_mutaboard_workspace_relation_click_focuses_version_from_idea(monkeypatch) -> None:
    _app = QApplication.instance() or QApplication([])
    stub = _MutaBoardWorkspaceDbStub()
    monkeypatch.setattr(mutaboard_module, "get_database", lambda: stub)

    workspace = mutaboard_module.MutaBoardWorkspace()
    try:
        first_column_id = next(iter(workspace._column_kinds))
        workspace._on_column_kind_changed(first_column_id, "version")
        QApplication.processEvents()

        idea_column = _column_widget_by_kind(workspace, "idea")
        idea_column.setCurrentRow(0)
        QApplication.processEvents()

        relation_item = next(
            workspace.structure_relations_list.item(index)
            for index in range(workspace.structure_relations_list.count())
            if workspace.structure_relations_list.item(index).data(Qt.ItemDataRole.UserRole) == ("version", -11)
        )
        workspace._on_structure_relation_clicked(relation_item)
        QApplication.processEvents()

        assert workspace._selected_card_key == ("version", -11)
        assert "Версия" in workspace.focus_card_kind_label.text()
    finally:
        workspace.deleteLater()
