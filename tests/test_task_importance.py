from __future__ import annotations

from datetime import date

from mindnavigator.storage import Database


def test_task_importance_defaults_and_persists(unique_temp_path) -> None:
    database = Database(path=unique_temp_path("task_importance", ".sqlite3"))
    try:
        task = database.create_task("Rated task", "", date(2026, 6, 2), "", "Medium")
        assert task.importance == 3

        updated = database.update_task(
            task.id,
            title=task.title,
            description=task.description,
            day=task.day,
            time_text=task.time_text,
            priority=task.priority,
            done=task.done,
            importance=5,
        )
        assert updated.importance == 5
        fetched = next(item for item in database.fetch_tasks() if item.id == task.id)
        assert fetched.importance == 5
    finally:
        database.close()
