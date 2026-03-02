from __future__ import annotations

from mindnavigator.entity_api import (
    API_NAME,
    API_PROTOCOL_VERSION,
    API_SCHEMA_VERSION,
    EntityApiPool,
)


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
