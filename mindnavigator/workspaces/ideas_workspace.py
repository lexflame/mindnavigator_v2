"""Рабочая область идей (IdeasWorkspace).

Входные данные:
    Список идей из базы данных, фильтры и действия пользователя.

Выходные данные:
    Обновленные записи идей и отображение карточек/инспектора.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from PySide6.QtCore import Qt, QSize, QAbstractListModel, QModelIndex
from PySide6.QtGui import QAction, QPainter, QColor, QFont, QCursor
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QListView,
    QStyledItemDelegate,
    QStyle,
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
)

from mindnavigator.storage import get_database
from mindnavigator.ui.modals import ConfirmDialog, exec_with_overlay
from mindnavigator.ui.workspaces.base_workspace import BaseWorkspace


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


class IdeaRoles:
    IdeaId = Qt.UserRole + 1
    Title = Qt.UserRole + 2
    Summary = Qt.UserRole + 3
    Body = Qt.UserRole + 4
    Status = Qt.UserRole + 5
    Type = Qt.UserRole + 6
    ValueScore = Qt.UserRole + 7
    EffortScore = Qt.UserRole + 8
    ProjectTitle = Qt.UserRole + 9
    Archived = Qt.UserRole + 10


class IdeasListModel(QAbstractListModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: list[IdeaItem] = []

    def rowCount(self, parent=QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._items)

    def data(self, index: QModelIndex, role: int):
        if not index.isValid():
            return None
        item = self._items[index.row()]
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
        if role == Qt.DisplayRole:
            return item.title
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if not index.isValid():
            return Qt.NoItemFlags
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def set_items(self, items: list[IdeaItem]) -> None:
        self.beginResetModel()
        self._items = items
        self.endResetModel()

    def item_at(self, row: int) -> Optional[IdeaItem]:
        if 0 <= row < len(self._items):
            return self._items[row]
        return None

    def index_for_id(self, idea_id: int) -> QModelIndex:
        for row, item in enumerate(self._items):
            if item.id == idea_id:
                return self.index(row)
        return QModelIndex()


class IdeasDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, option: QStyle.OptionViewItem, index: QModelIndex) -> None:
        painter.save()
        rect = option.rect.adjusted(10, 6, -10, -6)
        selected = option.state & QStyle.State_Selected
        background = QColor("#35363c" if selected else "#2a2b2f")
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(background)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(rect, 10, 10)

        title = index.data(IdeaRoles.Title) or "Без названия"
        project = index.data(IdeaRoles.ProjectTitle) or "Без проекта"
        status = STATUS_LABELS.get(index.data(IdeaRoles.Status), "")
        idea_type = TYPE_LABELS.get(index.data(IdeaRoles.Type), "")
        value_score = index.data(IdeaRoles.ValueScore)
        effort_score = index.data(IdeaRoles.EffortScore)

        title_font = QFont(option.font)
        title_font.setPointSize(title_font.pointSize() + 1)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.setPen(QColor("#f2f2f2"))
        painter.drawText(rect.adjusted(12, 8, -12, -36), Qt.TextSingleLine | Qt.AlignLeft, title)

        meta_font = QFont(option.font)
        meta_font.setPointSize(meta_font.pointSize() - 1)
        painter.setFont(meta_font)
        painter.setPen(QColor("#c0c0c0"))
        meta_text = f"{project} • {status} • {idea_type}"
        painter.drawText(rect.adjusted(12, 30, -12, -16), Qt.TextSingleLine | Qt.AlignLeft, meta_text)

        score_text = f"⭐ {value_score}  ⚙ {effort_score}"
        painter.setPen(QColor("#a8d4ff"))
        painter.drawText(rect.adjusted(12, 52, -12, -4), Qt.TextSingleLine | Qt.AlignLeft, score_text)

        painter.restore()

    def sizeHint(self, option: QStyle.OptionViewItem, index: QModelIndex) -> QSize:
        return QSize(option.rect.width(), 86)


class IdeasWorkspace(BaseWorkspace):
    workspace_id = "ideas"
    workspace_title = "Идеи"

    def __init__(self, parent: QWidget | None = None) -> None:
        self._db = get_database()
        self._current_idea_id: Optional[int] = None
        self._current_project_id: Optional[int] = None
        self._dirty = False
        super().__init__(parent)
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

        splitter = QSplitter(Qt.Horizontal)
        splitter.setObjectName("IdeasSplitter")

        list_host = QWidget()
        list_layout = QVBoxLayout(list_host)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(6)

        self.list_view = QListView()
        self.list_view.setObjectName("IdeasList")
        self.list_view.setModel(IdeasListModel(self.list_view))
        self.list_view.setItemDelegate(IdeasDelegate(self.list_view))
        self.list_view.setSelectionMode(QListView.SingleSelection)
        self.list_view.selectionModel().selectionChanged.connect(self._on_selection_changed)
        self.list_view.doubleClicked.connect(self._open_selected)
        self.list_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_view.customContextMenuRequested.connect(self._show_context_menu)

        list_layout.addWidget(self.list_view, 1)
        splitter.addWidget(list_host)

        self.inspector_stack = QStackedWidget()
        self.inspector_empty = QLabel("Выберите идею слева")
        self.inspector_empty.setObjectName("IdeasEmpty")
        self.inspector_empty.setAlignment(Qt.AlignCenter)
        self.inspector_stack.addWidget(self.inspector_empty)

        self.inspector_tabs = QTabWidget()
        self.inspector_tabs.setObjectName("IdeasInspectorTabs")

        content_tab = QWidget()
        content_layout = QFormLayout(content_tab)
        content_layout.setLabelAlignment(Qt.AlignLeft)
        content_layout.setFormAlignment(Qt.AlignTop)
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
        self.save_button.clicked.connect(self._save_current)
        self.revert_button = QToolButton()
        self.revert_button.setText("Отменить")
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
        self.transform_task_btn.clicked.connect(lambda: self._transform_idea("task"))
        self.transform_note_btn = QToolButton()
        self.transform_note_btn.setText("📝 Создать заметку")
        self.transform_note_btn.clicked.connect(lambda: self._transform_idea("note"))
        self.transform_object_btn = QToolButton()
        self.transform_object_btn.setText("🧱 Создать объект")
        self.transform_object_btn.clicked.connect(lambda: self._transform_idea("object"))
        self.transform_marker_btn = QToolButton()
        self.transform_marker_btn.setText("🗺️ Создать метку")
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

    def create_actions(self) -> dict[str, QAction]:
        action_new = QAction("+ Идея", self)
        action_new.triggered.connect(self._create_idea)
        action_import = QAction("Импорт", self)
        action_import.triggered.connect(lambda: self._set_status("Импорт пока не реализован"))
        action_triage = QAction("Разобрать инбокс", self)
        action_triage.triggered.connect(lambda: self._set_status("Разбор инбокса пока не реализован"))
        action_archive = QAction("В архив", self)
        action_archive.triggered.connect(self._archive_selected)
        return {
            "new": action_new,
            "import": action_import,
            "triage": action_triage,
            "archive": action_archive,
        }

    def get_selection(self):
        index = self.list_view.currentIndex()
        if not index.isValid():
            return None
        return index.data(IdeaRoles.IdeaId)

    def _set_status(self, text: str) -> None:
        self.status_row.setText(text)

    def _mark_dirty(self) -> None:
        self._dirty = True

    def _on_status_filter_changed(self) -> None:
        self.set_filter("status", self.status_filter.currentData())

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
        if not index.isValid():
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

    def _set_combo_value(self, combo: QComboBox, value: str) -> None:
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
        if result == QDialog.Accepted:
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

    def _create_idea(self) -> None:
        idea = self._db.create_idea("Новая идея")
        self.refresh()
        self._current_idea_id = idea.id
        self._sync_selection()
        self._open_selected()

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
        if exec_with_overlay(dialog, self) != QDialog.Accepted:
            return
        self._db.delete_idea(idea_id)
        self._current_idea_id = None
        self._current_project_id = None
        self.refresh()
        self._set_status("Идея удалена")

    def _show_context_menu(self, pos) -> None:
        index = self.list_view.indexAt(pos)
        if not index.isValid():
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
            item.setFlags(Qt.NoItemFlags)
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
