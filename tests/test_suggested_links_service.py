from datetime import date

from mindnavigator.services import SuggestedLinksService
from mindnavigator.storage import Database


def test_suggested_links_for_idea_are_ranked_and_exclude_existing_links(unique_temp_path) -> None:
    database = Database(path=unique_temp_path("suggested_links", ".sqlite3"))
    try:
        project = database.create_project("Work", "Search", date(2026, 6, 7), "Medium")
        other_project = database.create_project("Work", "Other", date(2026, 6, 7), "Medium")
        idea = database.create_idea(
            title="Оптимизация глобального поиска",
            summary="Ускорить поиск задач",
            project_id=project.id,
        )
        strongest = database.create_task(
            "Оптимизация поиска задач",
            "Профилировать глобальный поиск",
            date(2026, 6, 7),
            "",
            "Medium",
            project_id=project.id,
        )
        linked = database.create_task(
            "Глобальный поиск",
            "Уже связан",
            date(2026, 6, 7),
            "",
            "Medium",
            project_id=project.id,
        )
        database.create_task(
            "Оптимизация поиска",
            "Другой проект",
            date(2026, 6, 7),
            "",
            "Medium",
            project_id=other_project.id,
        )
        database.add_idea_relation(idea.id, "task", linked.id)

        suggestions = SuggestedLinksService(database).for_idea(idea.id)

        assert [item.target.id for item in suggestions] == [strongest.id]
        assert suggestions[0].score >= 2
        assert "поиск" in suggestions[0].reason
    finally:
        database.close()


def test_suggested_links_require_project_and_keyword_overlap(unique_temp_path) -> None:
    database = Database(path=unique_temp_path("suggested_links_empty", ".sqlite3"))
    try:
        idea = database.create_idea(title="Standalone idea")

        assert SuggestedLinksService(database).for_idea(idea.id) == []
        assert SuggestedLinksService(database).for_idea(999999) == []
    finally:
        database.close()
