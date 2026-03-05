from __future__ import annotations

from mindnavigator.sprint_composer import (
    SprintSourceNode,
    compose_sprint,
    extract_semantic_token,
)


def test_extract_semantic_token_returns_backticked_keyword() -> None:
    assert extract_semantic_token("## `SPRINT` - вводная задача") == "SPRINT"
    assert extract_semantic_token("## `Task` - вложенная задача") == "TASK"
    assert extract_semantic_token("без токена") == ""


def test_compose_sprint_builds_partitions_tasks_and_addons() -> None:
    nodes = [
        SprintSourceNode(
            id=211,
            title="SPRINT :: Интеграционный спринт",
            description="Sprint brief",
            parent_id=None,
        ),
        SprintSourceNode(
            id=213,
            title="PARTITION :: Integration :: Поведение для верхнего регистра",
            description="Partition brief",
            parent_id=211,
        ),
        SprintSourceNode(
            id=215,
            title="TASK :: ## `SPRINT` - Вводная задача",
            description="Task brief",
            parent_id=213,
        ),
        SprintSourceNode(
            id=219,
            title="ADDON :: Описание работы над опорным словом `SPRINT`",
            description="Addon detail",
            parent_id=215,
        ),
    ]

    composed = compose_sprint(nodes, root_id=211)

    assert composed.root_id == 211
    assert composed.title == "Интеграционный спринт"
    assert len(composed.partitions) == 1
    assert composed.partitions[0].index == 1
    assert composed.partitions[0].title == "Поведение для верхнего регистра"
    assert len(composed.partitions[0].tasks) == 1
    assert composed.partitions[0].tasks[0].id == 215
    assert composed.partitions[0].tasks[0].semantic_token == "SPRINT"
    assert composed.partitions[0].tasks[0].addons == ("Addon detail",)


def test_compose_sprint_synthesizes_task_for_empty_partition() -> None:
    nodes = [
        SprintSourceNode(id=1, title="SPRINT :: Root", description="", parent_id=None),
        SprintSourceNode(id=2, title="PARTITION :: Integration :: Empty", description="", parent_id=1),
    ]

    composed = compose_sprint(nodes, root_id=1)

    assert len(composed.partitions) == 1
    assert len(composed.partitions[0].tasks) == 1
    assert composed.partitions[0].tasks[0].id == 0
    assert "Synthesized" in composed.partitions[0].tasks[0].brief


def test_compose_sprint_rejects_non_sprint_root() -> None:
    nodes = [SprintSourceNode(id=1, title="TASK :: Не корневой спринт", description="", parent_id=None)]

    try:
        compose_sprint(nodes, root_id=1)
        assert False, "compose_sprint should reject non-SPRINT root"
    except ValueError as exc:
        assert "SPRINT" in str(exc)

