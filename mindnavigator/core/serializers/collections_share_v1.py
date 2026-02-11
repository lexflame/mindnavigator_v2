"""Import/export helpers for collections share payload v1."""

from __future__ import annotations

import json
from typing import Any

from mindnavigator.core.models.collection_item import CollectionItem

SCHEMA_NAME = "collections_share_v1"


def export_collections_share_v1(items: list[CollectionItem]) -> str:
    """Serialize collection items to share JSON payload."""
    payload = {
        "schema": SCHEMA_NAME,
        "items": [item.to_dict() for item in items],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def import_collections_share_v1(raw_json: str) -> list[CollectionItem]:
    """Deserialize collection items from share JSON payload.

    Unknown fields are ignored. Unsupported schema returns empty list.
    """
    try:
        payload: dict[str, Any] = json.loads(raw_json)
    except json.JSONDecodeError:
        return []
    if payload.get("schema") != SCHEMA_NAME:
        return []
    rows = payload.get("items")
    if not isinstance(rows, list):
        return []

    items: list[CollectionItem] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            items.append(CollectionItem.from_dict(row))
        except ValueError:
            continue
    return items
