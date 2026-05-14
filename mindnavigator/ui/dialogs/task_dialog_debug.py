from __future__ import annotations

from pathlib import Path

_LOG_PATH = Path(__file__).resolve().parents[3] / "task_dialog_debug.log"


def debug_task_dialog(message: str) -> None:
    _ = message
    return


def task_dialog_debug_log_path() -> Path:
    return _LOG_PATH

