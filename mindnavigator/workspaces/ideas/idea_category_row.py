"""IdeaCategoryRow class module for ideas workspace."""

from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class IdeaCategoryRow:
    category: str

__all__ = ["IdeaCategoryRow"]
