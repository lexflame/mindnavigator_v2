"""Навигация по проектам в боковой панели.

Входные данные:
    События выбора списка и фильтрации проектов.

Выходные данные:
    Сигналы изменения фильтра и выбранного проекта.
"""

from PySide6.QtCore import Qt, Signal, QSignalBlocker
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QAbstractItemView,
    QToolTip,
)

from mindnavigator.storage import get_database, normalize_priority, ProjectData


class _ProjectsListWidget(QListWidget):
    def __init__(self, owner: "ProjectsNav"):
        super().__init__(owner)
        self._owner = owner
        self._drag_source_project_id: int | None = None

    def startDrag(self, supportedActions):
        current = self.currentItem()
        payload = (current.data(Qt.UserRole) or {}) if current is not None else {}
        value = payload.get("value") or {}
        project_id = value.get("id") if payload.get("kind") == "project" else None
        self._drag_source_project_id = project_id if isinstance(project_id, int) else None
        super().startDrag(supportedActions)

    def dropEvent(self, event):
        source_id = self._drag_source_project_id
        if not isinstance(source_id, int):
            source_item = self.currentItem()
            source_data = source_item.data(Qt.UserRole) if source_item is not None else None
            source_payload = source_data if isinstance(source_data, dict) else {}
            source_kind = source_payload.get("kind")
            source_value = source_payload.get("value") or {}
            source_id = source_value.get("id")
            if source_kind != "project" or not isinstance(source_id, int):
                self._show_drop_reject(event, "Перемещать можно только проекты.")
                event.ignore()
                self._drag_source_project_id = None
                return

        target_item = self.itemAt(event.position().toPoint())
        target_data = target_item.data(Qt.UserRole) if target_item is not None else None
        target_payload = target_data if isinstance(target_data, dict) else {}
        target_kind = target_payload.get("kind")
        target_value = target_payload.get("value") or {}
        target_id = target_value.get("id")

        # Drop to root is allowed on empty area and on pseudo-items (clear/section/empty).
        if target_item is None or target_kind in {"clear", "section", "empty"}:
            ok = self._owner._handle_project_drop(source_id, None, as_child=False, drop_after=True)
            if ok:
                event.acceptProposedAction()
            else:
                self._show_drop_reject(event, self._owner._last_drop_error)
                event.ignore()
            self._drag_source_project_id = None
            return

        if target_kind != "project" or not isinstance(target_id, int):
            self._show_drop_reject(event, "Перемещать можно только проекты.")
            event.ignore()
            self._drag_source_project_id = None
            return

        target_rect = self.visualItemRect(target_item)
        point = event.position().toPoint()
        margin = max(4, target_rect.height() // 4)
        drop_before_zone = point.y() <= target_rect.top() + margin
        drop_after_zone = point.y() >= target_rect.bottom() - margin
        drop_after = point.y() > target_rect.center().y()
        target_depth = int(target_payload.get("depth") or 0)
        indent_x = target_depth * 16 + 18
        # Reparent only when dropping in the middle of row and far enough to the right.
        as_child = (not drop_before_zone and not drop_after_zone) and point.x() > (indent_x + 42)
        ok = self._owner._handle_project_drop(source_id, target_id, as_child=as_child, drop_after=drop_after)
        if ok:
            event.acceptProposedAction()
        else:
            self._show_drop_reject(event, self._owner._last_drop_error)
            event.ignore()
        self._drag_source_project_id = None

    def _show_drop_reject(self, event, message: str) -> None:
        text = (message or "").strip() or "Невалидный перенос проекта."
        QToolTip.showText(event.globalPosition().toPoint(), text, self)


class ProjectsNav(QWidget):
    """Панель навигации по проектам справа от левого меню."""

    project_filter_changed = Signal(object)
    filter_changed = Signal(str, object)

    def __init__(self, parent=None):
        """Создает и настраивает блок навигации проектов."""
        super().__init__(parent)
        self.setObjectName("ProjectsNav")
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
        self.list.setSelectionMode(QListWidget.SingleSelection)
        self.list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list.setDragDropMode(QAbstractItemView.DragDrop)
        self.list.setDefaultDropAction(Qt.MoveAction)
        self.list.setDragEnabled(True)
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

        self.setStyleSheet("""
            QWidget#ProjectsNav {
                background: #191a1d;
                border-right: 1px solid #2a2b2f;
            }
            QLabel#ProjectsHeader {
                color: #cfcfcf;
                font-size: 13px;
                font-weight: 600;
            }
            QLabel#ProjectsHint {
                color: #7a7a7a;
                font-size: 12px;
            }
            QListWidget#ProjectsFilterList {
                background: #16171a;
                border: 1px solid #2a2b2f;
                color: #cfcfcf;
            }
            QListWidget#ProjectsFilterList::item {
                padding: 6px 8px;
            }
            QListWidget#ProjectsFilterList::item:selected {
                background: #2a2b2f;
            }
        """)

    def _populate_for_mode(self, mode_name: str):
        """Заполняет список навигации для активного режима."""
        selected_key = self._selected_key
        self.list.clear()
        entries = []
        hint = ""
        header = mode_name
        if mode_name == "Задачи":
            header = "Проекты"
            hint = "Фильтрация задач по проектам"
            entries = self._project_entries()
            self._add_clear_item("Все проекты")
            self._add_entries(entries)
        elif mode_name == "Проекты":
            header = "Задачи"
            hint = "Фильтрация проектов по задачам"
            entries = self._task_entries()
            self._add_clear_item("Все задачи")
            self._add_entries(entries)
        elif mode_name == "Файлы":
            header = "Проекты"
            hint = "Фильтрация файлов по проектам"
            entries = self._project_entries()
            self._add_clear_item("Все проекты")
            self._add_entries(entries)
        elif mode_name == "Карты":
            header = "Проекты"
            hint = "Фильтрация карт по проектам"
            entries = self._project_entries()
            self._add_clear_item("Все проекты")
            self._add_entries(entries)
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
        else:
            header = "Навигация"
            hint = "Навигация (пока пусто)"

        self.header.setText(header)
        self.hint.setText(hint)
        self._select_key(selected_key)

    def _add_clear_item(self, label: str) -> None:
        item = QListWidgetItem(label)
        item.setData(Qt.UserRole, {"kind": "clear", "value": None})
        self.list.addItem(item)

    def _add_section(self, title: str, entries: list[dict]) -> None:
        if title:
            header_item = QListWidgetItem(title)
            header_item.setFlags(Qt.ItemIsEnabled)
            header_item.setForeground(Qt.gray)
            header_item.setData(Qt.UserRole, {"kind": "section", "value": None})
            self.list.addItem(header_item)
        self._add_entries(entries)

    def _add_entries(self, entries: list[dict]) -> None:
        if not entries:
            empty = QListWidgetItem("— нет данных —")
            empty.setFlags(Qt.ItemIsEnabled)
            empty.setForeground(Qt.gray)
            empty.setData(Qt.UserRole, {"kind": "empty", "value": None})
            self.list.addItem(empty)
            return
        for entry in entries:
            item = QListWidgetItem(entry["label"])
            item.setData(Qt.UserRole, entry)
            self.list.addItem(item)

    def _select_key(self, key):
        if self.list.count() == 0:
            return
        fallback_index = 0
        for idx in range(self.list.count()):
            item = self.list.item(idx)
            data = item.data(Qt.UserRole) or {}
            if data.get("kind") in {"section", "empty"}:
                continue
            if key is not None and data == key:
                self.list.setCurrentRow(idx)
                return
        self.list.setCurrentRow(fallback_index)

    def _project_item_label(self, project: ProjectData) -> str:
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
            return (project.sort_order, priority_order.get(priority, 4), project.title.lower(), project.id)

        for parent_id, items in children.items():
            items.sort(key=sibling_key)

        entries: list[dict] = []

        def append_subtree(parent_id: object, depth: int) -> None:
            for project in children.get(parent_id, []):
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

    def _task_entries(self) -> list[dict]:
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

    def _map_entries(self) -> list[dict]:
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

    def _marker_entries(self) -> list[dict]:
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

    def _on_item_selected(self, current: QListWidgetItem, previous: QListWidgetItem):
        """Обрабатывает выбор элемента для фильтрации."""
        if current is None:
            self._selected_key = None
            self.filter_changed.emit("clear", None)
            self.project_filter_changed.emit(None)
            return
        data = current.data(Qt.UserRole) or {}
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
        data = item.data(Qt.UserRole) or {}
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
            data = item.data(Qt.UserRole) or {}
            value = data.get("value") or {}
            if data.get("kind") == "project" and value.get("id") == source_project_id:
                selected = item
                self.list.setCurrentRow(idx)
                break
        if selected is not None:
            self._on_item_selected(selected, None)
        return True

    def _validate_project_relocation(
        self,
        by_id: dict[int, ProjectData],
        source_project_id: int,
        target_project_id: int | None,
        new_parent_id: int | None,
    ) -> tuple[bool, str]:
        max_depth_index = 3  # 4 levels in total (0..3)
        children: dict[object, list[int]] = {}
        for project in by_id.values():
            parent_id = project.parent_project_id if project.parent_project_id in by_id else None
            children.setdefault(parent_id, []).append(project.id)

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
            height = 1 + max(subtree_height(child_id) for child_id in child_ids)
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
