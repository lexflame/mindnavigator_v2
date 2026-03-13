"""Compatibility exports for dossier workspace implementation."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403
from .dossier_item_delegate import DossierItemDelegate
from .dossier_list_model import DossierListModel
from .dossier_roles import DossierRoles
from .dossier_workspace import DossierWorkspace

__all__ = [name for name in globals() if not name.startswith("__")]
