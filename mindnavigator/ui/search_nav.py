"""Панель поиска и фильтрации задач/объектов.

Входные данные:
    Текстовый запрос и события выбора результата.

Выходные данные:
    Сигналы активации результата поиска.
"""

from PySide6.QtCore import Qt, QTimer, Signal
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
from mindnavigator.services import GlobalSearchService
from mindnavigator.ui.styles import get_theme_palette

_SEARCH_DEBOUNCE_MS = 200


class SearchNav(QWidget):
    """Панель быстрого поиска по всем сущностям приложения."""

    resultActivated = Signal(dict)

    def __init__(self, parent=None):
        """Создает и настраивает блок быстрого поиска."""
        super().__init__(parent)
        self.setObjectName("SearchNav")
        self._theme_mode = "dark"
        self._ratio = 0.12
        self._min_w = 220
        self._max_w = 420
        self._fixed_h = 420
        self._db = get_database()
        self._search_service = GlobalSearchService(self._db)
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

        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(_SEARCH_DEBOUNCE_MS)
        self._search_timer.timeout.connect(self._run_scheduled_search)
        self.input.textChanged.connect(self._schedule_search)

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

        self.set_theme_mode("dark")

    def set_theme_mode(self, theme_mode: str) -> None:
        self._theme_mode = "light" if str(theme_mode).strip().lower() == "light" else "dark"
        palette = get_theme_palette(self._theme_mode)
        self.setStyleSheet(
            f"""
            QWidget#SearchNav {{
                background: {palette.panel_bg};
                border-right: 1px solid {palette.border};
                border-top: 1px solid {palette.border};
            }}
            QLabel#SearchHeader {{
                color: {palette.text};
                font-size: 13px;
                font-weight: 600;
            }}
            QLabel#SearchHint {{
                color: {palette.dim_text};
                font-size: 12px;
            }}
            QLineEdit#SearchInput {{
                background: {palette.input_bg};
                border: 1px solid {palette.border};
                border-radius: 4px;
                color: {palette.text};
                padding: 6px 8px;
            }}
            QLineEdit#SearchInput:focus {{
                border: 1px solid {palette.accent};
            }}
            QWidget#SearchResults {{
                background: {palette.elevated_bg};
                border: 1px solid {palette.border};
                border-radius: 6px;
            }}
            QLabel#SearchResultsTitle {{
                color: {palette.text};
                font-size: 12px;
                font-weight: 600;
            }}
            QLabel#SearchResultsPlaceholder {{
                color: {palette.muted_text};
                font-size: 11px;
            }}
            QListWidget#SearchResultsList {{
                background: transparent;
                border: none;
            }}
            QListWidget#SearchResultsList::item {{
                color: {palette.text};
                padding: 4px 6px;
            }}
            QListWidget#SearchResultsList::item:selected {{
                background: {palette.selection_bg};
                color: {palette.selection_text};
                border-radius: 4px;
            }}
            QLabel#SearchResultItem {{
                color: {palette.text};
                font-size: 12px;
            }}
        """
        )

    def update_width_for_window(self, window_width: int):
        """Пересчитывает ширину панели в зависимости от ширины окна."""
        w = int(window_width * self._ratio)
        w = max(self._min_w, min(self._max_w, w))
        self.setFixedWidth(w)

    def _on_result_double_clicked(self, item: QListWidgetItem) -> None:
        payload = item.data(Qt.ItemDataRole.UserRole) or {}
        if payload:
            self.resultActivated.emit(payload)

    def _collect_matches(self, query: str) -> list[dict]:
        return self._search_service.search(query)

    def _schedule_search(self, text: str) -> None:
        if not (text or "").strip():
            self._search_timer.stop()
            self._update_results("")
            return
        self._search_timer.start()

    def _run_scheduled_search(self) -> None:
        self._update_results(self.input.text())

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
