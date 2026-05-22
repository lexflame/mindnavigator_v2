"""Card delegate for ConceptBoard catalog columns."""

from __future__ import annotations

from ._shared import (
    QColor,
    QFont,
    QFontMetrics,
    QPainter,
    QPen,
    QSize,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    Qt,
)


class ConceptBoardDelegate(QStyledItemDelegate):
    """Draws a compact entity card for the board columns."""

    ROW_H = 126

    def __init__(
        self,
        parent=None,
        *,
        data_role: int = int(Qt.ItemDataRole.UserRole),
        row_height: int | None = None,
        stack_footer: bool = False,
    ) -> None:
        super().__init__(parent)
        self._data_role = int(data_role)
        self._row_height = max(80, int(row_height or self.ROW_H))
        self._stack_footer = bool(stack_footer)
        self._title_font = QFont()
        self._title_font.setPointSize(10)
        self._title_font.setBold(True)

        self._meta_font = QFont()
        self._meta_font.setPointSize(8)

        self._subtitle_font = QFont()
        self._subtitle_font.setPointSize(9)

        self._badge_font = QFont()
        self._badge_font.setPointSize(8)
        self._badge_font.setBold(True)

        self._footer_font = QFont()
        self._footer_font.setPointSize(8)

    def sizeHint(self, option: QStyleOptionViewItem, index):  # noqa: N802
        if index.data(self._data_role) is None:
            return super().sizeHint(option, index)
        return QSize(option.rect.width(), self._row_height)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:  # noqa: N802
        card = index.data(self._data_role)
        if card is None:
            super().paint(painter, option, index)
            return

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = option.rect.adjusted(6, 4, -6, -4)
        radius = 14
        background = QColor("#1f2632" if option.state & QStyle.StateFlag.State_Selected else "#121925")
        border = QColor(card.accent_color)
        border.setAlpha(210)
        painter.setBrush(background)
        painter.setPen(QPen(border, 1.2))
        painter.drawRoundedRect(rect, radius, radius)

        accent_rect = rect.adjusted(0, 0, 0, 0)
        accent_rect.setHeight(8)
        accent_fill = QColor(card.accent_color)
        painter.setBrush(accent_fill)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(accent_rect, 8, 8)

        inner_rect = rect.adjusted(10, 14, -10, -10)
        painter.setBrush(QColor(255, 255, 255, 10))
        painter.drawRoundedRect(inner_rect, 12, 12)

        x = rect.x() + 16
        y = rect.y() + 18
        width = rect.width() - 32

        badge_text = self._kind_badge_text(card.entity_kind)
        badge_width = max(58, len(badge_text) * 7 + 22)
        badge_rect = rect.adjusted(rect.width() - badge_width - 14, 16, -14, -(rect.height() - 38))
        painter.setBrush(accent_fill)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(badge_rect, 11, 11)
        painter.setFont(self._badge_font)
        painter.setPen(QColor("#ffffff"))
        painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, badge_text)

        painter.setFont(self._title_font)
        painter.setPen(QColor("#eef2fb"))
        title_width = max(10, badge_rect.x() - x - 10)
        title_metrics = QFontMetrics(self._title_font)
        title_text = title_metrics.elidedText(card.title, Qt.TextElideMode.ElideRight, title_width)
        painter.drawText(x, y + 14, title_text)

        painter.setFont(self._meta_font)
        painter.setPen(QColor("#8ea0b8"))
        meta_metrics = QFontMetrics(self._meta_font)
        meta_text = meta_metrics.elidedText(card.meta_text or card.entity_kind, Qt.TextElideMode.ElideRight, width)
        painter.drawText(x, y + 38, meta_text)

        painter.setFont(self._subtitle_font)
        painter.setPen(QColor("#c5cfdd"))
        subtitle_metrics = QFontMetrics(self._subtitle_font)
        subtitle = subtitle_metrics.elidedText(card.subtitle or "Без описания", Qt.TextElideMode.ElideRight, width)
        painter.drawText(x, y + 64, subtitle)

        footer_y = rect.bottom() - (48 if self._stack_footer else 30)
        painter.setFont(self._footer_font)
        painter.setPen(QColor("#73839a"))
        project_text = meta_metrics.elidedText(card.project_title or "Без проекта", Qt.TextElideMode.ElideRight, width // 2)
        painter.drawText(x, footer_y, project_text)

        links_text = meta_metrics.elidedText(card.link_summary, Qt.TextElideMode.ElideRight, 96)
        links_rect = (
            rect.adjusted(rect.width() - 114, rect.height() - 34, -14, -8)
            if self._stack_footer
            else rect.adjusted(rect.width() - 114, rect.height() - 40, -14, -12)
        )
        painter.setBrush(QColor(255, 255, 255, 12))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(links_rect, 10, 10)
        painter.setPen(QColor("#d8e4ff"))
        painter.drawText(links_rect, Qt.AlignmentFlag.AlignCenter, links_text)

        if getattr(card, "is_attached", False):
            attached_rect = rect.adjusted(16, rect.height() - 42, -(rect.width() - 100), -14)
            painter.setBrush(QColor(106, 213, 111, 36))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(attached_rect, 10, 10)
            painter.setPen(QColor("#bff0c2"))
            painter.drawText(attached_rect, Qt.AlignmentFlag.AlignCenter, "НА ДОСКЕ")

        painter.restore()

    @staticmethod
    def _kind_badge_text(entity_kind: str) -> str:
        return {
            "task": "TASK",
            "idea": "IDEA",
            "image": "IMAGE",
            "version": "VERSION",
            "solution": "SOLUTION",
            "file": "FILE",
            "link": "LINK",
            "map": "MAP",
            "marker": "MARKER",
            "note": "NOTE",
            "project": "PROJECT",
            "object": "OBJECT",
        }.get(entity_kind, entity_kind.upper())


ConceptBoardDelegate = ConceptBoardDelegate

__all__ = ["ConceptBoardDelegate", "ConceptBoardDelegate"]
