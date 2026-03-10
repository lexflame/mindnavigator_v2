"""MindDrawLinkState class module for minddraw workspace."""

from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class MindDrawLinkState:
    """Serializable directional link between two nodes."""

    source_id: str
    target_id: str

__all__ = ["MindDrawLinkState"]
