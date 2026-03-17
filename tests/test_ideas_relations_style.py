from __future__ import annotations

from pathlib import Path


def test_ideas_relations_list_has_explicit_light_text_color() -> None:
    source = Path("mindnavigator/workspaces/ideas/ideas_workspace.py").read_text(encoding="utf-8")
    assert "QWidget#IdeasWorkspace QListWidget {{" in source
    assert "color: {palette.text};" in source
    assert "get_theme_palette" in source
