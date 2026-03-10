"""NoteCategoryRow class module for notes workspace."""

from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class NoteCategoryRow:
    category: str

__all__ = ["NoteCategoryRow"]
