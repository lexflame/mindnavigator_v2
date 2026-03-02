from datetime import date

import pytest

from mindnavigator.storage import Database


@pytest.fixture()
def db(unique_temp_path):
    db_path = unique_temp_path("test_projects", ".sqlite3")
    database = Database(path=db_path)
    try:
        yield database
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def _create_project(db: Database, title: str, parent_id: int | None = None):
    return db.create_project(
        area="Work",
        title=title,
        updated=date(2026, 2, 20),
        priority="Medium",
        parent_project_id=parent_id,
    )


def test_move_project_reorders_root_siblings(db: Database):
    first = _create_project(db, "First")
    second = _create_project(db, "Second")
    third = _create_project(db, "Third")

    db.move_project(third.id, None, 0)

    roots = db.fetch_project_children(None)
    created_ids = {first.id, second.id, third.id}
    created_roots = [item for item in roots if item.id in created_ids]
    assert [item.id for item in created_roots] == [third.id, first.id, second.id]
    assert created_roots[0].sort_order < created_roots[1].sort_order < created_roots[2].sort_order


def test_move_project_reparents_to_new_parent(db: Database):
    parent_a = _create_project(db, "Parent A")
    parent_b = _create_project(db, "Parent B")
    child = _create_project(db, "Child", parent_id=parent_a.id)

    db.move_project(child.id, parent_b.id, None)

    children_a = db.fetch_project_children(parent_a.id)
    children_b = db.fetch_project_children(parent_b.id)
    assert children_a == []
    assert [item.id for item in children_b] == [child.id]
    assert children_b[0].parent_project_id == parent_b.id


def test_move_project_blocks_cycle(db: Database):
    root = _create_project(db, "Root")
    child = _create_project(db, "Child", parent_id=root.id)
    grandchild = _create_project(db, "Grandchild", parent_id=child.id)

    with pytest.raises(ValueError):
        db.move_project(root.id, grandchild.id, None)


def test_move_project_reindexes_old_and_new_groups(db: Database):
    parent_a = _create_project(db, "Parent A")
    parent_b = _create_project(db, "Parent B")
    child_a1 = _create_project(db, "A1", parent_id=parent_a.id)
    child_a2 = _create_project(db, "A2", parent_id=parent_a.id)

    db.move_project(child_a1.id, parent_b.id, None)

    children_a = db.fetch_project_children(parent_a.id)
    children_b = db.fetch_project_children(parent_b.id)
    assert [item.id for item in children_a] == [child_a2.id]
    assert [item.sort_order for item in children_a] == [0]
    assert [item.id for item in children_b] == [child_a1.id]
    assert [item.sort_order for item in children_b] == [0]
