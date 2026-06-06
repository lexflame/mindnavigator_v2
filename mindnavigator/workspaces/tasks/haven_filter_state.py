"""Pure state model for the tasks Haven filters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class HavenFilterState:
    scope_kind: Optional[str] = None
    scope_value: Optional[object] = None
    scope_label: str = ""
    importance: Optional[int] = None

    @property
    def badge_visible(self) -> bool:
        return self.scope_kind in {"project", "area"} and bool(self.scope_label)

    def set_scope(self, kind: str, value: object, label: str) -> None:
        normalized_kind = str(kind or "").strip().lower()
        if normalized_kind == "project":
            self.scope_kind = "project"
            self.scope_value = int(value)
            self.scope_label = str(label or "").strip()
            return
        if normalized_kind == "area":
            normalized_area = str(value or "").strip()
            self.scope_kind = "area"
            self.scope_value = normalized_area
            self.scope_label = str(label or normalized_area).strip()
            return
        raise ValueError(f"Unsupported Haven filter kind: {kind}")

    def clear_scope(self) -> None:
        self.scope_kind = None
        self.scope_value = None
        self.scope_label = ""

    def set_importance(self, importance: Optional[int]) -> None:
        self.importance = int(importance) if importance is not None else None

    def matches_importance(self, importance: int) -> bool:
        return self.importance == int(importance)

    def toggle_importance(self, importance: int) -> Optional[int]:
        selected = int(importance)
        self.importance = None if self.importance == selected else selected
        return self.importance
