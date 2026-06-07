from mindnavigator.services import SearchResultActionRegistry


def test_registry_returns_navigation_action_for_supported_entity() -> None:
    actions = SearchResultActionRegistry().actions_for({"entity": "idea", "id": 9})

    assert [(action.id, action.title) for action in actions] == [("open", "Перейти")]


def test_registry_adds_task_card_actions() -> None:
    actions = SearchResultActionRegistry().actions_for({"entity": "task", "id": 7})

    assert [action.id for action in actions] == ["open", "task.view", "task.edit"]


def test_registry_ignores_unsupported_or_incomplete_payload() -> None:
    registry = SearchResultActionRegistry()

    assert registry.actions_for({"entity": "unknown", "id": 1}) == ()
    assert registry.actions_for({"entity": "task"}) == ()
