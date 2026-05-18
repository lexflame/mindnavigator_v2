from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from PySide6.QtCore import QEvent, QItemSelectionModel, QModelIndex, QPointF, QRect, Qt
from PySide6.QtGui import QImage, QMouseEvent, QPainter, QPalette
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QComboBox, QStyleOptionViewItem

from mindnavigator.storage import (
    BOARD_COLUMN_COMPLETED,
    BOARD_COLUMN_DEFERRED,
    BOARD_COLUMN_IN_PROGRESS,
    BOARD_COLUMN_QUEUE,
    DEFERRED_PRIORITY,
    Database,
)
from mindnavigator.ui.filterable_combobox import FilterableComboBox
from mindnavigator.workspaces.tasks import task_edit_dialog
from mindnavigator.workspaces.tasks._shared import normalize_task_text_quotes
from mindnavigator.workspaces.tasks.cast_board import TasksBoardCast
from mindnavigator.workspaces.tasks.cast_dash import TasksDashCast
from mindnavigator.workspaces.tasks.cast_gantt import TasksGanttCast
from mindnavigator.workspaces.tasks.style import TasksWorkspaceStyle
from mindnavigator.workspaces.tasks.task_row import TaskRow
from mindnavigator.workspaces import tasks as tasks_workspace
from mindnavigator.workspaces.tasks import TaskRoles


def _find_task_row(model: tasks_workspace.TasksModel, task_id: int) -> int:
    for row in range(model.rowCount()):
        index = model.index(row, 0)
        if index.data(TaskRoles.RowType) != "task":
            continue
        if index.data(TaskRoles.TaskId) == task_id:
            return row
    return -1


def _create_completed_task(database: Database, title: str, completion_day: date, priority: str = "Medium") -> int:
    created = database.create_task(
        title=title,
        description="",
        day=completion_day,
        time_text="",
        priority=priority,
    )
    database.update_task(
        created.id,
        title=created.title,
        description=created.description,
        day=completion_day,
        time_text=created.time_text,
        priority=priority,
        done=True,
        project_id=created.project_id,
        parent_id=created.parent_id,
        recurrence_kind=created.recurrence_kind,
        recurrence_interval=created.recurrence_interval,
        marker_color=created.marker_color,
        marker_theme=created.marker_theme,
    )
    return created.id


def _select_task_ids(workspace: tasks_workspace.TasksWorkspace, task_ids: list[int]) -> None:
    selection_model = workspace.list.selectionModel()
    assert selection_model is not None
    selection_model.clearSelection()
    for index, task_id in enumerate(task_ids):
        row_idx = _find_task_row(workspace.model, task_id)
        assert row_idx >= 0
        model_index = workspace.model.index(row_idx, 0)
        selection_flags = (
            QItemSelectionModel.SelectionFlag.ClearAndSelect
            if index == 0
            else QItemSelectionModel.SelectionFlag.Select
        )
        selection_model.select(model_index, selection_flags)
        selection_model.setCurrentIndex(model_index, QItemSelectionModel.SelectionFlag.Current)
    QApplication.processEvents()


