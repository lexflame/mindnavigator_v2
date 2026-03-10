"""TasksItemDelegate class module for tasks workspace."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403
from .task_details_dialog import TaskDetailsDialog
from .task_edit_dialog import TaskEditDialog
from .tasks_model import TasksModel

class TasksItemDelegate(QStyledItemDelegate):
    ROW_H = 42
    HEADER_H = 32
    TIME_W = 140
    PROJECT_W = 420
    TEXT_V_PAD = 8
    TEXT_GAP = 6
    ROW_H_EXPANDED_MIN = 82
    TAG_H = 20
    TAG_PAD_X = 8
    TAG_GAP = 6
    TAG_LINE_GAP = 6
    PARENT_MOVE_BUTTON_H = 22
    PARENT_MOVE_BUTTON_PAD_X = 10
    PARENT_MOVE_BUTTON_GAP = 8

    C_BG = QColor("#16171a")
    C_ROW = QColor("#2a2d33")
    C_ROW_ALT = QColor("#2c2f36")
    C_BORDER = QColor("#3a3b40")
    C_TEXT = QColor("#cfcfcf")
    C_DIM = QColor("#8a8a8a")
    C_TODAY = QColor("#f2a23a")

    C_OVERDUE = QColor("#c84b4b")
    C_HIGH = QColor("#d94f4f")
    C_MED = QColor("#d0a93e")
    C_LOW = QColor("#4caf50")
    C_DEFER = QColor("#6f7a87")

    def __init__(self, parent=None):
        """Инициализирует делегат отрисовки строк задач."""
        super().__init__(parent)
        self._icon_doc = qta.icon("fa5s.file-alt", color="#cfcfcf")
        self._icon_grip = qta.icon("fa5s.grip-lines", color="#8a8a8a")
        self._icon_menu = qta.icon("fa5s.ellipsis-v", color="#cfcfcf")
        self._icon_fire = qta.icon("fa5s.fire", color="#d0a93e")
        self._icon_tomorrow = qta.icon("ph.arrow-u-right-down-bold", color="#cfcfcf")
        self._icon_subtask_open = qta.icon("fa5s.chevron-down", color="#8a8a8a")
        self._icon_subtask_closed = qta.icon("fa5s.chevron-right", color="#8a8a8a")
        self._icon_quick_add = qta.icon("fa5s.plus", color="#8a8a8a")
        self._marker_theme_icons = {
            "movies": qta.icon("fa5s.film", color="#4f7ecf"),
            "games": qta.icon("fa5s.gamepad", color="#4caf50"),
            "books": qta.icon("fa5s.book", color="#d0a93e"),
            "music": qta.icon("fa5s.music", color="#b17cff"),
            "work": qta.icon("fa5s.briefcase", color="#5fb7d9"),
            "personal": qta.icon("fa5s.user", color="#d98f5f"),
            "dev": qta.icon("fa5s.code", color="#8f9cff"),
        }
        self._marker_theme_asset_names = {
            "movies": "movie.png",
            "games": "game.png",
            "books": "book.png",
            "music": "music.png",
            "work": "main.png",
            "personal": "main.png",
            "dev": "develop.png",
        }
        self._marker_theme_pixmap_cache: Dict[str, QPixmap] = {}

        self._font = QFont()
        self._font.setPointSize(10)

        self._font_small = QFont()
        self._font_small.setPointSize(9)

        self._font_header = QFont()
        self._font_header.setPointSize(9)
        self._font_header.setBold(True)

    @staticmethod
    def _tasks_model(model: QAbstractItemModel | None) -> Optional[TasksModel]:
        if isinstance(model, TasksModel):
            return model
        return None

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        """Возвращает размер строки списка."""
        option_rect = getattr(option, "rect", QRect())
        row_type = index.data(TaskRoles.RowType)
        if row_type in ("header", "sort_header"):
            return QSize(option_rect.width(), self.HEADER_H)
        expanded = bool(index.data(TaskRoles.Expanded))
        if not expanded:
            return QSize(option_rect.width(), self.ROW_H)

        title = index.data(Qt.ItemDataRole.DisplayRole) or ""
        description = index.data(TaskRoles.Description) or ""
        depth = int(index.data(TaskRoles.SubtaskDepth) or 0)
        has_subtasks = bool(index.data(TaskRoles.HasSubtasks))
        layout = self._row_layout(option_rect, depth, has_subtasks)
        text_width = max(10, layout["title"].width())

        title_metrics = QFontMetrics(self._font)
        desc_metrics = QFontMetrics(self._font_small)
        title_height = title_metrics.boundingRect(0, 0, text_width, 1000, Qt.TextFlag.TextWordWrap, title).height()
        desc_height = 0
        if description:
            desc_height = desc_metrics.boundingRect(0, 0, text_width, 1000, Qt.TextFlag.TextWordWrap, description).height()

        tags = index.data(TaskRoles.AttachmentSummary) or []
        total_height = title_height + desc_height
        if description:
            total_height += self.TEXT_GAP
        if tags:
            total_height += self.TEXT_GAP + self._tags_height(tags, text_width)
        total_height += self.TEXT_V_PAD * 2
        total_height = max(total_height, self.ROW_H_EXPANDED_MIN)
        return QSize(option_rect.width(), total_height)

    def _tags_height(self, tags: List[str], max_width: int) -> int:
        if not tags:
            return 0
        metrics = QFontMetrics(self._font_small)
        line_width = 0
        lines = 1
        for tag in tags:
            tag_width = metrics.horizontalAdvance(tag) + self.TAG_PAD_X * 2
            if line_width > 0 and line_width + tag_width > max_width:
                lines += 1
                line_width = 0
            line_width += tag_width + self.TAG_GAP
        return lines * self.TAG_H + (lines - 1) * self.TAG_LINE_GAP

    def _draw_tags(self, painter: QPainter, start: QPoint, max_width: int, tags: List[str]) -> None:
        if not tags:
            return
        metrics = QFontMetrics(self._font_small)
        x = start.x()
        y = start.y()
        painter.setFont(self._font_small)
        for tag in tags:
            tag_width = metrics.horizontalAdvance(tag) + self.TAG_PAD_X * 2
            if x > start.x() and x + tag_width > start.x() + max_width:
                x = start.x()
                y += self.TAG_H + self.TAG_LINE_GAP
            rect = QRect(x, y, tag_width, self.TAG_H)
            painter.setPen(QColor("#3a3b40"))
            painter.setBrush(QColor("#1f2227"))
            painter.drawRoundedRect(rect, 8, 8)
            painter.setPen(self.C_DIM)
            painter.drawText(rect.adjusted(self.TAG_PAD_X, 0, -self.TAG_PAD_X, 0), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, tag)
            x += tag_width + self.TAG_GAP

    def _header_quick_rect(
        self,
        row_rect: QRect,
        header_text: str,
        include_today_badge: bool = False,
    ) -> QRect:
        metrics = QFontMetrics(self._font_header)
        text_left = row_rect.left() + 10
        text_width = metrics.horizontalAdvance(header_text)
        today_badge_width = metrics.horizontalAdvance("СЕГОДНЯ") if include_today_badge else 0
        quick_width = 116
        quick_height = row_rect.height()
        quick_x = text_left + text_width + 14 + today_badge_width
        max_right = row_rect.right() - 12
        if quick_x + quick_width > max_right:
            quick_x = max(text_left + 10, max_right - quick_width)
        return QRect(quick_x, row_rect.top(), quick_width, quick_height)

    @staticmethod
    def _task_quick_rect(layout: dict, row_rect: QRect) -> QRect:
        quick_width = 22
        quick_height = row_rect.height()
        toggle_rect = layout.get("subtask_toggle")
        if isinstance(toggle_rect, QRect) and not toggle_rect.isNull():
            anchor_left = toggle_rect.left()
        else:
            doc_rect = layout.get("doc")
            anchor_left = doc_rect.left() if isinstance(doc_rect, QRect) else row_rect.left() + 80
        quick_x = max(row_rect.left() + 8, anchor_left - quick_width - 4)
        return QRect(quick_x, row_rect.top(), quick_width, quick_height)

    def _marker_theme_asset_pixmap(self, marker_theme: str) -> QPixmap:
        theme_key = (marker_theme or "").strip().lower()
        if not theme_key:
            return QPixmap()
        cached = self._marker_theme_pixmap_cache.get(theme_key)
        if cached is not None:
            return cached
        asset_name = self._marker_theme_asset_names.get(theme_key)
        if not asset_name:
            pixmap = QPixmap()
            self._marker_theme_pixmap_cache[theme_key] = pixmap
            return pixmap
        asset_path = Path(__file__).resolve().parents[2] / "assets" / "badge" / asset_name
        pixmap = QPixmap(str(asset_path))
        self._marker_theme_pixmap_cache[theme_key] = pixmap
        return pixmap

    def _draw_marker_theme_overlay(self, painter: QPainter, row_rect: QRect, marker_theme: str) -> None:
        theme_key = (marker_theme or "").strip().lower()
        if not theme_key:
            return
        overlay_rect = QRect(
            row_rect.right() - 118,
            row_rect.top() + 2,
            112,
            max(18, row_rect.height() - 4),
        )
        asset_pixmap = self._marker_theme_asset_pixmap(theme_key)
        if not asset_pixmap.isNull():
            themed_pixmap = asset_pixmap.scaled(
                overlay_rect.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            target_rect = QRect(
                overlay_rect.right() - themed_pixmap.width(),
                overlay_rect.center().y() - themed_pixmap.height() // 2,
                themed_pixmap.width(),
                themed_pixmap.height(),
            )
            painter.save()
            painter.setOpacity(0.14)
            painter.drawPixmap(target_rect, themed_pixmap)
            painter.restore()
            return
        theme_icon = self._marker_theme_icons.get(theme_key)
        if theme_icon is None:
            return
        icon_rect = QRect(
            overlay_rect.center().x() - 10,
            overlay_rect.center().y() - 10,
            20,
            20,
        )
        painter.save()
        painter.setOpacity(0.2)
        theme_icon.paint(painter, icon_rect)
        painter.restore()

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        """Рисует строку задачи или заголовок дня."""
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        row_type = index.data(TaskRoles.RowType)
        r = getattr(option, "rect", QRect())
        option_state = getattr(option, "state", QStyle.StateFlag.State_None)

        if row_type == "header":
            d: date = index.data(TaskRoles.Day)
            txt = self._format_header(d)
            show_today = should_show_today_badge(d)
            painter.fillRect(r, self.C_BG)

            painter.setPen(self.C_DIM)
            painter.setFont(self._font_header)
            quick_rect = self._header_quick_rect(r, txt, include_today_badge=show_today)
            text_rect = QRect(r.left() + 10, r.top(), quick_rect.left() - r.left() - 18, r.height())
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, txt)

            if show_today:
                metrics = QFontMetrics(self._font_header)
                base_width = metrics.horizontalAdvance(txt)
                today_rect = QRect(
                    text_rect.left() + base_width + 6,
                    text_rect.top(),
                    text_rect.width() - base_width - 6,
                    text_rect.height(),
                )
                painter.setPen(self.C_TODAY)
                painter.drawText(today_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "СЕГОДНЯ")

            painter.setPen(self.C_BORDER)
            painter.drawLine(r.left() + 10, r.bottom(), r.right() - 10, r.bottom())
            if option_state & QStyle.StateFlag.State_MouseOver:
                painter.fillRect(quick_rect, QColor("#1f2227"))
                painter.setPen(self.C_BORDER)
                painter.drawLine(quick_rect.left(), quick_rect.top(), quick_rect.left(), quick_rect.bottom())
                painter.drawLine(quick_rect.right(), quick_rect.top(), quick_rect.right(), quick_rect.bottom())
                painter.setFont(self._font_small)
                painter.setPen(self.C_DIM)
                text_rect = quick_rect.adjusted(10, 0, -10, 0)
                painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, "Добавить задачу")
            painter.restore()
            return
        if row_type == "sort_header":
            sort_key = index.data(TaskRoles.SortKey) or "date"
            sort_dir = index.data(TaskRoles.SortDirection) or "asc"
            arrow = "▲" if sort_dir == "asc" else "▼"
            painter.fillRect(r, self.C_BG)

            layout = self._row_layout(r)
            painter.setFont(self._font_header)
            painter.setPen(self.C_DIM)
            painter.drawText(layout["date"], Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                             f"Дата {arrow}" if sort_key == "date" else "Дата")
            painter.drawText(layout["title"], Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                             f"Название {arrow}" if sort_key == "title" else "Название")
            painter.drawText(layout["priority"], Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                             f"Приоритет {arrow}" if sort_key == "priority" else "Приоритет")

            painter.setPen(self.C_BORDER)
            painter.drawLine(r.left() + 10, r.bottom(), r.right() - 10, r.bottom())
            painter.restore()
            return

        day: date = index.data(TaskRoles.Day)
        time_text: str = index.data(TaskRoles.DisplayTime) or ""
        title: str = index.data(Qt.ItemDataRole.DisplayRole) or ""
        description: str = index.data(TaskRoles.Description) or ""
        project_title: str = index.data(TaskRoles.ProjectTitle) or ""
        project_area: str = index.data(TaskRoles.ProjectArea) or ""
        recurrence_kind: str = (index.data(TaskRoles.RecurrenceKind) or "").strip().lower()
        marker_color: str = (index.data(TaskRoles.MarkerColor) or "").strip()
        marker_theme: str = (index.data(TaskRoles.MarkerTheme) or "").strip()
        priority: str = index.data(TaskRoles.Priority) or "Medium"
        done: bool = bool(index.data(TaskRoles.Done))
        completion_delay_minutes = max(0, int(index.data(TaskRoles.CompletionDelayMinutes) or 0))
        overdue = self._is_overdue(day, done)
        show_completion_delay = done and completion_delay_minutes > 4 * 60
        completion_delay_text = self._format_completion_delay(completion_delay_minutes) if show_completion_delay else ""
        expanded = bool(index.data(TaskRoles.Expanded))
        has_subtasks = bool(index.data(TaskRoles.HasSubtasks))
        subtasks_expanded = bool(index.data(TaskRoles.SubtasksExpanded))
        depth = int(index.data(TaskRoles.SubtaskDepth) or 0)

        bg = self.C_ROW if (index.row() % 2 == 0) else self.C_ROW_ALT
        selected = bool(option_state & QStyle.StateFlag.State_Selected)
        if selected:
            bg = QColor("#343844")
        bg = blend_task_row_background(bg, marker_color, selected=selected)

        painter.fillRect(r, bg)
        self._draw_marker_theme_overlay(painter, r, marker_theme)
        painter.setPen(self.C_BORDER)
        painter.drawRect(r.adjusted(0, 0, -1, -1))

        layout = self._row_layout(r, depth, has_subtasks)
        cy = r.center().y()

        grip_rect = layout["grip"]
        self._icon_grip.paint(painter, grip_rect)

        cb_rect = layout["checkbox"]
        painter.setPen(self.C_BORDER)
        painter.setBrush(QColor("#16171a"))
        painter.drawRect(cb_rect)

        if done:
            painter.setPen(QColor("#cfcfcf"))
            check_pad = max(3, min(8, cb_rect.height() // 4))
            painter.drawLine(
                cb_rect.left() + check_pad,
                cb_rect.center().y(),
                cb_rect.center().x() - 1,
                cb_rect.bottom() - check_pad,
            )
            painter.drawLine(
                cb_rect.center().x() - 1,
                cb_rect.bottom() - check_pad,
                cb_rect.right() - check_pad,
                cb_rect.top() + check_pad,
            )

        painter.setFont(self._font_small)
        painter.setPen(self.C_OVERDUE if overdue else self.C_DIM)
        time_rect = layout["date"]
        painter.drawText(time_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, time_text)

        tomorrow_rect = layout["tomorrow"]
        painter.setPen(self.C_BORDER)
        painter.setBrush(QColor("#1f2227"))
        painter.drawRect(tomorrow_rect)
        self._icon_tomorrow.paint(painter, QRect(tomorrow_rect.left() + 3, tomorrow_rect.top() + 3, 14, 14))

        project_rect = layout["project"]
        if project_title:
            painter.setFont(self._font_small)
            painter.setPen(self.C_DIM)
            display_project = f"{project_area} / {project_title}" if project_area else project_title
            if recurrence_kind in {"daily", "weekly", "monthly"}:
                display_project = f"{display_project} · REC"
            if marker_theme:
                display_project = f"{display_project} · {marker_theme.upper()}"
            elided_project = QFontMetrics(self._font_small).elidedText(
                display_project,
                Qt.TextElideMode.ElideRight,
                project_rect.width(),
            )
            painter.drawText(project_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, elided_project)

        icon_rect = layout["doc"]
        self._icon_doc.paint(painter, icon_rect)

        if has_subtasks:
            toggle_rect = layout["subtask_toggle"]
            toggle_icon = self._icon_subtask_open if subtasks_expanded else self._icon_subtask_closed
            toggle_icon.paint(painter, toggle_rect)

        painter.setFont(self._font)
        if done:
            title_color = self.C_DIM
        elif overdue:
            title_color = self.C_OVERDUE
        else:
            title_color = self.C_TEXT
        painter.setPen(title_color)

        menu_rect = layout["menu"]
        pr_rect = layout["priority"]
        title_rect = layout["title"]
        parent_move_rect, parent_move_target, parent_move_text = self._parent_schedule_action(index, r)
        title_content_rect = title_rect
        if not parent_move_rect.isNull():
            title_content_rect = title_rect.adjusted(0, 0, -(parent_move_rect.width() + self.PARENT_MOVE_BUTTON_GAP), 0)
        quick_rect = self._task_quick_rect(layout, r)
        if expanded:
            title_box = QRect(
                title_content_rect.left(),
                r.top() + self.TEXT_V_PAD,
                title_content_rect.width(),
                r.height() - self.TEXT_V_PAD * 2,
            )
            painter.drawText(title_box, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap, title)

            title_metrics = QFontMetrics(self._font)
            title_height = title_metrics.boundingRect(
                0, 0, title_content_rect.width(), 1000, Qt.TextFlag.TextWordWrap, title
            ).height()
            current_y = r.top() + self.TEXT_V_PAD + title_height

            if completion_delay_text:
                delay_box = QRect(
                    title_content_rect.left(),
                    current_y + self.TEXT_GAP,
                    title_content_rect.width(),
                    title_metrics.height(),
                )
                painter.setPen(self.C_OVERDUE)
                painter.drawText(delay_box, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, completion_delay_text)
                painter.setPen(title_color)
                current_y += self.TEXT_GAP + title_metrics.height()

            if description:
                desc_box = QRect(
                    title_content_rect.left(),
                    current_y + self.TEXT_GAP,
                    title_content_rect.width(),
                    r.height() - self.TEXT_V_PAD * 2 - title_height - self.TEXT_GAP,
                )
                painter.setFont(self._font_small)
                painter.setPen(self.C_DIM if not overdue else self.C_OVERDUE)
                painter.drawText(desc_box, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap, description)
                painter.setFont(self._font)
                desc_metrics = QFontMetrics(self._font_small)
                desc_height = desc_metrics.boundingRect(
                    0, 0, title_content_rect.width(), 1000, Qt.TextFlag.TextWordWrap, description
                ).height()
                current_y += self.TEXT_GAP + desc_height

            tags = index.data(TaskRoles.AttachmentSummary) or []
            if tags:
                current_y += self.TEXT_GAP
                self._draw_tags(painter, QPoint(title_content_rect.left(), current_y), title_content_rect.width(), tags)
        else:
            title_metrics = QFontMetrics(self._font)
            if completion_delay_text:
                delay_text = f" {completion_delay_text}"
                delay_width = title_metrics.horizontalAdvance(delay_text)
                title_width = max(40, title_content_rect.width() - delay_width)
                title_part = title_metrics.elidedText(title, Qt.TextElideMode.ElideRight, title_width)
                title_part_rect = QRect(title_content_rect.left(), title_content_rect.top(), title_width, title_content_rect.height())
                delay_part_rect = QRect(
                    title_part_rect.right(),
                    title_content_rect.top(),
                    title_content_rect.width() - title_width,
                    title_content_rect.height(),
                )
                painter.setPen(title_color)
                painter.drawText(title_part_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, title_part)
                painter.setPen(self.C_OVERDUE)
                painter.drawText(delay_part_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, delay_text)
                painter.setPen(title_color)
            else:
                elided = title_metrics.elidedText(title, Qt.TextElideMode.ElideRight, title_content_rect.width())
                painter.drawText(title_content_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, elided)

        if not parent_move_rect.isNull() and parent_move_target is not None:
            painter.setPen(QColor("#8a6a15"))
            painter.setBrush(QColor("#f2c14e"))
            painter.drawRoundedRect(parent_move_rect, 6, 6)
            painter.setFont(self._font_small)
            painter.setPen(QColor("#2d250f"))
            text_rect = parent_move_rect.adjusted(
                self.PARENT_MOVE_BUTTON_PAD_X,
                0,
                -self.PARENT_MOVE_BUTTON_PAD_X,
                0,
            )
            text = QFontMetrics(self._font_small).elidedText(parent_move_text, Qt.TextElideMode.ElideRight, text_rect.width())
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)

        # --- PRIORITY BLOCK (fixed layout) ---
        value_text = "OVERDUE" if overdue else priority
        value_color = self.C_OVERDUE if overdue else self._prio_color(priority)
        priority_hovered = bool(option_state & QStyle.StateFlag.State_MouseOver)
        priority_chip_rect = pr_rect.adjusted(2, 6, -2, -6)
        painter.setPen(QColor("#3a3b40"))
        painter.setBrush(QColor("#21252d") if priority_hovered else QColor("#1a1d23"))
        painter.drawRoundedRect(priority_chip_rect, 6, 6)

        # Жёсткая сетка справа
        icon_w = 18
        value_w = 72
        gap = 10
        label_w = priority_chip_rect.width() - value_w - icon_w - gap

        value_rect = QRect(
            priority_chip_rect.left() + label_w,
            priority_chip_rect.top(),
            value_w,
            priority_chip_rect.height()
        )

        icon_rect = QRect(
            priority_chip_rect.right() - icon_w,
            cy - 8,
            16,
            16
        )

        painter.setFont(self._font_small)

        # label
        painter.setPen(self.C_DIM)
        # painter.drawText(label_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, "приоритет")

        # value
        painter.setPen(value_color)
        painter.drawText(value_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, value_text)

        # icon
        self._icon_fire.paint(painter, icon_rect)

        painter.setPen(self.C_BORDER)
        painter.setBrush(QColor("#1f2227"))
        painter.drawRect(menu_rect)
        self._icon_menu.paint(painter, QRect(menu_rect.center().x() - 5, menu_rect.center().y() - 7, 14, 14))
        if option_state & QStyle.StateFlag.State_MouseOver:
            painter.fillRect(quick_rect, QColor("#1f2227"))
            painter.setPen(self.C_BORDER)
            painter.drawLine(quick_rect.left(), quick_rect.top(), quick_rect.left(), quick_rect.bottom())
            painter.drawLine(quick_rect.right(), quick_rect.top(), quick_rect.right(), quick_rect.bottom())
            icon_size = 12
            self._icon_quick_add.paint(
                painter,
                QRect(
                    quick_rect.center().x() - (icon_size // 2),
                    quick_rect.center().y() - (icon_size // 2),
                    icon_size,
                    icon_size,
                ),
            )


        painter.restore()

    def editorEvent(
        self,
        event: QEvent,
        model: QAbstractItemModel,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> bool:
        """Обрабатывает клики по флажку и меню строки."""
        row_type = index.data(TaskRoles.RowType)
        if row_type == "sort_header":
            if event.type() == QEvent.Type.MouseButtonRelease and isinstance(event, QMouseEvent) and event.button() == Qt.MouseButton.LeftButton:
                pos = event.position().toPoint()
                layout = self._row_layout(getattr(option, "rect", QRect()))
                tasks_model = self._tasks_model(model)
                if layout["title"].contains(pos):
                    if tasks_model is not None:
                        tasks_model.set_sort("title")
                    return True
                if layout["date"].contains(pos):
                    if tasks_model is not None:
                        tasks_model.set_sort("date")
                    return True
                if layout["priority"].contains(pos):
                    if tasks_model is not None:
                        tasks_model.set_sort("priority")
                    return True
            return False
        if row_type == "header":
            if event.type() == QEvent.Type.MouseButtonRelease and isinstance(event, QMouseEvent) and event.button() == Qt.MouseButton.LeftButton:
                pos = event.position().toPoint()
                r = getattr(option, "rect", QRect())
                header_day = index.data(TaskRoles.Day)
                header_text = self._format_header(header_day) if isinstance(header_day, date) else ""
                quick_rect = self._header_quick_rect(
                    r,
                    header_text,
                    include_today_badge=(
                        isinstance(header_day, date) and should_show_today_badge(header_day)
                    ),
                )
                tasks_model = self._tasks_model(model)
                if quick_rect.contains(pos) and tasks_model is not None:
                    target_day = index.data(TaskRoles.Day)
                    if isinstance(target_day, date):
                        tasks_model.quick_add_task_for_day(target_day)
                        return True
            return False
        if row_type != "task":
            return False

        if event.type() == QEvent.Type.MouseButtonRelease and isinstance(event, QMouseEvent) and event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            r = getattr(option, "rect", QRect())
            tasks_model = self._tasks_model(model)
            if tasks_model is None:
                return False

            depth = int(index.data(TaskRoles.SubtaskDepth) or 0)
            has_subtasks = bool(index.data(TaskRoles.HasSubtasks))
            layout = self._row_layout(r, depth, has_subtasks)
            cb_rect = layout.get("checkbox_hit", layout["checkbox"])
            tomorrow_rect = layout["tomorrow"]
            menu_rect = layout["menu"]
            priority_rect = layout["priority"]
            toggle_rect = layout.get("subtask_toggle")
            parent_move_rect, parent_move_target, _ = self._parent_schedule_action(index, r)
            quick_rect = self._task_quick_rect(layout, r)

            if has_subtasks and bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
                title_rect = layout.get("title")
                if (
                    (isinstance(toggle_rect, QRect) and toggle_rect.contains(pos))
                    or (isinstance(title_rect, QRect) and title_rect.contains(pos))
                ):
                    tasks_model.expand_subtasks_tree_by_row(index.row())
                    return True

            if has_subtasks and toggle_rect and toggle_rect.contains(pos):
                tasks_model.toggle_subtasks_expanded_by_row(index.row())
                return True

            if tomorrow_rect.contains(pos):
                task = tasks_model.task_at_row(index.row())
                if task is not None:
                    new_day = tasks_model.next_day_for_task(task)
                    tasks_model.move_task_to_day(task.id, new_day)
                return True

            if not parent_move_rect.isNull() and parent_move_target is not None and parent_move_rect.contains(pos):
                task = tasks_model.task_at_row(index.row())
                if task is not None:
                    tasks_model.move_task_to_parent_schedule(task.id, parent_move_target.id)
                return True

            if cb_rect.contains(pos):
                # confirm только если ставим done=True
                currently_done = bool(index.data(TaskRoles.Done))
                if not currently_done:
                    option_widget = getattr(option, "widget", None)
                    parent = option_widget if isinstance(option_widget, QWidget) else None
                    dialog = ConfirmDialog(
                        "Подтверждение",
                        "Пометить задачу выполненной?",
                        parent=parent,
                        confirm_text="Да",
                        cancel_text="Отмена",
                    )
                    if exec_with_overlay(dialog, parent) != QDialog.DialogCode.Accepted:
                        return True  # событие обработали, но действие отменили

                tasks_model.toggle_done_by_row(index.row())
                return True

            if menu_rect.contains(pos):
                self._show_row_menu(index)
                return True
            if priority_rect.contains(pos):
                tasks_model.cycle_priority_by_row(index.row())
                return True
            if quick_rect.contains(pos):
                task = tasks_model.task_at_row(index.row())
                if task is not None:
                    tasks_model.quick_add_subtask(task.id)
                    return True

        if event.type() == QEvent.Type.MouseButtonRelease and isinstance(event, QMouseEvent) and event.button() == Qt.MouseButton.RightButton:
            pos = event.position().toPoint()
            r = getattr(option, "rect", QRect())
            depth = int(index.data(TaskRoles.SubtaskDepth) or 0)
            has_subtasks = bool(index.data(TaskRoles.HasSubtasks))
            layout = self._row_layout(r, depth, has_subtasks)
            if layout["menu"].contains(pos) or r.contains(pos):
                self._show_row_menu(index)
                return True

        return False

    def _show_row_menu(self, index: QModelIndex):
        """Отображает контекстное меню строки."""
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
        act_open = menu.addAction("Открыть")
        menu.addSeparator()
        act_edit = menu.addAction("Редактировать")
        attachment_actions: Dict[QAction, TaskAttachmentData] = {}
        tasks_model = self._tasks_model(index.model())
        task = tasks_model.task_at_row(index.row()) if tasks_model is not None else None
        if task is not None:
            attachments = get_database().fetch_task_attachments(task.id)
            if attachments:
                attachments_menu = menu.addMenu("Вложения")
                for attachment in attachments[:12]:
                    display_name = self._attachment_display_name(attachment)
                    action = attachments_menu.addAction(
                        f"{attachment_kind_label(attachment.kind)}: {display_name}"
                    )
                    attachment_actions[action] = attachment
                menu.addSeparator()
        act_del = menu.addAction("Удалить")

        chosen = menu.exec(QCursor.pos())
        if chosen == act_open:
            self._open_task_view(index)
            return
        if chosen == act_edit:
            self._edit_task(index)
            return
        attachment = attachment_actions.get(chosen)
        if attachment is not None:
            self._open_attachment_preview(attachment)
            return
        if chosen != act_del:
            return

        # confirm delete
        title = index.data(TaskRoles.Title) or "задачу"
        parent = menu.parentWidget() or None
        dialog = ConfirmDialog(
            "Удалить задачу",
            f"Удалить задачу:\n«{title}» ?",
            parent=parent,
            confirm_text="Удалить",
            cancel_text="Отмена",
        )
        if exec_with_overlay(dialog, parent) != QDialog.DialogCode.Accepted:
            return

        if tasks_model is not None:
            tasks_model.delete_task_by_row(index.row())

    @staticmethod
    def _attachment_display_name(attachment: TaskAttachmentData) -> str:
        db = get_database()
        kind = (attachment.kind or "").strip().lower()
        if kind == "note":
            note = next((item for item in db.fetch_notes() if item.id == attachment.ref_id), None)
            return note.title if note is not None else f"id={attachment.ref_id}"
        if kind == "idea":
            idea = next((item for item in db.fetch_ideas(archived=True) if item.id == attachment.ref_id), None)
            return idea.title if idea is not None else f"id={attachment.ref_id}"
        if kind == "object":
            obj = next((item for item in db.fetch_objects() if item.id == attachment.ref_id), None)
            return obj.title if obj is not None else f"id={attachment.ref_id}"
        if kind == "map":
            map_item = next((item for item in db.fetch_maps() if item.id == attachment.ref_id), None)
            return map_item.title if map_item is not None else f"id={attachment.ref_id}"
        if kind == "marker":
            marker = next((item for item in db.fetch_map_markers() if item.id == attachment.ref_id), None)
            return marker.name if marker is not None else f"id={attachment.ref_id}"
        if kind in {"file", "image"}:
            cloud_file = next((item for item in db.fetch_cloud_files() if item.id == attachment.ref_id), None)
            if cloud_file is None:
                return f"id={attachment.ref_id}"
            return cloud_file.name or cloud_file.rel_path or f"id={attachment.ref_id}"
        return f"id={attachment.ref_id}"

    def _open_attachment_preview(self, attachment: TaskAttachmentData) -> None:
        db = get_database()
        parent = self.parent() if isinstance(self.parent(), QWidget) else None
        title = attachment_kind_label(attachment.kind)
        kind = (attachment.kind or "").strip().lower()
        if kind == "note":
            note = next((item for item in db.fetch_notes() if item.id == attachment.ref_id), None)
            if note is None:
                QMessageBox.information(parent, title, "Вложенная заметка не найдена.")
                return
            QMessageBox.information(parent, title, f"{note.title}\n\n{(note.preview or '').strip()[:700]}")
            return
        if kind == "idea":
            idea = next((item for item in db.fetch_ideas(archived=True) if item.id == attachment.ref_id), None)
            if idea is None:
                QMessageBox.information(parent, title, "Вложенная идея не найдена.")
                return
            summary = (idea.summary or "").strip()
            details = (idea.body_md or "").strip()
            text = f"{idea.title}\n\n{summary or details[:700]}"
            QMessageBox.information(parent, title, text)
            return
        if kind == "object":
            obj = next((item for item in db.fetch_objects() if item.id == attachment.ref_id), None)
            if obj is None:
                QMessageBox.information(parent, title, "Вложенный объект не найден.")
                return
            details = (obj.description or "").strip()
            QMessageBox.information(parent, title, f"{obj.title}\n\n{details[:700]}")
            return
        if kind == "map":
            map_item = next((item for item in db.fetch_maps() if item.id == attachment.ref_id), None)
            if map_item is None:
                QMessageBox.information(parent, title, "Вложенная карта не найдена.")
                return
            QMessageBox.information(parent, title, f"{map_item.title}\n\nПроект: {map_item.project or '—'}")
            return
        if kind == "marker":
            marker = next((item for item in db.fetch_map_markers() if item.id == attachment.ref_id), None)
            if marker is None:
                QMessageBox.information(parent, title, "Вложенная метка карты не найдена.")
                return
            QMessageBox.information(parent, title, f"{marker.name}\n\nТип: {marker.type}")
            return
        if kind in {"file", "image"}:
            cloud_file = next((item for item in db.fetch_cloud_files() if item.id == attachment.ref_id), None)
            if cloud_file is None:
                QMessageBox.information(parent, title, "Вложенный файл не найден.")
                return
            cloud_root = db.get_setting("cloud_storage_path", default="").strip()
            relative_path = cloud_file.rel_path or cloud_file.name
            full_path = str((Path(cloud_root) / relative_path) if cloud_root else Path(relative_path))
            QMessageBox.information(parent, title, f"{cloud_file.name}\n\n{full_path}")
            return
        QMessageBox.information(parent, title, f"Вложение id={attachment.ref_id}")

    def _edit_task(self, index: QModelIndex):
        """Открывает диалог редактирования задачи."""
        tasks_model = self._tasks_model(index.model())
        if tasks_model is None:
            return

        task = tasks_model.task_at_row(index.row())
        if task is None:
            return

        parent = self.parent() if isinstance(self.parent(), QWidget) else None
        dialog = TaskEditDialog(task, parent=parent)
        if exec_with_overlay(dialog, parent) != QDialog.DialogCode.Accepted:
            return

        values = dialog.values()
        try:
            tasks_model.update_task_by_row(
                index.row(),
                title=values["title"],
                description=values["description"],
                day=values["day"],
                time_text=values["time_text"],
                priority=values["priority"],
                done=values["done"],
                project_id=values["project_id"],
                recurrence_kind=values["recurrence_kind"],
                recurrence_interval=values["recurrence_interval"],
                marker_color=values["marker_color"],
                marker_theme=values["marker_theme"],
            )
        except ValueError as exc:
            QMessageBox.warning(parent or self.parent(), "Проверка", str(exc))

    def edit_task(self, index: QModelIndex) -> None:
        self._edit_task(index)

    def _open_task_view(self, index: QModelIndex) -> None:
        tasks_model = self._tasks_model(index.model())
        if tasks_model is None:
            return
        task = tasks_model.task_at_row(index.row())
        if task is None:
            return
        parent = self.parent() if isinstance(self.parent(), QWidget) else None
        dialog = TaskDetailsDialog(task, parent=parent)
        exec_with_overlay(dialog, parent)

    def open_task_view(self, index: QModelIndex) -> None:
        self._open_task_view(index)

    def _prio_color(self, p: str) -> QColor:
        """Возвращает цвет для приоритета."""
        p = (p or "").lower()
        if p == "high":
            return self.C_HIGH
        if p == "low":
            return self.C_LOW
        if p == "отложенная":
            return self.C_DEFER
        return self.C_MED

    @staticmethod
    def _is_overdue(d: date, done: bool) -> bool:
        """Проверяет, просрочена ли задача."""
        return (d < date.today()) and (not done)

    @staticmethod
    def _format_header(d: date) -> str:
        """Формирует подпись для заголовка дня."""
        wd = WEEKDAY_RU[d.weekday()]
        return f"{d.isoformat()} — {wd}"

    def format_header(self, d: date) -> str:
        return self._format_header(d)

    @staticmethod
    def _format_completion_delay(delay_minutes: int) -> str:
        """Формирует подпись расхождения по факту выполнения."""
        minutes = max(0, int(delay_minutes or 0))
        days = minutes // (24 * 60)
        hours = (minutes % (24 * 60)) // 60
        return f"(Просрочена: {days}д {hours}ч)"

    def _parent_schedule_action(self, index: QModelIndex, row_rect: QRect) -> Tuple[QRect, Optional[TaskRow], str]:
        """Возвращает геометрию и данные кнопки переноса на срок родителя."""
        parent_id = index.data(TaskRoles.ParentTaskId)
        if parent_id is None:
            return QRect(), None, ""

        done = bool(index.data(TaskRoles.Done))
        task_day: date = index.data(TaskRoles.Day)
        if not self._is_overdue(task_day, done):
            return QRect(), None, ""

        model = index.model()
        tasks_model = self._tasks_model(model)
        if tasks_model is None:
            return QRect(), None, ""
        parent_task = tasks_model.task_by_id(parent_id)
        if parent_task is None:
            return QRect(), None, ""
        if self._is_overdue(parent_task.day, parent_task.done):
            return QRect(), None, ""

        depth = int(index.data(TaskRoles.SubtaskDepth) or 0)
        has_subtasks = bool(index.data(TaskRoles.HasSubtasks))
        expanded = bool(index.data(TaskRoles.Expanded))
        layout = self._row_layout(row_rect, depth, has_subtasks)
        title_rect = layout["title"]
        text = self._format_parent_schedule_text(parent_task)
        rect = self._parent_schedule_button_rect(title_rect, text, expanded)
        if rect.isNull():
            return QRect(), None, ""
        return rect, parent_task, text

    @staticmethod
    def _format_parent_schedule_text(parent_task: TaskRow) -> str:
        if parent_task.time_text:
            return f"Перенести на {parent_task.day.isoformat()} {parent_task.time_text}"
        return f"Перенести на {parent_task.day.isoformat()}"

    def _parent_schedule_button_rect(self, title_rect: QRect, text: str, expanded: bool) -> QRect:
        """Строит прямоугольник кнопки переноса справа от заголовка."""
        available_width = title_rect.width() - 20
        if available_width < 160:
            return QRect()
        metrics = QFontMetrics(self._font_small)
        target_width = metrics.horizontalAdvance(text) + self.PARENT_MOVE_BUTTON_PAD_X * 2
        button_width = min(max(180, target_width), min(420, available_width))
        button_height = self.PARENT_MOVE_BUTTON_H
        x = title_rect.right() - button_width
        if expanded:
            y = title_rect.top() + self.TEXT_V_PAD
        else:
            y = title_rect.center().y() - (button_height // 2)
        return QRect(x, y, button_width, button_height)

    def _row_layout(self, r: QRect, depth: int = 0, has_subtasks: bool = False) -> dict:
        """Возвращает прямоугольники основных колонок строки."""
        x = r.left() + 10
        cy = r.center().y()

        grip_rect = QRect(x, cy - 8, 16, 16)
        x += 22

        checkbox_slot_side = max(18, r.height())
        checkbox_side = max(10, r.height() // 2)
        checkbox_y = cy - (checkbox_side // 2)
        checkbox_x = x + (checkbox_slot_side - checkbox_side) // 2
        cb_rect = QRect(checkbox_x, checkbox_y, checkbox_side, checkbox_side)
        cb_hit_rect = QRect(x, r.top(), checkbox_slot_side, r.height())
        x += checkbox_slot_side + 8

        tomorrow_rect = QRect(x, cy - 8, 20, 20)
        x += 28

        time_rect = QRect(x, r.top(), self.TIME_W, r.height())
        x += self.TIME_W + 6

        project_rect = QRect(x, r.top(), self.PROJECT_W, r.height())
        x += self.PROJECT_W + 6

        indent = max(0, depth) * 14
        x += indent

        toggle_w = 16 if has_subtasks else 0
        toggle_rect = QRect(x, cy - 8, toggle_w, 16)
        if has_subtasks:
            x += toggle_w + 4

        doc_rect = QRect(x, cy - 8, 16, 16)
        x += 22

        right_pad = 8
        menu_w = max(18, r.height())
        pr_w = 140
        menu_rect = QRect(r.right() - right_pad - menu_w, r.top(), menu_w, r.height())
        quick_rect = QRect()
        pr_rect = QRect(menu_rect.left() - pr_w - 8, r.top(), pr_w, r.height())
        title_rect = QRect(x, r.top(), pr_rect.left() - x - 10, r.height())

        return {
            "grip": grip_rect,
            "checkbox": cb_rect,
            "checkbox_hit": cb_hit_rect,
            "tomorrow": tomorrow_rect,
            "date": time_rect,
            "project": project_rect,
            "subtask_toggle": toggle_rect,
            "doc": doc_rect,
            "title": title_rect,
            "priority": pr_rect,
            "quick": quick_rect,
            "menu": menu_rect,
        }

    def row_layout(self, rect: QRect, depth: int = 0, has_subtasks: bool = False) -> dict:
        return self._row_layout(rect, depth, has_subtasks)

__all__ = ["TasksItemDelegate"]
