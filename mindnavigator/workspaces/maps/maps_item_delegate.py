"""MapsItemDelegate class module for maps workspace."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403
class MapsItemDelegate(QStyledItemDelegate):
    ROW_H = 112
    ROW_H_MIN = 124

    C_BG = QColor("#16171a")
    C_ROW = QColor("#2a2d33")
    C_ROW_ALT = QColor("#2c2f36")
    C_BORDER = QColor("#3a3b40")
    C_TEXT = QColor("#e1e1e1")
    C_DIM = QColor("#9a9a9a")
    C_PILL = QColor("#1f2126")
    C_PILL_BORDER = QColor("#2d2f35")
    C_BTN = QColor("#23262c")
    C_BTN_BORDER = QColor("#343740")
    C_BTN_TEXT = QColor("#e0e0e0")

    def __init__(self, parent=None):
        # Инициализация делегата для отрисовки строк.
        super().__init__(parent)
        # Настраиваем шрифты для отдельных блоков строки.
        self._font_title = QFont()
        self._font_title.setPointSize(10)
        self._font_title.setBold(True)

        self._font_desc = QFont()
        self._font_desc.setPointSize(9)

        self._font_pill = QFont()
        self._font_pill.setPointSize(9)

        self._font_button = QFont()
        self._font_button.setPointSize(9)
        self._font_button.setBold(True)

        # Загружаем иконку карты.
        self._icon_map = qta.icon("fa5s.map-marked-alt", color="#cfcfcf")

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex):
        # Высота строки зависит от длины описания.
        desc = index.data(MapRoles.Description) or ""
        layout = self._row_layout(option.rect)
        text_width = max(10, layout["text"].width())

        title_metrics = QFontMetrics(self._font_title)
        desc_metrics = QFontMetrics(self._font_desc)
        title_height = title_metrics.boundingRect(0, 0, text_width, 1000, Qt.TextFlag.TextWordWrap, "X").height()
        desc_height = 0
        if desc:
            desc_height = desc_metrics.boundingRect(0, 0, text_width, 1000, Qt.TextFlag.TextWordWrap, desc).height()

        total_height = title_height + desc_height + 96
        return QSize(option.rect.width(), max(self.ROW_H_MIN, total_height))

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        # Основная отрисовка карточки карты.
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        r = option.rect
        row_color = self.C_ROW_ALT if index.row() % 2 else self.C_ROW
        if option.state & QStyle.StateFlag.State_Selected:
            row_color = QColor("#34373e")

        painter.fillRect(r, self.C_BG)
        painter.fillRect(r.adjusted(6, 4, -6, -4), row_color)
        painter.setPen(self.C_BORDER)
        painter.drawRoundedRect(r.adjusted(6, 4, -6, -4), 6, 6)

        # Вычисляем layout и извлекаем данные.
        layout = self._row_layout(r)
        title = index.data(MapRoles.Title) or ""
        desc = index.data(MapRoles.Description) or ""
        project = index.data(MapRoles.Project) or ""
        tiles_h = index.data(MapRoles.TilesHeight) or 0
        tiles_w = index.data(MapRoles.TilesWidth) or 0

        icon_rect = layout["icon"]
        self._icon_map.paint(painter, icon_rect, Qt.AlignmentFlag.AlignCenter)

        # Рисуем заголовок и описание.
        painter.setPen(self.C_TEXT)
        painter.setFont(self._font_title)
        painter.drawText(layout["title"], Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, title)

        if desc:
            painter.setPen(self.C_DIM)
            painter.setFont(self._font_desc)
            painter.drawText(layout["desc"], Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, desc)

        # Дополнительные блоки и кнопки.
        self._draw_pill(painter, layout["project"], project)
        self._draw_pill(painter, layout["tiles"], f"Тайлы: {tiles_w}×{tiles_h}")
        self._draw_button(painter, layout["edit_btn"], "Редактировать свойства")
        self._draw_button(painter, layout["open_btn"], "Перейти к карте")

        painter.restore()

    @staticmethod
    def _row_layout(r: QRect) -> dict:
        # Рассчитываем положение и размеры всех блоков строки.
        left = r.left() + 14
        right = r.right() - 14
        top = r.top() + 10
        bottom = r.bottom() - 10
        icon_rect = QRect(left, top + 6, 18, 18)
        info_w = 210
        text_rect = QRect(left + 28, top, right - info_w - (left + 28), bottom - top)
        title_rect = QRect(text_rect.left(), text_rect.top(), text_rect.width(), 22)
        desc_rect = QRect(text_rect.left(), text_rect.top() + 24, text_rect.width(), text_rect.height() - 24)

        pill_x = right - info_w + 6
        pill_w = info_w - 12
        project_rect = QRect(pill_x, top, pill_w, 22)
        tiles_rect = QRect(pill_x, top + 28, pill_w, 22)
        edit_rect = QRect(pill_x, top + 56, pill_w, 22)
        open_rect = QRect(pill_x, top + 82, pill_w, 22)

        return {
            "icon": icon_rect,
            "text": text_rect,
            "title": title_rect,
            "desc": desc_rect,
            "project": project_rect,
            "tiles": tiles_rect,
            "edit_btn": edit_rect,
            "open_btn": open_rect,
        }

    def row_layout(self, rect: QRect) -> dict:
        return self._row_layout(rect)

    def _draw_pill(self, painter: QPainter, rect: QRect, text: str) -> None:
        # Рисуем "плашку" с текстом.
        painter.save()
        painter.setPen(self.C_PILL_BORDER)
        painter.setBrush(self.C_PILL)
        painter.drawRoundedRect(rect, 6, 6)
        painter.setPen(self.C_TEXT)
        painter.setFont(self._font_pill)
        painter.drawText(rect.adjusted(8, 0, -8, 0), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)
        painter.restore()

    def _draw_button(self, painter: QPainter, rect: QRect, text: str) -> None:
        # Рисуем псевдо-кнопку внутри делегата.
        painter.save()
        painter.setPen(self.C_BTN_BORDER)
        painter.setBrush(self.C_BTN)
        painter.drawRoundedRect(rect, 6, 6)
        painter.setPen(self.C_BTN_TEXT)
        painter.setFont(self._font_button)
        painter.drawText(rect.adjusted(8, 0, -8, 0), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)
        painter.restore()

__all__ = ["MapsItemDelegate"]
