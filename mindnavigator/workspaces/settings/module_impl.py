"""Compatibility exports for settings workspace implementation."""

from __future__ import annotations

from .settings_workspace import SettingsWorkspace, get_database, is_network_database_path

__all__ = ["SettingsWorkspace", "get_database", "is_network_database_path"]
