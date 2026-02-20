from mindnavigator.ui.dragdrop.controller import DragDropController, DragSafetyConfig
from mindnavigator.ui.dragdrop.model import DragPayload, DragPhase, MotionConfig
from mindnavigator.ui.dragdrop.policy import DropZoneRect


class _Recorder:
    def __init__(self) -> None:
        self.ghost_calls = 0
        self.ghost_positions: list[tuple[int, int]] = []
        self.ghost_opacity: list[float] = []
        self.ghost_scale: list[float] = []
        self.feedback_calls = 0
        self.feedback_events: list[tuple[str | None, bool]] = []
        self.clear_calls = 0
        self.drop_results: list[bool] = []

    def render_drag_ghost(self, _payload, pos, _opacity, _scale) -> None:
        self.ghost_calls += 1
        self.ghost_positions.append(pos)
        self.ghost_opacity.append(_opacity)
        self.ghost_scale.append(_scale)

    def render_zone_feedback(self, zone_id, is_valid) -> None:
        self.feedback_calls += 1
        self.feedback_events.append((zone_id, is_valid))

    def clear_drag_visuals(self) -> None:
        self.clear_calls += 1

    def play_drop_result(self, success: bool) -> None:
        self.drop_results.append(success)


def test_controller_drag_drop_happy_path():
    recorder = _Recorder()
    zones = [DropZoneRect("zone-a", 0, 0, 100, 100)]
    controller = DragDropController(
        get_drop_zones=lambda: zones,
        render_drag_ghost=recorder.render_drag_ghost,
        render_zone_feedback=recorder.render_zone_feedback,
        clear_drag_visuals=recorder.clear_drag_visuals,
        play_drop_result=recorder.play_drop_result,
    )

    payload = DragPayload(entity_type="task", entity_id=1, source_workspace="tasks")
    controller.arm_drag(payload, (5, 5), 0)
    controller.on_pointer_move((15, 15), 80)
    assert controller.state.phase == DragPhase.DRAGGING
    controller.on_pointer_release((20, 20), 100)

    assert recorder.ghost_calls >= 1
    assert recorder.feedback_calls >= 1
    assert recorder.feedback_events[-1] == ("zone-a", True)
    assert recorder.drop_results == [True]


def test_controller_cancel_before_threshold():
    recorder = _Recorder()
    controller = DragDropController(
        get_drop_zones=lambda: [],
        render_drag_ghost=recorder.render_drag_ghost,
        render_zone_feedback=recorder.render_zone_feedback,
        clear_drag_visuals=recorder.clear_drag_visuals,
        play_drop_result=recorder.play_drop_result,
    )

    payload = DragPayload(entity_type="task", entity_id=2, source_workspace="tasks")
    controller.arm_drag(payload, (0, 0), 0)
    controller.on_pointer_release((0, 0), 10)

    assert recorder.drop_results == []
    assert controller.state.phase == DragPhase.IDLE


def test_controller_motion_linear_interpolation():
    recorder = _Recorder()
    zones = [DropZoneRect("zone-a", 0, 0, 500, 500)]
    controller = DragDropController(
        get_drop_zones=lambda: zones,
        render_drag_ghost=recorder.render_drag_ghost,
        render_zone_feedback=recorder.render_zone_feedback,
        clear_drag_visuals=recorder.clear_drag_visuals,
        play_drop_result=recorder.play_drop_result,
        motion=MotionConfig(profile="linear", duration_ms=100, max_step_px=500),
    )

    payload = DragPayload(entity_type="task", entity_id=3, source_workspace="tasks")
    controller.arm_drag(payload, (0, 0), 0)
    controller.on_pointer_move((100, 0), 50)

    assert recorder.ghost_positions[-1] == (50, 0)


def test_controller_motion_clamps_max_step():
    recorder = _Recorder()
    zones = [DropZoneRect("zone-a", 0, 0, 2000, 2000)]
    controller = DragDropController(
        get_drop_zones=lambda: zones,
        render_drag_ghost=recorder.render_drag_ghost,
        render_zone_feedback=recorder.render_zone_feedback,
        clear_drag_visuals=recorder.clear_drag_visuals,
        play_drop_result=recorder.play_drop_result,
        motion=MotionConfig(profile="linear", duration_ms=1, max_step_px=10),
    )

    payload = DragPayload(entity_type="task", entity_id=4, source_workspace="tasks")
    controller.arm_drag(payload, (0, 0), 0)
    controller.on_pointer_move((1000, 1000), 1)

    assert recorder.ghost_positions[-1] == (10, 10)


def test_controller_visual_polish_invalid_target_style():
    recorder = _Recorder()
    controller = DragDropController(
        get_drop_zones=lambda: [],
        render_drag_ghost=recorder.render_drag_ghost,
        render_zone_feedback=recorder.render_zone_feedback,
        clear_drag_visuals=recorder.clear_drag_visuals,
        play_drop_result=recorder.play_drop_result,
        motion=MotionConfig(
            profile="linear",
            duration_ms=100,
            max_step_px=100,
            ghost_opacity=0.9,
            ghost_scale=1.0,
            ghost_invalid_opacity=0.5,
            ghost_invalid_scale=0.8,
            hover_scale_boost=1.1,
        ),
    )

    payload = DragPayload(entity_type="task", entity_id=5, source_workspace="tasks")
    controller.arm_drag(payload, (0, 0), 0)
    controller.on_pointer_move((30, 0), 100)

    assert recorder.feedback_events[-1] == (None, False)
    assert recorder.ghost_opacity[-1] == 0.5
    assert recorder.ghost_scale[-1] == 0.8


