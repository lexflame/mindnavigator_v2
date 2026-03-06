"""Рабочие области (workspaces) приложения.

Входные данные:
    Нет. Модуль агрегирует классы рабочих областей.

Выходные данные:
    Классы рабочих областей для импорта.
"""

from .projects import ProjectsWorkspace
from .collections import CollectionsWorkspace
from .maps import MapsListWorkspace
from .notes import NoteWorkspace
from .files import FileWorkspace
from .objects import ObjectWorkspace
from .characters import CharactersWorkspace
from .minddraw import MindDrawWorkspace
from .ideas import IdeasWorkspace
from .purchases import PurchasesWorkspace
