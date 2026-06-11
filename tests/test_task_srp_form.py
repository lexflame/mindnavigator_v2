from __future__ import annotations

from datetime import date

from PySide6.QtCore import QEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QWidget

from mindnavigator.storage import BOARD_COLUMN_IN_PROGRESS, BOARD_COLUMN_QUEUE, Database
from mindnavigator.workspaces import tasks as tasks_workspace
from mindnavigator.workspaces.tasks import task_details_dialog


def _task(database: Database, task_id: int):
    return next(item for item in database.fetch_tasks() if item.id == task_id)


def test_task_details_dialog_autosaves_stage_selection(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("task_details_stage_autosave", ".sqlite3")
    database = Database(path=db_path)
    dialog = None
    host = None
    try:
        task = database.create_task(
            title="Stage autosave",
            description="",
            day=date(2026, 3, 6),
            time_text="",
            priority="Medium",
        )
        monkeypatch.setattr(tasks_workspace, "get_database", lambda: database)
        monkeypatch.setattr(task_details_dialog, "get_database", lambda: database)
        model = tasks_workspace.TasksModel()

        class _Host(QWidget):
            def model(self):
                return model

        host = _Host()
        dialog = task_details_dialog.TaskDetailsDialog(model.task_by_id(task.id), parent=host)
        dialog.start_editing()
        stage_index = dialog.stage_inline.editor.findData(BOARD_COLUMN_IN_PROGRESS)

        dialog.stage_inline.editor.setCurrentIndex(stage_index)
        dialog.stage_inline.editor.activated.emit(stage_index)
        QApplication.processEvents()

        assert _task(database, task.id).board_column == BOARD_COLUMN_IN_PROGRESS
        assert dialog.stage_inline.currentIndex() == 1
    finally:
        if dialog is not None:
            dialog.deleteLater()
        if host is not None:
            host.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_task_details_dialog_autosaves_title_on_focus_loss(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("task_details_focus_autosave", ".sqlite3")
    database = Database(path=db_path)
    dialog = None
    try:
        task = database.create_task(
            title="Before focus loss",
            description="",
            day=date(2026, 3, 6),
            time_text="",
            priority="Medium",
        )
        monkeypatch.setattr(task_details_dialog, "get_database", lambda: database)
        dialog = task_details_dialog.TaskDetailsDialog(_task(database, task.id))
        dialog.show()
        dialog.start_editing()
        dialog.title_inline.editor.setFocus()
        dialog.title_inline.editor.setText("After focus loss")

        dialog.title_inline.editor.clearFocus()
        QApplication.sendEvent(dialog.title_inline.editor, QEvent(QEvent.Type.FocusOut))
        QTest.qWait(1)
        QApplication.processEvents()

        assert _task(database, task.id).title == "After focus loss"
    finally:
        if dialog is not None:
            dialog.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_task_details_dialog_autosaves_description_on_focus_loss(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("task_details_description_autosave", ".sqlite3")
    database = Database(path=db_path)
    dialog = None
    try:
        task = database.create_task(
            title="Description autosave",
            description="Before",
            day=date(2026, 3, 6),
            time_text="",
            priority="Medium",
        )
        monkeypatch.setattr(task_details_dialog, "get_database", lambda: database)
        dialog = task_details_dialog.TaskDetailsDialog(_task(database, task.id))
        dialog.show()
        dialog.start_editing()
        assert dialog.description_editor is not None
        dialog.description_editor.setPlainText("After description focus loss")

        dialog.description_editor.clearFocus()
        QApplication.sendEvent(dialog.description_editor, QEvent(QEvent.Type.FocusOut))
        QTest.qWait(1)
        QApplication.processEvents()

        assert _task(database, task.id).description == "After description focus loss"
        assert dialog.description_editor is not None
    finally:
        if dialog is not None:
            dialog.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_task_details_dialog_autosaves_checkbox_and_footer_status(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("task_details_choice_autosave", ".sqlite3")
    database = Database(path=db_path)
    dialog = None
    try:
        task = database.create_task(
            title="Choice autosave",
            description="",
            day=date(2026, 3, 6),
            time_text="",
            priority="Medium",
        )
        monkeypatch.setattr(task_details_dialog, "get_database", lambda: database)
        dialog = task_details_dialog.TaskDetailsDialog(_task(database, task.id))
        dialog.show()
        dialog.start_editing()

        dialog.plan_task_checkbox.setFocus()
        dialog.plan_task_checkbox.click()
        QApplication.processEvents()
        assert _task(database, task.id).is_plan_task is True

        done_index = dialog.footer_status_combo.findData(True)
        dialog.footer_status_combo.setCurrentIndex(done_index)
        dialog.footer_status_combo.activated.emit(done_index)
        QApplication.processEvents()
        assert _task(database, task.id).done is True
    finally:
        if dialog is not None:
            dialog.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_create_task_persists_initial_board_column(unique_temp_path) -> None:
    db_path = unique_temp_path("task_create_board_column", ".sqlite3")
    database = Database(path=db_path)
    try:
        task = database.create_task(
            title="Created in progress",
            description="",
            day=date(2026, 3, 6),
            time_text="",
            priority="Medium",
            board_column=BOARD_COLUMN_IN_PROGRESS,
        )

        assert _task(database, task.id).board_column == BOARD_COLUMN_IN_PROGRESS
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_task_create_dialog_keeps_stage_selection_local(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("task_create_stage_local", ".sqlite3")
    database = Database(path=db_path)
    dialog = None
    try:
        monkeypatch.setattr(task_details_dialog, "get_database", lambda: database)
        task_ids_before = {task.id for task in database.fetch_tasks()}
        dialog = tasks_workspace.TaskCreateDialog(board_column=BOARD_COLUMN_QUEUE)
        stage_index = dialog.stage_inline.editor.findData(BOARD_COLUMN_IN_PROGRESS)

        dialog.stage_inline.editor.setCurrentIndex(stage_index)
        dialog.stage_inline.editor.activated.emit(stage_index)
        QApplication.processEvents()

        assert dialog._task.id == 0
        assert dialog._task.board_column == BOARD_COLUMN_IN_PROGRESS
        assert dialog.values()["board_column"] == BOARD_COLUMN_IN_PROGRESS
        assert {task.id for task in database.fetch_tasks()} == task_ids_before
    finally:
        if dialog is not None:
            dialog.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)
