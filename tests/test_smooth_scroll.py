from mindnavigator.ui.smooth_scroll import SmoothScrollConfig, SmoothScrollController, SmoothScrollStats


class _FakeTimer:
    def __init__(self) -> None:
        self.active = False

    def isActive(self) -> bool:
        return self.active

    def start(self) -> None:
        self.active = True

    def stop(self) -> None:
        self.active = False


class _FakeScrollbar:
    def __init__(self, value: int, minimum: int, maximum: int, page_step: int = 80, frozen: bool = False) -> None:
        self._value = value
        self._minimum = minimum
        self._maximum = maximum
        self._page_step = page_step
        self._frozen = frozen

    def value(self) -> int:
        return self._value

    def setValue(self, value: int) -> None:
        if self._frozen:
            return
        self._value = max(self._minimum, min(self._maximum, value))

    def minimum(self) -> int:
        return self._minimum

    def maximum(self) -> int:
        return self._maximum

    def pageStep(self) -> int:
        return self._page_step


def _controller(config: SmoothScrollConfig, scrollbar: _FakeScrollbar) -> SmoothScrollController:
    controller = SmoothScrollController.__new__(SmoothScrollController)
    controller._config = config
    controller._stats = SmoothScrollStats()
    controller._pending_px = 0
    controller._target_value = None
    controller._stall_ticks = 0
    controller._timer = _FakeTimer()
    controller._scrollbar = lambda: scrollbar
    return controller


def test_queue_delta_clamps_target_and_counts_clamp() -> None:
    scrollbar = _FakeScrollbar(value=95, minimum=0, maximum=100)
    controller = _controller(SmoothScrollConfig(max_pending_px=200), scrollbar)

    controller._queue_delta(-100)

    assert controller._target_value == 100
    assert controller.snapshot_stats().clamped_targets == 1


def test_queue_delta_ignores_too_small_delta() -> None:
    scrollbar = _FakeScrollbar(value=50, minimum=0, maximum=100)
    controller = _controller(SmoothScrollConfig(min_effective_delta_px=5), scrollbar)

    controller._queue_delta(3)

    assert controller._target_value is None
    assert controller._pending_px == 0


def test_range_change_clamps_target_and_can_cancel() -> None:
    scrollbar = _FakeScrollbar(value=20, minimum=0, maximum=100)
    controller = _controller(SmoothScrollConfig(), scrollbar)
    controller._target_value = 80
    controller._pending_px = 100
    controller._timer.start()

    controller._on_range_changed(0, 60)
    assert controller._target_value == 60

    controller._on_range_changed(10, 10)
    assert controller._target_value is None
    assert controller._pending_px == 0
    assert controller._timer.isActive() is False


def test_tick_stall_cancels_animation() -> None:
    scrollbar = _FakeScrollbar(value=10, minimum=0, maximum=100, frozen=True)
    controller = _controller(SmoothScrollConfig(easing_factor=1.0), scrollbar)
    controller._target_value = 40

    controller._on_tick()
    controller._on_tick()

    assert controller._target_value is None
    assert controller.snapshot_stats().stall_cancels == 1


def test_stats_snapshot_and_reset() -> None:
    scrollbar = _FakeScrollbar(value=20, minimum=0, maximum=100)
    controller = _controller(SmoothScrollConfig(), scrollbar)
    controller._stats.wheel_events = 3
    controller._stats.applied_steps = 2

    snap = controller.snapshot_stats()
    assert snap.wheel_events == 3
    assert snap.applied_steps == 2

    controller.reset_stats()
    assert controller.snapshot_stats() == SmoothScrollStats()
