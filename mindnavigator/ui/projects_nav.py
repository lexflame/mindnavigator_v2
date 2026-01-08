from PySide6.QtCore import Qt, Signal, QSignalBlocker
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem

from mindnavigator.storage import get_database, ProjectData


class ProjectsNav(QWidget):
    """Панель навигации по проектам справа от левого меню."""

    project_filter_changed = Signal(object)

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
        self.list.currentItemChanged.connect(self._on_project_selected)

        self._selected_project_id = None

        layout.addWidget(self.header)
        layout.addWidget(self.hint)
        layout.addWidget(self.list, 1)
        layout.addStretch(0)

        self._populate_projects()

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
            QListWidget#ProjectsFilterList QScrollBar:vertical {
                background: #16171a;
                width: 6px;
                margin: 2px;
            }
            QListWidget#ProjectsFilterList QScrollBar::handle:vertical {
                background: #2a2b2f;
                border-radius: 3px;
                min-height: 24px;
            }
            QListWidget#ProjectsFilterList QScrollBar::handle:vertical:hover {
                background: #3a3c42;
            }
            QListWidget#ProjectsFilterList QScrollBar::add-line:vertical,
            QListWidget#ProjectsFilterList QScrollBar::sub-line:vertical {
                height: 0;
            }
            QListWidget#ProjectsFilterList QScrollBar::add-page:vertical,
            QListWidget#ProjectsFilterList QScrollBar::sub-page:vertical {
                background: none;
            }
            QListWidget#ProjectsFilterList::item {
                padding: 6px 8px;
            }
            QListWidget#ProjectsFilterList::item:selected {
                background: #2a2b2f;
            }
        """)

    def _populate_projects(self):
        """Заполняет список доступными проектами."""
        selected_id = self._selected_project_id
        self.list.clear()
        all_item = QListWidgetItem("Все проекты")
        all_item.setData(Qt.UserRole, None)
        self.list.addItem(all_item)

        projects = sorted(get_database().fetch_projects(), key=lambda p: (p.area.lower(), p.title.lower()))
        for project in projects:
            self.list.addItem(self._project_item(project))

        self._select_project_id(selected_id)

    def _select_project_id(self, project_id):
        """Выбирает проект по id, если он есть в списке."""
        if self.list.count() == 0:
            return
        fallback_index = 0
        for idx in range(self.list.count()):
            item = self.list.item(idx)
            if item.data(Qt.UserRole) == project_id:
                self.list.setCurrentRow(idx)
                return
        self.list.setCurrentRow(fallback_index)

    def _project_item(self, project: ProjectData) -> QListWidgetItem:
        """Создает элемент списка проекта."""
        suffix = " · архив" if project.archived else ""
        text = f"{project.area} · {project.title}{suffix}"
        item = QListWidgetItem(text)
        item.setData(Qt.UserRole, project.id)
        return item

    def _on_project_selected(self, current: QListWidgetItem, previous: QListWidgetItem):
        """Обрабатывает выбор проекта для фильтрации."""
        if current is None:
            self._selected_project_id = None
            self.project_filter_changed.emit(None)
            return
        project_id = current.data(Qt.UserRole)
        self._selected_project_id = project_id
        self.project_filter_changed.emit(project_id)

    def update_width_for_window(self, window_width: int):
        """Пересчитывает ширину панели в зависимости от ширины окна."""
        w = int(window_width * self._ratio)
        w = max(self._min_w, min(self._max_w, w))
        self.setFixedWidth(w)

    def set_mode_title(self, mode_name: str):
        """Обновляет заголовок панели для активного режима."""
        self.header.setText(f"Проекты · {mode_name}")
        is_tasks = mode_name == "Задачи"
        if not is_tasks:
            current = self.list.currentItem()
            self._selected_project_id = current.data(Qt.UserRole) if current else None
        with QSignalBlocker(self.list):
            self.hint.setVisible(is_tasks)
            self.list.setVisible(is_tasks)
            if is_tasks:
                self.hint.setText("Фильтрация задач по проектам")
                self._select_project_id(self._selected_project_id)
            else:
                self.hint.setText("Навигация (пока пусто)")
