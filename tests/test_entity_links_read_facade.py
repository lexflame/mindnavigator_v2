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
