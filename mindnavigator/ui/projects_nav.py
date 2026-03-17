"""Навигация по проектам в боковой панели.

Входные данные:
    События выбора списка и фильтрации проектов.

Выходные данные:
    Сигналы изменения фильтра и выбранного проекта.
"""

from PySide6.QtCore import Qt, Signal, QSignalBlocker
from PySide6.QtGui import QCursor, QDragEnterEvent, QDragMoveEvent, QDropEvent, QMouseEvent
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QAbstractItemView,
    QToolTip,
)
from pathlib import Path
from typing import Optional

from mindnavigator.storage import get_database, normalize_priority, ProjectData
from mindnavigator.ui.styles import get_theme_palette


class _ProjectsListWidget(QListWidget):
    def __init__(self, owner: "ProjectsNav"):
        super().__init__(owner)
        self._owner = owner
        self._drag_source_project_id: int | None = None
        self._pressed_project_id: int | None = None
        self._press_pos = None

    @staticmethod
    def _dnd_log(message: str) -> None:
        try:
            root_dir = Path(__file__).resolve().parents[2]
            log_path = root_dir / ".codex" / "manual" / "dnd.log"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as fp:
                fp.write(message + "\n")
        except (OSError, IndexError):
            pass

    def log_dnd(self, message: str) -> None:
        self._dnd_log(message)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        item = self.itemAt(event.position().toPoint())
        payload = (item.data(Qt.ItemDataRole.UserRole) or {}) if item is not None else {}
        value = payload.get("value") or {}
        project_id = value.get("id") if payload.get("kind") == "project" else None
        self._pressed_project_id = project_id if isinstance(project_id, int) else None
        self._press_pos = event.position().toPoint()
        self._dnd_log(f"mousePress source={self._pressed_project_id}")
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            super().mouseMoveEvent(event)
            return
        if self._press_pos is None or self._pressed_project_id is None:
            super().mouseMoveEvent(event)
            return
        distance = (event.position().toPoint() - self._press_pos).manhattanLength()
        if distance < QApplication.startDragDistance():
            super().mouseMoveEvent(event)
            return
        self._drag_source_project_id = self._pressed_project_id
        print(f"[ProjectsNav DnD] mouseMove trigger source={self._drag_source_project_id}")
        self._dnd_log(f"mouseMove trigger source={self._drag_source_project_id}")
        self.startDrag(Qt.DropAction.MoveAction)
        self._press_pos = None

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        source = event.source()
        if source is self or source is self.viewport():
            event.acceptProposedAction()
            return
        if source is None:
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        source = event.source()
        if source is self or source is self.viewport():
            event.acceptProposedAction()
            return
        if source is None:
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def startDrag(self, supported_actions) -> None:
        current = self.currentItem()
        if self._pressed_project_id is not None:
            self._drag_source_project_id = self._pressed_project_id
            self._pressed_project_id = None
            print(f"[ProjectsNav DnD] startDrag source={self._drag_source_project_id}")
            self._dnd_log(f"startDrag source={self._drag_source_project_id}")
            super().startDrag(supported_actions)
            return
        if current is None:
            selected = self.selectedItems()
            current = selected[0] if selected else None
        payload = (current.data(Qt.ItemDataRole.UserRole) or {}) if current is not None else {}
        value = payload.get("value") or {}
        project_id = value.get("id") if payload.get("kind") == "project" else None
        self._drag_source_project_id = project_id if isinstance(project_id, int) else None
        print(f"[ProjectsNav DnD] startDrag source={self._drag_source_project_id}")
        self._dnd_log(f"startDrag source={self._drag_source_project_id}")
        super().startDrag(supported_actions)

    def dropEvent(self, event: QDropEvent) -> None:
        source_id = self._drag_source_project_id
        if not isinstance(source_id, int):
            source_item = self.currentItem()
            if source_item is None:
                selected = self.selectedItems()
                source_item = selected[0] if selected else None
            source_data = source_item.data(Qt.ItemDataRole.UserRole) if source_item is not None else None
            source_payload = source_data if isinstance(source_data, dict) else {}
            source_kind = source_payload.get("kind")
            source_value = source_payload.get("value") or {}
            source_id = source_value.get("id")
            if source_kind != "project" or not isinstance(source_id, int):
                print("[ProjectsNav DnD] dropEvent rejected: invalid source")
                self._dnd_log("dropEvent rejected: invalid source")
                self._show_drop_reject(event, "Перемещать можно только проекты.")
                event.ignore()
                self._drag_source_project_id = None
                return

        point = event.position().toPoint()
        target_index = self.indexAt(point)
        target_item = self.item(target_index.row()) if target_index.isValid() else None
        target_data = target_item.data(Qt.ItemDataRole.UserRole) if target_item is not None else None
        target_payload = target_data if isinstance(target_data, dict) else {}
        target_kind = target_payload.get("kind")
        target_value = target_payload.get("value") or {}
        target_id = target_value.get("id")

        # Drop to root is allowed on empty area and on pseudo-items (clear/section/empty).
        if target_item is None or target_kind in {"clear", "section", "empty"}:
            print(f"[ProjectsNav DnD] dropEvent source={source_id} target=root")
            self._dnd_log(f"dropEvent source={source_id} target=root")
            ok = self._owner.handle_project_drop(source_id, None, as_child=False, drop_after=True)
            if ok:
                event.acceptProposedAction()
                print("[ProjectsNav DnD] dropEvent accepted root move")
                self._dnd_log("dropEvent accepted root move")
            else:
                self._show_drop_reject(event, self._owner.last_drop_error)
                event.ignore()
                print(f"[ProjectsNav DnD] dropEvent rejected root move: {self._owner.last_drop_error}")
                self._dnd_log(f"dropEvent rejected root move: {self._owner.last_drop_error}")
            self._drag_source_project_id = None
            return

        if target_kind != "project" or not isinstance(target_id, int):
            print(f"[ProjectsNav DnD] dropEvent rejected: invalid target kind={target_kind}")
            self._dnd_log(f"dropEvent rejected: invalid target kind={target_kind}")
            self._show_drop_reject(event, "Перемещать можно только проекты.")
            event.ignore()
            self._drag_source_project_id = None
            return

        target_rect = self.visualItemRect(target_item)
        margin = max(4, target_rect.height() // 4)
        drop_before_zone = point.y() <= target_rect.top() + margin
        drop_after_zone = point.y() >= target_rect.bottom() - margin
        drop_after = point.y() > target_rect.center().y()
        target_depth = int(target_payload.get("depth") or 0)
        indent_x = target_depth * 16 + 18
        # Reparent only when dropping in the middle of row and far enough to the right.
        as_child = (not drop_before_zone and not drop_after_zone) and point.x() > (indent_x + 72)

        if target_id == source_id:
            direction = 1 if drop_after else -1
            idx = self.row(target_item) + direction
            candidate_id = None
            while 0 <= idx < self.count():
                candidate = self.item(idx)
                candidate_payload = (candidate.data(Qt.ItemDataRole.UserRole) or {}) if candidate is not None else {}
                candidate_value = candidate_payload.get("value") or {}
                raw_id = candidate_value.get("id") if candidate_payload.get("kind") == "project" else None
                if isinstance(raw_id, int):
                    candidate_id = raw_id
                    break
                idx += direction
            if candidate_id is None:
                event.accept()
                self._drag_source_project_id = None
                return
            target_id = candidate_id
            as_child = False
            drop_after = direction > 0

        ok = self._owner.handle_project_drop(source_id, target_id, as_child=as_child, drop_after=drop_after)
        print(
            f"[ProjectsNav DnD] dropEvent source={source_id} target={target_id} "
            f"as_child={as_child} drop_after={drop_after} ok={ok}"
        )
        self._dnd_log(
            f"dropEvent source={source_id} target={target_id} "
            f"as_child={as_child} drop_after={drop_after} ok={ok}"
        )
        if ok:
            event.setDropAction(Qt.DropAction.MoveAction)
            event.acceptProposedAction()
        else:
            self._show_drop_reject(event, self._owner.last_drop_error)
            event.ignore()
            print(f"[ProjectsNav DnD] dropEvent rejected: {self._owner.last_drop_error}")
            self._dnd_log(f"dropEvent rejected: {self._owner.last_drop_error}")
        self._drag_source_project_id = None

    def _show_drop_reject(self, _event: QDropEvent, message: str) -> None:
        text = (message or "").strip() or "Невалидный перенос проекта."
        point = QCursor.pos()
        QToolTip.showText(point, text, self)


class ProjectsNav(QWidget):
    """Панель навигации по проектам справа от левого меню."""

    project_filter_changed = Signal(object)
    filter_changed = Signal(str, object)

    def __init__(self, parent=None):
        """Создает и настраивает блок навигации проектов."""
        super().__init__(parent)
        self.setObjectName("ProjectsNav")
        self._theme_mode = "dark"
        self._ratio = 0.12
        self._min_w = 220
        self._max_w = 420
        self._fixed_h = 420

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        self.header = QLabel("Проекты")
        self.header.setObjectName("ProjectsHeader")

        self.hint = QLabel("Фильтрация задач по проектам")
        self.hint.setObjectName("ProjectsHint")
        self.hint.setWordWrap(True)

        self.list = _ProjectsListWidget(self)
        self.list.setObjectName("ProjectsFilterList")
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.list.setDragEnabled(True)
        self.list.setAcceptDrops(True)
        self.list.viewport().setAcceptDrops(True)
        self.list.setDropIndicatorShown(True)
        self.list.currentItemChanged.connect(self._on_item_selected)
        self.list.itemDoubleClicked.connect(self._on_item_double_clicked)

        self._selected_key = None
        self._mode_name = "Задачи"
        self._collapsed_project_ids: set[int] = set()
        self._last_drop_error = ""

        layout.addWidget(self.header)
        layout.addWidget(self.hint)
        layout.addWidget(self.list, 1)
        layout.addStretch(0)

        self._populate_for_mode(self._mode_name)

        self.setFixedHeight(self._fixed_h)

        self.set_theme_mode("dark")

    def set_theme_mode(self, theme_mode: str) -> None:
        self._theme_mode = "light" if str(theme_mode).strip().lower() == "light" else "dark"
        palette = get_theme_palette(self._theme_mode)
        self.setStyleSheet(
            f"""
            QWidget#ProjectsNav {{
                background: {palette.panel_bg};
                border-right: 1px solid {palette.border};
            }}
            QLabel#ProjectsHeader {{
                color: {palette.text};
                font-size: 13px;
                font-weight: 600;
            }}
            QLabel#ProjectsHint {{
                color: {palette.dim_text};
                font-size: 12px;
            }}
            QListWidget#ProjectsFilterList {{
                background: {palette.window_bg};
                border: 1px solid {palette.border};
                color: {palette.text};
            }}
            QListWidget#ProjectsFilterList::item {{
                padding: 6px 8px;
            }}
            QListWidget#ProjectsFilterList::item:selected {{
                background: {palette.selection_bg};
                color: {palette.selection_text};
            }}
        """
        )

    def _populate_for_mode(self, mode_name: str):
        """Заполняет список навигации для активного режима."""
        selected_key = self._selected_key
        self.list.clear()
        header = "Навигация"
        hint = "Навигация (пока пусто)"
        if mode_name == "Задачи":
            header = "Проекты"
            hint = "Фильтрация задач по проектам"
            self._add_clear_item("Все проекты")
            self._add_entries(self._project_entries())
        elif mode_name == "Проекты":
            header = "Задачи"
            hint = "Фильтрация проектов по задачам"
            self._add_clear_item("Все задачи")
            self._add_entries(self._task_entries())
        elif mode_name == "Файлы":
            header = "Проекты"
            hint = "Фильтрация файлов по проектам"
            self._add_clear_item("Все проекты")
            self._add_entries(self._project_entries())
        elif mode_name == "Карты":
            header = "Проекты"
            hint = "Фильтрация карт по проектам"
            self._add_clear_item("Все проекты")
            self._add_entries(self._project_entries())
        elif mode_name == "Заметки":
            header = "Задачи и карты"
            hint = "Фильтрация заметок по задачам или проектам карт"
            self._add_clear_item("Без фильтра")
            self._add_section("Задачи", self._task_entries())
            self._add_section("Карты", self._map_entries())
        elif mode_name == "Объекты":
            header = "Проекты и метки"
            hint = "Фильтрация объектов по проектам, задачам и меткам"
            self._add_clear_item("Без фильтра")
            self._add_section("Проекты", self._project_entries())
            self._add_section("Задачи", self._task_entries())
            self._add_section("Метки на карте", self._marker_entries())

        self.header.setText(header)
        self.hint.setText(hint)
        self._select_key(selected_key)

    def _add_clear_item(self, label: str) -> None:
        item = QListWidgetItem(label)
        clear_flags = Qt.ItemFlags(Qt.ItemFlag.ItemIsEnabled)
        clear_flags |= Qt.ItemFlag.ItemIsSelectable
        item.setFlags(clear_flags)
        item.setData(Qt.ItemDataRole.UserRole, {"kind": "clear", "value": None})
        self.list.addItem(item)

    def _add_section(self, title: str, entries: list[dict]) -> None:
        if title:
            header_item = QListWidgetItem(title)
            header_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            header_item.setForeground(Qt.GlobalColor.gray)
            header_item.setData(Qt.ItemDataRole.UserRole, {"kind": "section", "value": None})
            self.list.addItem(header_item)
        self._add_entries(entries)

    def _add_entries(self, entries: list[dict]) -> None:
        if not entries:
            empty = QListWidgetItem("— нет данных —")
            empty.setFlags(Qt.ItemFlag.ItemIsEnabled)
            empty.setForeground(Qt.GlobalColor.gray)
            empty.setData(Qt.ItemDataRole.UserRole, {"kind": "empty", "value": None})
            self.list.addItem(empty)
            return
        for entry in entries:
            item = QListWidgetItem(entry["label"])
            if entry.get("kind") == "project":
                item_flags = Qt.ItemFlags(Qt.ItemFlag.ItemIsEnabled)
                item_flags |= Qt.ItemFlag.ItemIsSelectable
                item_flags |= Qt.ItemFlag.ItemIsDragEnabled
                item_flags |= Qt.ItemFlag.ItemIsDropEnabled
                item.setFlags(item_flags)
            else:
                item_flags = Qt.ItemFlags(Qt.ItemFlag.ItemIsEnabled)
                item_flags |= Qt.ItemFlag.ItemIsSelectable
                item.setFlags(item_flags)
            item.setData(Qt.ItemDataRole.UserRole, entry)
            self.list.addItem(item)

    def _select_key(self, key):
        if self.list.count() == 0:
            return
        fallback_index = 0
        for idx in range(self.list.count()):
            item = self.list.item(idx)
            data = item.data(Qt.ItemDataRole.UserRole) or {}
            if data.get("kind") in {"section", "empty"}:
                continue
            if key is not None and data == key:
                self.list.setCurrentRow(idx)
                return
        self.list.setCurrentRow(fallback_index)

    @staticmethod
    def _project_item_label(project: ProjectData) -> str:
        suffix = " · архив" if project.archived else ""
        return f"{project.area} · {project.title}{suffix}"

    def _project_entries(self) -> list[dict]:
        priority_order = {"High": 0, "Medium": 1, "Low": 2, "Отложенная": 3}
        projects = get_database().fetch_projects()
        by_id = {project.id: project for project in projects}
        children: dict[object, list[ProjectData]] = {}

        for project in projects:
            parent_id = project.parent_project_id if project.parent_project_id in by_id else None
            children.setdefault(parent_id, []).append(project)

        def sibling_key(project: ProjectData) -> tuple:
            priority = normalize_priority(project.priority)
            return project.sort_order, priority_order.get(priority, 4), project.title.lower(), project.id

        for parent_key, items in children.items():
            items.sort(key=sibling_key)

        entries: list[dict] = []

        def append_subtree(node_parent_id: object, depth: int) -> None:
            for project in children.get(node_parent_id, []):
                project_children = children.get(project.id, [])
                has_children = bool(project_children)
                is_expanded = project.id not in self._collapsed_project_ids
                marker = "v " if (has_children and is_expanded) else ("> " if has_children else "  ")
                entries.append(
                    {
                        "label": f"{'  ' * depth}{marker}{self._project_item_label(project)}",
                        "kind": "project",
                        "value": {"id": project.id, "title": project.title, "area": project.area},
                        "has_children": has_children,
                        "depth": depth,
                        "parent_id": project.parent_project_id,
                        "sort_order": project.sort_order,
                    }
                )
                if has_children and is_expanded:
                    append_subtree(project.id, depth + 1)

        append_subtree(None, 0)
        return entries

    @staticmethod
    def _task_entries() -> list[dict]:
        tasks = sorted(
            get_database().fetch_tasks(),
            key=lambda t: (t.day, t.time_text or "", t.title.lower()),
        )
        entries = []
        for task in tasks:
            label = task.title
            if task.project_title:
                label = f"{task.title} · {task.project_title}"
            entries.append(
                {"label": label, "kind": "task", "value": {"id": task.id, "project_id": task.project_id}}
            )
        return entries

    @staticmethod
    def _map_entries() -> list[dict]:
        maps = sorted(get_database().fetch_maps(), key=lambda m: m.title.lower())
        entries = []
        for item in maps:
            label = item.title
            if item.project:
                label = f"{item.title} · {item.project}"
            entries.append(
                {"label": label, "kind": "map", "value": {"id": item.id, "project": item.project}}
            )
        return entries

    @staticmethod
    def _marker_entries() -> list[dict]:
        maps = {m.id: m.title for m in get_database().fetch_maps()}
        markers = sorted(
            get_database().fetch_map_markers(),
            key=lambda m: (maps.get(m.map_id, "").lower(), m.name.lower()),
        )
        entries = []
        for marker in markers:
            map_title = maps.get(marker.map_id, "Без карты")
            label = f"{marker.name} · {map_title}"
            entries.append(
                {
                    "label": label,
                    "kind": "marker",
                    "value": {
                        "id": marker.id,
                        "map_id": marker.map_id,
                        "object_ids": marker.object_ids,
                    },
                }
            )
        return entries

    def _on_item_selected(self, current: Optional[QListWidgetItem], _previous: Optional[QListWidgetItem]) -> None:
        """Обрабатывает выбор элемента для фильтрации."""
        if current is None:
            self._selected_key = None
            self.filter_changed.emit("clear", None)
            self.project_filter_changed.emit(None)
            return
        data = current.data(Qt.ItemDataRole.UserRole) or {}
        kind = data.get("kind")
        value = data.get("value")
        if kind in {"section", "empty"}:
            return
        self._selected_key = data
        if kind == "project":
            self.project_filter_changed.emit(value["id"])
        elif kind == "clear":
            self.project_filter_changed.emit(None)
        self.filter_changed.emit(kind or "clear", value)

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        data = item.data(Qt.ItemDataRole.UserRole) or {}
        if data.get("kind") != "project" or not data.get("has_children"):
            return
        value = data.get("value") or {}
        project_id = value.get("id")
        if not isinstance(project_id, int):
            return
        if project_id in self._collapsed_project_ids:
            self._collapsed_project_ids.remove(project_id)
        else:
            self._collapsed_project_ids.add(project_id)
        with QSignalBlocker(self.list):
            self._populate_for_mode(self._mode_name)
        current = self.list.currentItem()
        if current is not None:
            self._on_item_selected(current, None)

    def _handle_project_drop(
        self,
        source_project_id: int,
        target_project_id: int | None,
        as_child: bool,
        drop_after: bool,
    ) -> bool:
        print(
            f"[ProjectsNav DnD] _handle_project_drop source={source_project_id} "
            f"target={target_project_id} as_child={as_child} drop_after={drop_after}"
        )
        self.list.log_dnd(
            f"_handle_project_drop source={source_project_id} "
            f"target={target_project_id} as_child={as_child} drop_after={drop_after}"
        )
        db = get_database()
        self._last_drop_error = ""
        projects = db.fetch_projects()
        by_id = {project.id: project for project in projects}

        if source_project_id not in by_id:
            self._last_drop_error = "Проект-источник не найден."
            return False
        if target_project_id is not None and target_project_id not in by_id:
            self._last_drop_error = "Целевой проект не найден."
            return False

        if target_project_id is None:
            new_parent_id = None
        elif as_child:
            new_parent_id = target_project_id
        else:
            new_parent_id = by_id[target_project_id].parent_project_id

        is_valid, reason = self._validate_project_relocation(
            by_id=by_id,
            source_project_id=source_project_id,
            target_project_id=target_project_id,
            new_parent_id=new_parent_id,
        )
        if not is_valid:
            self._last_drop_error = reason
            return False

        try:
            if target_project_id is None:
                db.move_project(source_project_id, None, None)
            elif as_child:
                db.move_project(source_project_id, target_project_id, None)
            else:
                target = by_id.get(target_project_id)
                if target is None:
                    self._last_drop_error = "Целевой проект не найден."
                    return False
                parent_id = target.parent_project_id
                siblings = db.fetch_project_children(parent_id)
                sibling_ids = [p.id for p in siblings if p.id != source_project_id]
                if target_project_id not in sibling_ids:
                    self._last_drop_error = "Невалидная позиция переноса."
                    return False
                index = sibling_ids.index(target_project_id)
                if drop_after:
                    index += 1
                db.move_project(source_project_id, parent_id, index)
        except ValueError as exc:
            self._last_drop_error = str(exc)
            return False

        with QSignalBlocker(self.list):
            self._populate_for_mode(self._mode_name)

        selected = None
        for idx in range(self.list.count()):
            item = self.list.item(idx)
            if item is None:
                continue
            data = item.data(Qt.ItemDataRole.UserRole) or {}
            value = data.get("value") or {}
            if data.get("kind") == "project" and value.get("id") == source_project_id:
                selected = item
                self.list.setCurrentRow(idx)
                break
        if selected is not None:
            self._on_item_selected(selected, None)
        return True

    @property
    def last_drop_error(self) -> str:
        return self._last_drop_error

    def handle_project_drop(
        self,
        source_project_id: int,
        target_project_id: int | None,
        as_child: bool,
        drop_after: bool,
    ) -> bool:
        return self._handle_project_drop(source_project_id, target_project_id, as_child=as_child, drop_after=drop_after)

    @staticmethod
    def _validate_project_relocation(
        by_id: dict[int, ProjectData],
        source_project_id: int,
        target_project_id: int | None,
        new_parent_id: int | None,
    ) -> tuple[bool, str]:
        max_depth_index = 3  # 4 levels in total (0..3)
        children: dict[object, list[int]] = {}
        for project_row in by_id.values():
            parent_id = project_row.parent_project_id if project_row.parent_project_id in by_id else None
            children.setdefault(parent_id, []).append(project_row.id)

        descendants: set[int] = set()
        stack = [source_project_id]
        while stack:
            current = stack.pop()
            for child_id in children.get(current, []):
                if child_id not in descendants:
                    descendants.add(child_id)
                    stack.append(child_id)

        if new_parent_id == source_project_id:
            return False, "Нельзя переместить проект внутрь самого себя."
        if new_parent_id in descendants:
            return False, "Нельзя переместить проект внутрь его потомка."

        depth_cache: dict[int, int] = {}

        def node_depth(project_id: int) -> int:
            if project_id in depth_cache:
                return depth_cache[project_id]
            project = by_id.get(project_id)
            if project is None or project.parent_project_id not in by_id:
                depth_cache[project_id] = 0
                return 0
            depth = node_depth(project.parent_project_id) + 1
            depth_cache[project_id] = depth
            return depth

        subtree_height_cache: dict[int, int] = {}

        def subtree_height(project_id: int) -> int:
            if project_id in subtree_height_cache:
                return subtree_height_cache[project_id]
            child_ids = children.get(project_id, [])
            if not child_ids:
                subtree_height_cache[project_id] = 0
                return 0
            height = 1 + max(subtree_height(child_node_id) for child_node_id in child_ids)
            subtree_height_cache[project_id] = height
            return height

        parent_depth = -1 if new_parent_id is None else node_depth(new_parent_id)
        projected_root_depth = parent_depth + 1
        projected_max_depth = projected_root_depth + subtree_height(source_project_id)
        if projected_max_depth > max_depth_index:
            return False, "Превышена максимальная глубина вложенности проектов (4 уровня)."

        if target_project_id is not None and target_project_id not in by_id:
            return False, "Целевой проект не найден."

        return True, ""

    def update_width_for_window(self, window_width: int):
        """Пересчитывает ширину панели в зависимости от ширины окна."""
        w = int(window_width * self._ratio)
        w = max(self._min_w, min(self._max_w, w))
        self.setFixedWidth(w)

    def set_mode_title(self, mode_name: str):
        """Обновляет заголовок панели для активного режима."""
        self._mode_name = mode_name
        with QSignalBlocker(self.list):
            self._populate_for_mode(mode_name)
        current = self.list.currentItem()
        if current is not None:
            self._on_item_selected(current, None)


