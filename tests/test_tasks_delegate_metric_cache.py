from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication

from mindnavigator.workspaces.tasks.tasks_item_delegate import TasksItemDelegate


class _CountingMetrics:
    def __init__(self, metrics) -> None:
        self._metrics = metrics
        self.bounding_rect_calls = 0

    def boundingRect(self, *args, **kwargs):
        self.bounding_rect_calls += 1
        return self._metrics.boundingRect(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._metrics, name)


def test_expanded_height_metrics_are_cached_by_content_and_width() -> None:
    _app = QApplication.instance() or QApplication([])
    delegate = TasksItemDelegate()
    title_metrics = _CountingMetrics(delegate._font_metrics)
    small_metrics = _CountingMetrics(delegate._font_small_metrics)
    delegate._font_metrics = title_metrics
    delegate._font_small_metrics = small_metrics
    try:
        first_height = delegate._expanded_content_height(
            420,
            "MN-1: Cached title",
            "Cached description",
            ("Заметка ×2",),
        )
        repeated_height = delegate._expanded_content_height(
            420,
            "MN-1: Cached title",
            "Cached description",
            ("Заметка ×2",),
        )

        assert repeated_height == first_height
        assert title_metrics.bounding_rect_calls == 1
        assert small_metrics.bounding_rect_calls == 1
        assert len(delegate._expanded_height_cache) == 1

        delegate._expanded_content_height(
            300,
            "MN-1: Cached title",
            "Cached description",
            ("Заметка ×2",),
        )
        assert title_metrics.bounding_rect_calls == 2
        assert small_metrics.bounding_rect_calls == 2
        assert len(delegate._expanded_height_cache) == 2

        delegate.clear_layout_metric_cache()
        assert delegate._expanded_height_cache == {}
    finally:
        delegate.deleteLater()


def test_priority_fire_icons_are_cached_and_reset_with_theme() -> None:
    _app = QApplication.instance() or QApplication([])
    delegate = TasksItemDelegate()
    try:
        first_icon = delegate._priority_fire_icon(QColor("#cf4d4d"))
        repeated_icon = delegate._priority_fire_icon(QColor("#cf4d4d"))

        assert repeated_icon is first_icon
        assert len(delegate._priority_fire_icon_cache) == 1

        delegate.set_theme_mode("light")
        assert delegate._priority_fire_icon_cache == {}
        assert delegate._expanded_height_cache == {}
    finally:
        delegate.deleteLater()
