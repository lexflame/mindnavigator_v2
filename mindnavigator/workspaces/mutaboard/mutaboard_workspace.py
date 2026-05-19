"""Workspace UI for the persistent MutaBoard experience."""

from __future__ import annotations

from dataclasses import replace

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
from .mutaboard_card import ConceptBoardCard
from .mutaboard_delegate import ConceptBoardDelegate
from .mutaboard_model import ConceptBoardModel, get_database
from mindnavigator.storage import (
    CloudFileData,
    IdeaData,
    MapData,
    MapMarkerData,
    MutaBoardColumnData,
    MutaBoardData,
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


class _MutaBoardColumnListWidget(QListWidget):
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

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ConceptBoardWorkspace")
        self._base_workspace_stylesheet = self.styleSheet()
        self._db = get_database()
        self._model = ConceptBoardModel(db=self._db)
        self._mutaboards_by_id: dict[int, MutaBoardData] = {}
        self._column_defs: dict[int, MutaBoardColumnData] = {}
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
        root.setObjectName("MutaBoardRoot")
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(16)

        top_splitter = QSplitter(Qt.Orientation.Horizontal, root)
        top_splitter.setObjectName("MutaBoardSplitter")
        top_splitter.addWidget(self._build_mutaboards_panel(top_splitter))
        top_splitter.addWidget(self._build_board_panel(top_splitter))
        top_splitter.addWidget(self._build_focus_panel(top_splitter))
        top_splitter.setStretchFactor(0, 1)
        top_splitter.setStretchFactor(1, 4)
        top_splitter.setStretchFactor(2, 2)
        root_layout.addWidget(top_splitter, 1)

        self.set_content(root)
        self._apply_mutaboard_style()

    def _build_mutaboards_panel(self, parent: QWidget) -> QFrame:
        panel = QFrame(parent)
        panel.setObjectName("MutaBoardListPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("Концептборды")
        title.setObjectName("MutaBoardListTitle")
        subtitle = QLabel("Смысловые доски поиска решения. Выберите активный концептборд или создайте новый.")
        subtitle.setObjectName("MutaBoardListSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        self.mutaboard_list = QListWidget(panel)
        self.mutaboard_list.setObjectName("MutaBoardList")
        self.mutaboard_list.itemSelectionChanged.connect(self._on_mutaboard_selection_changed)
        layout.addWidget(self.mutaboard_list, 1)

        self.add_mutaboard_button = QPushButton("+ Новый концептборд", panel)
        self.add_mutaboard_button.setObjectName("MutaBoardPrimaryButton")
        self.add_mutaboard_button.clicked.connect(self._create_mutaboard)
        layout.addWidget(self.add_mutaboard_button)

        footer = QLabel("Архив\nШаблоны\nНастройки концептбордов", panel)
        footer.setObjectName("MutaBoardListSubtitle")
        footer.setWordWrap(True)
        layout.addWidget(footer)
        return panel

    def _build_board_panel(self, parent: QWidget) -> QFrame:
        panel = QFrame(parent)
        panel.setObjectName("MutaBoardBoardWrap")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        overview = QFrame(panel)
        overview.setObjectName("MutaBoardBoardHeader")
        overview_layout = QHBoxLayout(overview)
        overview_layout.setContentsMargins(16, 16, 16, 16)
        overview_layout.setSpacing(12)

        overview_text = QVBoxLayout()
        overview_text.setContentsMargins(0, 0, 0, 0)
        overview_text.setSpacing(4)
        self.board_title_label = QLabel("Концептборд")
        self.board_title_label.setObjectName("MutaBoardBoardHeadline")
        overview_caption = QLabel("Смысловая доска поиска решения")
        overview_caption.setObjectName("MutaBoardBoardCaption")
        self.board_status_badge = QLabel("Исследование")
        self.board_status_badge.setObjectName("MutaBoardColumnCount")
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
            button.setObjectName("MutaBoardSecondaryButton")
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
        goal_card.setObjectName("MutaBoardScenarioCard")
        goal_layout = QVBoxLayout(goal_card)
        goal_layout.setContentsMargins(16, 16, 16, 16)
        goal_layout.setSpacing(8)
        goal_title = QLabel("Цель доски")
        goal_title.setObjectName("MutaBoardInsightTitle")
        self.goal_body_label = QLabel("Цель не задана")
        self.goal_body_label.setObjectName("MutaBoardBoardCaption")
        self.goal_body_label.setWordWrap(True)
        self.goal_hint_label = QLabel("Добавьте цель, чтобы концептборд не превратился в склад материалов.")
        self.goal_hint_label.setObjectName("MutaBoardListSubtitle")
        self.goal_hint_label.setWordWrap(True)
        self.goal_edit_button = QPushButton("Редактировать цель", goal_card)
        self.goal_edit_button.setObjectName("MutaBoardSecondaryButton")
        self.goal_edit_button.clicked.connect(self._edit_goal)
        goal_layout.addWidget(goal_title)
        goal_layout.addWidget(self.goal_body_label)
        goal_layout.addWidget(self.goal_hint_label)
        goal_layout.addWidget(self.goal_edit_button, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(goal_card)

        self.board_tabs = QTabWidget(panel)
        self.board_tabs.setObjectName("MutaBoardTabs")
        layout.addWidget(self.board_tabs, 1)

        flows_page = QWidget(panel)
        flows_layout = QVBoxLayout(flows_page)
        flows_layout.setContentsMargins(0, 0, 0, 0)
        flows_layout.setSpacing(14)

        header = QFrame(flows_page)
        header.setObjectName("MutaBoardBoardHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 16, 16, 16)
        header_layout.setSpacing(12)

        header_text = QVBoxLayout()
        header_text.setContentsMargins(0, 0, 0, 0)
        header_text.setSpacing(4)
        title = QLabel("Потоки решения")
        title.setObjectName("MutaBoardBoardHeadline")
        caption = QLabel(
            "Разложите материалы, идеи, версии и задачи по колонкам, чтобы пройти путь от входящих сигналов к решению."
        )
        caption.setObjectName("MutaBoardBoardCaption")
        caption.setWordWrap(True)
        header_text.addWidget(title)
        header_text.addWidget(caption)
        header_layout.addLayout(header_text, 1)

        self.add_column_button = QPushButton("+ Добавить", header)
        self.add_column_button.setObjectName("MutaBoardSecondaryButton")
        self.add_column_button.clicked.connect(self._add_column)
        header_layout.addWidget(self.add_column_button, 0, Qt.AlignmentFlag.AlignTop)
        flows_layout.addWidget(header)

        self.board_scroll = QScrollArea(flows_page)
        self.board_scroll.setObjectName("MutaBoardScroll")
        self.board_scroll.setWidgetResizable(True)
        self.board_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.board_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.board_inner = QWidget()
        self.board_inner.setObjectName("MutaBoardColumnsHost")
        self.board_layout = QHBoxLayout(self.board_inner)
        self.board_layout.setContentsMargins(0, 0, 0, 0)
        self.board_layout.setSpacing(10)

        self.board_scroll.setWidget(self.board_inner)
        flows_layout.addWidget(self.board_scroll, 1)

        self.board_tabs.addTab(flows_page, "Потоки")
        self.structure_panel = self._build_structure_panel(self.board_tabs)
        self.scenarios_panel = self._build_scenarios_panel(self.board_tabs)
        self.board_tabs.addTab(self.structure_panel, "Карта связей")
        self.board_tabs.addTab(self.scenarios_panel, "Итог")

        summary = QFrame(panel)
        summary.setObjectName("MutaBoardScenarioCard")
        summary_layout = QVBoxLayout(summary)
        summary_layout.setContentsMargins(16, 16, 16, 16)
        summary_layout.setSpacing(8)
        summary_title = QLabel("Итог и следующие шаги")
        summary_title.setObjectName("MutaBoardInsightTitle")
        self.summary_solution_label = QLabel("Текущее решение ещё не зафиксировано.")
        self.summary_solution_label.setObjectName("MutaBoardBoardCaption")
        self.summary_solution_label.setWordWrap(True)
        self.summary_checks_label = QLabel("Что проверить появится после заполнения вкладки «Итог».")
        self.summary_checks_label.setObjectName("MutaBoardListSubtitle")
        self.summary_checks_label.setWordWrap(True)
        self.summary_tasks_label = QLabel("Следующие задачи пока не заданы.")
        self.summary_tasks_label.setObjectName("MutaBoardListSubtitle")
        self.summary_tasks_label.setWordWrap(True)
        open_summary_button = QPushButton("Открыть итог", summary)
        open_summary_button.setObjectName("MutaBoardSecondaryButton")
        open_summary_button.clicked.connect(lambda: self.board_tabs.setCurrentWidget(self.scenarios_panel))
        self.accept_solution_button = QPushButton("Принять решение", summary)
        self.accept_solution_button.setObjectName("MutaBoardSecondaryButton")
        self.accept_solution_button.clicked.connect(self._accept_current_solution)
        self.review_solution_button = QPushButton("Отправить на проверку", summary)
        self.review_solution_button.setObjectName("MutaBoardSecondaryButton")
        self.review_solution_button.clicked.connect(self._send_current_solution_to_review)
        self.create_tasks_button = QPushButton("Создать задачи из решения", summary)
        self.create_tasks_button.setObjectName("MutaBoardSecondaryButton")
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
        panel.setObjectName("MutaBoardFocusPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        self.focus_heading_label = QLabel("Фокус: Концептборд")
        self.focus_heading_label.setObjectName("MutaBoardInspectorTitle")
        self.focus_caption_label = QLabel("Сводка по активной доске и выбранному элементу.")
        self.focus_caption_label.setObjectName("MutaBoardBoardCaption")
        self.focus_caption_label.setWordWrap(True)
        layout.addWidget(self.focus_heading_label)
        layout.addWidget(self.focus_caption_label)

        form_host = QWidget(panel)
        form = QFormLayout(form_host)
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(8)

        self.focus_title_input = QLineEdit(form_host)
        self.focus_title_input.setObjectName("MutaBoardFocusTitle")
        self.focus_title_input.textChanged.connect(self._sync_board_header_preview)
        self.focus_status_value = QLabel("Исследование")
        self.focus_updated_value = QLabel("—")
        self.focus_attached_value = QLabel("0")
        self.focus_description_input = QTextEdit(form_host)
        self.focus_description_input.setObjectName("MutaBoardFocusDescription")
        self.focus_description_input.setMinimumHeight(160)
        self.focus_description_input.setPlaceholderText("Цель, контекст и описание концептборда...")

        form.addRow("Название", self.focus_title_input)
        form.addRow("Статус", self.focus_status_value)
        form.addRow("Обновлён", self.focus_updated_value)
        form.addRow("Связанных элементов", self.focus_attached_value)
        form.addRow("Цель и описание", self.focus_description_input)
        layout.addWidget(form_host, 1)

        self.focus_card_panel = QFrame(panel)
        self.focus_card_panel.setObjectName("MutaBoardScenarioCard")
        card_layout = QVBoxLayout(self.focus_card_panel)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(8)
        self.focus_card_kind_label = QLabel("Элемент")
        self.focus_card_kind_label.setObjectName("MutaBoardScenarioTitle")
        self.focus_card_title_label = QLabel("Выберите элемент")
        self.focus_card_title_label.setObjectName("MutaBoardInsightTitle")
        self.focus_card_meta_label = QLabel("Связи и метаданные появятся здесь.")
        self.focus_card_meta_label.setObjectName("MutaBoardBoardCaption")
        self.focus_card_meta_label.setWordWrap(True)
        self.focus_card_links_label = QLabel("Связей: 0")
        self.focus_card_links_label.setObjectName("MutaBoardListSubtitle")
        self.focus_card_details = QTextEdit(self.focus_card_panel)
        self.focus_card_details.setObjectName("MutaBoardScenarioEditor")
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
            button.setObjectName("MutaBoardSecondaryButton")
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
        self.focus_save_button.setObjectName("MutaBoardPrimaryButton")
        self.focus_save_button.clicked.connect(self._save_current_mutaboard)
        layout.addWidget(self.focus_save_button)
        return panel

    def _build_structure_panel(self, parent: QWidget) -> QFrame:
        panel = QFrame(parent)
        panel.setObjectName("MutaBoardInsightPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("Карта связей")
        title.setObjectName("MutaBoardInsightTitle")
        self.structure_subtitle = QLabel("Показывает, как материалы, идеи и задачи сходятся к активному фокусу.")
        self.structure_subtitle.setObjectName("MutaBoardInsightBody")
        self.structure_subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(self.structure_subtitle)

        graph = QFrame(panel)
        graph.setObjectName("MutaBoardStructureGraph")
        graph_layout = QHBoxLayout(graph)
        graph_layout.setContentsMargins(8, 8, 8, 8)
        graph_layout.setSpacing(12)

        left_col = QVBoxLayout()
        left_col.setSpacing(10)
        center_col = QVBoxLayout()
        center_col.setSpacing(10)
        right_col = QVBoxLayout()
        right_col.setSpacing(10)

        self.structure_projects_label = self._create_structure_node("MutaBoardNodeMuted", "Проекты · 0")
        self.structure_objects_label = self._create_structure_node("MutaBoardNodeObject", "Объекты · 0")
        self.structure_ideas_label = self._create_structure_node("MutaBoardNodeIdea", "Идеи · 0")
        self.structure_hub_label = self._create_structure_node("MutaBoardNodeHub", "Концептборд")
        self.structure_links_label = self._create_structure_node("MutaBoardNodeMuted", "Связи · 0")
        self.structure_tasks_label = self._create_structure_node("MutaBoardNodeTask", "Задачи · 0")
        self.structure_other_label = self._create_structure_node("MutaBoardNodeMuted", "Остальное · 0")

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
        self.structure_details_label.setObjectName("MutaBoardBoardCaption")
        self.structure_details_label.setWordWrap(True)
        layout.addWidget(self.structure_details_label)
        return panel

    def _build_scenarios_panel(self, parent: QWidget) -> QFrame:
        panel = QFrame(parent)
        panel.setObjectName("MutaBoardInsightPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("Итог и следующие шаги")
        title.setObjectName("MutaBoardInsightTitle")
        subtitle = QLabel("Зафиксируйте текущее решение, проверки и следующие задачи, чтобы перейти от анализа к действию.")
        subtitle.setObjectName("MutaBoardInsightBody")
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
            card.setObjectName("MutaBoardScenarioCard")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(12, 12, 12, 12)
            card_layout.setSpacing(8)
            card_title = QLabel(label_text)
            card_title.setObjectName("MutaBoardScenarioTitle")
            editor = QTextEdit(card)
            editor.setObjectName("MutaBoardScenarioEditor")
            editor.setMinimumHeight(128)
            editor.textChanged.connect(self._refresh_outcome_summary)
            self._scenario_editors[key] = editor
            card_layout.addWidget(card_title)
            card_layout.addWidget(editor, 1)
            cards_row.addWidget(card, 1)
        layout.addLayout(cards_row, 1)

        self.scenarios_save_button = QPushButton("Сохранить итог", panel)
        self.scenarios_save_button.setObjectName("MutaBoardSecondaryButton")
        self.scenarios_save_button.clicked.connect(self._save_current_mutaboard)
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

    def _refresh_board_context(self, board: MutaBoardData | None) -> None:
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
    def _board_status_text(board: MutaBoardData | None) -> str:
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
        planning_text = self._scenario_editors["planning"].toPlainText().strip()
        links_text = self._scenario_editors["links"].toPlainText().strip()
        self.summary_solution_label.setText(capture_text or "Текущее решение ещё не зафиксировано.")
        self.summary_checks_label.setText(planning_text or "Что проверить появится после заполнения вкладки «Итог».")
        self.summary_tasks_label.setText(links_text or "Следующие задачи пока не заданы.")
        board = self._current_mutaboard()
        description = board.description if board is not None else ""
        status_text = self._board_status_text_from_values(description, capture_text, planning_text, links_text)
        self.board_status_badge.setText(status_text)
        self.focus_status_value.setText(status_text)

    def _refresh_focus(self, card: ConceptBoardCard | None) -> None:
        board = self._current_mutaboard()
        self._focused_card = card
        if card is None:
            self.focus_heading_label.setText("Фокус: Концептборд")
            self.focus_caption_label.setText("Редактируйте цель, описание и общий контекст активной доски.")
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

    def _focus_details_text(self, card: ConceptBoardCard, board: MutaBoardData | None) -> str:
        payload = card.source_payload
        if isinstance(payload, dict):
            return self._synthetic_focus_details(card, payload, board)
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
        board: MutaBoardData | None,
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

    def _task_focus_details(self, task: TaskData, card: ConceptBoardCard, board: MutaBoardData | None) -> str:
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

    def _idea_focus_details(self, idea: IdeaData, card: ConceptBoardCard, board: MutaBoardData | None) -> str:
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

    def _image_focus_details(self, cloud_file: CloudFileData, card: ConceptBoardCard, board: MutaBoardData | None) -> str:
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

    def _project_focus_details(self, project: ProjectData, card: ConceptBoardCard, board: MutaBoardData | None) -> str:
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

    def _marker_focus_details(self, marker: MapMarkerData, card: ConceptBoardCard, board: MutaBoardData | None) -> str:
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

    def _object_focus_details(self, obj: ObjectData, card: ConceptBoardCard, board: MutaBoardData | None) -> str:
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

    def _note_focus_details(self, note: NoteData, card: ConceptBoardCard, board: MutaBoardData | None) -> str:
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

    def _map_focus_details(self, map_item: MapData, card: ConceptBoardCard, board: MutaBoardData | None) -> str:
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
        if card.entity_kind in {"version", "solution"}:
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

    def _on_quick_add_idea(self) -> None:
        self._clear_card_selection()
        updated = self._append_unique_line(self.focus_description_input.toPlainText(), "Идея: ")
        self.focus_description_input.setPlainText(updated)
        self.focus_description_input.setFocus()
        self.set_status("Концептборд: добавлен черновик идеи.")

    def _on_quick_add_version(self) -> None:
        self.board_tabs.setCurrentWidget(self.scenarios_panel)
        updated = self._append_unique_line(self._scenario_editors["planning"].toPlainText(), "Проверить версию: ")
        self._scenario_editors["planning"].setPlainText(updated)
        self._scenario_editors["planning"].setFocus()
        self._refresh_outcome_summary()
        self.set_status("Концептборд: добавлен черновик версии.")

    def _on_quick_add_task(self) -> None:
        self.board_tabs.setCurrentWidget(self.scenarios_panel)
        updated = self._append_unique_line(self._scenario_editors["links"].toPlainText(), "Следующая задача: ")
        self._scenario_editors["links"].setPlainText(updated)
        self._scenario_editors["links"].setFocus()
        self._refresh_outcome_summary()
        self.set_status("Концептборд: добавлена следующая задача.")

    @staticmethod
    def _default_column_specs() -> list[tuple[str, str]]:
        return list(_DEFAULT_COLUMN_SPECS)

    def _ensure_default_columns(self, board_id: int) -> list[MutaBoardColumnData]:
        return self._db.replace_mutaboard_columns(board_id, self._default_column_specs())

    @staticmethod
    def _display_column_title(column: MutaBoardColumnData) -> str:
        title = str(column.title or "").strip()
        if title:
            return title
        return _COLUMN_KIND_LABELS.get(column.kind, column.kind)

    def _synthetic_cards_for_kind(self, board: MutaBoardData | None, kind: str) -> list[ConceptBoardCard]:
        if board is None:
            return []
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
        if card is None or card.entity_kind not in {"version", "solution"}:
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
        capture_text = self._scenario_editors["capture"].toPlainText().strip()
        if not capture_text:
            self.set_status("Концептборд: сначала сформулируйте текущее решение.")
            return
        updated = self._append_unique_line(self._scenario_editors["links"].toPlainText(), "Подготовить реализацию решения")
        self._scenario_editors["links"].setPlainText(updated)
        self._refresh_outcome_summary()
        self.set_status("Концептборд: решение помечено как принятое.")

    def _send_current_solution_to_review(self) -> None:
        capture_text = self._scenario_editors["capture"].toPlainText().strip()
        if not capture_text:
            self.set_status("Концептборд: сначала сформулируйте решение для проверки.")
            return
        updated = self._append_unique_line(self._scenario_editors["planning"].toPlainText(), "Проверить понятность решения")
        self._scenario_editors["planning"].setPlainText(updated)
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
        self._refresh_outcome_summary()
        self.set_status("Концептборд: следующие задачи собраны из решения.")

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
        self._refresh_mutaboards()
        self._refresh_status()

    def on_enter(self, context: dict | None = None) -> None:
        super().on_enter(context)
        self._populate_board()
        self._refresh_status()

    def _refresh_mutaboards(self) -> None:
        boards = self._db.fetch_mutaboards()
        if not boards:
            created = self._db.create_mutaboard("Концептборд 1", column_kinds=_DEFAULT_COLUMN_KINDS)
            self._ensure_default_columns(created.id)
            boards = self._db.fetch_mutaboards()
        current_id = self._current_mutaboard_id()
        self._mutaboards_by_id = {board.id: board for board in boards}

        self.mutaboard_list.blockSignals(True)
        self.mutaboard_list.clear()
        for board in boards:
            attached_count = len(self._db.fetch_mutaboard_items(board.id))
            updated_text = board.updated_at.strftime("%d.%m.%Y")
            item = QListWidgetItem(board.title)
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
            self.mutaboard_list.addItem(item)
        self.mutaboard_list.blockSignals(False)

        restore_id = current_id if current_id in self._mutaboards_by_id else boards[0].id
        for index in range(self.mutaboard_list.count()):
            item = self.mutaboard_list.item(index)
            if item.data(Qt.ItemDataRole.UserRole) != restore_id:
                continue
            self.mutaboard_list.setCurrentItem(item)
            break
        self._load_current_mutaboard()

    def _on_mutaboard_selection_changed(self) -> None:
        self._load_current_mutaboard()
        self._rebuild_board_columns()
        self._populate_board()
        self._refresh_status()

    def _current_mutaboard_id(self) -> int | None:
        item = self.mutaboard_list.currentItem()
        board_id = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
        return board_id if isinstance(board_id, int) else None

    def _current_mutaboard(self) -> MutaBoardData | None:
        board_id = self._current_mutaboard_id()
        if board_id is None:
            return None
        return self._mutaboards_by_id.get(board_id)

    def _create_mutaboard(self) -> None:
        next_index = len(self._mutaboards_by_id) + 1
        created = self._db.create_mutaboard(f"Концептборд {next_index}", column_kinds=_DEFAULT_COLUMN_KINDS)
        self._ensure_default_columns(created.id)
        self._model.reload()
        self._refresh_mutaboards()
        self._select_mutaboard(created.id)
        self.set_status(f"Концептборд: создан «{created.title}».")

    def _select_mutaboard(self, mutaboard_id: int) -> None:
        for index in range(self.mutaboard_list.count()):
            item = self.mutaboard_list.item(index)
            if item.data(Qt.ItemDataRole.UserRole) != mutaboard_id:
                continue
            self.mutaboard_list.setCurrentItem(item)
            break

    def _load_current_mutaboard(self) -> None:
        board = self._current_mutaboard()
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

    def _save_current_mutaboard(self) -> None:
        board = self._current_mutaboard()
        if board is None:
            self.set_status("Концептборд: сначала выберите доску.")
            return
        updated = self._db.update_mutaboard(
            board.id,
            title=self.focus_title_input.text(),
            description=self.focus_description_input.toPlainText(),
            capture_text=self._scenario_editors["capture"].toPlainText(),
            planning_text=self._scenario_editors["planning"].toPlainText(),
            links_text=self._scenario_editors["links"].toPlainText(),
        )
        self._mutaboards_by_id[updated.id] = updated
        self._refresh_mutaboards()
        self._select_mutaboard(updated.id)
        self._refresh_board_context(updated)
        self._refresh_outcome_summary()
        self._refresh_focus(None if self._selected_card_key is None else self._model.get_card(*self._selected_card_key))
        self.set_status(f"Концептборд: данные «{updated.title}» сохранены.")

    def _rebuild_board_columns(self) -> None:
        self._column_defs.clear()
        self._column_kinds.clear()
        self._column_lists.clear()
        self._column_count_labels.clear()
        self._column_title_labels.clear()
        while self.board_layout.count():
            item = self.board_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        board_id = self._current_mutaboard_id()
        if board_id is None:
            return
        columns = self._db.fetch_mutaboard_columns(board_id)
        if not columns:
            columns = self._ensure_default_columns(board_id)

        for column in columns:
            self._column_defs[column.id] = column
            self._column_kinds[column.id] = column.kind

            frame = QFrame(self.board_inner)
            frame.setObjectName("MutaBoardColumn")
            frame.setMinimumWidth(250)
            column_layout = QVBoxLayout(frame)
            column_layout.setContentsMargins(12, 12, 12, 12)
            column_layout.setSpacing(8)

            header_row = QHBoxLayout()
            header_row.setContentsMargins(0, 0, 0, 0)
            header_row.setSpacing(8)

            title_label = QLabel(self._display_column_title(column))
            title_label.setObjectName("MutaBoardScenarioTitle")
            header_row.addWidget(title_label, 1)
            self._column_title_labels[column.id] = title_label

            count_label = QLabel("0")
            count_label.setObjectName("MutaBoardColumnCount")
            header_row.addWidget(count_label, 0, Qt.AlignmentFlag.AlignRight)
            self._column_count_labels[column.id] = count_label
            column_layout.addLayout(header_row)

            kind_row = QHBoxLayout()
            kind_row.setContentsMargins(0, 0, 0, 0)
            kind_row.setSpacing(8)

            kind_combo = QComboBox(frame)
            kind_combo.setObjectName("MutaBoardColumnKindFilter")
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

            list_widget = _MutaBoardColumnListWidget(self, column.id, frame)
            list_widget.setObjectName("MutaBoardColumnList")
            list_widget.setItemDelegate(ConceptBoardDelegate(list_widget))
            list_widget.itemSelectionChanged.connect(
                lambda column_id=column.id: self._on_column_selection_changed(column_id)
            )
            column_layout.addWidget(list_widget, 1)

            add_button = QPushButton("+ Добавить", frame)
            add_button.setObjectName("MutaBoardSecondaryButton")
            add_button.setEnabled(False)
            add_button.setToolTip(_DISABLED_ACTION_TOOLTIP)
            column_layout.addWidget(add_button, 0, Qt.AlignmentFlag.AlignLeft)
            self._column_lists[column.id] = list_widget
            self.board_layout.addWidget(frame, 1)
        self.board_layout.addStretch(1)

    def _on_column_kind_changed(self, column_id: int, kind: object) -> None:
        if not isinstance(kind, str):
            return
        current = self._column_defs.get(column_id)
        if current is None or current.kind == kind:
            return
        updated = self._db.update_mutaboard_column(column_id, kind=kind, title=current.title, position=current.position)
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
        board_id = self._current_mutaboard_id()
        if board_id is None:
            self.set_status("Концептборд: сначала выберите доску.")
            return
        self._db.add_mutaboard_column(board_id, self._next_column_kind())
        self._refresh_mutaboards()
        self._select_mutaboard(board_id)
        self._rebuild_board_columns()
        self._populate_board()
        self._refresh_status()

    def _filtered_cards(self, entity_kind: str | None = None) -> list[ConceptBoardCard]:
        return self._model.filtered_cards(query=self.search_input.text(), entity_kind=entity_kind)

    def _populate_board(self) -> None:
        board_id = self._current_mutaboard_id()
        if board_id is None:
            return
        board = self._current_mutaboard()
        attached_items = self._db.fetch_mutaboard_items(board_id)
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

    def _refresh_structure(self, card: ConceptBoardCard | None) -> None:
        board = self._current_mutaboard()
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

    def _structure_overview_text(self, board: MutaBoardData | None) -> str:
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

    def _structure_detail_text(self, card: ConceptBoardCard, board: MutaBoardData | None) -> str:
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
        board = self._current_mutaboard()
        menu = QMenu(self)
        attach_action = menu.addAction("Связать с концептбордом")
        if board is None or (card.entity_kind, card.entity_id) in self._attached_card_keys:
            attach_action.setEnabled(board is not None and (card.entity_kind, card.entity_id) not in self._attached_card_keys)
        chosen = menu.exec(global_pos)
        if chosen is not attach_action or board is None:
            return
        self._db.attach_mutaboard_item(board.id, card.entity_kind, card.entity_id)
        self._populate_board()
        self._refresh_status()
        self.set_status(f"Концептборд: элемент «{card.title}» связан с «{board.title}».")

    def _refresh_status(self) -> None:
        total_count = len(self._model.cards())
        visible_count = sum(list_widget.count() for list_widget in self._column_lists.values())
        attached_count = len(self._attached_card_keys)
        if self.search_input.text().strip():
            self.set_status(f"Концептборд: элементов {visible_count} из {total_count} · связано {attached_count}.")
            return
        self.set_status(f"Концептборд: элементов {total_count} · связано {attached_count}.")

    def _apply_mutaboard_style(self) -> None:
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
            QWidget#MutaBoardRoot {{
                border: none;
                border-radius: 0px;
                padding: 0px;
                background: {shell_bg};
            }}
            QFrame#MutaBoardListPanel,
            QFrame#MutaBoardBoardWrap,
            QFrame#MutaBoardBoardHeader,
            QFrame#MutaBoardFocusPanel,
            QFrame#MutaBoardInsightPanel,
            QFrame#MutaBoardScenarioCard,
            QFrame#MutaBoardColumn {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {shell_panel}, stop:1 {shell_panel_alt});
                border: 1px solid {shell_border};
                border-radius: 18px;
            }}
            QScrollArea#MutaBoardScroll,
            QWidget#MutaBoardColumnsHost,
            QWidget#MutaBoardRoot QSplitter {{
                background: transparent;
                border: none;
            }}
            QTabWidget#MutaBoardTabs::pane {{
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
            QSplitter#MutaBoardSplitter::handle {{
                background: rgba(255, 255, 255, 0.04);
                width: 6px;
                margin: 10px 0;
                border-radius: 3px;
            }}
            QWidget#MutaBoardRoot QLabel {{
                color: {shell_text};
                background: transparent;
            }}
            QLabel#MutaBoardListTitle,
            QLabel#MutaBoardInsightTitle,
            QLabel#MutaBoardBoardHeadline,
            QLabel#MutaBoardInspectorTitle {{
                color: {shell_text};
                font-size: 19px;
                font-weight: 700;
            }}
            QLabel#MutaBoardListSubtitle,
            QLabel#MutaBoardInsightBody,
            QLabel#MutaBoardBoardCaption,
            QLabel#MutaBoardColumnCount,
            QLabel#MutaBoardScenarioTitle,
            QLabel#MutaBoardNodeMuted,
            QLabel#MutaBoardNodeTask,
            QLabel#MutaBoardNodeIdea,
            QLabel#MutaBoardNodeObject,
            QLabel#MutaBoardNodeHub {{
                color: {shell_dim_text};
            }}
            QListWidget#MutaBoardList,
            QListWidget#MutaBoardColumnList,
            QTextEdit#MutaBoardFocusDescription,
            QTextEdit#MutaBoardScenarioEditor,
            QLineEdit#MutaBoardFocusTitle,
            QComboBox#MutaBoardColumnKindFilter {{
                background: {shell_input};
                color: {shell_text};
                border: 1px solid {shell_border};
                border-radius: 12px;
                padding: 8px 10px;
            }}
            QListWidget#MutaBoardList::viewport,
            QListWidget#MutaBoardColumnList::viewport,
            QTextEdit#MutaBoardFocusDescription,
            QTextEdit#MutaBoardFocusDescription QWidget,
            QTextEdit#MutaBoardScenarioEditor,
            QTextEdit#MutaBoardScenarioEditor QWidget {{
                background: {shell_input};
                color: {shell_text};
            }}
            QComboBox#MutaBoardColumnKindFilter::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox#MutaBoardColumnKindFilter QAbstractItemView,
            QMenu {{
                background: {shell_panel_alt};
                color: {shell_text};
                border: 1px solid {shell_border};
                border-radius: 12px;
                padding: 6px;
            }}
            QComboBox#MutaBoardColumnKindFilter QAbstractItemView::item,
            QMenu::item {{
                background: transparent;
                color: {shell_text};
                padding: 8px 10px;
                border-radius: 8px;
            }}
            QComboBox#MutaBoardColumnKindFilter QAbstractItemView::item:selected,
            QMenu::item:selected {{
                background: rgba(111, 140, 255, 0.18);
            }}
            QListWidget#MutaBoardList::item:selected,
            QListWidget#MutaBoardColumnList::item:selected {{
                background: rgba(111, 140, 255, 0.18);
            }}
            QPushButton#MutaBoardPrimaryButton,
            QPushButton#MutaBoardSecondaryButton {{
                background: {shell_input};
                color: {shell_text};
                border: 1px solid {shell_border};
                border-radius: 12px;
                padding: 9px 14px;
            }}
            QPushButton#MutaBoardPrimaryButton:hover,
            QPushButton#MutaBoardSecondaryButton:hover,
            QTextEdit#MutaBoardFocusDescription:hover,
            QTextEdit#MutaBoardScenarioEditor:hover,
            QLineEdit#MutaBoardFocusTitle:hover,
            QComboBox#MutaBoardColumnKindFilter:hover {{
                background: {shell_input_hover};
            }}
            QPushButton#MutaBoardPrimaryButton:disabled,
            QPushButton#MutaBoardSecondaryButton:disabled {{
                color: {shell_dim_text};
                border-color: rgba(37, 49, 66, 0.7);
            }}
            QFrame#MutaBoardStructureGraph {{
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid {shell_border};
                border-radius: 16px;
            }}
            QLabel#MutaBoardNodeHub,
            QLabel#MutaBoardNodeIdea,
            QLabel#MutaBoardNodeTask,
            QLabel#MutaBoardNodeObject,
            QLabel#MutaBoardNodeMuted {{
                border: 1px solid {shell_border};
                border-radius: 16px;
                padding: 10px 12px;
                background: rgba(255, 255, 255, 0.04);
            }}
            QLabel#MutaBoardNodeHub {{
                color: {shell_text};
                background: rgba(111, 140, 255, 0.18);
            }}
            """
        )


MutaBoardWorkspace = ConceptBoardWorkspace

__all__ = ["ConceptBoardWorkspace", "MutaBoardWorkspace"]
