from __future__ import annotations

from mindnavigator.workspaces.minddraw.module_impl import (
    MindDrawLinkState,
    MindDrawNodeState,
    deserialize_minddraw_state,
    serialize_minddraw_state,
)


def test_minddraw_state_roundtrip() -> None:
    nodes = [
        MindDrawNodeState("n1", "Root", 10.0, 20.0, "task", 17, "Task 17"),
        MindDrawNodeState("n2", "Child", 40.5, 55.25, "project", 9, "Project 9"),
    ]
    links = [MindDrawLinkState("n1", "n2")]

    raw = serialize_minddraw_state(nodes, links)
    restored_nodes, restored_links = deserialize_minddraw_state(raw)

    assert restored_nodes == nodes
    assert restored_links == links


def test_minddraw_deserialize_skips_invalid_links() -> None:
    raw = """
    {
      "nodes": [
        {"node_id": "n1", "title": "A", "x": 0, "y": 0},
        {"node_id": "n2", "title": "B", "x": 10, "y": 10}
      ],
      "links": [
        {"source_id": "n1", "target_id": "n2"},
        {"source_id": "n1", "target_id": "unknown"},
        {"source_id": "n2", "target_id": "n2"}
      ]
    }
    """

    nodes, links = deserialize_minddraw_state(raw)

    assert [node.node_id for node in nodes] == ["n1", "n2"]
    assert links == [MindDrawLinkState("n1", "n2")]
