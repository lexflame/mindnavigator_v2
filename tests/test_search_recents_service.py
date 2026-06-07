import json

from mindnavigator.services import SearchRecentsService


class _Settings:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def get_setting(self, key: str, default: str = "") -> str:
        return self.values.get(key, default)

    def set_setting(self, key: str, value: str) -> None:
        self.values[key] = value


def _entity(entity_id: int) -> dict[str, object]:
    return {"entity": "task", "id": entity_id, "label": f"Задача {entity_id}", "ignored": object()}


def test_recent_entities_are_deduplicated_and_bounded() -> None:
    settings = _Settings()
    service = SearchRecentsService(settings, limit=2)

    service.record_entity(_entity(1))
    service.record_entity(_entity(2))
    service.record_entity(_entity(1))
    service.record_entity(_entity(3))

    assert [item["id"] for item in service.recent_entities()] == [3, 1]
    assert "ignored" not in settings.values[service.ENTITIES_KEY]


def test_recent_actions_keep_commands_and_entity_actions() -> None:
    settings = _Settings()
    service = SearchRecentsService(settings)

    service.record_command("task.create")
    service.record_result_action("task.view", _entity(7))
    service.record_command("task.create")

    actions = service.recent_actions()
    assert actions[0] == {"kind": "command", "command_id": "task.create"}
    assert actions[1]["action_id"] == "task.view"


def test_recents_ignore_malformed_json_and_entries() -> None:
    settings = _Settings()
    settings.values[SearchRecentsService.ENTITIES_KEY] = "not json"
    settings.values[SearchRecentsService.ACTIONS_KEY] = json.dumps([{"kind": "command"}, "bad"])
    service = SearchRecentsService(settings)

    assert service.recent_entities() == ()
    assert service.recent_actions() == ()
