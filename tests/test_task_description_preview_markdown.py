from __future__ import annotations

from mindnavigator.workspaces.tasks._shared import (
    _extract_markdown_code_blocks,
    _linkify_description_text,
)


def test_linkify_description_text_renders_inline_code() -> None:
    rendered = _linkify_description_text("before `x = 1` after")

    assert "before " in rendered
    assert " after" in rendered
    assert "<code" in rendered
    assert "x = 1" in rendered


def test_linkify_description_text_renders_fenced_code_block_with_language() -> None:
    rendered = _linkify_description_text("intro\n```python\nprint('hi')\n**bold**\n```\noutro")

    assert "intro<br>" in rendered
    assert ">python<" in rendered
    assert "<pre" in rendered
    assert "print(&#x27;hi&#x27;)" in rendered
    assert "**bold**" in rendered
    assert "<strong>" not in rendered
    assert "outro" in rendered


def test_linkify_description_text_keeps_urls_inside_code_plain() -> None:
    rendered = _linkify_description_text("visit https://example.com and `https://inside.example`")

    assert (
        "<a href='https://example.com' style=\"color:#6ECBFF;text-decoration:none;\">"
        "https://example.com</a>"
    ) in rendered
    assert "https://inside.example" in rendered
    assert "text-decoration:none" in rendered
    assert "<a href='https://inside.example'>https://inside.example</a>" not in rendered


def test_extract_markdown_code_blocks_collects_fenced_content_only() -> None:
    blocks = _extract_markdown_code_blocks(
        "before `inline`\n```python\nprint('a')\n```\nmid\n```\nvalue = 42\n```\nafter"
    )

    assert blocks == ["print('a')", "value = 42"]
