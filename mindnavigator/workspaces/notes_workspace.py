"""Рабочая область заметок и быстрых записей.

Входные данные:
    Тексты заметок, фильтры и пользовательские события.

Выходные данные:
    Обновлённые заметки и визуальные карточки.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Any

import qtawesome as qta
from PySide6.QtCore import Qt, QSize, QRect, QAbstractListModel, QModelIndex, QTimer, QObject, Signal
from PySide6.QtGui import QPainter, QColor, QFont, QShortcut, QKeySequence
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QToolButton,
    QButtonGroup,
    QLineEdit,
    QListView,
    QStyledItemDelegate,
    QStyle,
    QAbstractItemView,
    QTextEdit,
    QMenu,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QStackedWidget,
)

from mindnavigator.storage import get_database
from mindnavigator.ui.smooth_scroll import attach_smooth_scroll

@dataclass(frozen=True)
class NoteItem:
    id: int
    title: str
    preview: str
    tags: List[str]
    updated: datetime
    project: str
    favorite: bool = False
    attachment: bool = False
    locked: bool = False


@dataclass
class NoteWorkspaceState:
    selected_note_id: Optional[int] = None
    filter_mode: str = "Все"
    search_text: str = ""
    project_filter: Optional[str] = None
    tag_filter: Optional[str] = None
    task_filter: Optional[int] = None


class NoteRoles:
    RowType = Qt.ItemDataRole.UserRole + 1
    NoteId = Qt.ItemDataRole.UserRole + 2
    Title = Qt.ItemDataRole.UserRole + 3
    Preview = Qt.ItemDataRole.UserRole + 4
    Tags = Qt.ItemDataRole.UserRole + 5
    Updated = Qt.ItemDataRole.UserRole + 6
    Project = Qt.ItemDataRole.UserRole + 7
    Favorite = Qt.ItemDataRole.UserRole + 8
    Attachment = Qt.ItemDataRole.UserRole + 9
    Locked = Qt.ItemDataRole.UserRole + 10


class NotesModel(QAbstractListModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._db = get_database()
        self._notes: List[NoteItem] = []
        self._rows: List[NoteItem] = []
        self._filter_mode = "Все"
        self._search = ""
        self._project_filter: Optional[str] = None
        self._tag_filter: Optional[str] = None
        self._task_filter_id: Optional[int] = None
        self._loading = True
        self._load_notes()

    def _load_notes(self):
        self._notes = [
            NoteItem(
                note.id,
                note.title,
                note.preview,
                note.tags,
                note.updated,
                note.project,
                favorite=note.favorite,
                attachment=note.attachment,
                locked=note.locked,
            )
            for note in self._db.fetch_notes()
        ]
        self._rebuild()

    def rowCount(self, parent=QModelIndex()) -> int:
        if parent.isValid():
            return 0
        if self._loading:
            return 6
        return len(self._rows)

    def data(self, index: QModelIndex, role: int = int(Qt.ItemDataRole.DisplayRole)) -> Any:
        if not index.isValid():
            return None
        if self._loading:
            if role == NoteRoles.RowType:
                return "skeleton"
            return None

        note = self._rows[index.row()]

        if role == NoteRoles.RowType:
            return "note"
        if role == NoteRoles.NoteId:
            return note.id
        if role == NoteRoles.Title:
            return note.title
        if role == NoteRoles.Preview:
            return note.preview
        if role == NoteRoles.Tags:
            return note.tags
        if role == NoteRoles.Updated:
            return note.updated
        if role == NoteRoles.Project:
            return note.project
        if role == NoteRoles.Favorite:
            return note.favorite
        if role == NoteRoles.Attachment:
            return note.attachment
        if role == NoteRoles.Locked:
            return note.locked
        if role == Qt.ItemDataRole.DisplayRole:
            return note.title
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if not index.isValid():
            return Qt.NoItemFlags
        if self._loading:
            return Qt.NoItemFlags
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def set_loading(self, loading: bool):
        if self._loading == loading:
            return
        self.beginResetModel()
        self._loading = loading
        self.endResetModel()

    def set_filter_mode(self, mode: str):
        self._filter_mode = mode
        self._rebuild()

    def set_search(self, text: str):
        self._search = (text or "").strip().lower()
        self._rebuild()

    def set_project_filter(self, project: Optional[str]):
        self._project_filter = project
        self._task_filter_id = None
        self._filter_mode = "По проекту" if project else self._filter_mode
        self._rebuild()

    def set_tag_filter(self, tag: Optional[str]):
        self._tag_filter = tag
        self._filter_mode = "По тегу" if tag else self._filter_mode
        self._rebuild()

    def set_task_filter(self, task_id: Optional[int]):
        self._task_filter_id = task_id
        self._project_filter = None
        if task_id is not None:
            self._filter_mode = "По задаче"
        self._rebuild()

    def add_note(self, note: NoteItem):
        self._notes.insert(0, note)
        self._rebuild()

    def update_note(self, note_id: int, title: str, preview: str, tags: List[str]):
        updated_note = self._db.update_note(note_id, title, preview, tags)
        self._notes = [
            NoteItem(
                item.id,
                updated_note.title if item.id == note_id else item.title,
                updated_note.preview if item.id == note_id else item.preview,
                updated_note.tags if item.id == note_id else item.tags,
                updated_note.updated if item.id == note_id else item.updated,
                updated_note.project if item.id == note_id else item.project,
                favorite=updated_note.favorite if item.id == note_id else item.favorite,
                attachment=updated_note.attachment if item.id == note_id else item.attachment,
                locked=updated_note.locked if item.id == note_id else item.locked,
            )
            for item in self._notes
        ]
        self._rebuild()

    def note_by_id(self, note_id: int) -> Optional[NoteItem]:
        for note in self._notes:
            if note.id == note_id:
                return note
        return None

    def toggle_favorite(self, note_id: int):
        updated_note = self._db.toggle_note_favorite(note_id)
        self._notes = [
            NoteItem(
                item.id,
                updated_note.title if item.id == note_id else item.title,
                updated_note.preview if item.id == note_id else item.preview,
                updated_note.tags if item.id == note_id else item.tags,
                updated_note.updated if item.id == note_id else item.updated,
                updated_note.project if item.id == note_id else item.project,
                favorite=updated_note.favorite if item.id == note_id else item.favorite,
                attachment=updated_note.attachment if item.id == note_id else item.attachment,
                locked=updated_note.locked if item.id == note_id else item.locked,
            )
            for item in self._notes
        ]
        self._rebuild()

    def create_note(
        self,
        title: str,
        preview: str,
        tags: List[str],
        project: str,
    ) -> NoteItem:
        created = self._db.create_note(title, preview, tags, project)
        note = NoteItem(
            created.id,
            created.title,
            created.preview,
            created.tags,
            created.updated,
            created.project,
            favorite=created.favorite,
            attachment=created.attachment,
            locked=created.locked,
        )
        self.add_note(note)
        return note

    def delete_note(self, note_id: int):
        self._db.delete_note(note_id)
        self._notes = [n for n in self._notes if n.id != note_id]
        self._rebuild()

    def _rebuild(self):
        if self._loading:
            self.beginResetModel()
            self._rows = []
            self.endResetModel()
            return

        notes = list(self._notes)

        if self._filter_mode == "Избранные":
            notes = [n for n in notes if n.favorite]
        elif self._filter_mode == "Последние":
            notes.sort(key=lambda n: n.updated, reverse=True)
            notes = notes[:12]
        elif self._filter_mode == "По задаче" and self._task_filter_id is not None:
            task_project = None
            for task in self._db.fetch_tasks():
                if task.id == self._task_filter_id:
                    task_project = task.project_title
                    break
            if task_project:
                notes = [n for n in notes if n.project == task_project]
            else:
                notes = []
        elif self._filter_mode == "По проекту" and self._project_filter:
            notes = [n for n in notes if n.project == self._project_filter]
        elif self._filter_mode == "По тегу" and self._tag_filter:
            notes = [n for n in notes if self._tag_filter in n.tags]

        if self._search:
            notes = [
                n
                for n in notes
                if self._search in n.title.lower()
                or self._search in n.preview.lower()
                or any(self._search in tag.lower() for tag in n.tags)
            ]

        notes.sort(key=lambda n: n.updated, reverse=True)
        self.beginResetModel()
        self._rows = notes
        self.endResetModel()


class NotesController(QObject):
    note_open_requested = Signal(int)

    def __init__(self, model: NotesModel, state: NoteWorkspaceState, parent=None):
        super().__init__(parent)
        self._model = model
        self._state = state
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setInterval(2000)
        self._autosave_timer.timeout.connect(self._autosave_stub)

    def initialize(self):
        self._model.set_loading(True)
        QTimer.singleShot(450, lambda: self._model.set_loading(False))

    def set_search(self, text: str):
        self._state.search_text = text
        self._model.set_search(text)

    def set_filter(self, mode: str):
        self._state.filter_mode = mode
        self._model.set_filter_mode(mode)

    def set_project_filter(self, project: Optional[str]):
        self._state.project_filter = project
        self._model.set_project_filter(project)

    def set_tag_filter(self, tag: Optional[str]):
        self._state.tag_filter = tag
        self._model.set_tag_filter(tag)

    def set_task_filter(self, task_id: Optional[int]):
        self._state.task_filter = task_id
        self._model.set_task_filter(task_id)

    def open_note(self, note_id: int):
        self._state.selected_note_id = note_id
        self.note_open_requested.emit(note_id)

    def create_note(self):
        note = self._model.create_note(
            "Новая заметка",
            "Краткое описание...",
            ["draft"],
            "Inbox",
        )
        self.open_note(note.id)

    def rename_note(self, note_id: int, title: str):
        note = self._model.note_by_id(note_id)
        if not note:
            return
        self._model.update_note(note_id, title, note.preview, note.tags)

    def toggle_favorite(self, note_id: int):
        self._model.toggle_favorite(note_id)

    def delete_note(self, note_id: int):
        self._model.delete_note(note_id)
        if self._state.selected_note_id == note_id:
            self._state.selected_note_id = None

    def start_autosave(self):
        if not self._autosave_timer.isActive():
            self._autosave_timer.start()

    def stop_autosave(self):
        if self._autosave_timer.isActive():
            self._autosave_timer.stop()

    def _autosave_stub(self):
        # TODO: интеграция с FastAPI/SQLite синхронизацией.
        pass


class NoteCardDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._card_radius = 12

    def paint(self, painter: QPainter, option, index):
        row_type = index.data(NoteRoles.RowType)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = option.rect.adjusted(6, 6, -6, -6)
        if row_type == "skeleton":
            self._paint_skeleton(painter, rect)
            painter.restore()
            return

        is_selected = option.state & QStyle.StateFlag.State_Selected
        is_hover = option.state & QStyle.StateFlag.State_MouseOver

        bg = QColor("#1b1d22")
        border = QColor("#2b2f36")
        if is_selected:
            border = QColor("#3b82f6")
        elif is_hover:
            border = QColor("#3a3f47")

        painter.setBrush(bg)
        painter.setPen(border)
        painter.drawRoundedRect(rect, self._card_radius, self._card_radius)

        title = index.data(NoteRoles.Title) or ""
        preview = index.data(NoteRoles.Preview) or ""
        tags = index.data(NoteRoles.Tags) or []
        updated = index.data(NoteRoles.Updated)
        project = index.data(NoteRoles.Project) or ""

        title_rect = QRect(rect.left() + 14, rect.top() + 12, rect.width() - 28, 24)
        preview_rect = QRect(rect.left() + 14, rect.top() + 38, rect.width() - 28, 52)
        tags_rect = QRect(rect.left() + 14, rect.bottom() - 50, rect.width() - 28, 20)
        meta_rect = QRect(rect.left() + 14, rect.bottom() - 28, rect.width() - 28, 18)

        painter.setPen(QColor("#e6e6e6"))
        title_font = QFont()
        title_font.setPointSize(10)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.drawText(title_rect, Qt.TextFlag.TextSingleLine, title)

        painter.setPen(QColor("#a0a3a8"))
        preview_font = QFont()
        preview_font.setPointSize(9)
        painter.setFont(preview_font)
        painter.drawText(preview_rect, Qt.TextFlag.TextWordWrap, preview)

        painter.setPen(QColor("#7d828a"))
        tag_font = QFont()
        tag_font.setPointSize(8)
        painter.setFont(tag_font)
        painter.drawText(tags_rect, Qt.TextFlag.TextSingleLine, "  ".join(f"#{t}" for t in tags[:3]))

        painter.setPen(QColor("#6b7078"))
        meta_font = QFont()
        meta_font.setPointSize(8)
        painter.setFont(meta_font)
        meta_text = project
        if isinstance(updated, datetime):
            meta_text = f"{project} · {updated:%d %b %H:%M}"
        painter.drawText(meta_rect, Qt.TextFlag.TextSingleLine, meta_text)

        icon_y = rect.top() + 12
        icon_x = rect.right() - 18
        painter.setPen(Qt.NoPen)

        if index.data(NoteRoles.Locked):
            qta.icon("fa5s.lock", color="#8b8f96").paint(painter, QRect(icon_x, icon_y, 14, 14))
            icon_x -= 18
        if index.data(NoteRoles.Attachment):
            qta.icon("fa5s.paperclip", color="#8b8f96").paint(painter, QRect(icon_x, icon_y, 14, 14))
            icon_x -= 18
        if index.data(NoteRoles.Favorite):
            qta.icon("fa5s.star", color="#f4c560").paint(painter, QRect(icon_x, icon_y, 14, 14))

        painter.restore()

    def _paint_skeleton(self, painter: QPainter, rect: QRect):
        painter.setPen(QColor("#24272e"))
        painter.setBrush(QColor("#20232a"))
        painter.drawRoundedRect(rect, self._card_radius, self._card_radius)

        painter.setBrush(QColor("#2a2e36"))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(QRect(rect.left() + 14, rect.top() + 14, rect.width() - 60, 12), 6, 6)
        painter.drawRoundedRect(QRect(rect.left() + 14, rect.top() + 40, rect.width() - 30, 10), 6, 6)
        painter.drawRoundedRect(QRect(rect.left() + 14, rect.top() + 58, rect.width() - 40, 10), 6, 6)
        painter.drawRoundedRect(QRect(rect.left() + 14, rect.bottom() - 32, rect.width() - 80, 10), 6, 6)

    def sizeHint(self, option, index):
        return QSize(260, 170)


class NoteWorkspace(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("NotesWorkspace")
        self._state = NoteWorkspaceState()
        self._smooth_scroll_controllers: list[object] = []

        self._build_ui()
        self._wire_logic()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        header = QFrame()
        header.setObjectName("NotesHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(10, 8, 10, 8)
        header_layout.setSpacing(8)

        self.btn_toggle_left = QToolButton()
        self.btn_toggle_left.setIcon(qta.icon("fa5s.columns", color="#cfcfcf"))
        self.btn_toggle_left.setAutoRaise(True)
        self.btn_toggle_left.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_toggle_right = QToolButton()
        self.btn_toggle_right.setIcon(qta.icon("fa5s.align-right", color="#cfcfcf"))
        self.btn_toggle_right.setAutoRaise(True)
        self.btn_toggle_right.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_zen = QToolButton()
        self.btn_zen.setIcon(qta.icon("fa5s.eye", color="#cfcfcf"))
        self.btn_zen.setAutoRaise(True)
        self.btn_zen.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_zen.setCheckable(True)

        header_layout.addWidget(self.btn_toggle_left)
        header_layout.addWidget(self.btn_toggle_right)
        header_layout.addWidget(self.btn_zen)
        header_layout.addStretch(1)

        header_title = QLabel("Note Workspace")
        header_title.setObjectName("NotesHeaderTitle")
        header_layout.addWidget(header_title)
        header_layout.addStretch(1)

        self.btn_new_note = QToolButton()
        self.btn_new_note.setIcon(qta.icon("fa5s.plus", color="#ffffff"))
        self.btn_new_note.setText("Новая")
        self.btn_new_note.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.btn_new_note.setCursor(Qt.CursorShape.PointingHandCursor)

        header_layout.addWidget(self.btn_new_note)
        root.addWidget(header)

        self.splitter = QSplitter()
        self.splitter.setObjectName("NotesSplitter")
        self.splitter.setChildrenCollapsible(False)
        root.addWidget(self.splitter, 1)

        self.nav_panel = self._build_nav_panel()
        self.list_panel = self._build_list_panel()
        self.editor_panel = self._build_editor_panel()

        self.splitter.addWidget(self.nav_panel)
        self.splitter.addWidget(self.list_panel)
        self.splitter.addWidget(self.editor_panel)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setStretchFactor(2, 1)
        self.splitter.setSizes([240, 520, 420])

        self.setStyleSheet("""
            QWidget#NotesWorkspace { background: #16171a; }

            QFrame#NotesHeader {
                background: #1b1c1f;
                border: 1px solid #2a2b2f;
                border-radius: 10px;
            }

            QLabel#NotesHeaderTitle {
                color: #d7d7d7;
                font-size: 12px;
                letter-spacing: 0.6px;
            }

            QToolButton {
                background: transparent;
                border: none;
                color: #cfcfcf;
                padding: 4px 8px;
            }

            QToolButton:checked {
                color: #ffffff;
                background: #20242b;
                border-radius: 6px;
            }

            QFrame#NotesNavPanel,
            QFrame#NotesListPanel,
            QFrame#NotesEditorPanel {
                background: #1a1c20;
                border: 1px solid #2a2b2f;
                border-radius: 12px;
            }

            QLineEdit {
                background: #131417;
                border: 1px solid #2a2b2f;
                padding: 6px 8px;
                color: #e6e6e6;
                border-radius: 8px;
            }

            QTextEdit {
                background: #131417;
                border: 1px solid #2a2b2f;
                color: #e6e6e6;
                padding: 10px;
                border-radius: 10px;
            }

            QListView#NotesGrid {
                background: transparent;
                outline: none;
            }

            QTreeWidget {
                background: transparent;
                border: none;
                color: #b5b9c0;
            }

            QTreeWidget::item:selected {
                background: #20242b;
                color: #ffffff;
                border-radius: 6px;
            }
        """)

    def _build_nav_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("NotesNavPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        title = QLabel("Навигация")
        title.setStyleSheet("color:#c7cbd3; font-size:12px; font-weight:600;")
        layout.addWidget(title)

        self.nav_search = QLineEdit()
        self.nav_search.setPlaceholderText("Поиск заметок…")
        layout.addWidget(self.nav_search)

        filters = QFrame()
        filters_layout = QVBoxLayout(filters)
        filters_layout.setContentsMargins(0, 0, 0, 0)
        filters_layout.setSpacing(6)

        self.filters_group = QButtonGroup(self)
        self.filters_group.setExclusive(True)

        def filter_btn(text: str) -> QToolButton:
            btn = QToolButton()
            btn.setText(text)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setAutoRaise(True)
            btn.setToolButtonStyle(Qt.ToolButtonTextOnly)
            self.filters_group.addButton(btn)
            return btn

        self.btn_filter_all = filter_btn("Все")
        self.btn_filter_fav = filter_btn("Избранные ⭐")
        self.btn_filter_recent = filter_btn("Последние")
        self.btn_filter_project = filter_btn("По проекту")
        self.btn_filter_tag = filter_btn("По тегу")
        self.btn_filter_all.setChecked(True)

        filters_layout.addWidget(self.btn_filter_all)
        filters_layout.addWidget(self.btn_filter_fav)
        filters_layout.addWidget(self.btn_filter_recent)
        filters_layout.addWidget(self.btn_filter_project)
        filters_layout.addWidget(self.btn_filter_tag)
        layout.addWidget(filters)

        tree_label = QLabel("Структура")
        tree_label.setStyleSheet("color:#8c9097; font-size:11px;")
        layout.addWidget(tree_label)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(14)
        self.tree.setAnimated(True)
        self.tree.setDragDropMode(QAbstractItemView.NoDragDrop)
        # TODO: поддержка drag & drop для вложенности и перемещения заметок.

        projects = QTreeWidgetItem(["Проекты"])
        projects.setExpanded(True)
        for name in ["MindNavigator", "Discovery", "Design", "Platform", "Delivery"]:
            projects.addChild(QTreeWidgetItem([name]))

        tags = QTreeWidgetItem(["Теги"])
        tags.setExpanded(True)
        for name in ["product", "ux", "backend", "sync", "release"]:
            tags.addChild(QTreeWidgetItem([f"#{name}"]))

        self.tree.addTopLevelItem(projects)
        self.tree.addTopLevelItem(tags)
        layout.addWidget(self.tree, 1)

        quick = QFrame()
        quick_layout = QHBoxLayout(quick)
        quick_layout.setContentsMargins(0, 0, 0, 0)
        quick_layout.setSpacing(6)
        quick_label = QLabel("Быстрые действия")
        quick_label.setStyleSheet("color:#8c9097; font-size:11px;")
        quick_layout.addWidget(quick_label)
        quick_layout.addStretch(1)
        quick_btn = QToolButton()
        quick_btn.setIcon(qta.icon("fa5s.plus", color="#cfcfcf"))
        quick_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        quick_btn.setAutoRaise(True)
        self.quick_new_btn = quick_btn
        quick_layout.addWidget(quick_btn)
        layout.addWidget(quick)

        return panel

    def _build_list_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("NotesListPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        header = QFrame()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        self.list_title = QLabel("Заметки")
        self.list_title.setStyleSheet("color:#c7cbd3; font-size:12px; font-weight:600;")
        header_layout.addWidget(self.list_title)
        header_layout.addStretch(1)

        self.list_hint = QLabel("Grid view")
        self.list_hint.setStyleSheet("color:#6e727a; font-size:10px;")
        header_layout.addWidget(self.list_hint)
        layout.addWidget(header)

        self.list_view = QListView()
        self.list_view.setObjectName("NotesGrid")
        self.list_view.setViewMode(QListView.IconMode)
        self.list_view.setResizeMode(QListView.Adjust)
        self.list_view.setSpacing(12)
        self.list_view.setUniformItemSizes(True)
        self.list_view.setWordWrap(True)
        self.list_view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.list_view.setVerticalScrollMode(QListView.ScrollPerPixel)
        self.list_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_view.setMouseTracking(True)
        self.list_view.setContextMenuPolicy(Qt.CustomContextMenu)

        layout.addWidget(self.list_view, 1)

        self.empty_state = QFrame()
        empty_layout = QVBoxLayout(self.empty_state)
        empty_layout.setContentsMargins(0, 0, 0, 0)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_title = QLabel("Нет заметок")
        empty_title.setStyleSheet("color:#c7cbd3; font-size:14px; font-weight:600;")
        empty_desc = QLabel(
            "Создайте заметку через + или используйте поиск, чтобы быстро найти нужное."
        )
        empty_desc.setStyleSheet("color:#7b7f86; font-size:11px;")
        empty_desc.setWordWrap(True)
        empty_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_desc.setMaximumWidth(220)
        empty_layout.addWidget(empty_title)
        empty_layout.addWidget(empty_desc)
        layout.addWidget(self.empty_state)
        self.empty_state.hide()

        return panel

    def _build_editor_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("NotesEditorPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self.editor_stack = QStackedWidget()
        layout.addWidget(self.editor_stack, 1)

        empty = QFrame()
        empty_layout = QVBoxLayout(empty)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_title = QLabel("Выберите заметку")
        empty_title.setStyleSheet("color:#c7cbd3; font-size:14px; font-weight:600;")
        empty_hint = QLabel(
            "Создайте новую заметку или выберите карточку слева. Zen-mode скрывает навигацию и список."
        )
        empty_hint.setStyleSheet("color:#7b7f86; font-size:11px;")
        empty_hint.setWordWrap(True)
        empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_hint.setMaximumWidth(260)
        empty_layout.addWidget(empty_title)
        empty_layout.addWidget(empty_hint)

        editor = QFrame()
        editor_layout = QVBoxLayout(editor)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.setSpacing(8)

        breadcrumbs = QLabel("Проект → Заметка")
        breadcrumbs.setStyleSheet("color:#7b7f86; font-size:10px;")
        self.breadcrumbs_label = breadcrumbs
        editor_layout.addWidget(breadcrumbs)

        title_row = QHBoxLayout()
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Заголовок заметки")
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("Теги: #ux #sync")
        self.tags_edit.setFixedWidth(180)
        title_row.addWidget(self.title_edit, 1)
        title_row.addWidget(self.tags_edit)
        editor_layout.addLayout(title_row)

        self.editor = QTextEdit()
        self.editor.setPlaceholderText(
            "Markdown (подготовка)\n- чекбоксы\n- ссылки [[note]]\n- code block"
        )
        editor_layout.addWidget(self.editor, 1)

        status_row = QHBoxLayout()
        self.autosave_label = QLabel("Автосохранение: включено")
        self.autosave_label.setStyleSheet("color:#6e727a; font-size:10px;")
        status_row.addWidget(self.autosave_label)
        status_row.addStretch(1)
        editor_layout.addLayout(status_row)

        self.editor_stack.addWidget(empty)
        self.editor_stack.addWidget(editor)

        return panel

    def _wire_logic(self):
        self.model = NotesModel(self)
        self.controller = NotesController(self.model, self._state, self)
        self.controller.note_open_requested.connect(self._load_note_into_editor)

        self.list_view.setModel(self.model)
        self.list_view.setItemDelegate(NoteCardDelegate(self.list_view))
        self._smooth_scroll_controllers = [
            attach_smooth_scroll(self.tree),
            attach_smooth_scroll(self.list_view),
            attach_smooth_scroll(self.editor),
        ]

        self.filters_group.buttonClicked.connect(self._on_filter_changed)

        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(250)
        self.nav_search.textChanged.connect(self._on_search_changed)
        self.search_timer.timeout.connect(self._apply_search)

        self.tree.itemClicked.connect(self._on_tree_item_clicked)
        self.list_view.customContextMenuRequested.connect(self._open_context_menu)
        self.list_view.clicked.connect(self._on_note_clicked)

        self.btn_new_note.clicked.connect(self.controller.create_note)
        self.quick_new_btn.clicked.connect(self.controller.create_note)

        self.btn_toggle_left.clicked.connect(self._toggle_left_panel)
        self.btn_toggle_right.clicked.connect(self._toggle_right_panel)
        self.btn_zen.toggled.connect(self._toggle_zen_mode)

        QShortcut(QKeySequence("Ctrl+N"), self, self.controller.create_note)
        QShortcut(QKeySequence("Ctrl+F"), self, self.nav_search.setFocus)
        QShortcut(QKeySequence("Ctrl+S"), self, self._manual_save)

        self.title_edit.textChanged.connect(self._update_note_title)
        self.tags_edit.textChanged.connect(self._update_note_tags)
        self.editor.textChanged.connect(self._update_note_body)

        self.controller.initialize()
        self.controller.start_autosave()

    def set_project_filter(self, project: Optional[str]) -> None:
        """Устанавливает фильтр по проекту из внешней навигации."""
        self.controller.set_project_filter(project)
        self._refresh_empty_state()

    def set_task_filter(self, task_id: Optional[int]) -> None:
        """Устанавливает фильтр по задаче из внешней навигации."""
        self.controller.set_task_filter(task_id)
        self._refresh_empty_state()

    def _on_filter_changed(self):
        btn = self.filters_group.checkedButton()
        if not btn:
            return
        self.controller.set_filter(btn.text().replace(" ⭐", ""))
        self._refresh_empty_state()

    def _on_search_changed(self):
        self.search_timer.start()

    def _apply_search(self):
        self.controller.set_search(self.nav_search.text())
        self._refresh_empty_state()

    def _on_tree_item_clicked(self, item: QTreeWidgetItem, column: int):
        text = item.text(column)
        parent = item.parent()
        if not parent:
            return
        if parent.text(0) == "Проекты":
            self.controller.set_project_filter(text)
            self.btn_filter_project.setChecked(True)
        if parent.text(0) == "Теги":
            tag = text.lstrip("#")
            self.controller.set_tag_filter(tag)
            self.btn_filter_tag.setChecked(True)
        self._refresh_empty_state()

    def _open_context_menu(self, point):
        index = self.list_view.indexAt(point)
        if not index.isValid() or index.data(NoteRoles.RowType) != "note":
            return
        note_id = index.data(NoteRoles.NoteId)
        menu = QMenu(self)
        open_action = menu.addAction("Открыть")
        rename_action = menu.addAction("Переименовать")
        fav_action = menu.addAction("В избранное")
        delete_action = menu.addAction("Удалить")

        action = menu.exec(self.list_view.mapToGlobal(point))
        if action == open_action:
            self.controller.open_note(note_id)
        elif action == rename_action:
            self.title_edit.setFocus()
        elif action == fav_action:
            self.controller.toggle_favorite(note_id)
        elif action == delete_action:
            self.controller.delete_note(note_id)
            self._refresh_empty_state()

    def _on_note_clicked(self, index: QModelIndex):
        if index.data(NoteRoles.RowType) != "note":
            return
        note_id = index.data(NoteRoles.NoteId)
        self.controller.open_note(note_id)

    def _load_note_into_editor(self, note_id: int):
        note = self.model.note_by_id(note_id)
        if not note:
            self.editor_stack.setCurrentIndex(0)
            return
        self.editor_stack.setCurrentIndex(1)
        self.title_edit.blockSignals(True)
        self.tags_edit.blockSignals(True)
        self.editor.blockSignals(True)

        self.breadcrumbs_label.setText(f"{note.project} → {note.title}")
        self.title_edit.setText(note.title)
        self.tags_edit.setText(" ".join(f"#{t}" for t in note.tags))
        self.editor.setPlainText(note.preview)

        self.title_edit.blockSignals(False)
        self.tags_edit.blockSignals(False)
        self.editor.blockSignals(False)

    def _update_note_title(self):
        if not self._state.selected_note_id:
            return
        self.controller.rename_note(self._state.selected_note_id, self.title_edit.text())

    def _update_note_tags(self):
        if not self._state.selected_note_id:
            return
        tags = [tag.strip("#") for tag in self.tags_edit.text().split() if tag.strip()]
        note = self.model.note_by_id(self._state.selected_note_id)
        if not note:
            return
        self.model.update_note(self._state.selected_note_id, note.title, note.preview, tags)

    def _update_note_body(self):
        if not self._state.selected_note_id:
            return
        note = self.model.note_by_id(self._state.selected_note_id)
        if not note:
            return
        preview = self.editor.toPlainText().strip()
        if preview:
            preview = preview.split("\n", 1)[0][:140]
        self.model.update_note(self._state.selected_note_id, note.title, preview, note.tags)

    def _toggle_left_panel(self):
        self.nav_panel.setVisible(not self.nav_panel.isVisible())

    def _toggle_right_panel(self):
        self.editor_panel.setVisible(not self.editor_panel.isVisible())

    def _toggle_zen_mode(self, enabled: bool):
        if enabled:
            self.nav_panel.hide()
            self.list_panel.hide()
        else:
            self.nav_panel.show()
            self.list_panel.show()

    def _manual_save(self):
        self.autosave_label.setText("Автосохранение: сохранено")

    def _refresh_empty_state(self):
        if self.model.rowCount() == 0 and not self.model._loading:
            self.empty_state.show()
        else:
            self.empty_state.hide()
