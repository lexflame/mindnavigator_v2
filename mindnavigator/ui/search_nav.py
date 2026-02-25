"""Панель поиска и фильтрации задач/объектов.

Входные данные:
    Текстовый запрос и события выбора результата.

Выходные данные:
    Сигналы активации результата поиска.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QAbstractItemView,
)

from mindnavigator.storage import get_database

_COLLECTION_ENTITY_LABELS = {
    "building": "Здание",
    "city": "Город",
    "film": "Фильм",
    "game": "Игра",
    "character": "Персонаж",
    "other": "Другое",
}


class SearchNav(QWidget):
    """Панель быстрого поиска по всем сущностям приложения."""

    resultActivated = Signal(dict)

    def __init__(self, parent=None):
        """Создает и настраивает блок быстрого поиска."""
        super().__init__(parent)
        self.setObjectName("SearchNav")
        self._ratio = 0.12
        self._min_w = 220
        self._max_w = 420
        self._fixed_h = 420
        self._db = get_database()
        self._max_results = 8

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        self.header = QLabel("Поиск")
        self.header.setObjectName("SearchHeader")

        self.hint = QLabel("Быстрый поиск по всем сущностям")
        self.hint.setObjectName("SearchHint")
        self.hint.setWordWrap(True)

        self.input = QLineEdit()
        self.input.setObjectName("SearchInput")
        self.input.setPlaceholderText("Проекты, задачи, заметки, файлы…")
        self.input.setClearButtonEnabled(True)
        self.input.textChanged.connect(self._update_results)

        self.results = QWidget()
        self.results.setObjectName("SearchResults")
        self.results_layout = QVBoxLayout(self.results)
        self.results_layout.setContentsMargins(8, 8, 8, 8)
        self.results_layout.setSpacing(6)

        self.results_title = QLabel("Результаты поиска")
        self.results_title.setObjectName("SearchResultsTitle")

        self.results_placeholder = QLabel("Начните ввод, чтобы увидеть совпадения")
        self.results_placeholder.setObjectName("SearchResultsPlaceholder")
        self.results_placeholder.setWordWrap(True)

        self.results_list = QListWidget()
        self.results_list.setObjectName("SearchResultsList")
        self.results_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.results_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.results_list.setVisible(False)
        self.results_list.itemDoubleClicked.connect(self._on_result_double_clicked)

        self.results_layout.addWidget(self.results_title)
        self.results_layout.addWidget(self.results_placeholder)
        self.results_layout.addWidget(self.results_list)
        self.results_layout.addStretch(1)

        layout.addWidget(self.header)
        layout.addWidget(self.hint)
        layout.addWidget(self.input)
        layout.addWidget(self.results)
        layout.addStretch(1)

        self.setFixedHeight(self._fixed_h)

        self.setStyleSheet("""
            QWidget#SearchNav {
                background: #191a1d;
                border-right: 1px solid #2a2b2f;
                border-top: 1px solid #2a2b2f;
            }
            QLabel#SearchHeader {
                color: #cfcfcf;
                font-size: 13px;
                font-weight: 600;
            }
            QLabel#SearchHint {
                color: #7a7a7a;
                font-size: 12px;
            }
            QLineEdit#SearchInput {
                background: #16171a;
                border: 1px solid #2a2b2f;
                border-radius: 4px;
                color: #cfcfcf;
                padding: 6px 8px;
            }
            QLineEdit#SearchInput:focus {
                border: 1px solid #3a3c42;
            }
            QWidget#SearchResults {
                background: #151618;
                border: 1px solid #242529;
                border-radius: 6px;
            }
            QLabel#SearchResultsTitle {
                color: #b9bcc4;
                font-size: 12px;
                font-weight: 600;
            }
            QLabel#SearchResultsPlaceholder {
                color: #6e7178;
                font-size: 11px;
            }
            QListWidget#SearchResultsList {
                background: transparent;
                border: none;
            }
            QListWidget#SearchResultsList::item {
                color: #cfcfcf;
                padding: 4px 6px;
            }
            QListWidget#SearchResultsList::item:selected {
                background: #2a2b2f;
                border-radius: 4px;
            }
            QLabel#SearchResultItem {
                color: #cfcfcf;
                font-size: 12px;
            }
        """)

    def update_width_for_window(self, window_width: int):
        """Пересчитывает ширину панели в зависимости от ширины окна."""
        w = int(window_width * self._ratio)
        w = max(self._min_w, min(self._max_w, w))
        self.setFixedWidth(w)

    def _on_result_double_clicked(self, item: QListWidgetItem) -> None:
        payload = item.data(Qt.ItemDataRole.UserRole) or {}
        if payload:
            self.resultActivated.emit(payload)

    @staticmethod
    def _match_query(query: str, *values: str) -> bool:
        needle = query.lower()
        return any(needle in (value or "").lower() for value in values)

    def _collect_matches(self, query: str) -> list[dict]:
        matches: list[dict] = []
        for task in self._db.fetch_tasks():
            if self._match_query(query, task.title, task.description, task.project_title, task.project_area):
                matches.append(
                    {
                        "entity": "task",
                        "label": f"Задача: {task.title}",
                        "tooltip": task.description or task.project_title,
                        "id": task.id,
                    }
                )
        for project in self._db.fetch_projects():
            if self._match_query(query, project.title, project.area):
                matches.append(
                    {
                        "entity": "project",
                        "label": f"Проект: {project.title}",
                        "tooltip": project.area,
                        "id": project.id,
                    }
                )
        maps = self._db.fetch_maps()
        map_titles = {item.id: item.title for item in maps}
        for map_item in maps:
            if self._match_query(query, map_item.title, map_item.description, map_item.project):
                tooltip = map_item.project or map_item.description
                matches.append(
                    {
                        "entity": "map",
                        "label": f"Карта: {map_item.title}",
                        "tooltip": tooltip,
                        "id": map_item.id,
                    }
                )
        for marker in self._db.fetch_map_markers():
            if self._match_query(query, marker.name, marker.description, marker.properties):
                map_title = map_titles.get(marker.map_id, "")
                tooltip = f"Карта: {map_title}" if map_title else ""
                matches.append(
                    {
                        "entity": "marker",
                        "label": f"Метка: {marker.name}",
                        "tooltip": tooltip,
                        "id": marker.id,
                        "map_id": marker.map_id,
                    }
                )
        for note in self._db.fetch_notes():
            tags = " ".join(note.tags or [])
            if self._match_query(query, note.title, note.preview, tags, note.project):
                tooltip = note.project or note.preview
                matches.append(
                    {
                        "entity": "note",
                        "label": f"Заметка: {note.title}",
                        "tooltip": tooltip,
                        "id": note.id,
                    }
                )
        for file_item in self._db.fetch_cloud_files():
            if self._match_query(query, file_item.name, file_item.rel_path, file_item.description):
                tooltip = file_item.rel_path or file_item.description
                matches.append(
                    {
                        "entity": "file",
                        "label": f"Файл: {file_item.name}",
                        "tooltip": tooltip,
                        "id": file_item.id,
                    }
                )
        for obj in self._db.fetch_objects():
            if self._match_query(query, obj.title, obj.catalog, obj.object_type, obj.status, obj.description):
                tooltip_parts = [obj.catalog, obj.object_type, obj.status]
                tooltip = " · ".join(part for part in tooltip_parts if part)
                matches.append(
                    {
                        "entity": "object",
                        "label": f"Объект: {obj.title}",
                        "tooltip": tooltip,
                        "id": obj.id,
                    }
                )
        for collection in self._db.fetch_collection_items(search_text=query):
            entity_label = _COLLECTION_ENTITY_LABELS.get(collection.entity_type, collection.entity_type)
            tooltip_parts = [entity_label, collection.topic, collection.source_url]
            tooltip = " · ".join(part for part in tooltip_parts if part)
            matches.append(
                {
                    "entity": "collection",
                    "label": f"Коллекция: {collection.title}",
                    "tooltip": tooltip,
                    "id": collection.id,
                }
            )
        return matches

    def _update_results(self, text: str):
        query = (text or "").strip().lower()
        self.results_list.clear()

        if not query:
            self.results_placeholder.setText("Начните ввод, чтобы увидеть совпадения")
            self.results_placeholder.setVisible(True)
            self.results_list.setVisible(False)
            return

        matches = self._collect_matches(query)

        if not matches:
            self.results_placeholder.setText("Ничего не найдено")
            self.results_placeholder.setVisible(True)
            self.results_list.setVisible(False)
            return

        self.results_placeholder.setVisible(False)
        self.results_list.setVisible(True)
        for match in matches[: self._max_results]:
            item = QListWidgetItem(match["label"])
            item.setData(Qt.ItemDataRole.UserRole, match)
            tooltip = match.get("tooltip")
            if tooltip:
                item.setToolTip(tooltip)
            self.results_list.addItem(item)
