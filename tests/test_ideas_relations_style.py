from __future__ import annotations

from pathlib import Path


def test_ideas_relations_list_has_explicit_light_text_color() -> None:
    source = Path("mindnavigator/workspaces/ideas/ideas_workspace.py").read_text(encoding="utf-8")
    assert "QWidget#IdeasWorkspace QListWidget {{" in source
    assert "color: {palette.text};" in source
    assert "get_theme_palette" in source


def test_idea_relation_dialog_uses_themed_styles() -> None:
    source = Path("mindnavigator/workspaces/ideas/ideas_workspace.py").read_text(encoding="utf-8")
    assert "QDialog#IdeaRelationDialog {{" in source
    assert "QDialog#IdeaRelationDialog QComboBox {{" in source
    assert "QDialog#IdeaRelationDialog QToolButton {{" in source
    assert "IdeaRelationDialogTitle" in source


def test_main_window_refreshes_current_idea_relations_on_ideas_mode() -> None:
    source = Path("mindnavigator/window/collections/main_window.py").read_text(encoding="utf-8")
    assert 'elif mode_name == self.MODE_IDEAS:' in source
    assert "self.page_ideas.refresh_current_relations()" in source
