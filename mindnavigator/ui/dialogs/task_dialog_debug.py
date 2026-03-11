from __future__ import annotations

from datetime import datetime
from pathlib import Path

_LOG_PATH = Path(__file__).resolve().parents[3] / "task_dialog_debug.log"


def debug_task_dialog(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with _LOG_PATH.open("a", encoding="utf-8") as stream:
            stream.write(f"[{timestamp}] {message}\n")
    except OSError:
        return


def task_dialog_debug_log_path() -> Path:
    return _LOG_PATH

