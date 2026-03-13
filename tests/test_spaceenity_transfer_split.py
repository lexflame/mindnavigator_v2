from __future__ import annotations

import importlib

import mindnavigator.constants as legacy_constants
from mindnavigator.spaceenity.constants import APP_NAME
from mindnavigator.spaceenity.db_migrations import MigrationStep
from mindnavigator.spaceenity.entity_api import EntityApiService
from mindnavigator.spaceenity.http_client import HttpClientError
from mindnavigator.spaceenity.i18n import DEFAULT_LANGUAGE
from mindnavigator.spaceenity.i18n import normalize_language_code
from mindnavigator.spaceenity.marker_types import marker_type_options
from mindnavigator.spaceenity.resources import resource_path
from mindnavigator.spaceenity.update_service import UpdateService


def test_spaceenity_packages_export_expected_symbols() -> None:
    assert legacy_constants.APP_NAME == APP_NAME
    assert MigrationStep is not None
    assert EntityApiService is not None
    assert HttpClientError is not None
    assert normalize_language_code(DEFAULT_LANGUAGE) == DEFAULT_LANGUAGE
    assert resource_path is not None
    assert marker_type_options is not None
    assert UpdateService is not None


def test_spaceenity_transfer_split_updates_internal_imports() -> None:
    package_main = importlib.import_module("mindnavigator.__main__")
    settings_workspace = importlib.import_module("mindnavigator.workspaces.settings.settings_workspace")
    maps_shared = importlib.import_module("mindnavigator.workspaces.maps._shared")
    purchases_shared = importlib.import_module("mindnavigator.workspaces.purchases._shared")

    assert package_main.APP_NAME == APP_NAME
    assert settings_workspace.UpdateService is UpdateService
    assert maps_shared.resource_path is resource_path
    assert maps_shared.marker_type_options is marker_type_options
    assert purchases_shared.HttpClient.__module__ == "mindnavigator.spaceenity.http_client"
