from __future__ import annotations

from mindnavigator.main_window import normalize_enabled_workspace_ids


def test_normalize_enabled_workspace_ids_uses_defaults_on_empty_or_invalid() -> None:
    available = {"projects", "tasks", "notes"}

    assert normalize_enabled_workspace_ids("", available) == available
    assert normalize_enabled_workspace_ids("not-json", available) == available
    assert normalize_enabled_workspace_ids('{"a":1}', available) == available


def test_normalize_enabled_workspace_ids_filters_unknown_values() -> None:
    available = {"projects", "tasks", "notes"}

    result = normalize_enabled_workspace_ids('["tasks", "unknown", "notes", "tasks"]', available)

    assert result == {"tasks", "notes"}


def test_normalize_enabled_workspace_ids_falls_back_when_list_is_empty() -> None:
    available = {"projects", "tasks", "notes"}

    result = normalize_enabled_workspace_ids('[]', available)

    assert result == available
