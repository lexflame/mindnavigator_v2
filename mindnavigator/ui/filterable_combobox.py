from __future__ import annotations

from PySide6.QtCore import QEvent, QModelIndex, QObject, QPoint, QRegularExpression, Qt, QSortFilterProxyModel
from PySide6.QtWidgets import QAbstractItemView, QComboBox, QCompleter, QLineEdit


class _CompleterPopupSync(QObject):
    def __init__(self, line_edit: QLineEdit, completer: QCompleter, max_visible_items: int = 8) -> None:
        super().__init__(line_edit)
        self._line_edit = line_edit
        self._completer = completer
        self._popup = completer.popup()
        self._max_visible_items = max_visible_items
        self._configure_popup()
        self._line_edit.installEventFilter(self)
        if self._popup is not None:
            self._popup.installEventFilter(self)

    def eventFilter(self, watched, event) -> bool:  # noqa: N802 - Qt API
        if watched in (self._line_edit, self._popup) and event.type() in {
            QEvent.Type.Resize,
            QEvent.Type.Move,
            QEvent.Type.Show,
            QEvent.Type.FontChange,
            QEvent.Type.StyleChange,
            QEvent.Type.ScreenChangeInternal,
        }:
            self._sync_popup()
        return super().eventFilter(watched, event)

    def _configure_popup(self) -> None:
        if self._popup is None:
            return
        self._popup.setObjectName("FilterableComboPopup")
        self._popup.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self._popup.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._popup.setTextElideMode(Qt.TextElideMode.ElideRight)
        self._popup.setStyleSheet(
            """
            QAbstractItemView#FilterableComboPopup {
                background: #1f2026;
                color: #e6e6e6;
                border: 1px solid #2d3036;
                border-radius: 8px;
                padding: 4px;
                outline: none;
            }
            QAbstractItemView#FilterableComboPopup::item {
                padding: 6px 10px;
                border-radius: 6px;
            }
            QAbstractItemView#FilterableComboPopup::item:hover {
                background: #2b2f36;
            }
            QAbstractItemView#FilterableComboPopup::item:selected {
                background: #3a4356;
                color: #f2f4ff;
            }
            """
        )
        self._completer.setMaxVisibleItems(self._max_visible_items)
        self._sync_popup()

    def _sync_popup(self) -> None:
        if self._popup is None:
            return
        width = self._line_edit.width()
        if width > 0:
            self._popup.setFixedWidth(width)
        if self._popup.isVisible():
            self._popup.move(self._line_edit.mapToGlobal(QPoint(0, self._line_edit.height())))
        row_height = self._popup.sizeHintForRow(0)
        if row_height > 0:
            padding = self._popup.frameWidth() * 2 + 4
            self._popup.setMaximumHeight(row_height * self._max_visible_items + padding)


class FilterableComboBox(QComboBox):
    def __init__(self, parent=None, *, max_visible_items: int = 8) -> None:
        super().__init__(parent)
        self._has_explicit_selection = True
        self._filter_model = QSortFilterProxyModel(self)
        self._filter_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._filter_model.setFilterRole(Qt.ItemDataRole.DisplayRole)
        self._filter_model.setFilterKeyColumn(self.modelColumn())

        self.setEditable(True)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._completer = QCompleter(self._filter_model, self)
        self._completer.setCompletionMode(QCompleter.CompletionMode.UnfilteredPopupCompletion)
        self._completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.setCompleter(self._completer)

        line_edit = self.lineEdit()
        if line_edit is not None:
            line_edit.setClearButtonEnabled(True)
            line_edit.textEdited.connect(self._on_text_edited)
            self._popup_sync = _CompleterPopupSync(line_edit, self._completer, max_visible_items=max_visible_items)
        else:
            self._popup_sync = None

        self._completer.activated[QModelIndex].connect(self._on_completer_activated)
        self.activated.connect(self._on_combo_activated)
        self.currentIndexChanged.connect(self._on_current_index_changed)
        self._attach_source_model()

    def setModel(self, model) -> None:  # noqa: N802 - Qt API
        super().setModel(model)
        self._attach_source_model()

    def setModelColumn(self, visible_column: int) -> None:  # noqa: N802 - Qt API
        super().setModelColumn(visible_column)
        self._filter_model.setFilterKeyColumn(visible_column)
        self._completer.setCompletionColumn(visible_column)

    def showPopup(self) -> None:  # noqa: N802 - Qt API
        self._apply_filter(self.lineEdit().text() if self.lineEdit() is not None else "")
        self._completer.complete()

    def hidePopup(self) -> None:  # noqa: N802 - Qt API
        popup = self._completer.popup()
        if popup is not None:
            popup.hide()
        super().hidePopup()

    def currentData(self, role: int = int(Qt.ItemDataRole.UserRole)):  # noqa: N802 - Qt API
        if not self._has_explicit_selection:
            return None
        return super().currentData(role)

    def clear_filter(self) -> None:
        self._apply_filter("")

    def _attach_source_model(self) -> None:
        self._filter_model.setSourceModel(self.model())
        self._filter_model.setFilterKeyColumn(self.modelColumn())
        self._completer.setModel(self._filter_model)
        self._completer.setCompletionColumn(self.modelColumn())

    def _apply_filter(self, text: str) -> None:
        if text:
            regex = QRegularExpression(
                f".*{QRegularExpression.escape(text)}.*",
                QRegularExpression.PatternOption.CaseInsensitiveOption,
            )
        else:
            regex = QRegularExpression()
        self._filter_model.setFilterRegularExpression(regex)

    def _on_text_edited(self, text: str) -> None:
        self._has_explicit_selection = False
        self._apply_filter(text)
        self._completer.complete()

    def _on_completer_activated(self, index: QModelIndex) -> None:
        source_index = QModelIndex()
        if index.isValid() and index.model() is self._filter_model:
            source_index = self._filter_model.mapToSource(index)
        if not source_index.isValid():
            target_data = index.data(Qt.ItemDataRole.UserRole)
            target_text = index.data(Qt.ItemDataRole.DisplayRole)
            for row in range(self.count()):
                if target_data is not None and self.itemData(row, Qt.ItemDataRole.UserRole) == target_data:
                    source_index = self.model().index(row, self.modelColumn())
                    break
                if target_data is None and self.itemText(row) == target_text:
                    source_index = self.model().index(row, self.modelColumn())
                    break
        if not source_index.isValid():
            self._has_explicit_selection = False
            return
        self.setCurrentIndex(source_index.row())
        if self.lineEdit() is not None:
            self.lineEdit().setText(self.itemText(source_index.row()))
        self._has_explicit_selection = True

    def _on_combo_activated(self, index: int) -> None:
        self._has_explicit_selection = index >= 0

    def _on_current_index_changed(self, index: int) -> None:
        if index >= 0:
            self._has_explicit_selection = True


__all__ = ["FilterableComboBox"]
