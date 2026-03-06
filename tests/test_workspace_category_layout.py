from __future__ import annotations

from datetime import datetime, timezone

from mindnavigator.storage import CollectionCategoryData, CollectionItemData
from mindnavigator.workspaces.collections_workspace import (
    format_collection_item_row,
    group_collection_items_by_category,
)
from mindnavigator.workspaces.ideas_workspace import IdeaCategoryRow, IdeaItem, group_ideas_by_category
from mindnavigator.workspaces.ideas_workspace import idea_preview_line
from mindnavigator.workspaces.notes_workspace import NoteCategoryRow, NoteItem, group_notes_by_category
from mindnavigator.workspaces.notes_workspace import note_preview_line
from mindnavigator.workspaces.objects_workspace import ObjectCategoryRow, ObjectRow, group_objects_by_category
from mindnavigator.workspaces.objects_workspace import object_preview_line


def _now() -> datetime:
    return datetime.now(timezone.utc)


def test_group_notes_by_category_orders_groups_and_rows() -> None:
    rows = group_notes_by_category(
        [
            NoteItem(1, "N1", "p", [], _now(), "Work"),
            NoteItem(2, "N2", "p", [], _now(), ""),
            NoteItem(3, "N3", "p", [], _now(), "Alpha"),
        ]
    )

    categories = [row.category for row in rows if isinstance(row, NoteCategoryRow)]
    assert categories == ["Alpha", "Work", "Без проекта"]


def test_group_ideas_by_category_uses_status_headers() -> None:
    rows = group_ideas_by_category(
        [
            IdeaItem(1, "I1", "", "", "work", "other", 3, 3, None, "", False),
            IdeaItem(2, "I2", "", "", "inbox", "other", 3, 3, None, "", False),
            IdeaItem(3, "I3", "", "", "", "other", 3, 3, None, "", False),
        ]
    )

    categories = [row.category for row in rows if isinstance(row, IdeaCategoryRow)]
    assert categories == ["Inbox", "Work", "Без статуса"]


def test_group_objects_by_category_uses_catalog_root() -> None:
    rows = group_objects_by_category(
        [
            ObjectRow(1, "Obj 1", "Architecture/Houses", "", "", ""),
            ObjectRow(2, "Obj 2", "", "", "", ""),
            ObjectRow(3, "Obj 3", "Zeta", "", "", ""),
        ]
    )

    categories = [row.category for row in rows if isinstance(row, ObjectCategoryRow)]
    assert categories == ["Architecture", "Zeta", "Без каталога"]


def test_group_collections_and_row_format() -> None:
    categories_by_id = {
        10: CollectionCategoryData(10, "History", None, 0, "", ""),
    }
    items = [
        CollectionItemData(1, "Castle", 10, "building", "medieval", "", "https://x", "", "", "", "", ""),
        CollectionItemData(2, "Unknown", None, "other", "", "", "", "", "", "", "", ""),
    ]

    grouped = group_collection_items_by_category(items, categories_by_id)
    assert [category for category, _ in grouped] == ["History", "Без категории"]

    row_text = format_collection_item_row(items[0], categories_by_id)
    assert "Castle" in row_text
    assert "History" in row_text
    assert "#medieval" in row_text


def test_object_preview_line_returns_first_non_empty_line() -> None:
    text = "\n  \n  Первая строка описания  \nВторая строка\n"
    assert object_preview_line(text) == "Первая строка описания"
    assert object_preview_line("") == "Описание пока не добавлено."


def test_note_preview_line_compacts_newlines_and_spaces() -> None:
    text = "\r\n  Быстрое   превью заметки  \n\nСледующая строка"
    assert note_preview_line(text) == "Быстрое превью заметки"
    assert note_preview_line("   \n\t") == "Нет краткого описания."


def test_idea_preview_line_prefers_summary_then_body() -> None:
    assert idea_preview_line("  Кратко о идее  ", "Тело") == "Кратко о идее"
    assert idea_preview_line("", "\n  Текст из body  \n") == "Текст из body"
    assert idea_preview_line("", "") == "Нет превью идеи."