def test_tasks_model_cycles_priority_including_deferred(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("tasks_priority_cycle", ".sqlite3")
    database = Database(path=db_path)
    try:
        created = database.create_task(
            title="Priority cycle",
            description="",
            day=date(2026, 3, 6),
            time_text="09:00",
            priority="Low",
        )
        monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)
        model = tasks_workspace.TasksModel()
        row_idx = _find_task_row(model, created.id)
        assert row_idx >= 0

        model.cycle_priority_by_row(row_idx)
        row_idx = _find_task_row(model, created.id)
        assert model.index(row_idx, 0).data(TaskRoles.Priority) == "Medium"

        model.cycle_priority_by_row(row_idx)
        row_idx = _find_task_row(model, created.id)
        assert model.index(row_idx, 0).data(TaskRoles.Priority) == "High"

        model.cycle_priority_by_row(row_idx)
        row_idx = _find_task_row(model, created.id)
        assert row_idx == -1
        model.set_filter_mode("Отложенные")
        row_idx = _find_task_row(model, created.id)
        assert row_idx >= 0
        assert model.index(row_idx, 0).data(TaskRoles.Priority) == "Отложенная"
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_tasks_workspace_switches_to_light_theme(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("tasks_theme_switch", ".sqlite3")
    database = Database(path=db_path)
    try:
        monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)
        workspace = tasks_workspace.TasksWorkspace()

        workspace.set_theme_mode("light")

        base_color = workspace.gantt_table.palette().color(QPalette.ColorRole.Base).name().lower()
        assert workspace.delegate._theme_mode == "light"
        assert "#f5f7fb" in workspace.styleSheet()
        assert base_color == "#f5f7fb"
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_tasks_workspace_uses_extracted_mode_helpers(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("tasks_mode_helpers", ".sqlite3")
    database = Database(path=db_path)
    try:
        monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)
        workspace = tasks_workspace.TasksWorkspace()

        assert isinstance(workspace._style_helper, TasksWorkspaceStyle)
        assert isinstance(workspace._board_cast, TasksBoardCast)
        assert isinstance(workspace._gantt_cast, TasksGanttCast)
        assert isinstance(workspace._dash_cast, TasksDashCast)
        assert workspace.gantt_page is workspace._gantt_cast.page
        assert workspace.board_page is workspace._board_cast.page
        assert workspace.dash_page is workspace._dash_cast.page
        assert workspace.board_day_filter_checkbox is workspace._board_cast.day_filter_checkbox
        assert workspace.board_columns is workspace._board_cast.columns
        assert workspace.dash_bar_chart is workspace._dash_cast.bar_chart
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_tasks_workspace_shows_batch_bar_for_multi_selection(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("tasks_batch_bar_visibility", ".sqlite3")
    database = Database(path=db_path)
    workspace = None
    try:
        first_task = database.create_task(
            title="Batch select one",
            description="",
            day=date(2026, 3, 6),
            time_text="09:00",
            priority="Medium",
        )
        second_task = database.create_task(
            title="Batch select two",
            description="",
            day=date(2026, 3, 6),
            time_text="10:00",
            priority="High",
        )
        monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)

        workspace = tasks_workspace.TasksWorkspace()

        assert workspace.list.selectionMode() == tasks_workspace.QListView.SelectionMode.ExtendedSelection
        assert workspace.batch_bar.isHidden()

        _select_task_ids(workspace, [first_task.id, second_task.id])

        assert not workspace.batch_bar.isHidden()
        assert workspace.batch_selection_label.text() == "Выбрано задач: 2"

        workspace.batch_action_combo.setCurrentIndex(workspace.batch_action_combo.findData("move_to_day"))
        QApplication.processEvents()
        assert not workspace.batch_date_edit.isHidden()
        assert workspace.batch_project_combo.isHidden()

        workspace.batch_action_combo.setCurrentIndex(workspace.batch_action_combo.findData("move_to_project"))
        QApplication.processEvents()
        assert not workspace.batch_project_combo.isHidden()
        assert workspace.batch_marker_color_combo.isHidden()
    finally:
        if workspace is not None:
            workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_tasks_workspace_batch_action_defers_selected_tasks(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("tasks_batch_action_defer", ".sqlite3")
    database = Database(path=db_path)
    workspace = None
    try:
        first_task = database.create_task(
            title="Batch defer one",
            description="",
            day=date(2026, 3, 6),
            time_text="09:00",
            priority="Medium",
        )
        second_task = database.create_task(
            title="Batch defer two",
            description="",
            day=date(2026, 3, 6),
            time_text="11:00",
            priority="High",
        )
        monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)

        workspace = tasks_workspace.TasksWorkspace()
        _select_task_ids(workspace, [first_task.id, second_task.id])

        workspace.batch_action_combo.setCurrentIndex(workspace.batch_action_combo.findData("defer"))
        workspace._apply_batch_action()
        QApplication.processEvents()

        updated_tasks = {task.id: task for task in database.fetch_tasks()}
        assert updated_tasks[first_task.id].priority == DEFERRED_PRIORITY
        assert updated_tasks[second_task.id].priority == DEFERRED_PRIORITY
        assert workspace.batch_bar.isHidden()
        assert workspace.batch_action_combo.currentData() == ""
        assert workspace.status_row.text() == "Перенесено в отложенные: 2."
    finally:
        if workspace is not None:
            workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_tasks_delegate_dark_checkbox_is_not_transparent() -> None:
    delegate = tasks_workspace.TasksItemDelegate()
    delegate.set_theme_mode("dark")
    image = QImage(24, 24, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(0)

    painter = QPainter(image)
    delegate._draw_done_checkbox(painter, tasks_workspace.QRect(6, 6, 12, 12), False, delegate.C_BORDER)
    painter.end()

    center = image.pixelColor(12, 12)
    assert center.alpha() >= 200


def test_tasks_model_steps_priority_up_and_down_without_wrap(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("tasks_priority_step", ".sqlite3")
    database = Database(path=db_path)
    try:
        created = database.create_task(
            title="Priority step",
            description="",
            day=date(2026, 3, 6),
            time_text="09:00",
            priority="Medium",
        )
        monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)
        model = tasks_workspace.TasksModel()
        row_idx = _find_task_row(model, created.id)
        assert row_idx >= 0

        model.step_priority_by_row(row_idx, +1)
        row_idx = _find_task_row(model, created.id)
        assert model.index(row_idx, 0).data(TaskRoles.Priority) == "High"

        model.step_priority_by_row(row_idx, +1)
        row_idx = _find_task_row(model, created.id)
        assert model.index(row_idx, 0).data(TaskRoles.Priority) == "High"

        model.step_priority_by_row(row_idx, -1)
        row_idx = _find_task_row(model, created.id)
        assert model.index(row_idx, 0).data(TaskRoles.Priority) == "Medium"

        model.step_priority_by_row(row_idx, -1)
        row_idx = _find_task_row(model, created.id)
        assert model.index(row_idx, 0).data(TaskRoles.Priority) == "Low"

        model.step_priority_by_row(row_idx, -1)
        model.set_filter_mode("Отложенные")
        row_idx = _find_task_row(model, created.id)
        assert row_idx >= 0
        assert model.index(row_idx, 0).data(TaskRoles.Priority) == "Отложенная"
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_tasks_model_steps_board_stage_up_and_down_without_wrap(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("tasks_board_stage_step", ".sqlite3")
    database = Database(path=db_path)
    try:
        created = database.create_task(
            title="Board stage step",
            description="",
            day=date(2026, 3, 6),
            time_text="09:00",
            priority="Medium",
        )
        monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)
        model = tasks_workspace.TasksModel()
        row_idx = _find_task_row(model, created.id)
        assert row_idx >= 0
        assert model.index(row_idx, 0).data(TaskRoles.BoardColumn) == BOARD_COLUMN_QUEUE

        model.step_board_column_by_row(row_idx, +1)
        row_idx = _find_task_row(model, created.id)
        assert model.index(row_idx, 0).data(TaskRoles.BoardColumn) == BOARD_COLUMN_IN_PROGRESS

        model.step_board_column_by_row(row_idx, +1)
        row_idx = _find_task_row(model, created.id)
        assert model.index(row_idx, 0).data(TaskRoles.BoardColumn) == BOARD_COLUMN_COMPLETED

        model.step_board_column_by_row(row_idx, +1)
        row_idx = _find_task_row(model, created.id)
        assert model.index(row_idx, 0).data(TaskRoles.BoardColumn) == BOARD_COLUMN_COMPLETED

        model.step_board_column_by_row(row_idx, -1)
        row_idx = _find_task_row(model, created.id)
        assert model.index(row_idx, 0).data(TaskRoles.BoardColumn) == BOARD_COLUMN_IN_PROGRESS

        model.step_board_column_by_row(row_idx, -1)
        row_idx = _find_task_row(model, created.id)
        assert model.index(row_idx, 0).data(TaskRoles.BoardColumn) == BOARD_COLUMN_QUEUE

        model.step_board_column_by_row(row_idx, -1)
        model.set_filter_mode("Отложенные")
        row_idx = _find_task_row(model, created.id)
        assert row_idx >= 0
        assert model.index(row_idx, 0).data(TaskRoles.BoardColumn) == BOARD_COLUMN_DEFERRED
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_tasks_model_steps_plan_item_order_up_and_down_without_wrap(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("tasks_plan_order_step", ".sqlite3")
    database = Database(path=db_path)
    try:
        root = database.create_task(
            title="Plan root",
            description="",
            day=date(2026, 3, 6),
            time_text="09:00",
            priority="High",
            is_plan_task=True,
        )
        first = database.create_task(
            title="First step",
            description="",
            day=date(2026, 3, 6),
            time_text="09:10",
            priority="Medium",
            parent_id=root.id,
        )
        second = database.create_task(
            title="Second step",
            description="",
            day=date(2026, 3, 6),
            time_text="09:20",
            priority="Medium",
            parent_id=root.id,
        )
        third = database.create_task(
            title="Third step",
            description="",
            day=date(2026, 3, 6),
            time_text="09:30",
            priority="Medium",
            parent_id=root.id,
        )
        monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)
        model = tasks_workspace.TasksModel()
        model.set_filter_mode("РџР»Р°РЅ")

        root_row = _find_task_row(model, root.id)
        assert root_row >= 0
        model.expand_subtasks_tree_by_row(root_row)

        second_row = _find_task_row(model, second.id)
        assert second_row >= 0
        assert model.can_step_plan_item_order(second.id, -1) is True
        assert model.can_step_plan_item_order(second.id, +1) is True

        model.step_plan_item_order_by_row(second_row, -1)

        root_row = _find_task_row(model, root.id)
        model.expand_subtasks_tree_by_row(root_row)
        assert model.index(_find_task_row(model, second.id), 0).data(TaskRoles.PlanNumber) == "1."
        assert model.index(_find_task_row(model, first.id), 0).data(TaskRoles.PlanNumber) == "2."
        assert model.index(_find_task_row(model, third.id), 0).data(TaskRoles.PlanNumber) == "3."

        moved_row = _find_task_row(model, second.id)
        assert moved_row >= 0
        assert model.can_step_plan_item_order(second.id, -1) is False
        model.step_plan_item_order_by_row(moved_row, -1)

        root_row = _find_task_row(model, root.id)
        model.expand_subtasks_tree_by_row(root_row)
        assert model.index(_find_task_row(model, second.id), 0).data(TaskRoles.PlanNumber) == "1."

        moved_row = _find_task_row(model, second.id)
        model.step_plan_item_order_by_row(moved_row, +1)

        root_row = _find_task_row(model, root.id)
        model.expand_subtasks_tree_by_row(root_row)
        assert model.index(_find_task_row(model, first.id), 0).data(TaskRoles.PlanNumber) == "1."
        assert model.index(_find_task_row(model, second.id), 0).data(TaskRoles.PlanNumber) == "2."
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_tasks_delegate_priority_block_orders_icon_controls_and_stage_text() -> None:
    delegate = tasks_workspace.TasksItemDelegate()
    rects = delegate._priority_control_rects(tasks_workspace.QRect(0, 0, 220, 30))
    assert rects["icon"].left() < rects["priority_arrows"].left()
    assert rects["priority_arrows"].right() < rects["value"].left()
    assert rects["value"].right() < rects["stage_arrows"].left()


def test_tasks_delegate_plan_time_controls_place_arrows_right_of_time_text() -> None:
    delegate = tasks_workspace.TasksItemDelegate()
    controls = delegate._time_control_rects(tasks_workspace.QRect(0, 0, delegate.TIME_W, 30), show_plan_controls=True)
    assert controls["text"].left() == 0
    assert controls["text"].right() < controls["plan_arrows"].left()
    assert not controls["plan_up"].isNull()
    assert not controls["plan_down"].isNull()

    no_controls = delegate._time_control_rects(tasks_workspace.QRect(0, 0, delegate.TIME_W, 30), show_plan_controls=False)
    assert no_controls["plan_arrows"].isNull()
    assert no_controls["plan_up"].isNull()
    assert no_controls["plan_down"].isNull()


def test_task_priority_pickers_use_high_medium_low_deferred_order(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("tasks_priority_picker_order", ".sqlite3")
    database = Database(path=db_path)
    monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)
    monkeypatch.setattr(task_edit_dialog, "get_database", lambda: database)
    workspace = None
    dialog = None
    try:
        workspace = tasks_workspace.TasksWorkspace()
        assert [workspace.new_priority.itemText(idx) for idx in range(workspace.new_priority.count())] == [
            "High",
            "Medium",
            "Low",
            "Отложенная",
        ]
        assert [workspace.cmb_priority.itemText(idx) for idx in range(workspace.cmb_priority.count())] == [
            "Любой",
            "High",
            "Medium",
            "Low",
            "Отложенная",
        ]

        dialog = task_edit_dialog.TaskEditDialog(
            TaskRow(
                id=0,
                day=date(2026, 3, 6),
                time_text="",
                title="Task",
                description="",
                priority="Medium",
                done=False,
            )
        )
        assert [dialog.priority_edit.itemText(idx) for idx in range(dialog.priority_edit.count())] == [
            "High",
            "Medium",
            "Low",
            "Отложенная",
        ]
    finally:
        if dialog is not None:
            dialog.deleteLater()
        if workspace is not None:
            workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_task_edit_dialog_attachment_sources_include_active_and_archived_ideas(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("task_edit_dialog_attachment_ideas", ".sqlite3")
    database = Database(path=db_path)
    dialog = None
    try:
        task = database.create_task(
            title="Task",
            description="",
            day=date(2026, 3, 6),
            time_text="",
            priority="Medium",
        )
        active_idea = database.create_idea(title="Active idea", status="inbox")
        archived_idea = database.create_idea(title="Archived idea", status="inbox")
        database.set_idea_archived(archived_idea.id, True)

        monkeypatch.setattr(task_edit_dialog, "get_database", lambda: database)
        dialog = task_edit_dialog.TaskEditDialog(next(item for item in database.fetch_tasks() if item.id == task.id))

        assert active_idea.id in dialog._ideas_by_id
        assert archived_idea.id in dialog._ideas_by_id
        assert dialog._ideas_by_id[active_idea.id].title == "Active idea"
        assert dialog._ideas_by_id[archived_idea.id].title == "Archived idea"
    finally:
        if dialog is not None:
            dialog.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_task_edit_dialog_attachment_dialog_is_compact(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("task_edit_dialog_attachment_compact", ".sqlite3")
    database = Database(path=db_path)
    dialog = None
    attachment_dialog = None
    try:
        task = database.create_task(
            title="Task",
            description="",
            day=date(2026, 3, 6),
            time_text="",
            priority="Medium",
        )
        database.create_note(
            title="Very long attachment entity title for compact dialog verification",
            preview="",
            tags=[],
            project="",
        )
        monkeypatch.setattr(task_edit_dialog, "get_database", lambda: database)

        dialog = task_edit_dialog.TaskEditDialog(next(item for item in database.fetch_tasks() if item.id == task.id))
        attachment_dialog, kind_combo, item_combo = dialog._create_attachment_dialog()

        assert attachment_dialog.minimumWidth() == 550
        assert attachment_dialog.maximumWidth() == 550
        assert attachment_dialog.minimumHeight() == 200
        assert attachment_dialog.maximumHeight() == 200
        assert kind_combo.sizeAdjustPolicy() == QComboBox.SizeAdjustPolicy.AdjustToContents
        assert isinstance(item_combo, FilterableComboBox)
        assert item_combo.sizeAdjustPolicy() == QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        assert item_combo.minimumContentsLength() == 24
        assert item_combo.completer().popup().objectName() == "FilterableComboPopup"
        assert "#1f2026" in item_combo.completer().popup().styleSheet()
    finally:
        if attachment_dialog is not None:
            attachment_dialog.deleteLater()
        if dialog is not None:
            dialog.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_task_edit_dialog_attachment_dialog_item_combo_filters_by_substring(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("task_edit_dialog_attachment_filter", ".sqlite3")
    database = Database(path=db_path)
    dialog = None
    attachment_dialog = None
    try:
        task = database.create_task(
            title="Task",
            description="",
            day=date(2026, 3, 6),
            time_text="",
            priority="Medium",
        )
        keep = database.create_note(title="Alpha note", preview="", tags=[], project="")
        target = database.create_note(title="Beta reference note", preview="", tags=[], project="")
        monkeypatch.setattr(task_edit_dialog, "get_database", lambda: database)

        dialog = task_edit_dialog.TaskEditDialog(next(item for item in database.fetch_tasks() if item.id == task.id))
        attachment_dialog, kind_combo, item_combo = dialog._create_attachment_dialog()
        kind_combo.setCurrentIndex(kind_combo.findData("note"))
        QApplication.processEvents()

        line_edit = item_combo.lineEdit()
        assert line_edit is not None
        line_edit.setFocus()
        line_edit.selectAll()
        QTest.keyClicks(line_edit, "beta")
        QApplication.processEvents()

        completion_model = item_combo.completer().completionModel()
        assert completion_model.rowCount() == 1
        item_combo._on_completer_activated(completion_model.index(0, 0))

        assert item_combo.currentData() == target.id
        assert item_combo.currentData() != keep.id
    finally:
        if attachment_dialog is not None:
            attachment_dialog.deleteLater()
        if dialog is not None:
            dialog.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_task_edit_dialog_attachment_dialog_opens_file_picker_for_file_kind(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("task_edit_dialog_attachment_file_picker", ".sqlite3")
    database = Database(path=db_path)
    dialog = None
    attachment_dialog = None
    picker_calls: list[str] = []
    try:
        task = database.create_task(
            title="Task",
            description="",
            day=date(2026, 3, 6),
            time_text="",
            priority="Medium",
        )
        database.upsert_cloud_file(
            rel_path="docs/spec.pdf",
            name="spec.pdf",
            description="",
            checksum="checksum-task-file",
            hash_value="hash-task-file",
            size=128,
            is_image=False,
            valid=True,
        )

        class _FakeAttachDialog:
            def __init__(self, parent=None) -> None:
                picker_calls.append(type(parent).__name__)

            def exec(self) -> int:
                return int(task_edit_dialog.QDialog.DialogCode.Accepted)

            def selected_rel_path(self) -> str:
                return "docs/spec.pdf"

        monkeypatch.setattr(task_edit_dialog, "get_database", lambda: database)
        monkeypatch.setattr(task_edit_dialog, "AttachFileSelectNav", _FakeAttachDialog)

        dialog = task_edit_dialog.TaskEditDialog(next(item for item in database.fetch_tasks() if item.id == task.id))
        attachment_dialog, kind_combo, item_combo = dialog._create_attachment_dialog()

        kind_combo.setCurrentIndex(kind_combo.findData("file"))
        QApplication.processEvents()

        assert picker_calls == ["TaskEditDialog"]
        assert item_combo.currentData() is not None
        selected = database.fetch_cloud_files()[0]
        assert item_combo.currentData() == selected.id
    finally:
        if attachment_dialog is not None:
            attachment_dialog.deleteLater()
        if dialog is not None:
            dialog.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_task_create_dialog_suggests_project_by_title(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("tasks_project_suggest", ".sqlite3")
    database = Database(path=db_path)
    try:
        backend = database.create_project(
            area="Work",
            title="Backend API",
            updated=date(2026, 3, 6),
            priority="Medium",
        )
        _personal = database.create_project(
            area="Life",
            title="Personal Home",
            updated=date(2026, 3, 6),
            priority="Medium",
        )
        monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)

        dialog = tasks_workspace.TaskCreateDialog()
        try:
            dialog.title_edit.setText("Refactor backend API endpoints")
            QApplication.processEvents()
            assert dialog.project_edit.currentData() == backend.id
        finally:
            dialog.deleteLater()
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_tasks_workspace_switches_board_and_dash_modes(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("tasks_board_dash_modes", ".sqlite3")
    database = Database(path=db_path)
    monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)
    workspace = tasks_workspace.TasksWorkspace()
    try:
        assert workspace.btn_gantt.text() == "GANTT"
        assert workspace.btn_board.text() == "BOARD"
        assert workspace.btn_dash.text() == "DASH"
        assert workspace.btn_gantt.parent() is workspace.toolbar_row
        assert workspace.btn_board.parent() is workspace.toolbar_row
        assert workspace.btn_dash.parent() is workspace.toolbar_row

        toolbar_texts = [
            widget.text()
            for idx in range(workspace.toolbar_layout.count())
            if (item := workspace.toolbar_layout.itemAt(idx)) is not None
            if (widget := item.widget()) is not None
            if isinstance(widget, tasks_workspace.QToolButton)
        ]
        assert toolbar_texts[:3] == ["GANTT", "BOARD", "DASH"]

        workspace.btn_board.setChecked(True)
        assert workspace._board_mode is True
        assert workspace._dash_mode is False
        assert workspace.content_stack.currentWidget() is workspace.board_page

        workspace.btn_dash.setChecked(True)
        assert workspace._board_mode is False
        assert workspace._dash_mode is True
        assert workspace.content_stack.currentWidget() is workspace.dash_page

        workspace.btn_dash.setChecked(False)
        assert workspace._gantt_mode is False
        assert workspace._board_mode is False
        assert workspace._dash_mode is False
        assert workspace.content_stack.currentWidget() is workspace.list
    finally:
        workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_tasks_workspace_board_uses_kanban_columns_in_expected_order(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("tasks_board_columns_order", ".sqlite3")
    database = Database(path=db_path)
    monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)
    workspace = tasks_workspace.TasksWorkspace()
    try:
        assert list(workspace.board_columns.keys()) == [
            BOARD_COLUMN_DEFERRED,
            BOARD_COLUMN_QUEUE,
            BOARD_COLUMN_IN_PROGRESS,
            BOARD_COLUMN_COMPLETED,
        ]
    finally:
        workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_tasks_workspace_project_quick_links_show_top_five(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("tasks_project_quick_links", ".sqlite3")
    database = Database(path=db_path)
    monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)
    workspace = None
    try:
        projects = []
        for idx, count in enumerate([6, 5, 4, 3, 2, 1], start=1):
            project = database.create_project(
                area="Area",
                title=f"Project {idx}",
                updated=date(2026, 3, 6),
                priority="Medium",
            )
            projects.append((project, count))
        for project, count in projects:
            for task_idx in range(count):
                database.create_task(
                    title=f"T{project.id}-{task_idx}",
                    description="",
                    day=date(2026, 3, 6),
                    time_text="09:00",
                    priority="Medium",
                    project_id=project.id,
                )

        workspace = tasks_workspace.TasksWorkspace()
        workspace._refresh_project_quick_links()
        labels = [button.text() for button in workspace._project_quick_link_buttons]

        assert len(labels) == 5
        assert labels[0].endswith("(6)")
        assert labels[-1].endswith("(2)")
    finally:
        if workspace is not None:
            workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_tasks_workspace_project_quick_link_click_toggles_filter(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("tasks_project_quick_link_toggle", ".sqlite3")
    database = Database(path=db_path)
    monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)
    workspace = None
    try:
        project = database.create_project(
            area="Area",
            title="Pinned Project",
            updated=date(2026, 3, 6),
            priority="Medium",
        )
        database.create_task(
            title="Pinned task",
            description="",
            day=date(2026, 3, 6),
            time_text="09:00",
            priority="Medium",
            project_id=project.id,
        )
        database.create_task(
            title="Unfiltered task",
            description="",
            day=date(2026, 3, 6),
            time_text="10:00",
            priority="Medium",
        )

        workspace = tasks_workspace.TasksWorkspace()
        workspace._refresh_project_quick_links()
        assert len(workspace._project_quick_link_buttons) == 1
        quick_link = workspace._project_quick_link_buttons[0]

        quick_link.click()
        QApplication.processEvents()
        assert workspace.model._project_filter_id == project.id
        assert quick_link.isChecked() is True

        quick_link.click()
        QApplication.processEvents()
        assert workspace.model._project_filter_id is None
        assert quick_link.isChecked() is False
    finally:
        if workspace is not None:
            workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_tasks_workspace_project_filter_can_be_cleared_after_mode_switch(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("tasks_project_quick_link_clear_button", ".sqlite3")
    database = Database(path=db_path)
    monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)
    workspace = None
    try:
        project = database.create_project(
            area="Area",
            title="CODEX",
            updated=date(2026, 3, 6),
            priority="Medium",
        )
        database.create_task(
            title="CODEX task",
            description="",
            day=date(2026, 3, 6),
            time_text="09:00",
            priority="Medium",
            project_id=project.id,
        )
        database.create_task(
            title="Common task",
            description="",
            day=date(2026, 3, 6),
            time_text="10:00",
            priority="Medium",
        )

        workspace = tasks_workspace.TasksWorkspace()
        workspace.set_filter("tab", "all")
        workspace._refresh_project_quick_links()
        quick_link = workspace._project_quick_link_buttons[0]

        quick_link.click()
        QApplication.processEvents()
        assert workspace.model._project_filter_id == project.id
        assert workspace._project_filter_clear_button is not None
        assert workspace._project_filter_clear_button.isHidden() is False

        workspace.set_filter("tab", "plan")
        QApplication.processEvents()
        assert workspace.model._project_filter_id == project.id
        assert workspace._project_filter_clear_button.isHidden() is False

        workspace._project_filter_clear_button.click()
        QApplication.processEvents()
        assert workspace.model._project_filter_id is None
        assert workspace._project_filter_clear_button.isHidden() is True
    finally:
        if workspace is not None:
            workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_tasks_workspace_project_clear_button_survives_refresh_event_cycle(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("tasks_project_clear_button_lifetime", ".sqlite3")
    database = Database(path=db_path)
    monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)
    workspace = None
    try:
        project = database.create_project(
            area="Area",
            title="Live Project",
            updated=date(2026, 3, 6),
            priority="Medium",
        )
        database.create_task(
            title="Live task",
            description="",
            day=date(2026, 3, 6),
            time_text="09:00",
            priority="Medium",
            project_id=project.id,
        )

        workspace = tasks_workspace.TasksWorkspace()
        QApplication.processEvents()
        workspace._refresh_project_quick_links()
        QApplication.processEvents()

        workspace.set_filter("tab", "all")
        QApplication.processEvents()
        workspace._project_quick_link_buttons[0].click()
        QApplication.processEvents()

        assert workspace.model._project_filter_id == project.id
        assert workspace._project_filter_clear_button is not None
        assert workspace._project_filter_clear_button.isHidden() is False

        workspace.set_filter("tab", "plan")
        QApplication.processEvents()
        assert workspace._project_filter_clear_button.isHidden() is False
    finally:
        if workspace is not None:
            workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_tasks_board_defaults_to_queue_and_completed_is_not_done(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("tasks_board_default_and_completed", ".sqlite3")
    database = Database(path=db_path)
    monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)
    workspace = None
    try:
        queued_task = database.create_task(
            title="Queued task",
            description="",
            day=date(2026, 3, 6),
            time_text="09:00",
            priority="Medium",
        )
        deferred_task = database.create_task(
            title="Deferred task",
            description="",
            day=date(2026, 3, 6),
            time_text="10:00",
            priority=DEFERRED_PRIORITY,
        )

        fetched = {task.id: task for task in database.fetch_tasks()}
        assert fetched[queued_task.id].board_column == BOARD_COLUMN_QUEUE
        assert fetched[deferred_task.id].board_column == BOARD_COLUMN_DEFERRED

        workspace = tasks_workspace.TasksWorkspace()
        workspace._focus_day = date(2026, 3, 6)
        workspace._move_task_to_board_column(queued_task.id, BOARD_COLUMN_COMPLETED)

        updated = {task.id: task for task in database.fetch_tasks()}[queued_task.id]
        assert updated.board_column == BOARD_COLUMN_COMPLETED
        assert updated.done is False
    finally:
        if workspace is not None:
            workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_tasks_board_move_to_deferred_and_in_progress_persists(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("tasks_board_move_persists", ".sqlite3")
    database = Database(path=db_path)
    monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)
    workspace = None
    try:
        task = database.create_task(
            title="Board task",
            description="",
            day=date(2026, 3, 6),
            time_text="09:00",
            priority="High",
        )

        workspace = tasks_workspace.TasksWorkspace()
        workspace._focus_day = date(2026, 3, 6)
        workspace._move_task_to_board_column(task.id, BOARD_COLUMN_DEFERRED)
        deferred_state = {item.id: item for item in database.fetch_tasks()}[task.id]
        assert deferred_state.board_column == BOARD_COLUMN_DEFERRED
        assert deferred_state.priority == DEFERRED_PRIORITY

        workspace._move_task_to_board_column(task.id, BOARD_COLUMN_IN_PROGRESS)
        active_state = {item.id: item for item in database.fetch_tasks()}[task.id]
        assert active_state.board_column == BOARD_COLUMN_IN_PROGRESS
        assert active_state.priority == "Medium"
        assert active_state.done is False
    finally:
        if workspace is not None:
            workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_tasks_board_refresh_groups_tasks_by_board_column(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("tasks_board_groups", ".sqlite3")
    database = Database(path=db_path)
    monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)
    workspace = None
    try:
        queue_task = database.create_task(
            title="Queue task",
            description="",
            day=date(2026, 3, 6),
            time_text="09:00",
            priority="Medium",
        )
        in_progress_task = database.create_task(
            title="In progress task",
            description="",
            day=date(2026, 3, 6),
            time_text="10:00",
            priority="High",
        )
        completed_task = database.create_task(
            title="Completed task",
            description="",
            day=date(2026, 3, 6),
            time_text="11:00",
            priority="Low",
        )
        deferred_task = database.create_task(
            title="Deferred task",
            description="",
            day=date(2026, 3, 6),
            time_text="12:00",
            priority=DEFERRED_PRIORITY,
        )
        database.set_task_board_column(in_progress_task.id, BOARD_COLUMN_IN_PROGRESS)
        database.set_task_board_column(completed_task.id, BOARD_COLUMN_COMPLETED)

        workspace = tasks_workspace.TasksWorkspace()
        workspace._focus_day = date(2026, 3, 6)
        workspace._refresh_board_day()

        assert workspace.board_columns[BOARD_COLUMN_QUEUE].count() == 1
        assert workspace.board_columns[BOARD_COLUMN_IN_PROGRESS].count() == 1
        assert workspace.board_columns[BOARD_COLUMN_COMPLETED].count() == 1
        assert workspace.board_columns[BOARD_COLUMN_DEFERRED].count() == 1
        assert workspace.board_columns[BOARD_COLUMN_QUEUE].item(0).data(tasks_workspace.Qt.ItemDataRole.UserRole) == queue_task.id
        assert workspace.board_columns[BOARD_COLUMN_DEFERRED].item(0).data(tasks_workspace.Qt.ItemDataRole.UserRole) == deferred_task.id
    finally:
        if workspace is not None:
            workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_tasks_board_has_separate_day_filter_toggle(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("tasks_board_day_filter_toggle", ".sqlite3")
    database = Database(path=db_path)
    monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)
    workspace = None
    try:
        today_task = database.create_task(
            title="Today board task",
            description="",
            day=date(2026, 3, 6),
            time_text="09:00",
            priority="Medium",
        )
        other_day_task = database.create_task(
            title="Next day board task",
            description="",
            day=date(2026, 3, 7),
            time_text="10:00",
            priority="High",
        )

        workspace = tasks_workspace.TasksWorkspace()
        workspace._focus_day = date(2026, 3, 6)
        workspace.btn_board.setChecked(True)

        assert workspace.board_day_filter_checkbox.text() == "Фильтрация по дню"
        assert workspace.board_day_filter_checkbox.isChecked() is True

        workspace._refresh_board_day()
        assert workspace.board_columns[BOARD_COLUMN_QUEUE].count() == 1
        assert workspace.board_columns[BOARD_COLUMN_QUEUE].item(0).data(tasks_workspace.Qt.ItemDataRole.UserRole) == today_task.id

        workspace.board_day_filter_checkbox.setChecked(False)

        assert workspace.lbl_day.text() == "Все дни"
        assert workspace.btn_prev_day.isEnabled() is False
        assert workspace.btn_next_day.isEnabled() is False
        assert workspace.board_columns[BOARD_COLUMN_QUEUE].count() >= 2
        queue_titles = [
            workspace.board_columns[BOARD_COLUMN_QUEUE].item(index).text()
            for index in range(workspace.board_columns[BOARD_COLUMN_QUEUE].count())
        ]
        assert any("2026-03-06" in text and "Today board task" in text for text in queue_titles)
        assert any("2026-03-07" in text and "Next day board task" in text for text in queue_titles)
    finally:
        if workspace is not None:
            workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_tasks_workspace_flashes_task_after_move_to_tomorrow(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("tasks_flash_after_tomorrow_move", ".sqlite3")
    database = Database(path=db_path)
    monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)
    workspace = None
    try:
        task = database.create_task(
            title="Tomorrow move task",
            description="",
            day=date(2026, 3, 6),
            time_text="09:00",
            priority="Medium",
        )

        workspace = tasks_workspace.TasksWorkspace()
        moved = workspace.model.move_task_to_day(task.id, date(2026, 3, 7))
        QApplication.processEvents()

        assert moved is True
        assert task.id in workspace.delegate._task_flash_progress
    finally:
        if workspace is not None:
            workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_tasks_workspace_flashes_task_after_drag_and_drop(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("tasks_flash_after_drag_drop", ".sqlite3")
    database = Database(path=db_path)
    monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)
    workspace = None
    try:
        moved_task = database.create_task(
            title="Drag source",
            description="",
            day=date(2026, 3, 6),
            time_text="09:00",
            priority="Medium",
        )
        database.create_task(
            title="Next day anchor",
            description="",
            day=date(2026, 3, 7),
            time_text="10:00",
            priority="Medium",
        )

        workspace = tasks_workspace.TasksWorkspace()
        source_row = _find_task_row(workspace.model, moved_task.id)
        assert source_row >= 0
        source_index = workspace.model.index(source_row, 0)
        mime_data = workspace.model.mimeData([source_index])
        header_index = next(
            (
                workspace.model.index(row, 0)
                for row in range(workspace.model.rowCount())
                if workspace.model.index(row, 0).data(TaskRoles.RowType) == "header"
                and workspace.model.index(row, 0).data(TaskRoles.Day) == date(2026, 3, 7)
            ),
            None,
        )
        assert header_index is not None

        dropped = workspace.model.dropMimeData(
            mime_data,
            tasks_workspace.Qt.DropAction.MoveAction,
            -1,
            0,
            header_index,
        )
        QApplication.processEvents()

        assert dropped is True
        assert moved_task.id in workspace.delegate._task_flash_progress
    finally:
        if workspace is not None:
            workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_tasks_dash_shows_classic_entity_statistics(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("tasks_dash_classic_stats", ".sqlite3")
    database = Database(path=db_path)
    monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)
    workspace = None
    try:
        project = database.create_project(
            area="Area",
            title="Dash Project",
            updated=date(2026, 3, 6),
            priority="Medium",
        )
        database.create_task(
            title="Dash task",
            description="",
            day=date(2026, 3, 6),
            time_text="09:00",
            priority="High",
            project_id=project.id,
        )
        map_item = database.create_map(
            title="Dash Map",
            description="",
            project=project.title,
            tiles_path="",
            tiles_h=10,
            tiles_w=10,
        )
        database.upsert_map_marker(
            marker_id=101,
            map_id=map_item.id,
            name="Dash Marker",
            x=10.0,
            y=20.0,
            color="#ffffff",
            marker_type="pin",
            size=16.0,
        )
        database.create_object(
            title="Dash Object",
            catalog="Catalog",
            object_type="Type",
            status="Active",
            description="",
        )
        database.create_note(
            title="Dash Note",
            preview="Body",
            tags=[],
            project=project.title,
        )
        expected_totals = (
            len(database.fetch_tasks()),
            len(database.fetch_projects()),
            len(database.fetch_maps()),
            len(database.fetch_map_markers()),
            len(database.fetch_objects()),
            len(database.fetch_notes()),
        )

        workspace = tasks_workspace.TasksWorkspace()
        workspace._focus_day = date(2026, 3, 6)
        workspace._refresh_dash_day()
        QApplication.processEvents()

        summary = workspace.dash_summary_label.text()
        assert f"DASH на 2026-03-06: диаграммы пересчитаны и заполнены заново." in summary
        assert "На 2026-03-06: активных задач 1, High 1, Medium 0, Low 0, Отложенных 0." in summary
        assert "Результативность: нет завершенных задач для сравнения." in summary
        assert workspace.dash_bar_chart is not None
        assert workspace.dash_pie_chart is not None
        assert workspace.dash_pulse_chart is not None
        assert [(label, value) for label, value, _ in workspace.dash_bar_chart._items] == [
            ("Задачи", expected_totals[0]),
            ("Проекты", expected_totals[1]),
            ("Карты", expected_totals[2]),
            ("Метки", expected_totals[3]),
            ("Объекты", expected_totals[4]),
            ("Заметки", expected_totals[5]),
        ]
        assert [(label, value) for label, value, _ in workspace.dash_pie_chart._items] == [
            ("Задачи", expected_totals[0]),
            ("Проекты", expected_totals[1]),
            ("Карты", expected_totals[2]),
            ("Метки", expected_totals[3]),
            ("Объекты", expected_totals[4]),
            ("Заметки", expected_totals[5]),
        ]
        assert [(label, value) for label, value, _ in workspace.dash_pulse_chart._items] == [
            ("01.03", 0),
            ("02.03", 0),
            ("03.03", 0),
            ("04.03", 0),
            ("05.03", 0),
            ("06.03", 0),
        ]
    finally:
        if workspace is not None:
            workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_tasks_dash_shows_resultativity_against_previous_periods(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("tasks_dash_resultativity", ".sqlite3")
    database = Database(path=db_path)
    workspace = None
    try:
        _create_completed_task(database, "Prev 1", date(2026, 3, 1))
        _create_completed_task(database, "Prev 2", date(2026, 3, 2))
        _create_completed_task(database, "Prev 3", date(2026, 3, 4))
        _create_completed_task(database, "Recent 1", date(2026, 3, 5))
        _create_completed_task(database, "Recent 2", date(2026, 3, 6))
        _create_completed_task(database, "Recent 3", date(2026, 3, 6), priority="High")

        monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)
        workspace = tasks_workspace.TasksWorkspace()
        workspace._focus_day = date(2026, 3, 6)
        workspace._refresh_dash_day()
        QApplication.processEvents()

        summary = workspace.dash_summary_label.text()
        assert (
            "Результативность: 2.00x к прошлому темпу "
            "(импульс за последние 2 дня 3; база прошлых периодов 1.50 на 2 дня)."
        ) in summary
        assert workspace.dash_pulse_chart is not None
        assert [(label, value) for label, value, _ in workspace.dash_pulse_chart._items] == [
            ("01.03", 1),
            ("02.03", 1),
            ("03.03", 0),
            ("04.03", 1),
            ("05.03", 1),
            ("06.03", 2),
        ]
    finally:
        if workspace is not None:
            workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_tasks_delegate_attachment_display_name_for_note(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("tasks_attachment_menu_note", ".sqlite3")
    database = Database(path=db_path)
    try:
        task = database.create_task(
            title="Task with attachment",
            description="",
            day=date(2026, 3, 6),
            time_text="",
            priority="Medium",
        )
        note = database.create_note(
            title="Attached note",
            preview="Body",
            tags=[],
            project="Area",
        )
        database.add_task_attachment(task.id, "note", note.id)
        attachment = database.fetch_task_attachments(task.id)[0]
        monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)
        delegate = tasks_workspace.TasksItemDelegate()
        assert delegate._attachment_display_name(attachment) == "Attached note"
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_tasks_delegate_attachment_display_name_for_task(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("tasks_attachment_menu_task", ".sqlite3")
    database = Database(path=db_path)
    try:
        task = database.create_task(
            title="Task with attachment",
            description="",
            day=date(2026, 3, 6),
            time_text="",
            priority="Medium",
        )
        linked_task = database.create_task(
            title="Attached task",
            description="Body",
            day=date(2026, 3, 7),
            time_text="10:00",
            priority="High",
        )
        database.add_task_attachment(task.id, "task", linked_task.id)
        attachment = database.fetch_task_attachments(task.id)[0]
        monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)
        delegate = tasks_workspace.TasksItemDelegate()
        assert delegate._attachment_display_name(attachment) == "Attached task"
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_tasks_model_keeps_done_plan_items_visible_and_numbered_until_parent_done(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("tasks_plan_items_visible", ".sqlite3")
    database = Database(path=db_path)
    try:
        root = database.create_task(
            title="Plan root",
            description="",
            day=date(2026, 3, 6),
            time_text="09:00",
            priority="High",
            is_plan_task=True,
        )
        child = database.create_task(
            title="Plan child",
            description="",
            day=date(2026, 3, 6),
            time_text="09:10",
            priority="Low",
            parent_id=root.id,
        )
        grandchild = database.create_task(
            title="Plan grandchild",
            description="",
            day=date(2026, 3, 6),
            time_text="09:20",
            priority="Medium",
            parent_id=child.id,
        )
        monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)
        model = tasks_workspace.TasksModel()
        model.set_filter_mode("План")

        root_row = _find_task_row(model, root.id)
        assert root_row >= 0
        model.expand_subtasks_tree_by_row(root_row)

        child_row = _find_task_row(model, child.id)
        grandchild_row = _find_task_row(model, grandchild.id)
        assert child_row >= 0
        assert grandchild_row >= 0
        assert model.index(child_row, 0).data(TaskRoles.IsPlanItem) is True
        assert model.index(child_row, 0).data(TaskRoles.PlanNumber) == "1."
        assert model.index(grandchild_row, 0).data(TaskRoles.IsPlanItem) is False
        assert model.index(grandchild_row, 0).data(TaskRoles.PlanNumber) == ""

        model.toggle_done_by_row(child_row)
        child_row = _find_task_row(model, child.id)
        assert child_row >= 0
        assert model.index(child_row, 0).data(TaskRoles.Done) is True

        priority_before = next(task.priority for task in database.fetch_tasks() if task.id == child.id)
        model.step_priority_by_row(child_row, +1)
        priority_after = next(task.priority for task in database.fetch_tasks() if task.id == child.id)
        assert priority_after == priority_before
        assert tasks_workspace.TasksItemDelegate._is_overdue(date(2026, 3, 5), False, is_plan_item=True) is False
        assert tasks_workspace.TasksItemDelegate._is_overdue(
            date(2026, 3, 5),
            False,
            priority=DEFERRED_PRIORITY,
        ) is False
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_plan_execution_advances_current_item_and_records_actuals(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("tasks_plan_execution_progression", ".sqlite3")
    database = Database(path=db_path)
    try:
        root = database.create_task(
            title="Execution plan",
            description="",
            day=date(2026, 3, 6),
            time_text="09:00",
            priority="High",
            is_plan_task=True,
        )
        first = database.create_task(
            title="Investigate API",
            description="integration test setup",
            day=date(2026, 3, 6),
            time_text="09:10",
            priority="Medium",
            parent_id=root.id,
        )
        second = database.create_task(
            title="Ship fix",
            description="prepare rollout",
            day=date(2026, 3, 6),
            time_text="09:20",
            priority="Medium",
            parent_id=root.id,
        )
        started_at = (datetime.now(timezone.utc) - timedelta(minutes=60)).isoformat(timespec="seconds")
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with database._conn:
            database._conn.execute(
                """
                UPDATE tasks
                SET started_at = ?, gantt_estimate_minutes = 20, gantt_forecasted = 1, updated_at = ?
                WHERE id = ?;
                """,
                (started_at, now, first.id),
            )
            database._conn.execute(
                """
                UPDATE tasks
                SET started_at = '', gantt_estimate_minutes = 40, gantt_forecasted = 1, updated_at = ?
                WHERE id = ?;
                """,
                (now, second.id),
            )

        monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)
        model = tasks_workspace.TasksModel()
        model.set_filter_mode("План")

        root_row = _find_task_row(model, root.id)
        assert root_row >= 0
        model.expand_subtasks_tree_by_row(root_row)

        first_row = _find_task_row(model, first.id)
        second_row = _find_task_row(model, second.id)
        assert first_row >= 0 and second_row >= 0
        assert model.index(first_row, 0).data(TaskRoles.IsPlanItem) is True
        assert model.index(first_row, 0).data(TaskRoles.IsCurrentPlanItem) is True
        assert model.index(first_row, 0).data(TaskRoles.StartedAt) == started_at
        assert model.index(first_row, 0).data(TaskRoles.ActualMinutes) == 0
        assert model.index(second_row, 0).data(TaskRoles.IsCurrentPlanItem) is False
        assert model.index(second_row, 0).data(TaskRoles.StartedAt) == ""

        model.toggle_done_by_row(first_row)

        stored_tasks = {task.id: task for task in database.fetch_tasks()}
        completed = stored_tasks[first.id]
        next_item = stored_tasks[second.id]
        assert completed.done is True
        assert completed.finished_at
        assert completed.actual_minutes >= 55
        assert next_item.started_at
        assert next_item.finished_at == ""
        assert next_item.actual_minutes == 0
        assert next_item.gantt_estimate_minutes >= 115

        root_row = _find_task_row(model, root.id)
        model.expand_subtasks_tree_by_row(root_row)
        first_row = _find_task_row(model, first.id)
        second_row = _find_task_row(model, second.id)
        assert first_row >= 0 and second_row >= 0
        assert model.index(first_row, 0).data(TaskRoles.IsCurrentPlanItem) is False
        assert model.index(first_row, 0).data(TaskRoles.FinishedAt) == completed.finished_at
        assert model.index(first_row, 0).data(TaskRoles.ActualMinutes) == completed.actual_minutes
        assert model.index(second_row, 0).data(TaskRoles.IsCurrentPlanItem) is True
        assert model.index(second_row, 0).data(TaskRoles.StartedAt) == next_item.started_at
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_tasks_model_plan_item_drag_drop_reorders_only_within_parent(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("tasks_plan_drag_drop", ".sqlite3")
    database = Database(path=db_path)
    try:
        root = database.create_task(
            title="Plan root",
            description="",
            day=date(2026, 3, 6),
            time_text="09:00",
            priority="High",
            is_plan_task=True,
        )
        first = database.create_task(
            title="First step",
            description="",
            day=date(2026, 3, 6),
            time_text="09:10",
            priority="Medium",
            parent_id=root.id,
        )
        second = database.create_task(
            title="Second step",
            description="",
            day=date(2026, 3, 6),
            time_text="09:20",
            priority="Medium",
            parent_id=root.id,
        )
        other_root = database.create_task(
            title="Other root",
            description="",
            day=date(2026, 3, 6),
            time_text="10:00",
            priority="Medium",
        )
        monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)
        model = tasks_workspace.TasksModel()
        model.set_filter_mode("План")

        root_row = _find_task_row(model, root.id)
        assert root_row >= 0
        model.expand_subtasks_tree_by_row(root_row)

        second_row = _find_task_row(model, second.id)
        first_row = _find_task_row(model, first.id)
        other_row = _find_task_row(model, other_root.id)
        assert second_row >= 0 and first_row >= 0 and other_row >= 0

        mime_data = model.mimeData([model.index(second_row, 0)])
        reordered = model.dropMimeData(mime_data, tasks_workspace.Qt.DropAction.MoveAction, first_row, 0, QModelIndex())
        assert reordered is True

        root_row = _find_task_row(model, root.id)
        model.expand_subtasks_tree_by_row(root_row)
        assert model.index(_find_task_row(model, second.id), 0).data(TaskRoles.PlanNumber) == "1."
        assert model.index(_find_task_row(model, first.id), 0).data(TaskRoles.PlanNumber) == "2."

        blocked = model.dropMimeData(mime_data, tasks_workspace.Qt.DropAction.MoveAction, other_row, 0, QModelIndex())
        assert blocked is False
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_plan_reorder_promotes_new_first_item_to_current_and_starts_it(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("tasks_plan_reorder_current_item", ".sqlite3")
    database = Database(path=db_path)
    try:
        root = database.create_task(
            title="Plan root",
            description="",
            day=date(2026, 3, 6),
            time_text="09:00",
            priority="High",
            is_plan_task=True,
        )
        first = database.create_task(
            title="First step",
            description="",
            day=date(2026, 3, 6),
            time_text="09:10",
            priority="Medium",
            parent_id=root.id,
        )
        second = database.create_task(
            title="Second step",
            description="",
            day=date(2026, 3, 6),
            time_text="09:20",
            priority="Medium",
            parent_id=root.id,
        )
        monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)
        model = tasks_workspace.TasksModel()
        model.set_filter_mode("План")

        root_row = _find_task_row(model, root.id)
        assert root_row >= 0
        model.expand_subtasks_tree_by_row(root_row)

        first_row = _find_task_row(model, first.id)
        second_row = _find_task_row(model, second.id)
        assert first_row >= 0 and second_row >= 0
        first_started_at = model.index(first_row, 0).data(TaskRoles.StartedAt)
        assert model.index(first_row, 0).data(TaskRoles.IsCurrentPlanItem) is True
        assert first_started_at
        assert model.index(second_row, 0).data(TaskRoles.StartedAt) == ""

        assert model.reorder_plan_task_before(second.id, first.id) is True

        root_row = _find_task_row(model, root.id)
        assert root_row >= 0
        model.expand_subtasks_tree_by_row(root_row)

        first_row = _find_task_row(model, first.id)
        second_row = _find_task_row(model, second.id)
        assert first_row >= 0 and second_row >= 0
        assert model.index(second_row, 0).data(TaskRoles.IsCurrentPlanItem) is True
        assert model.index(second_row, 0).data(TaskRoles.StartedAt)
        assert model.index(first_row, 0).data(TaskRoles.IsCurrentPlanItem) is False
        assert model.index(first_row, 0).data(TaskRoles.StartedAt) == first_started_at
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_tasks_workspace_quick_create_replaces_ascii_quotes_in_title(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("tasks_quotes_quick_create", ".sqlite3")
    database = Database(path=db_path)
    workspace = None
    try:
        monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)
        workspace = tasks_workspace.TasksWorkspace()
        workspace.new_title.setText('Задача "тест"')
        workspace._quick_quote_filters[0]._normalize_line_edit(workspace.new_title.text())

        assert workspace.new_title.text() == "Задача «тест»"

        workspace._on_create_task()

        created = database.fetch_tasks()
        assert any(task.title == "Задача «тест»" for task in created)
    finally:
        if workspace is not None:
            workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_task_create_dialog_replaces_and_normalizes_ascii_quotes(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("tasks_quotes_dialog", ".sqlite3")
    database = Database(path=db_path)
    dialog = None
    try:
        monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)
        dialog = tasks_workspace.TaskCreateDialog()
        dialog.title_edit.setText('Новая "задача"')
        dialog._quote_filters[0]._normalize_line_edit(dialog.title_edit.text())
        dialog.description_edit.setPlainText('Описание "теста"')
        dialog._quote_filters[1]._normalize_plain_text_edit()

        assert dialog.title_edit.text() == "Новая «задача»"
        assert dialog.description_edit.toPlainText() == "Описание «теста»"

        dialog.title_edit.setText('Вставка "заголовка"')
        dialog.description_edit.setPlainText('Вставка "описания"')

        values = dialog.values()
        assert values["title"] == "Вставка «заголовка»"
        assert values["description"] == "Вставка «описания»"
    finally:
        if dialog is not None:
            dialog.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_normalize_task_text_quotes_uses_russian_guillemets() -> None:
    assert normalize_task_text_quotes('"тест"') == "«тест»"
    assert normalize_task_text_quotes('Он сказал: "да"') == 'Он сказал: «да»'
    assert normalize_task_text_quotes('""') == "«»"


def test_plan_mode_keeps_deferred_plan_root_visible_for_subtask_creation(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("tasks_plan_deferred_root_visible", ".sqlite3")
    database = Database(path=db_path)
    try:
        root = database.create_task(
            title="Deferred plan root",
            description="",
            day=date(2026, 3, 6),
            time_text="09:00",
            priority=DEFERRED_PRIORITY,
            is_plan_task=True,
        )
        monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)
        model = tasks_workspace.TasksModel()
        model.set_filter_mode("План")

        root_row = _find_task_row(model, root.id)
        assert root_row >= 0

        model.quick_add_subtask(root.id)

        created = next(task for task in database.fetch_tasks() if task.parent_id == root.id)
        assert created.priority == "Medium"

        root_row = _find_task_row(model, root.id)
        assert root_row >= 0
        model.expand_subtasks_tree_by_row(root_row)
        child_row = _find_task_row(model, created.id)
        assert child_row >= 0
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_task_edit_dialog_shows_plan_checkbox_and_disables_it_for_plan_items(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("task_edit_dialog_plan_checkbox", ".sqlite3")
    database = Database(path=db_path)
    try:
        root = database.create_task(
            title="Plan root",
            description="",
            day=date(2026, 3, 6),
            time_text="09:00",
            priority="Medium",
            is_plan_task=True,
        )
        child = database.create_task(
            title="Plan child",
            description="",
            day=date(2026, 3, 6),
            time_text="09:10",
            priority="Low",
            parent_id=root.id,
        )
        monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)
        monkeypatch.setattr(task_edit_dialog, "get_database", lambda: database)
        model = tasks_workspace.TasksModel()

        root_dialog = task_edit_dialog.TaskEditDialog(model.task_by_id(root.id))
        child_dialog = task_edit_dialog.TaskEditDialog(model.task_by_id(child.id))
        try:
            assert root_dialog.plan_task_edit.isEnabled() is True
            assert root_dialog.plan_task_edit.isChecked() is True
            assert child_dialog.plan_task_edit.isEnabled() is False
            assert child_dialog.project_edit.isEnabled() is False
            assert child_dialog.project_create_btn.isEnabled() is False
            assert child_dialog.priority_edit.isEnabled() is False
            assert child_dialog.values()["is_plan_task"] is False
        finally:
            root_dialog.deleteLater()
            child_dialog.deleteLater()
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_quick_subtask_under_plan_item_remains_regular_task(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("tasks_plan_item_regular_subtask", ".sqlite3")
    database = Database(path=db_path)
    try:
        root = database.create_task(
            title="Plan root",
            description="",
            day=date(2026, 3, 6),
            time_text="09:00",
            priority="High",
            is_plan_task=True,
        )
        child = database.create_task(
            title="Plan child",
            description="",
            day=date(2026, 3, 6),
            time_text="09:10",
            priority="Low",
            parent_id=root.id,
        )
        monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)
        monkeypatch.setattr(task_edit_dialog, "get_database", lambda: database)
        model = tasks_workspace.TasksModel()
        model.set_filter_mode("План")

        root_row = _find_task_row(model, root.id)
        assert root_row >= 0
        model.expand_subtasks_tree_by_row(root_row)

        model.quick_add_subtask(child.id)

        created = max(
            (task for task in database.fetch_tasks() if task.parent_id == child.id),
            key=lambda task: task.id,
        )
        assert model.is_plan_item(created.id) is False
        assert created.priority == child.priority

        child_row = _find_task_row(model, child.id)
        assert child_row >= 0
        model.expand_subtasks_tree_by_row(child_row)
        created_row = _find_task_row(model, created.id)
        assert created_row >= 0
        assert model.index(created_row, 0).data(TaskRoles.IsPlanItem) is False
        assert model.index(created_row, 0).data(TaskRoles.PlanNumber) == ""

        model.step_priority_by_row(created_row, +1)
        updated = next(task for task in database.fetch_tasks() if task.id == created.id)
        assert updated.priority == "Medium"

        dialog = task_edit_dialog.TaskEditDialog(model.task_by_id(created.id))
        try:
            assert dialog.priority_edit.isEnabled() is True
            assert dialog.project_edit.isEnabled() is True
            assert dialog.plan_task_edit.isEnabled() is True
        finally:
            dialog.deleteLater()
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_plan_items_inherit_parent_project_and_can_change_board_stage(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("tasks_plan_project_inherit_board", ".sqlite3")
    database = Database(path=db_path)
    try:
        project_a = database.create_project(title="Project A", area="Area", updated=date(2026, 3, 6), priority="Medium")
        project_b = database.create_project(title="Project B", area="Area", updated=date(2026, 3, 6), priority="Medium")
        root = database.create_task(
            title="Plan root",
            description="",
            day=date(2026, 3, 6),
            time_text="09:00",
            priority="High",
            project_id=project_a.id,
            is_plan_task=True,
        )
        child = database.create_task(
            title="Plan child",
            description="",
            day=date(2026, 3, 6),
            time_text="09:10",
            priority="Medium",
            parent_id=root.id,
        )
        monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)
        model = tasks_workspace.TasksModel()
        model.set_filter_mode("План")

        root_row = _find_task_row(model, root.id)
        assert root_row >= 0
        model.expand_subtasks_tree_by_row(root_row)

        model.update_task_by_row(
            root_row,
            title=root.title,
            description=root.description,
            day=root.day,
            time_text=root.time_text,
            priority=root.priority,
            done=root.done,
            project_id=project_b.id,
            recurrence_kind=root.recurrence_kind,
            recurrence_interval=root.recurrence_interval,
            is_plan_task=True,
            marker_color=root.marker_color,
            marker_theme=root.marker_theme,
        )

        root_row = _find_task_row(model, root.id)
        model.expand_subtasks_tree_by_row(root_row)
        child_row = _find_task_row(model, child.id)
        assert child_row >= 0
        assert model.index(child_row, 0).data(TaskRoles.ProjectTitle) == "Project B"

        child_task = next(task for task in database.fetch_tasks() if task.id == child.id)
        model.update_task_by_row(
            child_row,
            title=child_task.title,
            description=child_task.description,
            day=child_task.day,
            time_text=child_task.time_text,
            priority=child_task.priority,
            done=child_task.done,
            project_id=project_a.id,
            recurrence_kind=child_task.recurrence_kind,
            recurrence_interval=child_task.recurrence_interval,
            marker_color=child_task.marker_color,
            marker_theme=child_task.marker_theme,
        )
        child_task = next(task for task in database.fetch_tasks() if task.id == child.id)
        assert child_task.project_id == project_b.id

        model.step_board_column_by_row(child_row, +1)
        child_task = next(task for task in database.fetch_tasks() if task.id == child.id)
        assert child_task.board_column == BOARD_COLUMN_IN_PROGRESS
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_plan_item_stage_only_controls_center_stage_text() -> None:
    chip_rect = QRect(0, 0, 220, 30)
    controls = tasks_workspace.TasksItemDelegate._priority_control_rects(chip_rect, stage_only=True)
    assert controls["icon"].isNull()
    assert controls["priority_arrows"].isNull()
    assert controls["priority_up"].isNull()
    assert controls["priority_down"].isNull()
    assert abs(controls["value"].center().x() - chip_rect.center().x()) <= 12


def test_tasks_delegate_plan_time_up_arrow_reorders_sibling(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("tasks_plan_arrow_click", ".sqlite3")
    database = Database(path=db_path)
    try:
        root = database.create_task(
            title="Plan root",
            description="",
            day=date(2026, 3, 6),
            time_text="09:00",
            priority="High",
            is_plan_task=True,
        )
        first = database.create_task(
            title="First step",
            description="",
            day=date(2026, 3, 6),
            time_text="09:10",
            priority="Medium",
            parent_id=root.id,
        )
        second = database.create_task(
            title="Second step",
            description="",
            day=date(2026, 3, 6),
            time_text="09:20",
            priority="Medium",
            parent_id=root.id,
        )
        monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)
        model = tasks_workspace.TasksModel()
        model.set_filter_mode("РџР»Р°РЅ")
        delegate = tasks_workspace.TasksItemDelegate()

        root_row = _find_task_row(model, root.id)
        assert root_row >= 0
        model.expand_subtasks_tree_by_row(root_row)

        second_row = _find_task_row(model, second.id)
        assert second_row >= 0
        index = model.index(second_row, 0)
        option = QStyleOptionViewItem()
        option.rect = QRect(0, 0, 1200, delegate.ROW_H)
        layout = delegate.row_layout(
            option.rect,
            depth=int(index.data(TaskRoles.SubtaskDepth) or 0),
            has_subtasks=bool(index.data(TaskRoles.HasSubtasks)),
        )
        controls = delegate._time_control_rects(layout["date"], show_plan_controls=True)
        click_point = controls["plan_up"].center()
        event = QMouseEvent(
            QEvent.Type.MouseButtonRelease,
            QPointF(float(click_point.x()), float(click_point.y())),
            QPointF(float(click_point.x()), float(click_point.y())),
            QPointF(float(click_point.x()), float(click_point.y())),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )

        assert delegate.editorEvent(event, model, option, index) is True

        root_row = _find_task_row(model, root.id)
        model.expand_subtasks_tree_by_row(root_row)
        assert model.index(_find_task_row(model, second.id), 0).data(TaskRoles.PlanNumber) == "1."
        assert model.index(_find_task_row(model, first.id), 0).data(TaskRoles.PlanNumber) == "2."
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_tasks_delegate_does_not_mark_deferred_tasks_overdue() -> None:
    assert tasks_workspace.TasksItemDelegate._is_overdue(
        date(2026, 3, 5),
        False,
        priority=DEFERRED_PRIORITY,
    ) is False
    assert tasks_workspace.TasksItemDelegate._is_overdue(
        date(2026, 3, 5),
        False,
        priority="Medium",
    ) is True


def test_tasks_delegate_formats_plan_execution_text_for_current_item() -> None:
    now_dt = datetime(2026, 3, 6, 10, 5, tzinfo=timezone.utc)
    started_at = datetime(2026, 3, 6, 9, 0, tzinfo=timezone.utc).isoformat(timespec="seconds")

    text = tasks_workspace.TasksItemDelegate._format_plan_execution_text(
        is_plan_item=True,
        is_current_plan_item=True,
        done=False,
        started_at=started_at,
        finished_at="",
        actual_minutes=0,
        now_dt=now_dt,
    )

    assert text == "В работе: 1ч 05м"


def test_tasks_delegate_formats_plan_execution_text_for_completed_item() -> None:
    text = tasks_workspace.TasksItemDelegate._format_plan_execution_text(
        is_plan_item=True,
        is_current_plan_item=False,
        done=True,
        started_at="2026-03-06T09:00:00+00:00",
        finished_at="2026-03-06T10:40:00+00:00",
        actual_minutes=100,
        now_dt=datetime(2026, 3, 6, 12, 0, tzinfo=timezone.utc),
    )

    assert text == "Факт: 1ч 40м"
