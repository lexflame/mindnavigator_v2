from __future__ import annotations

from mindnavigator.transfer.sprint.sprint_classification import (
    classify_keyword,
    classify_mindnavigator_title,
)


def test_classify_keyword_maps_partition_c_tokens() -> None:
    assert classify_keyword("Fix") is not None
    assert classify_keyword("Feat") is not None
    assert classify_keyword("Integration") is not None
    assert classify_keyword("Design") is not None
    assert classify_keyword("Workspace") is not None
    assert classify_keyword("Reafactor") is not None


def test_classify_keyword_maps_partition_d_tokens() -> None:
    abstract_feature = classify_keyword("Фичи")
    enhancement = classify_keyword("Проработка")

    assert abstract_feature is not None
    assert abstract_feature.keyword == "ФИЧИ"
    assert abstract_feature.route == "feature-adjacent"
    assert abstract_feature.parity_handoff is True

    assert enhancement is not None
    assert enhancement.keyword == "ПРОРАБОТКА"
    assert enhancement.route == "enhancement"
    assert enhancement.parity_handoff is False


def test_classify_mindnavigator_title_supports_task_section_format() -> None:
    classification = classify_mindnavigator_title("TASK :: Fix :: Исправить падение приложения")

    assert classification is not None
    assert classification.keyword == "FIX"
    assert classification.route == "fix"
    assert classification.parity_candidate is True


def test_classify_mindnavigator_title_supports_backticked_semantic_token() -> None:
    classification = classify_mindnavigator_title("TASK :: ## `Reafactor` - Восстановить утраченный сценарий")

    assert classification is not None
    assert classification.keyword == "REFACTOR"
    assert classification.route == "refactor"


def test_classify_mindnavigator_title_supports_direct_keyword_format() -> None:
    classification = classify_mindnavigator_title("Workspace :: Обновить вложенный режим")

    assert classification is not None
    assert classification.keyword == "WORKSPACE"
    assert classification.route == "workspace"


def test_classify_mindnavigator_title_returns_none_for_unknown_format() -> None:
    assert classify_mindnavigator_title("TASK :: UnknownKind :: Проверка") is None
    assert classify_mindnavigator_title("Произвольная строка") is None


def test_classify_mindnavigator_title_supports_partition_d_formats() -> None:
    from_section = classify_mindnavigator_title("TASK :: Фичи :: Смежный функционал")
    from_backticks = classify_mindnavigator_title("TASK :: ## `Проработка` - Расширение поведения")

    assert from_section is not None
    assert from_section.keyword == "ФИЧИ"
    assert from_section.parity_handoff is True

    assert from_backticks is not None
    assert from_backticks.keyword == "ПРОРАБОТКА"
    assert from_backticks.parity_handoff is False
