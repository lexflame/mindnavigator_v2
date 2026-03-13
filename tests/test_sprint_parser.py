from __future__ import annotations

from mindnavigator.transfer.sprint.sprint_parser import normalize_keyword, parse_sprint_header


def test_normalize_keyword_supports_canonical_and_alias_tokens() -> None:
    assert normalize_keyword("SPRINT") == "SPRINT"
    assert normalize_keyword("sptrint") == "SPRINT"
    assert normalize_keyword("PARTIOTION") == "PARTITION"
    assert normalize_keyword("Reafactor") == "REFACTOR"
    assert normalize_keyword("Фичи") == "ФИЧИ"
    assert normalize_keyword("Проработка") == "ПРОРАБОТКА"


def test_parse_sprint_header_supports_extended_section_format() -> None:
    parsed = parse_sprint_header("PARTITION :: Integration :: Опорные и ключевые слова")

    assert parsed is not None
    assert parsed.keyword == "PARTITION"
    assert parsed.section == "Integration"
    assert parsed.title == "Опорные и ключевые слова"
    assert parsed.source_format == "extended"


def test_parse_sprint_header_supports_extended_type_format() -> None:
    parsed = parse_sprint_header("TASK :: Fix :: Исправить регрессию в обработчике")

    assert parsed is not None
    assert parsed.keyword == "TASK"
    assert parsed.section == "Fix"
    assert parsed.title == "Исправить регрессию в обработчике"
    assert parsed.source_format == "extended"


def test_parse_sprint_header_supports_short_format() -> None:
    parsed = parse_sprint_header("TASK :: Формат строки заголовка задачи")

    assert parsed is not None
    assert parsed.keyword == "TASK"
    assert parsed.section == ""
    assert parsed.title == "Формат строки заголовка задачи"
    assert parsed.source_format == "short"


def test_parse_sprint_header_supports_alias_and_hash_prefix() -> None:
    parsed = parse_sprint_header("## SPTRINT :: Интеграционный спринт")

    assert parsed is not None
    assert parsed.keyword == "SPRINT"
    assert parsed.title == "Интеграционный спринт"


def test_parse_sprint_header_rejects_unknown_or_malformed_titles() -> None:
    assert parse_sprint_header("Неизвестный формат") is None
    assert parse_sprint_header("UNKNOWN :: Заголовок") is None
    assert parse_sprint_header("TASK :: ") is None

