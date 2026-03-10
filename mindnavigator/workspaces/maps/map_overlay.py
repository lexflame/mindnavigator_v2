"""MapOverlay class module for maps workspace."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor

@dataclass(frozen=True)
class MapOverlay:
    id: int
    kind: str  # "region" | "path"
    points: List[QPointF]
    color: QColor
    title: str = ""

__all__ = ["MapOverlay"]
