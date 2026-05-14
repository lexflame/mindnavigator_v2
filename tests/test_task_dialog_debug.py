from __future__ import annotations

from mindnavigator.ui.dialogs import task_dialog_debug


def test_debug_task_dialog_no_longer_creates_log_file(monkeypatch, tmp_path) -> None:
    log_path = tmp_path / "task_dialog_debug.log"
    monkeypatch.setattr(task_dialog_debug, "_LOG_PATH", log_path)

    task_dialog_debug.debug_task_dialog("test message")

    assert task_dialog_debug.task_dialog_debug_log_path() == log_path
    assert log_path.exists() is False
