"""Workspace UI for the MutaBoard board and inspector."""

from __future__ import annotations

from datetime import date

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
    QToolButton,
    Qt,
    QVBoxLayout,
    QWidget,
    get_theme_palette,
)
from .mutaboard_card import MUTABOARD_STAGES, MutaBoardCard
from .mutaboard_delegate import MutaBoardDelegate
from .mutaboard_model import MutaBoardModel, get_database
from mindnavigator.storage import (
    BOARD_COLUMN_COMPLETED,
    BOARD_COLUMN_DEFERRED,
    BOARD_COLUMN_IN_PROGRESS,
    BOARD_COLUMN_QUEUE,
    IdeaData,
    TaskData,
)

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
_LINK_FILTER_LABELS = {
    "all": "Все связи",
    "linked": "Только связанные",
    "unlinked": "Без связей",
}
_TASK_STAGE_TO_BOARD_COLUMN = {
    "prep": BOARD_COLUMN_QUEUE,
    "active": BOARD_COLUMN_IN_PROGRESS,
    "done": BOARD_COLUMN_COMPLETED,
    "frozen": BOARD_COLUMN_DEFERRED,
}
_IDEA_STAGE_TO_STATUS = {
    "inbox": "inbox",
    "thinking": "ripe",
    "prep": "work",
    "done": "done",
    "frozen": "archived",
}


class _MutaBoardColumnListWidget(QListWidget):
    _drag_card: MutaBoardCard | None = None

    def __init__(self, workspace: "MutaBoardWorkspace", board_stage: str, parent=None) -> None:
        super().__init__(parent)
        self._workspace = workspace
        self._board_stage = board_stage
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setUniformItemSizes(False)
        self.setSpacing(4)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)

    def startDrag(self, supported_actions: Qt.DropActions) -> None:  # noqa: N802
        current_item = self.currentItem()
        card = current_item.data(Qt.ItemDataRole.UserRole) if current_item is not None else None
        if card is None or not self._workspace._is_card_draggable(card):
            type(self)._drag_card = None
            return
        type(self)._drag_card = card
        super().startDrag(supported_actions)

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if self._workspace._can_accept_drop(type(self)._drag_card, self._board_stage):
            event.acceptProposedAction()
            return
        event.ignore()

    def dragMoveEvent(self, event) -> None:  # noqa: N802
        if self._workspace._can_accept_drop(type(self)._drag_card, self._board_stage):
            event.acceptProposedAction()
            return
        event.ignore()

    def dropEvent(self, event) -> None:  # noqa: N802
        card = type(self)._drag_card
        type(self)._drag_card = None
        if not self._workspace._can_accept_drop(card, self._board_stage):
            event.ignore()
            return
        assert card is not None
        self._workspace._move_card_to_stage(card, self._board_stage)
        event.acceptProposedAction()


