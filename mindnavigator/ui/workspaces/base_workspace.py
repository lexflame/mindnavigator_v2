"""Base workspace layout with search, filters, and status handling."""

from __future__ import annotations

import json
from typing import Any

from PySide6.QtCore import QTimer, QSettings
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

class BaseWorkspace(QWidget):
    """Base class for workspace panels."""

    workspace_id: str = "base"
    workspace_title: str = "Workspace"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._query = ""
        self._filters: dict[str, Any] = {}
        self._busy = False
        self._state_restored = False
        self.actions: dict[str, QAction] = {}

        self._search_timer = QTimer(self)
        self._search_timer.setInterval(250)
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._apply_search)

        self._build_ui()
        self.actions = self.create_actions()
        self.build_toolbar(self.actions)
        self.update_action_states()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 12)
        layout.setSpacing(12)

        header_row = QHBoxLayout()
        header_row.setSpacing(8)
        self.title_label = QLabel(self.workspace_title)
        self.title_label.setObjectName("WorkspaceTitle")
        # header_row.addWidget(self.title_label)
        header_row.addStretch(1)
        layout.addLayout(header_row)

        self.toolbar_row = QWidget()
        self.toolbar_row.setObjectName("WorkspaceToolbar")
        self.toolbar_layout = QHBoxLayout(self.toolbar_row)
        self.toolbar_layout.setContentsMargins(0, 0, 0, 0)
        self.toolbar_layout.setSpacing(6)
        self.toolbar_layout.addStretch(1)
        layout.addWidget(self.toolbar_row)

        self.search_row = QWidget()
        self.search_row.setObjectName("WorkspaceSearch")
        search_layout = QHBoxLayout(self.search_row)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(6)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("WorkspaceSearchInput")
        self.search_input.setPlaceholderText("Search")
        self.search_input.textChanged.connect(self._on_search_changed)

        self.clear_button = QToolButton()
        self.clear_button.setObjectName("WorkspaceSearchClear")
        self.clear_button.setText("✕")
        self.clear_button.clicked.connect(lambda: self.search_input.setText(""))

        search_layout.addWidget(self.search_input, 1)
        search_layout.addWidget(self.clear_button)
        layout.addWidget(self.search_row)

        self.filter_row = QWidget()
        self.filter_row.setObjectName("WorkspaceFilters")
        self.filter_layout = QHBoxLayout(self.filter_row)
        self.filter_layout.setContentsMargins(0, 0, 0, 0)
        self.filter_layout.setSpacing(6)
        self.filter_layout.addStretch(1)
        self.filter_bar_layout = self.filter_layout
        layout.addWidget(self.filter_row)

        self.content_host = QWidget()
        self.content_host.setObjectName("WorkspaceContent")
        self.content_layout = QVBoxLayout(self.content_host)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(6)
        layout.addWidget(self.content_host, 1)

        self.status_row = QLabel("")
        self.status_row.setObjectName("WorkspaceStatus")
        self.status_row.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(self.status_row)

    def create_actions(self) -> dict[str, QAction]:
        return {}

    def build_toolbar(self, actions: dict[str, QAction]) -> None:
        while self.toolbar_layout.count():
            item = self.toolbar_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        for action in actions.values():
            button = QToolButton()
            button.setDefaultAction(action)
            self.toolbar_layout.addWidget(button)
        self.toolbar_layout.addStretch(1)

    def update_action_states(self) -> None:
        selection = self.get_selection()
        selection_list = selection if isinstance(selection, list) else ([] if selection is None else [selection])
        has_selection = bool(selection_list)
        selection_count = len(selection_list)
        edit_action = self.actions.get("edit")
        delete_action = self.actions.get("delete")
        if edit_action is not None:
            edit_action.setEnabled(has_selection and selection_count == 1 and not self._busy)
        if delete_action is not None:
            delete_action.setEnabled(has_selection and not self._busy)
        for key, action in self.actions.items():
            if key not in {"edit", "delete"}:
                action.setEnabled(not self._busy)

    def get_selection(self) -> Any:
        return None

    def _on_search_changed(self, text: str) -> None:
        self._query = text
        if not self._busy:
            self._search_timer.start()

    def _apply_search(self) -> None:
        self._query = self.search_input.text()
        self.apply_query(self._query)
        self.save_state()

    def apply_query(self, query: str) -> None:
        """Override to apply the query to the workspace content."""

    def set_filter(self, key: str, value: Any) -> None:
        if value is None:
            self._filters.pop(key, None)
        else:
            self._filters[key] = value
        self.apply_filters(self.get_filters())
        self.save_state()

    def apply_filters(self, filters: dict[str, Any]) -> None:
        """Override to apply filters to the workspace content."""

    def get_filters(self) -> dict[str, Any]:
        return dict(self._filters)

    def set_content(self, widget: QWidget) -> None:
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            child = item.widget()
            if child is not None:
                child.setParent(None)
        self.content_layout.addWidget(widget, 1)

    def _settings_key(self, suffix: str) -> str:
        return f"workspace/{self.workspace_id}/{suffix}"

    def save_state(self) -> None:
        settings = QSettings()
        settings.setValue(self._settings_key("search_text"), self._query)
        filters_payload = self.get_filters()
        settings.setValue(
            self._settings_key("filters"),
            json.dumps(filters_payload),
        )

    def restore_state(self) -> None:
        settings = QSettings()
        search_text_raw = settings.value(self._settings_key("search_text"), "", str)
        search_text = search_text_raw if isinstance(search_text_raw, str) else ""
        filters_json_raw = settings.value(self._settings_key("filters"), "{}", str)
        filters_json = filters_json_raw if isinstance(filters_json_raw, str) else "{}"
        try:
            stored_filters = json.loads(filters_json) if filters_json else {}
        except json.JSONDecodeError:
            stored_filters = {}
        self._filters = stored_filters if isinstance(stored_filters, dict) else {}
        self._query = search_text or ""
        self.search_input.setText(self._query)

    def set_busy(self, busy: bool, status_text: str | None = None) -> None:
        self._busy = busy
        self.search_input.setEnabled(not busy)
        self.clear_button.setEnabled(not busy)
        self.toolbar_row.setEnabled(not busy)
        self.filter_row.setEnabled(not busy)
        if status_text is not None:
            self.set_status(status_text)
        self.update_action_states()

    def set_status(self, text: str) -> None:
        self.status_row.setText(text)
        self.status_row.setProperty("error", False)
        self.status_row.setStyleSheet("")

    def set_error(self, text: str) -> None:
        self.status_row.setText(f"Error: {text}")
        self.status_row.setProperty("error", True)
        self.status_row.setStyleSheet("color: #d76b6b;")

    def on_enter(self, context: dict | None = None) -> None:
        if not self._state_restored:
            self.restore_state()
            self._state_restored = True
        self.apply_query(self._query)
        self.apply_filters(self.get_filters())
        self.update_action_states()

    @staticmethod
    def on_leave() -> None:
        return None

    @staticmethod
    def teardown() -> None:
        return None
