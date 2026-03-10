"""HeaderRow class module for tasks workspace."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

@dataclass(frozen=True)
class HeaderRow:
    day: date

__all__ = ["HeaderRow"]
