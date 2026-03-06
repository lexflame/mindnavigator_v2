from __future__ import annotations

import re
from pathlib import Path


def test_ideas_relations_list_has_explicit_light_text_color() -> None:
    source = Path("mindnavigator/workspaces/ideas_workspace.py").read_text(encoding="utf-8")
    match = re.search(
        r"QWidget#IdeasWorkspace QListWidget\s*\{(?P<body>.*?)\}",
        source,
        flags=re.DOTALL,
    )
    assert match is not None
    body = match.group("body")
    assert "color: #e6e6e6;" in body
