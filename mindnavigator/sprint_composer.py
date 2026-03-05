"""Sprint composition helpers for MindNavigator task trees."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .sprint_parser import parse_sprint_header


@dataclass(frozen=True)
class SprintSourceNode:
    id: int
    title: str
    description: str
    parent_id: int | None


@dataclass(frozen=True)
class SprintTaskEntry:
    id: int
    title: str
    brief: str
    semantic_token: str
    addons: tuple[str, ...]


@dataclass(frozen=True)
class SprintPartitionEntry:
    id: int
    index: int
    title: str
    brief: str
    tasks: tuple[SprintTaskEntry, ...]
    addons: tuple[str, ...]


@dataclass(frozen=True)
class ComposedSprint:
    root_id: int
    title: str
    brief: str
    partitions: tuple[SprintPartitionEntry, ...]


def compose_sprint(
    nodes: Iterable[SprintSourceNode],
    *,
    root_id: int,
    synthesize_empty_partition_task: bool = True,
) -> ComposedSprint:
    node_by_id = {int(node.id): node for node in nodes}
    root = node_by_id.get(int(root_id))
    if root is None:
        raise ValueError(f"Sprint root not found: {root_id}")

    root_header = parse_sprint_header(root.title)
    if root_header is None or root_header.keyword != "SPRINT":
        raise ValueError(f"Sprint root must use SPRINT header: {root.title!r}")

    child_map: dict[int, list[SprintSourceNode]] = {}
    for node in node_by_id.values():
        if node.parent_id is None:
            continue
        child_map.setdefault(int(node.parent_id), []).append(node)
    for items in child_map.values():
        items.sort(key=lambda item: int(item.id))

    partitions: list[SprintPartitionEntry] = []
    partition_nodes = [node for node in child_map.get(int(root_id), []) if _is_keyword(node.title, "PARTITION")]
    for index, partition_node in enumerate(partition_nodes, start=1):
        partition_header = parse_sprint_header(partition_node.title)
        partition_title = partition_header.title if partition_header else partition_node.title
        partition_addons = _collect_direct_addons(partition_node.id, child_map)
        tasks = _collect_partition_tasks(
            partition_node.id,
            child_map,
            synthesize_empty_partition_task=synthesize_empty_partition_task,
        )
        partitions.append(
            SprintPartitionEntry(
                id=int(partition_node.id),
                index=index,
                title=partition_title,
                brief=(partition_node.description or "").strip(),
                tasks=tuple(tasks),
                addons=tuple(partition_addons),
            )
        )

    return ComposedSprint(
        root_id=int(root.id),
        title=root_header.title,
        brief=(root.description or "").strip(),
        partitions=tuple(partitions),
    )


def extract_semantic_token(text: str) -> str:
    raw = (text or "").strip()
    if not raw:
        return ""
    first_tick = raw.find("`")
    if first_tick == -1:
        return ""
    second_tick = raw.find("`", first_tick + 1)
    if second_tick == -1:
        return ""
    return raw[first_tick + 1 : second_tick].strip().upper()


def _collect_partition_tasks(
    partition_id: int,
    child_map: dict[int, list[SprintSourceNode]],
    *,
    synthesize_empty_partition_task: bool,
) -> list[SprintTaskEntry]:
    task_nodes = [node for node in child_map.get(int(partition_id), []) if _is_keyword(node.title, "TASK")]
    tasks: list[SprintTaskEntry] = []
    for task_node in task_nodes:
        task_header = parse_sprint_header(task_node.title)
        task_title = task_header.title if task_header else task_node.title
        tasks.append(
            SprintTaskEntry(
                id=int(task_node.id),
                title=task_title,
                brief=(task_node.description or "").strip(),
                semantic_token=extract_semantic_token(task_title),
                addons=tuple(_collect_direct_addons(task_node.id, child_map)),
            )
        )

    if tasks or not synthesize_empty_partition_task:
        return tasks
    return [
        SprintTaskEntry(
            id=0,
            title="Auto-generated partition task",
            brief="Synthesized because PARTITION has no nested TASK nodes.",
            semantic_token="",
            addons=(),
        )
    ]


def _collect_direct_addons(node_id: int, child_map: dict[int, list[SprintSourceNode]]) -> list[str]:
    result: list[str] = []
    for node in child_map.get(int(node_id), []):
        if not _is_keyword(node.title, "ADDON"):
            continue
        parsed = parse_sprint_header(node.title)
        addon_text = (node.description or "").strip() or (parsed.title if parsed is not None else node.title)
        if addon_text:
            result.append(addon_text)
    return result


def _is_keyword(title: str, expected: str) -> bool:
    parsed = parse_sprint_header(title)
    return parsed is not None and parsed.keyword == expected
