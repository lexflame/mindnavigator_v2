"""HeaderRow class module for projects workspace."""

from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class HeaderRow:
    area: str

__all__ = ["HeaderRow"]
