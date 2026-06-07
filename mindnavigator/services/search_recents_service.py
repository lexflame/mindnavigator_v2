"""Bounded persistent history for command-palette entities and actions."""

from __future__ import annotations

import json
from typing import Mapping


class SearchRecentsService:
    ENTITIES_KEY = "ui.search_recent_entities"
    ACTIONS_KEY = "ui.search_recent_actions"

    def __init__(self, settings, *, limit: int = 5) -> None:
        self._settings = settings
        self._limit = max(1, int(limit))

    def recent_entities(self) -> tuple[dict[str, object], ...]:
        return tuple(valid for item in self._load(self.ENTITIES_KEY) if (valid := self._valid_entity(item)) is not None)

    def recent_actions(self) -> tuple[dict[str, object], ...]:
        return tuple(valid for item in self._load(self.ACTIONS_KEY) if (valid := self._valid_action(item)) is not None)

    def record_entity(self, payload: Mapping[str, object]) -> None:
        entity = self._entity_payload(payload)
        if entity is None:
            return
        key = self._entity_key(entity)
        items = [item for item in self.recent_entities() if self._entity_key(item) != key]
        self._save(self.ENTITIES_KEY, [entity, *items])

    def record_command(self, command_id: str) -> None:
        normalized_id = str(command_id or "").strip()
        if not normalized_id:
            return
        entry = {"kind": "command", "command_id": normalized_id}
        items = [item for item in self.recent_actions() if self._action_key(item) != self._action_key(entry)]
        self._save(self.ACTIONS_KEY, [entry, *items])

    def record_result_action(self, action_id: str, payload: Mapping[str, object]) -> None:
        normalized_id = str(action_id or "").strip()
        entity = self._entity_payload(payload)
        if not normalized_id or entity is None:
            return
        entry = {"kind": "action", "action_id": normalized_id, "payload": entity}
        items = [item for item in self.recent_actions() if self._action_key(item) != self._action_key(entry)]
        self._save(self.ACTIONS_KEY, [entry, *items])

    def _load(self, key: str) -> list[object]:
        try:
            value = json.loads(self._settings.get_setting(key, "[]"))
        except (TypeError, ValueError, json.JSONDecodeError):
            return []
        return value if isinstance(value, list) else []

    def _save(self, key: str, items: list[dict[str, object]]) -> None:
        self._settings.set_setting(key, json.dumps(items[: self._limit], ensure_ascii=False, separators=(",", ":")))

    @staticmethod
    def _entity_payload(payload: Mapping[str, object]) -> dict[str, object] | None:
        entity = str(payload.get("entity") or "").strip()
        entity_id = payload.get("id")
        label = str(payload.get("label") or "").strip()
        if not entity or entity_id is None or not label:
            return None
        result: dict[str, object] = {"entity": entity, "id": entity_id, "label": label}
        tooltip = str(payload.get("tooltip") or "").strip()
        if tooltip:
            result["tooltip"] = tooltip
        map_id = payload.get("map_id")
        if map_id is not None:
            result["map_id"] = map_id
        return result

    @classmethod
    def _valid_entity(cls, item: object) -> dict[str, object] | None:
        return cls._entity_payload(item) if isinstance(item, dict) else None

    @classmethod
    def _valid_action(cls, item: object) -> dict[str, object] | None:
        if not isinstance(item, dict):
            return None
        if item.get("kind") == "command":
            command_id = str(item.get("command_id") or "").strip()
            return {"kind": "command", "command_id": command_id} if command_id else None
        if item.get("kind") == "action":
            action_id = str(item.get("action_id") or "").strip()
            payload = cls._valid_entity(item.get("payload"))
            if action_id and payload is not None:
                return {"kind": "action", "action_id": action_id, "payload": payload}
        return None

    @staticmethod
    def _entity_key(payload: Mapping[str, object]) -> tuple[object, object]:
        return payload.get("entity"), payload.get("id")

    @classmethod
    def _action_key(cls, item: Mapping[str, object]) -> tuple[object, ...]:
        if item.get("kind") == "command":
            return "command", item.get("command_id")
        payload = item.get("payload")
        entity_key = cls._entity_key(payload) if isinstance(payload, dict) else (None, None)
        return "action", item.get("action_id"), *entity_key


__all__ = ["SearchRecentsService"]
