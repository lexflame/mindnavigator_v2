from __future__ import annotations

from datetime import date

from PySide6.QtWidgets import QApplication, QLabel, QListWidget, QLineEdit, QPlainTextEdit, QSpinBox

from mindnavigator.storage import Database
from mindnavigator.workspaces import dossier as dossier_workspace


def _set_combo_to_data(combo, value) -> None:
    for index in range(combo.count()):
        if combo.itemData(index) == value:
            combo.setCurrentIndex(index)
            return
    raise AssertionError(f"Value {value!r} not found in combo box.")


def test_dossier_create_dialog_serializes_common_and_kind_fields() -> None:
    _app = QApplication.instance() or QApplication([])
    dialog = dossier_workspace.DossierCreateDialog(seed_kind="book", seed_title="Solaris")
    try:
        dialog.summary_edit.setText("Ocean world.")
        dialog.description_edit.setPlainText("Psychology and contact.")
        dialog.tags_edit.setText("classic, sci-fi")
        dialog.rating_spin.setValue(8)
        dialog.source_edit.setText("Shelf A")
        dialog.cover_image_edit.setText("covers/solaris.jpg")
        field_type, author_widget = dialog._metadata_widgets["author_display"]
        assert field_type == "str"
        assert isinstance(author_widget, QLineEdit)
        author_widget.setText("Stanislaw Lem")
        field_type, year_widget = dialog._metadata_widgets["publication_year"]
        assert field_type == "int"
        assert isinstance(year_widget, QSpinBox)
        year_widget.setValue(1961)

        values = dialog.values()

        assert values["kind"] == "book"
        assert values["title"] == "Solaris"
        assert values["tags"] == ["classic", "sci-fi"]
        assert values["rating"] == 8
        assert values["metadata"] == {
            "author_display": "Stanislaw Lem",
            "publication_year": 1961,
        }
    finally:
        dialog.deleteLater()


def test_dossier_edit_dialog_preserves_metadata_per_kind_switch() -> None:
    _app = QApplication.instance() or QApplication([])
    initial = dossier_workspace.DossierData(
        id=7,
        kind="book",
        title="Dune",
        summary="",
        description="",
        tags=[],
        status="planned",
        rating=None,
        source="",
        cover_image="",
        metadata={"author_display": "Frank Herbert"},
        created_at="2026-03-13T10:00:00+00:00",
        updated_at="2026-03-13T10:00:00+00:00",
    )
    dialog = dossier_workspace.DossierEditDialog(initial)
    try:
        book_author = dialog._metadata_widgets["author_display"][1]
        assert isinstance(book_author, QLineEdit)
        book_author.setText("Frank Herbert")

        _set_combo_to_data(dialog.kind_combo, "game")
        game_developer = dialog._metadata_widgets["developer"][1]
        assert isinstance(game_developer, QLineEdit)
        game_developer.setText("Westwood Studios")

        _set_combo_to_data(dialog.kind_combo, "book")
        restored_author = dialog._metadata_widgets["author_display"][1]
        assert isinstance(restored_author, QLineEdit)
        assert restored_author.text() == "Frank Herbert"

        _set_combo_to_data(dialog.kind_combo, "game")
        values = dialog.values()
        assert values["kind"] == "game"
        assert values["metadata"]["developer"] == "Westwood Studios"
    finally:
        dialog.deleteLater()


def test_dossier_details_dialog_renders_metadata_and_links(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("dossier_details_dialog", ".sqlite3")
    database = Database(path=db_path)
    dialog = None
    try:
        dossier = database.create_dossier(
            kind="writer",
            title="Ursula K. Le Guin",
            summary="Writer of speculative fiction.",
            description="Earthsea and Hainish Cycle.",
            tags=["writer", "classic"],
            status="completed",
            metadata={"country": "USA", "languages": ["English"], "notable_works_summary": "Earthsea"},
        )
        task = database.create_task(
            title="Read Earthsea notes",
            description="",
            day=date(2026, 3, 13),
            time_text="11:00",
            priority="Medium",
        )
        database.add_dossier_link(dossier.id, "task", task.id)

        monkeypatch.setattr(dossier_workspace, "get_database", lambda: database)
        dialog = dossier_workspace.DossierDetailsDialog(dossier)

        labels = [label.text() for label in dialog.findChildren(QLabel)]
        assert "Ursula K. Le Guin" in labels
        assert any("Writer of speculative fiction." in text for text in labels)
        assert any("English" in text for text in labels)

        description_widgets = dialog.findChildren(QPlainTextEdit)
        assert description_widgets
        assert "Earthsea and Hainish Cycle." in description_widgets[0].toPlainText()

        links_widgets = dialog.findChildren(QListWidget)
        assert links_widgets
        assert links_widgets[0].count() == 1
        assert "Read Earthsea notes" in links_widgets[0].item(0).text()
    finally:
        if dialog is not None:
            dialog.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)
