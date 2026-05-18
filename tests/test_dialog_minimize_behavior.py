from __future__ import annotations

from PySide6.QtCore import QPoint, QPointF, Qt, QEvent, QTimer, QAbstractListModel
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication, QDialog, QMainWindow, QVBoxLayout, QWidget

from mindnavigator.ui import modals
from mindnavigator.ui.dialogs import frameless_patch
from mindnavigator.ui.dialogs.frameless_patch import (
    _TaskDialogOutsideClickMinimizer,
    _fit_minimizable_task_dialog_size,
    _try_minimize_task_dialog,
    prepare_minimizable_task_dialog_for_show,
)
from mindnavigator.ui.titlebar import TitleBar
from mindnavigator.window.collections.main_window import MainWindow
from mindnavigator.workspaces.tasks import tasks_item_delegate
from mindnavigator.workspaces.tasks import task_details_dialog
from mindnavigator.workspaces.tasks import task_edit_dialog
from mindnavigator.workspaces.tasks.tasks_model import TasksModel
from mindnavigator.workspaces.tasks.task_row import TaskRow


class _ImmediateAnimator:
    def __init__(self) -> None:
        self.calls = []

    def play(self, dialog: QWidget, *, on_finished=None):
        self.calls.append(dialog)
        if callable(on_finished):
            on_finished()
        return self

    def stop(self) -> None:
        return None


class _ProbeDialog(QDialog):
    def __init__(self) -> None:
        super().__init__()
        self.hide_calls = 0
        self.show_calls = 0
        self.enabled_states: list[bool] = []

    def hide(self) -> None:
        self.hide_calls += 1
        super().hide()

    def show(self) -> None:
        self.show_calls += 1
        super().show()

    def setEnabled(self, enabled: bool) -> None:
        self.enabled_states.append(bool(enabled))
        super().setEnabled(enabled)


class _MinimizeWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.calls = []

    def minimize_task_dialog(self, dialog: QWidget, task_id: int, is_edit_dialog: bool) -> None:
        self.calls.append((dialog, task_id, is_edit_dialog))


class _TaskDialogDb:
    def get_setting(self, *_args, **_kwargs):
        return ""

    def set_setting(self, *_args, **_kwargs) -> None:
        return None

    def fetch_projects(self):
        return []

    def fetch_notes(self):
        return []

    def fetch_tasks(self):
        return [
            TaskRow(
                id=91,
                day=__import__("datetime").date(2026, 3, 6),
                time_text="09:00",
                title="Task",
                description="",
                priority="Medium",
                done=False,
            )
        ]

    def fetch_ideas(self, **_kwargs):
        return []

    def fetch_objects(self):
        return []

    def fetch_maps(self):
        return []

    def fetch_map_markers(self):
        return []

    def fetch_cloud_files(self):
        return []

    def fetch_task_attachments(self, *_args, **_kwargs):
        return []


def test_titlebar_centers_minimized_task_host_and_shows_task_id() -> None:
    _app = QApplication.instance() or QApplication([])
    window = QMainWindow()
    window.resize(1400, 900)
    central = QWidget(window)
    central_layout = QVBoxLayout(central)
    central_layout.setContentsMargins(0, 0, 0, 0)
    titlebar = TitleBar(window)
    central_layout.addWidget(titlebar)
    window.setCentralWidget(central)
    window.show()
    QApplication.processEvents()
    try:
        titlebar.register_minimized_task_dialog(QWidget(), 42, True, lambda: None)
        QApplication.processEvents()

        host_center = titlebar.minimized_host.geometry().center().x()
        titlebar_center = titlebar.rect().center().x()
        assert abs(host_center - titlebar_center) <= 2
        chips = list(titlebar._minimized_buttons.values())
        assert len(chips) == 1
        assert chips[0].text() == "MN-42"
    finally:
        titlebar.deleteLater()
        window.deleteLater()


