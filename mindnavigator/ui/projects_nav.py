"""Навигация по проектам в боковой панели.

Входные данные:
    События выбора списка и фильтрации проектов.

Выходные данные:
    Сигналы изменения фильтра и выбранного проекта.
"""

from PySide6.QtCore import Qt, Signal, QSignalBlocker
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem

from mindnavigator.storage import get_database, normalize_priority, ProjectData


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

        self.list = QListWidget()
        self.list.setObjectName("ProjectsFilterList")
        self.list.setSelectionMode(QListWidget.SingleSelection)
        self.list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list.currentItemChanged.connect(self._on_item_selected)
        self.list.itemDoubleClicked.connect(self._on_item_double_clicked)

        self._selected_key = None
        self._mode_name = "Задачи"
        self._collapsed_project_ids: set[int] = set()

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

        def root_key(project: ProjectData) -> tuple:
            priority = normalize_priority(project.priority)
            return (project.area.lower(), priority_order.get(priority, 4), project.title.lower(), project.id)

        def child_key(project: ProjectData) -> tuple:
            priority = normalize_priority(project.priority)
            return (project.sort_order, priority_order.get(priority, 4), project.title.lower(), project.id)

        for parent_id, items in children.items():
            if parent_id is None:
                items.sort(key=root_key)
            else:
                items.sort(key=child_key)

        entries: list[dict] = []

        def append_subtree(parent_id: object, depth: int) -> None:
            for project in children.get(parent_id, []):
                project_children = children.get(project.id, [])
                has_children = bool(project_children)
                is_expanded = project.id not in self._collapsed_project_ids
                marker = "? " if (has_children and is_expanded) else ("? " if has_children else "  ")
                entries.append(
                    {
                        "label": f"{'  ' * depth}{marker}{self._project_item_label(project)}",
                        "kind": "project",
                        "value": {"id": project.id, "title": project.title, "area": project.area},
                        "has_children": has_children,
                        "depth": depth,
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
