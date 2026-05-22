"""HeaderRow class module for tasks workspace."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

@dataclass(frozen=True)
class HeaderRow:
    day: date
    total_minutes: int = 0
    overrun_minutes: int = 0

__all__ = ["HeaderRow"]
