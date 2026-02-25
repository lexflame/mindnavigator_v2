from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from PySide6.QtCore import QEasingCurve, QParallelAnimationGroup, QPropertyAnimation, QRect
from PySide6.QtWidgets import QGraphicsOpacityEffect, QWidget


def normalize_width_bounds(collapsed_width: int, expanded_width: int) -> tuple[int, int]:
    collapsed = max(1, int(collapsed_width))
    expanded = max(collapsed, int(expanded_width))
    return collapsed, expanded


def normalize_duration_ms(duration_ms: int) -> int:
    return max(1, int(duration_ms))


@dataclass(frozen=True)
class WidthExpandAnimationConfig:
    collapsed_width: int = 56
    expanded_width: int = 240
    duration_ms: int = 140
    easing: QEasingCurve.Type = QEasingCurve.Type.OutCubic

    def normalized(self) -> WidthExpandAnimationConfig:
        collapsed, expanded = normalize_width_bounds(self.collapsed_width, self.expanded_width)
        return WidthExpandAnimationConfig(
            collapsed_width=collapsed,
            expanded_width=expanded,
            duration_ms=normalize_duration_ms(self.duration_ms),
            easing=self.easing,
        )


@dataclass(frozen=True)
class DialogAppearAnimationConfig:
    duration_ms: int = 160
    offset_px: int = 14
    start_opacity: float = 0.0
    end_opacity: float = 1.0
    easing: QEasingCurve.Type = QEasingCurve.Type.OutCubic

    def normalized(self) -> DialogAppearAnimationConfig:
        start = max(0.0, min(1.0, float(self.start_opacity)))
        end = max(0.0, min(1.0, float(self.end_opacity)))
        return DialogAppearAnimationConfig(
            duration_ms=normalize_duration_ms(self.duration_ms),
            offset_px=max(0, int(self.offset_px)),
            start_opacity=start,
            end_opacity=end,
            easing=self.easing,
        )


class WidthExpandAnimator:
    """Fast, smooth width animation for sidebar/panel expansion."""

    def __init__(
        self,
        widget: QWidget,
        config: Optional[WidthExpandAnimationConfig] = None,
    ) -> None:
        self._widget = widget
        self._config = (config or WidthExpandAnimationConfig()).normalized()
        self._group = QParallelAnimationGroup(widget)
        self._min_animation = QPropertyAnimation(widget, b"minimumWidth", widget)
        self._max_animation = QPropertyAnimation(widget, b"maximumWidth", widget)
        self._group.addAnimation(self._min_animation)
        self._group.addAnimation(self._max_animation)
        self._expanded = widget.width() >= self._config.expanded_width

    @property
    def expanded(self) -> bool:
        return self._expanded

    def expand(self, *, immediate: bool = False) -> None:
        self.set_expanded(True, immediate=immediate)

    def collapse(self, *, immediate: bool = False) -> None:
        self.set_expanded(False, immediate=immediate)

    def toggle(self, *, immediate: bool = False) -> None:
        self.set_expanded(not self._expanded, immediate=immediate)

    def set_expanded(self, expanded: bool, *, immediate: bool = False) -> None:
        target_width = self._config.expanded_width if expanded else self._config.collapsed_width
        if immediate:
            self._group.stop()
            self._widget.setMinimumWidth(target_width)
            self._widget.setMaximumWidth(target_width)
            self._expanded = expanded
            return

        self._group.stop()
        start_width = max(1, self._widget.width())
        self._setup_animation(self._min_animation, start_width, target_width)
        self._setup_animation(self._max_animation, start_width, target_width)
        self._group.start()
        self._expanded = expanded

    def _setup_animation(self, animation: QPropertyAnimation, start_width: int, end_width: int) -> None:
        animation.setDuration(self._config.duration_ms)
        animation.setEasingCurve(self._config.easing)
        animation.setStartValue(start_width)
        animation.setEndValue(end_width)


class DialogAppearAnimator:
    """Fast fade + slide-in animation for dialog appearance."""

    def __init__(self, config: Optional[DialogAppearAnimationConfig] = None) -> None:
        self._config = (config or DialogAppearAnimationConfig()).normalized()
        self._active_animations: list[QParallelAnimationGroup] = []

    def play(self, widget: QWidget) -> None:
        cfg = self._config
        end_rect = widget.geometry()
        start_rect = QRect(end_rect)
        start_rect.translate(0, cfg.offset_px)

        opacity_effect = widget.graphicsEffect()
        if not isinstance(opacity_effect, QGraphicsOpacityEffect):
            opacity_effect = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(opacity_effect)
        opacity_effect.setOpacity(cfg.start_opacity)

        geometry_animation = QPropertyAnimation(widget, b"geometry", widget)
        geometry_animation.setDuration(cfg.duration_ms)
        geometry_animation.setEasingCurve(cfg.easing)
        geometry_animation.setStartValue(start_rect)
        geometry_animation.setEndValue(end_rect)

        opacity_animation = QPropertyAnimation(opacity_effect, b"opacity", widget)
        opacity_animation.setDuration(cfg.duration_ms)
        opacity_animation.setEasingCurve(cfg.easing)
        opacity_animation.setStartValue(cfg.start_opacity)
        opacity_animation.setEndValue(cfg.end_opacity)

        group = QParallelAnimationGroup(widget)
        group.addAnimation(geometry_animation)
        group.addAnimation(opacity_animation)
        group.finished.connect(lambda: self._on_animation_finished(group))
        self._active_animations.append(group)
        group.start()

    def _on_animation_finished(self, group: QParallelAnimationGroup) -> None:
        if group in self._active_animations:
            self._active_animations.remove(group)
