from datetime import date

from mindnavigator.services import GlobalSearchService
from mindnavigator.storage import Database


def test_full_text_search_indexes_existing_and_updated_entities(unique_temp_path) -> None:
    db_path = unique_temp_path("full_text_search", ".sqlite3")
    database = Database(path=db_path)
    try:
        task = database.create_task("Индексируемая задача", "Первичное описание", date(2026, 6, 7), "", "Medium")
        idea = database.create_idea("Индексируемая идея", summary="Концепция поиска")
        note = database.create_note("Индексируемая заметка", "Текст заметки", ["поиск"], "Inbox")
        obj = database.create_object("Индексируемый объект", "Каталог", "Документ", "Активен", "Описание")

        initial = database.search_full_text("индексируем")

        assert initial is not None
        assert {(item["entity"], item["id"]) for item in initial} == {
            ("task", task.id),
            ("idea", idea.id),
            ("note", note.id),
            ("object", obj.id),
        }

        database.update_object(obj.id, "Обновлённый объект", "Каталог", "Документ", "Активен", "Новый термин")
        database.delete_idea(idea.id)

        assert [(item["entity"], item["id"]) for item in database.search_full_text("новый термин") or []] == [
            ("object", obj.id)
        ]
        assert all(item["id"] != idea.id for item in database.search_full_text("концепция") or [])

        database.close()
        database = Database(path=db_path)
        assert [(item["entity"], item["id"]) for item in database.search_full_text("новый термин") or []] == [
            ("object", obj.id)
        ]
    finally:
        database.close()


def test_global_search_uses_full_text_index_for_primary_entities(unique_temp_path) -> None:
    database = Database(path=unique_temp_path("global_full_text_search", ".sqlite3"))
    try:
        idea = database.create_idea("Редкая индексная идея", summary="Уникальный маркер")

        matches = GlobalSearchService(database).search("уникальн")

        assert any(item["entity"] == "idea" and item["id"] == idea.id for item in matches)
    finally:
        database.close()
