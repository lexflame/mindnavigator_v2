"""Shared labels for task importance in task UI."""

from __future__ import annotations


TASK_IMPORTANCE_LABELS = {
    0: "Неопределён",
    1: "В конце дня",
    2: "В конце дня",
    3: "Важно",
    4: "Очень важно",
    5: "Есть сложности",
}

UNDEFINED_TASK_IMPORTANCE = 0


def normalize_task_importance(value: object, *, default: int = 3) -> int:
    try:
        parsed = int(value or default)
    except (TypeError, ValueError):
        parsed = default
    return max(1, min(5, parsed))


def task_importance_filter_key(value: object) -> int:
    if value is None or value == "":
        return UNDEFINED_TASK_IMPORTANCE
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return UNDEFINED_TASK_IMPORTANCE
    if parsed < 1 or parsed > 5:
        return UNDEFINED_TASK_IMPORTANCE
    return parsed


def task_importance_label(value: object) -> str:
    importance = task_importance_filter_key(value)
    if importance == UNDEFINED_TASK_IMPORTANCE:
        return TASK_IMPORTANCE_LABELS[UNDEFINED_TASK_IMPORTANCE]
    return TASK_IMPORTANCE_LABELS.get(importance, TASK_IMPORTANCE_LABELS[3])


def task_importance_combo_items() -> tuple[tuple[str, int], ...]:
    return tuple((f"{value} · {task_importance_label(value)}", value) for value in range(1, 6))


__all__ = [
    "TASK_IMPORTANCE_LABELS",
    "UNDEFINED_TASK_IMPORTANCE",
    "normalize_task_importance",
    "task_importance_filter_key",
    "task_importance_combo_items",
    "task_importance_label",
]
