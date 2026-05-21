"""Item delegate for Dossier list rows."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403
from .dossier_roles import DossierRoles


class DossierItemDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        if index.data(DossierRoles.RowType) == "group":
            self._paint_group_row(painter, option, index)
            return

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = option.rect.adjusted(10, 5, -10, -5)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)
        background = QColor("#26303d" if selected else "#1c1d22")
        border = QColor("#5f85b5" if selected else "#343943")
        if hovered and not selected:
            background = QColor("#20242c")
            border = QColor("#3d4653")

        painter.setBrush(background)
        painter.setPen(border)
        painter.drawRoundedRect(rect, 12, 12)

        kind = str(index.data(DossierRoles.Kind) or "")
        title = str(index.data(DossierRoles.Title) or "Без названия")
        summary = str(index.data(DossierRoles.Summary) or "")
        description = str(index.data(DossierRoles.Description) or "")
        status = str(index.data(DossierRoles.Status) or "")
        source = str(index.data(DossierRoles.Source) or "")
        cover_image = str(index.data(DossierRoles.CoverImage) or "")
        output_summary = str(index.data(DossierRoles.OutputSummary) or "нет")
        link_count = int(index.data(DossierRoles.LinkCount) or 0)
        tags_value = index.data(DossierRoles.Tags)
        metadata_value = index.data(DossierRoles.Metadata)
        rating = index.data(DossierRoles.Rating)

        dossier = DossierData(
            id=int(index.data(DossierRoles.DossierId) or 0),
            kind=kind,
            title=title,
            summary=summary,
            description=description,
            tags=list(tags_value) if isinstance(tags_value, list) else [],
            status=status,
            rating=int(rating) if isinstance(rating, int) else None,
            source=source,
            cover_image=cover_image,
            metadata=dict(metadata_value) if isinstance(metadata_value, dict) else {},
            created_at="",
            updated_at=str(index.data(DossierRoles.UpdatedAt) or ""),
        )

        cover_rect = QRect(rect.left() + 12, rect.top() + 12, 56, 80)
        self._paint_cover(painter, cover_rect, dossier)

        content_left = cover_rect.right() + 12
        content_width = rect.right() - content_left - 12

        badge_rect = QRect(rect.right() - 102, rect.top() + 12, 90, 24)
        badge_color = QColor(DOSSIER_KIND_COLORS.get(kind, "#6b7280"))
        painter.setBrush(badge_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(badge_rect, 12, 12)
        painter.setPen(QColor("#ffffff"))
        painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, dossier_kind_label(kind))

        title_font = QFont(option.font)
        title_font.setPointSize(title_font.pointSize() + 1)
        title_font.setBold(True)
        painter.setFont(title_font)
        title_metrics = QFontMetrics(title_font)
        painter.setPen(QColor("#f5f7fa"))
        title_rect = QRect(content_left, rect.top() + 12, content_width - 100, 24)
        painter.drawText(
            title_rect,
            Qt.TextFlag.TextSingleLine | Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            elided_text(title_metrics, title, title_rect.width()),
        )

        meta_font = QFont(option.font)
        meta_font.setPointSize(max(8, meta_font.pointSize() - 1))
        painter.setFont(meta_font)
        meta_metrics = QFontMetrics(meta_font)
        painter.setPen(QColor("#bbc4d0"))
        meta_rect = QRect(content_left, rect.top() + 39, content_width, 18)
        painter.drawText(
            meta_rect,
            Qt.TextFlag.TextSingleLine | Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            elided_text(meta_metrics, dossier_secondary_line(dossier), meta_rect.width()),
        )

        preview_rect = QRect(content_left, rect.top() + 60, content_width, 18)
        preview_text = dossier_preview_text(dossier)
        painter.setPen(QColor("#e2e6ec" if selected else "#c8ced7"))
        painter.drawText(
            preview_rect,
            Qt.TextFlag.TextSingleLine | Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            elided_text(meta_metrics, preview_text, preview_rect.width()),
        )

        footer_left = f"{dossier_links_count_text(link_count)}  |  Теги: {dossier_card_tags(dossier.tags)}"
        footer_right = f"Выход: {output_summary}"

        painter.setPen(QColor("#87a8d9"))
        footer_rect = QRect(content_left, rect.top() + 84, content_width, 16)
        painter.drawText(
            footer_rect,
            Qt.TextFlag.TextSingleLine | Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            elided_text(meta_metrics, footer_left, footer_rect.width()),
        )

        painter.setPen(QColor("#8dd3aa"))
        output_rect = QRect(content_left, rect.top() + 102, content_width, 16)
        painter.drawText(
            output_rect,
            Qt.TextFlag.TextSingleLine | Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            elided_text(meta_metrics, footer_right, output_rect.width()),
        )

        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        if index.data(DossierRoles.RowType) == "group":
            return QSize(option.rect.width(), 32)
        return QSize(option.rect.width(), 132)

    @staticmethod
    def _paint_group_row(painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        painter.save()
        rect = option.rect.adjusted(12, 6, -12, -2)
        label = str(index.data(DossierRoles.GroupLabel) or "Группа")
        count = int(index.data(DossierRoles.GroupCount) or 0)

        title_font = QFont(option.font)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.setPen(QColor("#8f98a8"))
        painter.drawText(
            rect,
            Qt.TextFlag.TextSingleLine | Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            f"{label} ({count})",
        )
        painter.restore()

    @staticmethod
    def _paint_cover(painter: QPainter, rect: QRect, dossier: DossierData) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        path = dossier_cover_path(dossier.cover_image)
        pixmap = load_dossier_cover_pixmap(path) if path else None
        if pixmap is not None:
            scaled = pixmap.scaled(
                rect.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            painter.setClipRect(rect)
            painter.drawPixmap(rect, scaled)
            painter.setClipping(False)
            painter.setPen(QColor("#39414e"))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect, 8, 8)
            painter.restore()
            return

        placeholder_color = QColor(DOSSIER_KIND_COLORS.get(dossier.kind, "#6b7280"))
        painter.setBrush(placeholder_color.darker(145))
        painter.setPen(QColor("#3b4048"))
        painter.drawRoundedRect(rect, 8, 8)

        painter.setPen(QColor("#ffffff"))
        font = QFont()
        font.setBold(True)
        font.setPointSize(max(9, font.pointSize()))
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, dossier_kind_label(dossier.kind)[:1])
        painter.restore()


__all__ = ["DossierItemDelegate"]
