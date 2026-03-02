from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

API_NAME = "mindnavigator.entity_api"
API_SCHEMA_VERSION = "2026-03-02"
API_PROTOCOL_VERSION = "1.0"
DEFAULT_SERVICE_NAME = "MindNavigator Entity API Pool"
DEFAULT_COMPATIBLE_CLIENTS = ("codex",)


@dataclass(frozen=True)
class EntityOperationSpec:
    name: str
    summary: str
    parameters: tuple[str, ...]
    returns: str
    idempotent: bool

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["parameters"] = list(self.parameters)
        return payload


@dataclass(frozen=True)
class EntityKindSpec:
    kind: str
    title: str
    identity_field: str
    list_fields: tuple[str, ...]
    mutable_fields: tuple[str, ...]
    execute_actions: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["list_fields"] = list(self.list_fields)
        payload["mutable_fields"] = list(self.mutable_fields)
        payload["execute_actions"] = list(self.execute_actions)
        return payload


@dataclass(frozen=True)
class BootstrapExample:
    operation: str
    request: dict[str, Any]
    response: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class EntityApiPool:
    """Describes the application entity API for machine clients such as Codex."""

    def __init__(
        self,
        *,
        service_name: str = DEFAULT_SERVICE_NAME,
        compatible_clients: tuple[str, ...] = DEFAULT_COMPATIBLE_CLIENTS,
    ) -> None:
        self._service_name = service_name
        self._compatible_clients = tuple(client.lower() for client in compatible_clients if client)
        self._operations = self._build_operations()
        self._entity_kinds = self._build_entity_kinds()
        self._examples = self._build_examples()

    def describe(self) -> dict[str, Any]:
        return {
            "service_name": self._service_name,
            "api_name": API_NAME,
            "protocol_version": API_PROTOCOL_VERSION,
            "schema_version": API_SCHEMA_VERSION,
            "compatible_clients": list(self._compatible_clients),
            "codex_compatible": "codex" in self._compatible_clients,
            "handshake": {
                "connect_operation": "describe",
                "purpose": "Return a machine-readable description of the entity API surface.",
                "required_client_fields": ["client_name"],
                "optional_client_fields": ["client_version", "capabilities"],
            },
            "operations": [operation.to_dict() for operation in self._operations],
            "entity_kinds": [entity_kind.to_dict() for entity_kind in self._entity_kinds],
            "examples": [example.to_dict() for example in self._examples],
        }

    def connect(
        self,
        *,
        client_name: str,
        client_version: str | None = None,
        capabilities: list[str] | None = None,
    ) -> dict[str, Any]:
        description = self.describe()
        description["connection"] = {
            "client_name": client_name,
            "client_version": client_version or "unknown",
            "requested_capabilities": list(capabilities or []),
            "accepted": bool(client_name.strip()),
        }
        return description

    @staticmethod
    def _build_operations() -> tuple[EntityOperationSpec, ...]:
        return (
            EntityOperationSpec(
                name="list_entities",
                summary="List entities by kind with optional filters and paging.",
                parameters=("entity_kind", "filters", "limit", "offset"),
                returns="entity_list",
                idempotent=True,
            ),
            EntityOperationSpec(
                name="get_entity",
                summary="Read a single entity by kind and identifier.",
                parameters=("entity_kind", "entity_id"),
                returns="entity",
                idempotent=True,
            ),
            EntityOperationSpec(
                name="create_entity",
                summary="Create a new entity instance for the selected kind.",
                parameters=("entity_kind", "payload"),
                returns="entity",
                idempotent=False,
            ),
            EntityOperationSpec(
                name="update_entity",
                summary="Apply partial updates to an existing entity.",
                parameters=("entity_kind", "entity_id", "payload"),
                returns="entity",
                idempotent=False,
            ),
            EntityOperationSpec(
                name="delete_entity",
                summary="Delete an entity, subject to safety rules for linked data.",
                parameters=("entity_kind", "entity_id", "force"),
                returns="delete_result",
                idempotent=False,
            ),
            EntityOperationSpec(
                name="execute_entity_action",
                summary="Run a domain action on an entity and return the action result.",
                parameters=("entity_kind", "entity_id", "action", "payload"),
                returns="action_result",
                idempotent=False,
            ),
        )

    @staticmethod
    def _build_entity_kinds() -> tuple[EntityKindSpec, ...]:
        return (
            EntityKindSpec(
                kind="task",
                title="Task",
                identity_field="id",
                list_fields=("id", "title", "day", "done", "priority", "project_id"),
                mutable_fields=("title", "description", "day", "time_text", "priority", "done", "project_id"),
                execute_actions=("mark_done", "mark_pending", "toggle_done"),
            ),
            EntityKindSpec(
                kind="project",
                title="Project",
                identity_field="id",
                list_fields=("id", "title", "area", "priority", "archived", "parent_project_id"),
                mutable_fields=("title", "area", "priority", "archived", "parent_project_id"),
                execute_actions=("archive", "unarchive"),
            ),
            EntityKindSpec(
                kind="note",
                title="Note",
                identity_field="id",
                list_fields=("id", "title", "project", "favorite", "locked"),
                mutable_fields=("title", "preview", "tags", "project", "favorite", "locked"),
                execute_actions=("favorite", "unfavorite", "lock", "unlock"),
            ),
            EntityKindSpec(
                kind="idea",
                title="Idea",
                identity_field="id",
                list_fields=("id", "title", "status", "priority"),
                mutable_fields=("title", "summary", "body_md", "status", "priority"),
                execute_actions=("promote", "archive"),
            ),
            EntityKindSpec(
                kind="object",
                title="Object",
                identity_field="id",
                list_fields=("id", "title", "category", "folder_path"),
                mutable_fields=("title", "description", "category", "folder_path"),
                execute_actions=("refresh_images",),
            ),
            EntityKindSpec(
                kind="map",
                title="Map",
                identity_field="id",
                list_fields=("id", "title", "image_path", "updated_at"),
                mutable_fields=("title", "image_path"),
                execute_actions=("rebuild_overlays",),
            ),
            EntityKindSpec(
                kind="collection_item",
                title="Collection Item",
                identity_field="id",
                list_fields=("id", "title", "entity_type", "category_id", "topic"),
                mutable_fields=("title", "entity_type", "category_id", "topic", "description"),
                execute_actions=("reimport",),
            ),
        )

    @staticmethod
    def _build_examples() -> tuple[BootstrapExample, ...]:
        return (
            BootstrapExample(
                operation="describe",
                request={
                    "client_name": "codex",
                    "client_version": "1.0",
                    "capabilities": ["crud", "execute"],
                },
                response={
                    "codex_compatible": True,
                    "operations": [
                        "list_entities",
                        "get_entity",
                        "create_entity",
                        "update_entity",
                        "delete_entity",
                        "execute_entity_action",
                    ],
                },
            ),
            BootstrapExample(
                operation="get_entity",
                request={
                    "entity_kind": "task",
                    "entity_id": 42,
                },
                response={
                    "entity": {
                        "id": 42,
                        "title": "Prepare sprint",
                        "done": False,
                    }
                },
            ),
            BootstrapExample(
                operation="execute_entity_action",
                request={
                    "entity_kind": "task",
                    "entity_id": 42,
                    "action": "mark_done",
                    "payload": {},
                },
                response={
                    "result": {
                        "status": "ok",
                        "done": True,
                    }
                },
            ),
        )
