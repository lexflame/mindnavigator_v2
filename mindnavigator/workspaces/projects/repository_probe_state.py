"""RepositoryProbeState class module for projects workspace."""

from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class RepositoryProbeState:
    available: bool
    branch_name: str = ""
    has_local_changes: bool = False
    message: str = ""

__all__ = ["RepositoryProbeState"]
