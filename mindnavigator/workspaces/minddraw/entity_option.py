"""EntityOption class module for minddraw workspace."""

from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class EntityOption:
    """One selectable entity from another workspace."""

    kind: str
    entity_id: int
    title: str
    subtitle: str = ""

__all__ = ["EntityOption"]
