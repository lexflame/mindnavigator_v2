from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QObject, QEvent, QTimer, Qt
from PySide6.QtWidgets import QAbstractItemView, QAbstractScrollArea, QWidget


@dataclass(slots=True)
class SmoothScrollConfig:
    frame_interval_ms: int = 12
    easing_factor: float = 0.33
    wheel_step_px: int = 42
    max_step_px: int = 120
    max_pending_px: int = 2400
    horizontal: bool = False


class SmoothScrollController(QObject):
    """Interpolates wheel events into smooth scroll updates."""

    def __init__(self, target: QAbstractScrollArea, config: SmoothScrollConfig | None = None) -> None:
        super().__init__(target)
        self._target = target
        self._config = config or SmoothScrollConfig()
        self._pending_px: int = 0
        self._target_value: int | None = None
        self._stall_ticks: int = 0
        self._timer = QTimer(self)
        self._timer.setInterval(self._config.frame_interval_ms)
        self._timer.timeout.connect(self._on_tick)
        self._install()

    def _install(self) -> None:
        viewport = self._target.viewport() if hasattr(self._target, "viewport") else self._target
        viewport.installEventFilter(self)
        self._target.installEventFilter(self)
        window = self._target.window()
        if window is not None and window is not self._target:
            window.installEventFilter(self)
        if isinstance(self._target, QAbstractItemView):
            self._target.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
            self._target.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        scrollbar = self._scrollbar()
        if scrollbar is not None:
            scrollbar.rangeChanged.connect(self._on_range_changed)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        event_type = event.type()
        if event_type in (
            QEvent.Type.FocusOut,
            QEvent.Type.WindowDeactivate,
            QEvent.Type.Hide,
            QEvent.Type.Close,
        ):
            self._cancel_animation()
            return super().eventFilter(watched, event)

        if event_type != QEvent.Type.Wheel:
            return super().eventFilter(watched, event)
        if not isinstance(watched, QWidget):
            return super().eventFilter(watched, event)

        delta = self._extract_delta_px(event)
        if delta == 0:
            return super().eventFilter(watched, event)

        self._queue_delta(delta)
        event.accept()
        return True

    def _extract_delta_px(self, event: QEvent) -> int:
        wheel = event
        pixel_delta = wheel.pixelDelta()  # type: ignore[attr-defined]
        angle_delta = wheel.angleDelta()  # type: ignore[attr-defined]
        axis_delta = pixel_delta.x() if self._config.horizontal else pixel_delta.y()
        if axis_delta:
            return axis_delta
        step_units = (angle_delta.x() if self._config.horizontal else angle_delta.y()) / 120.0
        if step_units == 0:
            return 0
        return int(step_units * self._config.wheel_step_px)

    def _queue_delta(self, delta_px: int) -> None:
        pending = self._pending_px + delta_px
        cap = self._config.max_pending_px
        self._pending_px = max(-cap, min(cap, pending))

        scrollbar = self._scrollbar()
        if scrollbar is None:
            return
        current = scrollbar.value()
        if self._target_value is None:
            self._target_value = current
        self._target_value = self._target_value - delta_px
        self._target_value = max(scrollbar.minimum(), min(scrollbar.maximum(), self._target_value))
        self._stall_ticks = 0
        if not self._timer.isActive():
            self._timer.start()

    def _on_tick(self) -> None:
        scrollbar = self._scrollbar()
        if scrollbar is None:
            self._timer.stop()
            self._target_value = None
            self._pending_px = 0
            return

        if self._target_value is None:
            self._timer.stop()
            return

        self._target_value = max(scrollbar.minimum(), min(scrollbar.maximum(), self._target_value))

        current = scrollbar.value()
        diff = self._target_value - current
        if abs(diff) <= 1:
            scrollbar.setValue(self._target_value)
            self._cancel_animation()
            return

        raw_step = int(diff * self._config.easing_factor)
        if raw_step == 0:
            raw_step = 1 if diff > 0 else -1
        cap = self._config.max_step_px
        step = max(-cap, min(cap, raw_step))
        next_value = max(scrollbar.minimum(), min(scrollbar.maximum(), current + step))
        scrollbar.setValue(next_value)
        moved = scrollbar.value() != current

        if not moved:
            self._stall_ticks += 1
            if self._stall_ticks >= 2:
                self._cancel_animation()
                return
        else:
            self._stall_ticks = 0

    def _scrollbar(self):
        return self._target.horizontalScrollBar() if self._config.horizontal else self._target.verticalScrollBar()

    def _on_range_changed(self, minimum: int, maximum: int) -> None:
        if self._target_value is None:
            return
        self._target_value = max(minimum, min(maximum, self._target_value))
        if minimum >= maximum:
            self._cancel_animation()

    def _cancel_animation(self) -> None:
        self._timer.stop()
        self._target_value = None
        self._pending_px = 0
        self._stall_ticks = 0


def attach_smooth_scroll(target: QAbstractScrollArea, config: SmoothScrollConfig | None = None) -> SmoothScrollController:
    return SmoothScrollController(target=target, config=config)
