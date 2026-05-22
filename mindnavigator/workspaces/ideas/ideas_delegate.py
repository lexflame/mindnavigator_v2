"""IdeasDelegate class module for ideas workspace."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403


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
        project = index.data(IdeaRoles.ProjectPath) or index.data(IdeaRoles.ProjectTitle) or "Без проекта"
        status = STATUS_LABELS.get(index.data(IdeaRoles.Status), "")
        idea_type = TYPE_LABELS.get(index.data(IdeaRoles.Type), "")
        value_score = index.data(IdeaRoles.ValueScore)
        effort_score = index.data(IdeaRoles.EffortScore)
        summary = index.data(IdeaRoles.Summary) or ""
        body_md = index.data(IdeaRoles.Body) or ""
        source_text = index.data(IdeaRoles.Source) or ""
        output_label = index.data(IdeaRoles.OutputLabel) or "нет"
        relations_count = int(index.data(IdeaRoles.RelationsCount) or 0)
        materials_count = int(index.data(IdeaRoles.MaterialsCount) or 0)
        updated_label = index.data(IdeaRoles.UpdatedLabel) or ""
        preview_text = idea_preview_line(summary, body_md)
        source_preview = self._compact_source(source_text)

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
            rect.adjusted(12, 46, -12, -30),
            Qt.TextFlag.TextSingleLine | Qt.AlignmentFlag.AlignLeft,
            preview_text,
        )

        painter.setPen(QColor("#d6c08d"))
        painter.drawText(
            rect.adjusted(12, 66, -12, -30),
            Qt.TextFlag.TextSingleLine | Qt.AlignmentFlag.AlignLeft,
            f"Источник: {source_preview}",
        )

        score_text = f"Value {value_score} | Effort {effort_score} | Выход: {output_label}"
        painter.setPen(QColor("#8bb5e8"))
        painter.drawText(
            rect.adjusted(12, 86, -12, -12),
            Qt.TextFlag.TextSingleLine | Qt.AlignmentFlag.AlignLeft,
            score_text,
        )

        footer_text = " | ".join(
            part
            for part in [
                f"Связи: {relations_count}",
                f"Материалы: {materials_count}",
                updated_label,
            ]
            if part
        )
        painter.setPen(QColor("#8d939b"))
        painter.drawText(
            rect.adjusted(12, 104, -12, -2),
            Qt.TextFlag.TextSingleLine | Qt.AlignmentFlag.AlignLeft,
            footer_text,
        )

        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        if index.data(IdeaRoles.RowType) == "category":
            return QSize(option.rect.width(), 30)
        return QSize(option.rect.width(), 128)

    @staticmethod
    def _compact_source(source_text: str) -> str:
        parts = [
            " ".join(raw_line.strip().split())
            for raw_line in str(source_text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
            if raw_line.strip()
        ]
        return " • ".join(parts) if parts else "нет"

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


__all__ = ["IdeasDelegate"]
