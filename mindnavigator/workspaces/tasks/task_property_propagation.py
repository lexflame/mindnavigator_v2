"""Task property propagation descriptors and result data."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any


TASK_PROPAGATABLE_FIELDS: dict[str, str] = {
    "marker_color": "Цвет",
    "project_id": "Проект",
    "priority": "Маркер",
    "marker_theme": "Тематика",
    "day": "Дата",
    "time_text": "Время",
}

TASK_PROPAGATABLE_CLEARABLE_FIELDS = {"marker_color", "project_id", "marker_theme", "time_text"}


@dataclass(frozen=True)
class TaskPropertyPropagationResult:
    property_name: str
    property_label: str
    recursive: bool
    target_count: int = 0
    updated_count: int = 0
    skipped_count: int = 0
    error_count: int = 0
    errors: tuple[str, ...] = ()

    @property
    def success(self) -> bool:
        return self.error_count == 0


def is_empty_task_property_value(property_name: str, value: Any) -> bool:
    if property_name == "project_id":
        return value is None
    if property_name == "day":
        return not isinstance(value, date)
    if property_name == "priority":
        return not str(value or "").strip()
    return not str(value or "").strip()

