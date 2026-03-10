"""ObjectRow class module for objects workspace."""

from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class ObjectRow:
    id: int
    title: str
    catalog: str
    object_type: str
    status: str
    description: str

__all__ = ["ObjectRow"]