def test_controller_visual_polish_drop_transition_hook():
    recorder = _Recorder()
    transitions: list[tuple[bool, int]] = []
    zones = [DropZoneRect("zone-a", 0, 0, 200, 200)]
    controller = DragDropController(
        get_drop_zones=lambda: zones,
        render_drag_ghost=recorder.render_drag_ghost,
        render_zone_feedback=recorder.render_zone_feedback,
        clear_drag_visuals=recorder.clear_drag_visuals,
        play_drop_result=recorder.play_drop_result,
        motion=MotionConfig(drop_success_duration_ms=111, drop_failure_duration_ms=222),
    )
    controller.on_drop_transition = lambda success, ms: transitions.append((success, ms))

    payload = DragPayload(entity_type="task", entity_id=6, source_workspace="tasks")
    controller.arm_drag(payload, (5, 5), 0)
    controller.on_pointer_move((15, 15), 80)
    controller.on_pointer_release((15, 15), 100)

    assert transitions[-1] == (True, 111)


def test_controller_cancel_when_pointer_leaves_window():
    recorder = _Recorder()
    canceled: list[str] = []
    controller = DragDropController(
        get_drop_zones=lambda: [DropZoneRect("zone-a", 0, 0, 100, 100)],
        render_drag_ghost=recorder.render_drag_ghost,
        render_zone_feedback=recorder.render_zone_feedback,
        clear_drag_visuals=recorder.clear_drag_visuals,
        play_drop_result=recorder.play_drop_result,
        is_within_window=lambda p: 0 <= p[0] <= 100 and 0 <= p[1] <= 100,
    )
    controller.on_drag_canceled = lambda reason: canceled.append(reason)

    payload = DragPayload(entity_type="task", entity_id=7, source_workspace="tasks")
    controller.arm_drag(payload, (10, 10), 0)
    controller.on_pointer_move((20, 20), 60)
    controller.on_pointer_move((500, 500), 70)

    assert canceled[-1] == "out_of_window"
    assert controller.state.phase == DragPhase.IDLE


def test_controller_escape_key_cancels_drag():
    recorder = _Recorder()
    canceled: list[str] = []
    controller = DragDropController(
        get_drop_zones=lambda: [DropZoneRect("zone-a", 0, 0, 100, 100)],
        render_drag_ghost=recorder.render_drag_ghost,
        render_zone_feedback=recorder.render_zone_feedback,
        clear_drag_visuals=recorder.clear_drag_visuals,
        play_drop_result=recorder.play_drop_result,
    )
    controller.on_drag_canceled = lambda reason: canceled.append(reason)

    payload = DragPayload(entity_type="task", entity_id=8, source_workspace="tasks")
    controller.arm_drag(payload, (10, 10), 0)
    controller.on_pointer_move((20, 20), 60)
    controller.on_key_event("Escape")

    assert canceled[-1] == "escape_key"
    assert controller.state.phase == DragPhase.IDLE


def test_controller_normalize_position_for_multi_monitor_offset():
    recorder = _Recorder()
    controller = DragDropController(
        get_drop_zones=lambda: [DropZoneRect("zone-a", 0, 0, 200, 200)],
        render_drag_ghost=recorder.render_drag_ghost,
        render_zone_feedback=recorder.render_zone_feedback,
        clear_drag_visuals=recorder.clear_drag_visuals,
        play_drop_result=recorder.play_drop_result,
        normalize_position=lambda p: (p[0] - 1000, p[1] - 500),
    )

    payload = DragPayload(entity_type="task", entity_id=9, source_workspace="tasks")
    controller.arm_drag(payload, (1010, 510), 0)
    controller.on_pointer_move((1020, 520), 80)

    assert controller.state.current_pos_global == (20, 20)
    assert recorder.feedback_events[-1] == ("zone-a", True)


def test_controller_fast_move_threshold_limits_jump():
    recorder = _Recorder()
    controller = DragDropController(
        get_drop_zones=lambda: [DropZoneRect("zone-a", 0, 0, 5000, 5000)],
        render_drag_ghost=recorder.render_drag_ghost,
        render_zone_feedback=recorder.render_zone_feedback,
        clear_drag_visuals=recorder.clear_drag_visuals,
        play_drop_result=recorder.play_drop_result,
        safety=DragSafetyConfig(fast_move_threshold_px=30),
    )

    payload = DragPayload(entity_type="task", entity_id=10, source_workspace="tasks")
    controller.arm_drag(payload, (0, 0), 0)
    controller.on_pointer_move((1000, 1000), 60)

    assert controller.state.current_pos_global == (30, 30)