def test_titlebar_minimized_scroll_viewport_is_configured_transparent() -> None:
    _app = QApplication.instance() or QApplication([])
    window = QMainWindow()
    titlebar = TitleBar(window)
    try:
        assert titlebar.minimized_scroll.viewport().objectName() == "MinimizedDialogsViewport"
        assert titlebar.minimized_scroll.autoFillBackground() is False
        assert titlebar.minimized_scroll.viewport().autoFillBackground() is False
        assert titlebar.minimized_strip.autoFillBackground() is False
    finally:
        titlebar.deleteLater()
        window.deleteLater()


def test_main_window_minimize_task_dialog_animates_down_and_registers_chip() -> None:
    _app = QApplication.instance() or QApplication([])
    dialog = _ProbeDialog()
    titlebar = TitleBar(QMainWindow())
    animator = _ImmediateAnimator()

    class _DummyWindow:
        def __init__(self) -> None:
            self._minimized_task_dialogs = {}
            self._minimized_task_dialog_animations = {}
            self._dialog_minimize_animator = animator
            self.title_bar = titlebar

        def _restore_minimized_task_dialog(self, current_dialog: QWidget) -> None:
            MainWindow._restore_minimized_task_dialog(self, current_dialog)

        def _finalize_task_dialog_minimize_animation(self, current_dialog: QWidget) -> None:
            MainWindow._finalize_task_dialog_minimize_animation(self, current_dialog)

        def _forget_minimized_task_dialog(self, current_dialog: QWidget) -> None:
            MainWindow._forget_minimized_task_dialog(self, current_dialog)

    dummy = _DummyWindow()
    try:
        MainWindow.minimize_task_dialog(dummy, dialog, 17, True)

        assert animator.calls == [dialog]
        assert dialog.hide_calls == 1
        assert dialog.enabled_states[:2] == [False, True]
        chips = list(titlebar._minimized_buttons.values())
        assert len(chips) == 1
        assert chips[0].text() == "MN-17"
        assert id(dialog) in dummy._minimized_task_dialogs
    finally:
        dialog.deleteLater()
        titlebar.deleteLater()
        titlebar.parentWidget().deleteLater()


def test_try_minimize_task_dialog_invokes_window_minimizer() -> None:
    _app = QApplication.instance() or QApplication([])
    window = _MinimizeWindow()
    dialog = QDialog(window)
    dialog.setProperty("task_dialog_id", 51)
    dialog.setProperty("task_dialog_kind", "edit")
    dialog.show()
    QApplication.processEvents()
    try:
        minimized = _try_minimize_task_dialog(dialog)
        assert minimized is True
        assert window.calls == [(dialog, 51, True)]
    finally:
        dialog.deleteLater()
        window.deleteLater()


