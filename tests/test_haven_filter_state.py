import pytest

from mindnavigator.workspaces.tasks.haven_filter_state import HavenFilterState


def test_haven_filter_state_normalizes_scope_and_badge() -> None:
    state = HavenFilterState()

    state.set_scope("project", "42", "  Core  ")
    assert state.scope_kind == "project"
    assert state.scope_value == 42
    assert state.scope_label == "Core"
    assert state.badge_visible is True

    state.set_scope("area", "  Work  ", "")
    assert state.scope_kind == "area"
    assert state.scope_value == "Work"
    assert state.scope_label == "Work"

    state.clear_scope()
    assert state.badge_visible is False
    assert state.scope_value is None


def test_haven_filter_state_toggles_importance_independently() -> None:
    state = HavenFilterState()
    state.set_scope("area", "Work", "Work")

    assert state.toggle_importance(5) == 5
    assert state.matches_importance(5) is True
    assert state.matches_importance(4) is False
    assert state.scope_kind == "area"
    assert state.toggle_importance(5) is None
    assert state.matches_importance(5) is False
    assert state.scope_kind == "area"


def test_haven_filter_state_rejects_unknown_scope() -> None:
    state = HavenFilterState()

    with pytest.raises(ValueError, match="Unsupported Haven filter kind"):
        state.set_scope("unknown", 1, "Unknown")
