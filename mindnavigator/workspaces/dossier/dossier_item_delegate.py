"""Item delegate for Dossier list rows."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403
from .dossier_roles import DossierRoles


class DossierItemDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        painter.save()

        rect = option.rect.adjusted(10, 4, -10, -4)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        background = QColor("#2b313c" if selected else "#1c1d22")
        border = QColor("#4d698c" if selected else "#2d2f35")
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(background)
        painter.setPen(border)
        painter.drawRoundedRect(rect, 10, 10)

        kind = str(index.data(DossierRoles.Kind) or "")
        title = str(index.data(DossierRoles.Title) or "Без названия")
        summary = str(index.data(DossierRoles.Summary) or "")
        description = str(index.data(DossierRoles.Description) or "")
        status = str(index.data(DossierRoles.Status) or "")
        source = str(index.data(DossierRoles.Source) or "")
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
            cover_image="",
            metadata=dict(metadata_value) if isinstance(metadata_value, dict) else {},
            created_at="",
            updated_at=str(index.data(DossierRoles.UpdatedAt) or ""),
        )

        title_font = QFont(option.font)
        title_font.setPointSize(title_font.pointSize() + 1)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.setPen(QColor("#f3f5f8"))
        title_metrics = QFontMetrics(title_font)

        badge_rect = QRect(rect.right() - 108, rect.top() + 10, 96, 24)
        badge_color = QColor(DOSSIER_KIND_COLORS.get(kind, "#6b7280"))
        painter.setBrush(badge_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(badge_rect, 12, 12)
        painter.setPen(QColor("#ffffff"))
        painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, dossier_kind_label(kind))

        title_rect = QRect(rect.left() + 12, rect.top() + 10, rect.width() - 132, 22)
        painter.drawText(
            title_rect,
            Qt.TextFlag.TextSingleLine | Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            elided_text(title_metrics, title, title_rect.width()),
        )

        meta_font = QFont(option.font)
        meta_font.setPointSize(max(8, meta_font.pointSize() - 1))
        painter.setFont(meta_font)
        meta_metrics = QFontMetrics(meta_font)
        painter.setPen(QColor("#bdc4ce"))
        meta_rect = QRect(rect.left() + 12, rect.top() + 36, rect.width() - 24, 18)
        painter.drawText(
            meta_rect,
            Qt.TextFlag.TextSingleLine | Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            elided_text(meta_metrics, dossier_secondary_line(dossier), meta_rect.width()),
        )

        preview_text = summary.strip() or description.strip() or dossier_metadata_preview(dossier)
        painter.setPen(QColor("#e0e4ea" if selected else "#c3c8d0"))
        preview_rect = QRect(rect.left() + 12, rect.top() + 58, rect.width() - 24, 20)
        painter.drawText(
            preview_rect,
            Qt.TextFlag.TextSingleLine | Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            elided_text(meta_metrics, preview_text, preview_rect.width()),
        )

        painter.setPen(QColor("#89a9da"))
        footer_rect = QRect(rect.left() + 12, rect.top() + 80, rect.width() - 24, 16)
        footer = dossier_metadata_preview(dossier) if dossier.metadata else f"Теги: {dossier_tags_text(dossier.tags)}"
        painter.drawText(
            footer_rect,
            Qt.TextFlag.TextSingleLine | Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            elided_text(meta_metrics, footer, footer_rect.width()),
        )

        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        return QSize(option.rect.width(), 108)


__all__ = ["DossierItemDelegate"]
