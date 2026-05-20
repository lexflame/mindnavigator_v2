"""Workspace UI for the persistent ConceptBoard experience."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from ._shared import (
    BaseWorkspace,
    QAbstractItemView,
    QComboBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTabWidget,
    QTextEdit,
    Qt,
    QVBoxLayout,
    QWidget,
    get_theme_palette,
)
from .concept_board_card import ConceptBoardCard
from .concept_board_delegate import ConceptBoardDelegate
from .concept_board_model import ConceptBoardModel, get_database
from mindnavigator.storage import (
    CloudFileData,
    IdeaData,
    MapData,
    MapMarkerData,
    ConceptBoardLinkData,
    ConceptBoardColumnData,
    ConceptBoardData,
    ConceptBoardSolutionData,
    ConceptBoardVersionData,
    NoteData,
    ObjectData,
    ProjectData,
    TaskData,
)

_COLUMN_KIND_LABELS = {
    "task": "Задачи",
    "idea": "Идеи",
    "image": "Материалы",
    "map": "Карты",
    "marker": "Метки",
    "note": "Заметки",
    "project": "Проекты",
    "object": "Объекты",
    "version": "Версии",
    "solution": "Решение",
    "file": "Файлы",
    "link": "Ссылки",
}
_CARD_KIND_TITLES = {
    "task": "Задача",
    "idea": "Идея",
    "image": "Изображение",
    "map": "Карта",
    "marker": "Метка",
    "note": "Заметка",
    "project": "Проект",
    "object": "Объект",
    "version": "Версия",
    "solution": "Решение",
    "file": "Файл",
    "link": "Ссылка",
}
_DEFAULT_COLUMN_KINDS = ("task", "idea", "image", "version", "solution")
_DEFAULT_COLUMN_SPECS = (
    ("task", "Входящие"),
    ("idea", "Идеи"),
    ("image", "Материалы"),
    ("version", "Версии"),
    ("task", "Задачи"),
    ("solution", "Решение"),
)
_DISABLED_ACTION_TOOLTIP = "Действие будет доступно на следующем этапе ремастеринга."


_CONCEPT_STATUS_TITLES = {
    "draft": "Р§РµСЂРЅРѕРІРёРє",
    "review": "РќР° РїСЂРѕРІРµСЂРєРµ",
    "accepted": "РџСЂРёРЅСЏС‚Рѕ",
    "rejected": "РћС‚РєР»РѕРЅРµРЅРѕ",
}
_LINK_TYPE_TITLES = {
    "relates_to": "РѕС‚РЅРѕСЃРёС‚СЃСЏ Рє",
    "inspires": "РІРґРѕС…РЅРѕРІР»СЏРµС‚",
    "develops": "СЂР°Р·РІРёРІР°РµС‚",
    "transforms_to": "РїСЂРµРІСЂР°С‰Р°РµС‚СЃСЏ РІ",
    "contradicts": "РїСЂРѕС‚РёРІРѕСЂРµС‡РёС‚",
}


class _ConceptBoardColumnListWidget(QListWidget):
    def __init__(self, workspace: "ConceptBoardWorkspace", column_id: int, parent=None) -> None:
        super().__init__(parent)
        self._workspace = workspace
        self._column_id = column_id
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setUniformItemSizes(False)
        self.setSpacing(4)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._open_context_menu)

    def _open_context_menu(self, pos) -> None:
        item = self.itemAt(pos)
        if item is None:
            return
        card = item.data(Qt.ItemDataRole.UserRole)
        if card is None:
            return
        self._workspace._open_card_context_menu(card, self.mapToGlobal(pos))


class ConceptBoardWorkspace(BaseWorkspace):
    """Workspace shell for persistent concept boards and board-specific columns."""

    workspace_id = "concept_board"
    workspace_title = "Концептборд"

    def _build_ui(self) -> None:
        super()._build_ui()
        self.toolbar_row.setVisible(False)
        self.link_scope_filter = QComboBox()
        self.link_scope_filter.setObjectName("ConceptBoardFilterCombo")
        self.link_scope_filter.addItem("Все элементы", "all")
        self.link_scope_filter.addItem("Только связанные", "linked")
        self.link_scope_filter.addItem("Без связей", "unlinked")
        self.link_scope_filter.currentIndexChanged.connect(self._on_link_scope_filter_changed)

        self.action_scope_filter = QComboBox()
        self.action_scope_filter.setObjectName("ConceptBoardFilterCombo")
        self.action_scope_filter.addItem("Все состояния", "all")
        self.action_scope_filter.addItem("Только требующие действия", "actionable")
        self.action_scope_filter.currentIndexChanged.connect(self._on_action_scope_filter_changed)

        self.filter_layout.addWidget(QLabel("Связи"))
        self.filter_layout.addWidget(self.link_scope_filter)
        self.filter_layout.addWidget(QLabel("Режим"))
        self.filter_layout.addWidget(self.action_scope_filter)
        self.filter_layout.addStretch(1)

        search_layout = self.search_row.layout()
        self.link_scope_label = QLabel("РЎРІСЏР·Рё")
        self.action_scope_label = QLabel("Р РµР¶РёРј")
        search_layout.insertWidget(0, self.link_scope_label)
        search_layout.insertWidget(1, self.link_scope_filter)
        search_layout.insertWidget(2, self.action_scope_label)
        search_layout.insertWidget(3, self.action_scope_filter)
        self.link_scope_label.setText("Связи")
        self.action_scope_label.setText("Режим")
        self.filter_row.setVisible(False)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ConceptBoardWorkspace")
        self._base_workspace_stylesheet = self.styleSheet()
        self._db = get_database()
        self._model = ConceptBoardModel(db=self._db)
        self._concept_boards_by_id: dict[int, ConceptBoardData] = {}
        self._column_defs: dict[int, ConceptBoardColumnData] = {}
        self._column_kinds: dict[int, str] = {}
        self._column_lists: dict[int, QListWidget] = {}
        self.board_columns: dict[int, QListWidget] = self._column_lists
        self._column_count_labels: dict[int, QLabel] = {}
        self._column_title_labels: dict[int, QLabel] = {}
        self._selected_card_key: tuple[str, int] | None = None
        self._focused_card: ConceptBoardCard | None = None
        self._attached_card_keys: set[tuple[str, int]] = set()
        self.search_input.setPlaceholderText("Поиск по концептборду...")
        self._build_shell()
        self.refresh()

    def _build_shell(self) -> None:
        root = QWidget(self)
        root.setObjectName("ConceptBoardRoot")
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(16)

        top_splitter = QSplitter(Qt.Orientation.Horizontal, root)
        top_splitter.setObjectName("ConceptBoardSplitter")
        top_splitter.addWidget(self._build_concept_boards_panel(top_splitter))
        top_splitter.addWidget(self._build_board_panel(top_splitter))
        top_splitter.addWidget(self._build_focus_panel(top_splitter))
        top_splitter.setStretchFactor(0, 1)
        top_splitter.setStretchFactor(1, 4)
        top_splitter.setStretchFactor(2, 2)
        root_layout.addWidget(top_splitter, 1)

        self.set_content(root)
        self._apply_concept_board_style()

    def _build_concept_boards_panel(self, parent: QWidget) -> QFrame:
        panel = QFrame(parent)
        panel.setObjectName("ConceptBoardListPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("Концептборды")
        title.setObjectName("ConceptBoardListTitle")
        subtitle = QLabel("Смысловые доски поиска решения. Выберите активный концептборд или создайте новый.")
        subtitle.setObjectName("ConceptBoardListSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        self.concept_board_list = QListWidget(panel)
        self.concept_board_list.setObjectName("ConceptBoardList")
        self.concept_board_list.itemSelectionChanged.connect(self._on_concept_board_selection_changed)
        layout.addWidget(self.concept_board_list, 1)

        self.add_concept_board_button = QPushButton("+ Новый концептборд", panel)
        self.add_concept_board_button.setObjectName("ConceptBoardPrimaryButton")
        self.add_concept_board_button.clicked.connect(self._create_concept_board)
        layout.addWidget(self.add_concept_board_button)

        footer = QLabel("Архив\nШаблоны\nНастройки концептбордов", panel)
        footer.setObjectName("ConceptBoardListSubtitle")
        footer.setWordWrap(True)
        layout.addWidget(footer)
        return panel

    def _build_board_panel(self, parent: QWidget) -> QFrame:
        panel = QFrame(parent)
        panel.setObjectName("ConceptBoardBoardWrap")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        overview = QFrame(panel)
        overview.setObjectName("ConceptBoardBoardHeader")
        overview_layout = QHBoxLayout(overview)
        overview_layout.setContentsMargins(16, 16, 16, 16)
        overview_layout.setSpacing(12)

        overview_text = QVBoxLayout()
        overview_text.setContentsMargins(0, 0, 0, 0)
        overview_text.setSpacing(4)
        self.board_title_label = QLabel("Концептборд")
        self.board_title_label.setObjectName("ConceptBoardBoardHeadline")
        overview_caption = QLabel("Смысловая доска поиска решения")
        overview_caption.setObjectName("ConceptBoardBoardCaption")
        self.board_status_badge = QLabel("Исследование")
        self.board_status_badge.setObjectName("ConceptBoardColumnCount")
        overview_text.addWidget(self.board_title_label)
        overview_text.addWidget(overview_caption)
        overview_layout.addLayout(overview_text, 1)
        overview_layout.addWidget(self.board_status_badge, 0, Qt.AlignmentFlag.AlignTop)

        actions_row = QHBoxLayout()
        actions_row.setContentsMargins(0, 0, 0, 0)
        actions_row.setSpacing(8)
        self.quick_add_idea_button = QPushButton("Идея", overview)
        self.quick_add_version_button = QPushButton("Версия", overview)
        self.quick_add_task_button = QPushButton("Задача", overview)
        for button in (
            self.quick_add_idea_button,
            self.quick_add_version_button,
            self.quick_add_task_button,
        ):
            button.setObjectName("ConceptBoardSecondaryButton")
            actions_row.addWidget(button)
        self.quick_add_idea_button.clicked.connect(self._on_quick_add_idea)
        self.quick_add_version_button.clicked.connect(self._on_quick_add_version)
        self.quick_add_task_button.clicked.connect(self._on_quick_add_task)
        self.quick_add_idea_button.setToolTip("Добавить черновик идеи в цель и описание доски.")
        self.quick_add_version_button.setToolTip("Добавить пункт проверки версии в итог.")
        self.quick_add_task_button.setToolTip("Добавить следующую задачу в итог.")
        overview_layout.addLayout(actions_row)
        layout.addWidget(overview)

        goal_card = QFrame(panel)
        goal_card.setObjectName("ConceptBoardScenarioCard")
        goal_layout = QVBoxLayout(goal_card)
        goal_layout.setContentsMargins(16, 16, 16, 16)
        goal_layout.setSpacing(8)
        goal_title = QLabel("Цель доски")
        goal_title.setObjectName("ConceptBoardInsightTitle")
        self.goal_body_label = QLabel("Цель не задана")
        self.goal_body_label.setObjectName("ConceptBoardBoardCaption")
        self.goal_body_label.setWordWrap(True)
        self.goal_hint_label = QLabel("Добавьте цель, чтобы концептборд не превратился в склад материалов.")
        self.goal_hint_label.setObjectName("ConceptBoardListSubtitle")
        self.goal_hint_label.setWordWrap(True)
        self.goal_edit_button = QPushButton("Редактировать цель", goal_card)
        self.goal_edit_button.setObjectName("ConceptBoardSecondaryButton")
        self.goal_edit_button.clicked.connect(self._edit_goal)
        goal_layout.addWidget(goal_title)
        goal_layout.addWidget(self.goal_body_label)
        goal_layout.addWidget(self.goal_hint_label)
        goal_layout.addWidget(self.goal_edit_button, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(goal_card)

        self.board_tabs = QTabWidget(panel)
        self.board_tabs.setObjectName("ConceptBoardTabs")
        layout.addWidget(self.board_tabs, 1)

        flows_page = QWidget(panel)
        flows_layout = QVBoxLayout(flows_page)
        flows_layout.setContentsMargins(0, 0, 0, 0)
        flows_layout.setSpacing(14)

        header = QFrame(flows_page)
        header.setObjectName("ConceptBoardBoardHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 16, 16, 16)
        header_layout.setSpacing(12)

        header_text = QVBoxLayout()
        header_text.setContentsMargins(0, 0, 0, 0)
        header_text.setSpacing(4)
        title = QLabel("Потоки решения")
        title.setObjectName("ConceptBoardBoardHeadline")
        caption = QLabel(
            "Разложите материалы, идеи, версии и задачи по колонкам, чтобы пройти путь от входящих сигналов к решению."
        )
        caption.setObjectName("ConceptBoardBoardCaption")
        caption.setWordWrap(True)
        header_text.addWidget(title)
        header_text.addWidget(caption)
        header_layout.addLayout(header_text, 1)

        self.add_column_button = QPushButton("+ Добавить", header)
        self.add_column_button.setObjectName("ConceptBoardSecondaryButton")
        self.add_column_button.clicked.connect(self._add_column)
        header_layout.addWidget(self.add_column_button, 0, Qt.AlignmentFlag.AlignTop)
        flows_layout.addWidget(header)

        self.board_scroll = QScrollArea(flows_page)
        self.board_scroll.setObjectName("ConceptBoardScroll")
        self.board_scroll.setWidgetResizable(True)
        self.board_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.board_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.board_inner = QWidget()
        self.board_inner.setObjectName("ConceptBoardColumnsHost")
        self.board_inner_layout = QVBoxLayout(self.board_inner)
        self.board_inner_layout.setContentsMargins(0, 0, 0, 0)
        self.board_inner_layout.setSpacing(0)
        self.columns_splitter = QSplitter(Qt.Orientation.Horizontal, self.board_inner)
        self.columns_splitter.setObjectName("ConceptBoardColumnsSplitter")
        self.columns_splitter.setChildrenCollapsible(False)
        self.columns_splitter.setHandleWidth(8)
        self.board_inner_layout.addWidget(self.columns_splitter)

        self.board_scroll.setWidget(self.board_inner)
        flows_layout.addWidget(self.board_scroll, 1)

        self.board_tabs.addTab(flows_page, "Потоки")
        self.structure_panel = self._build_structure_panel(self.board_tabs)
        self.scenarios_panel = self._build_scenarios_panel(self.board_tabs)
        self.board_tabs.addTab(self.structure_panel, "Карта связей")
        self.board_tabs.addTab(self.scenarios_panel, "Итог")

        summary = QFrame(panel)
        summary.setObjectName("ConceptBoardScenarioCard")
        summary_layout = QVBoxLayout(summary)
        summary_layout.setContentsMargins(16, 16, 16, 16)
        summary_layout.setSpacing(8)
        summary_title = QLabel("Итог и следующие шаги")
        summary_title.setObjectName("ConceptBoardInsightTitle")
        self.summary_solution_label = QLabel("Текущее решение ещё не зафиксировано.")
        self.summary_solution_label.setObjectName("ConceptBoardBoardCaption")
        self.summary_solution_label.setWordWrap(True)
        self.summary_checks_label = QLabel("Что проверить появится после заполнения вкладки «Итог».")
        self.summary_checks_label.setObjectName("ConceptBoardListSubtitle")
        self.summary_checks_label.setWordWrap(True)
        self.summary_tasks_label = QLabel("Следующие задачи пока не заданы.")
        self.summary_tasks_label.setObjectName("ConceptBoardListSubtitle")
        self.summary_tasks_label.setWordWrap(True)
        open_summary_button = QPushButton("Открыть итог", summary)
        open_summary_button.setObjectName("ConceptBoardSecondaryButton")
        open_summary_button.clicked.connect(lambda: self.board_tabs.setCurrentWidget(self.scenarios_panel))
        self.accept_solution_button = QPushButton("Принять решение", summary)
        self.accept_solution_button.setObjectName("ConceptBoardSecondaryButton")
        self.accept_solution_button.clicked.connect(self._accept_current_solution)
        self.review_solution_button = QPushButton("Отправить на проверку", summary)
        self.review_solution_button.setObjectName("ConceptBoardSecondaryButton")
        self.review_solution_button.clicked.connect(self._send_current_solution_to_review)
        self.create_tasks_button = QPushButton("Создать задачи из решения", summary)
        self.create_tasks_button.setObjectName("ConceptBoardSecondaryButton")
        self.create_tasks_button.clicked.connect(self._create_tasks_from_solution)
        summary_actions = QHBoxLayout()
        summary_actions.setContentsMargins(0, 0, 0, 0)
        summary_actions.setSpacing(8)
        summary_actions.addWidget(open_summary_button)
        summary_actions.addWidget(self.accept_solution_button)
        summary_actions.addWidget(self.review_solution_button)
        summary_actions.addWidget(self.create_tasks_button)
        summary_layout.addWidget(summary_title)
        summary_layout.addWidget(self.summary_solution_label)
        summary_layout.addWidget(self.summary_checks_label)
        summary_layout.addWidget(self.summary_tasks_label)
        summary_layout.addLayout(summary_actions)
        layout.addWidget(summary)
        return panel

    def _build_focus_panel(self, parent: QWidget) -> QFrame:
        panel = QFrame(parent)
        panel.setObjectName("ConceptBoardFocusPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        self.focus_heading_label = QLabel("Фокус: Концептборд")
        self.focus_heading_label.setObjectName("ConceptBoardInspectorTitle")
        self.focus_caption_label = QLabel("Сводка по активной доске и выбранному элементу.")
        self.focus_caption_label.setObjectName("ConceptBoardBoardCaption")
        self.focus_caption_label.setWordWrap(True)
        layout.addWidget(self.focus_heading_label)
        layout.addWidget(self.focus_caption_label)

        form_host = QWidget(panel)
        form = QFormLayout(form_host)
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(8)

        self.focus_title_input = QLineEdit(form_host)
        self.focus_title_input.setObjectName("ConceptBoardFocusTitle")
        self.focus_title_input.textChanged.connect(self._sync_board_header_preview)
        self.focus_status_value = QLabel("Исследование")
        self.focus_updated_value = QLabel("—")
        self.focus_attached_value = QLabel("0")
        self.focus_description_input = QTextEdit(form_host)
        self.focus_description_input.setObjectName("ConceptBoardFocusDescription")
        self.focus_description_input.setMinimumHeight(160)
        self.focus_description_input.setPlaceholderText("Цель, контекст и описание концептборда...")

        form.addRow("Название", self.focus_title_input)
        form.addRow("Статус", self.focus_status_value)
        form.addRow("Обновлён", self.focus_updated_value)
        form.addRow("Связанных элементов", self.focus_attached_value)
        form.addRow("Цель и описание", self.focus_description_input)
        layout.addWidget(form_host, 1)

        self.focus_card_panel = QFrame(panel)
        self.focus_card_panel.setObjectName("ConceptBoardScenarioCard")
        card_layout = QVBoxLayout(self.focus_card_panel)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(8)
        self.focus_card_kind_label = QLabel("Элемент")
        self.focus_card_kind_label.setObjectName("ConceptBoardScenarioTitle")
        self.focus_card_title_label = QLabel("Выберите элемент")
        self.focus_card_title_label.setObjectName("ConceptBoardInsightTitle")
        self.focus_card_meta_label = QLabel("Связи и метаданные появятся здесь.")
        self.focus_card_meta_label.setObjectName("ConceptBoardBoardCaption")
        self.focus_card_meta_label.setWordWrap(True)
        self.focus_card_links_label = QLabel("Связей: 0")
        self.focus_card_links_label.setObjectName("ConceptBoardListSubtitle")
        self.focus_card_details = QTextEdit(self.focus_card_panel)
        self.focus_card_details.setObjectName("ConceptBoardScenarioEditor")
        self.focus_card_details.setReadOnly(True)
        self.focus_card_details.setMinimumHeight(180)
        self.focus_card_primary_button = QPushButton("Связать", self.focus_card_panel)
        self.focus_card_secondary_button = QPushButton("Создать задачу", self.focus_card_panel)
        self.focus_card_tertiary_button = QPushButton("Открыть итог", self.focus_card_panel)
        self.focus_card_primary_button.clicked.connect(self._on_focus_primary_action)
        self.focus_card_secondary_button.clicked.connect(self._on_focus_secondary_action)
        self.focus_card_tertiary_button.clicked.connect(self._on_focus_tertiary_action)
        card_actions = QHBoxLayout()
        card_actions.setContentsMargins(0, 0, 0, 0)
        card_actions.setSpacing(8)
        for button in (
            self.focus_card_primary_button,
            self.focus_card_secondary_button,
            self.focus_card_tertiary_button,
        ):
            button.setObjectName("ConceptBoardSecondaryButton")
            button.setEnabled(False)
            button.setToolTip(_DISABLED_ACTION_TOOLTIP)
            card_actions.addWidget(button)
        card_layout.addWidget(self.focus_card_kind_label)
        card_layout.addWidget(self.focus_card_title_label)
        card_layout.addWidget(self.focus_card_meta_label)
        card_layout.addWidget(self.focus_card_links_label)
        card_layout.addWidget(self.focus_card_details, 1)
        card_layout.addLayout(card_actions)
        layout.addWidget(self.focus_card_panel, 1)
        self.focus_card_panel.hide()

        self.focus_save_button = QPushButton("Сохранить концептборд", panel)
        self.focus_save_button.setObjectName("ConceptBoardPrimaryButton")
        self.focus_save_button.clicked.connect(self._save_current_concept_board)
        layout.addWidget(self.focus_save_button)
        return panel

    def _build_structure_panel(self, parent: QWidget) -> QFrame:
        panel = QFrame(parent)
        panel.setObjectName("ConceptBoardInsightPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("Карта связей")
        title.setObjectName("ConceptBoardInsightTitle")
        self.structure_subtitle = QLabel("Показывает, как материалы, идеи и задачи сходятся к активному фокусу.")
        self.structure_subtitle.setObjectName("ConceptBoardInsightBody")
        self.structure_subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(self.structure_subtitle)

        graph = QFrame(panel)
        graph.setObjectName("ConceptBoardStructureGraph")
        graph_layout = QHBoxLayout(graph)
        graph_layout.setContentsMargins(8, 8, 8, 8)
        graph_layout.setSpacing(12)

        left_col = QVBoxLayout()
        left_col.setSpacing(10)
        center_col = QVBoxLayout()
        center_col.setSpacing(10)
        right_col = QVBoxLayout()
        right_col.setSpacing(10)

        self.structure_projects_label = self._create_structure_node("ConceptBoardNodeMuted", "Проекты · 0")
        self.structure_objects_label = self._create_structure_node("ConceptBoardNodeObject", "Объекты · 0")
        self.structure_ideas_label = self._create_structure_node("ConceptBoardNodeIdea", "Идеи · 0")
        self.structure_hub_label = self._create_structure_node("ConceptBoardNodeHub", "Концептборд")
        self.structure_links_label = self._create_structure_node("ConceptBoardNodeMuted", "Связи · 0")
        self.structure_tasks_label = self._create_structure_node("ConceptBoardNodeTask", "Задачи · 0")
        self.structure_other_label = self._create_structure_node("ConceptBoardNodeMuted", "Остальное · 0")

        left_col.addWidget(self.structure_projects_label)
        left_col.addWidget(self.structure_objects_label)
        left_col.addStretch(1)

        center_col.addWidget(self.structure_ideas_label, 0, Qt.AlignmentFlag.AlignHCenter)
        center_col.addWidget(self.structure_hub_label, 0, Qt.AlignmentFlag.AlignHCenter)
        center_col.addWidget(self.structure_links_label, 0, Qt.AlignmentFlag.AlignHCenter)

        right_col.addWidget(self.structure_tasks_label)
        right_col.addWidget(self.structure_other_label)
        right_col.addStretch(1)

        graph_layout.addLayout(left_col, 1)
        graph_layout.addLayout(center_col, 1)
        graph_layout.addLayout(right_col, 1)
        layout.addWidget(graph, 1)

        self.structure_details_label = QLabel("Выберите элемент или решение, чтобы увидеть смысловые связи и следующий шаг.")
        self.structure_details_label.setObjectName("ConceptBoardBoardCaption")
        self.structure_details_label.setWordWrap(True)
        layout.addWidget(self.structure_details_label)

        relations_title = QLabel("Путь к решению")
        relations_title.setObjectName("ConceptBoardScenarioTitle")
        layout.addWidget(relations_title)

        self.structure_relations_list = QListWidget(panel)
        self.structure_relations_list.setObjectName("ConceptBoardRelationList")
        self.structure_relations_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.structure_relations_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.structure_relations_list.setSpacing(4)
        self.structure_relations_list.setMinimumHeight(148)
        self.structure_relations_list.itemClicked.connect(self._on_structure_relation_clicked)
        layout.addWidget(self.structure_relations_list)
        return panel

    def _build_scenarios_panel(self, parent: QWidget) -> QFrame:
        panel = QFrame(parent)
        panel.setObjectName("ConceptBoardInsightPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("Итог и следующие шаги")
        title.setObjectName("ConceptBoardInsightTitle")
        subtitle = QLabel("Зафиксируйте текущее решение, проверки и следующие задачи, чтобы перейти от анализа к действию.")
        subtitle.setObjectName("ConceptBoardInsightBody")
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        cards_row = QHBoxLayout()
        cards_row.setSpacing(10)
        self._scenario_editors: dict[str, QTextEdit] = {}
        for key, label_text in (
            ("capture", "Текущее решение"),
            ("planning", "Что проверить"),
            ("links", "Следующие задачи"),
        ):
            card = QFrame(panel)
            card.setObjectName("ConceptBoardScenarioCard")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(12, 12, 12, 12)
            card_layout.setSpacing(8)
            card_title = QLabel(label_text)
            card_title.setObjectName("ConceptBoardScenarioTitle")
            editor = QTextEdit(card)
            editor.setObjectName("ConceptBoardScenarioEditor")
            editor.setMinimumHeight(128)
            editor.textChanged.connect(self._refresh_outcome_summary)
            self._scenario_editors[key] = editor
            card_layout.addWidget(card_title)
            card_layout.addWidget(editor, 1)
            cards_row.addWidget(card, 1)
        layout.addLayout(cards_row, 1)

        self.scenarios_save_button = QPushButton("Сохранить итог", panel)
        self.scenarios_save_button.setObjectName("ConceptBoardSecondaryButton")
        self.scenarios_save_button.clicked.connect(self._save_current_concept_board)
        layout.addWidget(self.scenarios_save_button, 0, Qt.AlignmentFlag.AlignRight)
        return panel

    def _create_structure_node(self, object_name: str, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName(object_name)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setMinimumHeight(42)
        return label

    def _edit_goal(self) -> None:
        self._clear_card_selection()
        self.focus_description_input.setFocus()

    def _clear_card_selection(self) -> None:
        for list_widget in self._column_lists.values():
            list_widget.blockSignals(True)
            list_widget.clearSelection()
            list_widget.setCurrentItem(None)
            list_widget.blockSignals(False)
        self._set_selected_card(None)

    def _sync_board_header_preview(self, text: str) -> None:
        title = text.strip() or "Без названия"
        self.board_title_label.setText(title)

    def _refresh_board_context(self, board: ConceptBoardData | None) -> None:
        title = board.title if board is not None and board.title.strip() else "Без названия"
        self.board_title_label.setText(title)
        status_text = self._board_status_text(board)
        self.board_status_badge.setText(status_text)
        self.focus_status_value.setText(status_text)
        goal_text = (board.description or "").strip() if board is not None else ""
        if goal_text:
            self.goal_body_label.setText(goal_text)
            self.goal_hint_label.setText("Цель можно уточнять по мере работы с материалами, версиями и задачами.")
        else:
            self.goal_body_label.setText("Цель не задана")
            self.goal_hint_label.setText("Добавьте цель, чтобы концептборд не превратился в склад материалов.")

    @staticmethod
    def _board_status_text(board: ConceptBoardData | None) -> str:
        if board is None:
            return "Черновик"
        return ConceptBoardWorkspace._board_status_text_from_values(
            board.description,
            board.capture_text,
            board.planning_text,
            board.links_text,
        )

    @staticmethod
    def _board_status_text_from_values(description: str, capture_text: str, planning_text: str, links_text: str) -> str:
        if (capture_text or "").strip():
            return "Решение принято" if (links_text or "").strip() else "На проверке"
        if (planning_text or "").strip():
            return "Проверка версии"
        if (description or "").strip():
            return "Исследование"
        return "Черновик"

    def _refresh_outcome_summary(self) -> None:
        capture_text = self._scenario_editors["capture"].toPlainText().strip()
        if capture_text:
            solution = self._persist_solution_from_current_state(status="review")
        if capture_text:
            solution = self._persist_solution_from_current_state(status="accepted")
        planning_text = self._scenario_editors["planning"].toPlainText().strip()
        links_text = self._scenario_editors["links"].toPlainText().strip()
        self.summary_solution_label.setText(capture_text or "Текущее решение ещё не зафиксировано.")
        self.summary_checks_label.setText(planning_text or "Что проверить появится после заполнения вкладки «Итог».")
        self.summary_tasks_label.setText(links_text or "Следующие задачи пока не заданы.")
        board = self._current_concept_board()
        description = board.description if board is not None else ""
        status_text = self._board_status_text_from_values(description, capture_text, planning_text, links_text)
        self.board_status_badge.setText(status_text)
        self.focus_status_value.setText(status_text)

    def _refresh_focus(self, card: ConceptBoardCard | None) -> None:
        board = self._current_concept_board()
        self._focused_card = card
        if card is None:
            self.focus_heading_label.setText("Фокус: Концептборд")
            self.focus_caption_label.setText(self._board_focus_caption(board))
            self.focus_card_panel.hide()
            self.focus_save_button.show()
            self.focus_title_input.parentWidget().show()
            return

        self.focus_heading_label.setText(f"Фокус: {_CARD_KIND_TITLES.get(card.entity_kind, 'Элемент')}")
        self.focus_caption_label.setText("Карточка показывает, как выбранный элемент участвует в поиске решения.")
        self.focus_title_input.parentWidget().hide()
        self.focus_save_button.hide()
        self.focus_card_panel.show()
        self.focus_card_kind_label.setText(_CARD_KIND_TITLES.get(card.entity_kind, "Элемент"))
        self.focus_card_title_label.setText(card.title)
        meta_parts = [part for part in (card.meta_text, card.subtitle) if part]
        self.focus_card_meta_label.setText(" · ".join(meta_parts) or "Метаданные недоступны.")
        self.focus_card_links_label.setText(f"Связей: {card.total_linked_count}")
        self.focus_card_details.setPlainText(self._focus_details_text(card, board))
        self._configure_focus_actions(card)

    def _board_focus_caption(self, board: ConceptBoardData | None) -> str:
        if board is None:
            return "Редактируйте цель, описание и общий контекст активной доски."
        attached_count = len(self._attached_card_keys)
        updated_text = board.updated_at.strftime("%d.%m.%Y %H:%M")
        goal_text = (board.description or "").strip() or "цель не задана"
        return (
            f"Статус: {self._board_status_text(board)} · "
            f"Связанных элементов: {attached_count} · "
            f"Обновлено: {updated_text}\n"
            f"Цель: {goal_text}"
        )

    def _focus_details_text(self, card: ConceptBoardCard, board: ConceptBoardData | None) -> str:
        payload = card.source_payload
        if isinstance(payload, dict):
            return self._synthetic_focus_details(card, payload, board)
        if isinstance(payload, ConceptBoardVersionData):
            return self._version_focus_details(payload, board)
        if isinstance(payload, ConceptBoardSolutionData):
            return self._solution_focus_details(payload, board)
        if isinstance(payload, TaskData):
            return self._task_focus_details(payload, card, board)
        if isinstance(payload, IdeaData):
            return self._idea_focus_details(payload, card, board)
        if isinstance(payload, CloudFileData):
            return self._image_focus_details(payload, card, board)
        if isinstance(payload, ProjectData):
            return self._project_focus_details(payload, card, board)
        if isinstance(payload, MapMarkerData):
            return self._marker_focus_details(payload, card, board)
        if isinstance(payload, ObjectData):
            return self._object_focus_details(payload, card, board)
        if isinstance(payload, NoteData):
            return self._note_focus_details(payload, card, board)
        if isinstance(payload, MapData):
            return self._map_focus_details(payload, card, board)
        lines = [card.title]
        if card.subtitle:
            lines.append("")
            lines.append(card.subtitle)
        if card.project_title:
            lines.append("")
            lines.append(f"Проект: {card.project_title}")
        if card.meta_text:
            lines.append(f"Контекст: {card.meta_text}")
        lines.append(f"Связей: {card.total_linked_count}")
        if board is not None:
            lines.append(f"Концептборд: {board.title}")
        return "\n".join(lines).strip()

    def _synthetic_focus_details(
        self,
        card: ConceptBoardCard,
        payload: dict[str, object],
        board: ConceptBoardData | None,
    ) -> str:
        lines = [card.title]
        if card.subtitle:
            lines.extend(("", card.subtitle))
        status = str(payload.get("status") or "").strip()
        if status:
            lines.append(f"Статус: {status}")
        why_yes = str(payload.get("why_yes") or "").strip()
        if why_yes:
            lines.extend(("", f"Почему да: {why_yes}"))
        why_not = str(payload.get("why_not") or "").strip()
        if why_not:
            lines.append(f"Почему нет: {why_not}")
        checks = payload.get("checks") or []
        if isinstance(checks, list) and checks:
            lines.extend(("", "Что проверить:"))
            lines.extend(f"• {item}" for item in checks)
        next_steps = payload.get("next_steps") or []
        if isinstance(next_steps, list) and next_steps:
            lines.extend(("", "Следующие задачи:"))
            lines.extend(f"• {item}" for item in next_steps)
        if board is not None:
            lines.extend(("", f"Концептборд: {board.title}"))
        return "\n".join(line for line in lines if line is not None).strip()

    def _version_focus_details(self, version: ConceptBoardVersionData, board: ConceptBoardData | None) -> str:
        lines = [version.title]
        if version.description:
            lines.extend(("", version.description))
        lines.append(f"Статус: {self._concept_status_title(version.status)}")
        if version.why_yes:
            lines.extend(("", f"Почему да: {version.why_yes}"))
        if version.why_no:
            lines.append(f"Почему нет: {version.why_no}")
        checks = self._split_board_lines(version.checks_text)
        if checks:
            lines.extend(("", "Что проверить:"))
            lines.extend(f"• {item}" for item in checks)
        if board is not None:
            lines.extend(("", f"Концептборд: {board.title}"))
        return "\n".join(lines)

    def _solution_focus_details(self, solution: ConceptBoardSolutionData, board: ConceptBoardData | None) -> str:
        lines = [solution.title]
        if solution.summary:
            lines.extend(("", solution.summary))
        lines.append(f"Статус: {self._concept_status_title(solution.status)}")
        if solution.why_selected:
            lines.extend(("", f"Почему выбрано: {solution.why_selected}"))
        if solution.rejected_text:
            lines.append(f"Что отвергнуто: {solution.rejected_text}")
        next_steps = self._split_board_lines(solution.next_steps_text)
        if next_steps:
            lines.extend(("", "Следующие задачи:"))
            lines.extend(f"• {item}" for item in next_steps)
        if solution.decided_at:
            lines.append(f"Дата принятия: {solution.decided_at}")
        if board is not None:
            lines.extend(("", f"Концептборд: {board.title}"))
        return "\n".join(lines)

    def _task_focus_details(self, task: TaskData, card: ConceptBoardCard, board: ConceptBoardData | None) -> str:
        lines = [
            task.title,
            "",
            f"Статус: {'Готово' if task.done else 'В работе'}",
            f"Приоритет: {task.priority or 'Не задан'}",
            f"Дата: {task.day.isoformat()}",
        ]
        if task.project_title:
            lines.append(f"Проект: {task.project_title}")
        if task.description:
            lines.extend(("", task.description))
        lines.append("")
        lines.append(f"Связанные идеи: {card.linked_idea_count}")
        lines.append(f"Связанные объекты: {card.linked_object_count}")
        if board is not None:
            lines.append(f"Концептборд: {board.title}")
        return "\n".join(lines)

    def _idea_focus_details(self, idea: IdeaData, card: ConceptBoardCard, board: ConceptBoardData | None) -> str:
        lines = [
            idea.title,
            "",
            f"Статус: {idea.status or 'Не задан'}",
            f"Тип: {idea.type or 'Не задан'}",
            f"Ценность / усилие: {idea.value_score} / {idea.effort_score}",
        ]
        if idea.project_title:
            lines.append(f"Проект: {idea.project_title}")
        excerpt = idea.summary or idea.body_md or idea.source
        if excerpt:
            lines.extend(("", excerpt))
        lines.append("")
        lines.append(f"Связанные задачи: {card.linked_task_count}")
        lines.append(f"Связанные объекты: {card.linked_object_count}")
        if board is not None:
            lines.append(f"Концептборд: {board.title}")
        return "\n".join(lines)

    def _image_focus_details(self, cloud_file: CloudFileData, card: ConceptBoardCard, board: ConceptBoardData | None) -> str:
        lines = [
            cloud_file.name or cloud_file.rel_path,
            "",
            f"Источник: {cloud_file.rel_path}",
            f"Размер: {cloud_file.size} B" if cloud_file.size else "Размер: не указан",
            f"Связей: {card.total_linked_count}",
        ]
        if cloud_file.description:
            lines.extend(("", cloud_file.description))
        if board is not None:
            lines.extend(("", f"Концептборд: {board.title}"))
        return "\n".join(lines)

    def _project_focus_details(self, project: ProjectData, card: ConceptBoardCard, board: ConceptBoardData | None) -> str:
        lines = [
            project.title,
            "",
            f"Область: {project.area or 'Не задана'}",
            f"Приоритет: {project.priority or 'Не задан'}",
            f"Связей: {card.total_linked_count}",
        ]
        if board is not None:
            lines.append(f"Концептборд: {board.title}")
        return "\n".join(lines)

    def _marker_focus_details(self, marker: MapMarkerData, card: ConceptBoardCard, board: ConceptBoardData | None) -> str:
        lines = [
            marker.name,
            "",
            f"Тип метки: {marker.type or 'Не задан'}",
            f"Размер: {marker.size}",
            f"Задачи: {len(marker.task_ids)}",
            f"Проекты: {len(marker.project_ids)}",
            f"Объекты: {len(marker.object_ids)}",
        ]
        if marker.description:
            lines.extend(("", marker.description))
        if board is not None:
            lines.append(f"Концептборд: {board.title}")
        return "\n".join(lines)

    def _object_focus_details(self, obj: ObjectData, card: ConceptBoardCard, board: ConceptBoardData | None) -> str:
        lines = [
            obj.title,
            "",
            f"Каталог: {obj.catalog or 'Не задан'}",
            f"Тип объекта: {obj.object_type or 'Не задан'}",
            f"Статус: {obj.status or 'Не задан'}",
            f"Связей: {card.total_linked_count}",
        ]
        if obj.description:
            lines.extend(("", obj.description))
        if board is not None:
            lines.append(f"Концептборд: {board.title}")
        return "\n".join(lines)

    def _note_focus_details(self, note: NoteData, card: ConceptBoardCard, board: ConceptBoardData | None) -> str:
        lines = [note.title]
        if note.project:
            lines.extend(("", f"Проект: {note.project}"))
        if note.preview:
            lines.extend(("", note.preview))
        if note.tags:
            lines.extend(("", f"Теги: {', '.join(note.tags)}"))
        lines.append(f"Связей: {card.total_linked_count}")
        if board is not None:
            lines.append(f"Концептборд: {board.title}")
        return "\n".join(lines)

    def _map_focus_details(self, map_item: MapData, card: ConceptBoardCard, board: ConceptBoardData | None) -> str:
        lines = [
            map_item.title,
            "",
            f"Проект: {map_item.project or 'Не задан'}",
            f"Метки: {card.total_linked_count}",
        ]
        if map_item.description:
            lines.extend(("", map_item.description))
        if board is not None:
            lines.append(f"Концептборд: {board.title}")
        return "\n".join(lines)

    def _configure_focus_actions(self, card: ConceptBoardCard) -> None:
        action_map = {
            "idea": ("Сделать версией", "Создать задачу", "Связать"),
            "task": ("Открыть задачу", "Редактировать", "Связать"),
            "image": ("Открыть", "Сделать материалом версии", "Связать"),
            "version": ("Принять как решение", "Создать задачу", "Связать"),
            "solution": ("Открыть итог", "Создать задачу", "Связать"),
        }
        labels = action_map.get(card.entity_kind, ("Связать", "Создать задачу", "Открыть итог"))
        for button, text in zip(
            (
                self.focus_card_primary_button,
                self.focus_card_secondary_button,
                self.focus_card_tertiary_button,
            ),
            labels,
        ):
            button.setText(text)
            button.setEnabled(False)
            button.setToolTip(_DISABLED_ACTION_TOOLTIP)
        self.focus_card_secondary_button.setEnabled(True)
        self.focus_card_secondary_button.setToolTip("Добавить этот элемент в список следующих задач.")
        self.focus_card_tertiary_button.setEnabled(True)
        self.focus_card_tertiary_button.setToolTip("Открыть вкладку «Итог» для фиксации решения.")
        if card.entity_kind in {"idea", "version", "solution"}:
            self.focus_card_primary_button.setEnabled(True)
            self.focus_card_primary_button.setToolTip("Перенести текущую версию в итоговое решение.")

    @staticmethod
    def _split_board_lines(text: str) -> list[str]:
        result: list[str] = []
        for raw_line in str(text or "").splitlines():
            line = raw_line.strip().lstrip("-• ").strip()
            if line:
                result.append(line)
        return result

    @staticmethod
    def _concept_status_title(status: str) -> str:
        normalized = (status or "").strip().lower()
        if not normalized:
            return _CONCEPT_STATUS_TITLES["draft"]
        return _CONCEPT_STATUS_TITLES.get(normalized, normalized.replace("_", " ").title())

    @staticmethod
    def _append_unique_line(text: str, line: str) -> str:
        normalized_line = line.strip()
        if not normalized_line:
            return text
        lines = [item.strip() for item in str(text or "").splitlines()]
        if normalized_line in lines:
            return text
        lines = [item for item in lines if item]
        lines.append(normalized_line)
        return "\n".join(lines)

    def _set_editor_text_and_focus(self, editor_key: str, line: str) -> None:
        editor = self._scenario_editors[editor_key]
        updated = self._append_unique_line(editor.toPlainText(), line)
        editor.setPlainText(updated)
        editor.setFocus()

    def _on_quick_add_idea(self) -> None:
        self._clear_card_selection()
        updated = self._append_unique_line(self.focus_description_input.toPlainText(), "Идея:")
        self.focus_description_input.setPlainText(updated)
        self.focus_description_input.setFocus()
        self.set_status("Концептборд: добавлен черновик идеи.")

    def _on_quick_add_version(self) -> None:
        board = self._current_concept_board()
        if board is not None:
            checks_text = self._scenario_editors["planning"].toPlainText().strip()
            default_title = self._split_board_lines(checks_text)
            version = self._db.create_concept_board_version(
                board.id,
                title=default_title[0] if default_title else f"Р’РµСЂСЃРёСЏ {len(self._db.fetch_concept_board_versions(board.id)) + 1}",
                description=self.focus_description_input.toPlainText().strip(),
                why_yes=self.focus_description_input.toPlainText().strip(),
                checks_text=checks_text,
                status="draft",
            )
            self._selected_card_key = ("version", version.id)
            self.board_tabs.setCurrentWidget(self.scenarios_panel)
            self._set_editor_text_and_focus("planning", "РџСЂРѕРІРµСЂРёС‚СЊ РІРµСЂСЃРёСЋ:")
            self._set_editor_text_and_focus("planning", "\u041f\u0440\u043e\u0432\u0435\u0440\u0438\u0442\u044c \u0432\u0435\u0440\u0441\u0438\u044e:")
            self._populate_board()
            self._refresh_outcome_summary()
            self.set_status(f"РљРѕРЅС†РµРїС‚Р±РѕСЂРґ: РґРѕР±Р°РІР»РµРЅР° РІРµСЂСЃРёСЏ В«{version.title}В».")
            return
        self.board_tabs.setCurrentWidget(self.scenarios_panel)
        self._set_editor_text_and_focus("planning", "Проверить версию:")
        self._refresh_outcome_summary()
        self.set_status("Концептборд: добавлен черновик версии.")

    def _on_quick_add_task(self) -> None:
        self.board_tabs.setCurrentWidget(self.scenarios_panel)
        self._set_editor_text_and_focus("links", "Следующая задача:")
        self._refresh_outcome_summary()
        self.set_status("Концептборд: добавлена следующая задача.")

    @staticmethod
    def _default_column_specs() -> list[tuple[str, str]]:
        return list(_DEFAULT_COLUMN_SPECS)

    def _ensure_default_columns(self, board_id: int) -> list[ConceptBoardColumnData]:
        return self._db.replace_concept_board_columns(board_id, self._default_column_specs())

    @staticmethod
    def _display_column_title(column: ConceptBoardColumnData) -> str:
        title = str(column.title or "").strip()
        if title:
            return title
        return _COLUMN_KIND_LABELS.get(column.kind, column.kind)

    def _board_list_item_text(self, board: ConceptBoardData, attached_count: int) -> str:
        updated_text = board.updated_at.strftime("%d.%m.%Y")
        return (
            f"{board.title}\n"
            f"{self._board_status_text(board)} · {attached_count} элементов · {updated_text}"
        )

    def _synthetic_cards_for_kind(self, board: ConceptBoardData | None, kind: str) -> list[ConceptBoardCard]:
        if board is None:
            return []
        if kind == "version":
            version_cards = [self._build_version_card(item, board) for item in self._db.fetch_concept_board_versions(board.id)]
            if version_cards:
                return version_cards
        if kind == "solution":
            solution_cards = [self._build_solution_card(item, board) for item in self._db.fetch_concept_board_solutions(board.id)]
            if solution_cards:
                return solution_cards
        check_lines = self._split_board_lines(board.planning_text)
        next_steps = self._split_board_lines(board.links_text)
        if kind == "version":
            version_summary = (board.description or "").strip() or (check_lines[0] if check_lines else "")
            if not version_summary:
                return []
            return [
                ConceptBoardCard(
                    entity_kind="version",
                    entity_id=-(board.id * 10 + 1),
                    title=f"Версия: {board.title}",
                    subtitle=version_summary,
                    project_id=None,
                    project_title=board.title,
                    accent_color="#a88cff",
                    meta_text="Черновик · Проверяется",
                    relation_count=len(check_lines) + len(next_steps),
                    relation_summary=f"Проверки · {len(check_lines)}",
                    stage="draft",
                    is_actionable=True,
                    source_payload={
                        "concept_kind": "version",
                        "status": "Проверяется" if check_lines else "Черновик",
                        "why_yes": version_summary,
                        "checks": check_lines,
                        "next_steps": next_steps,
                    },
                )
            ]
        if kind == "solution":
            solution_text = (board.capture_text or "").strip()
            if not solution_text:
                return []
            solution_title = self._split_board_lines(solution_text)
            return [
                ConceptBoardCard(
                    entity_kind="solution",
                    entity_id=-(board.id * 10 + 2),
                    title=solution_title[0] if solution_title else f"Решение: {board.title}",
                    subtitle=solution_text,
                    project_id=None,
                    project_title=board.title,
                    accent_color="#49c36b",
                    meta_text="Черновик решения",
                    relation_count=len(next_steps),
                    relation_summary=f"Следующие задачи · {len(next_steps)}",
                    stage="draft",
                    is_actionable=True,
                    source_payload={
                        "concept_kind": "solution",
                        "status": "Черновик",
                        "why_yes": solution_text,
                        "checks": check_lines,
                        "next_steps": next_steps,
                    },
                )
            ]
        return []

    def _build_version_card(self, version: ConceptBoardVersionData, board: ConceptBoardData) -> ConceptBoardCard:
        checks = self._split_board_lines(version.checks_text)
        relation_count = len(self._db.fetch_concept_board_links(board.id, source_kind="version", source_id=version.id))
        relation_count += len(self._db.fetch_concept_board_links(board.id, target_kind="version", target_id=version.id))
        if relation_count <= 0:
            relation_count = len(checks)
        return ConceptBoardCard(
            entity_kind="version",
            entity_id=version.id,
            title=version.title,
            subtitle=(version.description or version.why_yes or "").strip(),
            project_id=None,
            project_title=board.title,
            accent_color="#a88cff",
            meta_text=f"{self._concept_status_title(version.status)} В· РџСЂРѕРІРµСЂРѕРє {len(checks)}",
            relation_count=relation_count,
            relation_summary=f"РЎРІСЏР·Рё В· {relation_count}",
            stage=(version.status or "draft").strip().lower(),
            is_actionable=(version.status or "draft").strip().lower() != "accepted",
            source_payload=version,
        )

    def _build_solution_card(self, solution: ConceptBoardSolutionData, board: ConceptBoardData) -> ConceptBoardCard:
        next_steps = self._split_board_lines(solution.next_steps_text)
        relation_count = len(self._db.fetch_concept_board_links(board.id, source_kind="solution", source_id=solution.id))
        relation_count += len(self._db.fetch_concept_board_links(board.id, target_kind="solution", target_id=solution.id))
        if relation_count <= 0:
            relation_count = len(next_steps)
        return ConceptBoardCard(
            entity_kind="solution",
            entity_id=solution.id,
            title=solution.title,
            subtitle=(solution.summary or solution.why_selected or "").strip(),
            project_id=None,
            project_title=board.title,
            accent_color="#49c36b",
            meta_text=f"{self._concept_status_title(solution.status)} В· РЎР»РµРґСѓСЋС‰РёС… Р·Р°РґР°С‡ {len(next_steps)}",
            relation_count=relation_count,
            relation_summary=f"РЎРІСЏР·Рё В· {relation_count}",
            stage=(solution.status or "draft").strip().lower(),
            is_actionable=(solution.status or "draft").strip().lower() != "accepted",
            source_payload=solution,
        )

    @staticmethod
    def _empty_state_text(kind: str) -> tuple[str, str]:
        return {
            "task": ("Нет связанных задач", "Превратите решение в конкретные действия."),
            "idea": ("Нет идей", "Добавьте идеи, чтобы собрать варианты решения."),
            "image": ("Нет материалов", "Добавьте изображения, файлы и карты как опорные материалы."),
            "version": ("Нет версий", "Сформулируйте рабочую версию направления через цель и фокус."),
            "solution": ("Нет решения", "Зафиксируйте текущее решение во вкладке «Итог»."),
            "project": ("Нет проектов", "Свяжите проект, чтобы у решения появился контекст."),
            "object": ("Нет объектов", "Добавьте объекты, чтобы приземлить идею на сущности."),
            "note": ("Нет заметок", "Заметки помогут собрать объяснение решения."),
            "map": ("Нет карт", "Добавьте карту, если решение опирается на пространство."),
            "marker": ("Нет меток", "Свяжите метки, если решение живёт на карте."),
            "file": ("Нет файлов", "Добавьте референсы и документы для проверки версии."),
            "link": ("Нет ссылок", "Свяжите внешний источник, если он влияет на решение."),
        }.get(kind, ("Нет элементов", "Добавьте материалы или измените тип колонки."))

    def _on_focus_primary_action(self) -> None:
        card = self._focused_card
        board = self._current_concept_board()
        if card is None or board is None:
            return
        if isinstance(card.source_payload, IdeaData):
            version = self._db.create_concept_board_version(
                board.id,
                title=card.title,
                description=card.subtitle,
                why_yes=card.subtitle or card.title,
                checks_text=self._scenario_editors["planning"].toPlainText().strip(),
                status="review",
            )
            self._db.add_concept_board_link(
                board.id,
                source_kind="idea",
                source_id=card.entity_id,
                target_kind="version",
                target_id=version.id,
                link_type="develops",
            )
            self._selected_card_key = ("version", version.id)
            self._populate_board()
            self.set_status(f"РљРѕРЅС†РµРїС‚Р±РѕСЂРґ: РёРґРµСЏ В«{card.title}В» РїРµСЂРµРІРµРґРµРЅР° РІ РІРµСЂСЃРёСЋ.")
            return
        if isinstance(card.source_payload, ConceptBoardVersionData):
            proposal = str(card.subtitle or card.title).strip()
            current_text = self._scenario_editors["capture"].toPlainText().strip()
            if proposal:
                if not current_text:
                    self._scenario_editors["capture"].setPlainText(proposal)
                else:
                    self._scenario_editors["capture"].setPlainText(self._append_unique_line(current_text, proposal))
            solution = self._persist_solution_from_current_state(status="accepted", selected_version_id=card.source_payload.id)
            self._db.add_concept_board_link(
                board.id,
                source_kind="version",
                source_id=card.source_payload.id,
                target_kind="solution",
                target_id=solution.id,
                link_type="transforms_to",
            )
            self._selected_card_key = ("solution", solution.id)
            self._populate_board()
            self.board_tabs.setCurrentWidget(self.scenarios_panel)
            self._refresh_outcome_summary()
            self.set_status(f"РљРѕРЅС†РµРїС‚Р±РѕСЂРґ: РІРµСЂСЃРёСЏ В«{card.title}В» РїСЂРёРЅСЏС‚Р° РєР°Рє СЂРµС€РµРЅРёРµ.")
            return
        if isinstance(card.source_payload, ConceptBoardSolutionData):
            self.board_tabs.setCurrentWidget(self.scenarios_panel)
            self._scenario_editors["capture"].setFocus()
            self.set_status(f"РљРѕРЅС†РµРїС‚Р±РѕСЂРґ: РѕС‚РєСЂС‹С‚ РёС‚РѕРі РґР»СЏ В«{card.title}В».")
            return
        if card.entity_kind not in {"version", "solution"}:
            return
        payload = card.source_payload if isinstance(card.source_payload, dict) else {}
        proposal = str(payload.get("why_yes") or card.subtitle or card.title).strip()
        current_text = self._scenario_editors["capture"].toPlainText().strip()
        if not current_text:
            self._scenario_editors["capture"].setPlainText(proposal)
        else:
            self._scenario_editors["capture"].setPlainText(self._append_unique_line(current_text, proposal))
        self.board_tabs.setCurrentWidget(self.scenarios_panel)
        self._refresh_outcome_summary()
        self.set_status(f"Концептборд: решение обновлено из «{card.title}».")

    def _on_focus_secondary_action(self) -> None:
        card = self._focused_card
        if card is None:
            return
        next_task = f"Проверить: {card.title}"
        updated_text = self._append_unique_line(self._scenario_editors["links"].toPlainText(), next_task)
        self._scenario_editors["links"].setPlainText(updated_text)
        self.board_tabs.setCurrentWidget(self.scenarios_panel)
        self._refresh_outcome_summary()
        self.set_status(f"Концептборд: задача добавлена из «{card.title}».")

    def _on_focus_tertiary_action(self) -> None:
        self.board_tabs.setCurrentWidget(self.scenarios_panel)
        self.set_status("Концептборд: открыт итог и следующие шаги.")

    def _accept_current_solution(self) -> None:
        solution: ConceptBoardSolutionData | None = None
        capture_text = self._scenario_editors["capture"].toPlainText().strip()
        if capture_text:
            solution = self._persist_solution_from_current_state(status="accepted")
        if not capture_text:
            self.set_status("Концептборд: сначала сформулируйте текущее решение.")
            return
        self._set_editor_text_and_focus("links", "Подготовить реализацию решения")
        self._refresh_outcome_summary()
        self.set_status("Концептборд: решение помечено как принятое.")

    def _send_current_solution_to_review(self) -> None:
        solution: ConceptBoardSolutionData | None = None
        capture_text = self._scenario_editors["capture"].toPlainText().strip()
        if capture_text:
            solution = self._persist_solution_from_current_state(status="review")
        if not capture_text:
            self.set_status("Концептборд: сначала сформулируйте решение для проверки.")
            return
        self._set_editor_text_and_focus("planning", "Проверить понятность решения")
        self._refresh_outcome_summary()
        self.set_status("Концептборд: решение отправлено на проверку.")

    def _create_tasks_from_solution(self) -> None:
        capture_text = self._scenario_editors["capture"].toPlainText().strip()
        if not capture_text:
            self.set_status("Концептборд: сначала зафиксируйте решение.")
            return
        lines = self._split_board_lines(capture_text)
        seed = lines[0] if lines else "решение"
        updated = self._scenario_editors["links"].toPlainText()
        updated = self._append_unique_line(updated, f"Подготовить реализацию: {seed}")
        updated = self._append_unique_line(updated, f"Проверить риски: {seed}")
        self._scenario_editors["links"].setPlainText(updated)
        self._scenario_editors["links"].setFocus()
        self._refresh_outcome_summary()
        self.set_status("Концептборд: следующие задачи собраны из решения.")

    def _persist_solution_from_current_state(
        self,
        *,
        status: str,
        selected_version_id: int | None = None,
    ) -> ConceptBoardSolutionData:
        board = self._current_concept_board()
        if board is None:
            raise RuntimeError("concept board is not selected")
        capture_text = self._scenario_editors["capture"].toPlainText().strip()
        planning_text = self._scenario_editors["planning"].toPlainText().strip()
        links_text = self._scenario_editors["links"].toPlainText().strip()
        title_lines = self._split_board_lines(capture_text)
        title = title_lines[0] if title_lines else board.title
        if selected_version_id is None and isinstance(getattr(self._focused_card, "source_payload", None), ConceptBoardVersionData):
            selected_version_id = self._focused_card.source_payload.id
        if selected_version_id is None:
            versions = self._db.fetch_concept_board_versions(board.id)
            selected_version_id = versions[0].id if versions else None
        existing = self._db.fetch_concept_board_solutions(board.id)
        decided_at = datetime.now(timezone.utc).date().isoformat() if status == "accepted" else ""
        if existing:
            current = existing[0]
            if not decided_at:
                decided_at = current.decided_at
            return self._db.update_concept_board_solution(
                current.id,
                title=title,
                summary=capture_text,
                why_selected=capture_text,
                rejected_text=planning_text,
                next_steps_text=links_text,
                status=status,
                selected_version_id=selected_version_id,
                decided_at=decided_at,
            )
        return self._db.create_concept_board_solution(
            board.id,
            title=title,
            summary=capture_text,
            why_selected=capture_text,
            rejected_text=planning_text,
            next_steps_text=links_text,
            status=status,
            selected_version_id=selected_version_id,
            decided_at=decided_at,
        )

    def set_theme_mode(self, theme_mode: str) -> None:
        super().set_theme_mode(theme_mode)
        self._base_workspace_stylesheet = self.styleSheet()
        self._apply_concept_board_style()

    def set_status(self, text: str) -> None:
        super().set_status(text)
        self._base_workspace_stylesheet = self.styleSheet()
        self._apply_concept_board_style()

    def set_error(self, text: str) -> None:
        super().set_error(text)
        self._base_workspace_stylesheet = self.styleSheet()
        self._apply_concept_board_style()

    def restore_state(self) -> None:
        super().restore_state()
        filters = self.get_filters()
        self._sync_filter_widgets(filters)

    def _sync_filter_widgets(self, filters: dict[str, object]) -> None:
        self.link_scope_filter.blockSignals(True)
        self.action_scope_filter.blockSignals(True)
        try:
            self.link_scope_filter.setCurrentIndex(
                max(0, self.link_scope_filter.findData(str(filters.get("link_scope") or "all")))
            )
            self.action_scope_filter.setCurrentIndex(
                max(0, self.action_scope_filter.findData(str(filters.get("action_scope") or "all")))
            )
        finally:
            self.link_scope_filter.blockSignals(False)
            self.action_scope_filter.blockSignals(False)

    def _on_link_scope_filter_changed(self) -> None:
        self.set_filter("link_scope", self.link_scope_filter.currentData())

    def _on_action_scope_filter_changed(self) -> None:
        self.set_filter("action_scope", self.action_scope_filter.currentData())

    def apply_query(self, query: str) -> None:
        self._populate_board()
        self._refresh_status()

    def apply_filters(self, filters: dict[str, object]) -> None:
        self._sync_filter_widgets(filters)
        self._populate_board()
        self._refresh_status()

    def refresh(self) -> None:
        self._model.reload()
        self._refresh_concept_boards()
        self._refresh_status()

    def on_enter(self, context: dict | None = None) -> None:
        super().on_enter(context)
        self._populate_board()
        self._refresh_status()

    def _refresh_concept_boards(self) -> None:
        boards = self._db.fetch_concept_boards()
        if not boards:
            created = self._db.create_concept_board("Концептборд 1", column_kinds=_DEFAULT_COLUMN_KINDS)
            self._ensure_default_columns(created.id)
            boards = self._db.fetch_concept_boards()
        current_id = self._current_concept_board_id()
        self._concept_boards_by_id = {board.id: board for board in boards}

        self.concept_board_list.blockSignals(True)
        self.concept_board_list.clear()
        for board in boards:
            attached_count = len(self._db.fetch_concept_board_items(board.id))
            updated_text = board.updated_at.strftime("%d.%m.%Y")
            item = QListWidgetItem(self._board_list_item_text(board, attached_count))
            item.setData(Qt.ItemDataRole.UserRole, board.id)
            item.setToolTip(
                "\n".join(
                    part
                    for part in (
                        board.title,
                        f"Статус: {self._board_status_text(board)}",
                        f"Связанных элементов: {attached_count}",
                        f"Обновлено: {updated_text}",
                        board.description.strip() if board.description.strip() else "",
                    )
                    if part
                )
            )
            self.concept_board_list.addItem(item)
        self.concept_board_list.blockSignals(False)

        restore_id = current_id if current_id in self._concept_boards_by_id else boards[0].id
        for index in range(self.concept_board_list.count()):
            item = self.concept_board_list.item(index)
            if item.data(Qt.ItemDataRole.UserRole) != restore_id:
                continue
            self.concept_board_list.setCurrentItem(item)
            break
        self._load_current_concept_board()

    def _on_concept_board_selection_changed(self) -> None:
        self._load_current_concept_board()
        self._rebuild_board_columns()
        self._populate_board()
        self._refresh_status()

    def _current_concept_board_id(self) -> int | None:
        item = self.concept_board_list.currentItem()
        board_id = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
        return board_id if isinstance(board_id, int) else None

    def _current_concept_board(self) -> ConceptBoardData | None:
        board_id = self._current_concept_board_id()
        if board_id is None:
            return None
        return self._concept_boards_by_id.get(board_id)

    def _create_concept_board(self) -> None:
        next_index = len(self._concept_boards_by_id) + 1
        created = self._db.create_concept_board(f"Концептборд {next_index}", column_kinds=_DEFAULT_COLUMN_KINDS)
        self._ensure_default_columns(created.id)
        self._model.reload()
        self._refresh_concept_boards()
        self._select_concept_board(created.id)
        self.set_status(f"Концептборд: создан «{created.title}».")

    def _select_concept_board(self, concept_board_id: int) -> None:
        for index in range(self.concept_board_list.count()):
            item = self.concept_board_list.item(index)
            if item.data(Qt.ItemDataRole.UserRole) != concept_board_id:
                continue
            self.concept_board_list.setCurrentItem(item)
            break

    def select_concept_board(self, concept_board_id: int) -> None:
        self.refresh()
        self._select_concept_board(concept_board_id)

    def _load_current_concept_board(self) -> None:
        board = self._current_concept_board()
        if board is None:
            self.focus_title_input.clear()
            self.focus_updated_value.setText("—")
            self.focus_attached_value.setText("0")
            self.focus_description_input.clear()
            for editor in self._scenario_editors.values():
                editor.clear()
            self._refresh_board_context(None)
            self._refresh_outcome_summary()
            self._refresh_focus(None)
            return
        self.focus_title_input.setText(board.title)
        self.focus_updated_value.setText(board.updated_at.strftime("%Y-%m-%d %H:%M"))
        self.focus_description_input.setPlainText(board.description)
        self._scenario_editors["capture"].setPlainText(board.capture_text)
        self._scenario_editors["planning"].setPlainText(board.planning_text)
        self._scenario_editors["links"].setPlainText(board.links_text)
        self._refresh_board_context(board)
        self._refresh_outcome_summary()
        self._refresh_focus(None)

    def _save_current_concept_board(self) -> None:
        board = self._current_concept_board()
        if board is None:
            self.set_status("Концептборд: сначала выберите доску.")
            return
        updated = self._db.update_concept_board(
            board.id,
            title=self.focus_title_input.text(),
            description=self.focus_description_input.toPlainText(),
            capture_text=self._scenario_editors["capture"].toPlainText(),
            planning_text=self._scenario_editors["planning"].toPlainText(),
            links_text=self._scenario_editors["links"].toPlainText(),
        )
        self._concept_boards_by_id[updated.id] = updated
        self._refresh_concept_boards()
        self._select_concept_board(updated.id)
        self._refresh_board_context(updated)
        self._refresh_outcome_summary()
        self._populate_board()
        self._refresh_focus(None if self._selected_card_key is None else self._card_by_key(*self._selected_card_key))
        self.set_status(f"Концептборд: данные «{updated.title}» сохранены.")

    def _rebuild_board_columns(self) -> None:
        self._column_defs.clear()
        self._column_kinds.clear()
        self._column_lists.clear()
        self._column_count_labels.clear()
        self._column_title_labels.clear()
        while self.columns_splitter.count():
            widget = self.columns_splitter.widget(0)
            self.columns_splitter.widget(0).setParent(None)
            if widget is not None:
                widget.deleteLater()

        board_id = self._current_concept_board_id()
        if board_id is None:
            return
        columns = self._db.fetch_concept_board_columns(board_id)
        if not columns:
            columns = self._ensure_default_columns(board_id)

        for column in columns:
            self._column_defs[column.id] = column
            self._column_kinds[column.id] = column.kind

            frame = QFrame(self.columns_splitter)
            frame.setObjectName("ConceptBoardColumn")
            frame.setMinimumWidth(250)
            frame.setMaximumWidth(640)
            column_layout = QVBoxLayout(frame)
            column_layout.setContentsMargins(12, 12, 12, 12)
            column_layout.setSpacing(8)

            header_row = QHBoxLayout()
            header_row.setContentsMargins(0, 0, 0, 0)
            header_row.setSpacing(8)

            title_label = QLabel(self._display_column_title(column))
            title_label.setObjectName("ConceptBoardScenarioTitle")
            header_row.addWidget(title_label, 1)
            self._column_title_labels[column.id] = title_label

            count_label = QLabel("0")
            count_label.setObjectName("ConceptBoardColumnCount")
            header_row.addWidget(count_label, 0, Qt.AlignmentFlag.AlignRight)
            self._column_count_labels[column.id] = count_label
            column_layout.addLayout(header_row)

            kind_row = QHBoxLayout()
            kind_row.setContentsMargins(0, 0, 0, 0)
            kind_row.setSpacing(8)

            kind_combo = QComboBox(frame)
            kind_combo.setObjectName("ConceptBoardColumnKindFilter")
            for kind, label_text in _COLUMN_KIND_LABELS.items():
                kind_combo.addItem(label_text, kind)
            kind_combo.setCurrentIndex(max(0, kind_combo.findData(column.kind)))
            kind_combo.setToolTip(self._display_column_title(column))
            kind_combo.currentIndexChanged.connect(
                lambda _index, column_id=column.id, combo=kind_combo: self._on_column_kind_changed(
                    column_id, combo.currentData()
                )
            )
            kind_row.addWidget(kind_combo, 1)
            column_layout.addLayout(kind_row)

            list_widget = _ConceptBoardColumnListWidget(self, column.id, frame)
            list_widget.setObjectName("ConceptBoardColumnList")
            list_widget.setItemDelegate(ConceptBoardDelegate(list_widget))
            list_widget.itemSelectionChanged.connect(
                lambda column_id=column.id: self._on_column_selection_changed(column_id)
            )
            column_layout.addWidget(list_widget, 1)

            add_button = QPushButton("+ Добавить", frame)
            add_button.setObjectName("ConceptBoardSecondaryButton")
            add_button.setEnabled(False)
            add_button.setToolTip(_DISABLED_ACTION_TOOLTIP)
            column_layout.addWidget(add_button, 0, Qt.AlignmentFlag.AlignLeft)
            self._column_lists[column.id] = list_widget
            self.columns_splitter.addWidget(frame)
            self.columns_splitter.setStretchFactor(self.columns_splitter.count() - 1, 1)

    def _on_column_kind_changed(self, column_id: int, kind: object) -> None:
        if not isinstance(kind, str):
            return
        current = self._column_defs.get(column_id)
        if current is None or current.kind == kind:
            return
        updated = self._db.update_concept_board_column(column_id, kind=kind, title=current.title, position=current.position)
        self._column_defs[column_id] = updated
        self._column_kinds[column_id] = updated.kind
        self._populate_board()
        self._refresh_status()

    def _next_column_kind(self) -> str:
        current_kinds = list(self._column_kinds.values())
        for kind in _COLUMN_KIND_LABELS:
            if kind not in current_kinds:
                return kind
        return next(iter(_COLUMN_KIND_LABELS))

    def _add_column(self) -> None:
        board_id = self._current_concept_board_id()
        if board_id is None:
            self.set_status("Концептборд: сначала выберите доску.")
            return
        self._db.add_concept_board_column(board_id, self._next_column_kind())
        self._refresh_concept_boards()
        self._select_concept_board(board_id)
        self._rebuild_board_columns()
        self._populate_board()
        self._refresh_status()

    def _filtered_cards(self, entity_kind: str | None = None) -> list[ConceptBoardCard]:
        filters = self.get_filters()
        link_scope = str(filters.get("link_scope") or "all")
        linked_only = True if link_scope == "linked" else False if link_scope == "unlinked" else None
        actionable_only = str(filters.get("action_scope") or "all") == "actionable"
        return self._model.filtered_cards(
            query=self.search_input.text(),
            entity_kind=entity_kind,
            actionable_only=actionable_only,
            linked_only=linked_only,
        )

    def _populate_board(self) -> None:
        board_id = self._current_concept_board_id()
        if board_id is None:
            return
        board = self._current_concept_board()
        attached_items = self._db.fetch_concept_board_items(board_id)
        self._attached_card_keys = {(item.entity_kind, item.entity_id) for item in attached_items}
        self.focus_attached_value.setText(str(len(self._attached_card_keys)))

        selection_key = self._selected_card_key
        for column_id, list_widget in self._column_lists.items():
            kind = self._column_kinds.get(column_id)
            cards = self._filtered_cards(kind)
            if kind in {"version", "solution"}:
                cards = [*cards, *self._synthetic_cards_for_kind(board, kind)]
            list_widget.blockSignals(True)
            list_widget.clear()
            if cards:
                for card in cards:
                    card_key = (card.entity_kind, card.entity_id)
                    payload = replace(card, is_attached=card_key in self._attached_card_keys)
                    item = QListWidgetItem(payload.title)
                    item.setData(Qt.ItemDataRole.UserRole, payload)
                    item.setToolTip(payload.meta_text or payload.subtitle or payload.title)
                    list_widget.addItem(item)
            else:
                title, hint = self._empty_state_text(kind or "")
                item = QListWidgetItem(title)
                item.setToolTip(hint)
                item.setFlags(Qt.ItemFlag.NoItemFlags)
                list_widget.addItem(item)
            count_label = self._column_count_labels.get(column_id)
            if count_label is not None and kind is not None:
                count_label.setText(f"{len(cards)}")
            title_label = self._column_title_labels.get(column_id)
            column_def = self._column_defs.get(column_id)
            if title_label is not None and column_def is not None:
                title_label.setText(self._display_column_title(column_def))
            list_widget.blockSignals(False)
        if selection_key is not None and self._restore_selection(selection_key):
            return
        self._set_selected_card(None)

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

    def _on_column_selection_changed(self, column_id: int) -> None:
        current_list = self._column_lists[column_id]
        current_item = current_list.currentItem()
        if current_item is None:
            if not any(list_widget.currentItem() is not None for list_widget in self._column_lists.values()):
                self._set_selected_card(None)
            return
        for other_column_id, list_widget in self._column_lists.items():
            if other_column_id == column_id:
                continue
            list_widget.blockSignals(True)
            list_widget.clearSelection()
            list_widget.setCurrentItem(None)
            list_widget.blockSignals(False)
        self._set_selected_card(current_item.data(Qt.ItemDataRole.UserRole))

    def _set_selected_card(self, card: ConceptBoardCard | None) -> None:
        self._selected_card_key = None if card is None else (card.entity_kind, card.entity_id)
        self._refresh_structure(card)
        self._refresh_focus(card)

    def _on_structure_relation_clicked(self, item: QListWidgetItem) -> None:
        target_key = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(target_key, tuple) or len(target_key) != 2:
            return
        self.board_tabs.setCurrentWidget(self.structure_panel)
        if self._restore_selection((str(target_key[0]), int(target_key[1]))):
            return
        self.set_status("Концептборд: связанный элемент сейчас недоступен в потоках.")

    def _refresh_structure(self, card: ConceptBoardCard | None) -> None:
        board = self._current_concept_board()
        if card is None:
            self.structure_subtitle.setText(
                "Выберите элемент в потоках, чтобы увидеть путь от материалов и идей к решению."
            )
            self.structure_hub_label.setText(board.title if board is not None else "Концептборд")
            self.structure_projects_label.setText("Проекты · 0")
            self.structure_objects_label.setText("Объекты · 0")
            self.structure_ideas_label.setText("Идеи · 0")
            self.structure_tasks_label.setText("Задачи · 0")
            self.structure_other_label.setText("Остальное · 0")
            self.structure_links_label.setText("Связи · 0")
            self.structure_details_label.setText(self._structure_overview_text(board))
            self._set_structure_relations(self._structure_overview_relations(board))
            return
        counts = self._structure_counts_for_card(card)
        self.structure_subtitle.setText(
            f"Активный элемент: {card.title} ({_CARD_KIND_TITLES.get(card.entity_kind, card.entity_kind)})."
        )
        self.structure_hub_label.setText(card.title)
        self.structure_projects_label.setText(f"Проекты · {counts['projects']}")
        self.structure_objects_label.setText(f"Объекты · {counts['objects']}")
        self.structure_ideas_label.setText(f"Идеи · {counts['ideas']}")
        self.structure_tasks_label.setText(f"Задачи · {counts['tasks']}")
        self.structure_other_label.setText(f"Остальное · {counts['other']}")
        self.structure_links_label.setText(f"Связи · {counts['links']}")
        self.structure_details_label.setText(self._structure_detail_text(card, board))
        self._set_structure_relations(self._structure_relations_for_card(card, board))

    def _structure_overview_text(self, board: ConceptBoardData | None) -> str:
        if board is None:
            return "Карта связей станет активной после выбора концептборда."
        checks = self._split_board_lines(board.planning_text)
        next_steps = self._split_board_lines(board.links_text)
        lines = [f"Цель: {board.description.strip() or 'не задана'}"]
        if checks:
            lines.append(f"Что проверить: {checks[0]}")
        if next_steps:
            lines.append(f"Следующий шаг: {next_steps[0]}")
        return "\n".join(lines)

    def _persisted_structure_relations(
        self,
        board: ConceptBoardData,
        card: ConceptBoardCard | None = None,
    ) -> list[tuple[str, tuple[str, int] | None]]:
        relations: list[tuple[str, tuple[str, int] | None]] = []
        links = self._db.fetch_concept_board_links(board.id)
        current_key = self._structure_card_key(card) if card is not None else None
        for link in links:
            source_key = self._entity_relation_target_key(link.source_kind, link.source_id)
            target_key = self._entity_relation_target_key(link.target_kind, link.target_id)
            if current_key is not None and current_key not in {source_key, target_key}:
                continue
            source_label = self._entity_relation_label(link.source_kind, link.source_id)
            target_label = self._entity_relation_label(link.target_kind, link.target_id)
            verb = _LINK_TYPE_TITLES.get(link.link_type, _LINK_TYPE_TITLES["relates_to"])
            jump_target = target_key
            if current_key is not None and current_key == target_key:
                jump_target = source_key
            relations.append((f"{source_label} {verb} {target_label}", jump_target))
        return self._dedupe_relations(relations)

    def _structure_overview_relations(self, board: ConceptBoardData | None) -> list[tuple[str, tuple[str, int] | None]]:
        if board is None:
            return []
        relations: list[tuple[str, tuple[str, int] | None]] = []
        material_card = self._first_card_for_structure(("image", "map", "marker", "note"))
        idea_card = self._first_card_for_structure(("idea",))
        task_card = self._first_card_for_structure(("task",))
        version_card = self._first_synthetic_card(board, "version")
        solution_card = self._first_synthetic_card(board, "solution")
        if material_card is not None and idea_card is not None:
            relations.append(
                (
                    f"{self._structure_card_label(material_card)} вдохновляет {self._structure_card_label(idea_card)}",
                    self._structure_card_key(idea_card),
                )
            )
        if idea_card is not None and version_card is not None:
            relations.append(
                (
                    f"{self._structure_card_label(idea_card)} развивает {self._structure_card_label(version_card)}",
                    self._structure_card_key(version_card),
                )
            )
        if version_card is not None and solution_card is not None:
            relations.append(
                (
                    f"{self._structure_card_label(version_card)} превращается в {self._structure_card_label(solution_card)}",
                    self._structure_card_key(solution_card),
                )
            )
        if solution_card is not None and task_card is not None:
            relations.append(
                (
                    f"{self._structure_card_label(solution_card)} превращается в {self._structure_card_label(task_card)}",
                    self._structure_card_key(task_card),
                )
            )
        return self._dedupe_relations(relations)

    def _structure_detail_text(self, card: ConceptBoardCard, board: ConceptBoardData | None) -> str:
        payload = card.source_payload
        if isinstance(payload, dict):
            checks = payload.get("checks") or []
            next_steps = payload.get("next_steps") or []
            lines = [f"Узел: {card.title}"]
            if checks:
                lines.append(f"Проверка: {checks[0]}")
            if next_steps:
                lines.append(f"Следующее действие: {next_steps[0]}")
            return "\n".join(lines)
        lines = [f"Узел: {card.title}", f"Связей: {card.total_linked_count}"]
        if card.project_title:
            lines.append(f"Контекст: {card.project_title}")
        if card.linked_idea_count:
            lines.append(f"Идей: {card.linked_idea_count}")
        if card.linked_task_count:
            lines.append(f"Задач: {card.linked_task_count}")
        if card.linked_object_count:
            lines.append(f"Объектов: {card.linked_object_count}")
        if board is not None and board.capture_text.strip():
            lines.append(f"Ведёт к решению: {self._split_board_lines(board.capture_text)[0]}")
        return "\n".join(lines)

    def _structure_relations_for_card(
        self,
        card: ConceptBoardCard,
        board: ConceptBoardData | None,
    ) -> list[tuple[str, tuple[str, int] | None]]:
        persisted_relations = [] if board is None else self._persisted_structure_relations(board, card)
        payload = card.source_payload
        if isinstance(payload, dict):
            return self._dedupe_relations([*persisted_relations, *self._structure_relations_for_synthetic_card(card, payload, board)])
        if isinstance(payload, ConceptBoardVersionData):
            return self._dedupe_relations([*persisted_relations, *self._structure_relations_for_version_card(card, payload, board)])
        if isinstance(payload, ConceptBoardSolutionData):
            return self._dedupe_relations([*persisted_relations, *self._structure_relations_for_solution_card(card, payload, board)])
        if isinstance(payload, TaskData):
            return self._dedupe_relations([*persisted_relations, *self._structure_relations_for_task_card(card, payload)])
        if isinstance(payload, IdeaData):
            return self._dedupe_relations([*persisted_relations, *self._structure_relations_for_idea_card(card, payload, board)])
        if isinstance(payload, ProjectData):
            return self._dedupe_relations([*persisted_relations, *self._structure_relations_for_project_card(card, payload)])
        if isinstance(payload, MapMarkerData):
            return self._dedupe_relations([*persisted_relations, *self._structure_relations_for_marker_card(card, payload)])
        if isinstance(payload, MapData):
            return self._dedupe_relations([*persisted_relations, *self._structure_relations_for_map_card(card, payload)])
        if isinstance(payload, CloudFileData):
            return self._dedupe_relations([*persisted_relations, *self._structure_relations_for_image_card(card, board)])
        if isinstance(payload, NoteData):
            tags = [(f"{self._structure_card_label(card)} относится к тегу «{tag}»", None) for tag in payload.tags[:3]]
            return self._dedupe_relations([*persisted_relations, *tags])
        return persisted_relations

    def _structure_relations_for_synthetic_card(
        self,
        card: ConceptBoardCard,
        payload: dict[str, object],
        board: ConceptBoardData | None,
    ) -> list[tuple[str, tuple[str, int] | None]]:
        relations: list[tuple[str, tuple[str, int] | None]] = []
        checks = [str(item).strip() for item in payload.get("checks") or [] if str(item).strip()]
        next_steps = [str(item).strip() for item in payload.get("next_steps") or [] if str(item).strip()]
        if card.entity_kind == "version":
            idea_card = self._first_card_for_structure(("idea",))
            if idea_card is not None:
                relations.append(
                    (
                        f"{self._structure_card_label(idea_card)} развивает {self._structure_card_label(card)}",
                        self._structure_card_key(card),
                    )
                )
            solution_card = self._first_synthetic_card(board, "solution")
            if solution_card is not None:
                relations.append(
                    (
                        f"{self._structure_card_label(card)} превращается в {self._structure_card_label(solution_card)}",
                        self._structure_card_key(solution_card),
                    )
                )
            if checks:
                relations.append((f"{self._structure_card_label(card)} относится к проверке «{checks[0]}»", None))
        elif card.entity_kind == "solution":
            version_card = self._first_synthetic_card(board, "version")
            if version_card is not None:
                relations.append(
                    (
                        f"{self._structure_card_label(version_card)} превращается в {self._structure_card_label(card)}",
                        self._structure_card_key(card),
                    )
                )
            for step in next_steps[:3]:
                relations.append((f"{self._structure_card_label(card)} превращается в Задача «{step}»", None))
            if checks:
                relations.append((f"{self._structure_card_label(card)} относится к проверке «{checks[0]}»", None))
        return self._dedupe_relations(relations)

    def _structure_relations_for_version_card(
        self,
        card: ConceptBoardCard,
        payload: ConceptBoardVersionData,
        board: ConceptBoardData | None,
    ) -> list[tuple[str, tuple[str, int] | None]]:
        relations: list[tuple[str, tuple[str, int] | None]] = []
        checks = self._split_board_lines(payload.checks_text)
        solution_card = self._first_synthetic_card(board, "solution")
        if solution_card is not None:
            relations.append(
                (
                    f"{self._structure_card_label(card)} РїСЂРµРІСЂР°С‰Р°РµС‚СЃСЏ РІ {self._structure_card_label(solution_card)}",
                    self._structure_card_key(solution_card),
                )
            )
        if checks:
            relations.append((f"{self._structure_card_label(card)} РѕС‚РЅРѕСЃРёС‚СЃСЏ Рє РїСЂРѕРІРµСЂРєРµ В«{checks[0]}В»", None))
        return self._dedupe_relations(relations)

    def _structure_relations_for_solution_card(
        self,
        card: ConceptBoardCard,
        payload: ConceptBoardSolutionData,
        board: ConceptBoardData | None,
    ) -> list[tuple[str, tuple[str, int] | None]]:
        relations: list[tuple[str, tuple[str, int] | None]] = []
        for step in self._split_board_lines(payload.next_steps_text)[:3]:
            relations.append((f"{self._structure_card_label(card)} РїСЂРµРІСЂР°С‰Р°РµС‚СЃСЏ РІ Р—Р°РґР°С‡Р° В«{step}В»", None))
        if payload.selected_version_id is not None:
            version_key = self._entity_relation_target_key("version", payload.selected_version_id)
            version_label = self._entity_relation_label("version", payload.selected_version_id)
            relations.append((f"{version_label} РїСЂРµРІСЂР°С‰Р°РµС‚СЃСЏ РІ {self._structure_card_label(card)}", version_key))
        return self._dedupe_relations(relations)

    def _structure_relations_for_task_card(
        self,
        card: ConceptBoardCard,
        payload: TaskData,
    ) -> list[tuple[str, tuple[str, int] | None]]:
        relations: list[tuple[str, tuple[str, int] | None]] = []
        for attachment in self._db.fetch_task_attachments(payload.id):
            if attachment.kind == "idea":
                relations.append(
                    (
                        f"{self._entity_relation_label('idea', attachment.ref_id)} превращается в {self._structure_card_label(card)}",
                        self._structure_card_key(card),
                    )
                )
            elif attachment.kind == "object":
                relations.append(
                    (
                        f"{self._structure_card_label(card)} относится к {self._entity_relation_label('object', attachment.ref_id)}",
                        self._entity_relation_target_key("object", attachment.ref_id),
                    )
                )
            elif attachment.kind == "task":
                relations.append(
                    (
                        f"{self._structure_card_label(card)} развивает {self._entity_relation_label('task', attachment.ref_id)}",
                        self._entity_relation_target_key("task", attachment.ref_id),
                    )
                )
        return self._dedupe_relations(relations)

    def _structure_relations_for_idea_card(
        self,
        card: ConceptBoardCard,
        payload: IdeaData,
        board: ConceptBoardData | None,
    ) -> list[tuple[str, tuple[str, int] | None]]:
        relations: list[tuple[str, tuple[str, int] | None]] = []
        for relation in self._db.fetch_idea_relations(payload.id):
            if relation.entity_type == "idea":
                relations.append(
                    (
                        f"{self._structure_card_label(card)} развивает {self._entity_relation_label('idea', relation.entity_id)}",
                        self._entity_relation_target_key("idea", relation.entity_id),
                    )
                )
            elif relation.entity_type == "task":
                relations.append(
                    (
                        f"{self._structure_card_label(card)} превращается в {self._entity_relation_label('task', relation.entity_id)}",
                        self._entity_relation_target_key("task", relation.entity_id),
                    )
                )
            elif relation.entity_type == "object":
                relations.append(
                    (
                        f"{self._structure_card_label(card)} относится к {self._entity_relation_label('object', relation.entity_id)}",
                        self._entity_relation_target_key("object", relation.entity_id),
                    )
                )
            else:
                relations.append(
                    (
                        f"{self._structure_card_label(card)} относится к {self._entity_relation_label(relation.entity_type, relation.entity_id)}",
                        self._entity_relation_target_key(relation.entity_type, relation.entity_id),
                    )
                )
        version_card = self._first_synthetic_card(board, "version")
        if version_card is not None:
            relations.append(
                (
                    f"{self._structure_card_label(card)} развивает {self._structure_card_label(version_card)}",
                    self._structure_card_key(version_card),
                )
            )
        return self._dedupe_relations(relations)

    def _structure_relations_for_project_card(
        self,
        card: ConceptBoardCard,
        payload: ProjectData,
    ) -> list[tuple[str, tuple[str, int] | None]]:
        relations: list[tuple[str, tuple[str, int] | None]] = []
        if payload.linked_object_id is not None:
            relations.append(
                (
                    f"{self._structure_card_label(card)} относится к {self._entity_relation_label('object', payload.linked_object_id)}",
                    self._entity_relation_target_key("object", payload.linked_object_id),
                )
            )
        if payload.linked_map_id is not None:
            relations.append(
                (
                    f"{self._structure_card_label(card)} относится к {self._entity_relation_label('map', payload.linked_map_id)}",
                    self._entity_relation_target_key("map", payload.linked_map_id),
                )
            )
        if payload.linked_note_id is not None:
            relations.append(
                (
                    f"{self._structure_card_label(card)} относится к {self._entity_relation_label('note', payload.linked_note_id)}",
                    self._entity_relation_target_key("note", payload.linked_note_id),
                )
            )
        return self._dedupe_relations(relations)

    def _structure_relations_for_marker_card(
        self,
        card: ConceptBoardCard,
        payload: MapMarkerData,
    ) -> list[tuple[str, tuple[str, int] | None]]:
        relations: list[tuple[str, tuple[str, int] | None]] = []
        for project_id in payload.project_ids[:2]:
            relations.append(
                (
                    f"{self._structure_card_label(card)} относится к {self._entity_relation_label('project', project_id)}",
                    self._entity_relation_target_key("project", project_id),
                )
            )
        for object_id in payload.object_ids[:2]:
            relations.append(
                (
                    f"{self._structure_card_label(card)} относится к {self._entity_relation_label('object', object_id)}",
                    self._entity_relation_target_key("object", object_id),
                )
            )
        for task_id in payload.task_ids[:2]:
            relations.append(
                (
                    f"{self._structure_card_label(card)} превращается в {self._entity_relation_label('task', task_id)}",
                    self._entity_relation_target_key("task", task_id),
                )
            )
        for note_id in payload.note_ids[:1]:
            relations.append(
                (
                    f"{self._structure_card_label(card)} относится к {self._entity_relation_label('note', note_id)}",
                    self._entity_relation_target_key("note", note_id),
                )
            )
        for map_id in payload.map_ids[:1]:
            relations.append(
                (
                    f"{self._structure_card_label(card)} относится к {self._entity_relation_label('map', map_id)}",
                    self._entity_relation_target_key("map", map_id),
                )
            )
        for marker_id in payload.marker_ids[:1]:
            relations.append(
                (
                    f"{self._structure_card_label(card)} относится к {self._entity_relation_label('marker', marker_id)}",
                    self._entity_relation_target_key("marker", marker_id),
                )
            )
        for file_id in payload.file_ids[:1]:
            relations.append(
                (
                    f"{self._structure_card_label(card)} относится к {self._entity_relation_label('file', file_id)}",
                    self._entity_relation_target_key("file", file_id),
                )
            )
        return self._dedupe_relations(relations)

    def _structure_relations_for_map_card(
        self,
        card: ConceptBoardCard,
        payload: MapData,
    ) -> list[tuple[str, tuple[str, int] | None]]:
        relations = [
            (
                f"{self._structure_card_label(card)} относится к {self._entity_relation_label('marker', marker.id)}",
                self._entity_relation_target_key("marker", marker.id),
            )
            for marker in self._db.fetch_map_markers(map_id=payload.id)[:3]
        ]
        return self._dedupe_relations(relations)

    def _structure_relations_for_image_card(
        self,
        card: ConceptBoardCard,
        board: ConceptBoardData | None,
    ) -> list[tuple[str, tuple[str, int] | None]]:
        relations: list[tuple[str, tuple[str, int] | None]] = []
        idea_card = self._first_card_for_structure(("idea",))
        if idea_card is not None:
            relations.append(
                (
                    f"{self._structure_card_label(card)} вдохновляет {self._structure_card_label(idea_card)}",
                    self._structure_card_key(idea_card),
                )
            )
        version_card = self._first_synthetic_card(board, "version")
        if version_card is not None:
            relations.append(
                (
                    f"{self._structure_card_label(card)} вдохновляет {self._structure_card_label(version_card)}",
                    self._structure_card_key(version_card),
                )
            )
        return self._dedupe_relations(relations)

    def _set_structure_relations(self, relations: list[tuple[str, tuple[str, int] | None]]) -> None:
        self.structure_relations_list.clear()
        if relations:
            for relation, target_key in relations[:8]:
                item = QListWidgetItem(relation)
                item.setData(Qt.ItemDataRole.UserRole, target_key)
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                self.structure_relations_list.addItem(item)
            return
        item = QListWidgetItem("Нет явных смысловых связей")
        item.setToolTip("Добавьте идеи, материалы, версию или итог, чтобы карта связей стала содержательной.")
        item.setFlags(Qt.ItemFlag.NoItemFlags)
        self.structure_relations_list.addItem(item)

    def _first_card_for_structure(self, entity_kinds: tuple[str, ...]) -> ConceptBoardCard | None:
        for card in self._model.cards():
            if card.entity_kind in entity_kinds:
                return card
        return None

    def _first_synthetic_card(self, board: ConceptBoardData | None, kind: str) -> ConceptBoardCard | None:
        if board is None:
            return None
        cards = self._synthetic_cards_for_kind(board, kind)
        return cards[0] if cards else None

    def _card_by_key(self, entity_kind: str, entity_id: int) -> ConceptBoardCard | None:
        card = self._model.get_card(entity_kind, entity_id)
        if card is not None:
            return card
        board = self._current_concept_board()
        if board is None:
            return None
        for kind in ("version", "solution"):
            for current in self._synthetic_cards_for_kind(board, kind):
                if (current.entity_kind, current.entity_id) == (entity_kind, entity_id):
                    return current
        return None

    @staticmethod
    def _structure_card_key(card: ConceptBoardCard) -> tuple[str, int]:
        return (card.entity_kind, card.entity_id)

    def _structure_card_label(self, card: ConceptBoardCard) -> str:
        kind_title = _CARD_KIND_TITLES.get(card.entity_kind, card.entity_kind.title())
        return f"{kind_title} «{card.title}»"

    def _entity_relation_target_key(self, entity_kind: str, entity_id: int) -> tuple[str, int] | None:
        card = self._card_by_key(entity_kind, entity_id)
        if card is None:
            return None
        return self._structure_card_key(card)

    def _entity_relation_label(self, entity_kind: str, entity_id: int) -> str:
        card = self._card_by_key(entity_kind, entity_id)
        if card is not None:
            return self._structure_card_label(card)
        kind_title = _CARD_KIND_TITLES.get(entity_kind, entity_kind.title())
        return f"{kind_title} #{entity_id}"

    @staticmethod
    def _dedupe_relations(
        relations: list[tuple[str, tuple[str, int] | None]],
    ) -> list[tuple[str, tuple[str, int] | None]]:
        result: list[tuple[str, tuple[str, int] | None]] = []
        seen: set[str] = set()
        for relation, target_key in relations:
            normalized = relation.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            result.append((normalized, target_key))
        return result

    def _structure_counts_for_card(self, card: ConceptBoardCard) -> dict[str, int]:
        counts = {"projects": 0, "objects": 0, "ideas": 0, "tasks": 0, "other": 0, "links": card.total_linked_count}
        payload = card.source_payload
        if isinstance(payload, TaskData):
            counts["tasks"] = 1
            counts["ideas"] = card.linked_idea_count
            counts["objects"] = card.linked_object_count
            counts["links"] = card.total_linked_count
            return counts
        if isinstance(payload, IdeaData):
            counts["ideas"] = 1 + card.linked_idea_count
            counts["tasks"] = card.linked_task_count
            counts["objects"] = card.linked_object_count
            counts["links"] = card.total_linked_count
            return counts
        if isinstance(payload, ObjectData):
            counts["objects"] = 1
            counts["tasks"] = card.linked_task_count
            counts["ideas"] = card.linked_idea_count
            counts["links"] = card.total_linked_count
            return counts
        if isinstance(payload, ProjectData):
            counts["projects"] = 1
            counts["objects"] = 1 if payload.linked_object_id is not None else 0
            counts["other"] = sum(
                1 for value in (payload.linked_map_id, payload.linked_note_id) if value is not None
            )
            counts["links"] = counts["objects"] + counts["other"]
            return counts
        if isinstance(payload, MapMarkerData):
            counts["projects"] = len(payload.project_ids)
            counts["objects"] = len(payload.object_ids)
            counts["tasks"] = len(payload.task_ids)
            counts["other"] = len(payload.note_ids) + len(payload.file_ids) + len(payload.map_ids) + len(payload.marker_ids)
            counts["links"] = counts["projects"] + counts["objects"] + counts["tasks"] + counts["other"]
            return counts
        if isinstance(payload, MapData):
            counts["other"] = self._model.map_marker_count(payload.id)
            counts["links"] = counts["other"]
            return counts
        if isinstance(payload, NoteData):
            counts["other"] = len(payload.tags)
            counts["links"] = counts["other"]
            return counts
        if isinstance(payload, CloudFileData):
            return counts
        return counts

    def _open_card_context_menu(self, card: ConceptBoardCard, global_pos) -> None:
        board = self._current_concept_board()
        menu = QMenu(self)
        attach_action = menu.addAction("Связать с концептбордом")
        if board is None or (card.entity_kind, card.entity_id) in self._attached_card_keys:
            attach_action.setEnabled(board is not None and (card.entity_kind, card.entity_id) not in self._attached_card_keys)
        chosen = menu.exec(global_pos)
        if chosen is not attach_action or board is None:
            return
        self._db.attach_concept_board_item(board.id, card.entity_kind, card.entity_id)
        self._populate_board()
        self._refresh_status()
        self.set_status(f"Концептборд: элемент «{card.title}» связан с «{board.title}».")

    def _refresh_status(self) -> None:
        total_count = len(self._model.cards())
        visible_count = sum(
            1
            for list_widget in self._column_lists.values()
            for index in range(list_widget.count())
            if list_widget.item(index).data(Qt.ItemDataRole.UserRole) is not None
        )
        attached_count = len(self._attached_card_keys)
        filter_summary = self._active_filter_summary()
        if self.search_input.text().strip() or filter_summary:
            self.set_status(f"Концептборд: элементов {visible_count} из {total_count} · связано {attached_count}.")
            return
        self.set_status(f"Концептборд: элементов {total_count} · связано {attached_count}.")

    def _active_filter_summary(self) -> str:
        filters = self.get_filters()
        parts: list[str] = []
        link_scope = str(filters.get("link_scope") or "all")
        action_scope = str(filters.get("action_scope") or "all")
        if link_scope == "linked":
            parts.append("только связанные")
        elif link_scope == "unlinked":
            parts.append("без связей")
        if action_scope == "actionable":
            parts.append("требуют действия")
        return " · ".join(parts)

    def _apply_concept_board_style(self) -> None:
        palette = get_theme_palette("dark")
        shell_bg = "#0d1218"
        shell_panel = "#111722"
        shell_panel_alt = "#151d2a"
        shell_input = "#121b28"
        shell_input_hover = "#1a2433"
        shell_border = "#253142"
        shell_text = "#eef3ff"
        shell_dim_text = "#9aa8bc"
        self.setStyleSheet(
            self._base_workspace_stylesheet
            + f"""
            QWidget#WorkspaceToolbar,
            QWidget#WorkspaceSearch,
            QWidget#WorkspaceFilters,
            QWidget#WorkspaceContent {{
                background: {shell_panel};
                border: 1px solid {shell_border};
                border-radius: 14px;
                padding: 6px;
            }}
            QWidget#WorkspaceContent,
            QWidget#ConceptBoardRoot {{
                border: none;
                border-radius: 0px;
                padding: 0px;
                background: {shell_bg};
            }}
            QFrame#ConceptBoardListPanel,
            QFrame#ConceptBoardBoardWrap,
            QFrame#ConceptBoardBoardHeader,
            QFrame#ConceptBoardFocusPanel,
            QFrame#ConceptBoardInsightPanel,
            QFrame#ConceptBoardScenarioCard,
            QFrame#ConceptBoardColumn {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {shell_panel}, stop:1 {shell_panel_alt});
                border: 1px solid {shell_border};
                border-radius: 18px;
            }}
            QScrollArea#ConceptBoardScroll,
            QWidget#ConceptBoardColumnsHost,
            QWidget#ConceptBoardRoot QSplitter {{
                background: transparent;
                border: none;
            }}
            QSplitter#ConceptBoardColumnsSplitter::handle {{
                background: rgba(255, 255, 255, 0.05);
                width: 8px;
                margin: 18px 2px;
                border-radius: 4px;
            }}
            QSplitter#ConceptBoardColumnsSplitter::handle:hover {{
                background: rgba(111, 140, 255, 0.22);
            }}
            QTabWidget#ConceptBoardTabs::pane {{
                border: none;
                background: transparent;
            }}
            QTabBar::tab {{
                background: {shell_input};
                color: {shell_dim_text};
                border: 1px solid {shell_border};
                border-radius: 10px;
                padding: 8px 14px;
                margin-right: 6px;
            }}
            QTabBar::tab:selected {{
                color: {shell_text};
                background: rgba(111, 140, 255, 0.18);
            }}
            QSplitter#ConceptBoardSplitter::handle {{
                background: rgba(255, 255, 255, 0.04);
                width: 6px;
                margin: 10px 0;
                border-radius: 3px;
            }}
            QWidget#ConceptBoardRoot QLabel {{
                color: {shell_text};
                background: transparent;
            }}
            QLabel#ConceptBoardListTitle,
            QLabel#ConceptBoardInsightTitle,
            QLabel#ConceptBoardBoardHeadline,
            QLabel#ConceptBoardInspectorTitle {{
                color: {shell_text};
                font-size: 19px;
                font-weight: 700;
            }}
            QLabel#ConceptBoardListSubtitle,
            QLabel#ConceptBoardInsightBody,
            QLabel#ConceptBoardBoardCaption,
            QLabel#ConceptBoardColumnCount,
            QLabel#ConceptBoardScenarioTitle,
            QLabel#ConceptBoardNodeMuted,
            QLabel#ConceptBoardNodeTask,
            QLabel#ConceptBoardNodeIdea,
            QLabel#ConceptBoardNodeObject,
            QLabel#ConceptBoardNodeHub {{
                color: {shell_dim_text};
            }}
            QLineEdit#WorkspaceSearchInput,
            QToolButton#WorkspaceSearchClear,
            QWidget#WorkspaceToolbar QToolButton,
            QComboBox#ConceptBoardFilterCombo,
            QListWidget#ConceptBoardList,
            QListWidget#ConceptBoardColumnList,
            QListWidget#ConceptBoardRelationList,
            QTextEdit#ConceptBoardFocusDescription,
            QTextEdit#ConceptBoardScenarioEditor,
            QLineEdit#ConceptBoardFocusTitle,
            QComboBox#ConceptBoardColumnKindFilter {{
                background: {shell_input};
                color: {shell_text};
                border: 1px solid {shell_border};
                border-radius: 12px;
                padding: 8px 10px;
            }}
            QListWidget#ConceptBoardList::viewport,
            QListWidget#ConceptBoardColumnList::viewport,
            QListWidget#ConceptBoardRelationList::viewport,
            QTextEdit#ConceptBoardFocusDescription,
            QTextEdit#ConceptBoardFocusDescription QWidget,
            QTextEdit#ConceptBoardScenarioEditor,
            QTextEdit#ConceptBoardScenarioEditor QWidget {{
                background: {shell_input};
                color: {shell_text};
            }}
            QComboBox#ConceptBoardColumnKindFilter::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox#ConceptBoardFilterCombo::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox#ConceptBoardColumnKindFilter QAbstractItemView,
            QComboBox#ConceptBoardFilterCombo QAbstractItemView,
            QMenu {{
                background: {shell_panel_alt};
                color: {shell_text};
                border: 1px solid {shell_border};
                border-radius: 12px;
                padding: 6px;
            }}
            QComboBox#ConceptBoardColumnKindFilter QAbstractItemView::item,
            QComboBox#ConceptBoardFilterCombo QAbstractItemView::item,
            QMenu::item {{
                background: transparent;
                color: {shell_text};
                padding: 8px 10px;
                border-radius: 8px;
            }}
            QComboBox#ConceptBoardColumnKindFilter QAbstractItemView::item:selected,
            QComboBox#ConceptBoardFilterCombo QAbstractItemView::item:selected,
            QMenu::item:selected {{
                background: rgba(111, 140, 255, 0.18);
            }}
            QListWidget#ConceptBoardList::item:selected,
            QListWidget#ConceptBoardColumnList::item:selected,
            QListWidget#ConceptBoardRelationList::item:selected {{
                background: rgba(111, 140, 255, 0.18);
            }}
            QPushButton#ConceptBoardPrimaryButton,
            QPushButton#ConceptBoardSecondaryButton {{
                background: {shell_input};
                color: {shell_text};
                border: 1px solid {shell_border};
                border-radius: 12px;
                padding: 9px 14px;
            }}
            QPushButton#ConceptBoardPrimaryButton:hover,
            QPushButton#ConceptBoardSecondaryButton:hover,
            QTextEdit#ConceptBoardFocusDescription:hover,
            QTextEdit#ConceptBoardScenarioEditor:hover,
            QLineEdit#WorkspaceSearchInput:hover,
            QToolButton#WorkspaceSearchClear:hover,
            QWidget#WorkspaceToolbar QToolButton:hover,
            QComboBox#ConceptBoardFilterCombo:hover,
            QLineEdit#ConceptBoardFocusTitle:hover,
            QComboBox#ConceptBoardColumnKindFilter:hover {{
                background: {shell_input_hover};
            }}
            QPushButton#ConceptBoardPrimaryButton:disabled,
            QPushButton#ConceptBoardSecondaryButton:disabled {{
                color: {shell_dim_text};
                border-color: rgba(37, 49, 66, 0.7);
            }}
            QFrame#ConceptBoardStructureGraph {{
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid {shell_border};
                border-radius: 16px;
            }}
            QLabel#ConceptBoardNodeHub,
            QLabel#ConceptBoardNodeIdea,
            QLabel#ConceptBoardNodeTask,
            QLabel#ConceptBoardNodeObject,
            QLabel#ConceptBoardNodeMuted {{
                border: 1px solid {shell_border};
                border-radius: 16px;
                padding: 10px 12px;
                background: rgba(255, 255, 255, 0.04);
            }}
            QLabel#ConceptBoardNodeHub {{
                color: {shell_text};
                background: rgba(111, 140, 255, 0.18);
            }}
            """
        )


ConceptBoardWorkspace = ConceptBoardWorkspace

__all__ = ["ConceptBoardWorkspace", "ConceptBoardWorkspace"]
