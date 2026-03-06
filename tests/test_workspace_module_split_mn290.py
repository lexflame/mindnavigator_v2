from __future__ import annotations

from mindnavigator.workspaces.tasks import TasksWorkspace as TasksWorkspaceNew
from mindnavigator.workspaces.tasks_workspace import TasksWorkspace as TasksWorkspaceLegacy
from mindnavigator.workspaces.projects import ProjectsWorkspace as ProjectsWorkspaceNew
from mindnavigator.workspaces.projects_workspace import ProjectsWorkspace as ProjectsWorkspaceLegacy
from mindnavigator.workspaces.collections import CollectionsWorkspace as CollectionsWorkspaceNew
from mindnavigator.workspaces.collections_workspace import CollectionsWorkspace as CollectionsWorkspaceLegacy
from mindnavigator.workspaces.maps import MapsListWorkspace as MapsListWorkspaceNew
from mindnavigator.workspaces.maps_workspace import MapsListWorkspace as MapsListWorkspaceLegacy
from mindnavigator.workspaces.notes import NoteWorkspace as NoteWorkspaceNew
from mindnavigator.workspaces.notes_workspace import NoteWorkspace as NoteWorkspaceLegacy
from mindnavigator.workspaces.files import FileWorkspace as FileWorkspaceNew
from mindnavigator.workspaces.files_workspace import FileWorkspace as FileWorkspaceLegacy
from mindnavigator.workspaces.objects import ObjectWorkspace as ObjectWorkspaceNew
from mindnavigator.workspaces.objects_workspace import ObjectWorkspace as ObjectWorkspaceLegacy
from mindnavigator.workspaces.characters import CharactersWorkspace as CharactersWorkspaceNew
from mindnavigator.workspaces.characters_workspace import CharactersWorkspace as CharactersWorkspaceLegacy
from mindnavigator.workspaces.ideas import IdeasWorkspace as IdeasWorkspaceNew
from mindnavigator.workspaces.ideas_workspace import IdeasWorkspace as IdeasWorkspaceLegacy
from mindnavigator.workspaces.purchases import PurchasesWorkspace as PurchasesWorkspaceNew
from mindnavigator.workspaces.purchases_workspace import PurchasesWorkspace as PurchasesWorkspaceLegacy
from mindnavigator.workspaces.settings import SettingsWorkspace as SettingsWorkspaceNew
from mindnavigator.workspaces.settings_workspace import SettingsWorkspace as SettingsWorkspaceLegacy


def test_workspace_split_keeps_legacy_import_paths() -> None:
    assert TasksWorkspaceNew is TasksWorkspaceLegacy
    assert ProjectsWorkspaceNew is ProjectsWorkspaceLegacy
    assert CollectionsWorkspaceNew is CollectionsWorkspaceLegacy
    assert MapsListWorkspaceNew is MapsListWorkspaceLegacy
    assert NoteWorkspaceNew is NoteWorkspaceLegacy
    assert FileWorkspaceNew is FileWorkspaceLegacy
    assert ObjectWorkspaceNew is ObjectWorkspaceLegacy
    assert CharactersWorkspaceNew is CharactersWorkspaceLegacy
    assert IdeasWorkspaceNew is IdeasWorkspaceLegacy
    assert PurchasesWorkspaceNew is PurchasesWorkspaceLegacy
    assert SettingsWorkspaceNew is SettingsWorkspaceLegacy
