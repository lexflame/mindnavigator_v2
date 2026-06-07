from datetime import date

from mindnavigator.storage import Database


def test_task_hierarchy_queries_cover_children_descendants_and_plan_parent(unique_temp_path) -> None:
    db_path = unique_temp_path("task_hierarchy_queries", ".sqlite3")
    database = Database(path=db_path)
    try:
        root = database.create_task(
            "Plan", "", date(2026, 6, 7), "09:00", "Medium", is_plan_task=True,
        )
        child = database.create_task(
            "Child", "", date(2026, 6, 7), "10:00", "Medium", parent_id=root.id,
        )
        grandchild = database.create_task(
            "Grandchild", "", date(2026, 6, 7), "11:00", "Medium", parent_id=child.id,
        )

        assert database.task_has_children(root.id)
        assert database.task_has_descendants(root.id)
        assert not database.task_has_children(grandchild.id)
        assert not database.task_has_descendants(grandchild.id)
        assert database.task_parent_is_plan(child.id)
        assert not database.task_parent_is_plan(grandchild.id)
    finally:
        database.close()
        db_path.unlink(missing_ok=True)
