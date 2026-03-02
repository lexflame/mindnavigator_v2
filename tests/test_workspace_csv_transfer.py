from __future__ import annotations

from datetime import date

from mindnavigator.storage import Database
from mindnavigator.workspaces.csv_workspace_transfer import (
    build_category_path_map,
    export_collections_rows,
    export_notes_rows,
    import_notes_rows,
    import_projects_rows,
    import_tasks_rows,
    import_collections_rows,
)

def test_import_tasks_rows_restores_parent_and_done(unique_temp_path) -> None:
    db = Database(path=unique_temp_path("csv_tasks", ".db"))
    try:
        project = db.create_project(
            area="Work",
            title="CSV Project",
            updated=date(2026, 2, 25),
            priority="Medium",
        )
        rows = [
            {
                "id": "100",
                "parent_id": "",
                "project_title": project.title,
                "day": "2026-02-25",
                "time_text": "09:00",
                "title": "Parent CSV Task",
                "description": "root",
                "priority": "Medium",
                "done": "0",
                "recurrence_kind": "",
                "recurrence_interval": "1",
                "marker_color": "",
                "marker_theme": "",
            },
            {
                "id": "101",
                "parent_id": "100",
                "project_title": project.title,
                "day": "2026-02-25",
                "time_text": "10:00",
                "title": "Child CSV Task",
                "description": "child",
                "priority": "High",
                "done": "1",
                "recurrence_kind": "",
                "recurrence_interval": "1",
                "marker_color": "",
                "marker_theme": "",
            },
        ]

        result = import_tasks_rows(db, rows)
        assert result.imported == 2

        imported = {task.title: task for task in db.fetch_tasks() if task.title in {"Parent CSV Task", "Child CSV Task"}}
        assert imported["Child CSV Task"].parent_id == imported["Parent CSV Task"].id
        assert imported["Child CSV Task"].done is True
    finally:
        db.close()


def test_import_projects_rows_restores_parent_chain(unique_temp_path) -> None:
    db = Database(path=unique_temp_path("csv_projects", ".db"))
    try:
        rows = [
            {
                "id": "500",
                "parent_project_id": "",
                "area": "Architecture",
                "title": "Root CSV Project",
                "updated": "2026-02-25",
                "priority": "Medium",
                "archived": "0",
                "default_task_priority": "",
                "force_recurrence_kind": "",
                "linked_map_id": "",
                "linked_note_id": "",
                "linked_object_id": "",
                "marker_color": "",
                "marker_theme": "",
            },
            {
                "id": "501",
                "parent_project_id": "500",
                "area": "Architecture",
                "title": "Child CSV Project",
                "updated": "2026-02-25",
                "priority": "High",
                "archived": "0",
                "default_task_priority": "",
                "force_recurrence_kind": "",
                "linked_map_id": "",
                "linked_note_id": "",
                "linked_object_id": "",
                "marker_color": "",
                "marker_theme": "",
            },
        ]
        result = import_projects_rows(db, rows)
        assert result.imported == 2

        projects = {project.title: project for project in db.fetch_projects() if project.title in {"Root CSV Project", "Child CSV Project"}}
        assert projects["Child CSV Project"].parent_project_id == projects["Root CSV Project"].id
    finally:
        db.close()


def test_export_and_import_notes_rows_preserve_flags_and_tags(unique_temp_path) -> None:
    source_db = Database(path=unique_temp_path("csv_notes_source", ".db"))
    target_db = Database(path=unique_temp_path("csv_notes_target", ".db"))
    try:
        created = source_db.create_note(
            title="CSV Note",
            preview="line1\nline2",
            tags=["alpha", "beta"],
            project="Docs",
            favorite=True,
            attachment=True,
            locked=True,
        )
        rows = export_notes_rows([created])
        result = import_notes_rows(target_db, rows)
        assert result.imported == 1

        imported = [note for note in target_db.fetch_notes() if note.title == "CSV Note"]
        assert len(imported) == 1
        note = imported[0]
        assert note.preview == "line1\nline2"
        assert note.tags == ["alpha", "beta"]
        assert note.favorite is True
        assert note.attachment is True
        assert note.locked is True
    finally:
        source_db.close()
        target_db.close()


def test_export_collections_rows_contains_category_path_and_import_recreates_it(unique_temp_path) -> None:
    source_db = Database(path=unique_temp_path("csv_collections_source", ".db"))
    target_db = Database(path=unique_temp_path("csv_collections_target", ".db"))
    try:
        root = source_db.create_collection_category("Root")
        child = source_db.create_collection_category("Child", parent_id=root.id)
        source_db.create_collection_item(
            title="CSV Collection Item",
            entity_type="other",
            category_id=child.id,
            topic="topic",
            image_url="",
            source_url="https://example.com",
            description="desc",
            source_folder_path="",
            import_options_json="{}",
        )
        rows = export_collections_rows(
            source_db.fetch_collection_items(),
            source_db.fetch_collection_categories(),
        )
        only_row = next(row for row in rows if row["title"] == "CSV Collection Item")
        assert only_row["category_path"] == "Root / Child"

        result = import_collections_rows(target_db, [only_row])
        assert result.imported == 1

        imported_item = next(item for item in target_db.fetch_collection_items() if item.title == "CSV Collection Item")
        category_map = build_category_path_map(target_db.fetch_collection_categories())
        assert imported_item.category_id is not None
        assert category_map[imported_item.category_id] == "Root / Child"
    finally:
        source_db.close()
        target_db.close()
