from __future__ import annotations

from PySide6.QtWidgets import QApplication, QLabel

from mindnavigator.workspaces.characters import characters_workspace as characters_module


class _CharactersDbStub:
    def fetch_characters(self, **_kwargs):
        return []

    def describe_character_link_target(self, entity_kind, entity_id):
        return f"{entity_kind}:{entity_id}"

    def fetch_character_links(self, _character_id):
        return []


def test_characters_workspace_uses_utf8_labels(monkeypatch) -> None:
    _app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(characters_module, "get_database", lambda: _CharactersDbStub())

    workspace = characters_module.CharactersWorkspace()
    try:
        labels = {label.text() for label in workspace.findChildren(QLabel)}

        assert "Персонажи" in labels
        assert "Список персонажей" in labels
        assert "Карточка персонажа" in labels
        assert workspace.search_input.placeholderText() == "Поиск по имени, роли, тегам и описанию"
        assert workspace.tags_edit.placeholderText() == "через запятую"
        assert workspace.add_button.text() == "Новый"
        assert workspace.delete_button.text() == "Удалить"
        assert workspace.save_button.text() == "Сохранить"
        assert workspace.filter_label.text() == "Фильтр: все сущности"
        assert workspace._kind_choices()[0][0]
        assert "Р¤" not in workspace.filter_label.text()
        assert "QFrame#CharactersDetailsContainer QLabel {" in workspace.styleSheet()
        assert "color: #cfd5df;" in workspace.styleSheet()
    finally:
        workspace.deleteLater()
