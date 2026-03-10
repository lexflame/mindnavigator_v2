"""Window collections package exports."""

from .main_window import MainWindow, normalize_enabled_workspace_ids, normalize_nav_collapsed_setting
from .windowing import ResizeEdge

__all__ = [
    "MainWindow",
    "ResizeEdge",
    "normalize_enabled_workspace_ids",
    "normalize_nav_collapsed_setting",
]
