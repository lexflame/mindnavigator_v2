"""NoteCardDelegate class module for notes workspace."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403

class NoteCardDelegate(QStyledItemDelegate):
    ROW_H = 88

    def __init__(self, parent=None):
        super().__init__(parent)
        self._card_radius = 10

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        row_type = index.data(NoteRoles.RowType)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = option.rect.adjusted(6, 3, -6, -3)
        if row_type == "skeleton":
            self._paint_skeleton(painter, rect)
            painter.restore()
            return
        if row_type == "category":
            self._paint_category(painter, rect, index.data(NoteRoles.Title) or "")
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
        relation_summary = index.data(NoteRoles.RelationSummary) or ""
        preview_text = note_preview_line(preview)

        icon_y = rect.top() + 10
        icon_x = rect.right() - 18
        painter.setPen(Qt.PenStyle.NoPen)
        if index.data(NoteRoles.Locked):
            qta.icon("fa5s.lock", color="#8b8f96").paint(painter, QRect(icon_x, icon_y, 14, 14))
            icon_x -= 18
        if index.data(NoteRoles.Attachment):
            qta.icon("fa5s.paperclip", color="#8b8f96").paint(painter, QRect(icon_x, icon_y, 14, 14))
            icon_x -= 18
        if index.data(NoteRoles.Favorite):
            qta.icon("fa5s.star", color="#f4c560").paint(painter, QRect(icon_x, icon_y, 14, 14))

        text_right = icon_x - 8
        title_rect = QRect(rect.left() + 14, rect.top() + 9, text_right - rect.left() - 14, 20)
        preview_rect = QRect(rect.left() + 14, rect.top() + 30, text_right - rect.left() - 14, 18)
        meta_rect = QRect(rect.left() + 14, rect.bottom() - 26, rect.width() - 28, 16)

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
        painter.drawText(preview_rect, Qt.TextFlag.TextSingleLine, preview_text)

        painter.setPen(QColor("#6b7078"))
        meta_font = QFont()
        meta_font.setPointSize(8)
        painter.setFont(meta_font)
        tags_text = " ".join(f"#{tag}" for tag in tags[:3])
        meta_parts = [part for part in [tags_text, project, relation_summary] if part]
        if isinstance(updated, datetime):
            meta_parts.append(f"{updated:%d %b %H:%M}")
        meta_text = " | ".join(meta_parts) if meta_parts else "Без метаданных"
        painter.drawText(meta_rect, Qt.TextFlag.TextSingleLine, meta_text)

        painter.restore()

    def _paint_skeleton(self, painter: QPainter, rect: QRect):
        painter.setPen(QColor("#24272e"))
        painter.setBrush(QColor("#20232a"))
        painter.drawRoundedRect(rect, self._card_radius, self._card_radius)

        painter.setBrush(QColor("#2a2e36"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRect(rect.left() + 14, rect.top() + 14, rect.width() - 60, 12), 6, 6)
        painter.drawRoundedRect(QRect(rect.left() + 14, rect.top() + 40, rect.width() - 30, 10), 6, 6)
        painter.drawRoundedRect(QRect(rect.left() + 14, rect.top() + 58, rect.width() - 40, 10), 6, 6)
        painter.drawRoundedRect(QRect(rect.left() + 14, rect.bottom() - 32, rect.width() - 80, 10), 6, 6)

    @staticmethod
    def _paint_category(painter: QPainter, rect: QRect, title: str) -> None:
        painter.setPen(QColor("#343944"))
        center_y = rect.center().y()
        painter.drawLine(rect.left() + 6, center_y, rect.right() - 6, center_y)

        badge_width = max(120, min(rect.width() - 20, len(title) * 9 + 24))
        badge_rect = QRect(rect.left() + 14, rect.top(), badge_width, rect.height())
        painter.fillRect(badge_rect, QColor("#1a1d24"))
        painter.setPen(QColor("#8f959e"))
        badge_font = QFont()
        badge_font.setPointSize(8)
        badge_font.setBold(True)
        painter.setFont(badge_font)
        painter.drawText(
            badge_rect.adjusted(8, 0, -8, 0),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            title,
        )

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex):
        if index.data(NoteRoles.RowType) == "category":
            return QSize(260, 30)
        return QSize(260, self.ROW_H)

__all__ = ["NoteCardDelegate"]
