"""ObjectCardDelegate class module for objects workspace."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403

class ObjectCardDelegate(QStyledItemDelegate):
    ROW_H = 72

    C_BG = QColor("#171a20")
    C_BORDER = QColor("#2f333b")
    C_TEXT = QColor("#e6e6e6")
    C_MUTED = QColor("#9aa0a6")

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._font_title = QFont()
        self._font_title.setPointSize(10)
        self._font_title.setBold(True)

        self._font_meta = QFont()
        self._font_meta.setPointSize(9)

        self._font_preview = QFont()
        self._font_preview.setPointSize(9)

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex):
        if index.data(ObjectRoles.RowType) == "category":
            return QSize(option.rect.width(), 30)
        return QSize(option.rect.width(), self.ROW_H)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        painter.save()
        row_type = index.data(ObjectRoles.RowType)
        if row_type == "category":
            rect = option.rect.adjusted(10, 3, -10, -3)
            title = (index.data(ObjectRoles.Title) or "").strip() or "Без каталога"
            font = QFont(option.font)
            font.setPointSize(max(8, font.pointSize() - 1))
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(QColor("#8d939b"))
            painter.drawText(rect.adjusted(4, 0, -4, 0), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, title)
            painter.setPen(QColor("#30333a"))
            painter.drawLine(rect.left(), rect.bottom(), rect.right(), rect.bottom())
            painter.restore()
            return

        rect = option.rect.adjusted(8, 3, -8, -3)
        radius = 8

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        bg = QColor(self.C_BG)
        if option.state & QStyle.StateFlag.State_Selected:
            bg = QColor("#232833")
        painter.setBrush(bg)
        painter.setPen(self.C_BORDER)
        painter.drawRoundedRect(rect, radius, radius)

        title = index.data(ObjectRoles.Title) or ""
        catalog = index.data(ObjectRoles.Catalog) or ""
        object_type = index.data(ObjectRoles.ObjectType) or ""
        status = index.data(ObjectRoles.Status) or ""
        description = index.data(ObjectRoles.Description) or ""
        preview_text = object_preview_line(description)

        x = rect.x() + 14
        y = rect.y() + 8
        w = rect.width() - 28

        painter.setPen(self.C_TEXT)
        painter.setFont(self._font_title)
        title_metrics = QFontMetrics(self._font_title)
        title_text = title_metrics.elidedText(title, Qt.TextElideMode.ElideRight, w)
        painter.drawText(QRect(x, y, w, 20), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, title_text)

        meta_y = y + 20
        painter.setFont(self._font_meta)
        painter.setPen(self.C_MUTED)
        meta_parts = [part for part in [catalog, object_type, status] if part]
        meta_text = " | ".join(meta_parts) if meta_parts else "Без каталога"
        meta_metrics = QFontMetrics(self._font_meta)
        meta_text = meta_metrics.elidedText(meta_text, Qt.TextElideMode.ElideRight, w)
        painter.drawText(QRect(x, meta_y, w, 18), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, meta_text)

        preview_y = meta_y + 18
        painter.setFont(self._font_preview)
        painter.setPen(QColor("#b8bec6"))
        preview_metrics = QFontMetrics(self._font_preview)
        preview_text = preview_metrics.elidedText(preview_text, Qt.TextElideMode.ElideRight, w)
        painter.drawText(
            QRect(x, preview_y, w, 18),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            preview_text,
        )

        painter.restore()

__all__ = ["ObjectCardDelegate"]
