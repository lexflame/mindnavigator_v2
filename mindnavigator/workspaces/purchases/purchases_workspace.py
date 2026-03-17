"""PurchasesWorkspace class module for purchases workspace."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403
from ._shop_parse_worker import _ShopParseWorker
from mindnavigator.ui.styles import get_theme_palette

class PurchasesWorkspace(BaseWorkspace):
    workspace_id = "purchases"
    workspace_title = "Покупки"

    def __init__(self, parent: QWidget | None = None) -> None:
        self._db = get_database()
        self._theme_mode = "dark"
        self._smooth_scroll_controllers: list[object] = []
        self._current_item_id: int | None = None
        self._current_source_id: int | None = None
        self._items_cache: dict[int, dict] = {}
        self._parse_pool = QThreadPool.globalInstance()
        self._parse_pool.setMaxThreadCount(24)
        self._http = HttpClient(
            timeout=15.0,
            max_retries=2,
            backoff_seconds=1.5,
            user_agent="MindNavigator/ShopParser",
            on_error=self._set_status,
        )
        self._stop_updates = False
        self._parse_service = ShopParseService(self._db, build_default_parsers(self._http))
        super().__init__(parent)
        self.setObjectName("PurchasesWorkspace")
        self.search_input.setPlaceholderText("Поиск по товарам…")
        self._set_status("Готово к добавлению URL")

    def _build_ui(self) -> None:
        super()._build_ui()

        quick_in_stock = QCheckBox("В наличии")
        quick_in_stock.setObjectName("PurchasesQuickInStock")
        quick_recent = QCheckBox("Свежие цены")
        quick_recent.setObjectName("PurchasesQuickRecent")
        self.filter_layout.addWidget(QLabel("Быстрые фильтры"))
        self.filter_layout.addWidget(quick_in_stock)
        self.filter_layout.addWidget(quick_recent)
        self.filter_layout.addStretch(1)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("PurchasesSplitter")

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)
        left_layout.addWidget(QLabel("Категории"))

        self.category_search = QLineEdit()
        self.category_search.setPlaceholderText("Фильтр категорий…")
        left_layout.addWidget(self.category_search)

        self.category_tree = QTreeWidget()
        self.category_tree.setHeaderHidden(True)
        self.category_tree.setObjectName("PurchasesCategoryTree")
        self.category_tree.itemSelectionChanged.connect(self._on_category_selected)
        category_controls = QHBoxLayout()
        self.category_add_btn = QToolButton()
        self.category_add_btn.setText("Добавить")
        self.category_add_btn.setIcon(qta.icon("fa5s.plus", color="#cfcfcf"))
        self.category_rename_btn = QToolButton()
        self.category_rename_btn.setText("Переименовать")
        self.category_rename_btn.setIcon(qta.icon("fa5s.edit", color="#cfcfcf"))
        self.category_delete_btn = QToolButton()
        self.category_delete_btn.setText("Удалить")
        self.category_delete_btn.setIcon(qta.icon("fa5s.trash", color="#cfcfcf"))
        category_controls.addWidget(self.category_add_btn)
        category_controls.addWidget(self.category_rename_btn)
        category_controls.addWidget(self.category_delete_btn)
        category_controls.addStretch(1)
        left_layout.addLayout(category_controls)
        left_layout.addWidget(self.category_tree, 1)

        splitter.addWidget(left_panel)

        center_panel = QWidget()
        center_layout = QVBoxLayout(center_panel)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(8)

        center_header = QHBoxLayout()
        center_header.addWidget(QLabel("Товары"))
        self.items_count = QLabel("0")
        self.items_count.setObjectName("PurchasesItemsCount")
        center_header.addStretch(1)
        center_header.addWidget(self.items_count)
        center_layout.addLayout(center_header)

        self.items_table = QTableWidget(0, 5)
        self.items_table.setObjectName("PurchasesItemsTable")
        self.items_table.setHorizontalHeaderLabels(
            ["Товар", "Категория", "Лучшая цена", "Источники", "Актуальность"]
        )
        self.items_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.items_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.items_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.items_table.horizontalHeader().setStretchLastSection(True)
        self.items_table.verticalHeader().setVisible(False)
        self.items_table.setSortingEnabled(True)
        self.items_table.itemSelectionChanged.connect(self._on_item_selected)
        self.items_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.items_table.customContextMenuRequested.connect(self._show_items_context_menu)
        center_layout.addWidget(self.items_table, 1)

        splitter.addWidget(center_panel)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        add_box = QGroupBox("Добавить по URL")
        add_box.setObjectName("PurchasesAddBox")
        add_layout = QHBoxLayout(add_box)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://магазин/товар")
        self.url_parse_btn = QToolButton()
        self.url_parse_btn.setText("Парсить")
        self.url_parse_btn.clicked.connect(self._open_add_url_dialog)
        add_layout.addWidget(self.url_input, 1)
        add_layout.addWidget(self.url_parse_btn)
        right_layout.addWidget(add_box)

        self.card_tabs = QTabWidget()
        self.card_tabs.setObjectName("PurchasesCardTabs")

        details_tab = QWidget()
        details_layout = QFormLayout(details_tab)
        details_layout.setContentsMargins(12, 12, 12, 12)
        details_layout.setSpacing(8)
        self.detail_title = QLineEdit()
        self.detail_title.setReadOnly(True)
        self.detail_category = QLineEdit()
        self.detail_category.setReadOnly(True)
        self.detail_price = QLineEdit()
        self.detail_price.setReadOnly(True)
        self.detail_notes = QPlainTextEdit()
        self.detail_notes.setReadOnly(True)
        details_layout.addRow("Название", self.detail_title)
        details_layout.addRow("Категория", self.detail_category)
        details_layout.addRow("Лучшая цена", self.detail_price)
        details_layout.addRow("Заметки", self.detail_notes)
        self.card_tabs.addTab(details_tab, "Детали")

        sources_tab = QWidget()
        sources_layout = QVBoxLayout(sources_tab)
        sources_layout.setContentsMargins(12, 12, 12, 12)
        sources_layout.setSpacing(8)
        sources_toolbar = QHBoxLayout()
        self.source_update_btn = QToolButton()
        self.source_update_btn.setText("Обновить")
        self.source_update_btn.setIcon(qta.icon("fa5s.sync", color="#cfcfcf"))
        self.source_open_btn = QToolButton()
        self.source_open_btn.setText("Открыть")
        self.source_open_btn.setIcon(qta.icon("fa5s.external-link-alt", color="#cfcfcf"))
        self.source_delete_btn = QToolButton()
        self.source_delete_btn.setText("Удалить")
        self.source_delete_btn.setIcon(qta.icon("fa5s.trash", color="#cfcfcf"))
        self.source_raw_btn = QToolButton()
        self.source_raw_btn.setText("Raw JSON")
        self.source_raw_btn.setIcon(qta.icon("fa5s.code", color="#cfcfcf"))
        self.source_diag_btn = QToolButton()
        self.source_diag_btn.setText("Диагностика")
        self.source_diag_btn.setIcon(qta.icon("fa5s.bug", color="#cfcfcf"))
        sources_toolbar.addWidget(self.source_update_btn)
        sources_toolbar.addWidget(self.source_open_btn)
        sources_toolbar.addWidget(self.source_delete_btn)
        sources_toolbar.addWidget(self.source_raw_btn)
        sources_toolbar.addWidget(self.source_diag_btn)
        sources_toolbar.addStretch(1)
        sources_layout.addLayout(sources_toolbar)
        self.sources_table = QTableWidget(0, 5)
        self.sources_table.setHorizontalHeaderLabels(["Магазин", "URL", "Цена", "Наличие", "Артикул"])
        self.sources_table.horizontalHeader().setStretchLastSection(True)
        self.sources_table.verticalHeader().setVisible(False)
        self.sources_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.sources_table.itemSelectionChanged.connect(self._on_source_selected)
        sources_layout.addWidget(self.sources_table, 1)
        self.card_tabs.addTab(sources_tab, "Источники")

        properties_tab = QWidget()
        properties_layout = QVBoxLayout(properties_tab)
        properties_layout.setContentsMargins(12, 12, 12, 12)
        properties_layout.setSpacing(8)

        prop_toolbar = QHBoxLayout()
        self.prop_accept_btn = QToolButton()
        self.prop_accept_btn.setText("Принять в свойства товара")
        self.prop_accept_btn.setIcon(qta.icon("fa5s.check", color="#cfcfcf"))
        self.prop_delete_btn = QToolButton()
        self.prop_delete_btn.setText("Удалить свойство товара")
        self.prop_delete_btn.setIcon(qta.icon("fa5s.trash-alt", color="#cfcfcf"))
        prop_toolbar.addWidget(self.prop_accept_btn)
        prop_toolbar.addWidget(self.prop_delete_btn)
        prop_toolbar.addStretch(1)
        properties_layout.addLayout(prop_toolbar)

        props_split = QSplitter(Qt.Orientation.Horizontal)
        source_props_block = QWidget()
        source_props_layout = QVBoxLayout(source_props_block)
        source_props_layout.setContentsMargins(0, 0, 0, 0)
        source_props_layout.setSpacing(6)
        source_props_layout.addWidget(QLabel("Свойства источника"))
        self.source_props_table = QTableWidget(0, 4)
        self.source_props_table.setHorizontalHeaderLabels(["Имя", "Значение", "Ед.", "Ключ"])
        self.source_props_table.horizontalHeader().setStretchLastSection(True)
        self.source_props_table.verticalHeader().setVisible(False)
        self.source_props_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.source_props_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        source_props_layout.addWidget(self.source_props_table, 1)
        props_split.addWidget(source_props_block)

        item_props_block = QWidget()
        item_props_layout = QVBoxLayout(item_props_block)
        item_props_layout.setContentsMargins(0, 0, 0, 0)
        item_props_layout.setSpacing(6)
        item_props_layout.addWidget(QLabel("Свойства товара"))
        self.item_props_table = QTableWidget(0, 4)
        self.item_props_table.setHorizontalHeaderLabels(["Имя", "Значение", "Ед.", "Ключ"])
        self.item_props_table.horizontalHeader().setStretchLastSection(True)
        self.item_props_table.verticalHeader().setVisible(False)
        self.item_props_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        item_props_layout.addWidget(self.item_props_table, 1)
        props_split.addWidget(item_props_block)

        props_split.setStretchFactor(0, 1)
        props_split.setStretchFactor(1, 1)
        properties_layout.addWidget(props_split, 1)
        self.card_tabs.addTab(properties_tab, "Свойства")

        history_tab = QWidget()
        history_layout = QVBoxLayout(history_tab)
        history_layout.setContentsMargins(12, 12, 12, 12)
        history_layout.setSpacing(8)
        self.history_label = QLabel("Выберите источник для расчёта истории цен.")
        history_layout.addWidget(self.history_label)
        self.card_tabs.addTab(history_tab, "История цен")

        wishlist_tab = QWidget()
        self.wishlist_tab = wishlist_tab
        wishlist_layout = QVBoxLayout(wishlist_tab)
        wishlist_layout.setContentsMargins(12, 12, 12, 12)
        wishlist_layout.setSpacing(8)

        wishlist_header = QHBoxLayout()
        self.wishlist_combo = QComboBox()
        self.wishlist_add_btn = QToolButton()
        self.wishlist_add_btn.setText("Новый список")
        self.wishlist_add_btn.setIcon(qta.icon("fa5s.plus", color="#cfcfcf"))
        self.wishlist_delete_btn = QToolButton()
        self.wishlist_delete_btn.setText("Удалить список")
        self.wishlist_delete_btn.setIcon(qta.icon("fa5s.trash", color="#cfcfcf"))
        wishlist_header.addWidget(QLabel("Список"))
        wishlist_header.addWidget(self.wishlist_combo, 1)
        wishlist_header.addWidget(self.wishlist_add_btn)
        wishlist_header.addWidget(self.wishlist_delete_btn)
        wishlist_layout.addLayout(wishlist_header)

        add_row = QHBoxLayout()
        self.wishlist_qty = QSpinBox()
        self.wishlist_qty.setRange(1, 999)
        self.wishlist_qty.setValue(1)
        self.wishlist_priority = QSpinBox()
        self.wishlist_priority.setRange(1, 5)
        self.wishlist_priority.setValue(3)
        self.wishlist_target = QDoubleSpinBox()
        self.wishlist_target.setRange(0, 1_000_000)
        self.wishlist_target.setDecimals(2)
        self.wishlist_add_item_btn = QToolButton()
        self.wishlist_add_item_btn.setText("Добавить товар")
        self.wishlist_add_item_btn.setIcon(qta.icon("fa5s.cart-plus", color="#cfcfcf"))
        add_row.addWidget(QLabel("Кол-во"))
        add_row.addWidget(self.wishlist_qty)
        add_row.addWidget(QLabel("Приоритет"))
        add_row.addWidget(self.wishlist_priority)
        add_row.addWidget(QLabel("Цель"))
        add_row.addWidget(self.wishlist_target)
        add_row.addWidget(self.wishlist_add_item_btn)
        add_row.addStretch(1)
        wishlist_layout.addLayout(add_row)

        self.wishlist_table = QTableWidget(0, 5)
        self.wishlist_table.setHorizontalHeaderLabels(
            ["Товар", "Кол-во", "Приоритет", "Цель", "Источник"]
        )
        self.wishlist_table.horizontalHeader().setStretchLastSection(True)
        self.wishlist_table.verticalHeader().setVisible(False)
        self.wishlist_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        wishlist_layout.addWidget(self.wishlist_table, 1)

        self.wishlist_summary = QLabel("Итого: —")
        wishlist_layout.addWidget(self.wishlist_summary)

        self.card_tabs.addTab(wishlist_tab, "Хотелки")

        right_layout.addWidget(self.card_tabs, 1)

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        splitter.setStretchFactor(2, 2)

        self.set_content(splitter)
        self._smooth_scroll_controllers = [
            attach_smooth_scroll(self.category_tree),
            attach_smooth_scroll(self.items_table),
            attach_smooth_scroll(self.detail_notes),
            attach_smooth_scroll(self.sources_table),
            attach_smooth_scroll(self.source_props_table),
            attach_smooth_scroll(self.item_props_table),
            attach_smooth_scroll(self.wishlist_table),
        ]
        self._load_categories()
        self.refresh()

        self.source_update_btn.clicked.connect(self._update_selected_source)
        self.source_open_btn.clicked.connect(self._open_selected_source)
        self.source_delete_btn.clicked.connect(self._delete_selected_source)
        self.source_raw_btn.clicked.connect(self._show_selected_source_raw)
        self.source_diag_btn.clicked.connect(self._show_selected_source_diagnostics)
        self.prop_accept_btn.clicked.connect(self._accept_property_to_item)
        self.prop_delete_btn.clicked.connect(self._delete_item_property)
        self.wishlist_add_btn.clicked.connect(self._create_wishlist)
        self.wishlist_delete_btn.clicked.connect(self._delete_wishlist)
        self.wishlist_add_item_btn.clicked.connect(self._add_item_to_wishlist)
        self.wishlist_combo.currentIndexChanged.connect(self._load_wishlist_items)
        self._load_wishlists()
        self.category_add_btn.clicked.connect(self._add_category)
        self.category_rename_btn.clicked.connect(self._rename_category)
        self.category_delete_btn.clicked.connect(self._delete_category)

        self.set_theme_mode("dark")

    def set_theme_mode(self, theme_mode: str) -> None:
        self._theme_mode = "light" if str(theme_mode).strip().lower() == "light" else "dark"
        palette = get_theme_palette(self._theme_mode)
        self.setStyleSheet(
            f"""
            QWidget#PurchasesWorkspace {{ background: {palette.window_bg}; }}
            QWidget#PurchasesWorkspace QLabel {{ color: {palette.text}; }}
            QWidget#PurchasesWorkspace QTableWidget,
            QWidget#PurchasesWorkspace QTableWidget QLineEdit,
            QWidget#PurchasesWorkspace QTableWidget QAbstractItemView,
            QWidget#PurchasesWorkspace QTreeWidget,
            QWidget#PurchasesWorkspace QTreeWidget QAbstractItemView,
            QWidget#PurchasesWorkspace QComboBox,
            QWidget#PurchasesWorkspace QLineEdit,
            QWidget#PurchasesWorkspace QPlainTextEdit {{
                color: {palette.text};
            }}
            QWidget#PurchasesWorkspace QWidget#WorkspaceToolbar,
            QWidget#PurchasesWorkspace QWidget#WorkspaceSearch,
            QWidget#PurchasesWorkspace QWidget#WorkspaceFilters {{
                background: {palette.panel_bg};
                border: 1px solid {palette.border};
                border-radius: 10px;
                padding: 6px;
            }}
            QWidget#PurchasesWorkspace QWidget#WorkspaceStatus {{ color: {palette.dim_text}; }}
            QWidget#PurchasesWorkspace QToolButton {{
                color: {palette.text};
                background: {palette.elevated_bg};
                border: 1px solid {palette.border_strong};
                padding: 8px 12px;
                border-radius: 6px;
                min-height: 28px;
            }}
            QWidget#PurchasesWorkspace QToolButton:hover {{
                background: {palette.selection_bg};
                color: {palette.selection_text};
            }}
            QWidget#PurchasesWorkspace QLineEdit,
            QWidget#PurchasesWorkspace QPlainTextEdit,
            QWidget#PurchasesWorkspace QComboBox {{
                background: {palette.input_bg};
                color: {palette.text};
                border: 1px solid {palette.border};
                padding: 6px 8px;
                border-radius: 6px;
            }}
            QWidget#PurchasesWorkspace QCheckBox {{
                color: {palette.text};
            }}
            QTreeWidget#PurchasesCategoryTree {{
                background: {palette.window_bg};
                border: 1px solid {palette.border};
                border-radius: 8px;
                padding: 4px;
            }}
            QTableWidget#PurchasesItemsTable,
            QTableWidget {{
                background: {palette.window_bg};
                border: 1px solid {palette.border};
                border-radius: 8px;
                color: {palette.text};
            }}
            QTableWidget::horizontalHeader {{
                background: {palette.panel_alt_bg};
            }}
            QHeaderView::section {{
                color: {palette.text};
                background: {palette.panel_alt_bg};
                border: 1px solid {palette.border_strong};
                padding: 6px;
            }}
            QTableWidget::item:hover {{
                background: {palette.elevated_bg};
            }}
            QTableWidget::item:selected {{
                background: {palette.selection_bg};
                color: {palette.selection_text};
            }}
            QTabWidget#PurchasesCardTabs::pane {{
                border: 1px solid {palette.border};
                background: {palette.panel_bg};
                border-radius: 10px;
                padding: 6px;
            }}
            QTabWidget#PurchasesCardTabs QTabBar::tab {{
                background: {palette.input_bg};
                color: {palette.text};
                padding: 6px 12px;
                margin-right: 4px;
                border-radius: 6px;
            }}
            QTabWidget#PurchasesCardTabs QTabBar::tab:selected {{
                background: {palette.selection_bg};
                color: {palette.selection_text};
            }}
            QGroupBox#PurchasesAddBox {{
                border: 1px solid {palette.border};
                border-radius: 8px;
                margin-top: 10px;
                color: {palette.text};
            }}
            QGroupBox#PurchasesAddBox::title {{
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px 0 4px;
            }}
            QLineEdit[readOnly="true"],
            QPlainTextEdit[readOnly="true"] {{
                background: {palette.panel_alt_bg};
                color: {palette.text};
                border: 1px solid {palette.border};
                border-radius: 6px;
            }}
        """
        )

    def create_actions(self) -> dict[str, QAction]:
        action_add = QAction("Добавить по URL", self)
        action_add.setIcon(qta.icon("fa5s.link", color="#cfcfcf"))
        action_add.triggered.connect(self._open_add_url_dialog)
        action_refresh = QAction("Обновить данные", self)
        action_refresh.setIcon(qta.icon("fa5s.sync", color="#cfcfcf"))
        action_refresh.triggered.connect(self._refresh_sources_bulk)
        action_edit = QAction("Редактировать", self)
        action_edit.setIcon(qta.icon("fa5s.edit", color="#cfcfcf"))
        action_edit.triggered.connect(self._edit_selected_item)
        action_delete = QAction("Удалить товар", self)
        action_delete.setIcon(qta.icon("fa5s.trash", color="#cfcfcf"))
        action_delete.triggered.connect(self._delete_selected_item)
        action_compare = QAction("В сравнение", self)
        action_compare.setIcon(qta.icon("fa5s.balance-scale", color="#cfcfcf"))
        action_compare.triggered.connect(self._open_compare_dialog)
        action_wishlist = QAction("В хотелки", self)
        action_wishlist.setIcon(qta.icon("fa5s.heart", color="#cfcfcf"))
        action_wishlist.triggered.connect(self._open_wishlist_tab)
        action_export = QAction("Экспорт", self)
        action_export.setIcon(qta.icon("fa5s.file-export", color="#cfcfcf"))
        action_export.triggered.connect(self._export_purchases)
        action_import = QAction("Импорт", self)
        action_import.setIcon(qta.icon("fa5s.file-import", color="#cfcfcf"))
        action_import.triggered.connect(self._import_purchases)
        action_stop = QAction("Стоп", self)
        action_stop.setIcon(qta.icon("fa5s.stop-circle", color="#cfcfcf"))
        action_stop.triggered.connect(self._stop_updates_request)
        return {
            "add_url": action_add,
            "refresh": action_refresh,
            "edit": action_edit,
            "delete": action_delete,
            "compare": action_compare,
            "wishlist": action_wishlist,
            "export": action_export,
            "import": action_import,
            "stop": action_stop,
        }

    def get_selection(self):
        return self._current_item_id

    def _open_add_url_dialog(self) -> None:
        dialog = PurchaseAddByUrlDialog(self._db, self)
        if exec_with_overlay(dialog, self) != QDialog.DialogCode.Accepted:
            return
        result = dialog.result_payload()
        if result is None:
            return
        self._load_categories()
        self.refresh()
        self._select_item_by_id(result.item.id)
        self._set_status("Товар добавлен")

    def _open_compare_dialog(self) -> None:
        selected_rows = self.items_table.selectionModel().selectedRows()
        if len(selected_rows) == 2:
            item_ids = []
            for index in selected_rows:
                item = self.items_table.item(index.row(), 0)
                if item is None:
                    continue
                item_id = item.data(Qt.ItemDataRole.UserRole)
                if item_id is not None:
                    item_ids.append(int(item_id))
            if len(item_ids) == 2:
                dialog = PurchaseCompareDialog(self._db, item_ids=item_ids, parent=self)
                dialog.exec()
                return
        category_id = None
        if selected_rows:
            for index in selected_rows:
                item = self.items_table.item(index.row(), 0)
                if item is None:
                    continue
                item_id = item.data(Qt.ItemDataRole.UserRole)
                if item_id is None:
                    continue
                item_row = self._db.get_shop_item(int(item_id))
                if item_row is None:
                    continue
                if category_id is None:
                    category_id = item_row.category_id
                elif category_id != item_row.category_id:
                    self._set_status("Сравнение возможно только внутри одной категории")
                    break
                self._db.add_shop_compare_item(item_row.id, category_id)
        dialog = PurchaseCompareDialog(self._db, category_id=category_id, parent=self)
        dialog.exec()

    def _edit_selected_item(self) -> None:
        if self._current_item_id is None:
            self._set_status("Товар не выбран")
            return
        item = self._db.get_shop_item(self._current_item_id)
        if item is None:
            self._set_status("Товар не найден")
            return
        dialog = PurchaseEditDialog(self._db, item, parent=self)
        if exec_with_overlay(dialog, self) != QDialog.DialogCode.Accepted:
            return
        payload = dialog.payload()
        self._db.update_shop_item(
            item.id,
            title=payload["title"],
            category_id=payload["category_id"],
            user_notes=payload["user_notes"],
        )
        self._load_categories()
        self.refresh()
        self._select_item_by_id(item.id)
        self._set_status("Товар обновлён")

    def _delete_selected_item(self) -> None:
        if self._current_item_id is None:
            self._set_status("Товар не выбран")
            return
        dialog = ConfirmDialog(
            "Удалить товар",
            "Удалить выбранный товар и все его источники?",
            parent=self,
            confirm_text="Удалить",
            cancel_text="Отмена",
        )
        if exec_with_overlay(dialog, self) != QDialog.DialogCode.Accepted:
            return
        self._db.delete_shop_item(self._current_item_id)
        self._current_item_id = None
        self.refresh()
        self._set_status("Товар удалён")

    def _show_items_context_menu(self, pos) -> None:
        index = self.items_table.indexAt(pos)
        if not index.isValid():
            return
        row = index.row()
        item = self.items_table.item(row, 0)
        if item is None:
            return
        item_id = item.data(Qt.ItemDataRole.UserRole)
        if item_id is None:
            return
        if not self.items_table.selectionModel().isRowSelected(row, self.items_table.rootIndex()):
            self.items_table.selectRow(row)
        menu = QMenu(self)
        action_open = menu.addAction("Открыть источник")
        action_edit = menu.addAction("Редактировать")
        action_compare = menu.addAction("В сравнение")
        action_compare_two = menu.addAction("Сравнить два")
        action_wishlist = menu.addAction("В хотелки")
        menu.addSeparator()
        action_delete = menu.addAction("Удалить")
        action = menu.exec(self.items_table.viewport().mapToGlobal(pos))
        if action == action_open:
            self._open_first_source_for_item(int(item_id))
        elif action == action_edit:
            self._current_item_id = int(item_id)
            self._edit_selected_item()
        elif action == action_compare:
            self._current_item_id = int(item_id)
            self._open_compare_dialog()
        elif action == action_compare_two:
            selected_rows = self.items_table.selectionModel().selectedRows()
            if len(selected_rows) != 2:
                self._set_status("Выберите 2 товара")
                return
            self._open_compare_dialog()
        elif action == action_wishlist:
            self._current_item_id = int(item_id)
            self._open_wishlist_tab()
        if action == action_delete:
            self._delete_selected_item()

    def _open_first_source_for_item(self, item_id: int) -> None:
        sources = self._db.fetch_shop_sources(item_id)
        if not sources:
            self._set_status("Нет источников для открытия")
            return
        QDesktopServices.openUrl(QUrl(sources[0].url))

    def _open_wishlist_tab(self) -> None:
        if self.wishlist_tab is None:
            return
        self.card_tabs.setCurrentIndex(self.card_tabs.indexOf(self.wishlist_tab))

    def _export_purchases(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Экспорт данных покупок",
            "purchases_export.json",
            "JSON (*.json)",
        )
        if not path:
            return
        payload = self._db.export_purchases_data()
        try:
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
            self._set_status("Экспорт завершён")
        except OSError as exc:
            self._set_status(f"Ошибка экспорта: {exc}")

    def _import_purchases(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Импорт данных покупок",
            "",
            "JSON (*.json)",
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            self._set_status(f"Ошибка импорта: {exc}")
            return
        self._db.import_purchases_data(payload)
        self.refresh()
        self._load_categories()
        self._load_wishlists()
        self._set_status("Импорт завершён")

    def _set_status(self, text: str) -> None:
        self.set_status(text)

    def _add_item_row(
        self,
        title: str,
        category: str,
        best_price: str,
        sources: str,
        freshness: str,
        freshness_color: QColor | None = None,
        freshness_tip: str = "",
        item_id: int | None = None,
    ) -> None:
        row = self.items_table.rowCount()
        self.items_table.insertRow(row)
        for col, value in enumerate([title, category, best_price, sources, freshness]):
            item = QTableWidgetItem(value)
            if col == 0 and item_id is not None:
                item.setData(Qt.ItemDataRole.UserRole, item_id)
            if col == 3 and value == "0":
                item.setForeground(QColor("#ff6b6b"))
            if col == 4:
                if freshness_color is not None:
                    item.setForeground(freshness_color)
                if freshness_tip:
                    item.setToolTip(freshness_tip)
            self.items_table.setItem(row, col, item)
        self.items_count.setText(f"{self.items_table.rowCount()} товаров")

    def refresh(self) -> None:
        self.items_table.setSortingEnabled(False)
        current = self.category_tree.currentItem()
        category_id = current.data(0, Qt.ItemDataRole.UserRole) if current is not None else None
        items = self._db.fetch_shop_items_with_stats(
            search_text=self.search_input.text(),
            category_id=category_id,
        )
        self._items_cache = {item["id"]: item for item in items}
        self.items_table.setRowCount(0)
        for row in items:
            best_price = row["best_price"]
            price_text = f"{best_price:.2f}" if best_price is not None else "—"
            freshness, color, tip = self._format_freshness(row["last_parsed_at"])
            self._add_item_row(
                row["title"],
                row["category_title"] or "—",
                price_text,
                str(row["sources_count"]),
                freshness,
                freshness_color=color,
                freshness_tip=tip,
                item_id=row["id"],
            )
        self.items_count.setText(f"{len(items)} товаров")
        self.items_table.setSortingEnabled(True)
        if items and self._current_item_id is None:
            self.items_table.selectRow(0)
        elif not items:
            self._clear_details()

    def _select_item_by_id(self, item_id: int) -> None:
        for row in range(self.items_table.rowCount()):
            item = self.items_table.item(row, 0)
            if item is None:
                continue
            if item.data(Qt.ItemDataRole.UserRole) == item_id:
                self.items_table.selectRow(row)
                return

    def _load_categories(self) -> None:
        self.category_tree.clear()
        root_all = QTreeWidgetItem(["Все товары"])
        root_all.setData(0, Qt.ItemDataRole.UserRole, None)
        self.category_tree.addTopLevelItem(root_all)
        categories = self._db.fetch_shop_categories()
        by_parent: dict[Optional[int], list] = {}
        for cat in categories:
            by_parent.setdefault(cat.parent_id, []).append(cat)

        def add_children(parent_item: QTreeWidgetItem, parent_id: Optional[int]) -> None:
            for category_row in sorted(by_parent.get(parent_id, []), key=lambda c: c.title.lower()):
                category_item = QTreeWidgetItem([category_row.title])
                category_item.setData(0, Qt.ItemDataRole.UserRole, category_row.id)
                parent_item.addChild(category_item)
                add_children(category_item, category_row.id)

        for cat in sorted(by_parent.get(None, []), key=lambda c: c.title.lower()):
            item = QTreeWidgetItem([cat.title])
            item.setData(0, Qt.ItemDataRole.UserRole, cat.id)
            self.category_tree.addTopLevelItem(item)
            add_children(item, cat.id)
        self.category_tree.expandAll()
        self.category_tree.setCurrentItem(root_all)

    def _add_category(self) -> None:
        title, ok = QInputDialog.getText(self, "Новая категория", "Название:")
        if not ok:
            return
        title = (title or "").strip()
        if not title:
            return
        parent_id = None
        current = self.category_tree.currentItem()
        if current is not None:
            parent_id = current.data(0, Qt.ItemDataRole.UserRole)
        self._db.create_shop_category(title, parent_id=parent_id)
        self._load_categories()

    def _rename_category(self) -> None:
        current = self.category_tree.currentItem()
        if current is None:
            return
        category_id = current.data(0, Qt.ItemDataRole.UserRole)
        if category_id is None:
            self._set_status("Нельзя переименовать корневую категорию")
            return
        title, ok = QInputDialog.getText(self, "Переименовать", "Новое название:", text=current.text(0))
        if not ok:
            return
        title = (title or "").strip()
        if not title:
            return
        self._db.update_shop_category_title(int(category_id), title)
        self._load_categories()

    def _delete_category(self) -> None:
        current = self.category_tree.currentItem()
        if current is None:
            return
        category_id = current.data(0, Qt.ItemDataRole.UserRole)
        if category_id is None:
            self._set_status("Нельзя удалить корневую категорию")
            return
        confirm = QMessageBox.question(
            self,
            "Удалить категорию",
            "Удалить выбранную категорию? Товары будут без категории.",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self._db.delete_shop_category(int(category_id))
        self._load_categories()

    def _on_category_selected(self) -> None:
        current = self.category_tree.currentItem()
        if current is None:
            return
        category_id = current.data(0, Qt.ItemDataRole.UserRole)
        if category_id is None:
            self._set_status("Фильтр: все товары")
        else:
            self._set_status(f"Фильтр: категория #{category_id}")
        self.refresh()

    def _on_search_changed(self, text: str) -> None:
        super()._on_search_changed(text)
        self.refresh()

    @staticmethod
    def _format_freshness(parsed_at: str) -> tuple[str, QColor | None, str]:
        if not parsed_at:
            return "—", None, "Нет данных обновления"
        try:
            parsed_dt = datetime.fromisoformat(parsed_at)
        except ValueError:
            return "—", None, "Неверный формат даты"
        if parsed_dt.tzinfo is None:
            parsed_dt = parsed_dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        delta = now - parsed_dt
        hours = delta.total_seconds() / 3600.0
        if hours <= 12:
            return "Свежие", QColor("#7ed957"), f"{int(hours)}ч назад"
        if hours <= 48:
            return "Скоро устареет", QColor("#f6c343"), f"{int(hours)}ч назад"
        return "Устарело", QColor("#ff6b6b"), f"{int(hours)}ч назад"

    def _refresh_sources_bulk(self) -> None:
        item_ids = []
        selected = self.items_table.selectionModel().selectedRows()
        if selected:
            for index in selected:
                item = self.items_table.item(index.row(), 0)
                if item is not None:
                    item_id = item.data(Qt.ItemDataRole.UserRole)
                    if item_id is not None:
                        item_ids.append(int(item_id))
        else:
            item_ids = list(self._items_cache.keys())
        if not item_ids:
            self._set_status("Нет товаров для обновления")
            return
        sources = self._db.fetch_shop_sources_for_items(item_ids)
        if not sources:
            self._set_status("Нет источников для обновления")
            return
        self._set_status("Обновление источников…")
        self._stop_updates = False
        worker = _ShopParseWorker(self._parse_service, sources, lambda: self._stop_updates)
        worker.signals.progress.connect(self._on_parse_progress)
        worker.signals.message.connect(self._set_status)
        worker.signals.finished.connect(self._on_parse_finished)
        self._parse_pool.start(worker)

    def _on_parse_progress(self, done: int, total: int) -> None:
        self._set_status(f"Обновление: {done}/{total}")

    def _on_parse_finished(self) -> None:
        self._set_status("Обновление завершено")
        self.refresh()

    def _stop_updates_request(self) -> None:
        self._stop_updates = True
        self._set_status("Остановка обновлений…")

    def _on_item_selected(self) -> None:
        indexes = self.items_table.selectionModel().selectedRows()
        if not indexes:
            self._clear_details()
            return
        row = indexes[0].row()
        item = self.items_table.item(row, 0)
        if item is None:
            self._clear_details()
            return
        item_id = item.data(Qt.ItemDataRole.UserRole)
        if item_id is None:
            self._clear_details()
            return
        self._current_item_id = int(item_id)
        self._load_item_details(self._current_item_id)
        self._load_sources(self._current_item_id)

    def _clear_details(self) -> None:
        self._current_item_id = None
        self._current_source_id = None
        self.detail_title.setText("")
        self.detail_category.setText("")
        self.detail_price.setText("")
        self.detail_notes.setPlainText("")
        self.sources_table.setRowCount(0)
        self.source_props_table.setRowCount(0)
        self.item_props_table.setRowCount(0)
        self.history_label.setText("Выберите источник для расчёта истории цен.")

    def _load_item_details(self, item_id: int) -> None:
        item = self._db.get_shop_item(item_id)
        if item is None:
            self._clear_details()
            return
        category_title = "—"
        if item.category_id is not None:
            category = self._db.get_shop_category(item.category_id)
            if category is not None:
                category_title = category.title
        stats = self._items_cache.get(item_id, {})
        best_price = stats.get("best_price")
        price_text = f"{best_price:.2f}" if best_price is not None else "—"
        self.detail_title.setText(item.title)
        self.detail_category.setText(category_title)
        self.detail_price.setText(price_text)
        self.detail_notes.setPlainText(item.user_notes or "")

    def _load_sources(self, item_id: int) -> None:
        sources = self._db.fetch_shop_sources(item_id)
        self.sources_table.setRowCount(0)
        for source in sources:
            row = self.sources_table.rowCount()
            self.sources_table.insertRow(row)
            price_text = "—"
            if source.price is not None:
                price_text = f"{source.price:.2f} {source.currency}".strip()
            stock_text = source.stock_text or ("В наличии" if source.in_stock else "Нет в наличии")
            values = [source.shop_code, source.url, price_text, stock_text, source.sku]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, source.id)
                self.sources_table.setItem(row, col, item)
        if sources:
            self.sources_table.selectRow(0)
        self._load_properties(item_id, self._current_source_id)

    def _on_source_selected(self) -> None:
        indexes = self.sources_table.selectionModel().selectedRows()
        if not indexes:
            self._current_source_id = None
            self._load_properties(self._current_item_id, None)
            self._update_price_history(None)
            return
        row = indexes[0].row()
        item = self.sources_table.item(row, 0)
        if item is None:
            self._current_source_id = None
            self._load_properties(self._current_item_id, None)
            return
        source_id = item.data(Qt.ItemDataRole.UserRole)
        self._current_source_id = int(source_id) if source_id is not None else None
        self._load_properties(self._current_item_id, self._current_source_id)
        self._update_price_history(self._current_source_id)

    def _update_selected_source(self) -> None:
        if self._current_source_id is None:
            self._set_status("Источник не выбран")
            return
        self._set_status("Обновление источника пока не реализовано")

    def _open_selected_source(self) -> None:
        if self._current_source_id is None or self._current_item_id is None:
            self._set_status("Источник не выбран")
            return
        sources = self._db.fetch_shop_sources(self._current_item_id)
        source = next((s for s in sources if s.id == self._current_source_id), None)
        if source is None:
            self._set_status("Источник не найден")
            return
        QDesktopServices.openUrl(QUrl(source.url))

    def _delete_selected_source(self) -> None:
        if self._current_source_id is None:
            self._set_status("Источник не выбран")
            return
        dialog = ConfirmDialog(
            "Удалить источник",
            "Удалить выбранный источник?",
            parent=self,
            confirm_text="Удалить",
            cancel_text="Отмена",
        )
        if exec_with_overlay(dialog, self) != QDialog.DialogCode.Accepted:
            return
        self._db.delete_shop_source(self._current_source_id)
        if self._current_item_id is not None:
            self._load_sources(self._current_item_id)
        self._set_status("Источник удалён")

    def _show_selected_source_raw(self) -> None:
        if self._current_source_id is None or self._current_item_id is None:
            self._set_status("Источник не выбран")
            return
        sources = self._db.fetch_shop_sources(self._current_item_id)
        source = next((s for s in sources if s.id == self._current_source_id), None)
        if source is None:
            self._set_status("Источник не найден")
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Raw JSON")
        dialog.setObjectName("SourceRawDialog")
        dialog.setMinimumSize(560, 420)
        layout = QVBoxLayout(dialog)
        label = QLabel("Сырые данные источника")
        text = QPlainTextEdit()
        text.setPlainText(source.raw_json or "")
        text.setReadOnly(True)
        layout.addWidget(label)
        layout.addWidget(text, 1)
        dialog.exec()

    def _show_selected_source_diagnostics(self) -> None:
        if self._current_source_id is None:
            self._set_status("Источник не выбран")
            return
        logs = self._db.fetch_shop_parse_logs(self._current_source_id)
        dialog = QDialog(self)
        dialog.setWindowTitle("Диагностика парсинга")
        dialog.setObjectName("SourceDiagnosticsDialog")
        dialog.setMinimumSize(680, 420)
        layout = QVBoxLayout(dialog)
        table = QTableWidget(0, 5)
        table.setHorizontalHeaderLabels(["Дата", "Статус", "Content-Type", "URL", "Raw"])
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        for row_data in logs:
            row = table.rowCount()
            table.insertRow(row)
            values = [
                row_data.get("fetched_at", ""),
                str(row_data.get("status_code") or ""),
                row_data.get("content_type", ""),
                row_data.get("url", ""),
                row_data.get("raw_snippet", ""),
            ]
            for col, value in enumerate(values):
                table.setItem(row, col, QTableWidgetItem(value))
        layout.addWidget(table, 1)
        dialog.exec()

    def _load_properties(self, item_id: int | None, source_id: int | None) -> None:
        self.source_props_table.setRowCount(0)
        self.item_props_table.setRowCount(0)
        if item_id is None:
            return
        item_props = self._db.fetch_shop_item_properties(item_id)
        for prop in item_props:
            row = self.item_props_table.rowCount()
            self.item_props_table.insertRow(row)
            values = [prop.name, prop.value, prop.unit, prop.normalized_key]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, prop.id)
                self.item_props_table.setItem(row, col, item)

        if source_id is None:
            return
        source_props = self._db.fetch_shop_source_properties(source_id)
        for prop in source_props:
            row = self.source_props_table.rowCount()
            self.source_props_table.insertRow(row)
            normalized = prop.normalized_key or self._normalize_key(prop.name)
            values = [prop.name, prop.value, prop.unit, normalized]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, prop.id)
                self.source_props_table.setItem(row, col, item)

    @staticmethod
    def _normalize_key(name: str) -> str:
        raw = (name or "").strip().lower()
        raw = raw.replace("ё", "е")
        for token in ["/", "\\", ":", ";", ",", ".", "(", ")", "[", "]"]:
            raw = raw.replace(token, " ")
        raw = "_".join(filter(None, raw.split()))
        aliases = {
            "мощность": "power",
            "напряжение": "voltage",
            "ток": "current",
            "частота": "frequency",
            "вес": "weight",
            "габариты": "dimensions",
            "цвет": "color",
        }
        return aliases.get(raw, raw)

    def _accept_property_to_item(self) -> None:
        if self._current_item_id is None:
            self._set_status("Товар не выбран")
            return
        indexes = self.source_props_table.selectionModel().selectedRows()
        if not indexes:
            self._set_status("Свойство не выбрано")
            return
        accepted = 0
        for index in indexes:
            row = index.row()
            name_item = self.source_props_table.item(row, 0)
            value_item = self.source_props_table.item(row, 1)
            unit_item = self.source_props_table.item(row, 2)
            key_item = self.source_props_table.item(row, 3)
            if name_item is None or value_item is None:
                continue
            name = name_item.text()
            value = value_item.text()
            unit = unit_item.text() if unit_item else ""
            normalized = key_item.text() if key_item else ""
            if not normalized:
                normalized = self._normalize_key(name)
            self._db.upsert_shop_item_property(
                item_id=self._current_item_id,
                name=name,
                value=value,
                unit=unit,
                normalized_key=normalized,
            )
            accepted += 1
        self._load_properties(self._current_item_id, self._current_source_id)
        count = len(self._db.fetch_shop_item_properties(self._current_item_id))
        self._set_status(f"Принято: {accepted} (всего: {count})")

    def _delete_item_property(self) -> None:
        indexes = self.item_props_table.selectionModel().selectedRows()
        if not indexes:
            self._set_status("Свойство не выбрано")
            return
        row = indexes[0].row()
        item = self.item_props_table.item(row, 0)
        if item is None:
            return
        prop_id = item.data(Qt.ItemDataRole.UserRole)
        if prop_id is None:
            return
        self._db.delete_shop_item_property(int(prop_id))
        self._load_properties(self._current_item_id, self._current_source_id)
        self._set_status("Свойство удалено")

    def _update_price_history(self, source_id: int | None) -> None:
        if source_id is None:
            self.history_label.setText("Выберите источник для расчёта истории цен.")
            return
        stats = []
        for days in (7, 30, 90):
            history = self._db.fetch_shop_price_history(source_id, days)
            prices = [h.price for h in history if h.price is not None]
            if not prices:
                stats.append(f"{days}д: —")
                continue
            avg = sum(prices) / len(prices)
            stats.append(f"{days}д: min {min(prices):.2f} / avg {avg:.2f} / max {max(prices):.2f}")

        trend_text = "Тренд: —"
        history = self._db.fetch_shop_price_history(source_id, 90)
        points = [
            (idx, h.price)
            for idx, h in enumerate(history)
            if h.price is not None
        ]
        if len(points) >= 3:
            n = len(points)
            sum_x = sum(p[0] for p in points)
            sum_y = sum(p[1] for p in points)
            sum_xx = sum(p[0] ** 2 for p in points)
            sum_xy = sum(p[0] * p[1] for p in points)
            denom = (n * sum_xx - sum_x ** 2) or 1
            slope = (n * sum_xy - sum_x * sum_y) / denom
            trend_text = f"Тренд: {'рост' if slope > 0 else 'снижение' if slope < 0 else 'стабильно'}"

        self.history_label.setText("\n".join(stats + [trend_text]))

    def _load_wishlists(self) -> None:
        self.wishlist_combo.clear()
        lists = self._db.fetch_wishlists()
        if not lists:
            self.wishlist_combo.addItem("Нет списков", None)
            self.wishlist_combo.setEnabled(False)
            return
        self.wishlist_combo.setEnabled(True)
        for wl in lists:
            self.wishlist_combo.addItem(wl.title, wl.id)
        self._load_wishlist_items()

    def _create_wishlist(self) -> None:
        from PySide6.QtWidgets import QInputDialog

        title, ok = QInputDialog.getText(self, "Новый список", "Название списка:")
        if not ok:
            return
        title = (title or "").strip()
        if not title:
            return
        self._db.create_wishlist(title)
        self._load_wishlists()

    def _delete_wishlist(self) -> None:
        wishlist_id = self.wishlist_combo.currentData()
        if wishlist_id is None:
            return
        confirm = QMessageBox.question(self, "Удалить список", "Удалить выбранный список?")
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self._db.delete_wishlist(int(wishlist_id))
        self._load_wishlists()

    def _add_item_to_wishlist(self) -> None:
        if self._current_item_id is None:
            self._set_status("Товар не выбран")
            return
        wishlist_id = self.wishlist_combo.currentData()
        if wishlist_id is None:
            self._set_status("Список не выбран")
            return
        self._db.upsert_wishlist_item(
            wishlist_id=int(wishlist_id),
            item_id=self._current_item_id,
            qty=self.wishlist_qty.value(),
            priority=self.wishlist_priority.value(),
            target_price=self.wishlist_target.value() or None,
            chosen_source_id=None,
        )
        self._load_wishlist_items()
        self._set_status("Товар добавлен в хотелки")

    def _load_wishlist_items(self) -> None:
        wishlist_id = self.wishlist_combo.currentData()
        self.wishlist_table.setRowCount(0)
        if wishlist_id is None:
            self.wishlist_summary.setText("Итого: —")
            return
        items = self._db.fetch_wishlist_items(int(wishlist_id))
        total_current = 0.0
        total_expected = 0.0
        stats_map = {row["id"]: row for row in self._db.fetch_shop_items_with_stats()}
        for entry in items:
            item = self._db.get_shop_item(entry.item_id)
            title = item.title if item else f"#{entry.item_id}"
            target = entry.target_price
            target_text = f"{target:.2f}" if target is not None else "—"
            row = self.wishlist_table.rowCount()
            self.wishlist_table.insertRow(row)
            values = [
                title,
                str(entry.qty),
                str(entry.priority),
                target_text,
                "—",
            ]
            for col, value in enumerate(values):
                self.wishlist_table.setItem(row, col, QTableWidgetItem(value))
            best_price = None
            stat = stats_map.get(entry.item_id)
            if stat:
                best_price = stat.get("best_price")
            if best_price is not None:
                total_current += best_price * entry.qty
            min_30 = self._db.fetch_item_min_price_last_days(entry.item_id, 30)
            if min_30 is not None:
                total_expected += min_30 * entry.qty
            elif target is not None:
                total_expected += target * entry.qty
        if total_current or total_expected:
            self.wishlist_summary.setText(
                f"Итого: {total_current:.2f} | Ожидаемая: {total_expected:.2f}"
            )
        else:
            self.wishlist_summary.setText("Итого: —")

__all__ = ["PurchasesWorkspace"]
