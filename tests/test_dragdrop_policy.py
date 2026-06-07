from mindnavigator.ui.dragdrop.model import DragPayload
from mindnavigator.ui.dragdrop.policy import (
    DropZoneRect,
    EntityLinkDropPolicy,
    NestedHitTestService,
    RuleBasedDropValidator,
)


def test_nested_hit_test_prefers_smaller_zone_on_same_priority():
    zones = [
        DropZoneRect("root", 0, 0, 300, 300, priority=1),
        DropZoneRect("child", 50, 50, 100, 100, priority=1, parent_zone_id="root"),
    ]
    hit = NestedHitTestService().resolve_zone((60, 60), zones)
    assert hit == "child"


def test_nested_hit_test_prefers_higher_priority():
    zones = [
        DropZoneRect("a", 0, 0, 200, 200, priority=1),
        DropZoneRect("b", 0, 0, 300, 300, priority=2),
    ]
    hit = NestedHitTestService().resolve_zone((20, 20), zones)
    assert hit == "b"


def test_rule_based_drop_validator():
    payload_task = DragPayload(entity_type="task", entity_id=1, source_workspace="tasks")
    payload_note = DragPayload(entity_type="note", entity_id=2, source_workspace="notes")
    validator = RuleBasedDropValidator(
        {
            "task-zone": {"task"},
            "note-zone": {"note"},
        }
    )
    assert validator.validate(payload_task, "task-zone") is True
    assert validator.validate(payload_note, "task-zone") is False
    assert validator.validate(payload_task, "unknown-zone") is False


def test_entity_link_drop_policy_allows_only_declared_pairs_and_valid_ids():
    assert EntityLinkDropPolicy.can_link("task", 10, "idea", 20) is True
    assert EntityLinkDropPolicy.can_link("project", 10, "idea", 20) is False
    assert EntityLinkDropPolicy.can_link("task", 0, "idea", 20) is False
    assert EntityLinkDropPolicy.can_link("idea", 20, "idea", 20) is False
