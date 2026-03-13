from __future__ import annotations

import importlib


def test_workspace_packages_expose_public_workspaces() -> None:
    tasks_module = importlib.import_module("mindnavigator.workspaces.tasks")
    projects_module = importlib.import_module("mindnavigator.workspaces.projects")
    collections_module = importlib.import_module("mindnavigator.workspaces.collections")
    maps_module = importlib.import_module("mindnavigator.workspaces.maps")
    notes_module = importlib.import_module("mindnavigator.workspaces.notes")
    files_module = importlib.import_module("mindnavigator.workspaces.files")
    objects_module = importlib.import_module("mindnavigator.workspaces.objects")
    characters_module = importlib.import_module("mindnavigator.workspaces.characters")
    ideas_module = importlib.import_module("mindnavigator.workspaces.ideas")
    purchases_module = importlib.import_module("mindnavigator.workspaces.purchases")
    settings_module = importlib.import_module("mindnavigator.workspaces.settings")

    assert tasks_module.TasksWorkspace is not None
    assert projects_module.ProjectsWorkspace is not None
    assert collections_module.CollectionsWorkspace is not None
    assert maps_module.MapsListWorkspace is not None
    assert notes_module.NoteWorkspace is not None
    assert files_module.FileWorkspace is not None
    assert objects_module.ObjectWorkspace is not None
    assert characters_module.CharactersWorkspace is not None
    assert ideas_module.IdeasWorkspace is not None
    assert purchases_module.PurchasesWorkspace is not None
    assert settings_module.SettingsWorkspace is not None
