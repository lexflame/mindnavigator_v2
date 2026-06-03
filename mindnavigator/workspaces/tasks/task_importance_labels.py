"""Shared labels for task importance in task UI."""

from __future__ import annotations


TASK_IMPORTANCE_LABELS = {
    1: "В конце дня",
    2: "В конце дня",
    3: "Важно",
    4: "Очень важно",
    5: "Есть сложности",
}


def normalize_task_importance(value: object, *, default: int = 3) -> int:
    try:
        parsed = int(value or default)
    except (TypeError, ValueError):
        parsed = default
    return max(1, min(5, parsed))


def task_importance_label(value: object) -> str:
    importance = normalize_task_importance(value)
    return TASK_IMPORTANCE_LABELS.get(importance, TASK_IMPORTANCE_LABELS[3])


def task_importance_combo_items() -> tuple[tuple[str, int], ...]:
    return tuple((f"{value} · {task_importance_label(value)}", value) for value in range(1, 6))


__all__ = [
    "TASK_IMPORTANCE_LABELS",
    "normalize_task_importance",
    "task_importance_combo_items",
    "task_importance_label",
]
