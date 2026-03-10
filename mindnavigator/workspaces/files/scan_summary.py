"""ScanSummary class module for files workspace."""

from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class ScanSummary:
    total: int
    valid: int
    invalid: int
    skipped: int

__all__ = ["ScanSummary"]
