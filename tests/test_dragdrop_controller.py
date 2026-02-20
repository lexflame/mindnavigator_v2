from mindnavigator.ui.dragdrop.controller import DragDropController
from mindnavigator.ui.dragdrop.model import DragPayload, DragPhase, MotionConfig
from mindnavigator.ui.dragdrop.policy import DropZoneRect


class _Recorder:
    def __init__(self) -> None:
        self.ghost_calls = 0
        self.ghost_positions: list[tuple[int, int]] = []
        self.feedback_calls = 0
        self.clear_calls = 0
        self.drop_results: list[bool] = []

    def render_drag_ghost(self, _payload, pos, _opacity, _scale) -> None:
        self.ghost_calls += 1
        self.ghost_positions.append(pos)

    def render_zone_feedback(self, *_args) -> None:
        self.feedback_calls += 1

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
