from mindnavigator.ui.dragdrop.controller import DragDropController
from mindnavigator.ui.dragdrop.model import DragPayload
from mindnavigator.ui.dragdrop.policy import DropZoneRect, RuleBasedDropValidator


class _Executor:
    def __init__(self, result: bool = True) -> None:
        self.calls: list[tuple[str, int | str]] = []
        self.result = result

    def execute(self, payload: DragPayload, zone_id: str) -> bool:
        self.calls.append((zone_id, payload.entity_id))
        return self.result


def test_dragdrop_integration_commit_flow():
    zones = [DropZoneRect("task-zone", 0, 0, 200, 200)]
    validator = RuleBasedDropValidator({"task-zone": {"task"}})
    executor = _Executor(result=True)
    callbacks: list[str] = []

    controller = DragDropController(
        get_drop_zones=lambda: zones,
        render_drag_ghost=lambda *_: None,
        render_zone_feedback=lambda *_: None,
        clear_drag_visuals=lambda: None,
        play_drop_result=lambda success: callbacks.append(f"result:{success}"),
        validator=validator,
        executor=executor,
    )
    controller.on_drop_requested = lambda payload, zone: callbacks.append(f"request:{payload.entity_id}:{zone}")
    controller.on_drop_committed = lambda payload, zone: callbacks.append(f"commit:{payload.entity_id}:{zone}")

    payload = DragPayload(entity_type="task", entity_id=101, source_workspace="tasks")
    controller.arm_drag(payload, (10, 10), 0)
    controller.on_pointer_move((20, 20), 80)
    controller.on_pointer_release((20, 20), 90)

    assert executor.calls == [("task-zone", 101)]
    assert callbacks[0] == "request:101:task-zone"
    assert callbacks[1] == "commit:101:task-zone"
    assert callbacks[2] == "result:True"


def test_dragdrop_integration_reject_flow():
    zones = [DropZoneRect("task-zone", 0, 0, 200, 200)]
    validator = RuleBasedDropValidator({"task-zone": {"task"}})
    executor = _Executor(result=True)
    callbacks: list[str] = []

    controller = DragDropController(
        get_drop_zones=lambda: zones,
        render_drag_ghost=lambda *_: None,
        render_zone_feedback=lambda *_: None,
        clear_drag_visuals=lambda: None,
        play_drop_result=lambda success: callbacks.append(f"result:{success}"),
        validator=validator,
        executor=executor,
    )

    payload = DragPayload(entity_type="note", entity_id=102, source_workspace="notes")
    controller.arm_drag(payload, (10, 10), 0)
    controller.on_pointer_move((20, 20), 80)
    controller.on_pointer_release((20, 20), 90)

    assert executor.calls == []
    assert callbacks[-1] == "result:False"
