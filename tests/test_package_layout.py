from __future__ import annotations

import importlib
from pathlib import Path


def test_package_roots_do_not_contain_python_files() -> None:
    assert sorted(path.name for path in Path("mindnavigator").glob("*.py")) == []
    assert sorted(path.name for path in Path("mindnavigator/workspaces").glob("*.py")) == []


def test_workspaces_root_does_not_keep_legacy_workspace_alias_dirs() -> None:
    legacy_dirs = {
        "characters_workspace",
        "collections_workspace",
        "csv_workspace_transfer",
        "files_workspace",
        "ideas_workspace",
        "maps_workspace",
        "minddraw_workspace",
        "notes_workspace",
        "objects_workspace",
        "projects_workspace",
        "purchases_workspace",
        "settings_workspace",
        "tasks_workspace",
    }

    assert not legacy_dirs.intersection({path.name for path in Path("mindnavigator/workspaces").iterdir() if path.is_dir()})


def test_namespace_package_layout_keeps_submodule_imports() -> None:
    spaceenity_i18n = importlib.import_module("mindnavigator.spaceenity.i18n")
    main_window = importlib.import_module("mindnavigator.window.collections.main_window")
    tasks_workspace = importlib.import_module("mindnavigator.workspaces.tasks")
    csv_transfer = importlib.import_module("mindnavigator.workspaces.csv_transfer")

    assert spaceenity_i18n.normalize_language_code is not None
    assert main_window.MainWindow is not None
    assert tasks_workspace.TasksWorkspace is not None
    assert csv_transfer.import_tasks_rows is not None


def test_root_does_not_keep_legacy_transfer_alias_dirs() -> None:
    legacy_dirs = {
        "collections_importer",
        "csv_transfer",
        "db_migrations",
        "entity_api",
        "http_client",
        "i18n",
        "main_window",
        "marker_types",
        "resources",
        "shop_parsers",
        "shop_parsing",
        "sprint_classification",
        "sprint_composer",
        "sprint_parser",
        "update_service",
        "windowing",
    }

    assert not legacy_dirs.intersection({path.name for path in Path("mindnavigator").iterdir() if path.is_dir()})
