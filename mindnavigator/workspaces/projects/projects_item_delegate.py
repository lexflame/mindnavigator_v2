"""ProjectsItemDelegate class module for projects workspace."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403
from .projects_model import ProjectsModel
from .project_edit_dialog import ProjectEditDialog
from .project_area_edit_dialog import ProjectAreaEditDialog

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
        self._icon_tree_open = qta.icon("fa5s.chevron-down", color="#8a8a8a")
        self._icon_tree_closed = qta.icon("fa5s.chevron-right", color="#8a8a8a")

        self._font = QFont()
        self._font.setPointSize(10)

        self._font_small = QFont()
        self._font_small.setPointSize(9)

        self._font_header = QFont()
        self._font_header.setPointSize(9)
        self._font_header.setBold(True)

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        """Возвращает размер строки списка."""
        opt = cast(Any, option)
        rect = opt.rect
        width = rect.width() if rect is not None else 0
        row_type = index.data(ProjectRoles.RowType)
        if row_type == "header":
            return QSize(width, self.HEADER_H)
        return QSize(width, self.ROW_H)

    def _area_quick_rect(self, row_rect: QRect, area: str) -> QRect:
        left_pad = 0
        menu_w = max(18, row_rect.height())
        text_left = row_rect.left() + left_pad + menu_w + 8
        quick_w = 112
        quick_h = row_rect.height()
        area_w = QFontMetrics(self._font_header).horizontalAdvance(area or "")
        quick_x = text_left + area_w + 12
        max_right = row_rect.right() - 12
        if quick_x + quick_w > max_right:
            quick_x = max(text_left + 10, max_right - quick_w)
        return QRect(quick_x, row_rect.top(), quick_w, quick_h)

    def _project_quick_rect(self, title_rect: QRect, display_title: str) -> QRect:
        quick_w = 120
        quick_h = title_rect.height() - 14
        title_w = QFontMetrics(self._font).horizontalAdvance(display_title or "")
        quick_x = title_rect.left() + title_w + 10
        max_x = title_rect.right() - quick_w
        if quick_x > max_x:
            quick_x = max(title_rect.left(), max_x)
        return QRect(quick_x, title_rect.top() + 7, quick_w, quick_h)

    @staticmethod
    def _project_priority_rect(pr_rect: QRect, row_rect: QRect) -> QRect:
        priority_width = min(76, max(54, pr_rect.width() // 2))
        return QRect(pr_rect.left(), row_rect.top(), priority_width, row_rect.height())

    def _draw_attachment_badges(
        self,
        painter: QPainter,
        row_rect: QRect,
        attachment_summary: List[tuple[str, int]],
    ) -> None:
        if not attachment_summary:
            return
        metrics = QFontMetrics(self._font_small)
        badge_height = 18
        gap = 6
        max_width = max(80, row_rect.width() - 80)
        entries: List[tuple[str, QColor]] = []
        for kind, count in attachment_summary:
            label = ATTACHMENT_BADGE_LABELS.get(kind, (kind or "item").upper())
            text = f"{label} {count}" if count > 1 else label
            color = ATTACHMENT_BADGE_COLORS.get(kind, QColor("#475569"))
            entries.append((text, color))

        def total_width(items: List[tuple[str, QColor]]) -> int:
            if not items:
                return 0
            widths = [max(28, metrics.horizontalAdvance(text) + 12) for text, _ in items]
            return sum(widths) + gap * (len(widths) - 1)

        hidden = 0
        while len(entries) > 1 and total_width(entries) > max_width:
            hidden += 1
            entries.pop()
        if hidden:
            entries.append((f"+{hidden}", QColor("#374151")))

        widths = [max(28, metrics.horizontalAdvance(text) + 12) for text, _ in entries]
        total = sum(widths) + gap * (len(widths) - 1)
        x = row_rect.center().x() - total // 2
        y = row_rect.center().y() - badge_height // 2
        for idx, (text, color) in enumerate(entries):
            width = widths[idx]
            badge_rect = QRect(x, y, width, badge_height)
            painter.setPen(self.C_BORDER)
            painter.setBrush(color)
            painter.drawRoundedRect(badge_rect, 8, 8)
            luminance = color.red() * 0.299 + color.green() * 0.587 + color.blue() * 0.114
            painter.setPen(QColor("#111827") if luminance >= 160 else QColor("#f8fafc"))
            painter.setFont(self._font_small)
            painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, text)
            x += width + gap

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        """Рисует строку проекта или заголовок области."""
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        row_type = index.data(ProjectRoles.RowType)
        opt = cast(Any, option)
        r = opt.rect
        state = opt.state

        if row_type == "header":
            area: str = index.data(ProjectRoles.Area) or ""
            painter.fillRect(r, self.C_BG)
            painter.setPen(self.C_DIM)
            painter.setFont(self._font_header)
            left_pad = 0
            menu_w = max(18, r.height())
            menu_rect = QRect(r.left() + left_pad, r.top(), menu_w, r.height())
            quick_rect = self._area_quick_rect(r, area)
            text_rect = QRect(menu_rect.right() + 8, r.top(), quick_rect.left() - menu_rect.right() - 12, r.height())
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, area)
            if state & QStyle.StateFlag.State_MouseOver:
                painter.setPen(self.C_BORDER)
                painter.setBrush(QColor("#1f2227"))
                painter.drawRoundedRect(quick_rect, 4, 4)
                painter.setPen(self.C_DIM)
                painter.setFont(self._font_small)
                painter.drawText(quick_rect.adjusted(10, 0, -10, 0), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "+ Проект")
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
        depth: int = int(index.data(ProjectRoles.Depth) or 0)
        has_children: bool = bool(index.data(ProjectRoles.HasChildren))
        is_collapsed: bool = bool(index.data(ProjectRoles.IsCollapsed))
        marker_color: str = (index.data(ProjectRoles.MarkerColor) or "").strip()
        marker_theme: str = (index.data(ProjectRoles.MarkerTheme) or "").strip()

        bg = self.C_ROW if (index.row() % 2 == 0) else self.C_ROW_ALT
        if state & QStyle.StateFlag.State_Selected:
            bg = QColor("#343844")
        elif marker_color:
            tint = QColor(marker_color)
            if tint.isValid():
                bg = QColor(
                    int(bg.red() * 0.65 + tint.red() * 0.35),
                    int(bg.green() * 0.65 + tint.green() * 0.35),
                    int(bg.blue() * 0.65 + tint.blue() * 0.35),
                )

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

        depth = max(0, min(depth, 6))
        x += depth * 14

        marker_rect = QRect(x, cy - 8, 16, 16)
        if has_children:
            marker_icon = self._icon_tree_closed if is_collapsed else self._icon_tree_open
            marker_icon.paint(painter, marker_rect)
        else:
            painter.setFont(self._font_small)
            painter.setPen(self.C_DIM)
            painter.drawText(marker_rect, Qt.AlignmentFlag.AlignCenter, ".")
        x += 18

        painter.setFont(self._font)
        painter.setPen(self.C_TEXT if not archived else self.C_DIM)

        right_pad = 8
        menu_w = max(18, r.height())
        quick_w = 120
        pr_w = 160
        menu_rect = QRect(r.right() - right_pad - menu_w, r.top(), menu_w, r.height())
        quick_rect = QRect(menu_rect.left() - quick_w - 8, r.top(), quick_w, r.height())
        pr_rect = QRect(quick_rect.left() - pr_w - 8, r.top(), pr_w, r.height())

        title_rect = QRect(x, r.top(), pr_rect.left() - x - 10, r.height())
        display_title = f"{title} · {marker_theme.upper()}" if marker_theme else title
        quick_rect = self._project_quick_rect(title_rect, display_title)
        title_text_rect = QRect(
            title_rect.left(),
            title_rect.top(),
            max(10, quick_rect.left() - title_rect.left() - 8),
            title_rect.height(),
        )
        elided = QFontMetrics(self._font).elidedText(
            display_title,
            Qt.TextElideMode.ElideRight,
            title_text_rect.width(),
        )
        painter.drawText(title_text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, elided)

        raw_attachment_summary = index.data(ProjectRoles.AttachmentSummary) or []
        attachment_summary: List[tuple[str, int]] = []
        for entry in raw_attachment_summary:
            if not isinstance(entry, (tuple, list)) or len(entry) != 2:
                continue
            kind = (str(entry[0]) or "").strip().lower()
            try:
                count = int(entry[1])
            except (TypeError, ValueError):
                continue
            if kind and count > 0:
                attachment_summary.append((kind, count))
        if state & QStyle.StateFlag.State_MouseOver and attachment_summary:
            self._draw_attachment_badges(painter, r, attachment_summary)

        pr_color = self.C_ARCH if archived else self._prio_color(priority)
        painter.setFont(self._font_small)
        painter.setPen(pr_color)

        pin_w = 16
        priority_gap = 8
        pin_gap = 10
        priority_rect = self._project_priority_rect(pr_rect, r)
        date_rect = QRect(
            priority_rect.right() + priority_gap,
            r.top(),
            pr_rect.width() - priority_rect.width() - priority_gap - pin_w - pin_gap,
            r.height(),
        )

        painter.drawText(priority_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                         priority if not archived else "ARCH")

        painter.setPen(self.C_DIM)
        painter.drawText(date_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                         f"обновл. {updated}")

        pin_rect = QRect(pr_rect.right() - pin_w, cy - 8, pin_w, 16)
        self._icon_pin.paint(painter, pin_rect)

        painter.setPen(self.C_BORDER)
        painter.setBrush(QColor("#1f2227"))
        painter.drawRect(menu_rect)
        self._icon_menu.paint(painter, QRect(menu_rect.center().x() - 7, menu_rect.center().y() - 7, 14, 14))
        if state & QStyle.StateFlag.State_MouseOver:
            painter.setPen(self.C_BORDER)
            painter.setBrush(QColor("#1f2227"))
            painter.drawRoundedRect(quick_rect, 4, 4)
            painter.setPen(self.C_DIM)
            painter.drawText(quick_rect.adjusted(10, 0, -10, 0), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "+ Подпроект")

        painter.restore()

    def editorEvent(
        self,
        event: QEvent,
        model: QAbstractListModel,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> bool:
        """Обрабатывает клики по индикатору архивации и меню."""
        row_type = index.data(ProjectRoles.RowType)
        if row_type == "header":
            if event.type() == QEvent.Type.MouseButtonRelease and isinstance(event, QMouseEvent):
                if event.button() != Qt.MouseButton.LeftButton:
                    return False
                pos = event.position().toPoint()
                opt = cast(Any, option)
                r = opt.rect
                left_pad = 0
                menu_w = max(18, r.height())
                menu_rect = QRect(r.left() + left_pad, r.top(), menu_w, r.height())
                area = index.data(ProjectRoles.Area) or ""
                quick_rect = self._area_quick_rect(r, area)
                if menu_rect.contains(pos):
                    self._show_area_menu(index)
                    return True
                if quick_rect.contains(pos):
                    area = index.data(ProjectRoles.Area) or ""
                    if hasattr(model, "quick_add_project"):
                        typed_model = cast(ProjectsModel, model)
                        project_id = typed_model.quick_add_project(area=area, title="Новый проект")
                        self._refresh_area_combo(area)
                        self._focus_project(project_id)
                    return True
            return False

        if row_type != "project":
            return False

        if event.type() == QEvent.Type.MouseButtonRelease and isinstance(event, QMouseEvent):
            if event.button() != Qt.MouseButton.LeftButton:
                return False
            pos = event.position().toPoint()
            opt = cast(Any, option)
            r = opt.rect
            cy = r.center().y()

            x = r.left() + 10
            x += 22
            box_side = max(18, r.height())
            box_rect = QRect(x, r.top(), box_side, r.height())
            x += box_side + 8
            x += 22
            depth: int = int(index.data(ProjectRoles.Depth) or 0)
            depth = max(0, min(depth, 6))
            x += depth * 14
            marker_rect = QRect(x, cy - 8, 16, 16)

            right_pad = 8
            menu_w = max(18, r.height())
            quick_w = 120
            menu_rect = QRect(r.right() - right_pad - menu_w, r.top(), menu_w, r.height())
            quick_rect = QRect(menu_rect.left() - quick_w - 8, r.top(), quick_w, r.height())
            pr_w = 160
            pr_rect = QRect(quick_rect.left() - pr_w - 8, r.top(), pr_w, r.height())
            priority_rect = self._project_priority_rect(pr_rect, r)
            title_rect = QRect(x + 18, r.top(), pr_rect.left() - (x + 18) - 10, r.height())
            title = index.data(ProjectRoles.Title) or ""
            marker_theme = (index.data(ProjectRoles.MarkerTheme) or "").strip()
            display_title = f"{title} · {marker_theme.upper()}" if marker_theme else title
            quick_rect = self._project_quick_rect(title_rect, display_title)

            if marker_rect.contains(pos):
                if hasattr(model, "toggle_project_collapsed_by_row"):
                    model.toggle_project_collapsed_by_row(index.row())
                    return True

            if box_rect.contains(pos):
                typed_model = cast(ProjectsModel, model)
                typed_model.toggle_archive_by_row(index.row())
                return True
            if priority_rect.contains(pos):
                typed_model = cast(ProjectsModel, model)
                typed_model.cycle_priority_by_row(index.row())
                return True

            if menu_rect.contains(pos):
                self._show_row_menu(index)
                return True
            if quick_rect.contains(pos):
                project_id = index.data(ProjectRoles.ProjectId)
                area = index.data(ProjectRoles.Area) or ""
                if isinstance(project_id, int) and hasattr(model, "quick_add_project"):
                    typed_model = cast(ProjectsModel, model)
                    created_project_id = typed_model.quick_add_project(
                        area=area,
                        parent_project_id=project_id,
                        title="Новый подпроект",
                    )
                    self._refresh_area_combo(area)
                    self._focus_project(created_project_id)
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
        act_repository_status = menu.addAction("Статус репозитория")
        menu.addSeparator()
        archived = bool(index.data(ProjectRoles.Archived))
        act_archive = menu.addAction("Восстановить" if archived else "Архивировать")
        act_delete = menu.addAction("Удалить")

        chosen = menu.exec(QCursor.pos())
        if chosen == act_edit:
            self._edit_project(index)
            return
        if chosen == act_repository_status:
            self._show_repository_status(index, menu.parentWidget() or None)
            return
        if chosen == act_archive:
            model = index.model()
            if hasattr(model, "toggle_archive_by_row"):
                typed_model = cast(ProjectsModel, model)
                typed_model.toggle_archive_by_row(index.row())
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
        if show_dialog_standard(dialog, parent) != QDialog.DialogCode.Accepted:
            return

        model = index.model()
        if hasattr(model, "delete_project_by_row"):
            model.delete_project_by_row(index.row())
            self._refresh_area_combo()

    def _show_repository_status(self, index: QModelIndex, parent: Optional[QWidget]) -> None:
        model = index.model()
        if not isinstance(model, ProjectsModel):
            QMessageBox.information(parent or self.parent(), "Репозиторий проекта", "Модель проекта недоступна.")
            return
        state = model.repository_probe_by_row(index.row())
        repository_catalog = (index.data(ProjectRoles.RepositoryCatalog) or "").strip()
        if not state.available:
            details = state.message or "Статус репозитория недоступен."
            if repository_catalog:
                details = f"Каталог: {repository_catalog}\n{details}"
            QMessageBox.information(parent or self.parent(), "Репозиторий проекта", details)
            return
        dirty_text = "изменения есть" if state.has_local_changes else "чисто"
        message = (
            f"Каталог: {repository_catalog}\n"
            f"Ветка: {state.branch_name}\n"
            f"Состояние: {dirty_text}"
        )
        QMessageBox.information(parent or self.parent(), "Репозиторий проекта", message)

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
        if show_dialog_standard(dialog, parent) != QDialog.DialogCode.Accepted:
            return

        if hasattr(model, "delete_area"):
            model.delete_area(area)
            self._refresh_area_combo()

    def _edit_area(self, area: str, model):
        """Открывает диалог редактирования области проектов."""
        parent = self.parent() if isinstance(self.parent(), QWidget) else None
        dialog = ProjectAreaEditDialog(area, parent=parent)
        if exec_with_overlay(dialog, parent) != QDialog.DialogCode.Accepted:
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
        raw_model = index.model()
        if not isinstance(raw_model, ProjectsModel):
            return

        model = raw_model
        project = model.project_at_row(index.row())
        if project is None:
            return

        parent = self.parent() if isinstance(self.parent(), QWidget) else None
        dialog = ProjectEditDialog(project, parent=parent)
        if exec_with_overlay(dialog, parent) != QDialog.DialogCode.Accepted:
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
                    parent_project_id=values["parent_project_id"],
                    default_task_priority=values["default_task_priority"],
                    force_recurrence_kind=values["force_recurrence_kind"],
                    linked_map_id=values["linked_map_id"],
                    linked_note_id=values["linked_note_id"],
                    linked_object_id=values["linked_object_id"],
                    marker_color=values["marker_color"],
                    marker_theme=values["marker_theme"],
                    repository_catalog=values["repository_catalog"],
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

    def _focus_project(self, project_id: int) -> None:
        if not isinstance(project_id, int):
            return
        widget = self.parent()
        while widget is not None:
            focus_project = getattr(widget, "focus_project", None)
            if callable(focus_project):
                focus_project(project_id)
                return
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

__all__ = ["ProjectsItemDelegate"]
