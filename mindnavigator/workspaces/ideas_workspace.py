"""Рабочая область идей (IdeasWorkspace).

Входные данные:
    Список идей из базы данных, фильтры и действия пользователя.

Выходные данные:
    Обновленные записи идей и отображение карточек/инспектора.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional, Any, List, Union, Dict

from PySide6.QtCore import Qt, QSize, QAbstractListModel, QModelIndex
from PySide6.QtGui import QAction, QPainter, QColor, QFont, QCursor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QListView,
    QStyledItemDelegate,
    QStyle,
    QStyleOptionViewItem,
    QSplitter,
    QTabWidget,
    QFormLayout,
    QLineEdit,
    QPlainTextEdit,
    QComboBox,
    QSpinBox,
    QToolButton,
    QCheckBox,
    QMenu,
    QStackedWidget,
    QListWidget,
    QListWidgetItem,
    QDialog,
    QFileDialog,
    QMessageBox,
)

from mindnavigator.csv_transfer import CsvTransferError, CsvTransferService
from mindnavigator.storage import get_database
from mindnavigator.ui.modals import ConfirmDialog, exec_with_overlay
from mindnavigator.ui.workspaces.base_workspace import BaseWorkspace
from mindnavigator.workspaces.csv_workspace_transfer import (
    IDEAS_CSV_FIELDS,
    export_ideas_rows,
    import_ideas_rows,
)


IDEA_TYPES = [
    ("Все", None),
    ("Feature", "feature"),
    ("Story", "story"),
    ("Art", "art"),
    ("Research", "research"),
    ("Tech", "tech"),
    ("Other", "other"),
]

IDEA_STATUSES = [
    ("Все", None),
    ("Inbox", "inbox"),
    ("Work", "work"),
    ("Ripe", "ripe"),
    ("Done", "done"),
    ("Archived", "archived"),
]

STATUS_LABELS = {
    "inbox": "Inbox",
    "work": "Work",
    "ripe": "Ripe",
    "done": "Done",
    "archived": "Archived",
}

TYPE_LABELS = {
    "feature": "Feature",
    "story": "Story",
    "art": "Art",
    "research": "Research",
    "tech": "Tech",
    "other": "Other",
}


@dataclass(frozen=True)
class IdeaItem:
    id: int
    title: str
    summary: str
    body_md: str
    status: str
    idea_type: str
    value_score: int
    effort_score: int
    project_id: Optional[int]
    project_title: str
    archived: bool


@dataclass(frozen=True)
class IdeaCategoryRow:
    category: str


IdeaRow = Union[IdeaItem, IdeaCategoryRow]


class IdeaRoles:
    RowType = Qt.ItemDataRole.UserRole + 1
    IdeaId = Qt.ItemDataRole.UserRole + 2
    Title = Qt.ItemDataRole.UserRole + 3
    Summary = Qt.ItemDataRole.UserRole + 4
    Body = Qt.ItemDataRole.UserRole + 5
    Status = Qt.ItemDataRole.UserRole + 6
    Type = Qt.ItemDataRole.UserRole + 7
    ValueScore = Qt.ItemDataRole.UserRole + 8
    EffortScore = Qt.ItemDataRole.UserRole + 9
    ProjectTitle = Qt.ItemDataRole.UserRole + 10
    Archived = Qt.ItemDataRole.UserRole + 11


def normalize_idea_category(status: str) -> str:
    value = (status or "").strip().lower()
    return STATUS_LABELS.get(value, value.capitalize() if value else "Без статуса")


def group_ideas_by_category(items: List[IdeaItem]) -> List[IdeaRow]:
    order = ["Inbox", "Work", "Ripe", "Done", "Archived", "Без статуса"]
    groups: Dict[str, List[IdeaItem]] = {}
    for item in items:
        groups.setdefault(normalize_idea_category(item.status), []).append(item)
    rows: List[IdeaRow] = []
    for category in sorted(
        groups.keys(),
        key=lambda value: (order.index(value) if value in order else len(order), value.lower()),
    ):
        rows.append(IdeaCategoryRow(category))
        rows.extend(groups[category])
    return rows


def idea_preview_line(summary: str, body_md: str) -> str:
    """Возвращает компактное превью идеи из summary или текста описания."""
    sources = [summary or "", body_md or ""]
    for source in sources:
        normalized = source.replace("\r\n", "\n").replace("\r", "\n")
        for raw_line in normalized.split("\n"):
            line = " ".join(raw_line.strip().split())
            if line:
                return line
    return "Нет превью идеи."


class IdeasListModel(QAbstractListModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._ideas: list[IdeaItem] = []
        self._rows: list[IdeaRow] = []

    def rowCount(self, parent=QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._rows)

    def data(self, index: QModelIndex, role: int = int(Qt.ItemDataRole.DisplayRole)) -> Any:
        if not index.isValid():
            return None
        row = self._rows[index.row()]
        if role == IdeaRoles.RowType:
            return "category" if isinstance(row, IdeaCategoryRow) else "idea"
        if isinstance(row, IdeaCategoryRow):
            if role == IdeaRoles.Title:
                return row.category
            if role == Qt.ItemDataRole.DisplayRole:
                return row.category
            return None
        item = row
        if role == IdeaRoles.IdeaId:
            return item.id
        if role == IdeaRoles.Title:
            return item.title
        if role == IdeaRoles.Summary:
            return item.summary
        if role == IdeaRoles.Body:
            return item.body_md
        if role == IdeaRoles.Status:
            return item.status
        if role == IdeaRoles.Type:
            return item.idea_type
        if role == IdeaRoles.ValueScore:
            return item.value_score
        if role == IdeaRoles.EffortScore:
            return item.effort_score
        if role == IdeaRoles.ProjectTitle:
            return item.project_title
        if role == IdeaRoles.Archived:
            return item.archived
        if role == Qt.ItemDataRole.DisplayRole:
            return item.title
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if not index.isValid():
            return Qt.ItemFlags(Qt.ItemFlag.NoItemFlags)
        row = self._rows[index.row()]
        if isinstance(row, IdeaCategoryRow):
            return Qt.ItemFlags(Qt.ItemFlag.ItemIsEnabled)
        flags = Qt.ItemFlags(Qt.ItemFlag.ItemIsEnabled)
        flags |= Qt.ItemFlag.ItemIsSelectable
        return flags

    def set_items(self, items: list[IdeaItem]) -> None:
        self.beginResetModel()
        self._ideas = items
        self._rows = group_ideas_by_category(items)
        self.endResetModel()

    def item_at(self, row: int) -> Optional[IdeaItem]:
        if 0 <= row < len(self._rows):
            idea_row = self._rows[row]
            if isinstance(idea_row, IdeaItem):
                return idea_row
        return None

    def index_for_id(self, idea_id: int) -> QModelIndex:
        for row, item in enumerate(self._rows):
            if isinstance(item, IdeaItem) and item.id == idea_id:
                return self.index(row)
        return QModelIndex()

    def statuses(self) -> List[str]:
        return sorted(
            {(item.status or "").strip().lower() for item in self._ideas if (item.status or "").strip()},
            key=lambda value: (
                ["inbox", "work", "ripe", "done", "archived"].index(value)
                if value in {"inbox", "work", "ripe", "done", "archived"}
                else 99,
                value,
            ),
        )


class IdeasDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        painter.save()
        row_type = index.data(IdeaRoles.RowType)
        if row_type == "category":
            self._paint_category(painter, option, index)
            painter.restore()
            return
        rect = option.rect.adjusted(10, 3, -10, -3)
        selected = option.state & QStyle.StateFlag.State_Selected
        background = QColor("#2f3036" if selected else "#1f2024")
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(background)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, 8, 8)

        title = index.data(IdeaRoles.Title) or "Без названия"
        project = index.data(IdeaRoles.ProjectTitle) or "Без проекта"
        status = STATUS_LABELS.get(index.data(IdeaRoles.Status), "")
        idea_type = TYPE_LABELS.get(index.data(IdeaRoles.Type), "")
        value_score = index.data(IdeaRoles.ValueScore)
        effort_score = index.data(IdeaRoles.EffortScore)
        summary = index.data(IdeaRoles.Summary) or ""
        body_md = index.data(IdeaRoles.Body) or ""
        preview_text = idea_preview_line(summary, body_md)

        title_font = QFont(option.font)
        title_font.setPointSize(title_font.pointSize() + 1)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.setPen(QColor("#f2f2f2"))
        painter.drawText(
            rect.adjusted(12, 8, -12, -46),
            Qt.TextFlag.TextSingleLine | Qt.AlignmentFlag.AlignLeft,
            title,
        )

        meta_font = QFont(option.font)
        meta_font.setPointSize(meta_font.pointSize() - 1)
        painter.setFont(meta_font)
        painter.setPen(QColor("#c0c0c0"))
        meta_text = " | ".join(part for part in [project, status, idea_type] if part)
        painter.drawText(
            rect.adjusted(12, 28, -12, -28),
            Qt.TextFlag.TextSingleLine | Qt.AlignmentFlag.AlignLeft,
            meta_text,
        )

        painter.setPen(QColor("#adb3bc"))
        painter.drawText(
            rect.adjusted(12, 46, -12, -10),
            Qt.TextFlag.TextSingleLine | Qt.AlignmentFlag.AlignLeft,
            preview_text,
        )

        score_text = f"Value {value_score} | Effort {effort_score}"
        painter.setPen(QColor("#8bb5e8"))
        painter.drawText(
            rect.adjusted(12, 64, -12, -2),
            Qt.TextFlag.TextSingleLine | Qt.AlignmentFlag.AlignLeft,
            score_text,
        )

        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        if index.data(IdeaRoles.RowType) == "category":
            return QSize(option.rect.width(), 30)
        return QSize(option.rect.width(), 88)

    @staticmethod
    def _paint_category(painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        rect = option.rect.adjusted(10, 3, -10, -3)
        title = (index.data(IdeaRoles.Title) or "").strip() or "Без категории"
        font = QFont(option.font)
        font.setPointSize(max(8, font.pointSize() - 1))
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor("#8d939b"))
        painter.drawText(rect.adjusted(4, 0, -4, 0), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, title)
        painter.setPen(QColor("#30333a"))
        painter.drawLine(rect.left(), rect.bottom(), rect.right(), rect.bottom())


class IdeasWorkspace(BaseWorkspace):
    workspace_id = "ideas"
    workspace_title = "Идеи"

    def __init__(self, parent: QWidget | None = None) -> None:
        self._db = get_database()
        self._csv_service = CsvTransferService()
        self._current_idea_id: Optional[int] = None
        self._current_project_id: Optional[int] = None
        self._dirty = False
        super().__init__(parent)
        self.setObjectName("IdeasWorkspace")
        self.search_input.setPlaceholderText("Поиск…")
        self.refresh()

    def _build_ui(self) -> None:
        super()._build_ui()

        self.status_filter = QComboBox()
        for label, value in IDEA_STATUSES:
            self.status_filter.addItem(label, value)
        self.status_filter.currentIndexChanged.connect(self._on_status_filter_changed)

        self.type_filter = QComboBox()
        for label, value in IDEA_TYPES:
            self.type_filter.addItem(label, value)
        self.type_filter.currentIndexChanged.connect(self._on_type_filter_changed)

        self.archived_only = QCheckBox("Только архив")
        self.archived_only.stateChanged.connect(self._on_archived_filter_changed)

        self.filter_layout.addWidget(QLabel("Статус"))
        self.filter_layout.addWidget(self.status_filter)
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
        self.quick_status_label.setStyleSheet("color:#9ea3ac; font-size:11px;")
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
        content_layout = QFormLayout(content_tab)
        content_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        content_layout.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        content_layout.setContentsMargins(14, 12, 14, 12)
        content_layout.setSpacing(10)

        self.title_input = QLineEdit()
        self.summary_input = QLineEdit()
        self.body_input = QPlainTextEdit()
        self.type_input = QComboBox()
        for label, value in IDEA_TYPES[1:]:
            self.type_input.addItem(label, value)
        self.status_input = QComboBox()
        for label, value in IDEA_STATUSES[1:]:
            self.status_input.addItem(label, value)

        self.value_input = QSpinBox()
        self.value_input.setRange(1, 5)
        self.effort_input = QSpinBox()
        self.effort_input.setRange(1, 5)

        content_layout.addRow("Название", self.title_input)
        content_layout.addRow("Кратко", self.summary_input)
        content_layout.addRow("Описание", self.body_input)
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

        self.relations_list = QListWidget()
        relations_tab = QWidget()
        relations_layout = QVBoxLayout(relations_tab)
        relations_layout.setContentsMargins(12, 12, 12, 12)
        relations_layout.addWidget(self.relations_list, 1)
        self.inspector_tabs.addTab(relations_tab, "Связи")

        materials_tab = QWidget()
        materials_layout = QVBoxLayout(materials_tab)
        materials_layout.setContentsMargins(12, 12, 12, 12)
        materials_layout.addWidget(QLabel("Добавление материалов будет доступно позже."))
        self.inspector_tabs.addTab(materials_tab, "Материалы")

        transform_tab = QWidget()
        transform_layout = QVBoxLayout(transform_tab)
        transform_layout.setContentsMargins(12, 12, 12, 12)
        transform_layout.setSpacing(8)
        self.transform_task_btn = QToolButton()
        self.transform_task_btn.setText("✅ Создать задачу")
        self.transform_task_btn.setObjectName("IdeasTransformTask")
        self.transform_task_btn.clicked.connect(lambda: self._transform_idea("task"))
        self.transform_note_btn = QToolButton()
        self.transform_note_btn.setText("📝 Создать заметку")
        self.transform_note_btn.setObjectName("IdeasTransformNote")
        self.transform_note_btn.clicked.connect(lambda: self._transform_idea("note"))
        self.transform_object_btn = QToolButton()
        self.transform_object_btn.setText("🧱 Создать объект")
        self.transform_object_btn.setObjectName("IdeasTransformObject")
        self.transform_object_btn.clicked.connect(lambda: self._transform_idea("object"))
        self.transform_marker_btn = QToolButton()
        self.transform_marker_btn.setText("🗺️ Создать метку")
        self.transform_marker_btn.setObjectName("IdeasTransformMarker")
        self.transform_marker_btn.clicked.connect(lambda: self._transform_idea("marker"))
        transform_layout.addWidget(self.transform_task_btn)
        transform_layout.addWidget(self.transform_note_btn)
        transform_layout.addWidget(self.transform_object_btn)
        transform_layout.addWidget(self.transform_marker_btn)
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
        self.type_input.currentIndexChanged.connect(self._mark_dirty)
        self.status_input.currentIndexChanged.connect(self._mark_dirty)
        self.value_input.valueChanged.connect(self._mark_dirty)
        self.effort_input.valueChanged.connect(self._mark_dirty)
        self.quick_create_btn.clicked.connect(self._create_idea_from_quick_form)
        self.quick_status_btn.clicked.connect(self._open_quick_status_menu)
        self.quick_title_input.returnPressed.connect(self._create_idea_from_quick_form)
        self._set_quick_status(None)

        self.setStyleSheet("""
            QWidget#IdeasWorkspace { background: #16171a; }

            QWidget#IdeasWorkspace QLabel {
                color: #cfcfcf;
            }

            QWidget#IdeasWorkspace QWidget#WorkspaceToolbar,
            QWidget#IdeasWorkspace QWidget#WorkspaceSearch,
            QWidget#IdeasWorkspace QWidget#WorkspaceFilters {
                background: #1b1c1f;
                border: 1px solid #2a2b2f;
                border-radius: 10px;
                padding: 6px;
            }

            QWidget#IdeasWorkspace QWidget#WorkspaceStatus {
                color: #b8b8b8;
            }

            QWidget#IdeasWorkspace QToolButton {
                color: #cfcfcf;
                background: #2a2b2f;
                border: 1px solid #3a3b40;
                padding: 6px 10px;
                border-radius: 6px;
            }
            QWidget#IdeasWorkspace QToolButton:hover {
                background: #34363b;
            }
            QWidget#IdeasWorkspace QToolButton:disabled {
                color: #6e6f75;
                background: #1e1f23;
                border-color: #2a2b2f;
            }

            QWidget#IdeasWorkspace QLineEdit,
            QWidget#IdeasWorkspace QPlainTextEdit,
            QWidget#IdeasWorkspace QComboBox,
            QWidget#IdeasWorkspace QSpinBox {
                background: #202127;
                color: #cfcfcf;
                border: 1px solid #2a2b2f;
                padding: 6px 8px;
                border-radius: 6px;
            }

            QWidget#IdeasWorkspace QLineEdit:focus,
            QWidget#IdeasWorkspace QPlainTextEdit:focus,
            QWidget#IdeasWorkspace QComboBox:focus,
            QWidget#IdeasWorkspace QSpinBox:focus {
                border-color: #3b3c43;
            }

            QWidget#IdeasWorkspace QCheckBox {
                color: #cfcfcf;
                padding: 2px 4px;
            }

            QListView#IdeasList {
                background: #16171a;
                border: 1px solid #2a2b2f;
                border-radius: 10px;
                padding: 6px;
            }

            QStackedWidget#IdeasInspectorStack {
                background: transparent;
            }

            QTabWidget#IdeasInspectorTabs::pane {
                border: 1px solid #2a2b2f;
                background: #1b1c1f;
                border-radius: 10px;
                padding: 6px;
            }

            QTabWidget#IdeasInspectorTabs QTabBar::tab {
                background: #202127;
                color: #cfcfcf;
                padding: 6px 12px;
                margin-right: 4px;
                border-radius: 6px;
            }
            QTabWidget#IdeasInspectorTabs QTabBar::tab:selected {
                background: #2a2b2f;
            }

            QWidget#IdeasWorkspace QListWidget {
                background: #16171a;
                color: #e6e6e6;
                border: 1px solid #2a2b2f;
                border-radius: 8px;
                padding: 6px;
            }

            QLabel#IdeasEmpty {
                color: #8f9096;
            }
        """)

    def create_actions(self) -> dict[str, QAction]:
        action_new = QAction("+ Идея", self)
        action_new.triggered.connect(self._create_idea)
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

    def _mark_dirty(self) -> None:
        self._dirty = True

    def _on_status_filter_changed(self) -> None:
        status = self.status_filter.currentData()
        self.set_filter("status", status)
        self._set_quick_status(status if isinstance(status, str) else None)

    def _on_type_filter_changed(self) -> None:
        self.set_filter("type", self.type_filter.currentData())

    def _on_archived_filter_changed(self) -> None:
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
            model.set_items(items)
            quick_status = self.quick_status_label.property("quick_status")
            if isinstance(quick_status, str) and quick_status not in model.statuses():
                self._set_quick_status(None)
        self._sync_selection()

    def _sync_selection(self) -> None:
        if self._current_idea_id is None:
            self._current_project_id = None
            self.inspector_stack.setCurrentWidget(self.inspector_empty)
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
        self.update_action_states()

    def _on_selection_changed(self) -> None:
        if self._dirty and not self._maybe_save_changes():
            self._sync_selection()
            return
        index = self.list_view.currentIndex()
        if not index.isValid() or index.data(IdeaRoles.RowType) != "idea":
            self._current_idea_id = None
            self._current_project_id = None
            self.inspector_stack.setCurrentWidget(self.inspector_empty)
            self.update_action_states()
            return
        self._current_idea_id = index.data(IdeaRoles.IdeaId)
        self._load_idea(self._current_idea_id)
        self.inspector_stack.setCurrentWidget(self.inspector_tabs)
        self.update_action_states()

    def _open_selected(self) -> None:
        if self._current_idea_id is None:
            return
        self.inspector_stack.setCurrentWidget(self.inspector_tabs)
        self.title_input.setFocus()

    def _load_idea(self, idea_id: int) -> None:
        idea = self._db.get_idea(idea_id)
        if idea is None:
            return
        self._current_project_id = idea.project_id
        self.title_input.setText(idea.title)
        self.summary_input.setText(idea.summary)
        self.body_input.setPlainText(idea.body_md)
        self._set_combo_value(self.type_input, idea.type)
        self._set_combo_value(self.status_input, idea.status)
        self.value_input.setValue(idea.value_score)
        self.effort_input.setValue(idea.effort_score)
        self._dirty = False
        self._load_relations(idea_id)

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

    def _save_current(self) -> bool:
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

    def _revert_current(self) -> None:
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

    def _set_quick_status(self, status: Optional[str]) -> None:
        normalized = (status or "").strip().lower()
        if not normalized:
            self.quick_status_label.setText("Все категории")
            self.quick_status_label.setProperty("quick_status", None)
            return
        self.quick_status_label.setText(normalize_idea_category(normalized))
        self.quick_status_label.setProperty("quick_status", normalized)

    def _open_quick_status_menu(self) -> None:
        menu = QMenu(self)
        action_all = menu.addAction("Все категории")
        menu.addSeparator()
        status_actions: Dict[Any, str] = {}
        for label, value in IDEA_STATUSES[1:]:
            if value:
                action = menu.addAction(label)
                status_actions[action] = value
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

    def _create_idea_from_quick_form(self) -> None:
        title = (self.quick_title_input.text() or "").strip() or "Новая идея"
        quick_status = self.quick_status_label.property("quick_status")
        status = quick_status if isinstance(quick_status, str) and quick_status else "inbox"
        self._create_idea(title=title, status=status)
        self.quick_title_input.clear()

    def _archive_selected(self) -> None:
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
            return
        for relation in relations:
            label = f"{relation.entity_type} #{relation.entity_id}"
            self.relations_list.addItem(QListWidgetItem(label))

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

    def _export_ideas_csv(self) -> None:
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

    def _import_ideas_csv(self) -> None:
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