def test_task_dialog_outside_click_minimizer_reacts_to_click_outside_dialog() -> None:
    _app = QApplication.instance() or QApplication([])
    window = _MinimizeWindow()
    central = QWidget(window)
    central.setGeometry(0, 0, 800, 600)
    window.setCentralWidget(central)
    window.resize(800, 600)
    window.show()
    dialog = QDialog(window)
    dialog.setProperty("task_dialog_id", 73)
    dialog.setProperty("task_dialog_kind", "edit")
    dialog.setGeometry(200, 150, 260, 180)
    dialog.show()
    QApplication.processEvents()
    minimizer = _TaskDialogOutsideClickMinimizer(dialog)
    minimizer.enable()
    try:
        event = QMouseEvent(
            QEvent.Type.MouseButtonPress,
            QPointF(20, 20),
            QPointF(20, 20),
            QPointF(20, 20),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        minimizer.eventFilter(central, event)
        assert window.calls == [(dialog, 73, True)]
    finally:
        dialog.deleteLater()
        window.deleteLater()


def test_task_dialog_outside_click_minimizer_reacts_to_focus_leaving_dialog(monkeypatch) -> None:
    _app = QApplication.instance() or QApplication([])
    window = _MinimizeWindow()
    central = QWidget(window)
    window.setCentralWidget(central)
    window.show()
    dialog = QDialog(window)
    dialog.setProperty("task_dialog_id", 88)
    dialog.setProperty("task_dialog_kind", "edit")
    dialog.show()
    QApplication.processEvents()
    minimizer = _TaskDialogOutsideClickMinimizer(dialog)
    minimizer.enable()
    monkeypatch.setattr(QApplication, "activeWindow", staticmethod(lambda: window))
    monkeypatch.setattr(QApplication, "focusWidget", staticmethod(lambda: central))
    monkeypatch.setattr(QApplication, "activePopupWidget", staticmethod(lambda: None))
    monkeypatch.setattr(QApplication, "activeModalWidget", staticmethod(lambda: None))
    try:
        minimizer._minimize_if_detached()
        assert window.calls == [(dialog, 88, True)]
    finally:
        dialog.deleteLater()
        window.deleteLater()


def test_minimizable_task_dialog_is_clamped_to_parent_window_size() -> None:
    _app = QApplication.instance() or QApplication([])
    window = QMainWindow()
    window.setGeometry(50, 50, 1100, 700)
    dialog = QDialog(window)
    dialog.setProperty("task_dialog_minimizable", True)
    dialog.setMinimumSize(460, 420)
    dialog.resize(1450, 812)
    try:
        _fit_minimizable_task_dialog_size(dialog, window)
        assert dialog.width() == 980
        assert dialog.height() == 604
    finally:
        dialog.deleteLater()
        window.deleteLater()


def test_task_edit_dialog_is_clamped_to_compact_max_size() -> None:
    _app = QApplication.instance() or QApplication([])
    window = QMainWindow()
    window.setGeometry(50, 50, 1800, 1000)
    dialog = QDialog(window)
    dialog.setProperty("task_dialog_minimizable", True)
    dialog.setProperty("task_dialog_kind", "edit")
    dialog.setMinimumSize(460, 420)
    dialog.resize(1450, 812)
    try:
        _fit_minimizable_task_dialog_size(dialog, window)
        assert dialog.width() == 1040
        assert dialog.height() == 760
    finally:
        dialog.deleteLater()
        window.deleteLater()


def test_prepare_minimizable_task_dialog_for_show_forces_non_modal_state() -> None:
    _app = QApplication.instance() or QApplication([])
    window = QMainWindow()
    dialog = QDialog(window)
    dialog.setProperty("task_dialog_minimizable", True)
    dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
    try:
        prepare_minimizable_task_dialog_for_show(dialog, window, center=False)
        assert dialog.windowModality() == Qt.WindowModality.NonModal
    finally:
        dialog.deleteLater()
        window.deleteLater()


def test_task_edit_dialog_minimizes_itself_after_deactivate(monkeypatch) -> None:
    _app = QApplication.instance() or QApplication([])
    window = _MinimizeWindow()
    central = QWidget(window)
    window.setCentralWidget(central)
    window.show()
    monkeypatch.setattr(task_edit_dialog, "get_database", lambda: _TaskDialogDb())
    dialog = task_edit_dialog.TaskEditDialog(
        TaskRow(
            id=91,
            day=__import__("datetime").date(2026, 3, 6),
            time_text="09:00",
            title="Edit task",
            description="",
            priority="Medium",
            done=False,
        ),
        parent=window,
    )
    dialog.show()
    QApplication.processEvents()
    monkeypatch.setattr(QApplication, "activeWindow", staticmethod(lambda: window))
    monkeypatch.setattr(QApplication, "focusWidget", staticmethod(lambda: central))
    monkeypatch.setattr(QApplication, "activePopupWidget", staticmethod(lambda: None))
    monkeypatch.setattr(QApplication, "activeModalWidget", staticmethod(lambda: None))
    try:
        dialog._maybe_auto_minimize_on_deactivate()
        assert window.calls == [(dialog, 91, True)]
    finally:
        dialog.deleteLater()
        window.deleteLater()


def test_task_edit_dialog_show_event_prepares_minimizable_geometry(monkeypatch) -> None:
    _app = QApplication.instance() or QApplication([])
    window = _MinimizeWindow()
    window.setGeometry(50, 50, 1100, 700)
    monkeypatch.setattr(task_edit_dialog, "get_database", lambda: _TaskDialogDb())
    calls: list[tuple[QDialog, QWidget | None, bool]] = []
    overlay_calls: list[QDialog] = []

    def _fake_prepare(current_dialog: QDialog, current_parent: QWidget | None = None, *, center: bool = True) -> None:
        calls.append((current_dialog, current_parent, center))

    def _fake_ensure_overlay(current_dialog: QDialog) -> None:
        overlay_calls.append(current_dialog)

    monkeypatch.setattr(task_edit_dialog, "prepare_minimizable_task_dialog_for_show", _fake_prepare)
    monkeypatch.setattr(task_edit_dialog, "ensure_minimizable_task_dialog_overlay", _fake_ensure_overlay)
    dialog = task_edit_dialog.TaskEditDialog(
        TaskRow(
            id=96,
            day=__import__("datetime").date(2026, 3, 6),
            time_text="09:00",
            title="Edit task",
            description="",
            priority="Medium",
            done=False,
        ),
        parent=window,
    )
    try:
        dialog.show()
        QApplication.processEvents()
        assert calls
        assert calls[-1] == (dialog, window, True)
        assert overlay_calls == [dialog]
    finally:
        dialog.deleteLater()
        window.deleteLater()


def test_task_edit_dialog_exec_routes_through_minimizable_runner(monkeypatch) -> None:
    _app = QApplication.instance() or QApplication([])
    window = _MinimizeWindow()
    monkeypatch.setattr(task_edit_dialog, "get_database", lambda: _TaskDialogDb())
    calls: list[tuple[QDialog, QWidget | None]] = []

    def _fake_show_minimizable_task_dialog(current_dialog: QDialog, current_parent: QWidget | None = None) -> int:
        calls.append((current_dialog, current_parent))
        return 5

    monkeypatch.setattr(task_edit_dialog, "show_minimizable_task_dialog", _fake_show_minimizable_task_dialog)
    dialog = task_edit_dialog.TaskEditDialog(
        TaskRow(
            id=97,
            day=__import__("datetime").date(2026, 3, 6),
            time_text="09:00",
            title="Edit task",
            description="",
            priority="Medium",
            done=False,
        ),
        parent=window,
    )
    try:
        result = dialog.exec()
        assert result == 5
        assert calls == [(dialog, window)]
    finally:
        dialog.deleteLater()
        window.deleteLater()


def test_task_details_dialog_uses_larger_non_minimizable_geometry(monkeypatch) -> None:
    _app = QApplication.instance() or QApplication([])
    window = _MinimizeWindow()
    monkeypatch.setattr(task_details_dialog, "get_database", lambda: _TaskDialogDb())
    dialog = task_details_dialog.TaskDetailsDialog(
        TaskRow(
            id=91,
            day=__import__("datetime").date(2026, 3, 6),
            time_text="09:00",
            title="Details task",
            description="",
            priority="Medium",
            done=False,
        ),
        parent=window,
    )
    try:
        dialog.show()
        QApplication.processEvents()
        assert dialog.property("task_dialog_minimizable") is False
        assert dialog.minimumWidth() == 1100
        assert dialog.minimumHeight() == 700
        assert dialog.width() == 1260
        assert dialog.height() == 840
        assert dialog._columns_for_width(1200, dialog._PARAM_BREAKPOINTS, default=4) == 4
        assert dialog._columns_for_width(1300, dialog._DETAIL_BREAKPOINTS, default=6) == 6
    finally:
        dialog.deleteLater()
        window.deleteLater()

def test_task_details_dialog_is_not_routed_through_minimizable_runner(monkeypatch) -> None:
    _app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(task_details_dialog, "get_database", lambda: _TaskDialogDb())
    dialog = task_details_dialog.TaskDetailsDialog(
        TaskRow(
            id=92,
            day=__import__("datetime").date(2026, 3, 6),
            time_text="09:00",
            title="Details task",
            description="",
            priority="Medium",
            done=False,
        )
    )
    try:
        assert dialog.property("task_dialog_minimizable") is False
        assert not hasattr(dialog, "_schedule_auto_minimize_on_deactivate")
    finally:
        dialog.deleteLater()


def test_restore_minimizable_task_dialog_raises_dialog_after_overlay(monkeypatch) -> None:
    _app = QApplication.instance() or QApplication([])
    calls: list[str] = []

    class _RestoreProbeDialog(QDialog):
        def show(self) -> None:
            calls.append("show")
            super().show()

        def raise_(self) -> None:
            calls.append("raise")
            super().raise_()

        def activateWindow(self) -> None:
            calls.append("activate")
            super().activateWindow()

    dialog = _RestoreProbeDialog()
    dialog.setProperty("task_dialog_minimizable", True)
    dialog.setProperty("task_dialog_id", 303)
    monkeypatch.setattr(
        frameless_patch,
        "ensure_minimizable_task_dialog_overlay",
        lambda current_dialog: calls.append(f"overlay:{int(current_dialog.property('task_dialog_id') or 0)}"),
    )
    try:
        frameless_patch.restore_minimizable_task_dialog(dialog)
        assert calls == ["show", "overlay:303", "raise", "activate"]
    finally:
        dialog.deleteLater()


def test_show_minimizable_task_dialog_keeps_waiting_after_minimize_and_restore(monkeypatch) -> None:
    _app = QApplication.instance() or QApplication([])

    class _RestoreWindow(_MinimizeWindow):
        def minimize_task_dialog(self, dialog: QWidget, task_id: int, is_edit_dialog: bool) -> None:
            self.calls.append((dialog, task_id, is_edit_dialog))
            dialog.hide()
            QTimer.singleShot(0, lambda current_dialog=dialog: frameless_patch.restore_minimizable_task_dialog(current_dialog))
            QTimer.singleShot(0, dialog.accept)

    window = _RestoreWindow()
    window.show()
    monkeypatch.setattr(task_edit_dialog, "get_database", lambda: _TaskDialogDb())
    dialog = task_edit_dialog.TaskEditDialog(
        TaskRow(
            id=411,
            day=__import__("datetime").date(2026, 3, 6),
            time_text="09:00",
            title="Edit task",
            description="",
            priority="Medium",
            done=False,
        ),
        parent=window,
    )
    try:
        QTimer.singleShot(0, lambda: window.minimize_task_dialog(dialog, 411, True))
        result = frameless_patch._run_minimizable_task_dialog(dialog)
        assert result == int(QDialog.DialogCode.Accepted)
        assert window.calls == [(dialog, 411, True)]
    finally:
        dialog.deleteLater()
        window.deleteLater()


def test_tasks_delegate_applies_late_accept_after_exec_returns_rejected(monkeypatch) -> None:
    _app = QApplication.instance() or QApplication([])

    class _DeferredModel(TasksModel):
        def __init__(self) -> None:
            QAbstractListModel.__init__(self)
            self.updated: list[tuple[int, dict[str, object]]] = []
            self._task = TaskRow(
                id=322,
                day=__import__("datetime").date(2026, 3, 17),
                time_text="",
                title="Original title",
                description="",
                priority="High",
                done=False,
            )

        def task_at_row(self, row_idx: int):
            return self._task if row_idx == 2 else None

        def row_for_task_id(self, task_id: int) -> int:
            return 2 if task_id == self._task.id else -1

        def update_task_by_row(self, row_idx: int, **kwargs) -> None:
            self.updated.append((row_idx, kwargs))

    class _DeferredDialog(QDialog):
        def __init__(self, task, parent=None) -> None:
            super().__init__(parent)
            self.setProperty("task_dialog_id", int(task.id))
            self._values = {
                "title": "Updated title",
                "description": "",
                "day": __import__("datetime").date(2026, 3, 17),
                "time_text": "",
                "priority": "High",
                "done": False,
                "project_id": None,
                "recurrence_kind": "",
                "recurrence_interval": 1,
                "marker_color": "",
                "marker_theme": "",
            }

        def values(self):
            return dict(self._values)

    class _FakeIndex:
        def row(self) -> int:
            return 2

        def model(self):
            return object()

    def _fake_exec_with_overlay(dialog: QDialog, _parent: QWidget | None) -> int:
        QTimer.singleShot(0, dialog.accept)
        return int(QDialog.DialogCode.Rejected)

    monkeypatch.setattr(tasks_item_delegate, "TaskEditDialog", _DeferredDialog)
    monkeypatch.setattr(tasks_item_delegate, "exec_with_overlay", _fake_exec_with_overlay)
    model = _DeferredModel()
    view = QWidget()
    delegate = tasks_item_delegate.TasksItemDelegate(view)
    monkeypatch.setattr(delegate, "_tasks_model", lambda _model: model)
    try:
        delegate._edit_task(_FakeIndex())
        QApplication.processEvents()
        assert len(model.updated) == 1
        row_idx, payload = model.updated[0]
        assert row_idx == 2
        assert payload["title"] == "Updated title"
    finally:
        delegate.deleteLater()
        view.deleteLater()


def test_main_window_app_click_fallback_minimizes_visible_task_dialog(monkeypatch) -> None:
    _app = QApplication.instance() or QApplication([])
    dialog = QDialog()
    dialog.setProperty("task_dialog_minimizable", True)
    dialog.setProperty("task_dialog_id", 101)
    dialog.setProperty("task_dialog_kind", "edit")
    dialog.setGeometry(200, 200, 260, 180)

    class _ClickWindow:
        def __init__(self) -> None:
            self.calls = []

        def _iter_visible_task_dialogs(self):
            return [dialog]

        def _widget_belongs_to_dialog(self, widget: QWidget, current_dialog: QDialog) -> bool:
            return MainWindow._widget_belongs_to_dialog(widget, current_dialog)

        def minimize_task_dialog(self, current_dialog: QWidget, task_id: int, is_edit_dialog: bool) -> None:
            self.calls.append((current_dialog, task_id, is_edit_dialog))

    window = _ClickWindow()
    outside_widget = QWidget()
    monkeypatch.setattr(QApplication, "activePopupWidget", staticmethod(lambda: None))
    monkeypatch.setattr(QApplication, "widgetAt", staticmethod(lambda _pos: outside_widget))
    try:
        minimized = MainWindow._maybe_minimize_task_dialog_from_app_click(window, dialog.frameGeometry().topLeft() - QPoint(20, 20))
        assert minimized is True
        assert window.calls == [(dialog, 101, True)]
    finally:
        dialog.deleteLater()
        outside_widget.deleteLater()


def test_main_window_minimizes_top_task_dialog_when_app_becomes_inactive() -> None:
    dialog = QDialog()
    dialog.setProperty("task_dialog_minimizable", True)
    dialog.setProperty("task_dialog_id", 131)
    dialog.setProperty("task_dialog_kind", "edit")

    class _StateWindow:
        def __init__(self) -> None:
            self.calls = []

        def _iter_visible_task_dialogs(self):
            return [dialog]

        def _minimize_top_visible_task_dialog(self):
            return MainWindow._minimize_top_visible_task_dialog(self)

        def minimize_task_dialog(self, current_dialog: QWidget, task_id: int, is_edit_dialog: bool) -> None:
            self.calls.append((current_dialog, task_id, is_edit_dialog))

    window = _StateWindow()
    try:
        MainWindow._on_application_state_changed(window, Qt.ApplicationState.ApplicationInactive)
        assert window.calls == [(dialog, 131, True)]
    finally:
        dialog.deleteLater()


def test_show_dialog_standard_routes_minimizable_task_dialog_through_custom_runner(monkeypatch) -> None:
    class _SentinelDialog(QDialog):
        def exec(self) -> int:  # noqa: A003 - Qt API name
            raise AssertionError("custom minimizable runner should bypass direct dialog.exec()")

    dialog = _SentinelDialog()
    dialog.setProperty("task_dialog_minimizable", True)
    dialog.setProperty("task_dialog_id", 211)
    calls: list[tuple[QDialog, QWidget | None]] = []
    parent = QWidget()

    def _fake_show_minimizable_task_dialog(current_dialog: QDialog, current_parent: QWidget | None) -> int:
        calls.append((current_dialog, current_parent))
        return 7

    monkeypatch.setattr(
        "mindnavigator.ui.dialogs.frameless_patch.show_minimizable_task_dialog",
        _fake_show_minimizable_task_dialog,
    )
    try:
        result = modals.show_dialog_standard(dialog, parent)
        assert result == 7
        assert calls == [(dialog, parent)]
    finally:
        dialog.deleteLater()
        parent.deleteLater()
