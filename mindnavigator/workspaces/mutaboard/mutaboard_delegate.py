"""Mixed-card delegate for MutaBoard board columns."""

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
    Qt,
)


class MutaBoardDelegate(QStyledItemDelegate):
    """Draws a compact mixed-entity card for the board columns."""

    ROW_H = 92

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
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

    def sizeHint(self, option, index):  # noqa: N802
        return QSize(option.rect.width(), self.ROW_H)

    def paint(self, painter, option, index) -> None:  # noqa: N802
        card = index.data(Qt.ItemDataRole.UserRole)
        if card is None:
            super().paint(painter, option, index)
            return

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = option.rect.adjusted(6, 4, -6, -4)
        radius = 10
        background = QColor("#21262f" if option.state & QStyle.StateFlag.State_Selected else "#171c24")
        border = QColor(card.accent_color)
        border.setAlpha(200)
        painter.setBrush(background)
        painter.setPen(QPen(border, 1.1))
        painter.drawRoundedRect(rect, radius, radius)

        accent_rect = rect.adjusted(0, 0, 0, 0)
        accent_rect.setWidth(5)
        accent_fill = QColor(card.accent_color)
        painter.setBrush(accent_fill)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(accent_rect, 4, 4)

        x = rect.x() + 14
        y = rect.y() + 10
        width = rect.width() - 24

        badge_text = self._kind_badge_text(card.entity_kind)
        badge_width = max(48, len(badge_text) * 7 + 18)
        badge_rect = rect.adjusted(rect.width() - badge_width - 12, 10, -12, -(rect.height() - 28))
        painter.setBrush(accent_fill)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(badge_rect, 9, 9)
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
        meta_text = meta_metrics.elidedText(card.meta_text or card.stage, Qt.TextElideMode.ElideRight, width)
        painter.drawText(x, y + 34, meta_text)

        painter.setFont(self._subtitle_font)
        painter.setPen(QColor("#c5cfdd"))
        subtitle_metrics = QFontMetrics(self._subtitle_font)
        subtitle = subtitle_metrics.elidedText(card.subtitle or "Без описания", Qt.TextElideMode.ElideRight, width)
        painter.drawText(x, y + 56, subtitle)

        footer = []
        if card.project_title:
            footer.append(card.project_title)
        if card.total_linked_count:
            footer.append(f"Links: {card.total_linked_count}")
        if not card.can_drag:
            footer.append("Read-only")
        footer_text = " · ".join(footer) if footer else "Mixed entity card"
        painter.setFont(self._meta_font)
        painter.setPen(QColor("#73839a"))
        footer_text = meta_metrics.elidedText(footer_text, Qt.TextElideMode.ElideRight, width)
        painter.drawText(x, y + 76, footer_text)

        painter.restore()

    @staticmethod
    def _kind_badge_text(entity_kind: str) -> str:
        return {
            "task": "TASK",
            "idea": "IDEA",
            "object": "OBJECT",
        }.get(entity_kind, entity_kind.upper())


__all__ = ["MutaBoardDelegate"]
