from __future__ import annotations

import sys
from pathlib import Path


def resource_path(relative_path: str) -> str:
    """Возвращает абсолютный путь к ресурсу для dev и PyInstaller."""
    base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return str(base_path / relative_path)
