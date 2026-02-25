from __future__ import annotations

import mindnavigator.main_window as main_window
from mindnavigator.main_window import MainWindow


class _DummyTasksPage:
    def __init__(self) -> None:
        self.focused: list[int] = []

    def focus_task(self, task_id: int) -> bool:
        self.focused.append(task_id)
        return True


class _DummyWindow:
    MODE_TASKS = MainWindow.MODE_TASKS

    def __init__(self) -> None:
        self.calls: list[object] = []
        self._tray_message_task_id: int | None = None
        self.page_tasks = _DummyTasksPage()

    def _restore_from_tray(self) -> None:
        self.calls.append("restore")

    def _open_task_from_tray_notification(self, task_id: int) -> None:
        self.calls.append(("open", task_id))

    def set_mode(self, mode_name: str) -> None:
        self.calls.append(("mode", mode_name))


def test_on_tray_message_clicked_opens_task_when_task_id_is_bound() -> None:
    window = _DummyWindow()
    window._tray_message_task_id = 42

    MainWindow._on_tray_message_clicked(window)

    assert window.calls == ["restore", ("open", 42)]
    assert window._tray_message_task_id is None


def test_on_tray_message_clicked_only_restores_when_no_task_bound() -> None:
    window = _DummyWindow()

    MainWindow._on_tray_message_clicked(window)

    assert window.calls == ["restore"]
    assert window._tray_message_task_id is None


def test_open_task_from_tray_notification_switches_mode_and_focuses_task(monkeypatch) -> None:
    window = _DummyWindow()

    monkeypatch.setattr(main_window.QTimer, "singleShot", lambda _ms, callback: callback())

    MainWindow._open_task_from_tray_notification(window, 17)

    assert window.calls == [("mode", MainWindow.MODE_TASKS)]
    assert window.page_tasks.focused == [17]


def test_open_task_from_tray_notification_skips_focus_when_method_missing() -> None:
    class _NoFocusWindow:
        MODE_TASKS = MainWindow.MODE_TASKS

        def __init__(self) -> None:
            self.calls: list[object] = []
            self.page_tasks = object()

        def set_mode(self, mode_name: str) -> None:
            self.calls.append(("mode", mode_name))

    window = _NoFocusWindow()

    MainWindow._open_task_from_tray_notification(window, 5)

    assert window.calls == [("mode", MainWindow.MODE_TASKS)]
