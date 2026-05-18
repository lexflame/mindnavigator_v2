"""IdeasWorkspace class module for ideas workspace."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403
from PySide6.QtCore import QTimer
from .idea_category_edit_dialog import IdeaCategoryEditDialog, IdeaCategoryRenameDialog
from .ideas_list_model import IdeasListModel
from .ideas_delegate import IdeasDelegate
from .idea_image_preview_dialog import IdeaImagePreviewDialog
from .image_utils import load_scaled_pixmap
from mindnavigator.ui.styles import get_theme_palette
from mindnavigator.ui.dialogs import AttachFileSelectNav

IDEA_RELATION_KIND_ITEMS = [
    ("Задача", "task"),
    ("Заметка", "note"),
    ("Идея", "idea"),
    ("Объект", "object"),
    ("Карта", "map"),
    ("Метка карты", "marker"),
]

IDEA_RELATION_KIND_LABELS = {value: label for label, value in IDEA_RELATION_KIND_ITEMS}


class IdeaRelationDialog(QDialog):
    def __init__(self, candidates_by_kind: Dict[str, List[tuple[int, str]]], parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("IdeaRelationDialog")
        self.setWindowTitle("Добавить связь")
        self.setMinimumWidth(520)
        self._theme_mode = "dark"
        self._candidates_by_kind = candidates_by_kind

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("Связать идею с сущностью")
        title.setObjectName("IdeaRelationDialogTitle")
        layout.addWidget(title)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self.kind_combo = QComboBox()
        for label, value in IDEA_RELATION_KIND_ITEMS:
            self.kind_combo.addItem(label, value)

        self.target_combo = QComboBox()
        self.kind_combo.currentIndexChanged.connect(self._fill_targets)

        form.addRow("Тип", self.kind_combo)
        form.addRow("Элемент", self.target_combo)
        layout.addLayout(form)

        buttons_row = QHBoxLayout()
        buttons_row.addStretch(1)
        self.cancel_button = QToolButton()
        self.cancel_button.setText("Отмена")
        self.cancel_button.clicked.connect(self.reject)
        self.save_button = QToolButton()
        self.save_button.setText("Добавить")
        self.save_button.clicked.connect(self._accept)
        buttons_row.addWidget(self.cancel_button)
        buttons_row.addWidget(self.save_button)
        layout.addLayout(buttons_row)

        self._fill_targets()
        if parent is not None and hasattr(parent, "_theme_mode"):
            self.set_theme_mode(getattr(parent, "_theme_mode"))
        else:
            self.set_theme_mode("dark")

    def _fill_targets(self, *_args: object) -> None:
        entity_type = self.kind_combo.currentData()
        self.target_combo.clear()
        for entity_id, label in self._candidates_by_kind.get(entity_type, []):
            self.target_combo.addItem(label, entity_id)
        if self.target_combo.count() == 0:
            self.target_combo.addItem("— нет доступных элементов —", None)

    def _accept(self) -> None:
        if self.target_combo.currentData() is None:
            QMessageBox.warning(self, "Связи", "Выберите элемент для связи.")
            return
        self.accept()

    def values(self) -> dict[str, object]:
        return {
            "entity_type": self.kind_combo.currentData(),
            "entity_id": self.target_combo.currentData(),
        }

    def set_theme_mode(self, theme_mode: str) -> None:
        self._theme_mode = "light" if str(theme_mode).strip().lower() == "light" else "dark"
        palette = get_theme_palette(self._theme_mode)
        self.setStyleSheet(
            f"""
            QDialog#IdeaRelationDialog {{
                background: {palette.window_bg};
            }}

            QDialog#IdeaRelationDialog QLabel {{
                color: {palette.text};
            }}

            QDialog#IdeaRelationDialog QLabel#IdeaRelationDialogTitle {{
                color: {palette.text};
                font-size: 16px;
                font-weight: 600;
            }}

            QDialog#IdeaRelationDialog QComboBox {{
                background: {palette.input_bg};
                color: {palette.text};
                border: 1px solid {palette.border};
                padding: 6px 8px;
                border-radius: 6px;
            }}

            QDialog#IdeaRelationDialog QComboBox:focus {{
                border-color: {palette.accent};
            }}

            QDialog#IdeaRelationDialog QComboBox QAbstractItemView {{
                background: {palette.panel_bg};
                color: {palette.text};
                border: 1px solid {palette.border};
                selection-background-color: {palette.selection_bg};
                selection-color: {palette.selection_text};
            }}

            QDialog#IdeaRelationDialog QToolButton {{
                color: {palette.text};
                background: {palette.elevated_bg};
                border: 1px solid {palette.border_strong};
                padding: 6px 12px;
                border-radius: 6px;
            }}

            QDialog#IdeaRelationDialog QToolButton:hover {{
                background: {palette.selection_bg};
                color: {palette.selection_text};
            }}
        """
        )


class IdeasWorkspace(BaseWorkspace):
    workspace_id = "ideas"
    workspace_title = "Идеи"

    def __init__(self, parent: QWidget | None = None) -> None:
        self._db = get_database()
        self._csv_service = CsvTransferService()
        self._current_idea_id: Optional[int] = None
        self._current_project_id: Optional[int] = None
        self._dirty = False
        self._triage_mode = False
        self._theme_mode = "dark"
        self._idea_categories = []
        self._idea_categories_by_code: Dict[str, Any] = {}
        self._idea_images: List[IdeaImageData] = []
        self._current_material_index = 0
        super().__init__(parent)
        triage_action = self.actions.get("triage")
        if triage_action is not None:
            try:
                triage_action.triggered.disconnect()
            except (TypeError, RuntimeError):
                pass
            triage_action.triggered.connect(self._start_inbox_triage)
        self.setObjectName("IdeasWorkspace")
        self.search_input.setPlaceholderText("Поиск…")
        self.refresh()

    def _build_ui(self) -> None:
        super()._build_ui()

        self.status_filter = QComboBox()
        self.status_filter.currentIndexChanged.connect(self._on_status_filter_changed)
        self.manage_categories_btn = QToolButton()
        self.manage_categories_btn.setText("Категории")
        self.manage_categories_btn.setObjectName("IdeasManageCategories")
        self.manage_categories_btn.clicked.connect(self._open_manage_categories_menu)

        self.type_filter = QComboBox()
        for label, value in IDEA_TYPES:
            self.type_filter.addItem(label, value)
        self.type_filter.currentIndexChanged.connect(self._on_type_filter_changed)

        self.archived_only = QCheckBox("Только архив")
        self.archived_only.stateChanged.connect(self._on_archived_filter_changed)

        self.filter_layout.addWidget(QLabel("Статус"))
        self.filter_layout.addWidget(self.status_filter)
        self.filter_layout.addWidget(self.manage_categories_btn)
        self.filter_layout.addWidget(QLabel("Тип"))
        self.filter_layout.addWidget(self.type_filter)
        self.filter_layout.addWidget(self.archived_only)
        self.filter_layout.addStretch(1)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("IdeasSplitter")

        list_host = QWidget()
        list_layout = QVBoxLayout(list_host)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(6)

        quick_row = QWidget()
        quick_layout = QHBoxLayout(quick_row)
        quick_layout.setContentsMargins(0, 0, 0, 0)
        quick_layout.setSpacing(6)
        self.quick_status_btn = QToolButton()
        self.quick_status_btn.setText("Категория")
        self.quick_status_btn.setObjectName("IdeasQuickStatusBtn")
        self.quick_status_label = QLabel("Все категории")
        self.quick_status_label.setObjectName("IdeasQuickStatus")
        self.quick_title_input = QLineEdit()
        self.quick_title_input.setObjectName("IdeasQuickTitle")
        self.quick_title_input.setPlaceholderText("Быстрое создание идеи...")
        self.quick_create_btn = QToolButton()
        self.quick_create_btn.setText("Создать")
        self.quick_create_btn.setObjectName("IdeasQuickCreateBtn")
        quick_layout.addWidget(self.quick_status_btn)
        quick_layout.addWidget(self.quick_status_label)
        quick_layout.addWidget(self.quick_title_input, 1)
        quick_layout.addWidget(self.quick_create_btn)
        list_layout.addWidget(quick_row)

        self.list_view = QListView()
        self.list_view.setObjectName("IdeasList")
        self.list_view.setModel(IdeasListModel(self.list_view))
        self.list_view.setItemDelegate(IdeasDelegate(self.list_view))
        self.list_view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list_view.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.list_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list_view.selectionModel().selectionChanged.connect(self._on_selection_changed)
        self.list_view.doubleClicked.connect(self._open_selected)
        self.list_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_view.customContextMenuRequested.connect(self._show_context_menu)

        list_layout.addWidget(self.list_view, 1)
        splitter.addWidget(list_host)

        self.inspector_stack = QStackedWidget()
        self.inspector_stack.setObjectName("IdeasInspectorStack")
        self.inspector_empty = QLabel("Выберите идею слева")
        self.inspector_empty.setObjectName("IdeasEmpty")
        self.inspector_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.inspector_stack.addWidget(self.inspector_empty)

        self.inspector_tabs = QTabWidget()
        self.inspector_tabs.setObjectName("IdeasInspectorTabs")

        content_tab = QWidget()
        content_tab.setObjectName("IdeasContentTab")
        content_layout = QFormLayout(content_tab)
        content_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        content_layout.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        content_layout.setContentsMargins(14, 12, 14, 12)
        content_layout.setSpacing(10)

        self.title_input = QLineEdit()
        self.summary_input = QLineEdit()
        self.body_input = QPlainTextEdit()
        self.project_input = QComboBox()
        self._populate_projects()
        self.type_input = QComboBox()
        for label, value in IDEA_TYPES[1:]:
            self.type_input.addItem(label, value)
        self.status_input = QComboBox()
        self._reload_idea_categories()

        self.value_input = QSpinBox()
        self.value_input.setRange(1, 5)
        self.effort_input = QSpinBox()
        self.effort_input.setRange(1, 5)

        content_layout.addRow("Название", self.title_input)
        content_layout.addRow("Кратко", self.summary_input)
        content_layout.addRow("Описание", self.body_input)
        content_layout.addRow("Проект", self.project_input)
        content_layout.addRow("Тип", self.type_input)
        content_layout.addRow("Статус", self.status_input)
        content_layout.addRow("Ценность", self.value_input)
        content_layout.addRow("Сложность", self.effort_input)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        self.save_button = QToolButton()
        self.save_button.setText("Сохранить")
        self.save_button.setObjectName("IdeasSaveButton")
        self.save_button.clicked.connect(self._save_current)
        self.revert_button = QToolButton()
        self.revert_button.setText("Отменить")
        self.revert_button.setObjectName("IdeasRevertButton")
        self.revert_button.clicked.connect(self._revert_current)
        button_row.addWidget(self.revert_button)
        button_row.addWidget(self.save_button)
        content_layout.addRow("", button_row)

        self.inspector_tabs.addTab(content_tab, "Содержание")

        relations_tab = QWidget()
        relations_tab.setObjectName("IdeasRelationsTab")
        relations_layout = QVBoxLayout(relations_tab)
        relations_layout.setContentsMargins(12, 12, 12, 12)
        relations_layout.setSpacing(8)
        relations_actions = QHBoxLayout()
        self.relations_add_button = QToolButton()
        self.relations_add_button.setText("Добавить связь")
        self.relations_add_button.setObjectName("IdeasRelationsAdd")
        self.relations_add_button.clicked.connect(self._add_relation)
        self.relations_remove_button = QToolButton()
        self.relations_remove_button.setText("Удалить связь")
        self.relations_remove_button.setObjectName("IdeasRelationsRemove")
        self.relations_remove_button.clicked.connect(self._remove_selected_relation)
        relations_actions.addWidget(self.relations_add_button)
        relations_actions.addWidget(self.relations_remove_button)
        relations_actions.addStretch(1)
        relations_layout.addLayout(relations_actions)
        self.relations_list = QListWidget()
        self.relations_list.currentRowChanged.connect(lambda _row: self._update_relations_actions())
        relations_layout.addWidget(self.relations_list, 1)
        self.inspector_tabs.addTab(relations_tab, "Связи")

        materials_tab = QWidget()
        materials_tab.setObjectName("IdeasMaterialsTab")
        materials_layout = QVBoxLayout(materials_tab)
        materials_layout.setContentsMargins(12, 12, 12, 12)
        materials_layout.setSpacing(8)
        materials_actions = QHBoxLayout()
        self.materials_attach_button = QToolButton()
        self.materials_attach_button.setText("Прикрепить изображение")
        self.materials_attach_button.setObjectName("IdeasMaterialsAttach")
        self.materials_attach_button.clicked.connect(self._attach_material_image)
        self.materials_remove_button = QToolButton()
        self.materials_remove_button.setText("Удалить")
        self.materials_remove_button.setObjectName("IdeasMaterialsRemove")
        self.materials_remove_button.clicked.connect(self._remove_material_image)
        materials_actions.addWidget(self.materials_attach_button)
        materials_actions.addWidget(self.materials_remove_button)
        materials_actions.addStretch(1)

        self.materials_hint = QLabel("Прикрепите изображения из режима Файлы.")
        self.materials_hint.setObjectName("IdeasMaterialsHint")
        self.materials_hint.setWordWrap(True)

        self.materials_thumbnail_list = QListWidget()
        self.materials_thumbnail_list.setObjectName("IdeasMaterialsThumbnails")
        self.materials_thumbnail_list.setViewMode(QListView.ViewMode.IconMode)
        self.materials_thumbnail_list.setFlow(QListView.Flow.LeftToRight)
        self.materials_thumbnail_list.setResizeMode(QListView.ResizeMode.Adjust)
        self.materials_thumbnail_list.setMovement(QListView.Movement.Static)
        self.materials_thumbnail_list.setIconSize(QSize(64, 64))
        self.materials_thumbnail_list.setGridSize(QSize(92, 96))
        self.materials_thumbnail_list.setFixedHeight(112)
        self.materials_thumbnail_list.setSpacing(8)
        self.materials_thumbnail_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.materials_thumbnail_list.setToolTip("Двойной щелчок открывает изображение в полном размере.")
        self.materials_thumbnail_list.currentRowChanged.connect(self._on_material_thumbnail_selected)
        self.materials_thumbnail_list.itemDoubleClicked.connect(lambda _item: self._preview_material_image())

        self.materials_caption_input = QPlainTextEdit()
        self.materials_caption_input.setObjectName("IdeasMaterialsCaption")
        self.materials_caption_input.setPlaceholderText("Подпись к изображению...")

        self.materials_save_caption_button = QToolButton()
        self.materials_save_caption_button.setText("Сохранить подпись")
        self.materials_save_caption_button.setObjectName("IdeasMaterialsCaptionSave")
        self.materials_save_caption_button.clicked.connect(self._save_material_caption)

        materials_layout.addLayout(materials_actions)
        materials_layout.addWidget(self.materials_hint)
        materials_layout.addWidget(self.materials_thumbnail_list)
        materials_layout.addWidget(self.materials_caption_input)
        materials_layout.addWidget(self.materials_save_caption_button, 0, Qt.AlignmentFlag.AlignRight)
        self.inspector_tabs.addTab(materials_tab, "Материалы")

        transform_tab = QWidget()
        transform_tab.setObjectName("IdeasTransformTab")
        self.transform_tab = transform_tab
        transform_layout = QVBoxLayout(transform_tab)
        transform_layout.setContentsMargins(12, 12, 12, 12)
        transform_layout.setSpacing(8)
        self.triage_hint = QLabel(
            "Разбор инбокса: переведите идею в work или ripe, создайте задачу или отправьте в архив."
        )
        self.triage_hint.setObjectName("IdeasTriageHint")
        self.triage_hint.setWordWrap(True)
        transform_layout.addWidget(self.triage_hint)
        triage_row = QHBoxLayout()
        triage_row.setSpacing(6)
        self.triage_skip_btn = QToolButton()
        self.triage_skip_btn.setText("Пропустить")
        self.triage_skip_btn.setObjectName("IdeasTriageSkip")
        self.triage_skip_btn.clicked.connect(self._skip_inbox_idea)
        self.triage_work_btn = QToolButton()
        self.triage_work_btn.setText("В work")
        self.triage_work_btn.setObjectName("IdeasTriageWork")
        self.triage_work_btn.clicked.connect(lambda: self._triage_current_status("work"))
        self.triage_ripe_btn = QToolButton()
        self.triage_ripe_btn.setText("В ripe")
        self.triage_ripe_btn.setObjectName("IdeasTriageRipe")
        self.triage_ripe_btn.clicked.connect(lambda: self._triage_current_status("ripe"))
        self.triage_archive_btn = QToolButton()
        self.triage_archive_btn.setText("В архив")
        self.triage_archive_btn.setObjectName("IdeasTriageArchive")
        self.triage_archive_btn.clicked.connect(self._triage_archive_current)
        triage_row.addWidget(self.triage_skip_btn)
        triage_row.addWidget(self.triage_work_btn)
        triage_row.addWidget(self.triage_ripe_btn)
        triage_row.addWidget(self.triage_archive_btn)
        transform_layout.addLayout(triage_row)
        self.transform_task_btn = QToolButton()
        self.transform_task_btn.setText("✅ Создать задачу")
        self.transform_task_btn.setObjectName("IdeasTransformTask")
        self.transform_task_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.transform_task_btn.clicked.connect(lambda: self._triage_transform("task"))
        self.transform_note_btn = QToolButton()
        self.transform_note_btn.setText("📝 Создать заметку")
        self.transform_note_btn.setObjectName("IdeasTransformNote")
        self.transform_note_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.transform_note_btn.clicked.connect(lambda: self._transform_idea("note"))
        self.transform_object_btn = QToolButton()
        self.transform_object_btn.setText("🧱 Создать объект")
        self.transform_object_btn.setObjectName("IdeasTransformObject")
        self.transform_object_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.transform_object_btn.clicked.connect(lambda: self._transform_idea("object"))
        self.transform_marker_btn = QToolButton()
        self.transform_marker_btn.setText("🗺️ Создать метку")
        self.transform_marker_btn.setObjectName("IdeasTransformMarker")
        self.transform_marker_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.transform_marker_btn.clicked.connect(lambda: self._transform_idea("marker"))
        self._transform_action_buttons = [
            self.transform_task_btn,
            self.transform_note_btn,
            self.transform_object_btn,
            self.transform_marker_btn,
        ]
        self._transform_action_min_width = max(button.sizeHint().width() for button in self._transform_action_buttons)
        self.transform_actions_host = QWidget()
        self.transform_actions_host.setObjectName("IdeasTransformActionsHost")
        transform_actions_row = QHBoxLayout(self.transform_actions_host)
        transform_actions_row.setContentsMargins(0, 0, 0, 0)
        transform_actions_row.setSpacing(6)
        transform_actions_row.addWidget(self.transform_task_btn, 1)
        transform_actions_row.addWidget(self.transform_note_btn, 1)
        transform_actions_row.addWidget(self.transform_object_btn, 1)
        transform_actions_row.addWidget(self.transform_marker_btn, 1)
        transform_layout.addWidget(self.transform_actions_host)
        transform_layout.addStretch(1)
        self.inspector_tabs.addTab(transform_tab, "Решение")

        self.inspector_stack.addWidget(self.inspector_tabs)
        splitter.addWidget(self.inspector_stack)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 4)

        self.set_content(splitter)

        self.title_input.textChanged.connect(self._mark_dirty)
        self.summary_input.textChanged.connect(self._mark_dirty)
        self.body_input.textChanged.connect(self._mark_dirty)
        self.project_input.currentIndexChanged.connect(self._on_project_changed)
        self.type_input.currentIndexChanged.connect(self._mark_dirty)
        self.status_input.currentIndexChanged.connect(self._mark_dirty)
        self.value_input.valueChanged.connect(self._mark_dirty)
        self.effort_input.valueChanged.connect(self._mark_dirty)
        self.quick_create_btn.clicked.connect(self._create_idea_from_quick_form)
        self.quick_status_btn.clicked.connect(self._open_quick_status_menu)
        self.quick_title_input.returnPressed.connect(self._create_idea_from_quick_form)
        self._set_quick_status(None)
        self._update_material_view()

        self.set_theme_mode("dark")
        QTimer.singleShot(0, self._sync_transform_action_widths)

    def showEvent(self, event) -> None:  # noqa: N802 - Qt API
        super().showEvent(event)
        QTimer.singleShot(0, self._sync_transform_action_widths)

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt API
        super().resizeEvent(event)
        self._sync_transform_action_widths()

    def _sync_transform_action_widths(self) -> None:
        if not hasattr(self, "transform_actions_host"):
            return
        layout = self.transform_actions_host.layout()
        if layout is None:
            return
        count = len(getattr(self, "_transform_action_buttons", []))
        if count == 0:
            return
        available_width = self.transform_actions_host.width()
        if available_width <= 0:
            return
        spacing_total = layout.spacing() * (count - 1)
        target_width = max(self._transform_action_min_width, max(1, (available_width - spacing_total) // count))
        for button in self._transform_action_buttons:
            button.setFixedWidth(target_width)

    def set_theme_mode(self, theme_mode: str) -> None:
        self._theme_mode = "light" if str(theme_mode).strip().lower() == "light" else "dark"
        palette = get_theme_palette(self._theme_mode)
        self.setStyleSheet(
            f"""
            QWidget#IdeasWorkspace {{ background: {palette.window_bg}; }}

            QWidget#IdeasWorkspace QLabel {{
                color: {palette.text};
            }}

            QLabel#IdeasQuickStatus {{
                color: {palette.chart_muted};
                font-size: 11px;
            }}

            QWidget#IdeasWorkspace QWidget#WorkspaceToolbar,
            QWidget#IdeasWorkspace QWidget#WorkspaceSearch,
            QWidget#IdeasWorkspace QWidget#WorkspaceFilters {{
                background: {palette.panel_bg};
                border: 1px solid {palette.border};
                border-radius: 10px;
                padding: 6px;
            }}

            QWidget#IdeasWorkspace QWidget#WorkspaceStatus {{
                color: {palette.dim_text};
            }}

            QWidget#IdeasWorkspace QToolButton {{
                color: {palette.text};
                background: {palette.elevated_bg};
                border: 1px solid {palette.border_strong};
                padding: 6px 10px;
                border-radius: 6px;
            }}
            QWidget#IdeasWorkspace QToolButton:hover {{
                background: {palette.selection_bg};
                color: {palette.selection_text};
            }}
            QWidget#IdeasWorkspace QToolButton:disabled {{
                color: {palette.muted_text};
                background: {palette.panel_bg};
                border-color: {palette.border};
            }}

            QWidget#IdeasWorkspace QLineEdit,
            QWidget#IdeasWorkspace QPlainTextEdit,
            QWidget#IdeasWorkspace QComboBox,
            QWidget#IdeasWorkspace QSpinBox {{
                background: {palette.input_bg};
                color: {palette.text};
                border: 1px solid {palette.border};
                padding: 6px 8px;
                border-radius: 6px;
            }}

            QWidget#IdeasWorkspace QLineEdit:focus,
            QWidget#IdeasWorkspace QPlainTextEdit:focus,
            QWidget#IdeasWorkspace QComboBox:focus,
            QWidget#IdeasWorkspace QSpinBox:focus {{
                border-color: {palette.accent};
            }}

            QWidget#IdeasWorkspace QCheckBox {{
                color: {palette.text};
                padding: 2px 4px;
            }}

            QListView#IdeasList {{
                background: {palette.window_bg};
                border: 1px solid {palette.border};
                border-radius: 10px;
                padding: 6px;
            }}

            QStackedWidget#IdeasInspectorStack {{
                background: transparent;
            }}

            QTabWidget#IdeasInspectorTabs::pane {{
                border: 1px solid {palette.border};
                background: {palette.panel_bg};
                border-radius: 10px;
                padding: 6px;
            }}

            QWidget#IdeasContentTab,
            QWidget#IdeasRelationsTab,
            QWidget#IdeasMaterialsTab,
            QWidget#IdeasTransformTab {{
                background: transparent;
            }}

            QTabWidget#IdeasInspectorTabs QTabBar::tab {{
                background: {palette.input_bg};
                color: {palette.text};
                padding: 6px 12px;
                margin-right: 4px;
                border-radius: 6px;
            }}
            QTabWidget#IdeasInspectorTabs QTabBar::tab:selected {{
                background: {palette.selection_bg};
                color: {palette.selection_text};
            }}

            QWidget#IdeasWorkspace QListWidget {{
                background: {palette.window_bg};
                color: {palette.text};
                border: 1px solid {palette.border};
                border-radius: 8px;
                padding: 6px;
            }}

            QLabel#IdeasEmpty {{
                color: {palette.dim_text};
            }}
        """
        )

    def create_actions(self) -> dict[str, QAction]:
        action_new = QAction("+ Идея", self)
        action_new.triggered.connect(self._create_default_idea)
        action_export = QAction("Экспорт", self)
        action_export.triggered.connect(self._export_ideas_csv)
        action_import = QAction("Импорт", self)
        action_import.triggered.connect(self._import_ideas_csv)
        action_triage = QAction("Разобрать инбокс", self)
        action_triage.triggered.connect(lambda: self._set_status("Разбор инбокса пока не реализован"))
        action_archive = QAction("В архив", self)
        action_archive.triggered.connect(self._archive_selected)
        return {
            "new": action_new,
            "export": action_export,
            "import": action_import,
            "triage": action_triage,
            "archive": action_archive,
        }

    def build_toolbar(self, actions: dict[str, QAction]) -> None:
        while self.toolbar_layout.count():
            item = self.toolbar_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.toolbar_layout.addStretch(1)
        for action in actions.values():
            button = QToolButton()
            button.setDefaultAction(action)
            self.toolbar_layout.addWidget(button)

    def get_selection(self):
        index = self.list_view.currentIndex()
        if not index.isValid() or index.data(IdeaRoles.RowType) != "idea":
            return None
        return index.data(IdeaRoles.IdeaId)

    def _set_status(self, text: str) -> None:
        self.status_row.setText(text)

    def _category_titles(self) -> Dict[str, str]:
        return {category.code: category.title for category in self._idea_categories}

    def _category_order_map(self) -> Dict[str, int]:
        return {category.code: index for index, category in enumerate(self._idea_categories)}

    def _category_title(self, status: Optional[str]) -> str:
        normalized = (status or "").strip().lower()
        return normalize_idea_category(normalized, self._category_titles())

    def _reload_idea_categories(
        self,
        *,
        filter_value: Optional[str] = None,
        editor_value: Optional[str] = None,
    ) -> None:
        if filter_value is None and hasattr(self, "status_filter") and self.status_filter.count():
            current_filter = self.status_filter.currentData()
            filter_value = current_filter if isinstance(current_filter, str) else None
        if editor_value is None and hasattr(self, "status_input") and self.status_input.count():
            current_editor = self.status_input.currentData()
            editor_value = current_editor if isinstance(current_editor, str) else None

        self._idea_categories = self._db.list_idea_categories()
        self._idea_categories_by_code = {category.code: category for category in self._idea_categories}

        self.status_filter.blockSignals(True)
        self.status_filter.clear()
        self.status_filter.addItem("Все", None)
        for category in self._idea_categories:
            self.status_filter.addItem(category.title, category.code)
        filter_index = self.status_filter.findData(filter_value)
        self.status_filter.setCurrentIndex(filter_index if filter_index >= 0 else 0)
        self.status_filter.blockSignals(False)

        self.status_input.blockSignals(True)
        self.status_input.clear()
        for category in self._idea_categories:
            self.status_input.addItem(category.title, category.code)
        target_editor = editor_value or "inbox"
        editor_index = self.status_input.findData(target_editor)
        self.status_input.setCurrentIndex(editor_index if editor_index >= 0 else 0)
        self.status_input.blockSignals(False)

        selected_filter = self.status_filter.currentData()
        self._set_quick_status(selected_filter if isinstance(selected_filter, str) else None)

    def _choose_category_code(
        self,
        *,
        dialog_title: str,
        prompt_text: str,
        include_system: bool,
    ) -> Optional[str]:
        categories = [category for category in self._idea_categories if include_system or not category.is_system]
        if not categories:
            QMessageBox.information(self, dialog_title, "Нет доступных категорий.")
            return None
        labels = [category.title for category in categories]
        selected_label, accepted = QInputDialog.getItem(self, dialog_title, prompt_text, labels, 0, False)
        if not accepted:
            return None
        for category in categories:
            if category.title == selected_label:
                return category.code
        return None

    def _create_idea_category(self) -> None:
        if self._dirty and not self._maybe_save_changes():
            return
        dialog = IdeaCategoryEditDialog(
            title="Категории идей",
            heading="Создание категории",
            field_label="Название",
            submit_text="Создать",
            parent=self,
        )
        if exec_with_overlay(dialog, self) != QDialog.DialogCode.Accepted:
            return
        title = dialog.title_value()
        if not title:
            return
        try:
            category = self._db.create_idea_category(title)
        except ValueError as exc:
            QMessageBox.warning(self, "Категории идей", str(exc))
            return
        self._reload_idea_categories()
        self.refresh()
        self._set_status(f"Категория «{category.title}» добавлена")

    def _rename_idea_category(self) -> None:
        if self._dirty and not self._maybe_save_changes():
            return
        categories = [(category.code, category.title) for category in self._idea_categories]
        if not categories:
            QMessageBox.information(self, "Категории идей", "Нет доступных категорий.")
            return
        dialog = IdeaCategoryRenameDialog(categories=categories, parent=self)
        if exec_with_overlay(dialog, self) != QDialog.DialogCode.Accepted:
            return
        category_code = dialog.category_code()
        category = self._idea_categories_by_code.get(category_code)
        if category is None:
            return
        title = dialog.title_value()
        if not title:
            return
        try:
            updated = self._db.update_idea_category_title(category_code, title)
        except ValueError as exc:
            QMessageBox.warning(self, "Категории идей", str(exc))
            return
        self._reload_idea_categories(filter_value=category_code, editor_value=category_code)
        self.refresh()
        self._set_status(f"Категория «{updated.title}» переименована")

    def _delete_idea_category(self) -> None:
        if self._dirty and not self._maybe_save_changes():
            return
        category_code = self._choose_category_code(
            dialog_title="Категории идей",
            prompt_text="Удалить категорию:",
            include_system=False,
        )
        if category_code is None:
            return
        category = self._idea_categories_by_code.get(category_code)
        if category is None:
            return
        confirm = QMessageBox.question(
            self,
            "Удалить категорию",
            f"Удалить категорию «{category.title}»? Идеи будут перенесены в Inbox.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            self._db.delete_idea_category(category_code)
        except ValueError as exc:
            QMessageBox.warning(self, "Категории идей", str(exc))
            return
        self._reload_idea_categories(editor_value="inbox")
        self.refresh()
        self._set_status(f"Категория «{category.title}» удалена")

    def _open_manage_categories_menu(self, *_args: object) -> None:
        menu = QMenu(self)
        create_action = menu.addAction("Создать категорию")
        rename_action = menu.addAction("Переименовать категорию")
        delete_action = menu.addAction("Удалить категорию")
        chosen = menu.exec(self.manage_categories_btn.mapToGlobal(self.manage_categories_btn.rect().bottomLeft()))
        if chosen == create_action:
            self._create_idea_category()
        elif chosen == rename_action:
            self._rename_idea_category()
        elif chosen == delete_action:
            self._delete_idea_category()

    def _mark_dirty(self, *_args: object) -> None:
        self._dirty = True

    def _populate_projects(self, selected_id: Optional[int] = None) -> None:
        self.project_input.blockSignals(True)
        self.project_input.clear()
        self.project_input.addItem("Без проекта", None)
        projects = get_database().fetch_projects()
        projects_by_id = {project.id: project for project in projects}
        title_cache: Dict[int, str] = {}

        def full_title(project_id: int, seen: Optional[set[int]] = None) -> str:
            cached = title_cache.get(project_id)
            if cached is not None:
                return cached
            project = projects_by_id.get(project_id)
            if project is None:
                return ""
            seen_set = seen or set()
            if project_id in seen_set:
                title_cache[project_id] = project.title
                return project.title
            if project.parent_project_id is None:
                title_cache[project_id] = project.title
                return project.title
            parent_title = full_title(project.parent_project_id, seen_set | {project_id})
            resolved = f"{parent_title} / {project.title}" if parent_title else project.title
            title_cache[project_id] = resolved
            return resolved

        visible_projects = [
            project
            for project in projects
            if not project.archived or project.id == selected_id
        ]
        visible_projects.sort(
            key=lambda project: (
                project.area.lower(),
                full_title(project.id).lower(),
                project.id,
            )
        )
        for project in visible_projects:
            title = full_title(project.id)
            label = f"{project.area} · {title}" if project.area else title
            if project.archived:
                label = f"{label} (архив)"
            self.project_input.addItem(label, project.id)
        selected_index = self.project_input.findData(selected_id)
        self.project_input.setCurrentIndex(selected_index if selected_index >= 0 else 0)
        self.project_input.blockSignals(False)

    def _on_project_changed(self, _index: int) -> None:
        self._current_project_id = self.project_input.currentData()
        self._mark_dirty()

    def _update_relations_actions(self) -> None:
        has_idea = self._current_idea_id is not None
        current_item = self.relations_list.currentItem()
        relation_id = current_item.data(Qt.ItemDataRole.UserRole) if current_item is not None else None
        self.relations_add_button.setEnabled(has_idea)
        self.relations_remove_button.setEnabled(has_idea and relation_id is not None)

    def refresh_current_relations(self) -> None:
        if self._current_idea_id is None:
            self._update_relations_actions()
            return
        self._load_relations(self._current_idea_id)

    def _relation_candidates_by_kind(self) -> Dict[str, List[tuple[int, str]]]:
        candidates: Dict[str, List[tuple[int, str]]] = {
            "task": [],
            "note": [],
            "idea": [],
            "object": [],
            "map": [],
            "marker": [],
        }
        for task in self._db.fetch_tasks():
            label = f"{task.title} · {task.project_title}" if task.project_title else task.title
            candidates["task"].append((task.id, label))
        for note in self._db.fetch_notes():
            label = f"{note.title} · {note.project}" if note.project else note.title
            candidates["note"].append((note.id, label))
        seen_idea_ids: set[int] = set()
        for archived in (False, True):
            for idea in self._db.fetch_ideas(archived=archived):
                if idea.id == self._current_idea_id or idea.id in seen_idea_ids:
                    continue
                seen_idea_ids.add(idea.id)
                label = f"{idea.title} · {idea.project_title}" if idea.project_title else idea.title
                candidates["idea"].append((idea.id, label))
        for obj in self._db.fetch_objects():
            label = f"{obj.title} · {obj.catalog}" if obj.catalog else obj.title
            candidates["object"].append((obj.id, label))
        for map_item in self._db.fetch_maps():
            label = f"{map_item.title} · {map_item.project}" if map_item.project else map_item.title
            candidates["map"].append((map_item.id, label))
        fetch_markers = getattr(self._db, "fetch_map_markers", None)
        if callable(fetch_markers):
            map_titles = {map_item.id: map_item.title for map_item in self._db.fetch_maps()}
            for marker in fetch_markers():
                map_title = map_titles.get(marker.map_id, "")
                label = f"{marker.name} · {map_title}" if map_title else marker.name
                candidates["marker"].append((marker.id, label))
        for entity_type, items in candidates.items():
            items.sort(key=lambda item: (item[1].casefold(), item[0]))
            candidates[entity_type] = items
        return candidates

    def _relation_display_label(self, entity_type: str, entity_id: int) -> str:
        label_prefix = IDEA_RELATION_KIND_LABELS.get(entity_type, entity_type.capitalize())
        if entity_type == "task":
            task = next((item for item in self._db.fetch_tasks() if item.id == entity_id), None)
            if task is not None:
                suffix = f"{task.title} · {task.project_title}" if task.project_title else task.title
                return f"{label_prefix} · {suffix}"
        elif entity_type == "note":
            note = next((item for item in self._db.fetch_notes() if item.id == entity_id), None)
            if note is not None:
                suffix = f"{note.title} · {note.project}" if note.project else note.title
                return f"{label_prefix} · {suffix}"
        elif entity_type == "idea":
            for archived in (False, True):
                idea = next((item for item in self._db.fetch_ideas(archived=archived) if item.id == entity_id), None)
                if idea is not None:
                    suffix = f"{idea.title} · {idea.project_title}" if idea.project_title else idea.title
                    return f"{label_prefix} · {suffix}"
        elif entity_type == "object":
            obj = next((item for item in self._db.fetch_objects() if item.id == entity_id), None)
            if obj is not None:
                suffix = f"{obj.title} · {obj.catalog}" if obj.catalog else obj.title
                return f"{label_prefix} · {suffix}"
        elif entity_type == "map":
            map_item = next((item for item in self._db.fetch_maps() if item.id == entity_id), None)
            if map_item is not None:
                suffix = f"{map_item.title} · {map_item.project}" if map_item.project else map_item.title
                return f"{label_prefix} · {suffix}"
        elif entity_type == "marker":
            fetch_markers = getattr(self._db, "fetch_map_markers", None)
            if callable(fetch_markers):
                marker = next((item for item in fetch_markers() if item.id == entity_id), None)
                if marker is not None:
                    map_titles = {map_item.id: map_item.title for map_item in self._db.fetch_maps()}
                    map_title = map_titles.get(marker.map_id, "")
                    suffix = f"{marker.name} · {map_title}" if map_title else marker.name
                    return f"{label_prefix} · {suffix}"
        return f"{label_prefix} #{entity_id}"

    def _add_relation(self) -> None:
        if self._current_idea_id is None:
            return
        candidates_by_kind = self._relation_candidates_by_kind()
        if not any(candidates_by_kind.values()):
            QMessageBox.information(self, "Связи", "Нет доступных элементов для связывания.")
            return
        dialog = IdeaRelationDialog(candidates_by_kind, parent=self)
        if exec_with_overlay(dialog, self) != QDialog.DialogCode.Accepted:
            return
        values = dialog.values()
        entity_type = values.get("entity_type")
        entity_id = values.get("entity_id")
        if not isinstance(entity_type, str) or not isinstance(entity_id, int):
            QMessageBox.warning(self, "Связи", "Выберите элемент для связи.")
            return
        self._db.add_idea_relation(self._current_idea_id, entity_type, entity_id)
        self._load_relations(self._current_idea_id)
        self._set_status("Связь добавлена")

    def _remove_selected_relation(self) -> None:
        if self._current_idea_id is None:
            return
        current_item = self.relations_list.currentItem()
        if current_item is None or current_item.data(Qt.ItemDataRole.UserRole) is None:
            QMessageBox.information(self, "Связи", "Выберите связь для удаления.")
            return
        relation_id = int(current_item.data(Qt.ItemDataRole.UserRole))
        self._db.delete_idea_relation(relation_id)
        self._load_relations(self._current_idea_id)
        self._set_status("Связь удалена")

    def _on_status_filter_changed(self, *_args: object) -> None:
        status = self.status_filter.currentData()
        self.set_filter("status", status)
        self._set_quick_status(status if isinstance(status, str) else None)

    def _on_type_filter_changed(self, *_args: object) -> None:
        self.set_filter("type", self.type_filter.currentData())

    def _on_archived_filter_changed(self, *_args: object) -> None:
        self.set_filter("archived", self.archived_only.isChecked())

    def apply_query(self, query: str) -> None:
        self.refresh()

    def apply_filters(self, filters: dict[str, object]) -> None:
        self.refresh()

    def refresh(self) -> None:
        filters = self.get_filters()
        ideas = self._db.fetch_ideas(
            project_id=None,
            search=self._query,
            status=filters.get("status"),
            idea_type=filters.get("type"),
            archived=bool(filters.get("archived")),
        )
        items = [
            IdeaItem(
                id=idea.id,
                title=idea.title,
                summary=idea.summary,
                body_md=idea.body_md,
                status=idea.status,
                idea_type=idea.type,
                value_score=idea.value_score,
                effort_score=idea.effort_score,
                project_id=idea.project_id,
                project_title=idea.project_title,
                archived=idea.archived_at is not None,
            )
            for idea in ideas
        ]
        model = self.list_view.model()
        if isinstance(model, IdeasListModel):
            model.set_items(
                items,
                status_titles=self._category_titles(),
                status_order=self._category_order_map(),
            )
            quick_status = self.quick_status_label.property("quick_status")
            if isinstance(quick_status, str) and quick_status not in model.statuses():
                self._set_quick_status(None)
        self._sync_selection()

    def _sync_selection(self) -> None:
        if self._current_idea_id is None:
            self._current_project_id = None
            self.inspector_stack.setCurrentWidget(self.inspector_empty)
            self._update_relations_actions()
            self.update_action_states()
            return
        model = self.list_view.model()
        if isinstance(model, IdeasListModel):
            index = model.index_for_id(self._current_idea_id)
            if index.isValid():
                self.list_view.setCurrentIndex(index)
                self.inspector_stack.setCurrentWidget(self.inspector_tabs)
                self._load_idea(self._current_idea_id)
                return
        self._current_idea_id = None
        self.inspector_stack.setCurrentWidget(self.inspector_empty)
        self._update_relations_actions()
        self.update_action_states()

    def _on_selection_changed(self, *_args: object) -> None:
        if self._dirty and not self._maybe_save_changes():
            self._sync_selection()
            return
        index = self.list_view.currentIndex()
        if not index.isValid() or index.data(IdeaRoles.RowType) != "idea":
            self._current_idea_id = None
            self._current_project_id = None
            self.inspector_stack.setCurrentWidget(self.inspector_empty)
            self._update_relations_actions()
            self.update_action_states()
            return
        self._current_idea_id = index.data(IdeaRoles.IdeaId)
        self._load_idea(self._current_idea_id)
        self.inspector_stack.setCurrentWidget(self.inspector_tabs)
        self.update_action_states()

    def _open_selected(self, *_args: object) -> None:
        if self._current_idea_id is None:
            return
        self.inspector_stack.setCurrentWidget(self.inspector_tabs)
        self.title_input.setFocus()

    def _load_idea(self, idea_id: int) -> None:
        idea = self._db.get_idea(idea_id)
        if idea is None:
            return
        self._populate_projects(idea.project_id)
        self._current_project_id = self.project_input.currentData()
        self.title_input.setText(idea.title)
        self.summary_input.setText(idea.summary)
        self.body_input.setPlainText(idea.body_md)
        self._set_combo_value(self.type_input, idea.type)
        self._set_combo_value(self.status_input, idea.status)
        self.value_input.setValue(idea.value_score)
        self.effort_input.setValue(idea.effort_score)
        self._dirty = False
        self._load_relations(idea_id)
        self._load_materials(idea_id)

    @staticmethod
    def _set_combo_value(combo: QComboBox, value: str) -> None:
        for i in range(combo.count()):
            if combo.itemData(i) == value:
                combo.setCurrentIndex(i)
                return

    def _maybe_save_changes(self) -> bool:
        if not self._dirty or self._current_idea_id is None:
            return True
        dialog = ConfirmDialog(
            "Сохранить изменения?",
            "Есть несохраненные изменения. Сохранить?",
            parent=self,
            confirm_text="Сохранить",
            cancel_text="Отменить",
        )
        result = exec_with_overlay(dialog, self)
        if result == QDialog.DialogCode.Accepted:
            return self._save_current()
        self._dirty = False
        return True

    def _save_current(self, *_args: object) -> bool:
        if self._current_idea_id is None:
            return False
        idea = self._db.update_idea(
            idea_id=self._current_idea_id,
            title=self.title_input.text(),
            summary=self.summary_input.text(),
            body_md=self.body_input.toPlainText(),
            idea_type=self.type_input.currentData(),
            status=self.status_input.currentData(),
            value_score=self.value_input.value(),
            effort_score=self.effort_input.value(),
            project_id=self._current_project_id,
        )
        self._dirty = False
        self._set_status("Изменения сохранены")
        self.refresh()
        model = self.list_view.model()
        if isinstance(model, IdeasListModel):
            index = model.index_for_id(idea.id)
            if index.isValid():
                self.list_view.setCurrentIndex(index)
        return True

    def _revert_current(self, *_args: object) -> None:
        if self._current_idea_id is None:
            return
        self._load_idea(self._current_idea_id)
        self._dirty = False
        self._set_status("Изменения отменены")

    def _create_idea(self, title: str = "Новая идея", status: Optional[str] = None) -> None:
        status_value = (status or "").strip().lower() or "inbox"
        idea = self._db.create_idea(title, status=status_value)
        self.refresh()
        self._current_idea_id = idea.id
        self._sync_selection()
        self._open_selected()

    def _create_default_idea(self, checked: bool = False) -> None:
        _ = checked
        self._create_idea()

    def _set_quick_status(self, status: Optional[str]) -> None:
        normalized = (status or "").strip().lower()
        if not normalized:
            self.quick_status_label.setText("Все категории")
            self.quick_status_label.setProperty("quick_status", None)
            return
        self.quick_status_label.setText(self._category_title(normalized))
        self.quick_status_label.setProperty("quick_status", normalized)

    def _open_quick_status_menu(self, *_args: object) -> None:
        menu = QMenu(self)
        action_all = menu.addAction("Все категории")
        menu.addSeparator()
        status_actions: Dict[Any, str] = {}
        for category in self._idea_categories:
            action = menu.addAction(category.title)
            status_actions[action] = category.code
        chosen = menu.exec(self.quick_status_btn.mapToGlobal(self.quick_status_btn.rect().bottomLeft()))
        if chosen is None:
            return
        if chosen == action_all:
            self.status_filter.setCurrentIndex(0)
            return
        selected = status_actions.get(chosen)
        if selected is None:
            return
        for idx in range(self.status_filter.count()):
            if self.status_filter.itemData(idx) == selected:
                self.status_filter.setCurrentIndex(idx)
                break

    def _create_idea_from_quick_form(self, *_args: object) -> None:
        title = (self.quick_title_input.text() or "").strip() or "Новая идея"
        quick_status = self.quick_status_label.property("quick_status")
        status = quick_status if isinstance(quick_status, str) and quick_status else "inbox"
        self._create_idea(title=title, status=status)
        self.quick_title_input.clear()

    def _archive_selected(self, *_args: object) -> None:
        idea_id = self.get_selection()
        if idea_id is None:
            return
        idea = self._db.get_idea(idea_id)
        if idea is None:
            return
        archived = idea.archived_at is None
        self._db.set_idea_archived(idea_id, archived)
        self._set_status("Идея архивирована" if archived else "Идея восстановлена")
        self.refresh()

    def _delete_selected(self) -> None:
        idea_id = self.get_selection()
        if idea_id is None:
            return
        dialog = ConfirmDialog(
            "Удалить идею",
            "Это действие нельзя отменить. Удалить идею?",
            parent=self,
            confirm_text="Удалить",
            cancel_text="Отмена",
        )
        if exec_with_overlay(dialog, self) != QDialog.DialogCode.Accepted:
            return
        self._db.delete_idea(idea_id)
        self._current_idea_id = None
        self._current_project_id = None
        self.refresh()
        self._set_status("Идея удалена")

    def _show_context_menu(self, pos) -> None:
        index = self.list_view.indexAt(pos)
        if not index.isValid() or index.data(IdeaRoles.RowType) != "idea":
            return
        idea_id = index.data(IdeaRoles.IdeaId)
        idea = self._db.get_idea(idea_id)
        menu = QMenu(self)
        action_edit = menu.addAction("Edit")
        action_archive = menu.addAction("Archive" if idea and not idea.archived_at else "Unarchive")
        action_delete = menu.addAction("Delete")
        transform_menu = menu.addMenu("Transform")
        transform_task = transform_menu.addAction("Task")
        transform_note = transform_menu.addAction("Note")
        transform_object = transform_menu.addAction("Object")
        transform_marker = transform_menu.addAction("Marker")

        action = menu.exec(QCursor.pos())
        if action == action_edit:
            self.list_view.setCurrentIndex(index)
            self._open_selected()
        elif action == action_archive:
            self._current_idea_id = idea_id
            self._archive_selected()
        elif action == action_delete:
            self._current_idea_id = idea_id
            self._delete_selected()
        elif action == transform_task:
            self._current_idea_id = idea_id
            self._transform_idea("task")
        elif action == transform_note:
            self._current_idea_id = idea_id
            self._transform_idea("note")
        elif action == transform_object:
            self._current_idea_id = idea_id
            self._transform_idea("object")
        elif action == transform_marker:
            self._current_idea_id = idea_id
            self._transform_idea("marker")

    def _load_relations(self, idea_id: int) -> None:
        self.relations_list.clear()
        relations = self._db.fetch_idea_relations(idea_id)
        if not relations:
            item = QListWidgetItem("Связей пока нет")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.relations_list.addItem(item)
            self._update_relations_actions()
            return
        for relation in relations:
            item = QListWidgetItem(self._relation_display_label(relation.entity_type, relation.entity_id))
            item.setData(Qt.ItemDataRole.UserRole, relation.id)
            self.relations_list.addItem(item)
        self._update_relations_actions()

    def _load_materials(self, idea_id: int) -> None:
        self._idea_images = self._db.fetch_idea_images(idea_id)
        self._current_material_index = 0
        self._refresh_material_thumbnails()
        self._update_material_view()

    def _refresh_material_thumbnails(self) -> None:
        self.materials_thumbnail_list.blockSignals(True)
        self.materials_thumbnail_list.clear()
        cloud_root = self._cloud_root_path()
        for idx, image in enumerate(self._idea_images):
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, idx)
            item.setToolTip(image.rel_path)
            if cloud_root is not None:
                pixmap = load_scaled_pixmap(cloud_root / image.rel_path, self.materials_thumbnail_list.iconSize())
                if not pixmap.isNull():
                    item.setIcon(pixmap)
            self.materials_thumbnail_list.addItem(item)
        if self._idea_images:
            self.materials_thumbnail_list.setCurrentRow(self._current_material_index)
        self.materials_thumbnail_list.blockSignals(False)

    def _update_material_view(self) -> None:
        enabled = self._current_idea_id is not None
        self.materials_attach_button.setEnabled(enabled)
        has_images = bool(self._idea_images)
        self.materials_remove_button.setEnabled(has_images)
        self.materials_thumbnail_list.setEnabled(has_images)
        self.materials_caption_input.setEnabled(has_images)
        self.materials_save_caption_button.setEnabled(has_images)
        if not has_images:
            self.materials_hint.setText("Прикрепите изображения из режима Файлы.")
            self.materials_caption_input.setPlainText("")
            return

        self._current_material_index = max(0, min(self._current_material_index, len(self._idea_images) - 1))
        image = self._idea_images[self._current_material_index]
        self.materials_hint.setText(image.rel_path)
        self.materials_caption_input.setPlainText(image.caption)
        self.materials_thumbnail_list.blockSignals(True)
        self.materials_thumbnail_list.setCurrentRow(self._current_material_index)
        self.materials_thumbnail_list.blockSignals(False)

    def _cloud_root_path(self) -> Optional[Path]:
        cloud_root = self._db.get_setting("cloud_storage_path", default="").strip()
        return Path(cloud_root) if cloud_root else None

    def _attach_material_image(self) -> None:
        if self._current_idea_id is None:
            return
        dialog = AttachFileSelectNav(self)
        if exec_with_overlay(dialog, self) != QDialog.DialogCode.Accepted:
            return
        rel_path = dialog.selected_rel_path()
        if not rel_path:
            return
        try:
            self._db.add_idea_image(self._current_idea_id, rel_path)
        except ValueError as exc:
            QMessageBox.warning(self, "Материалы", str(exc))
            return
        self._load_materials(self._current_idea_id)
        for idx, image in enumerate(self._idea_images):
            if image.rel_path == rel_path:
                self._current_material_index = idx
                break
        self._update_material_view()

    def _remove_material_image(self) -> None:
        if not self._idea_images:
            return
        image = self._idea_images[self._current_material_index]
        confirm = QMessageBox.question(
            self,
            "Материалы",
            "Удалить прикреплённое изображение?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self._db.delete_idea_image(image.id)
        self._idea_images.pop(self._current_material_index)
        if self._current_material_index >= len(self._idea_images):
            self._current_material_index = max(0, len(self._idea_images) - 1)
        self._refresh_material_thumbnails()
        self._update_material_view()

    def _save_material_caption(self) -> None:
        if not self._idea_images:
            return
        image = self._idea_images[self._current_material_index]
        try:
            updated = self._db.update_idea_image(image.id, self.materials_caption_input.toPlainText())
        except ValueError as exc:
            QMessageBox.warning(self, "Материалы", str(exc))
            return
        self._idea_images[self._current_material_index] = updated
        self._set_status("Подпись изображения сохранена")

    def _on_material_thumbnail_selected(self, row: int) -> None:
        if row < 0 or row >= len(self._idea_images):
            return
        self._current_material_index = row
        self._update_material_view()

    def _preview_material_image(self) -> None:
        if self._current_idea_id is None or not self._idea_images:
            return
        cloud_root = self._cloud_root_path()
        if cloud_root is None:
            QMessageBox.warning(self, "Материалы", "Путь к облаку не задан.")
            return
        dialog = IdeaImagePreviewDialog(
            self,
            idea_id=self._current_idea_id,
            images=self._idea_images,
            start_index=self._current_material_index,
            cloud_root=cloud_root,
        )
        dialog.exec()

    def _transform_idea(self, kind: str) -> None:
        if self._current_idea_id is None:
            return
        idea = self._db.get_idea(self._current_idea_id)
        if idea is None:
            return
        if kind == "task":
            task = self._db.create_task(
                title=idea.title,
                description=idea.body_md,
                day=date.today(),
                time_text="",
                priority="Medium",
                project_id=idea.project_id,
            )
            self._db.add_idea_relation(idea.id, "task", task.id)
            self._set_status("Создана задача")
        elif kind == "note":
            note = self._db.create_note(
                title=idea.title,
                preview=idea.summary or idea.body_md,
                tags=[],
                project=idea.project_title,
            )
            self._db.add_idea_relation(idea.id, "note", note.id)
            self._set_status("Создана заметка")
        elif kind == "object":
            obj = self._db.create_object(
                title=idea.title,
                catalog="",
                object_type="",
                status="",
                description=idea.body_md,
            )
            self._db.add_idea_relation(idea.id, "object", obj.id)
            self._set_status("Создан объект")
        else:
            self._set_status("Для метки нужно выбрать карту")
            return
        self._db.update_idea(
            idea_id=idea.id,
            title=idea.title,
            summary=idea.summary,
            body_md=idea.body_md,
            idea_type=idea.type,
            status="ripe",
            value_score=idea.value_score,
            effort_score=idea.effort_score,
            project_id=idea.project_id,
            source=idea.source,
        )
        self._load_relations(idea.id)
        self.refresh()

    def _start_inbox_triage(self, *_args: object) -> None:
        if self._dirty and not self._maybe_save_changes():
            return
        self._triage_mode = True
        self.search_input.setText("")
        self.type_filter.setCurrentIndex(0)
        self.archived_only.setChecked(False)
        inbox_index = self.status_filter.findData("inbox")
        if inbox_index >= 0:
            self.status_filter.setCurrentIndex(inbox_index)
        if not self._select_first_inbox_idea():
            self._triage_mode = False
            self._set_status("Инбокс пуст: нет идей со статусом inbox.")
            return
        self.inspector_tabs.setCurrentWidget(self.transform_tab)
        self._set_status(f"Разбор инбокса: {self._inbox_count()} идей в очереди.")

    def _select_first_inbox_idea(self) -> bool:
        model = self.list_view.model()
        if not isinstance(model, IdeasListModel):
            return False
        index = model.first_idea_index("inbox")
        if not index.isValid():
            return False
        self.list_view.setCurrentIndex(index)
        self._open_selected()
        return True

    def _select_next_inbox_idea(self) -> bool:
        if self._current_idea_id is None:
            return self._select_first_inbox_idea()
        model = self.list_view.model()
        if not isinstance(model, IdeasListModel):
            return False
        index = model.next_idea_index(self._current_idea_id, "inbox")
        if not index.isValid():
            return False
        self.list_view.setCurrentIndex(index)
        self._open_selected()
        return True

    def _inbox_count(self) -> int:
        return len(self._db.fetch_ideas(status="inbox"))

    def _advance_inbox_triage(self, status_message: str) -> None:
        self.refresh()
        if self._triage_mode and self._select_first_inbox_idea():
            self.inspector_tabs.setCurrentWidget(self.transform_tab)
            self._set_status(f"{status_message} Осталось inbox: {self._inbox_count()}.")
            return
        self._triage_mode = False
        self._current_idea_id = None
        self._sync_selection()
        self._set_status(f"{status_message} Инбокс разобран.")

    def _triage_current_status(self, status: str) -> None:
        if self._current_idea_id is None:
            return
        if self._dirty:
            self._set_combo_value(self.status_input, status)
            if not self._save_current():
                return
        else:
            idea = self._db.get_idea(self._current_idea_id)
            if idea is None:
                return
            self._db.update_idea(
                idea_id=idea.id,
                title=idea.title,
                summary=idea.summary,
                body_md=idea.body_md,
                idea_type=idea.type,
                status=status,
                value_score=idea.value_score,
                effort_score=idea.effort_score,
                project_id=idea.project_id,
                source=idea.source,
            )
        self._advance_inbox_triage(f"Идея переведена в {self._category_title(status)}.")

    def _triage_archive_current(self) -> None:
        if self._current_idea_id is None:
            return
        if self._dirty and not self._save_current():
            return
        self._db.set_idea_archived(self._current_idea_id, True)
        self._advance_inbox_triage("Идея отправлена в архив.")

    def _triage_transform(self, kind: str) -> None:
        if self._current_idea_id is None:
            return
        if self._dirty and not self._save_current():
            return
        self._transform_idea(kind)
        if kind == "task" and self._triage_mode:
            self._advance_inbox_triage("Из идеи создана задача.")

    def _skip_inbox_idea(self) -> None:
        if self._current_idea_id is None:
            if not self._select_first_inbox_idea():
                self._set_status("Инбокс пуст.")
            return
        if self._select_next_inbox_idea():
            self.inspector_tabs.setCurrentWidget(self.transform_tab)
            self._set_status("Идея пропущена.")
            return
        self._set_status("Это последняя идея в inbox.")

    def _export_ideas_csv(self, *_args: object) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Ideas",
            "ideas_export.csv",
            "CSV (*.csv)",
        )
        if not path:
            return
        rows = export_ideas_rows(self._db.fetch_ideas(archived=True))
        if not rows:
            self._set_status("Нет данных для экспорта")
            return
        try:
            self._csv_service.export_to_file(path, rows, fieldnames=IDEAS_CSV_FIELDS)
        except CsvTransferError as exc:
            QMessageBox.warning(self, "Ideas", f"Export failed: {exc}")
            return
        self._set_status("Экспорт завершен")

    def _import_ideas_csv(self, *_args: object) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Ideas",
            "",
            "CSV (*.csv)",
        )
        if not path:
            return
        try:
            rows = self._csv_service.import_from_file(path)
        except CsvTransferError as exc:
            QMessageBox.warning(self, "Ideas", f"Import failed: {exc}")
            return
        result = import_ideas_rows(self._db, rows)
        self.refresh()
        self._set_status(f"Импорт завершен: {result.imported}, пропущено: {result.skipped}")

__all__ = ["IdeasWorkspace"]
