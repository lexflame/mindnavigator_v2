"""Qt helpers for context entity linking in text editors."""

from __future__ import annotations

from typing import Callable, Optional, Sequence, cast

from PySide6.QtCore import QEvent, QObject, QPoint, QRect, QTimer, Qt
from PySide6.QtGui import QColor, QContextMenuEvent, QPainter, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QLineEdit, QMenu, QMessageBox, QPlainTextEdit, QTextEdit, QWidget
from shiboken6 import isValid

from mindnavigator.context_entity_linking import (
    CONTEXT_LINK_ENTITY_TYPES,
    ContextEntityLinkService,
    ContextEntitySearchResult,
    ContextEntitySearchService,
    PendingContextLink,
    extract_capitalized_words,
    normalize_context_word,
)

_UNDERLINE_COLOR = QColor("#20F5D2")
_UNDERLINE_HOVER_COLOR = QColor("#57FFE6")


def _text_from_widget(widget: QLineEdit | QPlainTextEdit | QTextEdit) -> str:
    if isinstance(widget, QLineEdit):
        return widget.text()
    return widget.toPlainText()


def _word_at_position(text: str, position: int, field: str = ""):
    for word in extract_capitalized_words(text, field=field):
        if word.start <= position < word.end:
            return word
    return None


def _short_result_label(result: ContextEntitySearchResult) -> str:
    prefix = CONTEXT_LINK_ENTITY_TYPES.get(result.entity_type, result.entity_type)
    title = (result.title or "").strip()
    if len(title) > 64:
        title = f"{title[:63]}…"
    return f"{prefix}: {title}"


class _LineEditContextOverlay(QWidget):
    def __init__(self, line_edit: QLineEdit) -> None:
        super().__init__(line_edit)
        self._line_edit = line_edit
        self._ranges: list[tuple[int, int]] = []
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setStyleSheet("background: transparent;")
        self.hide()

    def set_ranges(self, ranges: Sequence[tuple[int, int]]) -> None:
        self._ranges = list(ranges)
        self.setVisible(bool(self._ranges))
        self.update()

    def sync_geometry(self) -> None:
        self.setGeometry(self._line_edit.rect())
        self.raise_()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt API
        super().paintEvent(event)
        if not self._ranges:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = painter.pen()
        pen.setColor(_UNDERLINE_COLOR)
        pen.setWidth(2)
        painter.setPen(pen)
        text = self._line_edit.text()
        font_metrics = self._line_edit.fontMetrics()
        cursor_rect = self._line_edit.cursorRect()
        cursor_pos = self._line_edit.cursorPosition()
        cursor_prefix_width = font_metrics.horizontalAdvance(text[:cursor_pos])
        baseline = min(self.height() - 3, cursor_rect.bottom() + 1)
        clip_rect = self.rect().adjusted(2, 0, -2, 0)
        for start, end in self._ranges:
            start_width = font_metrics.horizontalAdvance(text[:start])
            end_width = font_metrics.horizontalAdvance(text[:end])
            start_x = cursor_rect.x() - (cursor_prefix_width - start_width)
            end_x = cursor_rect.x() - (cursor_prefix_width - end_width)
            rect = QRect(start_x, baseline, max(1, end_x - start_x), 3).intersected(clip_rect)
            if rect.width() > 1:
                painter.drawLine(rect.left(), rect.top(), rect.right(), rect.top())


