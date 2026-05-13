from __future__ import annotations

from mindnavigator.workspaces.tasks._shared import (
    _extract_markdown_code_blocks,
    _linkify_description_text,
    extract_task_reference_ids,
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


def test_linkify_description_text_renders_task_reference_links_outside_urls() -> None:
    rendered = _linkify_description_text("See MN-42 and #7, but keep https://example.com/#123 as url.")

    assert "<a href='task:42'" in rendered
    assert ">MN-42</a>" in rendered
    assert "<a href='task:7'" in rendered
    assert ">#7</a>" in rendered
    assert "https://example.com/#123</a>" in rendered
    assert "task:123" not in rendered


def test_extract_task_reference_ids_collects_unique_ids_in_order() -> None:
    extracted = extract_task_reference_ids("MN-42 then #7 then MN-42", "ignore text", "#99")

    assert extracted == [42, 7, 99]
