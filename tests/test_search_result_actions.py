from types import SimpleNamespace

from mindnavigator.window.collections.main_window import MainWindow


class _TaskPage:
    def __init__(self) -> None:
        self.viewed: list[int] = []
        self.edited: list[int] = []

    def open_task_for_view(self, task_id: int) -> None:
        self.viewed.append(task_id)

    def open_task_for_edit(self, task_id: int) -> None:
        self.edited.append(task_id)


class _Recents:
    def __init__(self) -> None:
        self.entities: list[dict] = []
        self.commands: list[str] = []
        self.actions: list[tuple[str, dict]] = []

    def record_entity(self, payload: dict) -> None:
        self.entities.append(payload)

    def record_command(self, command_id: str) -> None:
        self.commands.append(command_id)

    def record_result_action(self, action_id: str, payload: dict) -> None:
        self.actions.append((action_id, payload))


def _window_stub():
    task_page = _TaskPage()
    modes: list[int] = []
    return SimpleNamespace(
        MODE_TASKS=1,
        page_tasks=task_page,
        set_mode=modes.append,
    ), task_page, modes


def test_task_card_actions_use_public_workspace_methods() -> None:
    window, task_page, modes = _window_stub()

    MainWindow._execute_search_result_action(window, "task.view", {"entity": "task", "id": 12})
    MainWindow._execute_search_result_action(window, "task.edit", {"entity": "task", "id": 13})

    assert modes == [1, 1]
    assert task_page.viewed == [12]
    assert task_page.edited == [13]


def test_search_open_action_delegates_to_existing_navigation() -> None:
    activated: list[dict] = []
    window = SimpleNamespace(_on_search_result_activated=activated.append)
    payload = {"entity": "idea", "id": 9}

    MainWindow._execute_search_result_action(window, "open", payload)

    assert activated == [payload]


def test_palette_activation_records_recent_items() -> None:
    recents = _Recents()
    activated: list[dict] = []
    callbacks: list[str] = []
    executed_actions: list[tuple[str, dict]] = []
    window = SimpleNamespace(
        _search_recents=recents,
        _on_search_result_activated=activated.append,
        _resolve_hotkey_callback=lambda command_id: lambda: callbacks.append(command_id),
        _execute_search_result_action=lambda action_id, payload: executed_actions.append((action_id, payload)),
    )
    payload = {"entity": "task", "id": 4, "label": "Задача 4"}

    MainWindow._activate_command_palette_item(window, "entity", payload)
    MainWindow._activate_command_palette_item(window, "command", "task.create")
    MainWindow._activate_command_palette_item(
        window,
        "action",
        {"action_id": "task.view", "payload": payload},
    )

    assert recents.entities == [payload]
    assert recents.commands == ["task.create"]
    assert recents.actions == [("task.view", payload)]
    assert activated == [payload]
    assert callbacks == ["task.create"]
    assert executed_actions == [("task.view", payload)]
