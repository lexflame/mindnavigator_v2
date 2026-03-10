"""MindDraw workspace prototype with mind-map style canvas and entity links."""

from __future__ import annotations

import json
import math
import uuid
from dataclasses import dataclass
from typing import Callable, Optional

from PySide6.QtCore import QPointF, QRectF, QSettings, Qt
from PySide6.QtGui import QAction, QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGraphicsItem,
    QGraphicsPathItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from mindnavigator.storage import get_database
from mindnavigator.ui.workspaces.base_workspace import BaseWorkspace

import sys
_storage_get_database = get_database

def get_database():
    module = sys.modules.get("mindnavigator.workspaces.minddraw.module_impl")
    if module is not None:
        override = getattr(module, "get_database", None)
        if override is not None and override is not get_database:
            return override()
    return _storage_get_database()

from .minddraw_node_state import MindDrawNodeState
from .minddraw_link_state import MindDrawLinkState
from .entity_option import EntityOption









def serialize_minddraw_state(nodes: list[MindDrawNodeState], links: list[MindDrawLinkState]) -> str:
    """Serialize nodes and links into compact JSON string."""

    payload = {
        "nodes": [
            {
                "node_id": node.node_id,
                "title": node.title,
                "x": node.x,
                "y": node.y,
                "entity_kind": node.entity_kind,
                "entity_id": node.entity_id,
                "entity_title": node.entity_title,
            }
            for node in nodes
        ],
        "links": [
            {
                "source_id": link.source_id,
                "target_id": link.target_id,
            }
            for link in links
        ],
    }
    return json.dumps(payload, ensure_ascii=False)


def deserialize_minddraw_state(raw: str) -> tuple[list[MindDrawNodeState], list[MindDrawLinkState]]:
    """Deserialize JSON payload into validated state objects."""

    try:
        payload = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return [], []
    if not isinstance(payload, dict):
        return [], []

    nodes: list[MindDrawNodeState] = []
    links: list[MindDrawLinkState] = []

    for row in payload.get("nodes", []):
        if not isinstance(row, dict):
            continue
        node_id = str(row.get("node_id") or "").strip()
        title = str(row.get("title") or "").strip()
        if not node_id:
            continue
        if not title:
            title = "Topic"
        entity_id_raw = row.get("entity_id")
        entity_id: Optional[int]
        try:
            entity_id = int(entity_id_raw) if entity_id_raw is not None else None
        except (TypeError, ValueError):
            entity_id = None
        try:
            x = float(row.get("x", 0.0))
            y = float(row.get("y", 0.0))
        except (TypeError, ValueError):
            x, y = 0.0, 0.0
        nodes.append(
            MindDrawNodeState(
                node_id=node_id,
                title=title,
                x=x,
                y=y,
                entity_kind=str(row.get("entity_kind") or "").strip(),
                entity_id=entity_id,
                entity_title=str(row.get("entity_title") or "").strip(),
            )
        )

    node_ids = {node.node_id for node in nodes}
    for row in payload.get("links", []):
        if not isinstance(row, dict):
            continue
        source_id = str(row.get("source_id") or "").strip()
        target_id = str(row.get("target_id") or "").strip()
        if not source_id or not target_id or source_id == target_id:
            continue
        if source_id not in node_ids or target_id not in node_ids:
            continue
        links.append(MindDrawLinkState(source_id=source_id, target_id=target_id))

    return nodes, links
