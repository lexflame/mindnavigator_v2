from __future__ import annotations

import mindnavigator.main_window as legacy_main_window
import mindnavigator.windowing as legacy_windowing

from mindnavigator.main_window import MainWindow as LegacyMainWindow
from mindnavigator.main_window import normalize_enabled_workspace_ids as legacy_normalize_enabled_workspace_ids
from mindnavigator.main_window import normalize_nav_collapsed_setting as legacy_normalize_nav_collapsed_setting
from mindnavigator.window.collections import MainWindow, ResizeEdge, normalize_enabled_workspace_ids, normalize_nav_collapsed_setting
from mindnavigator.windowing import ResizeEdge as LegacyResizeEdge


def test_window_transfer_split_keeps_legacy_import_paths() -> None:
    assert LegacyMainWindow is MainWindow
    assert LegacyResizeEdge is ResizeEdge
    assert legacy_normalize_enabled_workspace_ids is normalize_enabled_workspace_ids
    assert legacy_normalize_nav_collapsed_setting is normalize_nav_collapsed_setting
    assert legacy_main_window.get_database is not None
    assert legacy_main_window.QTimer is not None
    assert legacy_windowing.ResizeEdge is ResizeEdge
