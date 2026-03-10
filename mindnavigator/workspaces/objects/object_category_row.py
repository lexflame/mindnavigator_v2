"""ObjectCategoryRow class module for objects workspace."""

from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class ObjectCategoryRow:
    category: str

__all__ = ["ObjectCategoryRow"]
