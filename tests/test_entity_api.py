from __future__ import annotations

from datetime import date

import pytest

from mindnavigator.entity_api import (
    API_NAME,
    API_PROTOCOL_VERSION,
    API_SCHEMA_VERSION,
    CodexEntityAdapter,
    EntityApiError,
    EntityApiPool,
    EntityApiService,
    EntityNotFoundError,
)
from mindnavigator.storage import Database


def test_entity_api_pool_describe_returns_codex_compatible_contract() -> None:
    pool = EntityApiPool()

    description = pool.describe()

    assert description["service_name"] == "MindNavigator Entity API Pool"
    assert description["api_name"] == API_NAME
    assert description["protocol_version"] == API_PROTOCOL_VERSION
    assert description["schema_version"] == API_SCHEMA_VERSION
    assert description["codex_compatible"] is True
    assert "codex" in description["compatible_clients"]


def test_entity_api_pool_describe_includes_endpoint_inventory() -> None:
    pool = EntityApiPool()

    description = pool.describe()
    operation_names = [item["name"] for item in description["operations"]]

    assert operation_names == [
        "list_entities",
        "get_entity",
        "create_entity",
        "update_entity",
        "delete_entity",
        "execute_entity_action",
    ]
    assert description["handshake"]["connect_operation"] == "describe"
    assert "client_name" in description["handshake"]["required_client_fields"]


def test_entity_api_pool_describe_lists_supported_entity_kinds() -> None:
    pool = EntityApiPool()

    description = pool.describe()
    kinds = {item["kind"]: item for item in description["entity_kinds"]}

    assert {"task", "project", "note", "idea", "object", "map", "collection_item"} <= set(kinds)
    assert "mark_done" in kinds["task"]["execute_actions"]
    assert "title" in kinds["project"]["mutable_fields"]
    assert "preview" in kinds["note"]["mutable_fields"]


def test_entity_api_pool_connect_echoes_client_handshake() -> None:
    pool = EntityApiPool()

    payload = pool.connect(client_name="codex", client_version="2026.03", capabilities=["crud", "execute"])

    assert payload["connection"] == {
        "client_name": "codex",
        "client_version": "2026.03",
        "requested_capabilities": ["crud", "execute"],
        "accepted": True,
    }
    assert payload["examples"][0]["operation"] == "describe"
    assert payload["examples"][0]["response"]["codex_compatible"] is True


def test_entity_api_service_task_crud_round_trip(unique_temp_path) -> None:
    database = Database(path=unique_temp_path("entity_api_task", ".sqlite3"))
    service = EntityApiService(database=database)
    try:
        created = service.create_entity(
            "task",
            {
                "title": "API Task",
                "description": "initial",
                "day": "2026-03-02",
                "time_text": "09:15",
                "priority": "High",
            },
        )

        fetched = service.get_entity("task", created["id"])
        updated = service.update_entity(
            "task",
            created["id"],
            {
                "description": "updated",
                "done": True,
            },
        )
        listed = service.list_entities("task", filters={"id": created["id"]})
        deleted = service.delete_entity("task", created["id"])

        assert fetched["title"] == "API Task"
        assert updated["description"] == "updated"
        assert updated["done"] is True
        assert [item["id"] for item in listed] == [created["id"]]
        assert deleted == {"entity_kind": "task", "entity_id": created["id"], "deleted": True}
        with pytest.raises(EntityNotFoundError):
            service.get_entity("task", created["id"])
    finally:
        database.close()


def test_entity_api_service_project_create_update_delete(unique_temp_path) -> None:
    database = Database(path=unique_temp_path("entity_api_project", ".sqlite3"))
    service = EntityApiService(database=database)
    try:
        created = service.create_entity(
            "project",
            {
                "area": "API",
                "title": "API Project",
                "updated": "2026-03-02",
                "priority": "Medium",
            },
        )

        updated = service.update_entity(
            "project",
            created["id"],
            {
                "archived": True,
                "title": "API Project Updated",
            },
        )
        deleted = service.delete_entity("project", created["id"])

        assert created["area"] == "API"
        assert updated["archived"] is True
        assert updated["title"] == "API Project Updated"
        assert deleted["deleted"] is True
    finally:
        database.close()


