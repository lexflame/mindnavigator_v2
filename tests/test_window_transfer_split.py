from __future__ import annotations

import mindnavigator.window.collections.main_window as main_window
from mindnavigator.window.collections import (
    MainWindow,
    ResizeEdge,
    normalize_enabled_workspace_ids,
    normalize_nav_collapsed_setting,
)
from mindnavigator.window.collections.windowing import ResizeEdge as WindowResizeEdge


def test_window_packages_export_main_window_symbols() -> None:
    assert WindowResizeEdge is ResizeEdge
    assert main_window.MainWindow is MainWindow
    assert main_window.normalize_enabled_workspace_ids is normalize_enabled_workspace_ids
    assert main_window.normalize_nav_collapsed_setting is normalize_nav_collapsed_setting
    assert main_window.get_database is not None
    assert main_window.QTimer is not None
