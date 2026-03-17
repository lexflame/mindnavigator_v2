"""MindDrawWorkspace class module for minddraw workspace."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403
from .minddraw_entity_picker_dialog import MindDrawEntityPickerDialog
from .minddraw_node_item import MindDrawNodeItem
from mindnavigator.ui.styles import get_theme_palette


class MindDrawWorkspace(BaseWorkspace):
    """Mind-map workspace with lightweight entity integration."""

    workspace_id = "minddraw"
    workspace_title = "MindDraw"
    _STATE_KEY = "workspace/minddraw/canvas_state"

    def __init__(self, parent: QWidget | None = None) -> None:
        self._db = get_database()
        self._nodes: dict[str, MindDrawNodeState] = {}
        self._links: list[MindDrawLinkState] = []
        self._node_items: dict[str, MindDrawNodeItem] = {}
        self._link_items: dict[tuple[str, str], QGraphicsPathItem] = {}
        super().__init__(parent)
        self.setObjectName("MindDrawWorkspace")
        self.search_input.setPlaceholderText("Поиск по узлам MindDraw…")
        self.set_theme_mode(self._theme_mode)
        self._load_canvas_state()

    def _build_ui(self) -> None:
        super()._build_ui()

        canvas_wrap = QWidget()
        canvas_wrap.setObjectName("MindDrawCanvasWrap")
        canvas_layout = QVBoxLayout(canvas_wrap)
        canvas_layout.setContentsMargins(0, 0, 0, 0)
        canvas_layout.setSpacing(10)

        self.hint_label = QLabel(
            "Связывайте узлы между собой и прикрепляйте к ним задачи, проекты, заметки, карты и другие сущности."
        )
        self.hint_label.setObjectName("MindDrawHint")
        self.hint_label.setWordWrap(True)
        canvas_layout.addWidget(self.hint_label)

        self.scene = QGraphicsScene(self)
        self.scene.setSceneRect(-2200, -1800, 4400, 3600)
        self.scene.selectionChanged.connect(self.update_action_states)

        self.view = QGraphicsView(self.scene)
        self.view.setObjectName("MindDrawCanvas")
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.view.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.view.setFrameShape(QFrame.Shape.NoFrame)
        self.view.setBackgroundBrush(QColor("#161a22"))
        self.view.viewport().setObjectName("MindDrawCanvasViewport")
        canvas_layout.addWidget(self.view, 1)

        self.set_content(canvas_wrap)

    def _apply_workspace_style(self) -> None:
        palette = get_theme_palette(self._theme_mode)
        canvas_gradient = (
            """
                qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #f7fbff,
                    stop: 0.55 #eef3fb,
                    stop: 1 #e6edf8
                )
            """
            if self._theme_mode == "light"
            else """
                qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #141821,
                    stop: 0.55 #171b24,
                    stop: 1 #10141b
                )
            """
        )
        self.setStyleSheet(
            f"""
            QWidget#MindDrawWorkspace {{
                background: {palette.window_bg};
            }}
            QWidget#MindDrawWorkspace QLabel {{
                color: {palette.text};
            }}
            QWidget#MindDrawWorkspace QWidget#WorkspaceToolbar,
            QWidget#MindDrawWorkspace QWidget#WorkspaceSearch,
            QWidget#MindDrawWorkspace QWidget#WorkspaceFilters {{
                background: {palette.panel_bg};
                border: 1px solid {palette.border};
                border-radius: 10px;
                padding: 6px;
            }}
            QWidget#MindDrawWorkspace QWidget#WorkspaceStatus {{
                color: {palette.dim_text};
            }}
            QWidget#MindDrawWorkspace QToolButton {{
                color: {palette.text};
                background: {palette.elevated_bg};
                border: 1px solid {palette.border_strong};
                border-radius: 7px;
                padding: 7px 12px;
                min-height: 28px;
            }}
            QWidget#MindDrawWorkspace QToolButton:hover {{
                background: {palette.selection_bg};
                color: {palette.selection_text};
            }}
            QWidget#MindDrawWorkspace QToolButton:disabled {{
                color: {palette.muted_text};
                background: {palette.panel_alt_bg};
                border-color: {palette.border};
            }}
            QWidget#MindDrawWorkspace QLineEdit {{
                background: {palette.input_bg};
                color: {palette.text};
                border: 1px solid {palette.border};
                border-radius: 8px;
                padding: 8px 10px;
            }}
            QWidget#MindDrawWorkspace QLineEdit:focus {{
                border-color: {palette.accent};
            }}
            QWidget#MindDrawCanvasWrap {{
                background: transparent;
            }}
            QLabel#MindDrawHint {{
                background: {palette.panel_bg};
                color: {palette.text};
                border: 1px solid {palette.border};
                border-radius: 12px;
                padding: 12px 14px;
            }}
            QGraphicsView#MindDrawCanvas {{
                background: {canvas_gradient};
                border: 1px solid {palette.border};
                border-radius: 16px;
            }}
            QWidget#MindDrawCanvasViewport {{
                background: transparent;
            }}
            QGraphicsView#MindDrawCanvas QScrollBar:vertical,
            QGraphicsView#MindDrawCanvas QScrollBar:horizontal {{
                background: {palette.panel_bg};
                border: none;
                margin: 8px;
            }}
            QGraphicsView#MindDrawCanvas QScrollBar::handle:vertical,
            QGraphicsView#MindDrawCanvas QScrollBar::handle:horizontal {{
                background: {palette.border_strong};
                border-radius: 6px;
                min-height: 28px;
                min-width: 28px;
            }}
            """
        )

    def set_theme_mode(self, theme_mode: str) -> None:
        self._theme_mode = "light" if str(theme_mode).strip().lower() == "light" else "dark"
        self._apply_workspace_style()
        if hasattr(self, "view"):
            palette = get_theme_palette(self._theme_mode)
            self.view.setBackgroundBrush(QColor(palette.chart_bg))
        self._refresh_link_styles()

    def create_actions(self) -> dict[str, QAction]:
        action_add = QAction("Добавить узел", self)
        action_add.triggered.connect(self._action_add_node)

        action_attach = QAction("Привязать сущность", self)
        action_attach.triggered.connect(self._action_attach_entity)

        action_link = QAction("Связать выбранные", self)
        action_link.triggered.connect(self._action_link_selected)

        action_unlink = QAction("Разорвать связь", self)
        action_unlink.triggered.connect(self._action_unlink_selected)

        action_delete = QAction("Удалить выбранные", self)
        action_delete.triggered.connect(self._action_delete_selected)

        action_clear = QAction("Очистить поле", self)
        action_clear.triggered.connect(self._action_clear)

        return {
            "add": action_add,
            "attach": action_attach,
            "link": action_link,
            "unlink": action_unlink,
            "delete": action_delete,
            "clear": action_clear,
        }

    def get_selection(self):
        return [item.node_id for item in self._selected_node_items()]

    def update_action_states(self) -> None:
        selected = self._selected_node_items()
        selected_count = len(selected)
        if "attach" in self.actions:
            self.actions["attach"].setEnabled(selected_count in {0, 1})
        if "link" in self.actions:
            self.actions["link"].setEnabled(selected_count == 2)
        if "unlink" in self.actions:
            self.actions["unlink"].setEnabled(selected_count == 2)
        if "delete" in self.actions:
            self.actions["delete"].setEnabled(selected_count > 0)
        if "clear" in self.actions:
            self.actions["clear"].setEnabled(bool(self._nodes))
        if "add" in self.actions:
            self.actions["add"].setEnabled(True)

    def apply_query(self, query: str) -> None:
        needle = (query or "").strip().lower()
        for node_id, state in self._nodes.items():
            item = self._node_items.get(node_id)
            if item is None:
                continue
            if not needle:
                item.setOpacity(1.0)
                continue
            haystack = f"{state.title} {state.entity_title} {state.entity_kind}".lower()
            item.setOpacity(1.0 if needle in haystack else 0.26)

    def _action_add_node(self) -> None:
        text, accepted = QInputDialog.getText(self, "Новый узел", "Название")
        if not accepted:
            return
        title = (text or "").strip() or f"Тема {len(self._nodes) + 1}"
        offset = float(len(self._nodes) * 42)
        self._create_node(title=title, x=-60.0 + offset, y=-24.0 + offset)
        self.set_status(f"Добавлен узел: {title}")

    def _action_attach_entity(self) -> None:
        dialog = MindDrawEntityPickerDialog(self._fetch_entity_options, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        option = dialog.selected_option()
        if option is None:
            return

        selected = self._selected_node_items()
        if len(selected) == 1:
            node_id = selected[0].node_id
            state = self._nodes[node_id]
            updated = MindDrawNodeState(
                node_id=state.node_id,
                title=option.title,
                x=state.x,
                y=state.y,
                entity_kind=option.kind,
                entity_id=option.entity_id,
                entity_title=option.title,
            )
            self._nodes[node_id] = updated
            self._sync_node_item(updated)
        else:
            self._create_node(
                title=option.title,
                x=-40.0 + len(self._nodes) * 36.0,
                y=-30.0 + len(self._nodes) * 32.0,
                entity_kind=option.kind,
                entity_id=option.entity_id,
                entity_title=option.title,
            )
        self.set_status(f"Привязана сущность: {option.kind}:{option.entity_id}")

    def _action_link_selected(self) -> None:
        selected = self._selected_node_items()
        if len(selected) != 2:
            QMessageBox.information(self, "MindDraw", "Выберите ровно 2 узла для связи.")
            return
        source_id = selected[0].node_id
        target_id = selected[1].node_id
        if source_id == target_id:
            return
        if self._has_link(source_id, target_id):
            QMessageBox.information(self, "MindDraw", "Эти узлы уже связаны.")
            return
        self._links.append(MindDrawLinkState(source_id=source_id, target_id=target_id))
        self._rebuild_links()
        self._save_canvas_state()

    def _action_unlink_selected(self) -> None:
        selected = self._selected_node_items()
        if len(selected) != 2:
            QMessageBox.information(self, "MindDraw", "Выберите 2 узла для удаления связи.")
            return
        source_id = selected[0].node_id
        target_id = selected[1].node_id
        before = len(self._links)
        self._links = [
            link
            for link in self._links
            if not (
                (link.source_id == source_id and link.target_id == target_id)
                or (link.source_id == target_id and link.target_id == source_id)
            )
        ]
        if len(self._links) != before:
            self._rebuild_links()
            self._save_canvas_state()

    def _action_delete_selected(self) -> None:
        selected = self._selected_node_items()
        if not selected:
            return
        for item in list(selected):
            self._remove_node(item.node_id)
        self._rebuild_links()
        self._save_canvas_state()

    def _action_clear(self) -> None:
        answer = QMessageBox.question(
            self,
            "Очистка MindDraw",
            "Удалить все узлы и связи?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        for node_id in list(self._nodes.keys()):
            self._remove_node(node_id)
        self._links.clear()
        self._rebuild_links()
        self._save_canvas_state()

    def _selected_node_items(self) -> list[MindDrawNodeItem]:
        selected: list[MindDrawNodeItem] = []
        for item in self.scene.selectedItems():
            if isinstance(item, MindDrawNodeItem):
                selected.append(item)
        return selected

    def _create_node(
        self,
        *,
        title: str,
        x: float,
        y: float,
        entity_kind: str = "",
        entity_id: Optional[int] = None,
        entity_title: str = "",
    ) -> MindDrawNodeState:
        node_id = uuid.uuid4().hex[:12]
        state = MindDrawNodeState(
            node_id=node_id,
            title=title,
            x=float(x),
            y=float(y),
            entity_kind=(entity_kind or "").strip(),
            entity_id=entity_id,
            entity_title=(entity_title or "").strip(),
        )
        self._nodes[node_id] = state
        self._add_node_item(state)
        self._save_canvas_state()
        self.update_action_states()
        return state

    def _add_node_item(self, state: MindDrawNodeState) -> None:
        item = MindDrawNodeItem(state, self._on_node_moved)
        item.setPos(QPointF(state.x, state.y))
        self.scene.addItem(item)
        self._node_items[state.node_id] = item

    def _sync_node_item(self, state: MindDrawNodeState) -> None:
        item = self._node_items.get(state.node_id)
        if item is None:
            self._add_node_item(state)
            return
        item.set_state(state)
        item.setPos(QPointF(state.x, state.y))

    def _remove_node(self, node_id: str) -> None:
        self._nodes.pop(node_id, None)
        item = self._node_items.pop(node_id, None)
        if item is not None:
            self.scene.removeItem(item)
        self._links = [link for link in self._links if link.source_id != node_id and link.target_id != node_id]

    def _on_node_moved(self, node_id: str, pos: QPointF) -> None:
        state = self._nodes.get(node_id)
        if state is None:
            return
        self._nodes[node_id] = MindDrawNodeState(
            node_id=state.node_id,
            title=state.title,
            x=float(pos.x()),
            y=float(pos.y()),
            entity_kind=state.entity_kind,
            entity_id=state.entity_id,
            entity_title=state.entity_title,
        )
        self._rebuild_links()
        self._save_canvas_state()

    def _has_link(self, source_id: str, target_id: str) -> bool:
        for link in self._links:
            if (link.source_id == source_id and link.target_id == target_id) or (
                link.source_id == target_id and link.target_id == source_id
            ):
                return True
        return False

    def _rebuild_links(self) -> None:
        for item in self._link_items.values():
            self.scene.removeItem(item)
        self._link_items.clear()

        valid_links: list[MindDrawLinkState] = []
        for link in self._links:
            source_item = self._node_items.get(link.source_id)
            target_item = self._node_items.get(link.target_id)
            if source_item is None or target_item is None:
                continue
            path_item = self._build_link_item(source_item, target_item)
            self.scene.addItem(path_item)
            path_item.setZValue(-10)
            self._link_items[(link.source_id, link.target_id)] = path_item
            valid_links.append(link)
        self._links = valid_links

    def _build_link_item(self, source_item: MindDrawNodeItem, target_item: MindDrawNodeItem) -> QGraphicsPathItem:
        start = source_item.sceneBoundingRect().center()
        end = target_item.sceneBoundingRect().center()
        dx = end.x() - start.x()
        dy = end.y() - start.y()
        distance = max(20.0, math.hypot(dx, dy))
        control_shift = min(90.0, distance * 0.25)

        path = QPainterPath(start)
        path.cubicTo(
            QPointF(start.x() + control_shift, start.y()),
            QPointF(end.x() - control_shift, end.y()),
            end,
        )

        angle = math.atan2(dy, dx)
        arrow_len = 10.0
        arrow_a = QPointF(
            end.x() - math.cos(angle - math.pi / 7) * arrow_len,
            end.y() - math.sin(angle - math.pi / 7) * arrow_len,
        )
        arrow_b = QPointF(
            end.x() - math.cos(angle + math.pi / 7) * arrow_len,
            end.y() - math.sin(angle + math.pi / 7) * arrow_len,
        )
        path.moveTo(end)
        path.lineTo(arrow_a)
        path.moveTo(end)
        path.lineTo(arrow_b)

        item = QGraphicsPathItem(path)
        palette = get_theme_palette(self._theme_mode)
        item.setPen(QPen(QColor(palette.accent), 2.0))
        return item

    def _refresh_link_styles(self) -> None:
        if not self._link_items:
            return
        palette = get_theme_palette(self._theme_mode)
        pen = QPen(QColor(palette.accent), 2.0)
        for item in self._link_items.values():
            item.setPen(pen)

    def _save_canvas_state(self) -> None:
        settings = QSettings()
        nodes = [self._nodes[node_id] for node_id in sorted(self._nodes.keys())]
        links = list(self._links)
        settings.setValue(self._STATE_KEY, serialize_minddraw_state(nodes, links))

    def _load_canvas_state(self) -> None:
        settings = QSettings()
        raw_value = settings.value(self._STATE_KEY, "", str)
        raw_state = raw_value if isinstance(raw_value, str) else ""
        nodes, links = deserialize_minddraw_state(raw_state)
        if not nodes:
            self._create_node(title="Central Topic", x=-110.0, y=-35.0)
            self.set_status("MindDraw готов к работе")
            return

        self._nodes.clear()
        self._links.clear()
        self._node_items.clear()
        self._link_items.clear()
        self.scene.clear()

        for state in nodes:
            self._nodes[state.node_id] = state
            self._add_node_item(state)
        self._links = links
        self._rebuild_links()
        self.set_status("Состояние MindDraw восстановлено")
        self.update_action_states()

    def _fetch_entity_options(self, kind: str, query: str) -> list[EntityOption]:
        needle = (query or "").strip().lower()

        def match(text: str) -> bool:
            if not needle:
                return True
            return needle in text.lower()

        options: list[EntityOption] = []
        if kind == "task":
            for task in self._db.fetch_tasks():
                if match(task.title):
                    options.append(EntityOption("task", task.id, task.title, task.day.isoformat()))
        elif kind == "project":
            for project in self._db.fetch_projects():
                title = f"{project.area} · {project.title}" if project.area else project.title
                if match(title):
                    options.append(EntityOption("project", project.id, project.title, project.area or ""))
        elif kind == "idea":
            for idea in self._db.fetch_ideas(archived=True):
                if match(idea.title):
                    options.append(EntityOption("idea", idea.id, idea.title, idea.project_title or ""))
        elif kind == "note":
            for note in self._db.fetch_notes():
                if match(note.title):
                    options.append(EntityOption("note", note.id, note.title, note.project or ""))
        elif kind == "map":
            for map_row in self._db.fetch_maps():
                if match(map_row.title):
                    options.append(EntityOption("map", map_row.id, map_row.title, map_row.project or ""))
        elif kind == "object":
            for obj in self._db.fetch_objects():
                title = f"{obj.title} · {obj.catalog}" if obj.catalog else obj.title
                if match(title):
                    options.append(EntityOption("object", obj.id, obj.title, obj.catalog or ""))
        elif kind == "character":
            for character in self._db.fetch_characters():
                title = f"{character.name} · {character.role}" if character.role else character.name
                if match(title):
                    options.append(EntityOption("character", character.id, character.name, character.role or ""))
        elif kind == "file":
            for file_item in self._db.fetch_cloud_files():
                title = file_item.name or file_item.rel_path
                if match(title):
                    options.append(EntityOption("file", file_item.id, title, file_item.rel_path or ""))
        elif kind == "collection":
            for item in self._db.fetch_collection_items():
                title = f"{item.title} · {item.topic}" if item.topic else item.title
                if match(title):
                    options.append(EntityOption("collection", item.id, item.title, item.topic or ""))
        elif kind == "purchase":
            for item in self._db.fetch_shop_items():
                if match(item.title):
                    options.append(EntityOption("purchase", item.id, item.title, "Покупки"))

        options.sort(key=lambda row: (row.title.lower(), row.entity_id))
        return options[:500]


__all__ = ["MindDrawWorkspace"]