def test_entity_api_service_note_create_and_update(unique_temp_path) -> None:
    database = Database(path=unique_temp_path("entity_api_note", ".sqlite3"))
    service = EntityApiService(database=database)
    try:
        created = service.create_entity(
            "note",
            {
                "title": "API Note",
                "preview": "line1",
                "tags": ["alpha", "beta"],
                "project": "Inbox",
                "favorite": True,
            },
        )
        updated = service.update_entity(
            "note",
            created["id"],
            {
                "preview": "line2",
                "tags": "beta,gamma",
            },
        )

        assert created["favorite"] is True
        assert updated["preview"] == "line2"
        assert updated["tags"] == ["beta", "gamma"]
    finally:
        database.close()


def test_entity_api_service_map_delete_requires_force(unique_temp_path) -> None:
    database = Database(path=unique_temp_path("entity_api_map", ".sqlite3"))
    service = EntityApiService(database=database)
    try:
        created = service.create_entity(
            "map",
            {
                "title": "API Map",
                "description": "desc",
                "project": "",
                "tiles_path": "tiles",
                "tiles_h": 2,
                "tiles_w": 3,
            },
        )

        with pytest.raises(EntityApiError):
            service.delete_entity("map", created["id"])

        deleted = service.delete_entity("map", created["id"], force=True)
        assert deleted["deleted"] is True
    finally:
        database.close()


def test_entity_api_service_reports_missing_and_unsupported_entities(unique_temp_path) -> None:
    database = Database(path=unique_temp_path("entity_api_errors", ".sqlite3"))
    service = EntityApiService(database=database)
    try:
        with pytest.raises(EntityApiError):
            service.list_entities("unknown-kind")
        with pytest.raises(EntityNotFoundError):
            service.get_entity("task", 999999)
    finally:
        database.close()


def test_entity_api_service_execute_actions_update_entities(unique_temp_path) -> None:
    database = Database(path=unique_temp_path("entity_api_execute", ".sqlite3"))
    service = EntityApiService(database=database)
    try:
        task = service.create_entity("task", {"title": "Exec Task", "day": "2026-03-02"})
        project = service.create_entity(
            "project",
            {"area": "API", "title": "Exec Project", "updated": "2026-03-02"},
        )
        note = service.create_entity("note", {"title": "Exec Note"})
        idea = service.create_entity("idea", {"title": "Exec Idea", "status": "inbox"})

        task_result = service.execute_entity_action("task", task["id"], "mark_done")
        project_result = service.execute_entity_action("project", project["id"], "archive")
        note_result = service.execute_entity_action("note", note["id"], "favorite")
        idea_result = service.execute_entity_action("idea", idea["id"], "promote")

        assert task_result["entity"]["done"] is True
        assert project_result["entity"]["archived"] is True
        assert note_result["entity"]["favorite"] is True
        assert idea_result["entity"]["status"] == "work"
    finally:
        database.close()


def test_entity_api_service_execute_rejects_unsupported_action(unique_temp_path) -> None:
    database = Database(path=unique_temp_path("entity_api_execute_errors", ".sqlite3"))
    service = EntityApiService(database=database)
    try:
        task = service.create_entity("task", {"title": "Exec Task", "day": "2026-03-02"})

        with pytest.raises(EntityApiError):
            service.execute_entity_action("task", task["id"], "archive")
    finally:
        database.close()


def test_codex_entity_adapter_handshake_and_proxy(unique_temp_path) -> None:
    database = Database(path=unique_temp_path("entity_api_adapter", ".sqlite3"))
    service = EntityApiService(database=database)
    adapter = CodexEntityAdapter(service=service, client_version="2026.03")
    try:
        handshake = adapter.handshake()
        created = adapter.create_entity("task", {"title": "Adapter Task", "day": "2026-03-02"})
        action_result = adapter.execute_entity_action("task", created["id"], "toggle_done")
        fetched = adapter.get_entity("task", created["id"])

        assert handshake["connection"]["client_name"] == "codex"
        assert handshake["connection"]["client_version"] == "2026.03"
        assert action_result["entity"]["done"] is True
        assert fetched["done"] is True
    finally:
        database.close()