class MutaBoardWorkspace(BaseWorkspace):
    """Workspace shell for the mixed-entity MutaBoard mode."""

    workspace_id = "mutaboard"
    workspace_title = "Мутаборд"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("MutaBoardWorkspace")
        self._base_workspace_stylesheet = self.styleSheet()
        self._db = get_database()
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

        self.linked_filter = QComboBox(self.filter_row)
        self.linked_filter.setObjectName("MutaBoardLinkedFilter")
        for key, label in _LINK_FILTER_LABELS.items():
            self.linked_filter.addItem(label, key)
        self.linked_filter.currentIndexChanged.connect(self._on_linked_filter_changed)

        self.actionable_only_checkbox = QCheckBox("Только actionable", self.filter_row)
        self.actionable_only_checkbox.setObjectName("MutaBoardActionableOnly")
        self.actionable_only_checkbox.toggled.connect(self._on_actionable_only_toggled)

        self.filter_bar_layout.insertWidget(self.filter_bar_layout.count() - 1, self.kind_filter)
        self.filter_bar_layout.insertWidget(self.filter_bar_layout.count() - 1, self.project_filter)
        self.filter_bar_layout.insertWidget(self.filter_bar_layout.count() - 1, self.linked_filter)
        self.filter_bar_layout.insertWidget(self.filter_bar_layout.count() - 1, self.actionable_only_checkbox)

    def _build_board_shell(self) -> None:
        root = QWidget(self)
        root.setObjectName("MutaBoardRoot")
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

            list_widget = _MutaBoardColumnListWidget(self, stage, column)
            list_widget.setObjectName("MutaBoardColumnList")
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
        self.inspector_links_value = QLabel("—")
        self.inspector_subtitle_value = QLabel("—")
        self.inspector_subtitle_value.setWordWrap(True)

        form.addRow("Тип", self.inspector_kind_value)
        form.addRow("Заголовок", self.inspector_title_value)
        form.addRow("Стадия", self.inspector_stage_value)
        form.addRow("Проект", self.inspector_project_value)
        form.addRow("Мета", self.inspector_meta_value)
        form.addRow("Связи", self.inspector_links_value)
        form.addRow("Описание", self.inspector_subtitle_value)
        inspector_layout.addWidget(self.inspector_form_host)

        self.inspector_footer = QLabel("Выберите карточку, чтобы увидеть связи и доступные мутации.")
        self.inspector_footer.setObjectName("MutaBoardInspectorFooter")
        self.inspector_footer.setWordWrap(True)
        self.inspector_primary_action = QToolButton(self.inspector)
        self.inspector_primary_action.setObjectName("MutaBoardInspectorAction")
        self.inspector_primary_action.clicked.connect(self._run_primary_action)
        inspector_layout.addWidget(self.inspector_primary_action)

        self.inspector_secondary_action = QToolButton(self.inspector)
        self.inspector_secondary_action.setObjectName("MutaBoardInspectorAction")
        self.inspector_secondary_action.clicked.connect(self._run_secondary_action)
        inspector_layout.addWidget(self.inspector_secondary_action)

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

    def set_status(self, text: str) -> None:
        super().set_status(text)
        self._base_workspace_stylesheet = self.styleSheet()
        self._apply_mutaboard_style()

    def set_error(self, text: str) -> None:
        super().set_error(text)
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
            linked_only=self._linked_filter_value(),
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
        linked_only = self.get_filters().get("linked_only")

        kind_index = self.kind_filter.findData(entity_kind if isinstance(entity_kind, str) else "all")
        self.kind_filter.blockSignals(True)
        self.kind_filter.setCurrentIndex(max(0, kind_index))
        self.kind_filter.blockSignals(False)

        self.actionable_only_checkbox.blockSignals(True)
        self.actionable_only_checkbox.setChecked(actionable_only)
        self.actionable_only_checkbox.blockSignals(False)

        linked_key = "all"
        if linked_only is True:
            linked_key = "linked"
        elif linked_only is False:
            linked_key = "unlinked"
        linked_index = self.linked_filter.findData(linked_key)
        self.linked_filter.blockSignals(True)
        self.linked_filter.setCurrentIndex(max(0, linked_index))
        self.linked_filter.blockSignals(False)

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
            self.inspector_links_value.setText("—")
            self.inspector_subtitle_value.setText("—")
            self.inspector_footer.setText("Выберите карточку, чтобы увидеть связи и доступные мутации.")
            self._set_action_button(self.inspector_primary_action, None)
            self._set_action_button(self.inspector_secondary_action, None)
            return
        self._selected_card_key = (card.entity_kind, card.entity_id)
        self.inspector_empty.hide()
        self.inspector_kind_value.setText(_KIND_LABELS.get(card.entity_kind, card.entity_kind))
        self.inspector_title_value.setText(card.title or "—")
        self.inspector_stage_value.setText(_STAGE_TITLES.get(card.stage, card.stage))
        self.inspector_project_value.setText(card.project_title or "—")
        self.inspector_meta_value.setText(card.meta_text or "—")
        self.inspector_links_value.setText(card.link_summary)
        self.inspector_subtitle_value.setText(card.subtitle or "—")
        actions = self._actions_for_card(card)
        self._set_action_button(self.inspector_primary_action, actions[0] if len(actions) > 0 else None)
        self._set_action_button(self.inspector_secondary_action, actions[1] if len(actions) > 1 else None)
        self.inspector_footer.setText(self._inspector_footer_text(card, actions))

    @staticmethod
    def _inspector_footer_text(card: MutaBoardCard, actions: list[tuple[str, str]]) -> str:
        if actions:
            action_names = ", ".join(action[0] for action in actions)
            return f"Связи: {card.link_summary}. Доступно: {action_names}."
        return f"Связи: {card.link_summary}. Для этой карточки нет inspector actions."

    @staticmethod
    def _set_action_button(button: QToolButton, action_payload: tuple[str, str] | None) -> None:
        if action_payload is None:
            button.hide()
            button.setEnabled(False)
            button.setText("")
            button.setProperty("action_key", "")
            return
        button.setText(action_payload[0])
        button.setProperty("action_key", action_payload[1])
        button.setEnabled(True)
        button.show()

    def _actions_for_card(self, card: MutaBoardCard) -> list[tuple[str, str]]:
        if card.entity_kind == "idea":
            return [
                ("Создать задачу", "idea_create_task"),
                ("Создать объект", "idea_create_object"),
            ]
        if card.entity_kind == "object":
            return [
                ("Создать задачу", "object_create_task"),
                ("Создать идею", "object_create_idea"),
            ]
        if card.entity_kind == "task":
            return [
                ("Создать идею", "task_create_idea"),
                ("Создать объект", "task_create_object"),
            ]
        return []

    def _can_accept_drop(self, card: MutaBoardCard | None, target_stage: str) -> bool:
        if card is None:
            return False
        return self._can_move_card_to_stage(card, target_stage)

    @staticmethod
    def _is_card_draggable(card: MutaBoardCard) -> bool:
        return bool(card.can_drag)

    def _can_move_card_to_stage(self, card: MutaBoardCard, target_stage: str) -> bool:
        if target_stage == card.stage:
            return False
        if card.entity_kind == "task":
            payload = card.source_payload
            return isinstance(payload, TaskData) and not payload.done and target_stage in _TASK_STAGE_TO_BOARD_COLUMN
        if card.entity_kind == "idea":
            return target_stage in _IDEA_STAGE_TO_STATUS
        return False

    def _move_card_to_stage(self, card: MutaBoardCard, target_stage: str) -> None:
        if not self._can_move_card_to_stage(card, target_stage):
            self.set_status("Мутаборд: перенос для этой карточки недоступен.")
            return
        if card.entity_kind == "task":
            board_column = _TASK_STAGE_TO_BOARD_COLUMN.get(target_stage)
            if board_column is None:
                self.set_status("Мутаборд: stage не маппится в task board column.")
                return
            self._db.set_task_board_column(card.entity_id, board_column)
            self.refresh()
            self.set_status(f"Мутаборд: задача перенесена в {_STAGE_TITLES[target_stage].lower()}.")
            return
        if card.entity_kind == "idea":
            payload = card.source_payload
            if not isinstance(payload, IdeaData):
                self.set_status("Мутаборд: идея не содержит полного payload.")
                return
            self._move_idea_to_stage(payload, target_stage)

    def _move_idea_to_stage(self, idea: IdeaData, target_stage: str) -> None:
        next_status = _IDEA_STAGE_TO_STATUS.get(target_stage)
        if next_status is None:
            self.set_status("Мутаборд: stage не маппится в idea status.")
            return
        if idea.archived_at is not None and next_status != "archived":
            self._db.set_idea_archived(idea.id, False)
        archived = next_status == "archived"
        self._db.update_idea(
            idea_id=idea.id,
            title=idea.title,
            summary=idea.summary,
            body_md=idea.body_md,
            idea_type=idea.type,
            status=next_status,
            value_score=idea.value_score,
            effort_score=idea.effort_score,
            project_id=idea.project_id,
            source=idea.source,
        )
        if archived:
            self._db.set_idea_archived(idea.id, True)
        self.refresh()
        self.set_status(f"Мутаборд: идея перенесена в {_STAGE_TITLES[target_stage].lower()}.")

    def _run_primary_action(self) -> None:
        self._run_inspector_action(self.inspector_primary_action.property("action_key"))

    def _run_secondary_action(self) -> None:
        self._run_inspector_action(self.inspector_secondary_action.property("action_key"))

    def _run_inspector_action(self, action_key: object) -> None:
        if not isinstance(action_key, str) or not action_key:
            return
        selected_card = self._selected_card()
        if selected_card is None:
            self.set_status("Мутаборд: сначала выберите карточку.")
            return
        if action_key == "idea_create_task" and isinstance(selected_card.source_payload, IdeaData):
            self._create_task_from_idea(selected_card.source_payload)
            return
        if action_key == "idea_create_object" and isinstance(selected_card.source_payload, IdeaData):
            self._create_object_from_idea(selected_card.source_payload)
            return
        if action_key == "object_create_task":
            self._create_task_from_object(selected_card)
            return
        if action_key == "object_create_idea":
            self._create_idea_from_object(selected_card)
            return
        if action_key == "task_create_idea" and isinstance(selected_card.source_payload, TaskData):
            self._create_idea_from_task(selected_card.source_payload)
            return
        if action_key == "task_create_object" and isinstance(selected_card.source_payload, TaskData):
            self._create_object_from_task(selected_card.source_payload)
            return
        self.set_status("Мутаборд: action пока не поддерживается.")

    def _selected_card(self) -> MutaBoardCard | None:
        if self._selected_card_key is None:
            return None
        for card in self._model.cards():
            if (card.entity_kind, card.entity_id) == self._selected_card_key:
                return card
        return None

    def _create_task_from_idea(self, idea: IdeaData) -> None:
        task = self._db.create_task(
            title=idea.title,
            description=idea.body_md or idea.summary,
            day=date.today(),
            time_text="",
            priority="Medium",
            project_id=idea.project_id,
        )
        self._db.add_idea_relation(idea.id, "task", task.id)
        if idea.archived_at is not None:
            self._db.set_idea_archived(idea.id, False)
        self._db.update_idea(
            idea_id=idea.id,
            title=idea.title,
            summary=idea.summary,
            body_md=idea.body_md,
            idea_type=idea.type,
            status="ripe",
            value_score=idea.value_score,
            effort_score=idea.effort_score,
            project_id=idea.project_id,
            source=idea.source,
        )
        self._selected_card_key = ("task", task.id)
        self.refresh()
        self.set_status("Мутаборд: из идеи создана задача.")

    def _create_object_from_idea(self, idea: IdeaData) -> None:
        obj = self._db.create_object(
            title=idea.title,
            catalog=idea.project_title,
            object_type="",
            status="",
            description=idea.body_md or idea.summary,
        )
        self._db.add_idea_relation(idea.id, "object", obj.id)
        if idea.archived_at is not None:
            self._db.set_idea_archived(idea.id, False)
        self._db.update_idea(
            idea_id=idea.id,
            title=idea.title,
            summary=idea.summary,
            body_md=idea.body_md,
            idea_type=idea.type,
            status="ripe",
            value_score=idea.value_score,
            effort_score=idea.effort_score,
            project_id=idea.project_id,
            source=idea.source,
        )
        self._selected_card_key = ("object", obj.id)
        self.refresh()
        self.set_status("Мутаборд: из идеи создан объект.")

    def _create_task_from_object(self, card: MutaBoardCard) -> None:
        task = self._db.create_task(
            title=card.title,
            description=card.subtitle if card.subtitle != "Без описания" else card.meta_text,
            day=date.today(),
            time_text="",
            priority="Medium",
        )
        self._db.add_task_attachment(task.id, "object", card.entity_id)
        self._selected_card_key = ("task", task.id)
        self.refresh()
        self.set_status("Мутаборд: из объекта создана задача.")

    def _create_idea_from_object(self, card: MutaBoardCard) -> None:
        idea = self._db.create_idea(
            title=card.title,
            summary=card.subtitle if card.subtitle != "Без описания" else "",
            body_md=card.meta_text,
            idea_type="other",
            status="inbox",
            source=card.project_title or card.meta_text,
        )
        self._db.add_idea_relation(idea.id, "object", card.entity_id)
        self._selected_card_key = ("idea", idea.id)
        self.refresh()
        self.set_status("Мутаборд: из объекта создана идея.")

    def _create_idea_from_task(self, task: TaskData) -> None:
        idea = self._db.create_idea(
            title=task.title,
            summary=task.description,
            body_md=task.description,
            idea_type="other",
            status="work" if task.board_column == BOARD_COLUMN_IN_PROGRESS else "ripe",
            project_id=task.project_id,
            source=f"MN-{task.id}",
        )
        self._db.add_idea_relation(idea.id, "task", task.id)
        self._selected_card_key = ("idea", idea.id)
        self.refresh()
        self.set_status("Мутаборд: из задачи создана идея.")

    def _create_object_from_task(self, task: TaskData) -> None:
        obj = self._db.create_object(
            title=task.title,
            catalog=task.project_title,
            object_type="",
            status="",
            description=task.description,
        )
        self._db.add_task_attachment(task.id, "object", obj.id)
        self._selected_card_key = ("object", obj.id)
        self.refresh()
        self.set_status("Мутаборд: из задачи создан объект.")

    def _refresh_status(self) -> None:
        total_count = len(self._model.cards())
        visible_count = len(self._filtered_cards())
        if self.search_input.text().strip() or self.get_filters():
            self.set_status(f"Мутаборд: карточек {visible_count} из {total_count}.")
            return
        self.set_status(f"Мутаборд: карточек {total_count}.")

    def _linked_filter_value(self) -> bool | None:
        current = self.linked_filter.currentData()
        if current == "linked":
            return True
        if current == "unlinked":
            return False
        return None

    def _apply_mutaboard_style(self) -> None:
        palette = get_theme_palette("dark")
        shell_bg = "#0d1218"
        shell_panel = "#121922"
        shell_panel_alt = "#18212c"
        shell_input = "#141c26"
        shell_input_hover = "#1a2431"
        shell_border = "#273140"
        shell_border_strong = "#3a4658"
        shell_text = "#eef4ff"
        shell_dim_text = "#95a3b8"
        shell_muted = "#71839b"
        self.setStyleSheet(
            self._base_workspace_stylesheet
            + f"""
            QWidget#WorkspaceToolbar,
            QWidget#WorkspaceSearch,
            QWidget#WorkspaceFilters,
            QWidget#WorkspaceContent,
            QWidget#MutaBoardRoot {{
                background: {shell_panel};
                border: 1px solid {shell_border};
                border-radius: 12px;
                padding: 6px;
            }}
            QWidget#WorkspaceContent,
            QWidget#MutaBoardRoot {{
                border: none;
                border-radius: 0px;
                padding: 0px;
            }}
            QLineEdit#WorkspaceSearchInput {{
                background: {shell_input};
                color: {shell_text};
                border: 1px solid {shell_border};
                border-radius: 8px;
                padding: 6px 8px;
                selection-background-color: {palette.selection_bg};
                selection-color: {palette.selection_text};
            }}
            QLineEdit#WorkspaceSearchInput:focus {{
                border: 1px solid {palette.accent};
            }}
            QToolButton#WorkspaceSearchClear {{
                background: {shell_input};
                color: {shell_text};
                border: 1px solid {shell_border_strong};
                border-radius: 8px;
                padding: 4px 8px;
            }}
            QToolButton#WorkspaceSearchClear:hover {{
                background: {shell_input_hover};
                color: {palette.selection_text};
            }}
            QLabel#WorkspaceStatus {{
                color: {shell_dim_text};
            }}
            QWidget#MutaBoardWorkspace {{
                background: {shell_bg};
            }}
            QLabel#MutaBoardSummary {{
                color: {shell_dim_text};
                font-size: 12px;
            }}
            QFrame#MutaBoardBoardWrap,
            QFrame#MutaBoardInspector,
            QFrame#MutaBoardColumn {{
                background: {shell_panel};
                border: 1px solid {shell_border};
                border-radius: 14px;
            }}
            QFrame#MutaBoardInspector {{
                background: {shell_panel_alt};
                border-color: {shell_border_strong};
            }}
            QScrollArea#MutaBoardScroll,
            QWidget#MutaBoardColumnsHost,
            QWidget#qt_scrollarea_viewport {{
                background: {shell_bg};
                border: none;
            }}
            QSplitter#MutaBoardSplitter::handle {{
                background: {shell_bg};
                width: 10px;
            }}
            QLabel#MutaBoardColumnTitle,
            QLabel#MutaBoardInspectorTitle {{
                color: {shell_text};
                font-size: 13px;
                font-weight: 700;
            }}
            QListWidget#MutaBoardColumnList {{
                background: {shell_panel};
                color: {shell_text};
                border: 1px solid {shell_border};
                border-radius: 10px;
                outline: none;
            }}
            QListWidget#MutaBoardColumnList::item {{
                background: transparent;
                border: none;
            }}
            QListWidget#MutaBoardColumnList::item:selected {{
                background: transparent;
                color: {shell_text};
            }}
            QComboBox#MutaBoardKindFilter,
            QComboBox#MutaBoardProjectFilter,
            QComboBox#MutaBoardLinkedFilter {{
                background: {shell_input};
                color: {shell_text};
                border: 1px solid {shell_border};
                border-radius: 8px;
                padding: 5px 8px;
                min-width: 140px;
            }}
            QComboBox#MutaBoardKindFilter::drop-down,
            QComboBox#MutaBoardProjectFilter::drop-down,
            QComboBox#MutaBoardLinkedFilter::drop-down {{
                border: none;
                background: {shell_input};
                width: 22px;
            }}
            QComboBox#MutaBoardKindFilter:hover,
            QComboBox#MutaBoardProjectFilter:hover,
            QComboBox#MutaBoardLinkedFilter:hover {{
                background: {shell_input_hover};
                border-color: {shell_border_strong};
            }}
            QComboBox#MutaBoardKindFilter QAbstractItemView,
            QComboBox#MutaBoardProjectFilter QAbstractItemView,
            QComboBox#MutaBoardLinkedFilter QAbstractItemView {{
                background: {shell_panel_alt};
                color: {shell_text};
                border: 1px solid {shell_border};
                selection-background-color: {palette.selection_bg};
                selection-color: {palette.selection_text};
                outline: none;
            }}
            QCheckBox#MutaBoardActionableOnly {{
                color: {shell_text};
                spacing: 6px;
            }}
            QCheckBox#MutaBoardActionableOnly::indicator {{
                width: 14px;
                height: 14px;
                border-radius: 4px;
                border: 1px solid {shell_border_strong};
                background: {shell_input};
            }}
            QCheckBox#MutaBoardActionableOnly::indicator:checked {{
                background: {palette.accent};
                border-color: {palette.accent_hover};
            }}
            QToolButton#MutaBoardInspectorAction {{
                color: {shell_text};
                background: {shell_input};
                border: 1px solid {shell_border_strong};
                border-radius: 8px;
                padding: 7px 10px;
                min-height: 30px;
                text-align: left;
            }}
            QToolButton#MutaBoardInspectorAction:hover {{
                background: {palette.selection_bg};
                color: {palette.selection_text};
            }}
            QLabel#MutaBoardInspectorEmpty,
            QLabel#MutaBoardInspectorFooter,
            QWidget#MutaBoardInspectorFormHost QLabel {{
                color: {shell_dim_text};
            }}
            QWidget#MutaBoardInspectorFormHost {{
                background: transparent;
            }}
            QWidget#MutaBoardInspectorFormHost QLabel {{
                background: transparent;
            }}
            QScrollBar:vertical,
            QScrollBar:horizontal {{
                background: {shell_panel};
                border: none;
                margin: 0px;
            }}
            QScrollBar::handle:vertical,
            QScrollBar::handle:horizontal {{
                background: {shell_border_strong};
                border-radius: 6px;
                min-height: 24px;
                min-width: 24px;
            }}
            QScrollBar::handle:vertical:hover,
            QScrollBar::handle:horizontal:hover {{
                background: {shell_muted};
            }}
            QScrollBar::add-line,
            QScrollBar::sub-line,
            QScrollBar::add-page,
            QScrollBar::sub-page {{
                background: transparent;
                border: none;
            }}
            """
        )

    def _on_kind_filter_changed(self) -> None:
        current_kind = self.kind_filter.currentData()
        self.set_filter("entity_kind", None if current_kind == "all" else current_kind)

    def _on_project_filter_changed(self) -> None:
        current_project = self.project_filter.currentData()
        self.set_filter("project_id", current_project if isinstance(current_project, int) else None)

    def _on_linked_filter_changed(self) -> None:
        self.set_filter("linked_only", self._linked_filter_value())

    def _on_actionable_only_toggled(self, checked: bool) -> None:
        self.set_filter("actionable_only", checked if checked else None)
