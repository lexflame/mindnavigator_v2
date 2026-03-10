"""Helpers for resolving application resource paths."""

from __future__ import annotations

import sys
from pathlib import Path


def resource_path(relative_path: str) -> str:
    """Resolve a resource path for dev and PyInstaller builds."""
    base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    return str(base_path / relative_path)
