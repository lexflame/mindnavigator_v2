"""Рабочая область управления проектами.

Входные данные:
    Данные проектов и фильтры пользовательского интерфейса.

Выходные данные:
    Обновлённые записи проектов и визуальные карточки.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import List, Union, Optional

import qtawesome as qta
from PySide6.QtCore import Qt, QSize, QRect, QAbstractListModel, QModelIndex, QEvent, QDate
from PySide6.QtGui import QPainter, QColor, QFont, QFontMetrics, QCursor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QToolButton, QButtonGroup,
    QComboBox, QLineEdit, QListView, QMenu, QStyledItemDelegate, QStyle, QDialog,
    QDialogButtonBox, QFormLayout, QMessageBox, QDateEdit, QCheckBox
)

from mindnavigator.storage import (
    format_project_date,
    get_database,
    normalize_priority,
    validate_area,
    validate_title,
)
from mindnavigator.ui.modals import ConfirmDialog, exec_with_overlay, show_dialog_standard
from mindnavigator.ui.styles import MATH_PHYS_BACKGROUND

# ProjectsWorkspace — UI-близнец TasksWorkspace:
# - та же структура верхней панели
# - тот же подход к группировке (заголовки + строки)
# - QListView + делегат ради скорости


@dataclass(frozen=True)
class ProjectRow:
    id: int
    area: str               # group header key
    title: str
    updated: date
    priority: str           # Low | Medium | High
    archived: bool


@dataclass(frozen=True)
class HeaderRow:
    area: str


Row = Union[ProjectRow, HeaderRow]


class ProjectRoles:
    RowType = Qt.UserRole + 1   # header | project
    Area = Qt.UserRole + 2
    Title = Qt.UserRole + 3
    Updated = Qt.UserRole + 4
    Priority = Qt.UserRole + 5
    Archived = Qt.UserRole + 6
    ProjectId = Qt.UserRole + 7
    UpdatedDate = Qt.UserRole + 8


class ProjectsModel(QAbstractListModel):
    def __init__(self, parent=None):
        """Создает модель данных проектов."""
        super().__init__(parent)
        self._db = get_database()
        self._all_rows: List[Row] = []
        self._rows: List[Row] = []
        self._filter_mode = "Все"      # Все | Активные | Архив
        self._search = ""
        self._area_focus: Optional[str] = None
        self._task_filter_id: Optional[int] = None
        self._reload_from_db()

    def _reload_from_db(self):
        """Обновляет список проектов из базы данных."""
        projects = self._db.fetch_projects()
        self._all_rows = [
            ProjectRow(
                p.id,
                p.area,
                p.title,
                p.updated,
                p.priority,
                p.archived,
            )
            for p in projects
        ]
        self._rebuild()

    def refresh(self) -> None:
        """Перезагружает данные проектов из базы."""
        self._reload_from_db()

    def rowCount(self, parent=QModelIndex()) -> int:
        """Возвращает количество строк в модели."""
        if parent.isValid():
            return 0
        return len(self._rows)

    def data(self, index: QModelIndex, role: int):
        """Отдает данные для делегата по ролям."""
        if not index.isValid():
            return None
        r = self._rows[index.row()]

        if role == ProjectRoles.RowType:
            return "header" if isinstance(r, HeaderRow) else "project"

        if isinstance(r, HeaderRow):
            if role == ProjectRoles.Area:
                return r.area
            if role == Qt.DisplayRole:
                return r.area
            return None

        if role == ProjectRoles.ProjectId:
            return r.id
        if role == ProjectRoles.Area:
            return r.area
        if role == ProjectRoles.Title:
            return r.title
        if role == ProjectRoles.Updated:
            return format_project_date(r.updated)
        if role == ProjectRoles.UpdatedDate:
            return r.updated
        if role == ProjectRoles.Priority:
            return r.priority
        if role == ProjectRoles.Archived:
            return r.archived
        if role == Qt.DisplayRole:
            return r.title
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        """Устанавливает флаги взаимодействия для строки."""
        if not index.isValid():
            return Qt.NoItemFlags
        r = self._rows[index.row()]
        if isinstance(r, HeaderRow):
            return Qt.ItemIsEnabled
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def set_filter_mode(self, mode: str):
        """Обновляет режим фильтрации."""
        self._filter_mode = mode
        self._rebuild()

    def set_search(self, text: str):
        """Устанавливает строку поиска."""
        self._search = (text or "").strip().lower()
        self._rebuild()

    def set_area_focus(self, area: Optional[str]):
        """Фиксирует активную область проектов."""
        self._area_focus = area
        self._rebuild()

    def set_task_filter(self, task_id: Optional[int]):
        """Фильтрует проекты по выбранной задаче."""
        self._task_filter_id = task_id
        self._rebuild()

    def add_project(self, area: str, title: str, updated: date, priority: str, archived: bool):
        """Добавляет новый проект и пересобирает список."""
        project = self._db.create_project(area=area, title=title, updated=updated, priority=priority, archived=archived)
        self._all_rows.append(
            ProjectRow(project.id, project.area, project.title, project.updated, project.priority, project.archived)
        )
        self._rebuild()

    def area_has_active(self, area: str) -> bool:
        """Проверяет наличие активных проектов в области."""
        return any(
            isinstance(it, ProjectRow) and it.area == area and not it.archived
            for it in self._all_rows
        )

    def set_area_archived(self, area: str, archived: bool):
        """Архивирует или восстанавливает все проекты области."""
        self._db.set_projects_archived_for_area(area, archived)
        new_all: List[Row] = []
        for it in self._all_rows:
            if isinstance(it, ProjectRow) and it.area == area:
                it = ProjectRow(it.id, it.area, it.title, it.updated, it.priority, archived)
            new_all.append(it)
        self._all_rows = new_all
        self._rebuild()

    def delete_area(self, area: str):
        """Удаляет все проекты в области."""
        self._db.delete_projects_by_area(area)
        self._all_rows = [
            it for it in self._all_rows if not (isinstance(it, ProjectRow) and it.area == area)
        ]
        if self._area_focus == area:
            self._area_focus = None
        self._rebuild()

    def rename_area(self, area: str, new_area: str):
        """Переименовывает область проектов."""
        self._db.rename_project_area(area, new_area)
        new_all: List[Row] = []
        for it in self._all_rows:
            if isinstance(it, ProjectRow) and it.area == area:
                it = ProjectRow(it.id, new_area, it.title, it.updated, it.priority, it.archived)
            new_all.append(it)
        self._all_rows = new_all
        if self._area_focus == area:
            self._area_focus = new_area
        self._rebuild()

    def project_at_row(self, row_idx: int) -> Optional[ProjectRow]:
        """Возвращает проект по индексу строки или None."""
        if row_idx < 0 or row_idx >= len(self._rows):
            return None
        r = self._rows[row_idx]
        if isinstance(r, HeaderRow):
            return None
        return r

    def update_project_by_row(
        self,
        row_idx: int,
        area: str,
        title: str,
        updated: date,
        priority: str,
        archived: bool,
    ):
        """Обновляет проект по индексу строки."""
        r = self.project_at_row(row_idx)
        if r is None:
            return
        updated_project = self._db.update_project(
            project_id=r.id,
            area=area,
            title=title,
            updated=updated,
            priority=priority,
            archived=archived,
        )

        new_all: List[Row] = []
        for it in self._all_rows:
            if isinstance(it, ProjectRow) and it.id == r.id:
                it = ProjectRow(
                    updated_project.id,
                    updated_project.area,
                    updated_project.title,
                    updated_project.updated,
                    updated_project.priority,
                    updated_project.archived,
                )
            new_all.append(it)

        self._all_rows = new_all
        self._rebuild()

    def toggle_archive_by_row(self, row_idx: int):
        """Переключает архивный статус проекта по строке."""
        if row_idx < 0 or row_idx >= len(self._rows):
            return
        r = self._rows[row_idx]
        if isinstance(r, HeaderRow):
            return

        new_archived = not r.archived
        self._db.set_project_archived(r.id, new_archived)
        new_all: List[Row] = []
        for it in self._all_rows:
            if isinstance(it, ProjectRow) and it.id == r.id:
                it = ProjectRow(it.id, it.area, it.title, it.updated, it.priority, new_archived)
            new_all.append(it)

        self._all_rows = new_all
        self._rebuild()

    def delete_project_by_row(self, row_idx: int):
        """Удаляет проект по индексу строки."""
        r = self.project_at_row(row_idx)
        if r is None:
            return
        self._db.delete_project(r.id)
        self._all_rows = [it for it in self._all_rows if not (isinstance(it, ProjectRow) and it.id == r.id)]
        self._rebuild()

    def _rebuild(self):
        """Пересобирает список проектов с учетом фильтров."""
        search = self._search
        task_project_id = None
        if self._task_filter_id is not None:
            for task in self._db.fetch_tasks():
                if task.id == self._task_filter_id:
                    task_project_id = task.project_id
                    break

        projects: List[ProjectRow] = []
        for it in self._all_rows:
            if not isinstance(it, ProjectRow):
                continue

            if self._task_filter_id is not None:
                if task_project_id is None or it.id != task_project_id:
                    continue

            if self._area_focus is not None and it.area != self._area_focus:
                continue

            if self._filter_mode in ("Все", "Активные") and it.archived:
                continue
            if self._filter_mode == "Архив" and not it.archived:
                continue

            if search and search not in it.title.lower():
                continue

            projects.append(it)

        priority_order = {"High": 0, "Medium": 1, "Low": 2, "Отложенная": 3}

        def priority_key(priority: str) -> int:
            return priority_order[normalize_priority(priority)]

        projects.sort(key=lambda x: (x.area.lower(), priority_key(x.priority), x.title.lower(), x.id))

        new_rows: List[Row] = []
        cur: Optional[str] = None
        for p in projects:
            if cur != p.area:
                cur = p.area
                new_rows.append(HeaderRow(cur))
            new_rows.append(p)

        self.beginResetModel()
        self._rows = new_rows
        self.endResetModel()


class ProjectsItemDelegate(QStyledItemDelegate):
    ROW_H = 42
    HEADER_H = 32

    C_BG = QColor("#16171a")
    C_ROW = QColor("#2a2d33")
    C_ROW_ALT = QColor("#2c2f36")
    C_BORDER = QColor("#3a3b40")
    C_TEXT = QColor("#cfcfcf")
    C_DIM = QColor("#8a8a8a")

    C_ARCH = QColor("#6f7a87")
    C_HIGH = QColor("#d94f4f")
    C_MED = QColor("#d0a93e")
    C_LOW = QColor("#4caf50")
    C_DEFER = QColor("#6f7a87")

    def __init__(self, parent=None):
        """Инициализирует делегат отрисовки проектов."""
        super().__init__(parent)
        self._icon_folder = qta.icon("fa5s.folder-open", color="#cfcfcf")
        self._icon_grip = qta.icon("fa5s.grip-lines", color="#8a8a8a")
        self._icon_menu = qta.icon("fa5s.ellipsis-v", color="#cfcfcf")
        self._icon_pin = qta.icon("fa5s.thumbtack", color="#d0a93e")

        self._font = QFont()
        self._font.setPointSize(10)

        self._font_small = QFont()
        self._font_small.setPointSize(9)

        self._font_header = QFont()
        self._font_header.setPointSize(9)
        self._font_header.setBold(True)

    def sizeHint(self, option, index):
        """Возвращает размер строки списка."""
        row_type = index.data(ProjectRoles.RowType)
        if row_type == "header":
            return QSize(option.rect.width(), self.HEADER_H)
        return QSize(option.rect.width(), self.ROW_H)

    def paint(self, painter: QPainter, option, index: QModelIndex):
        """Рисует строку проекта или заголовок области."""
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, False)

        row_type = index.data(ProjectRoles.RowType)
        r = option.rect

        if row_type == "header":
            area: str = index.data(ProjectRoles.Area) or ""
            painter.fillRect(r, self.C_BG)
            painter.setPen(self.C_DIM)
            painter.setFont(self._font_header)
            left_pad = 10
            menu_w = 24
            menu_rect = QRect(r.left() + left_pad, r.top() + 4, menu_w, r.height() - 8)
            text_rect = QRect(menu_rect.right() + 8, r.top(), r.right() - menu_rect.right() - 18, r.height())
            painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, area)
            painter.setPen(self.C_BORDER)
            painter.drawLine(r.left() + 10, r.bottom(), r.right() - 10, r.bottom())
            painter.setPen(self.C_BORDER)
            painter.setBrush(QColor("#1f2227"))
            painter.drawRect(menu_rect)
            self._icon_menu.paint(
                painter,
                QRect(menu_rect.center().x() - 7, menu_rect.center().y() - 7, 14, 14),
            )
            painter.restore()
            return

        title: str = index.data(ProjectRoles.Title) or ""
        updated: str = index.data(ProjectRoles.Updated) or ""
        priority: str = index.data(ProjectRoles.Priority) or "Medium"
        archived: bool = bool(index.data(ProjectRoles.Archived))

        bg = self.C_ROW if (index.row() % 2 == 0) else self.C_ROW_ALT
        if option.state & QStyle.State_Selected:
            bg = QColor("#343844")

        painter.fillRect(r, bg)
        painter.setPen(self.C_BORDER)
        painter.drawRect(r.adjusted(0, 0, -1, -1))

        x = r.left() + 10
        cy = r.center().y()

        grip_rect = QRect(x, cy - 8, 16, 16)
        self._icon_grip.paint(painter, grip_rect)
        x += 22

        # archive checkbox-like indicator
        box_rect = QRect(x, cy - 7, 14, 14)
        painter.setPen(self.C_BORDER)
        painter.setBrush(QColor("#16171a"))
        painter.drawRect(box_rect)

        if archived:
            painter.setPen(QColor("#cfcfcf"))
            painter.drawLine(box_rect.left() + 3, box_rect.center().y(),
                             box_rect.center().x() - 1, box_rect.bottom() - 3)
            painter.drawLine(box_rect.center().x() - 1, box_rect.bottom() - 3,
                             box_rect.right() - 2, box_rect.top() + 3)

        x += 22

        icon_rect = QRect(x, cy - 8, 16, 16)
        self._icon_folder.paint(painter, icon_rect)
        x += 22

        painter.setFont(self._font)
        painter.setPen(self.C_TEXT if not archived else self.C_DIM)

        right_pad = 18
        menu_w = 30
        pr_w = 160
        menu_rect = QRect(r.right() - right_pad - menu_w, r.top() + 6, menu_w, r.height() - 12)
        pr_rect = QRect(menu_rect.left() - pr_w - 8, r.top(), pr_w, r.height())

        title_rect = QRect(x, r.top(), pr_rect.left() - x - 10, r.height())
        elided = QFontMetrics(self._font).elidedText(title, Qt.ElideRight, title_rect.width())
        painter.drawText(title_rect, Qt.AlignVCenter | Qt.AlignLeft, elided)

        pr_color = self.C_ARCH if archived else self._prio_color(priority)
        painter.setFont(self._font_small)
        painter.setPen(pr_color)

        priority_w = 60
        pin_w = 16
        priority_gap = 8
        pin_gap = 10
        priority_rect = QRect(pr_rect.left(), r.top(), priority_w, r.height())
        date_rect = QRect(
            priority_rect.right() + priority_gap,
            r.top(),
            pr_rect.width() - priority_w - priority_gap - pin_w - pin_gap,
            r.height(),
        )

        painter.drawText(priority_rect, Qt.AlignVCenter | Qt.AlignRight,
                         priority if not archived else "ARCH")

        painter.setPen(self.C_DIM)
        painter.drawText(date_rect, Qt.AlignVCenter | Qt.AlignRight,
                         f"обновл. {updated}")

        pin_rect = QRect(pr_rect.right() - pin_w, cy - 8, pin_w, 16)
        self._icon_pin.paint(painter, pin_rect)

        painter.setPen(self.C_BORDER)
        painter.setBrush(QColor("#1f2227"))
        painter.drawRect(menu_rect)
        self._icon_menu.paint(painter, QRect(menu_rect.center().x() - 7, menu_rect.center().y() - 7, 14, 14))

        painter.restore()

    def editorEvent(self, event, model, option, index):
        """Обрабатывает клики по индикатору архивации и меню."""
        row_type = index.data(ProjectRoles.RowType)
        if row_type == "header":
            if event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
                pos = event.position().toPoint()
                r = option.rect
                left_pad = 10
                menu_w = 24
                menu_rect = QRect(r.left() + left_pad, r.top() + 4, menu_w, r.height() - 8)
                if menu_rect.contains(pos):
                    self._show_area_menu(index)
                    return True
            return False

        if row_type != "project":
            return False

        if event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
            pos = event.position().toPoint()
            r = option.rect
            cy = r.center().y()

            x = r.left() + 10
            x += 22
            box_rect = QRect(x, cy - 7, 14, 14)

            right_pad = 18
            menu_w = 30
            menu_rect = QRect(r.right() - right_pad - menu_w, r.top() + 6, menu_w, r.height() - 12)

            if box_rect.contains(pos):
                model.toggle_archive_by_row(index.row())
                return True

            if menu_rect.contains(pos):
                self._show_row_menu(index)
                return True

        return False

    def _show_row_menu(self, index: QModelIndex):
        """Показывает контекстное меню проекта."""
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background: #1f2227;
                color: #e6e6e6;
                border: 1px solid #2a2b2f;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 14px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background: #2b2f36;
            }
            QMenu::separator {
                height: 1px;
                background: #2a2b2f;
                margin: 4px 8px;
            }
        """)
        act_edit = menu.addAction("Редактировать")
        menu.addSeparator()
        archived = bool(index.data(ProjectRoles.Archived))
        act_archive = menu.addAction("Восстановить" if archived else "Архивировать")
        act_delete = menu.addAction("Удалить")

        chosen = menu.exec(QCursor.pos())
        if chosen == act_edit:
            self._edit_project(index)
            return
        if chosen == act_archive:
            model = index.model()
            if hasattr(model, "toggle_archive_by_row"):
                model.toggle_archive_by_row(index.row())
            return
        if chosen != act_delete:
            return

        title = index.data(ProjectRoles.Title) or "проект"
        parent = menu.parentWidget() or None
        dialog = ConfirmDialog(
            "Удалить проект",
            f"Удалить проект:\n«{title}» ?",
            parent=parent,
            confirm_text="Удалить",
            cancel_text="Отмена",
        )
        if show_dialog_standard(dialog, parent) != QDialog.Accepted:
            return

        model = index.model()
        if hasattr(model, "delete_project_by_row"):
            model.delete_project_by_row(index.row())
            self._refresh_area_combo()

    def _show_area_menu(self, index: QModelIndex):
        """Показывает меню действий области проектов."""
        area = index.data(ProjectRoles.Area) or ""
        model = index.model()
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background: #1f2227;
                color: #e6e6e6;
                border: 1px solid #2a2b2f;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 14px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background: #2b2f36;
            }
            QMenu::separator {
                height: 1px;
                background: #2a2b2f;
                margin: 4px 8px;
            }
        """)
        act_edit = menu.addAction("Редактировать")
        menu.addSeparator()
        has_active = True
        if hasattr(model, "area_has_active"):
            has_active = model.area_has_active(area)
        act_archive = menu.addAction("Архивировать" if has_active else "Восстановить")
        act_delete = menu.addAction("Удалить")

        chosen = menu.exec(QCursor.pos())
        if chosen == act_edit:
            self._edit_area(area, model)
            return
        if chosen == act_archive:
            if hasattr(model, "set_area_archived"):
                model.set_area_archived(area, archived=has_active)
                self._refresh_area_combo(area)
            return
        if chosen != act_delete:
            return

        parent = menu.parentWidget() or None
        dialog = ConfirmDialog(
            "Удалить область",
            f"Удалить все проекты в области:\n«{area}» ?",
            parent=parent,
            confirm_text="Удалить",
            cancel_text="Отмена",
        )
        if show_dialog_standard(dialog, parent) != QDialog.Accepted:
            return

        if hasattr(model, "delete_area"):
            model.delete_area(area)
            self._refresh_area_combo()

    def _edit_area(self, area: str, model):
        """Открывает диалог редактирования области проектов."""
        parent = self.parent() if isinstance(self.parent(), QWidget) else None
        dialog = ProjectAreaEditDialog(area, parent=parent)
        if exec_with_overlay(dialog, parent) != QDialog.Accepted:
            return

        values = dialog.values()
        if hasattr(model, "rename_area"):
            try:
                model.rename_area(area, values["area"])
                self._refresh_area_combo(values["area"])
            except ValueError as exc:
                QMessageBox.warning(parent or self.parent(), "Проверка", str(exc))

    def _edit_project(self, index: QModelIndex):
        """Открывает диалог редактирования проекта."""
        model = index.model()
        if not hasattr(model, "project_at_row"):
            return

        project = model.project_at_row(index.row())
        if project is None:
            return

        parent = self.parent() if isinstance(self.parent(), QWidget) else None
        dialog = ProjectEditDialog(project, parent=parent)
        if exec_with_overlay(dialog, parent) != QDialog.Accepted:
            return

        values = dialog.values()
        if hasattr(model, "update_project_by_row"):
            try:
                model.update_project_by_row(
                    index.row(),
                    area=values["area"],
                    title=values["title"],
                    updated=values["updated"],
                    priority=values["priority"],
                    archived=values["archived"],
                )
                self._refresh_area_combo(values["area"])
            except ValueError as exc:
                QMessageBox.warning(parent or self.parent(), "Проверка", str(exc))

    def _refresh_area_combo(self, selected: Optional[str] = None):
        """Просит рабочую область обновить список областей."""
        widget = self.parent()
        while widget is not None:
            if hasattr(widget, "_refresh_area_combo"):
                widget._refresh_area_combo(selected)
                break
            widget = widget.parent()

    def _prio_color(self, p: str) -> QColor:
        """Возвращает цвет для приоритета проекта."""
        p = (p or "").lower()
        if p == "high":
            return self.C_HIGH
        if p == "low":
            return self.C_LOW
        if p == "отложенная":
            return self.C_DEFER
        return self.C_MED


class ProjectEditDialog(QDialog):
    def __init__(self, project: Optional[ProjectRow] = None, parent=None):
        """Создает диалог создания или редактирования проекта."""
        super().__init__(parent)
        is_new = project is None
        self.setWindowTitle("Создание проекта" if is_new else "Редактирование проекта")
        self.setObjectName("ProjectEditDialog")
        self.setProperty("dialog_category", "minimal_flex")
        self.setFixedSize(560, 300)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        title_label = QLabel("Создание проекта" if is_new else "Редактирование проекта")
        title_label.setObjectName("DialogTitle")
        layout.addWidget(title_label)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        form.setFormAlignment(Qt.AlignTop)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(12)

        self.area_edit = QLineEdit(project.area if project else "")
        self.area_edit.setPlaceholderText("Область проекта")

        self.title_edit = QLineEdit(project.title if project else "")
        self.title_edit.setPlaceholderText("Название проекта")

        self.updated_edit = QDateEdit()
        self.updated_edit.setCalendarPopup(True)
        self.updated_edit.setDisplayFormat("dd.MM.yyyy")
        self.updated_edit.setKeyboardTracking(False)
        self.updated_edit.setDate(QDate.currentDate())
        if project:
            self.updated_edit.setDate(QDate(project.updated.year, project.updated.month, project.updated.day))

        self.priority_edit = QComboBox()
        self.priority_edit.addItems(["Low", "Medium", "High"])
        self.priority_edit.setCurrentText(project.priority if project else "Medium")

        self.archived_edit = QCheckBox("Архивировать")
        self.archived_edit.setChecked(project.archived if project else False)

        form.addRow("Область", self.area_edit)
        form.addRow("Название", self.title_edit)
        form.addRow("Дата обновления", self.updated_edit)
        form.addRow("Приоритет", self.priority_edit)
        form.addRow("", self.archived_edit)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setStyleSheet(f"""
            QDialog#ProjectEditDialog {{
                {MATH_PHYS_BACKGROUND}
            }}

            QDialog#ProjectEditDialog QLabel {{
                color: #cfcfcf;
            }}

            QDialog#ProjectEditDialog QLabel#DialogTitle {{
                color: #f2f2f2;
                font-size: 18px;
                font-weight: 600;
            }}

            QDialog#ProjectEditDialog QLineEdit,
            QDialog#ProjectEditDialog QComboBox,
            QDialog#ProjectEditDialog QDateEdit {{
                background: #202127;
                color: #e6e6e6;
                border: 1px solid #2a2b2f;
                padding: 8px 10px;
                border-radius: 6px;
                min-height: 28px;
            }}

            QDialog#ProjectEditDialog QCheckBox {{
                color: #cfcfcf;
                padding: 4px 0;
            }}

            QDialog#ProjectEditDialog QComboBox::drop-down {{
                border: none;
                width: 18px;
            }}

            QDialog#ProjectEditDialog QDialogButtonBox QPushButton {{
                background: #2a2b2f;
                color: #e6e6e6;
                border: 1px solid #3a3b40;
                padding: 8px 14px;
                border-radius: 6px;
                min-width: 90px;
            }}

            QDialog#ProjectEditDialog QDialogButtonBox QPushButton:hover {{
                background: #34363b;
            }}
        """)

    def _on_accept(self):
        """Проверяет ввод перед сохранением изменений."""
        try:
            validate_area(self.area_edit.text())
            validate_title(self.title_edit.text(), field_name="Название проекта")
            normalize_priority(self.priority_edit.currentText())
        except ValueError as exc:
            QMessageBox.warning(self, "Проверка", str(exc))
            return

        self.accept()

    def values(self) -> dict:
        """Возвращает значения формы проекта."""
        qd = self.updated_edit.date()
        return {
            "area": self.area_edit.text().strip(),
            "title": self.title_edit.text().strip(),
            "updated": date(qd.year(), qd.month(), qd.day()),
            "priority": self.priority_edit.currentText().strip() or "Medium",
            "archived": self.archived_edit.isChecked(),
        }


class ProjectAreaEditDialog(QDialog):
    def __init__(self, area: str, parent=None):
        """Создает диалог редактирования области проектов."""
        super().__init__(parent)
        self.setWindowTitle("Редактирование области")
        self.setObjectName("ProjectAreaEditDialog")
        self.setProperty("dialog_category", "minimal_flex")
        self.setFixedSize(560, 300)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        title_label = QLabel("Редактирование области")
        title_label.setObjectName("DialogTitle")
        layout.addWidget(title_label)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        form.setFormAlignment(Qt.AlignTop)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(12)

        self.area_edit = QLineEdit(area)
        self.area_edit.setPlaceholderText("Область проекта")
        form.addRow("Область", self.area_edit)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setStyleSheet(f"""
            QDialog#ProjectAreaEditDialog {{
                {MATH_PHYS_BACKGROUND}
            }}

            QDialog#ProjectAreaEditDialog QLabel {{
                color: #cfcfcf;
            }}

            QDialog#ProjectAreaEditDialog QLabel#DialogTitle {{
                color: #f2f2f2;
                font-size: 18px;
                font-weight: 600;
            }}

            QDialog#ProjectAreaEditDialog QLineEdit {{
                background: #202127;
                color: #e6e6e6;
                border: 1px solid #2a2b2f;
                padding: 8px 10px;
                border-radius: 6px;
                min-height: 28px;
            }}

            QDialog#ProjectAreaEditDialog QDialogButtonBox QPushButton {{
                background: #2a2b2f;
                color: #e6e6e6;
                border: 1px solid #3a3b40;
                padding: 8px 14px;
                border-radius: 6px;
                min-width: 90px;
            }}

            QDialog#ProjectAreaEditDialog QDialogButtonBox QPushButton:hover {{
                background: #34363b;
            }}
        """)

    def _on_accept(self):
        """Проверяет ввод перед сохранением изменений."""
        try:
            validate_area(self.area_edit.text())
        except ValueError as exc:
            QMessageBox.warning(self, "Проверка", str(exc))
            return
        self.accept()

    def values(self) -> dict:
        """Возвращает значения формы области."""
        return {
            "area": self.area_edit.text().strip(),
        }


class ProjectsWorkspace(QWidget):
    def __init__(self, parent=None):
        """Создает рабочую область проектов."""
        super().__init__(parent)
        self.setObjectName("ProjectsWorkspace")

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        top = QFrame()
        top.setObjectName("ProjectsTopbar")
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(10, 8, 10, 8)
        top_layout.setSpacing(8)

        self.tabs_group = QButtonGroup(self)
        self.tabs_group.setExclusive(True)

        def tab_btn(text: str) -> QToolButton:
            """Создает кнопку вкладки фильтра."""
            b = QToolButton()
            b.setText(text)
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setAutoRaise(True)
            self.tabs_group.addButton(b)
            return b

        self.tab_all = tab_btn("Все")
        self.tab_active = tab_btn("Активные")
        self.tab_arch = tab_btn("Архив")
        self.tab_all.setChecked(True)

        top_layout.addWidget(self.tab_all)
        top_layout.addWidget(self.tab_active)
        top_layout.addWidget(self.tab_arch)

        top_layout.addSpacing(12)

        self.cmb_area = QComboBox()
        self.cmb_area.addItems(["Все области", *get_database().project_areas()])
        self.cmb_area.setFixedWidth(180)
        top_layout.addWidget(self.cmb_area)

        top_layout.addSpacing(12)

        self.cmb_priority = QComboBox()
        self.cmb_priority.addItems(["Любой", "Low", "Medium", "High"])
        self.cmb_priority.setFixedWidth(110)

        self.btn_create = QToolButton()
        self.btn_create.setText("Создать")
        self.btn_create.setCursor(Qt.PointingHandCursor)

        top_layout.addWidget(self.cmb_priority)
        top_layout.addWidget(self.btn_create)

        top_layout.addStretch(1)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Поиск…")
        self.search.setFixedWidth(260)
        top_layout.addWidget(self.search)

        root.addWidget(top)

        self.list = QListView()
        self.list.setObjectName("ProjectsList")
        self.list.setUniformItemSizes(True)
        self.list.setVerticalScrollMode(QListView.ScrollPerPixel)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list.setSelectionMode(QListView.SingleSelection)
        root.addWidget(self.list, 1)

        self.model = ProjectsModel(self)
        self.list.setModel(self.model)

        self.delegate = ProjectsItemDelegate(self.list)
        self.list.setItemDelegate(self.delegate)

        for b in self.tabs_group.buttons():
            b.clicked.connect(self._on_tab_changed)

        self.search.textChanged.connect(self.model.set_search)
        self.cmb_area.currentTextChanged.connect(self._on_area_changed)
        self.btn_create.clicked.connect(self._on_create_project)

        self.setStyleSheet("""
            QWidget#ProjectsWorkspace { background: #16171a; }

            QFrame#ProjectsTopbar {
                background: #1b1c1f;
                border: 1px solid #2a2b2f;
            }

            QToolButton {
                color: #cfcfcf;
                border: none;
                padding: 6px 8px;
            }
            QToolButton:checked { background: #2a2b2f; }

            QComboBox, QLineEdit {
                background: #202127;
                color: #cfcfcf;
                border: 1px solid #2a2b2f;
                padding: 6px 8px;
            }

            QListView#ProjectsList {
                background: #16171a;
                border: 1px solid #2a2b2f;
            }
        """)

    def _on_tab_changed(self):
        """Обрабатывает переключение фильтров по статусу."""
        if self.tab_arch.isChecked():
            self.model.set_filter_mode("Архив")
        elif self.tab_active.isChecked():
            self.model.set_filter_mode("Активные")
        else:
            self.model.set_filter_mode("Все")

    def _on_area_changed(self, text: str):
        """Обновляет фильтрацию по области проекта."""
        if text == "Все области":
            self.model.set_area_focus(None)
        else:
            self.model.set_area_focus(text)

    def refresh_projects(self) -> None:
        """Перезагружает список проектов из базы."""
        self.model.refresh()

    def set_task_filter(self, task_id: Optional[int]) -> None:
        """Устанавливает фильтр по задаче для списка проектов."""
        self.model.set_task_filter(task_id)

    def _refresh_area_combo(self, selected: Optional[str] = None):
        """Обновляет список областей проектов."""
        current = selected or self.cmb_area.currentText()
        self.cmb_area.blockSignals(True)
        self.cmb_area.clear()
        self.cmb_area.addItems(["Все области", *get_database().project_areas()])
        if current:
            self.cmb_area.setCurrentText(current)
        if self.cmb_area.currentText() != current and current != "Все области":
            self.cmb_area.setCurrentText("Все области")
        self.cmb_area.blockSignals(False)

    def _on_create_project(self):
        """Открывает диалог создания проекта."""
        dialog = ProjectEditDialog(parent=self)
        if show_dialog_standard(dialog, self) != QDialog.Accepted:
            return

        values = dialog.values()
        try:
            self.model.add_project(
                area=values["area"],
                title=values["title"],
                updated=values["updated"],
                priority=values["priority"],
                archived=values["archived"],
            )
            self._refresh_area_combo(values["area"])
        except ValueError as exc:
            QMessageBox.warning(self, "Проверка", str(exc))
