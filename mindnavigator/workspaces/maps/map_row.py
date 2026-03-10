"""MapRow class module for maps workspace."""

from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)
class MapRow:
    id: int
    title: str
    description: str
    project: str
    tiles_path: str
    tiles_h: int
    tiles_w: int

__all__ = ["MapRow"]
