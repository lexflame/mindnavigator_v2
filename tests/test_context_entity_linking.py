from __future__ import annotations

from datetime import date

from PySide6.QtWidgets import QApplication, QTextEdit

from mindnavigator.context_entity_linking import (
    ContextEntityLinkService,
    ContextEntitySearchService,
    extract_capitalized_words,
    normalize_context_word,
)
from mindnavigator.storage import Database
from mindnavigator.ui.context_entity_linking import attach_context_entity_linking


def test_extract_capitalized_words_skips_urls_emails_and_tags() -> None:
    text = "Проект MindNavigator https://Example.com test@Example.com #Архив <b>Карта</b>"

    words = extract_capitalized_words(text, field="body")

    assert [(word.raw, word.field) for word in words] == [("Проект", "body"), ("MindNavigator", "body")]


def test_context_search_finds_entities_across_supported_types(tmp_path) -> None:
    db = Database(tmp_path / "mind.db")
    try:
        task = db.create_task("MindNavigator UI", "Интерфейс", date.today(), "", "Medium")
        idea = db.create_idea("Контекстные связи", summary="MindNavigator")
        note = db.create_note("Архитектура поиска", "Проект MindNavigator", [], "Inbox")
        obj = db.create_object("Проект MindNavigator", "", "", "", "Карта продукта")

        results = ContextEntitySearchService(db).search_context_entities("MindNavigator", limit=8)

        result_keys = {(result.entity_type, result.entity_id) for result in results}
        assert ("task", task.id) in result_keys
        assert ("idea", idea.id) in result_keys
        assert ("note", note.id) in result_keys
        assert ("object", obj.id) in result_keys
    finally:
        db.close()


def test_context_link_service_writes_task_attachment_and_metadata(tmp_path) -> None:
    db = Database(tmp_path / "mind.db")
    try:
        task = db.create_task("Связать", "", date.today(), "", "Medium")
        note = db.create_note("MindNavigator", "Описание", [], "Inbox")

        result = ContextEntityLinkService(db).create_context_link(
            "task",
            task.id,
            "note",
            note.id,
            "MindNavigator",
            "description",
        )
        duplicate = ContextEntityLinkService(db).create_context_link(
            "task",
            task.id,
            "note",
            note.id,
            "MindNavigator",
            "description",
        )

        assert result.success is True
        assert result.created is True
        assert duplicate.duplicate is True
        assert any(attachment.kind == "note" and attachment.ref_id == note.id for attachment in db.fetch_task_attachments(task.id))
        links = db.fetch_context_entity_links(source_type="task", source_id=task.id)
        assert len(links) == 1
        assert links[0].anchor_text == "MindNavigator"
    finally:
        db.close()


def test_context_linking_highlights_capitalized_words_in_text_edit(tmp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db = Database(tmp_path / "mind.db")
    editor = QTextEdit()
    try:
        task = db.create_task("Источник", "", date.today(), "", "Medium")
        db.create_note("MindNavigator", "Описание", [], "Inbox")
        editor.setPlainText("Связать MindNavigator с задачей.")

        controller = attach_context_entity_linking(
            editor,
            db,
            source_type="task",
            source_id_getter=lambda: task.id,
            source_field="description",
        )
        controller.refresh_now()

        assert normalize_context_word("MindNavigator") in controller._ranges_by_word
        assert controller._ranges_by_word[normalize_context_word("MindNavigator")]
    finally:
        editor.deleteLater()
        db.close()
