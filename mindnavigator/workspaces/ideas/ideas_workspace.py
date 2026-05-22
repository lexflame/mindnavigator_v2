"""IdeasWorkspace class module for ideas workspace."""

from __future__ import annotations

from datetime import datetime, timezone

from ._shared import *  # noqa: F401,F403
from PySide6.QtCore import QMimeData, QTimer, Signal
from PySide6.QtGui import QDrag, QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QDialogButtonBox
from .idea_category_edit_dialog import IdeaCategoryEditDialog, IdeaCategoryRenameDialog
from .ideas_list_model import IdeasListModel
from .ideas_delegate import IdeasDelegate
from .idea_image_preview_dialog import IdeaImagePreviewDialog
from .image_utils import load_scaled_pixmap
from mindnavigator.workspaces.concept_board.concept_board_card import CONCEPT_BOARD_KIND_IDEA, ConceptBoardCard
from mindnavigator.workspaces.concept_board.concept_board_delegate import ConceptBoardDelegate
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
IDEA_RELATION_GROUP_ORDER = ("task", "note", "idea", "object", "map", "marker", "concept_board")
IDEA_RELATION_TYPE_ITEMS = [
    ("РћС‚РЅРѕСЃРёС‚СЃСЏ Рє", "related"),
    ("Р Р°Р·РІРёРІР°РµС‚", "develops"),
    ("РџСЂРѕС‚РёРІРѕСЂРµС‡РёС‚", "conflicts"),
    ("РџСЂРµРІСЂР°С‰Р°РµС‚СЃСЏ РІ", "transforms_to"),
    ("РСЃС‚РѕС‡РЅРёРє", "source"),
]
IDEA_RELATION_TYPE_LABELS = {value: label for label, value in IDEA_RELATION_TYPE_ITEMS}
IDEA_OUTPUT_LABELS = {
    "task": "задача",
    "note": "заметка",
    "object": "объект",
    "marker": "метка карты",
    "map": "карта",
    "idea": "идея",
    "concept_board": "концептборд",
}
IDEA_OUTPUT_PRIORITY = ("task", "note", "object", "concept_board", "marker", "map", "idea")
IDEA_DEVELOPMENT_TEMPLATE = (
    "## Почему это важно\n"
    "\n"
    "## Что может дать\n"
    "\n"
    "## Что непонятно\n"
    "\n"
    "## Что проверить\n"
    "\n"
    "## Риски и ограничения\n"
)
_FUNNEL_CARD_ROLE = int(Qt.ItemDataRole.UserRole) + 50
_FUNNEL_IDEA_ACCENT = "#6ad56f"
_FUNNEL_CARD_ROW_HEIGHT = 160


def _idea_source_lines(raw_text: str) -> list[str]:
    normalized = (raw_text or "").replace("\r\n", "\n").replace("\r", "\n")
    result: list[str] = []
    for raw_line in normalized.split("\n"):
        line = " ".join(raw_line.strip().split())
        if line and line not in result:
            result.append(line)
    return result


def _join_idea_sources(lines: list[str]) -> str:
    return "\n".join(_idea_source_lines("\n".join(lines)))


def _dossier_source_label(title: str) -> str:
    normalized_title = " ".join(str(title or "").strip().split())
    return f"Досье: {normalized_title}" if normalized_title else "Досье"


def _build_project_path_map(projects: list[object]) -> dict[int, str]:
    by_id = {int(project.id): project for project in projects if getattr(project, "id", None) is not None}
    cache: dict[int, str] = {}

    def resolve(project_id: int, seen: set[int]) -> str:
        if project_id in cache:
            return cache[project_id]
        project = by_id.get(project_id)
        if project is None:
            return ""
        title = " ".join(str(getattr(project, "title", "") or "").split())
        area = " ".join(str(getattr(project, "area", "") or "").split())
        parent_id = getattr(project, "parent_project_id", None)
        base_title = f"{area} / {title}" if area and title else area or title
        if not base_title:
            cache[project_id] = ""
            return ""
        if parent_id is None or parent_id in seen:
            cache[project_id] = base_title
            return base_title
        parent_title = resolve(int(parent_id), seen | {project_id})
        cache[project_id] = f"{parent_title} / {title}" if parent_title and title else parent_title or base_title
        return cache[project_id]

    for project_id in by_id:
        resolve(project_id, set())
    return cache


class IdeasFunnelList(QListWidget):
    MIME_TYPE = "application/x-mindnavigator-idea-id"

    def __init__(self, status_code: str, workspace: "IdeasWorkspace") -> None:
        super().__init__()
        self._status_code = status_code
        self._workspace = workspace
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)

    def startDrag(self, supported_actions: Qt.DropActions) -> None:
        current_item = self.currentItem()
        if current_item is None:
            return
        idea_id = current_item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(idea_id, int):
            return
        mime_data = QMimeData()
        mime_data.setData(self.MIME_TYPE, str(idea_id).encode("ascii"))
        drag = QDrag(self)
        drag.setMimeData(mime_data)
        drag.exec(supported_actions)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasFormat(self.MIME_TYPE):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:
        if event.mimeData().hasFormat(self.MIME_TYPE):
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event) -> None:
        payload = event.mimeData().data(self.MIME_TYPE)
        try:
            idea_id = int(bytes(payload).decode("ascii"))
        except (TypeError, ValueError):
            event.ignore()
            return
        if self._workspace.move_idea_to_funnel_status(idea_id, self._status_code):
            event.acceptProposedAction()
            return
        event.ignore()


class _IdeaSourcesInput(QWidget):
    textChanged = Signal()
    addDossierRequested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self._editor = QPlainTextEdit(self)
        self._editor.setObjectName("IdeasSourceInput")
        self._editor.setPlaceholderText("Каждый источник с новой строки")
        self._editor.setFixedHeight(88)
        self._editor.textChanged.connect(self.textChanged.emit)
        layout.addWidget(self._editor)

        actions = QHBoxLayout()
        actions.setContentsMargins(0, 0, 0, 0)
        actions.setSpacing(6)
        self.add_dossier_button = QToolButton(self)
        self.add_dossier_button.setObjectName("IdeasSourceAddDossier")
        self.add_dossier_button.setText("Добавить досье")
        self.add_dossier_button.clicked.connect(self.addDossierRequested.emit)
        actions.addWidget(self.add_dossier_button)
        actions.addStretch(1)
        layout.addLayout(actions)

    def text(self) -> str:
        return self._editor.toPlainText()

    def setText(self, text: str) -> None:
        self._editor.setPlainText(text or "")

    def placeholderText(self) -> str:
        return self._editor.placeholderText()

    def setPlaceholderText(self, text: str) -> None:
        self._editor.setPlaceholderText(text)

    def append_source(self, source_text: str) -> None:
        lines = _idea_source_lines(self.text())
        source = " ".join(str(source_text or "").strip().split())
        if not source or source in lines:
            return
        lines.append(source)
        self.setText(_join_idea_sources(lines))