class ContextEntityLinkingController(QObject):
    def __init__(
        self,
        widget: QLineEdit | QPlainTextEdit | QTextEdit,
        db,
        *,
        source_type: str,
        source_id_getter: Callable[[], Optional[int]],
        source_field: str,
        pending_sink: Optional[Callable[[PendingContextLink], None]] = None,
        notify: Optional[Callable[[str], None]] = None,
        refresh_callback: Optional[Callable[[], None]] = None,
        debounce_ms: int = 250,
    ) -> None:
        super().__init__(widget)
        self.widget: QLineEdit | QPlainTextEdit | QTextEdit | None = widget
        self._source_type = source_type
        self._source_id_getter = source_id_getter
        self._source_field = source_field
        self._pending_sink = pending_sink
        self._notify = notify
        self._refresh_callback = refresh_callback
        self._search_service = ContextEntitySearchService(db)
        self._link_service = ContextEntityLinkService(db)
        self._cache: dict[str, list[ContextEntitySearchResult]] = {}
        self._ranges_by_word: dict[str, list[tuple[int, int]]] = {}
        self._line_overlay = _LineEditContextOverlay(widget) if isinstance(widget, QLineEdit) else None
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(max(0, debounce_ms))
        self._timer.timeout.connect(self.refresh_now)
        widget.setProperty("mn_spellcheck_disabled", True)
        widget.textChanged.connect(self.schedule_refresh)
        widget.installEventFilter(self)
        widget.destroyed.connect(self._on_widget_destroyed)
        if self._line_overlay is not None:
            self._line_overlay.sync_geometry()
        self.schedule_refresh()

    def _on_widget_destroyed(self, *_args) -> None:
        self._timer.stop()
        self._cache.clear()
        self.widget = None

    def _alive(self) -> bool:
        return self.widget is not None and isValid(self.widget)

    def eventFilter(self, obj, event) -> bool:
        if obj is self.widget and isinstance(obj, QLineEdit) and event.type() in {
            QEvent.Type.Resize,
            QEvent.Type.Move,
            QEvent.Type.Show,
            QEvent.Type.FontChange,
            QEvent.Type.StyleChange,
        }:
            if self._line_overlay is not None and isValid(self._line_overlay):
                self._line_overlay.sync_geometry()
                self._line_overlay.update()
        if obj is self.widget and event.type() == QEvent.Type.ContextMenu and isinstance(
            obj, (QLineEdit, QPlainTextEdit, QTextEdit)
        ):
            return self._show_context_menu(obj, cast(QContextMenuEvent, event))
        return super().eventFilter(obj, event)

    def schedule_refresh(self, *_args) -> None:
        if self._alive():
            self._timer.start()

    def refresh_now(self) -> None:
        if not self._alive():
            return
        widget = cast(QLineEdit | QPlainTextEdit | QTextEdit, self.widget)
        text = _text_from_widget(widget)
        words = extract_capitalized_words(text, field=self._source_field)
        self._ranges_by_word.clear()
        for word in words:
            results = self._results_for_word(word.raw)
            if not results:
                continue
            self._ranges_by_word.setdefault(word.normalized, []).append((word.start, word.end))
        self._apply_highlight()

    def _results_for_word(self, word: str) -> list[ContextEntitySearchResult]:
        normalized = normalize_context_word(word)
        if normalized not in self._cache:
            self._cache[normalized] = self._search_service.search_context_entities(
                word,
                source_entity_type=self._source_type,
                source_entity_id=self._source_id_getter(),
                limit=8,
            )
        return self._cache[normalized]

    def _apply_highlight(self) -> None:
        widget = self.widget
        if widget is None or not isValid(widget):
            return
        ranges = [item for bucket in self._ranges_by_word.values() for item in bucket]
        if isinstance(widget, QLineEdit):
            if self._line_overlay is not None and isValid(self._line_overlay):
                self._line_overlay.set_ranges(ranges)
            return
        text_widget = cast(QPlainTextEdit | QTextEdit, widget)
        selections = []
        for start, end in ranges:
            cursor = text_widget.textCursor()
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
            selection = QTextEdit.ExtraSelection()
            selection.cursor = cursor
            selection.format.setUnderlineColor(_UNDERLINE_COLOR)
            selection.format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SingleUnderline)
            selections.append(selection)
        text_widget.setExtraSelections(selections)

    def _position_from_event(self, widget: QLineEdit | QPlainTextEdit | QTextEdit, point: QPoint) -> Optional[int]:
        if isinstance(widget, QLineEdit):
            return widget.cursorPositionAt(point)
        return widget.cursorForPosition(point).position()

    def _show_context_menu(self, widget: QLineEdit | QPlainTextEdit | QTextEdit, event: QContextMenuEvent) -> bool:
        position = self._position_from_event(widget, event.pos())
        if position is None:
            return False
        word = _word_at_position(_text_from_widget(widget), position, self._source_field)
        if isinstance(widget, QLineEdit):
            widget.setCursorPosition(position)
        else:
            widget.setTextCursor(widget.cursorForPosition(event.pos()))
        menu = widget.createStandardContextMenu()
        if not isinstance(menu, QMenu):
            return False
        try:
            if word is not None:
                results = self._results_for_word(word.raw)
                if results:
                    first_standard_action = menu.actions()[0] if menu.actions() else None
                    link_menu = QMenu("Связать", menu)
                    for result in results:
                        action = link_menu.addAction(_short_result_label(result))
                        action.setToolTip(f"{result.subtitle} · {result.matched_field} · {result.score:.2f}")
                        action.triggered.connect(
                            lambda _checked=False, current_word=word.raw, current_result=result: self._link_to_result(
                                current_word,
                                current_result,
                            )
                        )
                    menu.insertMenu(first_standard_action, link_menu)
                    menu.insertSeparator(first_standard_action)
            menu.exec(event.globalPos())
        finally:
            menu.deleteLater()
        return True

    def _link_to_result(self, anchor_text: str, result: ContextEntitySearchResult) -> None:
        source_id = self._source_id_getter()
        if source_id is None or int(source_id) <= 0:
            if self._pending_sink is None:
                self._show_message("Сначала сохраните текущую сущность.")
                return
            self._pending_sink(
                PendingContextLink(
                    target_type=result.entity_type,
                    target_id=result.entity_id,
                    anchor_text=anchor_text,
                    source_field=self._source_field,
                )
            )
            self._show_message(f"Связь будет создана после сохранения: {_short_result_label(result)}.")
            return
        link_result = self._link_service.create_context_link(
            self._source_type,
            int(source_id),
            result.entity_type,
            result.entity_id,
            anchor_text,
            self._source_field,
        )
        if link_result.duplicate:
            self._show_message("Связь уже существует.")
            return
        if not link_result.success:
            self._show_message(link_result.message or "Не удалось создать связь.")
            return
        self._show_message(f"Связь создана с {result.subtitle.lower()} «{result.title}».")
        if self._refresh_callback is not None:
            self._refresh_callback()

    def _show_message(self, text: str) -> None:
        if self._notify is not None:
            self._notify(text)
            return
        parent = cast(QWidget, self.widget).window() if self.widget is not None and isValid(self.widget) else None
        QMessageBox.information(parent, "Связи", text)


def attach_context_entity_linking(
    widget: QLineEdit | QPlainTextEdit | QTextEdit,
    db,
    *,
    source_type: str,
    source_id_getter: Callable[[], Optional[int]],
    source_field: str,
    pending_sink: Optional[Callable[[PendingContextLink], None]] = None,
    notify: Optional[Callable[[str], None]] = None,
    refresh_callback: Optional[Callable[[], None]] = None,
) -> ContextEntityLinkingController:
    controller = ContextEntityLinkingController(
        widget,
        db,
        source_type=source_type,
        source_id_getter=source_id_getter,
        source_field=source_field,
        pending_sink=pending_sink,
        notify=notify,
        refresh_callback=refresh_callback,
    )
    controllers = getattr(widget, "_mn_context_entity_linking_controllers", [])
    controllers.append(controller)
    setattr(widget, "_mn_context_entity_linking_controllers", controllers)
    return controller


__all__ = ["ContextEntityLinkingController", "attach_context_entity_linking"]
