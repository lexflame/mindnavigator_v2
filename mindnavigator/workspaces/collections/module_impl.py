"""Compatibility exports for collections workspace implementation."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403
from ._entry_thumb_signals import _EntryThumbSignals
from ._entry_thumb_worker import _EntryThumbWorker
from .collection_media_preview_dialog import CollectionMediaPreviewDialog
from .collection_item_edit_dialog import CollectionItemEditDialog
from .collection_relation_dialog import CollectionRelationDialog
from .collections_workspace import CollectionsWorkspace

__all__ = [name for name in globals() if not name.startswith("__")]
