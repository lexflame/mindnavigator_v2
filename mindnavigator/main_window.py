"""Compatibility exports for the main window module."""

from .window.collections.main_window import (
    MainWindow,
    QTimer,
    ResizeEdge,
    get_database,
    normalize_enabled_workspace_ids,
    normalize_nav_collapsed_setting,
)

__all__ = [
    "MainWindow",
    "QTimer",
    "ResizeEdge",
    "get_database",
    "normalize_enabled_workspace_ids",
    "normalize_nav_collapsed_setting",
]
