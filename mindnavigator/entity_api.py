from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from datetime import date, datetime
from typing import Any, Iterable, Mapping

from .storage import Database, get_database

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


class EntityApiError(RuntimeError):
    """Raised when an entity API request cannot be completed."""


class EntityNotFoundError(EntityApiError):
    """Raised when a requested entity is missing."""


_IDEA_PROMOTION_FLOW = ("inbox", "work", "ripe", "done")


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
                mutable_fields=("title", "area", "updated", "priority", "archived", "parent_project_id"),
                execute_actions=("archive", "unarchive"),
            ),
            EntityKindSpec(
                kind="note",
                title="Note",
                identity_field="id",
                list_fields=("id", "title", "project", "favorite", "locked"),
                mutable_fields=("title", "preview", "tags"),
                execute_actions=("favorite", "unfavorite", "lock", "unlock"),
            ),
            EntityKindSpec(
                kind="idea",
                title="Idea",
                identity_field="id",
                list_fields=("id", "title", "status", "type", "project_id"),
                mutable_fields=("title", "summary", "body_md", "type", "status", "value_score", "effort_score", "project_id", "source"),
                execute_actions=("promote", "archive", "unarchive"),
            ),
            EntityKindSpec(
                kind="object",
                title="Object",
                identity_field="id",
                list_fields=("id", "title", "catalog", "object_type", "status"),
                mutable_fields=("title", "catalog", "object_type", "status", "description"),
                execute_actions=(),
            ),
            EntityKindSpec(
                kind="map",
                title="Map",
                identity_field="id",
                list_fields=("id", "title", "project", "tiles_path", "tiles_h", "tiles_w"),
                mutable_fields=("title", "description", "project", "tiles_path", "tiles_h", "tiles_w"),
                execute_actions=(),
            ),
            EntityKindSpec(
                kind="collection_item",
                title="Collection Item",
                identity_field="id",
                list_fields=("id", "title", "entity_type", "category_id", "topic"),
                mutable_fields=("title", "entity_type", "category_id", "topic", "image_url", "source_url", "description"),
                execute_actions=(),
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


class EntityApiService(EntityApiPool):
    """Provides list/get/create/update/delete operations for supported entity kinds."""

    def __init__(
        self,
        *,
        database: Database | None = None,
        service_name: str = DEFAULT_SERVICE_NAME,
        compatible_clients: tuple[str, ...] = DEFAULT_COMPATIBLE_CLIENTS,
    ) -> None:
        super().__init__(service_name=service_name, compatible_clients=compatible_clients)
        self._db = database or get_database()

    def list_entities(
        self,
        entity_kind: str,
        *,
        filters: Mapping[str, object] | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        records = [self._serialize_entity(item) for item in self._fetch_entities(entity_kind)]
        if filters:
            normalized_filters = {str(key): self._serialize_value(value) for key, value in filters.items()}
            records = [
                item
                for item in records
                if all(item.get(key) == value for key, value in normalized_filters.items())
            ]
        offset = max(0, int(offset or 0))
        if limit is not None:
            return records[offset : offset + max(0, int(limit))]
        return records[offset:]

    def get_entity(self, entity_kind: str, entity_id: int) -> dict[str, Any]:
        entity = self._get_entity_record(entity_kind, entity_id)
        if entity is None:
            raise EntityNotFoundError(f"Entity not found: {entity_kind}:{entity_id}")
        return self._serialize_entity(entity)

    def create_entity(self, entity_kind: str, payload: Mapping[str, object]) -> dict[str, Any]:
        kind = self._normalize_kind(entity_kind)
        data = dict(payload)
        if kind == "task":
            entity = self._db.create_task(
                title=self._require_string(data, "title"),
                description=self._string(data.get("description")),
                day=self._date_value(data.get("day"), date.today()),
                time_text=self._string(data.get("time_text")),
                priority=self._string(data.get("priority"), "Medium"),
                project_id=self._optional_int(data.get("project_id")),
                parent_id=self._optional_int(data.get("parent_id")),
                recurrence_kind=self._string(data.get("recurrence_kind")),
                recurrence_interval=self._int_value(data.get("recurrence_interval"), 1),
                marker_color=self._string(data.get("marker_color")),
                marker_theme=self._string(data.get("marker_theme")),
            )
        elif kind == "project":
            entity = self._db.create_project(
                area=self._require_string(data, "area"),
                title=self._require_string(data, "title"),
                updated=self._date_value(data.get("updated"), date.today()),
                priority=self._string(data.get("priority"), "Medium"),
                archived=self._bool_value(data.get("archived"), False),
                parent_project_id=self._optional_int(data.get("parent_project_id")),
                default_task_priority=self._string(data.get("default_task_priority")),
                force_recurrence_kind=self._string(data.get("force_recurrence_kind")),
                linked_map_id=self._optional_int(data.get("linked_map_id")),
                linked_note_id=self._optional_int(data.get("linked_note_id")),
                linked_object_id=self._optional_int(data.get("linked_object_id")),
                marker_color=self._string(data.get("marker_color")),
                marker_theme=self._string(data.get("marker_theme")),
            )
        elif kind == "note":
            entity = self._db.create_note(
                title=self._require_string(data, "title"),
                preview=self._string(data.get("preview")),
                tags=self._string_list(data.get("tags")),
                project=self._string(data.get("project")),
                favorite=self._bool_value(data.get("favorite"), False),
                attachment=self._bool_value(data.get("attachment"), False),
                locked=self._bool_value(data.get("locked"), False),
            )
        elif kind == "idea":
            entity = self._db.create_idea(
                title=self._require_string(data, "title"),
                summary=self._string(data.get("summary")),
                body_md=self._string(data.get("body_md")),
                idea_type=self._string(data.get("type"), "other"),
                status=self._string(data.get("status"), "inbox"),
                value_score=self._int_value(data.get("value_score"), 3),
                effort_score=self._int_value(data.get("effort_score"), 3),
                project_id=self._optional_int(data.get("project_id")),
                source=self._string(data.get("source")),
            )
        elif kind == "object":
            entity = self._db.create_object(
                title=self._require_string(data, "title"),
                catalog=self._string(data.get("catalog")),
                object_type=self._string(data.get("object_type")),
                status=self._string(data.get("status")),
                description=self._string(data.get("description")),
            )
        elif kind == "map":
            entity = self._db.create_map(
                title=self._require_string(data, "title"),
                description=self._string(data.get("description")),
                project=self._string(data.get("project")),
                tiles_path=self._string(data.get("tiles_path")),
                tiles_h=self._int_value(data.get("tiles_h"), 1),
                tiles_w=self._int_value(data.get("tiles_w"), 1),
            )
        elif kind == "collection_item":
            entity = self._db.create_collection_item(
                title=self._require_string(data, "title"),
                entity_type=self._string(data.get("entity_type"), "other"),
                category_id=self._optional_int(data.get("category_id")),
                topic=self._string(data.get("topic")),
                image_url=self._string(data.get("image_url")),
                source_url=self._string(data.get("source_url")),
                description=self._string(data.get("description")),
                source_folder_path=self._string(data.get("source_folder_path")),
                import_options_json=self._string(data.get("import_options_json")),
            )
        else:
            raise EntityApiError(f"Unsupported entity kind: {entity_kind}")
        return self._serialize_entity(entity)

    def update_entity(self, entity_kind: str, entity_id: int, payload: Mapping[str, object]) -> dict[str, Any]:
        kind = self._normalize_kind(entity_kind)
        data = dict(payload)
        current = self._get_entity_record(kind, entity_id)
        if current is None:
            raise EntityNotFoundError(f"Entity not found: {kind}:{entity_id}")
        if kind == "task":
            entity = self._db.update_task(
                entity_id,
                title=self._string(data.get("title"), current.title),
                description=self._string(data.get("description"), current.description),
                day=self._date_value(data.get("day"), current.day),
                time_text=self._string(data.get("time_text"), current.time_text),
                priority=self._string(data.get("priority"), current.priority),
                done=self._bool_value(data.get("done"), current.done),
                project_id=self._optional_int(data.get("project_id"), current.project_id),
                parent_id=self._optional_int(data.get("parent_id"), current.parent_id),
                recurrence_kind=self._string(data.get("recurrence_kind"), current.recurrence_kind),
                recurrence_interval=self._int_value(data.get("recurrence_interval"), current.recurrence_interval),
                marker_color=self._string(data.get("marker_color"), current.marker_color),
                marker_theme=self._string(data.get("marker_theme"), current.marker_theme),
            )
        elif kind == "project":
            entity = self._db.update_project(
                entity_id,
                area=self._string(data.get("area"), current.area),
                title=self._string(data.get("title"), current.title),
                updated=self._date_value(data.get("updated"), current.updated),
                priority=self._string(data.get("priority"), current.priority),
                archived=self._bool_value(data.get("archived"), current.archived),
                parent_project_id=self._optional_int(data.get("parent_project_id"), current.parent_project_id),
                sort_order=self._optional_int(data.get("sort_order"), current.sort_order),
                default_task_priority=self._string(data.get("default_task_priority"), current.default_task_priority),
                force_recurrence_kind=self._string(data.get("force_recurrence_kind"), current.force_recurrence_kind),
                linked_map_id=self._optional_int(data.get("linked_map_id"), current.linked_map_id),
                linked_note_id=self._optional_int(data.get("linked_note_id"), current.linked_note_id),
                linked_object_id=self._optional_int(data.get("linked_object_id"), current.linked_object_id),
                marker_color=self._string(data.get("marker_color"), current.marker_color),
                marker_theme=self._string(data.get("marker_theme"), current.marker_theme),
            )
        elif kind == "note":
            entity = self._db.update_note(
                entity_id,
                title=self._string(data.get("title"), current.title),
                preview=self._string(data.get("preview"), current.preview),
                tags=self._string_list(data.get("tags"), current.tags),
            )
        elif kind == "idea":
            entity = self._db.update_idea(
                entity_id,
                title=self._string(data.get("title"), current.title),
                summary=self._string(data.get("summary"), current.summary),
                body_md=self._string(data.get("body_md"), current.body_md),
                idea_type=self._string(data.get("type"), current.type),
                status=self._string(data.get("status"), current.status),
                value_score=self._int_value(data.get("value_score"), current.value_score),
                effort_score=self._int_value(data.get("effort_score"), current.effort_score),
                project_id=self._optional_int(data.get("project_id"), current.project_id),
                source=self._string(data.get("source"), current.source),
            )
        elif kind == "object":
            entity = self._db.update_object(
                entity_id,
                title=self._string(data.get("title"), current.title),
                catalog=self._string(data.get("catalog"), current.catalog),
                object_type=self._string(data.get("object_type"), current.object_type),
                status=self._string(data.get("status"), current.status),
                description=self._string(data.get("description"), current.description),
            )
        elif kind == "map":
            entity = self._db.update_map(
                entity_id,
                title=self._string(data.get("title"), current.title),
                description=self._string(data.get("description"), current.description),
                project=self._string(data.get("project"), current.project),
                tiles_path=self._string(data.get("tiles_path"), current.tiles_path),
                tiles_h=self._int_value(data.get("tiles_h"), current.tiles_h),
                tiles_w=self._int_value(data.get("tiles_w"), current.tiles_w),
            )
        elif kind == "collection_item":
            entity = self._db.update_collection_item(
                entity_id,
                title=self._string(data.get("title"), current.title),
                entity_type=self._string(data.get("entity_type"), current.entity_type),
                category_id=self._optional_int(data.get("category_id"), current.category_id),
                topic=self._string(data.get("topic"), current.topic),
                image_url=self._string(data.get("image_url"), current.image_url),
                source_url=self._string(data.get("source_url"), current.source_url),
                description=self._string(data.get("description"), current.description),
                source_folder_path=self._string(data.get("source_folder_path"), current.source_folder_path),
                import_options_json=self._string(data.get("import_options_json"), current.import_options_json),
            )
        else:
            raise EntityApiError(f"Unsupported entity kind: {entity_kind}")
        return self._serialize_entity(entity)

    def delete_entity(self, entity_kind: str, entity_id: int, *, force: bool = False) -> dict[str, Any]:
        kind = self._normalize_kind(entity_kind)
        if self._get_entity_record(kind, entity_id) is None:
            raise EntityNotFoundError(f"Entity not found: {kind}:{entity_id}")
        if kind == "task":
            self._db.delete_task(entity_id)
        elif kind == "project":
            self._db.delete_project(entity_id)
        elif kind == "note":
            self._db.delete_note(entity_id)
        elif kind == "idea":
            self._db.delete_idea(entity_id)
        elif kind == "object":
            self._db.delete_object(entity_id)
        elif kind == "collection_item":
            self._db.delete_collection_item(entity_id)
        elif kind == "map":
            if not force:
                raise EntityApiError("Map deletion requires force=True because dependent markers/overlays may exist.")
            self._db.delete_map(entity_id)
        else:
            raise EntityApiError(f"Unsupported entity kind: {entity_kind}")
        return {"entity_kind": kind, "entity_id": int(entity_id), "deleted": True}

    def execute_entity_action(
        self,
        entity_kind: str,
        entity_id: int,
        action: str,
        payload: Mapping[str, object] | None = None,
    ) -> dict[str, Any]:
        kind = self._normalize_kind(entity_kind)
        current = self._get_entity_record(kind, entity_id)
        if current is None:
            raise EntityNotFoundError(f"Entity not found: {kind}:{entity_id}")
        normalized_action = (action or "").strip().lower()
        action_payload = self._serialize_value(dict(payload or {}))
        if kind == "task":
            if normalized_action == "mark_done":
                entity = self._update_task_done(current, True)
            elif normalized_action == "mark_pending":
                entity = self._update_task_done(current, False)
            elif normalized_action == "toggle_done":
                entity = self._update_task_done(current, not bool(current.done))
            else:
                raise EntityApiError(f"Unsupported action '{action}' for entity kind '{kind}'.")
        elif kind == "project":
            if normalized_action not in {"archive", "unarchive"}:
                raise EntityApiError(f"Unsupported action '{action}' for entity kind '{kind}'.")
            self._db.set_project_archived(int(entity_id), normalized_action == "archive")
            entity = self.get_entity(kind, int(entity_id))
        elif kind == "note":
            if normalized_action == "favorite":
                entity = self._serialize_entity(self._db.set_note_favorite(int(entity_id), True))
            elif normalized_action == "unfavorite":
                entity = self._serialize_entity(self._db.set_note_favorite(int(entity_id), False))
            elif normalized_action == "lock":
                entity = self._serialize_entity(self._db.set_note_locked(int(entity_id), True))
            elif normalized_action == "unlock":
                entity = self._serialize_entity(self._db.set_note_locked(int(entity_id), False))
            else:
                raise EntityApiError(f"Unsupported action '{action}' for entity kind '{kind}'.")
        elif kind == "idea":
            if normalized_action == "promote":
                entity = self._promote_idea(current)
            elif normalized_action in {"archive", "unarchive"}:
                self._db.set_idea_archived(int(entity_id), normalized_action == "archive")
                entity = self.get_entity(kind, int(entity_id))
            else:
                raise EntityApiError(f"Unsupported action '{action}' for entity kind '{kind}'.")
        else:
            raise EntityApiError(f"Entity kind '{kind}' does not support execute actions.")
        return {
            "entity_kind": kind,
            "entity_id": int(entity_id),
            "action": normalized_action,
            "entity": entity,
            "payload": action_payload,
        }

    def _fetch_entities(self, entity_kind: str) -> list[Any]:
        kind = self._normalize_kind(entity_kind)
        if kind == "task":
            return list(self._db.fetch_tasks())
        if kind == "project":
            return list(self._db.fetch_projects())
        if kind == "note":
            return list(self._db.fetch_notes())
        if kind == "idea":
            return list(self._db.fetch_ideas())
        if kind == "object":
            return list(self._db.fetch_objects())
        if kind == "map":
            return list(self._db.fetch_maps())
        if kind == "collection_item":
            return list(self._db.fetch_collection_items())
        raise EntityApiError(f"Unsupported entity kind: {entity_kind}")

    def _get_entity_record(self, entity_kind: str, entity_id: int) -> Any | None:
        kind = self._normalize_kind(entity_kind)
        entity_id = int(entity_id)
        if kind == "idea":
            return self._db.get_idea(entity_id)
        for item in self._fetch_entities(kind):
            if int(getattr(item, "id", 0)) == entity_id:
                return item
        return None

    def _normalize_kind(self, entity_kind: str) -> str:
        kind = (entity_kind or "").strip().lower()
        supported = {item.kind for item in self._entity_kinds}
        if kind not in supported:
            raise EntityApiError(f"Unsupported entity kind: {entity_kind}")
        return kind

    def _update_task_done(self, current: Any, done: bool) -> dict[str, Any]:
        self._db.set_task_done(int(current.id), bool(done))
        updated = self._get_entity_record("task", int(current.id))
        if updated is None:
            raise EntityNotFoundError(f"Entity not found: task:{current.id}")
        return self._serialize_entity(updated)

    def _promote_idea(self, current: Any) -> dict[str, Any]:
        status = str(getattr(current, "status", "") or "").strip().lower()
        if status in _IDEA_PROMOTION_FLOW:
            next_index = min(_IDEA_PROMOTION_FLOW.index(status) + 1, len(_IDEA_PROMOTION_FLOW) - 1)
            next_status = _IDEA_PROMOTION_FLOW[next_index]
        else:
            next_status = _IDEA_PROMOTION_FLOW[0]
        entity = self._db.update_idea(
            int(current.id),
            title=str(current.title),
            summary=str(current.summary),
            body_md=str(current.body_md),
            idea_type=str(current.type),
            status=next_status,
            value_score=int(current.value_score),
            effort_score=int(current.effort_score),
            project_id=current.project_id,
            source=str(current.source),
        )
        return self._serialize_entity(entity)

    @staticmethod
    def _serialize_entity(entity: Any) -> dict[str, Any]:
        if is_dataclass(entity):
            payload = asdict(entity)
        elif isinstance(entity, Mapping):
            payload = dict(entity)
        else:
            raise EntityApiError("Unsupported entity payload for serialization.")
        return {str(key): EntityApiService._serialize_value(value) for key, value in payload.items()}

    @staticmethod
    def _serialize_value(value: Any) -> Any:
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, list):
            return [EntityApiService._serialize_value(item) for item in value]
        if isinstance(value, tuple):
            return [EntityApiService._serialize_value(item) for item in value]
        if isinstance(value, dict):
            return {str(key): EntityApiService._serialize_value(item) for key, item in value.items()}
        return value

    @staticmethod
    def _require_string(payload: Mapping[str, object], key: str) -> str:
        value = EntityApiService._string(payload.get(key))
        if not value:
            raise EntityApiError(f"Field '{key}' is required.")
        return value

    @staticmethod
    def _string(value: object, default: str = "") -> str:
        if value is None:
            return default
        return str(value).strip()

    @staticmethod
    def _string_list(value: object, default: Iterable[str] | None = None) -> list[str]:
        if value is None:
            return [str(item).strip() for item in (default or []) if str(item).strip()]
        if isinstance(value, str):
            items = [part.strip() for part in value.split(",")]
            return [item for item in items if item]
        if isinstance(value, Iterable):
            result = []
            for item in value:
                item_text = str(item).strip()
                if item_text:
                    result.append(item_text)
            return result
        raise EntityApiError("List field must be a sequence of strings.")

    @staticmethod
    def _bool_value(value: object, default: bool = False) -> bool:
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        text = str(value).strip().lower()
        if text in {"1", "true", "yes", "on"}:
            return True
        if text in {"0", "false", "no", "off", ""}:
            return False
        raise EntityApiError(f"Cannot parse boolean value: {value!r}")

    @staticmethod
    def _int_value(value: object, default: int = 0) -> int:
        if value is None or value == "":
            return int(default)
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise EntityApiError(f"Cannot parse integer value: {value!r}") from exc

    @staticmethod
    def _optional_int(value: object, default: int | None = None) -> int | None:
        if value is None or value == "":
            return default
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise EntityApiError(f"Cannot parse optional integer value: {value!r}") from exc

    @staticmethod
    def _date_value(value: object, default: date) -> date:
        if value is None or value == "":
            return default
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        if isinstance(value, datetime):
            return value.date()
        try:
            return date.fromisoformat(str(value))
        except ValueError as exc:
            raise EntityApiError(f"Cannot parse date value: {value!r}") from exc


class CodexEntityAdapter:
    """Codex-friendly wrapper that performs a compatibility handshake before each call."""

    def __init__(
        self,
        service: EntityApiService | None = None,
        client_version: str = API_PROTOCOL_VERSION,
    ) -> None:
        self._service = service or EntityApiService()
        self._client_version = client_version

    def handshake(self) -> dict[str, Any]:
        connection = self._service.connect(
            client_name="codex",
            client_version=self._client_version,
            capabilities=["crud", "execute"],
        )
        if not connection.get("codex_compatible"):
            raise EntityApiError("Entity API service is not compatible with Codex.")
        return connection

    def list_entities(
        self,
        entity_kind: str,
        *,
        filters: Mapping[str, object] | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        self.handshake()
        return self._service.list_entities(entity_kind, filters=filters, limit=limit, offset=offset)

    def get_entity(self, entity_kind: str, entity_id: int) -> dict[str, Any]:
        self.handshake()
        return self._service.get_entity(entity_kind, entity_id)

    def create_entity(self, entity_kind: str, payload: Mapping[str, object]) -> dict[str, Any]:
        self.handshake()
        return self._service.create_entity(entity_kind, payload)

    def update_entity(self, entity_kind: str, entity_id: int, payload: Mapping[str, object]) -> dict[str, Any]:
        self.handshake()
        return self._service.update_entity(entity_kind, entity_id, payload)

    def delete_entity(self, entity_kind: str, entity_id: int, *, force: bool = False) -> dict[str, Any]:
        self.handshake()
        return self._service.delete_entity(entity_kind, entity_id, force=force)

    def execute_entity_action(
        self,
        entity_kind: str,
        entity_id: int,
        action: str,
        payload: Mapping[str, object] | None = None,
    ) -> dict[str, Any]:
        self.handshake()
        return self._service.execute_entity_action(entity_kind, entity_id, action, payload)
