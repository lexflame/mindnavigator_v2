"""Marker class module for maps workspace."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from PySide6.QtGui import QColor

@dataclass(frozen=True)
class Marker:
    id: int
    name: str
    x: float
    y: float
    color: QColor
    type: str
    size: float
    description: str = ""
    properties: str = ""
    task_ids: List[int] = field(default_factory=list)
    project_ids: List[int] = field(default_factory=list)
    note_ids: List[int] = field(default_factory=list)
    object_ids: List[int] = field(default_factory=list)
    file_ids: List[int] = field(default_factory=list)
    map_ids: List[int] = field(default_factory=list)
    marker_ids: List[int] = field(default_factory=list)
    parent_path: str = ""
    image_path: str = ""

__all__ = ["Marker"]