class _IdeaDossierSourceDialog(QDialog):
    def __init__(self, db, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._db = db
        self.setObjectName("IdeaDossierSourceDialog")
        self.setWindowTitle("Выбрать досье")
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self.search_edit = QLineEdit(self)
        self.search_edit.setPlaceholderText("Поиск по досье")
        self.dossier_combo = QComboBox(self)
        form.addRow("Поиск", self.search_edit)
        form.addRow("Досье", self.dossier_combo)
        layout.addLayout(form)

        buttons = QDialogButtonBox(self)
        self._ok_button = buttons.addButton(QDialogButtonBox.StandardButton.Ok)
        buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.search_edit.textChanged.connect(self._fill_dossiers)
        self._fill_dossiers()

    def _fill_dossiers(self) -> None:
        self.dossier_combo.clear()
        dossiers = self._db.fetch_dossiers(search_text=self.search_edit.text())
        if not dossiers:
            self.dossier_combo.addItem("— нет доступных —", None)
            self._ok_button.setEnabled(False)
            return
        for dossier in dossiers:
            label = f"{dossier.title} · {dossier.kind}" if dossier.kind else dossier.title
            self.dossier_combo.addItem(label, dossier.id)
        self._ok_button.setEnabled(True)

    def selected_source_text(self) -> str:
        dossier_id = self.dossier_combo.currentData()
        if not isinstance(dossier_id, int):
            return ""
        dossier = self._db.get_dossier(dossier_id)
        if dossier is None:
            return ""
        return _dossier_source_label(dossier.title)


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

        self.relation_type_combo = QComboBox()
        for label, value in IDEA_RELATION_TYPE_ITEMS:
            self.relation_type_combo.addItem(label, value)

        self.target_combo = QComboBox()
        self.kind_combo.currentIndexChanged.connect(self._fill_targets)

        form.addRow("Тип", self.kind_combo)
        form.addRow("Элемент", self.target_combo)
        form.insertRow(1, "РЎРјС‹СЃР»", self.relation_type_combo)
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
            "relation_kind": self.relation_type_combo.currentData(),
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
        self._triage_total = 0
        self._triage_position = 0
        self._theme_mode = "dark"
        self._idea_categories = []
        self._idea_categories_by_code: Dict[str, Any] = {}
        self._idea_images: List[IdeaImageData] = []
        self._current_material_index = 0
        self._status_message = ""
        self._stats_text = ""
        self._visible_idea_items: List[IdeaItem] = []
        super().__init__(parent)
        triage_action = self.actions.get("triage")
        if triage_action is not None:
            try:
                triage_action.triggered.disconnect()
            except (TypeError, RuntimeError):
                pass
            triage_action.triggered.connect(self._start_inbox_triage)
        self.setObjectName("IdeasWorkspace")
        self.search_input.setPlaceholderText("Поиск по идеям, краткому описанию, тексту, источнику...")
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

        view_mode_row = QWidget()
        view_mode_layout = QHBoxLayout(view_mode_row)
        view_mode_layout.setContentsMargins(0, 0, 0, 0)
        view_mode_layout.setSpacing(6)
        self.view_mode_label = QLabel("Режим")
        self.view_mode_combo = QComboBox()
        self.view_mode_combo.addItem("Список", "list")
        self.view_mode_combo.addItem("Воронка", "funnel")
        self.view_mode_combo.addItem("Матрица", "matrix")
        self.view_mode_combo.addItem("Связи", "links")
        self.view_mode_combo.currentIndexChanged.connect(self._on_view_mode_changed)
        view_mode_layout.addWidget(self.view_mode_label)
        view_mode_layout.addWidget(self.view_mode_combo)
        view_mode_layout.addStretch(1)
        list_layout.addWidget(view_mode_row)

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
        self.funnel_view = QWidget()
        self.funnel_view.setObjectName("IdeasFunnelView")
        funnel_layout = QHBoxLayout(self.funnel_view)
        funnel_layout.setContentsMargins(0, 0, 0, 0)
        funnel_layout.setSpacing(8)
        self.funnel_lists: Dict[str, IdeasFunnelList] = {}
        self.funnel_headers: Dict[str, QLabel] = {}
        for status_code, title in (
            ("inbox", "Входящие"),
            ("work", "В работе"),
            ("ripe", "Созрели"),
            ("archived", "Архив"),
        ):
            column_host = QWidget()
            column_host.setObjectName("IdeasFunnelColumn")
            column_layout = QVBoxLayout(column_host)
            column_layout.setContentsMargins(8, 8, 8, 8)
            column_layout.setSpacing(6)
            heading = QLabel(title)
            heading.setObjectName("IdeasFunnelHeading")
            column_layout.addWidget(heading)
            column_list = IdeasFunnelList(status_code, self)
            column_list.setObjectName(f"IdeasFunnelList_{status_code}")
            column_list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
            column_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            column_list.setUniformItemSizes(False)
            column_list.setSpacing(6)
            column_list.setItemDelegate(
                ConceptBoardDelegate(
                    column_list,
                    data_role=_FUNNEL_CARD_ROLE,
                    row_height=_FUNNEL_CARD_ROW_HEIGHT,
                    stack_footer=True,
                )
            )
            column_list.itemActivated.connect(self._on_alt_view_item_activated)
            column_list.itemClicked.connect(self._on_alt_view_item_activated)
            column_layout.addWidget(column_list, 1)
            funnel_layout.addWidget(column_host, 1)
            self.funnel_lists[status_code] = column_list
            self.funnel_headers[status_code] = heading
        self.matrix_view = QWidget()
        self.matrix_view.setObjectName("IdeasMatrixView")
        matrix_root = QVBoxLayout(self.matrix_view)
        matrix_root.setContentsMargins(0, 0, 0, 0)
        matrix_root.setSpacing(8)
        self.matrix_lists: Dict[str, QListWidget] = {}
        self.matrix_headers: Dict[str, QLabel] = {}
        for row_titles in (
            ("РЎРґРµР»Р°С‚СЊ РїРµСЂРІС‹Рј", "Р—Р°РїР»Р°РЅРёСЂРѕРІР°С‚СЊ"),
            ("Р‘С‹СЃС‚СЂРѕ Р·Р°РєСЂС‹С‚СЊ", "Р’ Р°СЂС…РёРІ / РїРѕР·Р¶Рµ"),
        ):
            row_layout = QHBoxLayout()
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(8)
            for title in row_titles:
                quadrant_host = QWidget()
                quadrant_host.setObjectName("IdeasMatrixQuadrant")
                quadrant_layout = QVBoxLayout(quadrant_host)
                quadrant_layout.setContentsMargins(8, 8, 8, 8)
                quadrant_layout.setSpacing(6)
                heading = QLabel(title)
                heading.setObjectName("IdeasMatrixHeading")
                quadrant_layout.addWidget(heading)
                quadrant_list = QListWidget()
                quadrant_list.setObjectName("IdeasMatrixList")
                quadrant_list.itemActivated.connect(self._on_alt_view_item_activated)
                quadrant_list.itemClicked.connect(self._on_alt_view_item_activated)
                quadrant_layout.addWidget(quadrant_list, 1)
                row_layout.addWidget(quadrant_host, 1)
                self.matrix_lists[title] = quadrant_list
                self.matrix_headers[title] = heading
            matrix_root.addLayout(row_layout, 1)
        matrix_list_values = list(self.matrix_lists.values())
        matrix_header_values = list(self.matrix_headers.values())
        if len(matrix_list_values) == 4 and len(matrix_header_values) == 4:
            self.matrix_lists = {
                "first": matrix_list_values[0],
                "planned": matrix_list_values[1],
                "quick": matrix_list_values[2],
                "later": matrix_list_values[3],
            }
            self.matrix_headers = {
                "first": matrix_header_values[0],
                "planned": matrix_header_values[1],
                "quick": matrix_header_values[2],
                "later": matrix_header_values[3],
            }
        self.links_view = QTreeWidget()
        self.links_view.setObjectName("IdeasLinksView")
        self.links_view.setHeaderHidden(True)
        self.links_view.itemActivated.connect(lambda item, _column: self._on_alt_view_item_activated(item))
        self.links_view.itemClicked.connect(lambda item, _column: self._on_alt_view_item_activated(item))
        self.list_mode_stack = QStackedWidget()
        self.list_mode_stack.setObjectName("IdeasListModeStack")
        self.list_mode_stack.addWidget(self.list_view)
        self.list_mode_stack.addWidget(self.funnel_view)
        self.list_mode_stack.addWidget(self.matrix_view)
        self.list_mode_stack.addWidget(self.links_view)

        list_layout.addWidget(self.list_mode_stack, 1)
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
        self.title_input.setPlaceholderText("Название идеи")
        self.summary_input = QLineEdit()
        self.summary_input.setPlaceholderText("Краткая формулировка идеи...")
        self.body_input = QPlainTextEdit()
        self.body_input.setPlaceholderText("Разверните идею, контекст и детали...")
        self.project_input = QComboBox()
        self._populate_projects()
        self.type_input = QComboBox()
        for label, value in IDEA_TYPES[1:]:
            self.type_input.addItem(label, value)
        self.status_input = QComboBox()
        self._reload_idea_categories()
        self.source_input = _IdeaSourcesInput()

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
        content_layout.addRow("Источники", self.source_input)
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

        self.content_tab_index = self.inspector_tabs.addTab(content_tab, "Суть")

        development_tab = QWidget()
        development_tab.setObjectName("IdeasDevelopmentTab")
        development_layout = QVBoxLayout(development_tab)
        development_layout.setContentsMargins(12, 12, 12, 12)
        development_layout.setSpacing(8)
        self.development_hint = QLabel(
            "Развитие помогает превратить сырую мысль в проверяемую идею. "
            "Шаблон записывается в поле «Описание» на вкладке «Суть»."
        )
        self.development_hint.setObjectName("IdeasDevelopmentHint")
        self.development_hint.setWordWrap(True)
        self.development_insert_button = QToolButton()
        self.development_insert_button.setText("Вставить шаблон развития")
        self.development_insert_button.setObjectName("IdeasDevelopmentInsert")
        self.development_insert_button.clicked.connect(self._insert_development_template)
        self.development_preview = QPlainTextEdit()
        self.development_preview.setObjectName("IdeasDevelopmentPreview")
        self.development_preview.setReadOnly(True)
        self.development_preview.setPlaceholderText("Описание идеи появится здесь.")
        self.development_preview.setMinimumHeight(220)
        development_layout.addWidget(self.development_hint)
        development_layout.addWidget(self.development_insert_button, 0, Qt.AlignmentFlag.AlignLeft)
        development_layout.addWidget(self.development_preview, 1)
        self.development_tab_index = self.inspector_tabs.addTab(development_tab, "Развитие")

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
        self.relations_open_button = QToolButton()
        self.relations_open_button.setText("РћС‚РєСЂС‹С‚СЊ СЃРІСЏР·СЊ")
        self.relations_open_button.setObjectName("IdeasRelationsOpen")
        self.relations_open_button.clicked.connect(self._open_selected_relation)
        relations_actions.addWidget(self.relations_add_button)
        relations_actions.addWidget(self.relations_open_button)
        relations_actions.addWidget(self.relations_remove_button)
        relations_actions.addStretch(1)
        relations_layout.addLayout(relations_actions)
        self.relations_list = QListWidget()
        self.relations_list.currentRowChanged.connect(lambda _row: self._update_relations_actions())
        self.relations_list.itemDoubleClicked.connect(lambda _item: self._open_selected_relation())
        relations_layout.addWidget(self.relations_list, 1)
        self.relations_tab_index = self.inspector_tabs.addTab(relations_tab, "Связи")

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

        self.materials_hint = QLabel(
            "Материалов пока нет.\nДобавьте изображение или референс, чтобы связать идею с визуальным контекстом."
        )
        self.materials_hint.setObjectName("IdeasMaterialsHint")
        self.materials_hint.setWordWrap(True)

        self.materials_thumbnail_list = QListWidget()
        self.materials_thumbnail_list.setObjectName("IdeasMaterialsThumbnails")
        self.materials_thumbnail_list.setViewMode(QListView.ViewMode.IconMode)
        self.materials_thumbnail_list.setFlow(QListView.Flow.LeftToRight)
        self.materials_thumbnail_list.setResizeMode(QListView.ResizeMode.Adjust)
        self.materials_thumbnail_list.setMovement(QListView.Movement.Static)
        self.materials_thumbnail_list.setIconSize(QSize(88, 88))
        self.materials_thumbnail_list.setGridSize(QSize(116, 122))
        self.materials_thumbnail_list.setFixedHeight(138)
        self.materials_thumbnail_list.setSpacing(8)
        self.materials_thumbnail_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.materials_thumbnail_list.setToolTip("Двойной щелчок открывает изображение в полном размере.")
        self.materials_thumbnail_list.currentRowChanged.connect(self._on_material_thumbnail_selected)
        self.materials_thumbnail_list.itemDoubleClicked.connect(lambda _item: self._preview_material_image())

        self.materials_caption_input = QPlainTextEdit()
        self.materials_caption_input.setObjectName("IdeasMaterialsCaption")
        self.materials_caption_input.setPlaceholderText("Подпись и контекст материала...")

        self.materials_save_caption_button = QToolButton()
        self.materials_save_caption_button.setText("Сохранить подпись")
        self.materials_save_caption_button.setObjectName("IdeasMaterialsCaptionSave")
        self.materials_save_caption_button.clicked.connect(self._save_material_caption)

        materials_layout.addLayout(materials_actions)
        materials_layout.addWidget(self.materials_hint)
        materials_layout.addWidget(self.materials_thumbnail_list)
        materials_layout.addWidget(self.materials_caption_input)
        materials_layout.addWidget(self.materials_save_caption_button, 0, Qt.AlignmentFlag.AlignRight)
        self.materials_tab_index = self.inspector_tabs.addTab(materials_tab, "Материалы и референсы")

        transform_tab = QWidget()
        transform_tab.setObjectName("IdeasTransformTab")
        self.transform_tab = transform_tab
        transform_layout = QVBoxLayout(transform_tab)
        transform_layout.setContentsMargins(12, 12, 12, 12)
        transform_layout.setSpacing(8)
        self.triage_progress_label = QLabel("Выход идеи")
        self.triage_progress_label.setObjectName("IdeasTriageProgress")
        transform_layout.addWidget(self.triage_progress_label)
        self.triage_hint = QLabel(
            "Идея должна либо созреть, либо стать действием, либо уйти в архив."
        )
        self.triage_hint.setObjectName("IdeasTriageHint")
        self.triage_hint.setWordWrap(True)
        transform_layout.addWidget(self.triage_hint)
        self.output_summary_label = QLabel("Выход: нет")
        self.output_summary_label.setObjectName("IdeasOutputSummary")
        self.output_summary_label.setWordWrap(True)
        transform_layout.addWidget(self.output_summary_label)
        transform_layout.addWidget(QLabel("Разобрать идею"))
        triage_row = QHBoxLayout()
        triage_row.setSpacing(6)
        self.triage_skip_btn = QToolButton()
        self.triage_skip_btn.setText("Пропустить")
        self.triage_skip_btn.setObjectName("IdeasTriageSkip")
        self.triage_skip_btn.clicked.connect(self._skip_inbox_idea)
        self.triage_work_btn = QToolButton()
        self.triage_work_btn.setText("В работу")
        self.triage_work_btn.setObjectName("IdeasTriageWork")
        self.triage_work_btn.clicked.connect(lambda: self._triage_current_status("work"))
        self.triage_ripe_btn = QToolButton()
        self.triage_ripe_btn.setText("Созрела")
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
        transform_layout.addWidget(QLabel("Преобразовать в"))
        self.transform_task_btn = QToolButton()
        self.transform_task_btn.setText("Создать задачу")
        self.transform_task_btn.setObjectName("IdeasTransformTask")
        self.transform_task_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.transform_task_btn.clicked.connect(lambda: self._triage_transform("task"))
        self.transform_note_btn = QToolButton()
        self.transform_note_btn.setText("Создать заметку")
        self.transform_note_btn.setObjectName("IdeasTransformNote")
        self.transform_note_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.transform_note_btn.clicked.connect(lambda: self._triage_transform("note"))
        self.transform_object_btn = QToolButton()
        self.transform_object_btn.setText("Создать объект")
        self.transform_object_btn.setObjectName("IdeasTransformObject")
        self.transform_object_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.transform_object_btn.clicked.connect(lambda: self._triage_transform("object"))
        self.transform_marker_btn = QToolButton()
        self.transform_marker_btn.setText("Создать метку карты")
        self.transform_marker_btn.setObjectName("IdeasTransformMarker")
        self.transform_marker_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.transform_marker_btn.clicked.connect(lambda: self._triage_transform("marker"))
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
        self.transform_concept_board_btn = QToolButton()
        self.transform_concept_board_btn.setText("Добавить в концептборд")
        self.transform_concept_board_btn.setObjectName("IdeasTransformConceptBoard")
        self.transform_concept_board_btn.clicked.connect(self._attach_current_idea_to_concept_board)
        transform_layout.addWidget(self.transform_concept_board_btn, 0, Qt.AlignmentFlag.AlignLeft)
        transform_layout.addStretch(1)
        self.output_tab_index = self.inspector_tabs.addTab(transform_tab, "Выход")

        self.inspector_stack.addWidget(self.inspector_tabs)
        splitter.addWidget(self.inspector_stack)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 4)

        self.set_content(splitter)

        self.title_input.textChanged.connect(self._mark_dirty)
        self.summary_input.textChanged.connect(self._mark_dirty)
        self.body_input.textChanged.connect(self._mark_dirty)
        self.body_input.textChanged.connect(self._sync_development_preview)
        self.project_input.currentIndexChanged.connect(self._on_project_changed)
        self.type_input.currentIndexChanged.connect(self._mark_dirty)
        self.status_input.currentIndexChanged.connect(self._mark_dirty)
        self.source_input.textChanged.connect(self._mark_dirty)
        self.source_input.addDossierRequested.connect(self._add_dossier_source)
        self.value_input.valueChanged.connect(self._mark_dirty)
        self.effort_input.valueChanged.connect(self._mark_dirty)
        self.quick_create_btn.clicked.connect(self._create_idea_from_quick_form)
        self.quick_status_btn.clicked.connect(self._open_quick_status_menu)
        self.quick_title_input.returnPressed.connect(self._create_idea_from_quick_form)
        self._set_quick_status(None)
        self._update_material_view()
        self._init_triage_shortcuts()

        self.set_theme_mode("dark")
        QTimer.singleShot(0, self._sync_transform_action_widths)

    def _init_triage_shortcuts(self) -> None:
        self._triage_shortcuts: list[QShortcut] = []
        bindings = [
            ("W", lambda: self._triage_current_status("work")),
            ("R", lambda: self._triage_current_status("ripe")),
            ("A", self._triage_archive_current),
            ("T", lambda: self._triage_transform("task")),
            ("N", lambda: self._triage_transform("note")),
            ("O", lambda: self._triage_transform("object")),
            ("Space", self._skip_inbox_idea),
            ("Escape", self._exit_triage_mode),
        ]
        for sequence, callback in bindings:
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            shortcut.activated.connect(lambda cb=callback: self._run_triage_shortcut(cb))
            self._triage_shortcuts.append(shortcut)

    def _run_triage_shortcut(self, callback) -> None:
        if not self._should_handle_triage_shortcut():
            return
        callback()

    def _should_handle_triage_shortcut(self) -> bool:
        if not self._triage_mode:
            return False
        focus_widget = QApplication.focusWidget()
        if focus_widget is None:
            return True
        if isinstance(focus_widget, (QLineEdit, QPlainTextEdit, QComboBox, QSpinBox)):
            return False
        return self.isAncestorOf(focus_widget) or focus_widget is self

    def _exit_triage_mode(self) -> None:
        if not self._triage_mode:
            return
        self._triage_mode = False
        self._triage_total = 0
        self._triage_position = 0
        self._update_triage_panel()
        self._set_status("Режим разбора inbox завершён.")

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

            QLabel#IdeasWorkspaceHeading {{
                color: {palette.text};
                font-size: 15px;
                font-weight: 600;
            }}

            QLabel#IdeasTriageProgress,
            QLabel#IdeasOutputSummary {{
                color: {palette.chart_muted};
                font-weight: 600;
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
            QWidget#IdeasDevelopmentTab,
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

            QWidget#IdeasWorkspace QWidget#IdeasFunnelColumn {{
                background: {palette.panel_alt_bg};
                border: 1px solid {palette.border};
                border-radius: 10px;
            }}

            QWidget#IdeasWorkspace QWidget#IdeasMatrixQuadrant {{
                background: {palette.panel_alt_bg};
                border: 1px solid {palette.border};
                border-radius: 10px;
            }}

            QWidget#IdeasWorkspace QLabel#IdeasFunnelHeading {{
                color: {palette.text};
                font-size: 12px;
                font-weight: 600;
            }}

            QWidget#IdeasWorkspace QLabel#IdeasMatrixHeading {{
                color: {palette.text};
                font-size: 12px;
                font-weight: 600;
            }}

            QLabel#IdeasEmpty {{
                color: {palette.dim_text};
            }}
        """
        )

    def create_actions(self) -> dict[str, QAction]:
        action_new = QAction("+ Идея", self)
        action_new.triggered.connect(self._create_default_idea)
        action_triage = QAction("Разобрать inbox", self)
        action_triage.triggered.connect(lambda: self._set_status("Разбор инбокса пока не реализован"))
        action_export = QAction("Экспорт", self)
        action_export.triggered.connect(self._export_ideas_csv)
        action_import = QAction("Импорт", self)
        action_import.triggered.connect(self._import_ideas_csv)
        action_archive = QAction("В архив", self)
        action_archive.triggered.connect(self._archive_selected)
        return {
            "new": action_new,
            "triage": action_triage,
            "export": action_export,
            "import": action_import,
            "archive": action_archive,
        }

    def build_toolbar(self, actions: dict[str, QAction]) -> None:
        while self.toolbar_layout.count():
            item = self.toolbar_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        heading = QLabel("Идеи · Инкубатор решений")
        heading.setObjectName("IdeasWorkspaceHeading")
        self.toolbar_layout.addWidget(heading)
        self.toolbar_layout.addSpacing(12)

        ordered_keys = ("new", "triage", "export", "import", "archive")
        for key in ordered_keys:
            action = actions.get(key)
            if action is None:
                continue
            button = QToolButton()
            button.setDefaultAction(action)
            if key == "archive":
                button.setObjectName("IdeasArchiveAction")
            self.toolbar_layout.addWidget(button)
            if key in {"triage", "import"}:
                self.toolbar_layout.addSpacing(6)
        self.toolbar_layout.addStretch(1)

    def get_selection(self):
        index = self.list_view.currentIndex()
        if not index.isValid() or index.data(IdeaRoles.RowType) != "idea":
            return None
        return index.data(IdeaRoles.IdeaId)

    def update_action_states(self) -> None:
        super().update_action_states()
        archive_action = self.actions.get("archive")
        if archive_action is None:
            return
        idea_id = self.get_selection()
        idea = self._db.get_idea(idea_id) if idea_id is not None else None
        archive_action.setEnabled(idea is not None and not self._busy)
        archive_action.setText("Восстановить" if idea is not None and idea.archived_at is not None else "В архив")

    def _set_status(self, text: str) -> None:
        self._status_message = text.strip()
        self._refresh_status_bar()

    def _refresh_status_bar(self) -> None:
        self._stats_text = self._compose_stats_text()
        parts = [part for part in [self._status_message, self._stats_text] if part]
        self.status_row.setText(" | ".join(parts))

    def _compose_stats_text(self) -> str:
        active_ideas = self._db.fetch_ideas(archived=False)
        archived_ideas = self._db.fetch_ideas(archived=True)
        inbox = sum(1 for idea in active_ideas if (idea.status or "").strip().lower() == "inbox")
        work = sum(1 for idea in active_ideas if (idea.status or "").strip().lower() == "work")
        ripe = sum(1 for idea in active_ideas if (idea.status or "").strip().lower() == "ripe")
        total = len(active_ideas) + len(archived_ideas)
        return (
            f"Идей: {total}"
            f" | Входящие: {inbox}"
            f" | В работе: {work}"
            f" | Созрели: {ripe}"
            f" | Архив: {len(archived_ideas)}"
        )

    def _update_empty_state(self, items: List[IdeaItem]) -> None:
        if items:
            self.inspector_empty.setText("Выберите идею слева")
            return
        filters = self.get_filters()
        if self._query:
            self.inspector_empty.setText("Ничего не найдено\nПопробуйте изменить запрос или сбросить фильтры.")
            return
        if filters.get("status") == "inbox":
            self.inspector_empty.setText("Inbox пуст\nВсе входящие идеи разобраны.")
            return
        self.inspector_empty.setText("Идей пока нет\nСоздайте первую идею или импортируйте CSV.")

    @staticmethod
    def _format_relative_time(value: datetime) -> str:
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            value = value.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        delta = max(0, int((now - value).total_seconds()))
        if delta < 60:
            return "только что"
        if delta < 3600:
            return f"{delta // 60} мин назад"
        if delta < 86400:
            return f"{delta // 3600} ч назад"
        return f"{delta // 86400} д назад"

    def _idea_output_label(self, idea, relations: List[object]) -> str:
        relation_types = {
            (relation.entity_type or "").strip().lower()
            for relation in relations
            if (getattr(relation, "relation_kind", "related") or "related").strip().lower() == "transforms_to"
        }
        if not relation_types:
            relation_types = {(relation.entity_type or "").strip().lower() for relation in relations}
        for entity_type in IDEA_OUTPUT_PRIORITY:
            if entity_type in relation_types:
                return IDEA_OUTPUT_LABELS[entity_type]
        if idea.archived_at is not None:
            return "архив"
        return "нет"

    @staticmethod
    def _relation_kind_title(relation_kind: Optional[str]) -> str:
        normalized = (relation_kind or "related").strip().lower() or "related"
        return IDEA_RELATION_TYPE_LABELS.get(normalized, IDEA_RELATION_TYPE_LABELS["related"])

    def _set_counted_tab_title(self, tab_index: int, title: str, count: Optional[int] = None) -> None:
        if count is None:
            self.inspector_tabs.setTabText(tab_index, title)
            return
        self.inspector_tabs.setTabText(tab_index, f"{title} ({count})")

    @staticmethod
    def _quadrant_label(item: IdeaItem) -> str:
        if item.value_score >= 4 and item.effort_score <= 2:
            return "Сделать первым"
        if item.value_score >= 4:
            return "Запланировать"
        if item.effort_score <= 2:
            return "Быстро закрыть"
        return "В архив / позже"

    @staticmethod
    def _quadrant_key(item: IdeaItem) -> str:
        if item.value_score >= 4 and item.effort_score <= 2:
            return "first"
        if item.value_score >= 4:
            return "planned"
        if item.effort_score <= 2:
            return "quick"
        return "later"

    @staticmethod
    def _funnel_bucket(item: IdeaItem) -> str:
        if item.archived:
            return "archived"
        status = (item.status or "").strip().lower()
        if status in {"inbox", "work", "ripe"}:
            return status
        if status == "done":
            return "ripe"
        return "inbox"

    def _add_alt_view_header(self, widget: QListWidget, text: str) -> None:
        item = QListWidgetItem(text)
        item.setFlags(Qt.ItemFlag.NoItemFlags)
        widget.addItem(item)

    def _add_alt_view_idea(self, widget: QListWidget, item: IdeaItem, *, prefix: str = "") -> None:
        line = (
            f"{prefix}{item.title} · {self._category_title(item.status)}"
            f" · Value {item.value_score} / Effort {item.effort_score}"
            f" · Выход: {item.output_label}"
        )
        row = QListWidgetItem(line)
        row.setData(Qt.ItemDataRole.UserRole, item.id)
        widget.addItem(row)

    @staticmethod
    def _relation_group_title(entity_type: str) -> str:
        if entity_type == "concept_board":
            return "РљРѕРЅС†РµРїС‚Р±РѕСЂРґС‹"
        return IDEA_RELATION_KIND_LABELS.get(entity_type, entity_type.capitalize())

    @staticmethod
    def _relation_payload(item: Optional[QListWidgetItem]) -> Optional[tuple[int, str, int]]:
        if item is None:
            return None
        relation_id = item.data(Qt.ItemDataRole.UserRole)
        entity_type = item.data(int(Qt.ItemDataRole.UserRole) + 1)
        entity_id = item.data(int(Qt.ItemDataRole.UserRole) + 2)
        if isinstance(relation_id, int) and isinstance(entity_type, str) and isinstance(entity_id, int):
            return relation_id, entity_type, entity_id
        return None

    def _funnel_card_for_idea(self, item: IdeaItem) -> ConceptBoardCard:
        preview = idea_preview_line(item.summary, item.body_md)
        meta_parts = [
            item.project_title,
            STATUS_LABELS.get((item.status or "").strip().lower(), item.status),
            TYPE_LABELS.get((item.idea_type or "").strip().lower(), item.idea_type),
        ]
        return ConceptBoardCard(
            entity_kind=CONCEPT_BOARD_KIND_IDEA,
            entity_id=item.id,
            title=item.title,
            subtitle=preview,
            project_id=item.project_id,
            project_title=item.project_title,
            accent_color=_FUNNEL_IDEA_ACCENT,
            meta_text=" · ".join(str(part).strip() for part in meta_parts if str(part or "").strip()),
            relation_count=max(0, int(item.relations_count)),
            relation_summary=f"Связи · {max(0, int(item.relations_count))}",
            source_payload=item,
        )

    def _populate_funnel_view(self) -> None:
        self.funnel_view.clear()
        order = [
            ("inbox", "Входящие"),
            ("work", "В работе"),
            ("ripe", "Созрели"),
            ("archived", "Архив"),
        ]
        grouped: Dict[str, List[IdeaItem]] = {key: [] for key, _label in order}
        for item in self._visible_idea_items:
            status = (item.status or "").strip().lower()
            grouped["archived" if item.archived else status].append(item)
        for key, label in order:
            bucket = grouped.get(key, [])
            self._add_alt_view_header(self.funnel_view, f"{label} · {len(bucket)}")
            if not bucket:
                self._add_alt_view_header(self.funnel_view, "  Нет идей")
                continue
            for item in bucket:
                self._add_alt_view_idea(self.funnel_view, item, prefix="  ")

    def _populate_funnel_view(self) -> None:
        grouped: Dict[str, List[IdeaItem]] = {key: [] for key in self.funnel_lists}
        for item in self._visible_idea_items:
            grouped[self._funnel_bucket(item)].append(item)
        for key, widget in self.funnel_lists.items():
            widget.clear()
            bucket = grouped.get(key, [])
            heading = self.funnel_headers.get(key)
            if heading is not None:
                base_title = heading.text().split(" · ", 1)[0]
                heading.setText(f"{base_title} · {len(bucket)}")
            if not bucket:
                empty_row = QListWidgetItem("Нет идей")
                empty_row.setFlags(Qt.ItemFlag.NoItemFlags)
                widget.addItem(empty_row)
                continue
            bucket.sort(key=lambda idea: idea.id, reverse=True)
            for item in bucket:
                preview = idea_preview_line(item.summary, item.body_md)
                row = QListWidgetItem(
                    f"{item.title}\n{preview}\nValue {item.value_score} / Effort {item.effort_score} · Выход: {item.output_label}"
                )
                row.setData(Qt.ItemDataRole.UserRole, item.id)
                row.setData(_FUNNEL_CARD_ROLE, self._funnel_card_for_idea(item))
                row.setToolTip(f"{item.title}\n{preview}")
                widget.addItem(row)

    def move_idea_to_funnel_status(self, idea_id: int, status_code: str) -> bool:
        target_status = (status_code or "").strip().lower()
        if target_status not in {"inbox", "work", "ripe", "archived"}:
            return False
        if self._dirty and self._current_idea_id == idea_id and not self._maybe_save_changes():
            return False
        idea = self._db.get_idea(idea_id)
        if idea is None:
            return False
        was_archived = idea.archived_at is not None
        current_bucket = "archived" if was_archived else self._funnel_bucket(
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
                archived=was_archived,
                source=idea.source,
            )
        )
        if current_bucket == target_status:
            return True
        if target_status == "archived":
            self._db.set_idea_archived(idea_id, True)
        else:
            if was_archived:
                self._db.set_idea_archived(idea_id, False)
            if (idea.status or "").strip().lower() != target_status:
                self._db.update_idea(
                    idea_id=idea.id,
                    title=idea.title,
                    summary=idea.summary,
                    body_md=idea.body_md,
                    idea_type=idea.type,
                    status=target_status,
                    value_score=idea.value_score,
                    effort_score=idea.effort_score,
                    project_id=idea.project_id,
                    source=idea.source,
                )
        self._current_idea_id = idea_id
        self.refresh()
        self.select_idea(idea_id)
        self._set_status(f"Идея перемещена в {self._category_title(target_status)}.")
        return True

    def _populate_matrix_view(self) -> None:
        self.matrix_view.clear()
        groups: Dict[str, List[IdeaItem]] = {
            "Сделать первым": [],
            "Запланировать": [],
            "Быстро закрыть": [],
            "В архив / позже": [],
        }
        for item in self._visible_idea_items:
            groups[self._quadrant_label(item)].append(item)
        for label, bucket in groups.items():
            self._add_alt_view_header(self.matrix_view, f"{label} · {len(bucket)}")
            if not bucket:
                self._add_alt_view_header(self.matrix_view, "  Нет идей")
                continue
            bucket.sort(key=lambda idea: (-idea.value_score, idea.effort_score, idea.title.casefold(), idea.id))
            for item in bucket:
                self._add_alt_view_idea(self.matrix_view, item, prefix="  ")

    def _populate_matrix_view(self) -> None:
        groups: Dict[str, List[IdeaItem]] = {key: [] for key in self.matrix_lists}
        for item in self._visible_idea_items:
            groups[self._quadrant_key(item)].append(item)
        for label, widget in self.matrix_lists.items():
            widget.clear()
            bucket = groups.get(label, [])
            heading = self.matrix_headers.get(label)
            if heading is not None:
                base_title = heading.text().split(" · ", 1)[0]
                heading.setText(f"{base_title} · {len(bucket)}")
            if not bucket:
                empty_row = QListWidgetItem("Нет идей")
                empty_row.setFlags(Qt.ItemFlag.NoItemFlags)
                widget.addItem(empty_row)
                continue
            bucket.sort(key=lambda idea: (-idea.value_score, idea.effort_score, idea.title.casefold(), idea.id))
            for item in bucket:
                row = QListWidgetItem(
                    f"{item.title}\n{idea_preview_line(item.summary, item.body_md)}\nВыход: {item.output_label}"
                )
                row.setData(Qt.ItemDataRole.UserRole, item.id)
                row.setToolTip(item.title)
                widget.addItem(row)

    def _populate_links_view(self) -> None:
        self.links_view.clear()
        if self._current_idea_id is None:
            self._add_alt_view_header(self.links_view, "Выберите идею, чтобы увидеть её связи.")
            return
        idea = next((item for item in self._visible_idea_items if item.id == self._current_idea_id), None)
        if idea is None:
            current = self._db.get_idea(self._current_idea_id)
            if current is not None:
                self._add_alt_view_header(self.links_view, f"{current.title}")
            else:
                self._add_alt_view_header(self.links_view, "Связи недоступны.")
                return
        else:
            self._add_alt_view_header(self.links_view, f"{idea.title}")
        relations = self._db.fetch_idea_relations(self._current_idea_id)
        if not relations:
            self._add_alt_view_header(self.links_view, "Связей пока нет")
            self._add_alt_view_header(
                self.links_view,
                "Свяжите идею с задачей, заметкой, объектом или картой, чтобы она стала частью рабочего контекста.",
            )
            return
        grouped: Dict[str, List[object]] = {}
        for relation in relations:
            grouped.setdefault(relation.entity_type, []).append(relation)
        for entity_type in sorted(grouped.keys()):
            title = IDEA_RELATION_KIND_LABELS.get(entity_type, entity_type.capitalize())
            self._add_alt_view_header(self.links_view, f"{title} · {len(grouped[entity_type])}")
            for relation in grouped[entity_type]:
                label = self._relation_display_label(relation.entity_type, relation.entity_id)
                row = QListWidgetItem(f"  {label}")
                row.setData(Qt.ItemDataRole.UserRole, (relation.entity_type, relation.entity_id))
                self.links_view.addItem(row)

    def _populate_links_view(self) -> None:
        self.links_view.clear()
        if self._current_idea_id is None:
            empty_item = QTreeWidgetItem(["Р’С‹Р±РµСЂРёС‚Рµ РёРґРµСЋ, С‡С‚РѕР±С‹ СѓРІРёРґРµС‚СЊ РµС‘ СЃРІСЏР·Рё."])
            empty_item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.links_view.addTopLevelItem(empty_item)
            return
        idea = next((item for item in self._visible_idea_items if item.id == self._current_idea_id), None)
        if idea is None:
            current = self._db.get_idea(self._current_idea_id)
            if current is None:
                unavailable_item = QTreeWidgetItem(["РЎРІСЏР·Рё РЅРµРґРѕСЃС‚СѓРїРЅС‹."])
                unavailable_item.setFlags(Qt.ItemFlag.NoItemFlags)
                self.links_view.addTopLevelItem(unavailable_item)
                return
            root_title = current.title
        else:
            root_title = idea.title
        root_item = QTreeWidgetItem([root_title])
        root_item.setFlags(Qt.ItemFlag.NoItemFlags)
        self.links_view.addTopLevelItem(root_item)

        relations = self._db.fetch_idea_relations(self._current_idea_id)
        if not relations:
            empty_group = QTreeWidgetItem(["РЎРІСЏР·РµР№ РїРѕРєР° РЅРµС‚"])
            empty_group.setFlags(Qt.ItemFlag.NoItemFlags)
            root_item.addChild(empty_group)
            empty_hint = QTreeWidgetItem(
                ["РЎРІСЏР¶РёС‚Рµ РёРґРµСЋ СЃ Р·Р°РґР°С‡РµР№, Р·Р°РјРµС‚РєРѕР№, РѕР±СЉРµРєС‚РѕРј РёР»Рё РєР°СЂС‚РѕР№, С‡С‚РѕР±С‹ РѕРЅР° СЃС‚Р°Р»Р° С‡Р°СЃС‚СЊСЋ СЂР°Р±РѕС‡РµРіРѕ РєРѕРЅС‚РµРєСЃС‚Р°."]
            )
            empty_hint.setFlags(Qt.ItemFlag.NoItemFlags)
            root_item.addChild(empty_hint)
            self.links_view.expandItem(root_item)
            return

        grouped: Dict[str, List[object]] = {}
        for relation in relations:
            grouped.setdefault(relation.entity_type, []).append(relation)
        for entity_type in IDEA_RELATION_GROUP_ORDER:
            bucket = grouped.get(entity_type, [])
            if not bucket:
                continue
            title = self._relation_group_title(entity_type)
            group_item = QTreeWidgetItem([f"{title} В· {len(bucket)}"])
            group_item.setFlags(Qt.ItemFlag.NoItemFlags)
            root_item.addChild(group_item)
            for relation in bucket:
                label = self._relation_display_label(relation.entity_type, relation.entity_id)
                row = QTreeWidgetItem([f"{self._relation_kind_title(getattr(relation, 'relation_kind', 'related'))} В· {label}"])
                row.setData(0, Qt.ItemDataRole.UserRole, (relation.entity_type, relation.entity_id))
                group_item.addChild(row)
            self.links_view.expandItem(group_item)
        self.links_view.expandItem(root_item)

    def _populate_mode_views(self) -> None:
        if not hasattr(self, "funnel_view"):
            return
        self._populate_funnel_view()
        self._populate_matrix_view()
        self._populate_links_view()

    def _on_view_mode_changed(self, *_args: object) -> None:
        mode = self.view_mode_combo.currentData()
        page_index = {
            "list": 0,
            "funnel": 1,
            "matrix": 2,
            "links": 3,
        }.get(mode, 0)
        self.list_mode_stack.setCurrentIndex(page_index)
        self._populate_mode_views()

    def _on_alt_view_item_activated(self, item: QListWidgetItem) -> None:
        idea_id = item.data(Qt.ItemDataRole.UserRole)
        if (
            isinstance(idea_id, tuple)
            and len(idea_id) == 2
            and isinstance(idea_id[0], str)
            and isinstance(idea_id[1], int)
        ):
            self._open_relation_target(idea_id[0], idea_id[1])
            return
        if not isinstance(idea_id, int):
            return
        model = self.list_view.model()
        if not isinstance(model, IdeasListModel):
            return
        index = model.index_for_id(idea_id)
        if not index.isValid():
            return
        self.list_view.setCurrentIndex(index)
        self._open_selected()

    def _reset_tab_titles(self) -> None:
        self._set_counted_tab_title(self.content_tab_index, "Суть")
        self._set_counted_tab_title(self.development_tab_index, "Развитие")
        self._set_counted_tab_title(self.relations_tab_index, "Связи", 0)
        self._set_counted_tab_title(self.materials_tab_index, "Материалы и референсы", 0)
        self._set_counted_tab_title(self.output_tab_index, "Выход")

    def _sync_development_preview(self) -> None:
        if not hasattr(self, "development_preview"):
            return
        self.development_preview.setPlainText(self.body_input.toPlainText().strip())

    def _insert_development_template(self) -> None:
        current_text = self.body_input.toPlainText().strip()
        if IDEA_DEVELOPMENT_TEMPLATE.strip() in current_text:
            self._set_status("Шаблон развития уже добавлен в описание.")
            self.inspector_tabs.setCurrentIndex(self.content_tab_index)
            self.body_input.setFocus()
            return
        if current_text:
            new_text = f"{current_text}\n\n{IDEA_DEVELOPMENT_TEMPLATE}"
        else:
            new_text = IDEA_DEVELOPMENT_TEMPLATE
        self.body_input.setPlainText(new_text)
        self.inspector_tabs.setCurrentIndex(self.content_tab_index)
        self.body_input.setFocus()
        self._set_status("Шаблон развития добавлен в описание идеи.")

    def _update_output_summary(self, idea_id: Optional[int]) -> None:
        if idea_id is None:
            self.output_summary_label.setText("Выход: нет")
            return
        idea = self._db.get_idea(idea_id)
        if idea is None:
            self.output_summary_label.setText("Выход: нет")
            return
        relations = self._db.fetch_idea_relations(idea_id)
        self.output_summary_label.setText(f"Выход: {self._idea_output_label(idea, relations)}")

    def _update_triage_panel(self) -> None:
        if not hasattr(self, "triage_progress_label"):
            return
        if not self._triage_mode or self._triage_total <= 0:
            self.triage_progress_label.setText("Выход идеи")
            self.triage_hint.setText("Идея должна либо созреть, либо стать действием, либо уйти в архив.")
            return
        remaining = self._inbox_count()
        position = max(1, min(self._triage_position, self._triage_total))
        self.triage_progress_label.setText(f"Разбор идеи {position} из {self._triage_total}")
        self.triage_hint.setText(
            "Поймал → Оценил → Развил → Связал → Превратил. "
            f"Осталось inbox: {remaining}."
        )

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
            f"Удалить категорию «{category.title}»? Идеи будут перенесены во Входящие.",
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
        payload = self._relation_payload(self.relations_list.currentItem())
        self.relations_add_button.setEnabled(has_idea)
        self.relations_open_button.setEnabled(has_idea and payload is not None)
        self.relations_remove_button.setEnabled(has_idea and payload is not None)

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
        elif entity_type == "concept_board":
            board = next((item for item in self._db.fetch_concept_boards() if item.id == entity_id), None)
            if board is not None:
                return f"Концептборд · {board.title}"
        return f"{label_prefix} #{entity_id}"

    def _find_main_window(self) -> object | None:
        parent = self.parent()
        while parent is not None:
            if hasattr(parent, "set_mode") and hasattr(parent, "MODE_CONCEPTBOARD"):
                return parent
            parent = parent.parent() if hasattr(parent, "parent") else None
        return None

    def _find_navigation_window(self) -> object | None:
        parent = self.parent()
        while parent is not None:
            if hasattr(parent, "set_mode"):
                return parent
            parent = parent.parent() if hasattr(parent, "parent") else None
        return None

    def _open_relation_target(self, entity_type: str, entity_id: int) -> bool:
        main_window = self._find_navigation_window()
        if main_window is None:
            return False
        handlers: dict[str, tuple[str, str, str]] = {
            "task": ("MODE_TASKS", "page_tasks", "focus_task"),
            "note": ("MODE_NOTES", "page_notes", "select_note"),
            "idea": ("MODE_IDEAS", "page_ideas", "select_idea"),
            "object": ("MODE_OBJECTS", "page_objects", "select_object"),
            "map": ("MODE_MAPS", "page_maps", "select_map"),
            "marker": ("MODE_MAPS", "page_maps", "select_marker"),
            "concept_board": ("MODE_CONCEPTBOARD", "page_concept_board", "select_concept_board"),
        }
        payload = handlers.get(entity_type)
        if payload is None:
            return False
        mode_attr, page_attr, method_name = payload
        mode_name = getattr(main_window, mode_attr, None)
        page = getattr(main_window, page_attr, None)
        if mode_name is None or page is None or not hasattr(page, method_name):
            return False
        try:
            main_window.set_mode(mode_name)
        except Exception:
            return False
        method = getattr(page, method_name)
        QTimer.singleShot(0, lambda relation_entity_id=entity_id, callback=method: callback(relation_entity_id))
        return True

    def _ensure_concept_board_target(self):
        boards = self._db.fetch_concept_boards()
        if boards:
            return boards[0]
        return self._db.create_concept_board("Концептборд 1")

    def _open_concept_board(self, concept_board_id: int) -> None:
        main_window = self._find_main_window()
        if main_window is None:
            return
        try:
            main_window.set_mode(main_window.MODE_CONCEPTBOARD)
        except Exception:
            return
        page = getattr(main_window, "page_concept_board", None)
        if page is not None and hasattr(page, "select_concept_board"):
            try:
                page.select_concept_board(concept_board_id)
            except Exception:
                return

    def _attach_current_idea_to_concept_board(self) -> None:
        if self._current_idea_id is None:
            return
        idea = self._db.get_idea(self._current_idea_id)
        if idea is None:
            return
        board = self._ensure_concept_board_target()
        self._db.attach_concept_board_item(board.id, "idea", idea.id)
        self._db.add_idea_relation(idea.id, "concept_board", board.id, "transforms_to")
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
        self.refresh()
        self._current_idea_id = idea.id
        self._sync_selection()
        self._open_concept_board(board.id)
        self._set_status(f"Идея добавлена в концептборд «{board.title}».")

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
        relation_kind = values.get("relation_kind")
        entity_id = values.get("entity_id")
        if not isinstance(entity_type, str) or not isinstance(entity_id, int):
            QMessageBox.warning(self, "Связи", "Выберите элемент для связи.")
            return
        self._db.add_idea_relation(
            self._current_idea_id,
            entity_type,
            entity_id,
            relation_kind if isinstance(relation_kind, str) else "related",
        )
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

    def _open_selected_relation(self) -> None:
        payload = self._relation_payload(self.relations_list.currentItem())
        if payload is None:
            QMessageBox.information(self, "РЎРІСЏР·Рё", "Р’С‹Р±РµСЂРёС‚Рµ СЃРІСЏР·Р°РЅРЅС‹Р№ СЌР»РµРјРµРЅС‚ РґР»СЏ РѕС‚РєСЂС‹С‚РёСЏ.")
            return
        _relation_id, entity_type, entity_id = payload
        if not self._open_relation_target(entity_type, entity_id):
            QMessageBox.information(self, "РЎРІСЏР·Рё", "Р­С‚Сѓ СЃРІСЏР·СЊ РїРѕРєР° РЅРµ СѓРґР°Р»РѕСЃСЊ РѕС‚РєСЂС‹С‚СЊ.")
            return
        self._set_status("РЎРІСЏР·Р°РЅРЅС‹Р№ СЌР»РµРјРµРЅС‚ РѕС‚РєСЂС‹С‚")

    def _on_status_filter_changed(self, *_args: object) -> None:
        status = self.status_filter.currentData()
        self.set_filter("status", status)
        self._set_quick_status(status if isinstance(status, str) else None)

    def _on_type_filter_changed(self, *_args: object) -> None:
        self.set_filter("type", self.type_filter.currentData())

    def _on_archived_filter_changed(self, *_args: object) -> None:
        self.set_filter("archived", self.archived_only.isChecked())

    def apply_query(self, query: str) -> None:
        _ = query
        self._status_message = ""
        self.refresh()

    def apply_filters(self, filters: dict[str, object]) -> None:
        _ = filters
        self._status_message = ""
        self.refresh()

    def refresh(self) -> None:
        filters = self.get_filters()
        project_paths = _build_project_path_map(self._db.fetch_projects())
        ideas = self._db.fetch_ideas(
            project_id=None,
            search=self._query,
            status=filters.get("status"),
            idea_type=filters.get("type"),
            archived=bool(filters.get("archived")),
        )
        items: List[IdeaItem] = []
        for idea in ideas:
            relations = self._db.fetch_idea_relations(idea.id)
            materials = self._db.fetch_idea_images(idea.id)
            items.append(
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
                    source=idea.source,
                    output_label=self._idea_output_label(idea, relations),
                    relations_count=len(relations),
                    materials_count=len(materials),
                    updated_label=self._format_relative_time(idea.updated_at),
                    project_path=project_paths.get(idea.project_id or -1, idea.project_title),
                )
            )
        self._visible_idea_items = items
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
        self._update_empty_state(items)
        self._sync_selection()
        self._populate_mode_views()
        self._refresh_status_bar()

    def _sync_selection(self) -> None:
        if self._current_idea_id is None:
            self._current_project_id = None
            self.inspector_stack.setCurrentWidget(self.inspector_empty)
            self._reset_tab_titles()
            self._update_output_summary(None)
            self._update_triage_panel()
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
        self._reset_tab_titles()
        self._update_output_summary(None)
        self._update_triage_panel()
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
            self._populate_links_view()
            self._update_relations_actions()
            self.update_action_states()
            return
        self._current_idea_id = index.data(IdeaRoles.IdeaId)
        self._load_idea(self._current_idea_id)
        self.inspector_stack.setCurrentWidget(self.inspector_tabs)
        self._populate_links_view()
        self.update_action_states()

    def select_idea(self, idea_id: int) -> bool:
        model = self.list_view.model()
        if not isinstance(model, IdeasListModel):
            return False
        index = model.index_for_id(idea_id)
        if not index.isValid() and self.archived_only.isChecked():
            self.archived_only.blockSignals(True)
            self.archived_only.setChecked(False)
            self.archived_only.blockSignals(False)
            self.set_filter("archived", False)
            self.refresh()
            index = model.index_for_id(idea_id)
        if not index.isValid():
            return False
        self.list_view.setCurrentIndex(index)
        self._open_selected()
        return True

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
        self.source_input.setText(_join_idea_sources(_idea_source_lines(idea.source)))
        self.value_input.setValue(idea.value_score)
        self.effort_input.setValue(idea.effort_score)
        self._dirty = False
        self._load_relations(idea_id)
        self._load_materials(idea_id)
        self._sync_development_preview()
        self._update_output_summary(idea_id)
        self._update_triage_panel()
        self.update_action_states()

    def _add_dossier_source(self) -> None:
        dialog = _IdeaDossierSourceDialog(self._db, parent=self)
        if exec_with_overlay(dialog, self) != QDialog.DialogCode.Accepted:
            return
        source_text = dialog.selected_source_text()
        if source_text:
            self.source_input.append_source(source_text)

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
            source=_join_idea_sources(_idea_source_lines(self.source_input.text())),
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

    def _set_selected_idea_status(self, idea_id: int, status: str) -> None:
        if self._dirty and not self._maybe_save_changes():
            return
        idea = self._db.get_idea(idea_id)
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
        self._current_idea_id = idea_id
        self.refresh()
        self._set_status(f"Идея переведена в {self._category_title(status)}.")

    def _show_context_menu(self, pos) -> None:
        index = self.list_view.indexAt(pos)
        if not index.isValid() or index.data(IdeaRoles.RowType) != "idea":
            return
        idea_id = index.data(IdeaRoles.IdeaId)
        idea = self._db.get_idea(idea_id)
        menu = QMenu(self)
        action_open = menu.addAction("Открыть")
        action_edit = menu.addAction("Редактировать")
        transform_task = menu.addAction("Создать задачу")
        transform_note = menu.addAction("Создать заметку")
        transform_object = menu.addAction("Создать объект")
        transform_concept_board = menu.addAction("Добавить в концептборд")
        transform_marker = menu.addAction("Создать метку карты")
        menu.addSeparator()
        status_work = menu.addAction("В работу")
        status_ripe = menu.addAction("Созрела")
        action_archive = menu.addAction("В архив" if idea and not idea.archived_at else "Восстановить")
        menu.addSeparator()
        action_delete = menu.addAction("Удалить")

        action = menu.exec(QCursor.pos())
        if action == action_open:
            self.list_view.setCurrentIndex(index)
            self._open_selected()
        elif action == action_edit:
            self.list_view.setCurrentIndex(index)
            self._open_selected()
        elif action == status_work:
            self._set_selected_idea_status(idea_id, "work")
        elif action == status_ripe:
            self._set_selected_idea_status(idea_id, "ripe")
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
        elif action == transform_concept_board:
            self._current_idea_id = idea_id
            self._attach_current_idea_to_concept_board()
        elif action == transform_marker:
            self._current_idea_id = idea_id
            self._transform_idea("marker")

    def _load_relations(self, idea_id: int) -> None:
        self.relations_list.clear()
        relations = self._db.fetch_idea_relations(idea_id)
        self._set_counted_tab_title(self.relations_tab_index, "Связи", len(relations))
        if not relations:
            item = QListWidgetItem(
                "Связей пока нет\nСвяжите идею с задачей, заметкой, объектом или картой."
            )
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.relations_list.addItem(item)
            self._update_relations_actions()
            self._populate_links_view()
            return
        grouped: Dict[str, List[object]] = {}
        for relation in relations:
            grouped.setdefault((relation.entity_type or "").strip().lower(), []).append(relation)
        ordered_types = [entity_type for entity_type in IDEA_RELATION_GROUP_ORDER if entity_type in grouped]
        ordered_types.extend(sorted(entity_type for entity_type in grouped if entity_type not in IDEA_RELATION_GROUP_ORDER))
        for entity_type in ordered_types:
            bucket = grouped[entity_type]
            header = QListWidgetItem(f"{self._relation_group_title(entity_type)} В· {len(bucket)}")
            header.setFlags(Qt.ItemFlag.NoItemFlags)
            self.relations_list.addItem(header)
            for relation in bucket:
                item = QListWidgetItem(
                    f"  {self._relation_kind_title(getattr(relation, 'relation_kind', 'related'))} В· "
                    f"{self._relation_display_label(relation.entity_type, relation.entity_id)}"
                )
                item.setData(Qt.ItemDataRole.UserRole, relation.id)
                item.setData(int(Qt.ItemDataRole.UserRole) + 1, entity_type)
                item.setData(int(Qt.ItemDataRole.UserRole) + 2, relation.entity_id)
                item.setToolTip("Р”РІРѕР№РЅРѕР№ С‰РµР»С‡РѕРє РѕС‚РєСЂС‹РІР°РµС‚ СЃРІСЏР·Р°РЅРЅСѓСЋ СЃСѓС‰РЅРѕСЃС‚СЊ.")
                self.relations_list.addItem(item)
        self._update_relations_actions()
        self._populate_links_view()

    def _load_materials(self, idea_id: int) -> None:
        self._idea_images = self._db.fetch_idea_images(idea_id)
        self._current_material_index = 0
        self._set_counted_tab_title(self.materials_tab_index, "Материалы и референсы", len(self._idea_images))
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
            self.materials_hint.setText(
                "Материалов пока нет.\nДобавьте изображение или референс, чтобы связать идею с визуальным контекстом."
            )
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

    def _transform_idea(self, kind: str) -> bool:
        if self._current_idea_id is None:
            return False
        idea = self._db.get_idea(self._current_idea_id)
        if idea is None:
            return False
        if kind == "task":
            task = self._db.create_task(
                title=idea.title,
                description=idea.body_md,
                day=date.today(),
                time_text="",
                priority="Medium",
                project_id=idea.project_id,
            )
            self._db.add_idea_relation(idea.id, "task", task.id, "transforms_to")
            self._set_status("Создана задача")
        elif kind == "note":
            note = self._db.create_note(
                title=idea.title,
                preview=idea.summary or idea.body_md,
                tags=[],
                project=idea.project_title,
            )
            self._db.add_idea_relation(idea.id, "note", note.id, "transforms_to")
            self._set_status("Создана заметка")
        elif kind == "object":
            obj = self._db.create_object(
                title=idea.title,
                catalog="",
                object_type="",
                status="",
                description=idea.body_md,
            )
            self._db.add_idea_relation(idea.id, "object", obj.id, "transforms_to")
            self._set_status("Создан объект")
        else:
            self._set_status("Для метки нужно выбрать карту")
            return False
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
        return True

    def _start_inbox_triage(self, *_args: object) -> None:
        if self._dirty and not self._maybe_save_changes():
            return
        self.search_input.setText("")
        self.type_filter.setCurrentIndex(0)
        self.archived_only.setChecked(False)
        inbox_index = self.status_filter.findData("inbox")
        if inbox_index >= 0:
            self.status_filter.setCurrentIndex(inbox_index)
        self._triage_total = self._inbox_count()
        self._triage_position = 1 if self._triage_total else 0
        self._triage_mode = self._triage_total > 0
        self._update_triage_panel()
        if not self._triage_mode or not self._select_first_inbox_idea():
            self._triage_mode = False
            self._triage_total = 0
            self._triage_position = 0
            self._update_triage_panel()
            self._set_status("Inbox пуст. Нет идей для разбора.")
            return
        self.inspector_tabs.setCurrentWidget(self.transform_tab)
        self._update_triage_panel()
        self._set_status(f"Разбор идеи {self._triage_position} из {self._triage_total}.")

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
        if self._triage_mode:
            self._triage_position = min(self._triage_total, self._triage_position + 1)
        if self._triage_mode and self._select_first_inbox_idea():
            self.inspector_tabs.setCurrentWidget(self.transform_tab)
            self._update_triage_panel()
            self._set_status(f"{status_message} Разбор идеи {self._triage_position} из {self._triage_total}.")
            return
        self._triage_mode = False
        self._triage_total = 0
        self._triage_position = 0
        self._current_idea_id = None
        self._sync_selection()
        self._update_triage_panel()
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
        if not self._transform_idea(kind):
            return
        if self._triage_mode and kind in {"task", "note", "object"}:
            messages = {
                "task": "Из идеи создана задача.",
                "note": "Из идеи создана заметка.",
                "object": "Из идеи создан объект.",
            }
            self._advance_inbox_triage(messages[kind])

    def _skip_inbox_idea(self) -> None:
        if self._current_idea_id is None:
            if not self._select_first_inbox_idea():
                self._set_status("Инбокс пуст.")
            return
        if self._select_next_inbox_idea():
            if self._triage_mode:
                self._triage_position = min(self._triage_total, self._triage_position + 1)
                self._update_triage_panel()
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
