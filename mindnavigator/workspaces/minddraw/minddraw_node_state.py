"""MindDrawNodeState class module for minddraw workspace."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class MindDrawNodeState:
    """Serializable node payload for canvas persistence."""

    node_id: str
    title: str
    x: float
    y: float
    entity_kind: str = ""
    entity_id: Optional[int] = None
    entity_title: str = ""

__all__ = ["MindDrawNodeState"]
