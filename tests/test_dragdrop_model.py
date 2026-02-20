import pytest

from mindnavigator.ui.dragdrop.model import DragPayload, DragPhase, DragSessionState, MotionConfig


def test_drag_payload_debug_dict():
    payload = DragPayload(
        entity_type="task",
        entity_id=42,
        source_workspace="tasks",
        meta={"priority": "high"},
    )
    assert payload.to_debug_dict()["entity_id"] == 42


def test_motion_config_validate_ok():
    cfg = MotionConfig(profile="ease_out", duration_ms=120, max_step_px=64, ghost_opacity=0.75, ghost_scale=1.05)
    cfg.validate()


def test_motion_config_validate_errors():
    with pytest.raises(ValueError):
        MotionConfig(profile="bad").validate()
    with pytest.raises(ValueError):
        MotionConfig(duration_ms=0).validate()
    with pytest.raises(ValueError):
        MotionConfig(max_step_px=0).validate()
    with pytest.raises(ValueError):
        MotionConfig(ghost_opacity=1.5).validate()
    with pytest.raises(ValueError):
        MotionConfig(ghost_scale=0).validate()
    with pytest.raises(ValueError):
        MotionConfig(ghost_invalid_opacity=2.0).validate()
    with pytest.raises(ValueError):
        MotionConfig(ghost_invalid_scale=0.0).validate()
    with pytest.raises(ValueError):
        MotionConfig(hover_scale_boost=0.0).validate()
    with pytest.raises(ValueError):
        MotionConfig(drop_success_duration_ms=0).validate()
    with pytest.raises(ValueError):
        MotionConfig(drop_failure_duration_ms=0).validate()


def test_drag_session_transition_happy_path():
    state = DragSessionState()
    state.transition(DragPhase.ARMING)
    state.transition(DragPhase.DRAGGING)
    state.transition(DragPhase.DROPPING)
    state.transition(DragPhase.IDLE)
    assert state.phase == DragPhase.IDLE


def test_drag_session_transition_invalid():
    state = DragSessionState()
    with pytest.raises(ValueError):
        state.transition(DragPhase.DRAGGING)


def test_drag_session_update_target_and_reset():
    state = DragSessionState(phase=DragPhase.ARMING, start_pos_global=(10, 20), started_at_ms=100)
    state.update_position((20, 30), 140)
    state.set_target("zone-1", True)

    debug = state.to_debug_dict()
    assert debug["current_pos_global"] == (20, 30)
    assert debug["target_zone_id"] == "zone-1"
    assert debug["is_target_valid"] is True

    state.reset()
    assert state.phase == DragPhase.IDLE
    assert state.current_pos_global == (0, 0)
    assert state.target_zone_id is None
