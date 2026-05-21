"""Dossier workspace implementation."""

from __future__ import annotations

from datetime import datetime

from ._shared import *  # noqa: F401,F403
from .dossier_details_dialog import DossierDetailsDialog
from .dossier_editor_dialog import DossierCreateDialog, DossierEditDialog
from .dossier_item_delegate import DossierItemDelegate
from .dossier_list_model import DossierListModel
from .dossier_roles import DossierRoles

LINK_ID_ROLE = int(Qt.ItemDataRole.UserRole)
LINK_ENTITY_KIND_ROLE = LINK_ID_ROLE + 1
LINK_ENTITY_ID_ROLE = LINK_ID_ROLE + 2

VIEW_MODE_LABELS = {
    "list": "Список",
    "shelf": "Полка",
    "matrix": "Матрица",
    "links": "Связи",
}


class DossierLinkDialog(QDialog):
    def __init__(self, database, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._db = database
        self._theme_mode = resolve_theme_mode(parent)
        self.setObjectName("DossierLinkDialog")
        self.setWindowTitle("Добавить связь")
        self.setMinimumWidth(480)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        form = QFormLayout()

        self.kind_combo = QComboBox(self)
        for label, kind in DOSSIER_LINK_KIND_OPTIONS:
            self.kind_combo.addItem(label, kind)

        self.search_edit = QLineEdit(self)
        self.search_edit.setPlaceholderText("Поиск связанной сущности")

        self.entity_combo = QComboBox(self)

        form.addRow("Тип сущности", self.kind_combo)
        form.addRow("Поиск", self.search_edit)
        form.addRow("Сущность", self.entity_combo)
        layout.addLayout(form)

        buttons = QDialogButtonBox(self)
        self._ok_button = buttons.addButton(QDialogButtonBox.StandardButton.Ok)
        buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.kind_combo.currentIndexChanged.connect(self._fill_entities)
        self.search_edit.textChanged.connect(self._fill_entities)
        self._fill_entities()

        palette = get_theme_palette(self._theme_mode)
        self.setStyleSheet(
            f"""
            QDialog#DossierLinkDialog {{
                background: {palette.window_bg};
                color: {palette.text};
            }}
            QDialog#DossierLinkDialog QLabel {{
                color: {palette.text};
            }}
            QDialog#DossierLinkDialog QLineEdit,
            QDialog#DossierLinkDialog QComboBox {{
                background: {palette.input_bg};
                color: {palette.text};
                border: 1px solid {palette.border_strong};
                border-radius: 6px;
                padding: 6px 8px;
            }}
            QDialog#DossierLinkDialog QLineEdit:focus,
            QDialog#DossierLinkDialog QComboBox:focus {{
                border: 1px solid {palette.accent};
            }}
            QDialog#DossierLinkDialog QComboBox QAbstractItemView {{
                background: {palette.elevated_bg};
                color: {palette.text};
                border: 1px solid {palette.border};
                selection-background-color: {palette.selection_bg};
                selection-color: {palette.selection_text};
                outline: none;
            }}
            QDialog#DossierLinkDialog QDialogButtonBox QPushButton {{
                background: {palette.panel_bg};
                color: {palette.text};
                border: 1px solid {palette.border_strong};
                border-radius: 8px;
                padding: 8px 14px;
            }}
            QDialog#DossierLinkDialog QDialogButtonBox QPushButton:hover {{
                background: {palette.selection_bg};
                color: {palette.selection_text};
            }}
            """
        )

    def _fill_entities(self) -> None:
        self.entity_combo.clear()
        options = self._db.fetch_dossier_link_options(str(self.kind_combo.currentData() or ""), self.search_edit.text())
        if not options:
            self.entity_combo.addItem("— нет доступных —", None)
            self._ok_button.setEnabled(False)
            return
        for entity_id, label in options:
            self.entity_combo.addItem(label, entity_id)
        self._ok_button.setEnabled(True)

    def values(self) -> dict[str, object]:
        return {
            "entity_kind": str(self.kind_combo.currentData() or ""),
            "entity_id": self.entity_combo.currentData(),
        }


class DossierWorkspace(BaseWorkspace):
    workspace_id = "dossier"
    workspace_title = "Досье"

    def __init__(self, parent: QWidget | None = None) -> None:
        self._db = get_database()
        self._current_dossier_id: Optional[int] = None
        self._last_refresh_text = "—"
        super().__init__(parent)
        self.setObjectName("DossierWorkspace")
        self.search_input.setPlaceholderText("Поиск по названию, описанию, тегам, источнику, полям...")
        self.set_theme_mode(self._theme_mode)
        self.refresh()

    def _build_ui(self) -> None:
        super()._build_ui()

        self.kind_filter = QComboBox()
        for label, value in DOSSIER_KIND_OPTIONS:
            self.kind_filter.addItem(label, value)
        self.kind_filter.currentIndexChanged.connect(self._on_kind_filter_changed)

        self.status_filter = QComboBox()
        for label, value in DOSSIER_STATUS_OPTIONS:
            self.status_filter.addItem(label, value)
        self.status_filter.currentIndexChanged.connect(self._on_status_filter_changed)

        self.rating_filter = QComboBox()
        for label, value in DOSSIER_RATING_OPTIONS:
            self.rating_filter.addItem(label, value)
        self.rating_filter.currentIndexChanged.connect(self._on_rating_filter_changed)

        self.tag_filter_input = QLineEdit()
        self.tag_filter_input.setPlaceholderText("Все теги")
        self.tag_filter_input.textChanged.connect(self._on_tag_filter_changed)

        self.group_filter = QComboBox()
        for label, value in DOSSIER_GROUP_OPTIONS:
            self.group_filter.addItem(label, value)
        self.group_filter.currentIndexChanged.connect(self._on_group_filter_changed)

        self.reset_filters_button = QToolButton()
        self.reset_filters_button.setText("Сбросить")
        self.reset_filters_button.clicked.connect(self._reset_filters)

        self.filter_layout.addWidget(QLabel("Вид"))
        self.filter_layout.addWidget(self.kind_filter)
        self.filter_layout.addWidget(QLabel("Статус"))
        self.filter_layout.addWidget(self.status_filter)
        self.filter_layout.addWidget(QLabel("Рейтинг"))
        self.filter_layout.addWidget(self.rating_filter)
        self.filter_layout.addWidget(QLabel("Тег"))
        self.filter_layout.addWidget(self.tag_filter_input)
        self.filter_layout.addWidget(QLabel("Группы"))
        self.filter_layout.addWidget(self.group_filter)
        self.filter_layout.addWidget(self.reset_filters_button)
        self.filter_layout.addStretch(1)

        content_host = QWidget()
        content_layout = QVBoxLayout(content_host)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(8)

        summary_card = QFrame()
        summary_card.setObjectName("DossierSummaryCard")
        summary_layout = QVBoxLayout(summary_card)
        summary_layout.setContentsMargins(14, 12, 14, 12)
        summary_layout.setSpacing(8)

        summary_title = QLabel("Панель выдачи")
        summary_title.setObjectName("DossierSectionLabel")
        summary_layout.addWidget(summary_title)

        self.summary_chips_host = QWidget()
        self.summary_chips_layout = QHBoxLayout(self.summary_chips_host)
        self.summary_chips_layout.setContentsMargins(0, 0, 0, 0)
        self.summary_chips_layout.setSpacing(6)
        summary_layout.addWidget(self.summary_chips_host)

        self.summary_label = QLabel("")
        self.summary_label.setObjectName("DossierSummaryLabel")
        self.summary_label.setVisible(False)
        summary_layout.addWidget(self.summary_label)
        content_layout.addWidget(summary_card)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("DossierSplitter")
        splitter.setChildrenCollapsible(False)

        list_host = QWidget()
        list_layout = QVBoxLayout(list_host)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(8)

        top_row = QWidget()
        top_row_layout = QHBoxLayout(top_row)
        top_row_layout.setContentsMargins(0, 0, 0, 0)
        top_row_layout.setSpacing(8)

        quick_row = QWidget()
        quick_layout = QHBoxLayout(quick_row)
        quick_layout.setContentsMargins(0, 0, 0, 0)
        quick_layout.setSpacing(6)

        self.quick_kind = QComboBox()
        for label, value in DOSSIER_KIND_OPTIONS[1:]:
            self.quick_kind.addItem(label, value)

        self.quick_title_input = QLineEdit()
        self.quick_title_input.setPlaceholderText("Название нового досье...")

        self.quick_create_btn = QToolButton()
        self.quick_create_btn.setText("Создать")
        self.quick_create_btn.clicked.connect(self._create_dossier_from_quick_form)
        self.quick_title_input.returnPressed.connect(self._create_dossier_from_quick_form)

        quick_layout.addWidget(self.quick_kind)
        quick_layout.addWidget(self.quick_title_input, 1)
        quick_layout.addWidget(self.quick_create_btn)
        top_row_layout.addWidget(quick_row, 1)

        self.view_mode_group = QButtonGroup(self)
        self.view_mode_buttons: dict[str, QToolButton] = {}
        for mode_key in ("list", "shelf", "matrix", "links"):
            button = QToolButton()
            button.setText(VIEW_MODE_LABELS[mode_key])
            button.setCheckable(True)
            button.clicked.connect(lambda checked=False, mode=mode_key: self._set_view_mode(mode))
            if mode_key != "list":
                button.setEnabled(False)
                button.setToolTip("Режим подготовлен и будет включен на следующем этапе.")
            self.view_mode_group.addButton(button)
            self.view_mode_buttons[mode_key] = button
            top_row_layout.addWidget(button)

        list_layout.addWidget(top_row)

        self.left_mode_stack = QStackedWidget()

        list_page = QWidget()
        list_page_layout = QVBoxLayout(list_page)
        list_page_layout.setContentsMargins(0, 0, 0, 0)
        list_page_layout.setSpacing(0)

        self.list_view = QListView()
        self.list_view.setObjectName("DossierList")
        self.list_view.setModel(DossierListModel(self.list_view))
        self.list_view.setItemDelegate(DossierItemDelegate(self.list_view))
        self.list_view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list_view.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.list_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list_view.selectionModel().selectionChanged.connect(self._on_selection_changed)
        self.list_view.doubleClicked.connect(self._open_details_dialog)
        self.list_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_view.customContextMenuRequested.connect(self._show_context_menu)
        list_page_layout.addWidget(self.list_view)

        self.empty_list_page = self._build_empty_list_page()

        self.left_mode_stack.addWidget(list_page)
        self.left_mode_stack.addWidget(self.empty_list_page)
        list_layout.addWidget(self.left_mode_stack, 1)
        splitter.addWidget(list_host)

        self.preview_stack = QStackedWidget()
        self.preview_stack.addWidget(self._build_preview_empty_page())
        self.preview_stack.addWidget(self._build_preview_inspector())
        splitter.addWidget(self.preview_stack)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        content_layout.addWidget(splitter, 1)
        self.set_content(content_host)

    def _build_empty_list_page(self) -> QWidget:
        page = QFrame()
        page.setObjectName("DossierEmptyCard")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(10)
        layout.addStretch(1)

        self.empty_list_title = QLabel("Досье пока нет")
        self.empty_list_title.setObjectName("DossierEmptyTitle")
        self.empty_list_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.empty_list_title)

        self.empty_list_text = QLabel("Создайте первую карточку или импортируйте данные.")
        self.empty_list_text.setWordWrap(True)
        self.empty_list_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.empty_list_text)

        button_row = QWidget()
        button_layout = QHBoxLayout(button_row)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(8)
        button_layout.addStretch(1)

        self.empty_create_button = QToolButton()
        self.empty_create_button.setText("+ Досье")
        self.empty_create_button.clicked.connect(self._open_create_dialog)
        button_layout.addWidget(self.empty_create_button)

        self.empty_secondary_button = QToolButton()
        self.empty_secondary_button.setText("Сбросить фильтры")
        self.empty_secondary_button.clicked.connect(self._reset_filters)
        button_layout.addWidget(self.empty_secondary_button)
        button_layout.addStretch(1)

        layout.addWidget(button_row)
        layout.addStretch(1)
        return page

    def _build_preview_empty_page(self) -> QWidget:
        page = QFrame()
        page.setObjectName("DossierPreviewCard")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(10)
        layout.addStretch(1)

        title = QLabel("Выберите досье")
        title.setObjectName("DossierPreviewTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        text = QLabel("Справа появятся сведения, заметки, связи и вывод.")
        text.setWordWrap(True)
        text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(text)
        layout.addStretch(1)
        return page

    def _build_preview_inspector(self) -> QWidget:
        host = QFrame()
        host.setObjectName("DossierPreviewCard")
        layout = QVBoxLayout(host)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        self.preview_title_label = QLabel("Досье не выбрано")
        self.preview_title_label.setObjectName("DossierPreviewTitle")
        self.preview_title_label.setWordWrap(True)

        self.preview_meta_label = QLabel("Выберите карточку слева, чтобы открыть инспектор.")
        self.preview_meta_label.setObjectName("DossierPreviewMeta")
        self.preview_meta_label.setWordWrap(True)

        layout.addWidget(self.preview_title_label)
        layout.addWidget(self.preview_meta_label)

        self.preview_tabs = QTabWidget()
        self.preview_tabs.addTab(self._build_overview_tab(), "Обзор")
        self.preview_tabs.addTab(self._build_metadata_tab(), "Сведения")
        self.preview_tabs.addTab(self._build_notes_tab(), "Заметки")
        self.preview_tabs.addTab(self._build_links_tab(), "Связи")
        self.preview_tabs.addTab(self._build_output_tab(), "Вывод")
        layout.addWidget(self.preview_tabs, 1)
        return host

    def _build_overview_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        overview_top = QWidget()
        overview_top_layout = QHBoxLayout(overview_top)
        overview_top_layout.setContentsMargins(0, 0, 0, 0)
        overview_top_layout.setSpacing(10)

        self.preview_cover_label = QLabel("Нет обложки")
        self.preview_cover_label.setObjectName("DossierPreviewCover")
        self.preview_cover_label.setFixedSize(116, 156)
        self.preview_cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_cover_label.setWordWrap(True)
        overview_top_layout.addWidget(self.preview_cover_label)

        overview_text = QWidget()
        overview_text_layout = QVBoxLayout(overview_text)
        overview_text_layout.setContentsMargins(0, 0, 0, 0)
        overview_text_layout.setSpacing(8)

        self.preview_summary_label = QLabel("")
        self.preview_summary_label.setObjectName("DossierPreviewSummary")
        self.preview_summary_label.setWordWrap(True)

        self.preview_tags_label = QLabel("")
        self.preview_tags_label.setWordWrap(True)

        self.preview_source_label = QLabel("")
        self.preview_source_label.setWordWrap(True)

        self.preview_output_overview_label = QLabel("")
        self.preview_output_overview_label.setWordWrap(True)

        overview_text_layout.addWidget(self.preview_summary_label)
        overview_text_layout.addWidget(self.preview_tags_label)
        overview_text_layout.addWidget(self.preview_source_label)
        overview_text_layout.addWidget(self.preview_output_overview_label)
        overview_text_layout.addStretch(1)
        overview_top_layout.addWidget(overview_text, 1)

        layout.addWidget(overview_top)
        layout.addStretch(1)
        return page

    def _build_metadata_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.preview_metadata_label = QLabel("")
        self.preview_metadata_label.setWordWrap(True)
        self.preview_metadata_label.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(self.preview_metadata_label)
        layout.addStretch(1)
        return page

    def _build_notes_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        notes_intro = QLabel("Мои комментарии, наблюдения, цитаты и все, что стоит использовать дальше.")
        notes_intro.setWordWrap(True)
        layout.addWidget(notes_intro)

        self.preview_description = QPlainTextEdit()
        self.preview_description.setReadOnly(True)
        self.preview_description.setPlaceholderText("Заметки появятся после выбора досье.")
        layout.addWidget(self.preview_description, 1)
        return page

    def _build_links_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        links_header = QWidget()
        links_header_layout = QHBoxLayout(links_header)
        links_header_layout.setContentsMargins(0, 0, 0, 0)
        links_header_layout.setSpacing(6)

        self.preview_links_header_label = QLabel("Связи")
        links_header_layout.addWidget(self.preview_links_header_label)
        links_header_layout.addStretch(1)

        self.add_link_button = QToolButton()
        self.add_link_button.setText("Связать")
        self.add_link_button.clicked.connect(self._open_add_link_dialog)

        self.remove_link_button = QToolButton()
        self.remove_link_button.setText("Удалить связь")
        self.remove_link_button.clicked.connect(self._remove_selected_link)

        links_header_layout.addWidget(self.add_link_button)
        links_header_layout.addWidget(self.remove_link_button)
        layout.addWidget(links_header)

        self.preview_links = QListWidget()
        self.preview_links.itemSelectionChanged.connect(self._update_link_action_states)
        layout.addWidget(self.preview_links, 1)
        return page

    def _build_output_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.preview_output_label = QLabel("")
        self.preview_output_label.setWordWrap(True)
        layout.addWidget(self.preview_output_label)

        self.preview_output_hint_label = QLabel("")
        self.preview_output_hint_label.setWordWrap(True)
        layout.addWidget(self.preview_output_hint_label)

        actions_row = QWidget()
        actions_layout = QHBoxLayout(actions_row)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(6)

        self.create_idea_button = QToolButton()
        self.create_idea_button.setText("Создать идею")
        self.create_idea_button.setEnabled(False)
        self.create_idea_button.setToolTip("Интеграция с идеями будет добавлена на следующем этапе.")
        actions_layout.addWidget(self.create_idea_button)

        self.create_task_button = QToolButton()
        self.create_task_button.setText("Создать задачу")
        self.create_task_button.setEnabled(False)
        self.create_task_button.setToolTip("Интеграция с задачами будет добавлена на следующем этапе.")
        actions_layout.addWidget(self.create_task_button)

        self.conceptboard_button = QToolButton()
        self.conceptboard_button.setText("В концептборд")
        self.conceptboard_button.setEnabled(False)
        self.conceptboard_button.setToolTip("Добавить досье в концептборд как материал или источник.")
        actions_layout.addWidget(self.conceptboard_button)

        self.output_link_button = QToolButton()
        self.output_link_button.setText("Связать")
        self.output_link_button.clicked.connect(self._open_add_link_dialog)
        actions_layout.addWidget(self.output_link_button)

        actions_layout.addStretch(1)
        layout.addWidget(actions_row)
        layout.addStretch(1)
        return page

    def create_actions(self) -> dict[str, QAction]:
        action_new = QAction("+ Досье", self)
        action_new.triggered.connect(self._open_create_dialog)

        action_edit = QAction("Изменить", self)
        action_edit.triggered.connect(self._open_edit_dialog)

        action_details = QAction("Карточка", self)
        action_details.triggered.connect(self._open_details_dialog)

        action_refresh = QAction("Обновить", self)
        action_refresh.triggered.connect(self.refresh)

        action_export = QAction("Экспорт", self)
        action_export.setToolTip("Экспорт будет добавлен на следующем этапе.")

        action_import = QAction("Импорт", self)
        action_import.setToolTip("Импорт будет добавлен на следующем этапе.")

        action_delete = QAction("Удалить", self)
        action_delete.triggered.connect(self._delete_selected)

        return {
            "new": action_new,
            "edit": action_edit,
            "details": action_details,
            "refresh": action_refresh,
            "export": action_export,
            "import": action_import,
            "delete": action_delete,
        }

    def build_toolbar(self, actions: dict[str, QAction]) -> None:
        while self.toolbar_layout.count():
            item = self.toolbar_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        for key in ("new", "edit", "details"):
            self.toolbar_layout.addWidget(self._make_toolbar_button(actions[key], "DossierPrimaryAction"))

        spacer = QWidget()
        spacer.setFixedWidth(18)
        self.toolbar_layout.addWidget(spacer)

        for key in ("refresh", "export", "import"):
            self.toolbar_layout.addWidget(self._make_toolbar_button(actions[key], "DossierUtilityAction"))

        self.toolbar_layout.addStretch(1)
        self.toolbar_layout.addWidget(self._make_toolbar_button(actions["delete"], "DossierDangerAction"))

    def _make_toolbar_button(self, action: QAction, object_name: str) -> QToolButton:
        button = QToolButton()
        button.setObjectName(object_name)
        button.setDefaultAction(action)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        return button

    def update_action_states(self) -> None:
        super().update_action_states()
        details_action = self.actions.get("details")
        if details_action is not None:
            details_action.setEnabled(self.get_selection() is not None and not self._busy)
        for key in ("export", "import"):
            action = self.actions.get(key)
            if action is not None:
                action.setEnabled(False)
        self._update_link_action_states()

    def set_theme_mode(self, theme_mode: str) -> None:
        self._theme_mode = "light" if str(theme_mode).strip().lower() == "light" else "dark"
        palette = get_theme_palette(self._theme_mode)
        self.setStyleSheet(
            f"""
            QWidget#DossierWorkspace {{
                background: {palette.window_bg};
            }}
            QWidget#DossierWorkspace QLabel {{
                color: {palette.text};
            }}
            QWidget#DossierWorkspace QWidget#WorkspaceToolbar,
            QWidget#DossierWorkspace QWidget#WorkspaceSearch,
            QWidget#DossierWorkspace QWidget#WorkspaceFilters,
            QWidget#DossierWorkspace QFrame#DossierSummaryCard,
            QWidget#DossierWorkspace QFrame#DossierPreviewCard,
            QWidget#DossierWorkspace QFrame#DossierEmptyCard {{
                background: {palette.panel_bg};
                border: 1px solid {palette.border};
                border-radius: 10px;
                padding: 6px;
            }}
            QWidget#DossierWorkspace QToolButton,
            QWidget#DossierWorkspace QComboBox,
            QWidget#DossierWorkspace QLineEdit,
            QWidget#DossierWorkspace QPlainTextEdit,
            QWidget#DossierWorkspace QListWidget,
            QWidget#DossierWorkspace QListView,
            QWidget#DossierWorkspace QTabWidget::pane {{
                background: {palette.input_bg};
                color: {palette.text};
                border: 1px solid {palette.border};
                border-radius: 8px;
            }}
            QWidget#DossierWorkspace QToolButton,
            QWidget#DossierWorkspace QComboBox,
            QWidget#DossierWorkspace QLineEdit,
            QWidget#DossierWorkspace QPlainTextEdit,
            QWidget#DossierWorkspace QListWidget,
            QWidget#DossierWorkspace QListView {{
                padding: 6px 8px;
            }}
            QWidget#DossierWorkspace QComboBox QAbstractItemView {{
                background: {palette.elevated_bg};
                color: {palette.text};
                border: 1px solid {palette.border};
                selection-background-color: {palette.selection_bg};
                selection-color: {palette.selection_text};
                outline: none;
            }}
            QWidget#DossierWorkspace QListWidget::item:selected,
            QWidget#DossierWorkspace QListView::item:selected {{
                background: {palette.selection_bg};
                color: {palette.selection_text};
            }}
            QWidget#DossierWorkspace QSplitter::handle {{
                background: {palette.panel_alt_bg};
                border: 1px solid {palette.border};
            }}
            QWidget#DossierWorkspace QToolButton:hover {{
                background: {palette.selection_bg};
                color: {palette.selection_text};
            }}
            QWidget#DossierWorkspace QToolButton:disabled {{
                color: {palette.muted_text};
                background: {palette.panel_alt_bg};
            }}
            QWidget#DossierWorkspace QToolButton#DossierDangerAction {{
                border-color: {palette.danger};
                color: {palette.text};
            }}
            QWidget#DossierWorkspace QToolButton#DossierDangerAction:hover {{
                background: {palette.danger};
                color: {palette.selection_text};
            }}
            QWidget#DossierWorkspace QLabel#DossierPreviewTitle,
            QWidget#DossierWorkspace QLabel#DossierEmptyTitle {{
                font-size: 18px;
                font-weight: 700;
                color: {palette.text};
            }}
            QWidget#DossierWorkspace QLabel#DossierPreviewMeta {{
                color: {palette.dim_text};
            }}
            QWidget#DossierWorkspace QLabel#DossierPreviewSummary,
            QWidget#DossierWorkspace QLabel#DossierSummaryLabel {{
                color: {palette.text};
            }}
            QWidget#DossierWorkspace QLabel#DossierSectionLabel {{
                color: {palette.selection_text};
                font-weight: 600;
            }}
            QWidget#DossierWorkspace QLabel#DossierPreviewCover {{
                background: {palette.panel_alt_bg};
                border: 1px dashed {palette.border_strong};
                border-radius: 10px;
                color: {palette.dim_text};
                padding: 8px;
            }}
            QWidget#DossierWorkspace QTabBar::tab {{
                background: {palette.panel_alt_bg};
                color: {palette.text};
                border: 1px solid {palette.border};
                border-bottom: none;
                padding: 8px 12px;
                margin-right: 4px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }}
            QWidget#DossierWorkspace QTabBar::tab:selected {{
                background: {palette.selection_bg};
                color: {palette.selection_text};
            }}
            {build_popup_menu_stylesheet(self._theme_mode)}
            {build_scrollbar_stylesheet(get_scrollbar_tokens(self._theme_mode), scope="QWidget#DossierWorkspace")}
            """
        )

    def restore_state(self) -> None:
        super().restore_state()
        filters = self.get_filters()
        if not isinstance(filters.get("view_mode"), str):
            self._filters["view_mode"] = "list"
        self._sync_filter_controls()

    def get_selection(self) -> Optional[int]:
        index = self.list_view.currentIndex()
        if not index.isValid():
            return None
        value = index.data(DossierRoles.DossierId)
        return int(value) if isinstance(value, int) else None

    def _sync_filter_controls(self) -> None:
        self._set_combo_value(self.kind_filter, self.get_filters().get("kind"))
        self._set_combo_value(self.status_filter, self.get_filters().get("status"))
        self._set_combo_value(self.rating_filter, self.get_filters().get("rating"))
        self._set_combo_value(self.group_filter, self.get_filters().get("group_by") or "none")
        self._set_line_edit_value(self.tag_filter_input, self.get_filters().get("tag"))
        self._sync_view_mode_buttons(str(self.get_filters().get("view_mode") or "list"))

    @staticmethod
    def _set_combo_value(combo: QComboBox, value: object) -> None:
        for index in range(combo.count()):
            if combo.itemData(index) == value:
                combo.blockSignals(True)
                combo.setCurrentIndex(index)
                combo.blockSignals(False)
                return

    @staticmethod
    def _set_line_edit_value(line_edit: QLineEdit, value: object) -> None:
        text = str(value or "")
        line_edit.blockSignals(True)
        line_edit.setText(text)
        line_edit.blockSignals(False)

    def _sync_view_mode_buttons(self, mode: str) -> None:
        normalized = mode if mode in VIEW_MODE_LABELS else "list"
        for mode_key, button in self.view_mode_buttons.items():
            button.blockSignals(True)
            button.setChecked(mode_key == normalized)
            button.blockSignals(False)

    def _update_link_action_states(self) -> None:
        if not hasattr(self, "add_link_button") or not hasattr(self, "preview_links"):
            return
        dossier_selected = self.get_selection() is not None and not self._busy
        self.add_link_button.setEnabled(dossier_selected)
        self.output_link_button.setEnabled(dossier_selected)
        current_item = self.preview_links.currentItem()
        link_id = current_item.data(LINK_ID_ROLE) if current_item is not None else None
        self.remove_link_button.setEnabled(dossier_selected and link_id is not None)

    def _on_kind_filter_changed(self) -> None:
        self.set_filter("kind", self.kind_filter.currentData())

    def _on_status_filter_changed(self) -> None:
        self.set_filter("status", self.status_filter.currentData())

    def _on_rating_filter_changed(self) -> None:
        self.set_filter("rating", self.rating_filter.currentData())

    def _on_tag_filter_changed(self) -> None:
        self.set_filter("tag", self.tag_filter_input.text().strip())

    def _on_group_filter_changed(self) -> None:
        self.set_filter("group_by", self.group_filter.currentData())

    def _set_view_mode(self, mode: str) -> None:
        normalized_mode = mode if mode in VIEW_MODE_LABELS else "list"
        self.set_filter("view_mode", normalized_mode)

    def _reset_filters(self) -> None:
        self._filters.pop("kind", None)
        self._filters.pop("status", None)
        self._filters.pop("rating", None)
        self._filters.pop("tag", None)
        self._filters["group_by"] = "none"
        self._filters["view_mode"] = "list"
        self._sync_filter_controls()
        self.apply_filters(self.get_filters())
        self.save_state()

    def _open_create_dialog(self, checked: bool = False) -> None:
        _ = checked
        dialog = DossierCreateDialog(
            parent=self,
            seed_kind=str(self.quick_kind.currentData() or self.kind_filter.currentData() or "book"),
            seed_title=(self.quick_title_input.text() or "").strip(),
        )
        if show_dialog_standard(dialog, self) != QDialog.DialogCode.Accepted:
            return
        try:
            dossier = self._db.create_dossier(**dialog.values())
        except ValueError as exc:
            QMessageBox.warning(self, "Досье", str(exc))
            return
        self._current_dossier_id = dossier.id
        self.quick_title_input.clear()
        self.refresh()
        self.set_status("Досье создано.")

    def _create_dossier_from_quick_form(self) -> None:
        self._open_create_dialog()

    def _open_edit_dialog(self, checked: bool = False) -> None:
        _ = checked
        dossier_id = self.get_selection()
        if dossier_id is None:
            return
        dossier = self._db.get_dossier(dossier_id)
        if dossier is None:
            return
        dialog = DossierEditDialog(dossier, parent=self)
        if show_dialog_standard(dialog, self) != QDialog.DialogCode.Accepted:
            return
        try:
            updated = self._db.update_dossier(dossier_id=dossier_id, **dialog.values())
        except ValueError as exc:
            QMessageBox.warning(self, "Досье", str(exc))
            return
        self._current_dossier_id = updated.id
        self.refresh()
        self.set_status("Досье обновлено.")

    def _open_details_dialog(self, checked: bool = False) -> None:
        _ = checked
        dossier_id = self.get_selection()
        if dossier_id is None:
            return
        dossier = self._db.get_dossier(dossier_id)
        if dossier is None:
            return
        dialog = DossierDetailsDialog(dossier, parent=self)
        show_dialog_standard(dialog, self)

    def _open_add_link_dialog(self, checked: bool = False) -> None:
        _ = checked
        dossier_id = self.get_selection()
        if dossier_id is None:
            return
        dialog = DossierLinkDialog(self._db, parent=self)
        if show_dialog_standard(dialog, self) != QDialog.DialogCode.Accepted:
            return
        values = dialog.values()
        entity_id = values.get("entity_id")
        if entity_id is None:
            QMessageBox.warning(self, "Досье", "Нет доступной сущности для привязки.")
            return
        try:
            self._db.add_dossier_link(dossier_id, str(values.get("entity_kind") or ""), int(entity_id))
        except ValueError as exc:
            QMessageBox.warning(self, "Досье", str(exc))
            return
        self._load_preview(dossier_id)
        self.refresh()
        self.set_status("Связь добавлена.")

    def _remove_selected_link(self, checked: bool = False) -> None:
        _ = checked
        dossier_id = self.get_selection()
        if dossier_id is None:
            return
        item = self.preview_links.currentItem()
        if item is None:
            return
        link_id = item.data(LINK_ID_ROLE)
        if link_id is None:
            return
        self._db.delete_dossier_link(int(link_id))
        self._load_preview(dossier_id)
        self.refresh()
        self.set_status("Связь удалена.")

    def _delete_selected(self, checked: bool = False, *, require_confirmation: bool = True) -> None:
        _ = checked
        dossier_id = self.get_selection()
        if dossier_id is None:
            return
        if require_confirmation:
            dialog = ConfirmDialog(
                "Удалить досье",
                "Это действие нельзя отменить. Удалить выбранное досье?",
                parent=self,
                confirm_text="Удалить",
                cancel_text="Отмена",
            )
            if exec_with_overlay(dialog, self) != QDialog.DialogCode.Accepted:
                return
        self._db.delete_dossier(dossier_id)
        self._current_dossier_id = None
        self.refresh()
        self.set_status("Досье удалено.")

    def _show_context_menu(self, pos) -> None:
        index = self.list_view.indexAt(pos)
        menu = QMenu(self)
        menu.setStyleSheet(build_popup_menu_stylesheet(self._theme_mode))

        action_new = menu.addAction("+ Досье")
        action_edit = None
        action_details = None
        action_link = None
        action_refresh = menu.addAction("Обновить")
        action_delete = None
        if index.isValid():
            action_details = menu.addAction("Открыть карточку")
            action_edit = menu.addAction("Изменить")
            action_link = menu.addAction("Связать")
            menu.addSeparator()
            action_delete = menu.addAction("Удалить")

        chosen = menu.exec(self.list_view.mapToGlobal(pos))
        if chosen == action_new:
            self._open_create_dialog()
        elif chosen == action_refresh:
            self.refresh()
        elif action_details is not None and chosen == action_details:
            self.list_view.setCurrentIndex(index)
            self._open_details_dialog()
        elif action_edit is not None and chosen == action_edit:
            self.list_view.setCurrentIndex(index)
            self._open_edit_dialog()
        elif action_link is not None and chosen == action_link:
            self.list_view.setCurrentIndex(index)
            self._open_add_link_dialog()
        elif action_delete is not None and chosen == action_delete:
            self.list_view.setCurrentIndex(index)
            self._delete_selected()

    def apply_query(self, query: str) -> None:
        _ = query
        self.refresh()

    def apply_filters(self, filters: dict[str, object]) -> None:
        _ = filters
        self.refresh()

    def _add_chip(self, text: str) -> None:
        chip = QLabel(text)
        chip.setProperty("chip", True)
        chip.setStyleSheet(
            """
            QLabel[chip="true"] {
                background: rgba(103, 132, 176, 0.18);
                border: 1px solid rgba(124, 154, 201, 0.35);
                border-radius: 11px;
                padding: 4px 10px;
            }
            """
        )
        self.summary_chips_layout.addWidget(chip)

    def _update_summary(self, items: list[DossierData], tag_filter: str) -> None:
        if not hasattr(self, "summary_label"):
            return

        while self.summary_chips_layout.count():
            item = self.summary_chips_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        total = len(items)
        kind_counts: dict[str, int] = {}
        status_counts: dict[str, int] = {}
        tag_counts: dict[str, int] = {}
        unrated_count = 0
        for item in items:
            kind_label = dossier_kind_label(item.kind)
            status_label = dossier_status_label(item.status)
            kind_counts[kind_label] = kind_counts.get(kind_label, 0) + 1
            status_counts[status_label] = status_counts.get(status_label, 0) + 1
            if item.rating is None:
                unrated_count += 1
            for tag in item.tags:
                normalized_tag = str(tag or "").strip()
                if normalized_tag:
                    tag_counts[normalized_tag] = tag_counts.get(normalized_tag, 0) + 1

        parts = [f"Итого: {total}"]
        self._add_chip(f"Найдено: {total}")
        for label, count in sorted(kind_counts.items(), key=lambda item: (-item[1], item[0].lower()))[:4]:
            self._add_chip(f"{label}: {count}")
            parts.append(f"{label}: {count}")
        for preferred_status in ("Активно", "Завершено", "В планах", "Отложено"):
            count = status_counts.get(preferred_status)
            if count:
                self._add_chip(f"{preferred_status}: {count}")
                parts.append(f"{preferred_status}: {count}")
        if unrated_count:
            self._add_chip(f"Без оценки: {unrated_count}")
            parts.append(f"Без оценки: {unrated_count}")
        if tag_counts:
            top_tag, top_count = sorted(tag_counts.items(), key=lambda item: (-item[1], item[0].lower()))[0]
            self._add_chip(f"Топ тег: {top_tag} ×{top_count}")
            parts.append(f"Теги: {self._render_count_summary(tag_counts, limit=3)}")
        elif tag_filter:
            parts.append(f"Тег: {tag_filter}")

        self.summary_chips_layout.addStretch(1)
        self.summary_label.setText(" • ".join(parts))

    @staticmethod
    def _render_count_summary(counts: dict[str, int], *, limit: int) -> str:
        if not counts:
            return "—"
        ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0].lower()))
        return ", ".join(f"{label} ×{count}" for label, count in ordered[:limit])

    def _collect_card_metrics(self, items: list[DossierData]) -> tuple[dict[int, int], dict[int, str]]:
        link_counts: dict[int, int] = {}
        output_summaries: dict[int, str] = {}
        for item in items:
            links = self._db.fetch_dossier_links(item.id)
            link_counts[item.id] = len(links)
            output_summaries[item.id] = dossier_output_summary(links)
        return link_counts, output_summaries

    def refresh(self) -> None:
        filters = self.get_filters()
        items = self._db.fetch_dossiers(
            kind=filters.get("kind") if isinstance(filters.get("kind"), str) else None,
            status=filters.get("status") if isinstance(filters.get("status"), str) else None,
            search_text=self._query,
            tag=filters.get("tag") if isinstance(filters.get("tag"), str) and filters.get("tag") else None,
        )
        rating_filter = filters.get("rating")
        if isinstance(rating_filter, int):
            items = [item for item in items if item.rating == rating_filter]

        link_counts, output_summaries = self._collect_card_metrics(items)

        model = self.list_view.model()
        if isinstance(model, DossierListModel):
            model.set_items(
                items,
                group_by=str(filters.get("group_by") or "none"),
                link_counts=link_counts,
                output_summaries=output_summaries,
            )

        self._update_summary(items, str(filters.get("tag") or ""))
        self._last_refresh_text = datetime.now().strftime("%H:%M:%S")
        self._update_status_text(len(items))
        self._update_list_state(items)
        self._sync_view_mode_buttons(str(filters.get("view_mode") or "list"))
        self._sync_selection()

    def _update_list_state(self, items: list[DossierData]) -> None:
        filters = self.get_filters()
        has_query = bool(self._query.strip())
        has_filters = any(
            filters.get(key)
            for key in ("kind", "status", "rating", "tag")
        ) or str(filters.get("group_by") or "none") != "none"

        if items:
            self.left_mode_stack.setCurrentIndex(0)
            return

        self.left_mode_stack.setCurrentIndex(1)
        if has_query or has_filters:
            self.empty_list_title.setText("Ничего не найдено")
            self.empty_list_text.setText("Попробуйте изменить запрос или сбросить фильтры.")
            self.empty_secondary_button.setText("Сбросить фильтры")
            self.empty_secondary_button.setEnabled(True)
        else:
            self.empty_list_title.setText("Досье пока нет")
            self.empty_list_text.setText("Создайте первую карточку или импортируйте данные.")
            self.empty_secondary_button.setText("Импорт")
            self.empty_secondary_button.setEnabled(False)

    def _update_status_text(self, item_count: int) -> None:
        filters = self.get_filters()
        active_filters: list[str] = []
        if isinstance(filters.get("kind"), str):
            active_filters.append(dossier_kind_label(str(filters["kind"])))
        if isinstance(filters.get("status"), str):
            active_filters.append(dossier_status_label(str(filters["status"])))
        if isinstance(filters.get("rating"), int):
            active_filters.append(dossier_rating_label(filters["rating"]))
        if isinstance(filters.get("tag"), str) and filters.get("tag"):
            active_filters.append(f"тег: {filters['tag']}")

        group_label = next(
            (label for label, value in DOSSIER_GROUP_OPTIONS if value == str(filters.get("group_by") or "none")),
            "Без групп",
        )
        view_label = VIEW_MODE_LABELS.get(str(filters.get("view_mode") or "list"), "Список")
        filters_text = ", ".join(active_filters) if active_filters else "нет"
        self.status_row.setText(
            f"Найдено досье: {item_count} | Активные фильтры: {filters_text} | Вид: {view_label} | "
            f"Группы: {group_label} | Обновлено: {self._last_refresh_text}"
        )

    def _sync_selection(self) -> None:
        model = self.list_view.model()
        if not isinstance(model, DossierListModel):
            return
        if self._current_dossier_id is None:
            first_index = model.first_item_index()
            if first_index.isValid():
                self.list_view.setCurrentIndex(first_index)
            else:
                self._clear_preview()
                self.update_action_states()
            return
        index = model.index_for_id(self._current_dossier_id)
        if index.isValid():
            self.list_view.setCurrentIndex(index)
            return
        self._current_dossier_id = None
        first_index = model.first_item_index()
        if first_index.isValid():
            self.list_view.setCurrentIndex(first_index)
            return
        self._clear_preview()
        self.update_action_states()

    def _on_selection_changed(self) -> None:
        dossier_id = self.get_selection()
        self._current_dossier_id = dossier_id
        if dossier_id is None:
            self._clear_preview()
            self.update_action_states()
            return
        self._load_preview(dossier_id)
        self.update_action_states()

    def _clear_preview(self) -> None:
        self.preview_stack.setCurrentIndex(0)
        self.preview_title_label.setText("Досье не выбрано")
        self.preview_meta_label.setText("Выберите карточку слева, чтобы открыть инспектор.")
        self.preview_summary_label.clear()
        self.preview_description.clear()
        self.preview_tags_label.clear()
        self.preview_source_label.clear()
        self.preview_metadata_label.clear()
        self.preview_output_overview_label.clear()
        self.preview_output_label.clear()
        self.preview_output_hint_label.clear()
        self.preview_links.clear()
        self.preview_cover_label.setText("Нет обложки")
        self.preview_cover_label.setPixmap(QPixmap())
        self._update_link_action_states()

    def _render_metadata_html(self, dossier: DossierData) -> str:
        parts: list[str] = []
        for field_name in DossierData.METADATA_FIELDS[dossier.kind]:
            value = dossier.metadata.get(field_name)
            rendered = render_list_value(value) if value not in (None, "", []) else "—"
            label_text = DOSSIER_METADATA_LABELS.get(field_name, field_name.replace("_", " ").title())
            parts.append(f"<b>{label_text}</b><br>{rendered}")
        if not parts:
            return "Сведения пока не заполнены"
        return "<br><br>".join(parts)

    def _load_preview(self, dossier_id: int) -> None:
        dossier = self._db.get_dossier(dossier_id)
        if dossier is None:
            self._clear_preview()
            return

        links = self._db.fetch_dossier_links(dossier_id)
        output_summary = dossier_output_summary(links)

        self.preview_stack.setCurrentIndex(1)
        self.preview_title_label.setText(dossier.title or "Без названия")
        self.preview_meta_label.setText(dossier_secondary_line(dossier))
        self.preview_summary_label.setText(dossier.summary or "Краткое описание пока не заполнено.")
        self.preview_description.setPlainText(dossier.description or "")
        self.preview_tags_label.setText(f"Теги: {dossier_tags_text(dossier.tags)}")
        self.preview_source_label.setText(f"Источник: {dossier.source or 'Не указан'}")
        self.preview_metadata_label.setText(self._render_metadata_html(dossier))
        self.preview_output_overview_label.setText(f"Выход: {output_summary}")
        self.preview_output_label.setText(
            f"Мой вывод пока не сохранен отдельно.\n\nТекущий вычисляемый выход: {output_summary}."
        )
        self.preview_output_hint_label.setText(
            "Запись не должна быть тупиком: свяжите ее с задачей, идеей, картой, объектом или заметкой."
        )
        self.preview_links_header_label.setText(dossier_links_count_text(len(links)))

        cover_pixmap = load_dossier_cover_pixmap(dossier.cover_image)
        if cover_pixmap is None:
            self.preview_cover_label.setPixmap(QPixmap())
            self.preview_cover_label.setText(dossier_kind_label(dossier.kind))
        else:
            self.preview_cover_label.setText("")
            self.preview_cover_label.setPixmap(
                cover_pixmap.scaled(
                    self.preview_cover_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

        self.preview_links.clear()
        if links:
            for link in sorted(links, key=lambda item: (item.entity_kind, item.entity_id)):
                label = self._db.describe_dossier_link_target(link.entity_kind, link.entity_id)
                item = QListWidgetItem(f"{DOSSIER_LINK_KIND_LABELS.get(link.entity_kind, link.entity_kind.title())}: {label}")
                item.setData(LINK_ID_ROLE, link.id)
                item.setData(LINK_ENTITY_KIND_ROLE, link.entity_kind)
                item.setData(LINK_ENTITY_ID_ROLE, link.entity_id)
                self.preview_links.addItem(item)
        else:
            placeholder = QListWidgetItem(
                "Связей пока нет\nСвяжите досье с задачей, идеей, картой, объектом или персонажем."
            )
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            self.preview_links.addItem(placeholder)
        self._update_link_action_states()


__all__ = ["DossierLinkDialog", "DossierWorkspace"]
