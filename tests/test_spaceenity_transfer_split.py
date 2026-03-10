from __future__ import annotations

import importlib

import mindnavigator.constants as legacy_constants
import mindnavigator.i18n as legacy_i18n
import mindnavigator.resources as legacy_resources
from mindnavigator.db_migrations import MigrationStep as LegacyMigrationStep
from mindnavigator.entity_api import EntityApiService as LegacyEntityApiService
from mindnavigator.http_client import HttpClientError as LegacyHttpClientError
from mindnavigator.marker_types import marker_type_options as legacy_marker_type_options
from mindnavigator.spaceenity.constants import APP_NAME
from mindnavigator.spaceenity.db_migrations import MigrationStep
from mindnavigator.spaceenity.entity_api import EntityApiService
from mindnavigator.spaceenity.http_client import HttpClientError
from mindnavigator.spaceenity.i18n import normalize_language_code
from mindnavigator.spaceenity.marker_types import marker_type_options
from mindnavigator.spaceenity.resources import resource_path
from mindnavigator.spaceenity.update_service import UpdateService
from mindnavigator.update_service import UpdateService as LegacyUpdateService


def test_spaceenity_transfer_split_keeps_legacy_import_paths() -> None:
    assert legacy_constants.APP_NAME == APP_NAME
    assert LegacyMigrationStep is MigrationStep
    assert LegacyEntityApiService is EntityApiService
    assert LegacyHttpClientError is HttpClientError
    assert legacy_i18n.normalize_language_code is normalize_language_code
    assert legacy_resources.resource_path is resource_path
    assert legacy_marker_type_options is marker_type_options
    assert LegacyUpdateService is UpdateService


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
