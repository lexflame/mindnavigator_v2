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
