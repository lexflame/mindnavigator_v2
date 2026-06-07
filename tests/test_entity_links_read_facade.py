from __future__ import annotations

from datetime import date

from mindnavigator.storage import Database


def test_entity_links_facade_combines_outgoing_and_incoming_legacy_links(unique_temp_path) -> None:
    database = Database(path=unique_temp_path("entity_links_facade", ".sqlite3"))
    try:
        task = database.create_task("Source task", "", date(2026, 6, 7), "", "Medium")
        target_task = database.create_task("Target task", "", date(2026, 6, 7), "", "Medium")
        idea = database.create_idea(title="Idea")
        dossier = database.create_dossier("film", "Dossier")

        attachment = database.add_task_attachment(task.id, "task", target_task.id)
        database.update_task_attachment_comment(attachment.id, "work item")
        database.add_context_entity_link("idea", idea.id, "task", target_task.id, "MN", "body")
        database.add_idea_relation(idea.id, "task", target_task.id, "develops")
        database.add_dossier_link(dossier.id, "task", target_task.id)

        links = database.fetch_entity_links("task", target_task.id)

        assert {(link.origin, link.direction, link.other_entity.kind) for link in links} == {
            ("task_attachments", "incoming", "task"),
            ("context_entity_links", "incoming", "idea"),
            ("idea_relations", "incoming", "idea"),
            ("dossier_links", "incoming", "dossier"),
        }
        attachment = next(link for link in links if link.origin == "task_attachments")
        assert attachment.metadata["comment"] == "work item"
        mention = next(link for link in links if link.origin == "context_entity_links")
        assert mention.metadata == {"anchor_text": "MN", "source_field": "body"}
        assert database.fetch_entity_links("task", target_task.id, direction="outgoing") == []
    finally:
        database.close()


def test_entity_links_facade_normalizes_symmetric_collection_relations(unique_temp_path) -> None:
    database = Database(path=unique_temp_path("entity_links_collection", ".sqlite3"))
    try:
        left = database.create_collection_item(title="Left", entity_type="other")
        right = database.create_collection_item(title="Right", entity_type="other")
        relation = database.create_collection_relation(left.id, right.id, "supports")

        links = database.fetch_entity_links("collection_item", right.id, direction="incoming")

        assert len(links) == 1
        assert links[0].link_id == f"collection_relations:{relation.id}"
        assert links[0].direction == "symmetric"
        assert links[0].other_entity.id == left.id
        assert links[0].metadata["legacy_relation_kind"] == "supports"
    finally:
        database.close()


def test_entity_links_facade_includes_character_project_and_concept_board_links(unique_temp_path) -> None:
    database = Database(path=unique_temp_path("entity_links_extended", ".sqlite3"))
    try:
        source_project = database.create_project("Work", "Source project", date(2026, 6, 7), "Medium")
        related_project = database.create_project("Work", "Related project", date(2026, 6, 7), "Medium")
        task = database.create_task("Linked task", "", date(2026, 6, 7), "", "Medium")
        note = database.create_note("Linked note", "", [], "")
        character = database.create_character("Character")
        board = database.create_concept_board("Board")

        database.replace_project_related_projects(source_project.id, [related_project.id])
        database.replace_project_related_tasks(source_project.id, [task.id])
        database.add_character_link(character.id, "note", note.id)
        database.add_concept_board_link(
            board.id,
            source_kind="task",
            source_id=task.id,
            target_kind="note",
            target_id=note.id,
            link_type="develops",
        )

        note_links = database.fetch_entity_links("note", note.id)
        task_links = database.fetch_entity_links("task", task.id)
        related_project_links = database.fetch_entity_links("project", related_project.id)

        assert {(link.origin, link.other_entity.kind) for link in note_links} == {
            ("character_links", "character"),
            ("mutaboard_links", "task"),
        }
        board_link = next(link for link in note_links if link.origin == "mutaboard_links")
        assert board_link.direction == "incoming"
        assert board_link.relation_kind == "develops"
        assert board_link.metadata["concept_board_id"] == board.id
        assert {(link.origin, link.other_entity.kind) for link in task_links} == {
            ("project_related_tasks", "project"),
            ("mutaboard_links", "note"),
        }
        project_link = related_project_links[0]
        assert project_link.origin == "project_related_projects"
        assert project_link.direction == "incoming"
        assert project_link.other_entity.id == source_project.id
    finally:
        database.close()
