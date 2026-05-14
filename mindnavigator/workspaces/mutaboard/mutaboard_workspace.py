"""Workspace UI for the MutaBoard board and inspector."""

from __future__ import annotations

from ._shared import (
    BaseWorkspace,
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    Qt,
    QVBoxLayout,
    QWidget,
    get_theme_palette,
)
from .mutaboard_card import MUTABOARD_STAGES, MutaBoardCard
from .mutaboard_delegate import MutaBoardDelegate
from .mutaboard_model import MutaBoardModel

_STAGE_TITLES = {
    "inbox": "Inbox",
    "thinking": "Осмысление",
    "prep": "Подготовка",
    "active": "В работе",
    "review": "Проверка",
    "done": "Готово",
    "frozen": "Заморожено",
}
_KIND_LABELS = {
    "all": "Все сущности",
    "task": "Задачи",
    "idea": "Идеи",
    "object": "Объекты",
}


class MutaBoardWorkspace(BaseWorkspace):
    """Workspace shell for the mixed-entity MutaBoard mode."""

    workspace_id = "mutaboard"
    workspace_title = "Мутаборд"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("MutaBoardWorkspace")
        self._base_workspace_stylesheet = self.styleSheet()
        self._model = MutaBoardModel()
        self._column_lists: dict[str, QListWidget] = {}
        self.board_columns: dict[str, QListWidget] = self._column_lists
        self._selected_card_key: tuple[str, int] | None = None
        self.search_input.setPlaceholderText("Поиск по мутаборду")
        self._build_filters()
        self._build_board_shell()
        self.refresh()

    def _build_filters(self) -> None:
        self.kind_filter = QComboBox(self.filter_row)
        self.kind_filter.setObjectName("MutaBoardKindFilter")
        for kind, label in _KIND_LABELS.items():
            self.kind_filter.addItem(label, kind)
        self.kind_filter.currentIndexChanged.connect(self._on_kind_filter_changed)

        self.project_filter = QComboBox(self.filter_row)
        self.project_filter.setObjectName("MutaBoardProjectFilter")
        self.project_filter.currentIndexChanged.connect(self._on_project_filter_changed)

        self.actionable_only_checkbox = QCheckBox("Только actionable", self.filter_row)
        self.actionable_only_checkbox.setObjectName("MutaBoardActionableOnly")
        self.actionable_only_checkbox.toggled.connect(self._on_actionable_only_toggled)

        self.filter_bar_layout.insertWidget(self.filter_bar_layout.count() - 1, self.kind_filter)
        self.filter_bar_layout.insertWidget(self.filter_bar_layout.count() - 1, self.project_filter)
        self.filter_bar_layout.insertWidget(self.filter_bar_layout.count() - 1, self.actionable_only_checkbox)

    def _build_board_shell(self) -> None:
        root = QWidget(self)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(10)

        summary = QLabel(
            "Единое поле для задач, идей и объектов. На этом этапе доска уже собирает mixed-card поток "
            "и синхронизирует выделение с inspector."
        )
        summary.setObjectName("MutaBoardSummary")
        summary.setWordWrap(True)
        root_layout.addWidget(summary)

        self.splitter = QSplitter(Qt.Orientation.Horizontal, root)
        self.splitter.setObjectName("MutaBoardSplitter")

        board_wrap = QFrame(self.splitter)
        board_wrap.setObjectName("MutaBoardBoardWrap")
        board_wrap_layout = QVBoxLayout(board_wrap)
        board_wrap_layout.setContentsMargins(0, 0, 0, 0)
        board_wrap_layout.setSpacing(0)

        self.board_scroll = QScrollArea(board_wrap)
        self.board_scroll.setObjectName("MutaBoardScroll")
        self.board_scroll.setWidgetResizable(True)
        self.board_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.board_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.board_inner = QWidget()
        self.board_inner.setObjectName("MutaBoardColumnsHost")
        self.board_layout = QHBoxLayout(self.board_inner)
        self.board_layout.setContentsMargins(0, 0, 0, 0)
        self.board_layout.setSpacing(10)

        self._column_title_labels: dict[str, QLabel] = {}
        for stage in MUTABOARD_STAGES:
            column = QFrame(self.board_inner)
            column.setObjectName("MutaBoardColumn")
            column.setProperty("board_stage", stage)
            column_layout = QVBoxLayout(column)
            column_layout.setContentsMargins(10, 10, 10, 10)
            column_layout.setSpacing(8)

            title_label = QLabel(_STAGE_TITLES[stage])
            title_label.setObjectName("MutaBoardColumnTitle")
            column_layout.addWidget(title_label)
            self._column_title_labels[stage] = title_label

            list_widget = QListWidget(column)
            list_widget.setObjectName("MutaBoardColumnList")
            list_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
            list_widget.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
            list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            list_widget.setUniformItemSizes(False)
            list_widget.setSpacing(4)
            list_widget.setItemDelegate(MutaBoardDelegate(list_widget))
            list_widget.itemSelectionChanged.connect(
                lambda current_stage=stage: self._on_column_selection_changed(current_stage)
            )
            column_layout.addWidget(list_widget, 1)
            self.board_layout.addWidget(column, 1)
            self._column_lists[stage] = list_widget

        self.board_scroll.setWidget(self.board_inner)
        board_wrap_layout.addWidget(self.board_scroll, 1)

        self.inspector = QFrame(self.splitter)
        self.inspector.setObjectName("MutaBoardInspector")
        self.inspector.setMinimumWidth(280)
        self.inspector.setMaximumWidth(380)
        inspector_layout = QVBoxLayout(self.inspector)
        inspector_layout.setContentsMargins(16, 16, 16, 16)
        inspector_layout.setSpacing(12)

        inspector_title = QLabel("Inspector")
        inspector_title.setObjectName("MutaBoardInspectorTitle")
        inspector_layout.addWidget(inspector_title)

        self.inspector_empty = QLabel("Выберите карточку на доске.")
        self.inspector_empty.setObjectName("MutaBoardInspectorEmpty")
        self.inspector_empty.setWordWrap(True)
        inspector_layout.addWidget(self.inspector_empty)

        self.inspector_form_host = QWidget(self.inspector)
        self.inspector_form_host.setObjectName("MutaBoardInspectorFormHost")
        form = QFormLayout(self.inspector_form_host)
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(8)

        self.inspector_kind_value = QLabel("—")
        self.inspector_title_value = QLabel("—")
        self.inspector_stage_value = QLabel("—")
        self.inspector_project_value = QLabel("—")
        self.inspector_meta_value = QLabel("—")
        self.inspector_subtitle_value = QLabel("—")
        self.inspector_subtitle_value.setWordWrap(True)

        form.addRow("Тип", self.inspector_kind_value)
        form.addRow("Заголовок", self.inspector_title_value)
        form.addRow("Стадия", self.inspector_stage_value)
        form.addRow("Проект", self.inspector_project_value)
        form.addRow("Мета", self.inspector_meta_value)
        form.addRow("Описание", self.inspector_subtitle_value)
        inspector_layout.addWidget(self.inspector_form_host)

        self.inspector_footer = QLabel("Phase 3: read-only board + selection sync.")
        self.inspector_footer.setObjectName("MutaBoardInspectorFooter")
        self.inspector_footer.setWordWrap(True)
        inspector_layout.addWidget(self.inspector_footer)
        inspector_layout.addStretch(1)

        self.splitter.addWidget(board_wrap)
        self.splitter.addWidget(self.inspector)
        self.splitter.setStretchFactor(0, 4)
        self.splitter.setStretchFactor(1, 1)
        root_layout.addWidget(self.splitter, 1)

        self.set_content(root)
        self._set_selected_card(None)
        self._apply_mutaboard_style()

    def set_theme_mode(self, theme_mode: str) -> None:
        super().set_theme_mode(theme_mode)
        self._base_workspace_stylesheet = self.styleSheet()
        self._apply_mutaboard_style()

    def apply_query(self, query: str) -> None:
        self._populate_board()
        self._refresh_status()

    def apply_filters(self, filters: dict[str, object]) -> None:
        self._populate_board()
        self._refresh_status()

    def refresh(self) -> None:
        self._model.reload()
        self._refresh_project_options()
        self._populate_board()
        self._refresh_status()

    def on_enter(self, context: dict | None = None) -> None:
        super().on_enter(context)
        self._sync_filter_controls_from_state()
        self._populate_board()
        self._refresh_status()

    def _refresh_project_options(self) -> None:
        current_project_id = self.project_filter.currentData()
        project_pairs = sorted(
            {
                (card.project_id, card.project_title)
                for card in self._model.cards()
                if card.project_id is not None and card.project_title
            },
            key=lambda pair: pair[1].casefold(),
        )
        self.project_filter.blockSignals(True)
        self.project_filter.clear()
        self.project_filter.addItem("Все проекты", None)
        for project_id, project_title in project_pairs:
            self.project_filter.addItem(project_title, project_id)
        restore_index = self.project_filter.findData(current_project_id)
        self.project_filter.setCurrentIndex(max(0, restore_index))
        self.project_filter.blockSignals(False)

    def _filtered_cards(self) -> list[MutaBoardCard]:
        project_id = self.project_filter.currentData()
        return self._model.filtered_cards(
            query=self.search_input.text(),
            entity_kind=self.kind_filter.currentData(),
            project_id=project_id if isinstance(project_id, int) else None,
            actionable_only=self.actionable_only_checkbox.isChecked(),
        )

    def _populate_board(self) -> None:
        cards = self._filtered_cards()
        grouped = self._model.grouped_cards(cards)
        selection_key = self._selected_card_key
        for stage, list_widget in self._column_lists.items():
            list_widget.blockSignals(True)
            list_widget.clear()
            stage_cards = grouped.get(stage, [])
            for card in stage_cards:
                item = QListWidgetItem(card.title)
                item.setData(Qt.ItemDataRole.UserRole, card)
                item.setToolTip(card.meta_text or card.subtitle or card.title)
                list_widget.addItem(item)
            self._column_title_labels[stage].setText(f"{_STAGE_TITLES[stage]} · {len(stage_cards)}")
            list_widget.blockSignals(False)
        if selection_key is not None and self._restore_selection(selection_key):
            return
        self._set_selected_card(None)

    def _sync_filter_controls_from_state(self) -> None:
        entity_kind = self.get_filters().get("entity_kind")
        actionable_only = bool(self.get_filters().get("actionable_only"))
        project_id = self.get_filters().get("project_id")

        kind_index = self.kind_filter.findData(entity_kind if isinstance(entity_kind, str) else "all")
        self.kind_filter.blockSignals(True)
        self.kind_filter.setCurrentIndex(max(0, kind_index))
        self.kind_filter.blockSignals(False)

        self.actionable_only_checkbox.blockSignals(True)
        self.actionable_only_checkbox.setChecked(actionable_only)
        self.actionable_only_checkbox.blockSignals(False)

        project_index = self.project_filter.findData(project_id if isinstance(project_id, int) else None)
        self.project_filter.blockSignals(True)
        self.project_filter.setCurrentIndex(max(0, project_index))
        self.project_filter.blockSignals(False)

    def _restore_selection(self, selection_key: tuple[str, int]) -> bool:
        for list_widget in self._column_lists.values():
            for index in range(list_widget.count()):
                item = list_widget.item(index)
                card = item.data(Qt.ItemDataRole.UserRole)
                if card is None:
                    continue
                if (card.entity_kind, card.entity_id) != selection_key:
                    continue
                list_widget.blockSignals(True)
                list_widget.setCurrentItem(item)
                list_widget.blockSignals(False)
                self._set_selected_card(card)
                return True
        return False

    def _on_column_selection_changed(self, stage: str) -> None:
        current_list = self._column_lists[stage]
        current_item = current_list.currentItem()
        if current_item is None:
            if not any(list_widget.currentItem() is not None for list_widget in self._column_lists.values()):
                self._set_selected_card(None)
            return
        for other_stage, list_widget in self._column_lists.items():
            if other_stage == stage:
                continue
            list_widget.blockSignals(True)
            list_widget.clearSelection()
            list_widget.setCurrentItem(None)
            list_widget.blockSignals(False)
        self._set_selected_card(current_item.data(Qt.ItemDataRole.UserRole))

    def _set_selected_card(self, card: MutaBoardCard | None) -> None:
        if card is None:
            self._selected_card_key = None
            self.inspector_empty.show()
            self.inspector_kind_value.setText("—")
            self.inspector_title_value.setText("—")
            self.inspector_stage_value.setText("—")
            self.inspector_project_value.setText("—")
            self.inspector_meta_value.setText("—")
            self.inspector_subtitle_value.setText("—")
            return
        self._selected_card_key = (card.entity_kind, card.entity_id)
        self.inspector_empty.hide()
        self.inspector_kind_value.setText(_KIND_LABELS.get(card.entity_kind, card.entity_kind))
        self.inspector_title_value.setText(card.title or "—")
        self.inspector_stage_value.setText(_STAGE_TITLES.get(card.stage, card.stage))
        self.inspector_project_value.setText(card.project_title or "—")
        self.inspector_meta_value.setText(card.meta_text or "—")
        self.inspector_subtitle_value.setText(card.subtitle or "—")

    def _refresh_status(self) -> None:
        total_count = len(self._model.cards())
        visible_count = len(self._filtered_cards())
        if self.search_input.text().strip() or self.get_filters():
            self.set_status(f"Мутаборд: карточек {visible_count} из {total_count}.")
            return
        self.set_status(f"Мутаборд: карточек {total_count}.")

    def _apply_mutaboard_style(self) -> None:
        palette = get_theme_palette(self._theme_mode)
        self.setStyleSheet(
            self._base_workspace_stylesheet
            + f"""
            QWidget#MutaBoardWorkspace {{
                background: transparent;
            }}
            QLabel#MutaBoardSummary {{
                color: {palette.dim_text};
                font-size: 12px;
            }}
            QFrame#MutaBoardBoardWrap,
            QFrame#MutaBoardInspector,
            QFrame#MutaBoardColumn {{
                background: {palette.panel_bg};
                border: 1px solid {palette.border};
                border-radius: 14px;
            }}
            QScrollArea#MutaBoardScroll,
            QWidget#MutaBoardColumnsHost,
            QWidget#qt_scrollarea_viewport {{
                background: transparent;
                border: none;
            }}
            QLabel#MutaBoardColumnTitle,
            QLabel#MutaBoardInspectorTitle {{
                color: {palette.text};
                font-size: 13px;
                font-weight: 700;
            }}
            QListWidget#MutaBoardColumnList {{
                background: transparent;
                border: none;
                outline: none;
            }}
            QListWidget#MutaBoardColumnList::item {{
                background: transparent;
                border: none;
            }}
            QComboBox#MutaBoardKindFilter,
            QComboBox#MutaBoardProjectFilter {{
                background: {palette.input_bg};
                color: {palette.text};
                border: 1px solid {palette.border};
                border-radius: 6px;
                padding: 5px 8px;
                min-width: 140px;
            }}
            QCheckBox#MutaBoardActionableOnly {{
                color: {palette.text};
                spacing: 6px;
            }}
            QLabel#MutaBoardInspectorEmpty,
            QLabel#MutaBoardInspectorFooter,
            QWidget#MutaBoardInspectorFormHost QLabel {{
                color: {palette.dim_text};
            }}
            """
        )

    def _on_kind_filter_changed(self) -> None:
        current_kind = self.kind_filter.currentData()
        self.set_filter("entity_kind", None if current_kind == "all" else current_kind)

    def _on_project_filter_changed(self) -> None:
        current_project = self.project_filter.currentData()
        self.set_filter("project_id", current_project if isinstance(current_project, int) else None)

    def _on_actionable_only_toggled(self, checked: bool) -> None:
        self.set_filter("actionable_only", checked if checked else None)
