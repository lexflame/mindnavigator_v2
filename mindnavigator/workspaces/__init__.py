"""Рабочие области (workspaces) приложения.

Входные данные:
    Нет. Модуль агрегирует классы рабочих областей.

Выходные данные:
    Классы рабочих областей для импорта.
"""

from .projects_workspace import ProjectsWorkspace
from .collections_workspace import CollectionsWorkspace
from .maps_workspace import MapsListWorkspace
from .notes_workspace import NoteWorkspace
from .files_workspace import FileWorkspace
from .objects_workspace import ObjectWorkspace
from .characters_workspace import CharactersWorkspace
from .ideas_workspace import IdeasWorkspace
from .purchases_workspace import PurchasesWorkspace
