"""CollectionsWorkspace class module for collections workspace."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403
from ._entry_thumb_signals import _EntryThumbSignals
from ._entry_thumb_worker import _EntryThumbWorker
from .collection_media_preview_dialog import CollectionMediaPreviewDialog
from .collection_item_edit_dialog import CollectionItemEditDialog
from .collection_relation_dialog import CollectionRelationDialog
from mindnavigator.ui.styles import get_theme_palette

class CollectionsWorkspace(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("CollectionsWorkspace")
        self._db = get_database()
        self._csv_service = CsvTransferService()
        self._theme_mode = "dark"
        self._smooth_scroll_controllers: list[object] = []
        self._items: List[CollectionItemData] = []
        self._items_by_id: Dict[int, CollectionItemData] = {}
        self._categories: List[CollectionCategoryData] = []
        self._categories_by_id: Dict[int, CollectionCategoryData] = {}
        self._relations: List[CollectionRelationData] = []
        self._entries: List[CollectionEntryData] = []
        self._entries_by_id: Dict[int, CollectionEntryData] = {}
        self._current_item_id: Optional[int] = None
        self._thumb_size = QSize(56, 56)
        self._entry_thumb_size = QSize(72, 72)
        self._missing_entry_color = QColor("#8b8b8b")
        self._thumb_cache: Dict[str, QIcon] = {}
        self._thumb_pending_urls: set[str] = set()
        self._thumb_loader = QNetworkAccessManager(self)
        self._thumb_loader.finished.connect(self._on_thumb_loaded)
        self._entry_thumb_dir = Path.home() / ".mindnavigator" / "collection_thumbs"
        self._entry_thumb_signals = _EntryThumbSignals()
        self._entry_thumb_signals.ready.connect(self._on_entry_thumb_ready)
        self._entry_thumb_pool = QThreadPool(self)
        self._build_ui()
        self.refresh_collections()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Коллекции")
        title.setObjectName("CollectionsTitle")
        header.addWidget(title)
        header.addStretch(1)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Поиск по коллекциям...")
        self.search_edit.textChanged.connect(self.refresh_collections)

        self.topic_filter = QComboBox()
        self.topic_filter.currentIndexChanged.connect(self.refresh_collections)

        self.type_filter = QComboBox()
        self.type_filter.addItem("Все типы", "")
        for label, value in ENTITY_CHOICES:
            self.type_filter.addItem(label, value)
        self.type_filter.currentIndexChanged.connect(self.refresh_collections)

        self.include_subcategories = QCheckBox("Включая подкатегории")
        self.include_subcategories.setChecked(True)
        self.include_subcategories.stateChanged.connect(self.refresh_collections)

        self.add_button = QToolButton()
        self.add_button.setText("Добавить")
        self.add_button.clicked.connect(self._add_item)
        self.export_button = QToolButton()
        self.export_button.setText("Экспорт")
        self.export_button.clicked.connect(self._export_collections_csv)
        self.import_button = QToolButton()
        self.import_button.setText("Импорт")
        self.import_button.clicked.connect(self._import_collections_csv)

        header.addWidget(self.search_edit)
        header.addWidget(self.topic_filter)
        header.addWidget(self.type_filter)
        header.addWidget(self.include_subcategories)
        header.addWidget(self.add_button)
        header.addWidget(self.export_button)
        header.addWidget(self.import_button)
        layout.addLayout(header)

        quick_row = QFrame()
        quick_row.setObjectName("CollectionsQuickRow")
        quick_layout = QHBoxLayout(quick_row)
        quick_layout.setContentsMargins(0, 0, 0, 0)
        quick_layout.setSpacing(6)
        self.quick_category_btn = QToolButton()
        self.quick_category_btn.setText("Категория")
        self.quick_category_label = QLabel("Все категории")
        self.quick_category_label.setObjectName("CollectionsQuickCategory")
        self.quick_type_combo = QComboBox()
        for label, value in ENTITY_CHOICES:
            self.quick_type_combo.addItem(label, value)
        self.quick_title_edit = QLineEdit()
        self.quick_title_edit.setPlaceholderText("Быстрое создание элемента...")
        self.quick_create_btn = QToolButton()
        self.quick_create_btn.setText("Создать")
        quick_layout.addWidget(self.quick_category_btn)
        quick_layout.addWidget(self.quick_category_label)
        quick_layout.addWidget(self.quick_type_combo)
        quick_layout.addWidget(self.quick_title_edit, 1)
        quick_layout.addWidget(self.quick_create_btn)
        layout.addWidget(quick_row)

        splitter = QSplitter()

        category_panel = QFrame()
        category_layout = QVBoxLayout(category_panel)
        category_layout.setContentsMargins(0, 0, 0, 0)
        category_layout.setSpacing(6)
        category_label = QLabel("Категории")
        category_label.setObjectName("CollectionsCategoriesTitle")
        self.category_tree = QTreeWidget()
        self.category_tree.setHeaderHidden(True)
        self.category_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.category_tree.customContextMenuRequested.connect(self._open_category_menu)
        self.category_tree.currentItemChanged.connect(self._on_category_tree_changed)
        category_layout.addWidget(category_label)
        category_layout.addWidget(self.category_tree, 1)

        list_panel = QFrame()
        list_layout = QVBoxLayout(list_panel)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(8)
        self.items_list = QListWidget()
        self.items_list.setIconSize(self._thumb_size)
        self.items_list.currentItemChanged.connect(self._on_item_selected)
        list_layout.addWidget(self.items_list, 1)

        right = QFrame()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(12, 12, 12, 12)
        right_layout.setSpacing(8)

        self.details_title = QLabel("Выберите элемент")
        self.details_title.setObjectName("CollectionsDetailsTitle")
        self.details_type = QLabel("")
        self.details_category = QLabel("")
        self.details_topic = QLabel("")
        self.details_links = QLabel("")
        self.details_links.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        self.details_links.setOpenExternalLinks(True)
        self.details_description = QLabel("")
        self.details_description.setObjectName("CollectionsDescription")
        self.details_description.setWordWrap(True)

        actions = QHBoxLayout()
        self.edit_button = QToolButton()
        self.edit_button.setText("Редактировать")
        self.edit_button.clicked.connect(self._edit_current_item)
        self.delete_button = QToolButton()
        self.delete_button.setText("Удалить")
        self.delete_button.clicked.connect(self._delete_current_item)
        self.refresh_import_button = QToolButton()
        self.refresh_import_button.setText("Обновить из папки")
        self.refresh_import_button.clicked.connect(self._update_from_folder)
        self.link_button = QToolButton()
        self.link_button.setText("Создать связь")
        self.link_button.clicked.connect(self._add_relation)
        actions.addWidget(self.edit_button)
        actions.addWidget(self.refresh_import_button)
        actions.addWidget(self.link_button)
        actions.addStretch(1)
        actions.addWidget(self.delete_button)

        rel_title = QLabel("Перекрестные связи")
        rel_title.setObjectName("CollectionsRelationsTitle")
        self.relations_list = QListWidget()
        self.remove_relation_button = QToolButton()
        self.remove_relation_button.setText("Удалить выбранную связь")
        self.remove_relation_button.clicked.connect(self._remove_relation)

        entries_title = QLabel("Элементы коллекции")
        entries_title.setObjectName("CollectionsRelationsTitle")
        entries_filters = QHBoxLayout()
        self.filter_images = QCheckBox("Изображения")
        self.filter_images.setChecked(True)
        self.filter_images.stateChanged.connect(self._refresh_entries)
        self.filter_videos = QCheckBox("Видео")
        self.filter_videos.setChecked(True)
        self.filter_videos.stateChanged.connect(self._refresh_entries)
        self.filter_docs = QCheckBox("Документы")
        self.filter_docs.setChecked(True)
        self.filter_docs.stateChanged.connect(self._refresh_entries)
        self.filter_other = QCheckBox("Прочее")
        self.filter_other.setChecked(True)
        self.filter_other.stateChanged.connect(self._refresh_entries)
        self.group_by_folder = QCheckBox("Группировать по подпапкам")
        self.group_by_folder.setChecked(False)
        self.group_by_folder.stateChanged.connect(self._refresh_entries)
        entries_filters.addWidget(self.filter_images)
        entries_filters.addWidget(self.filter_videos)
        entries_filters.addWidget(self.filter_docs)
        entries_filters.addWidget(self.filter_other)
        entries_filters.addStretch(1)
        entries_filters.addWidget(self.group_by_folder)

        self.entries_list = QListWidget()
        self.entries_list.setIconSize(self._entry_thumb_size)
        self.entries_list.itemDoubleClicked.connect(self._open_entry)
        self.entries_list.currentItemChanged.connect(self._on_entry_current_changed)
        self.remove_entry_button = QToolButton()
        self.remove_entry_button.setText("Удалить элемент")
        self.remove_entry_button.clicked.connect(self._remove_selected_entry)

        right_layout.addWidget(self.details_title)
        right_layout.addWidget(self.details_type)
        right_layout.addWidget(self.details_category)
        right_layout.addWidget(self.details_topic)
        right_layout.addWidget(self.details_links)
        right_layout.addWidget(self.details_description)
        right_layout.addLayout(actions)
        right_layout.addWidget(rel_title)
        right_layout.addWidget(self.relations_list, 1)
        right_layout.addWidget(self.remove_relation_button, 0, Qt.AlignmentFlag.AlignRight)
        right_layout.addWidget(entries_title)
        right_layout.addLayout(entries_filters)
        right_layout.addWidget(self.entries_list, 2)
        right_layout.addWidget(self.remove_entry_button, 0, Qt.AlignmentFlag.AlignRight)

        splitter.addWidget(category_panel)
        splitter.addWidget(list_panel)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        splitter.setStretchFactor(2, 3)
        layout.addWidget(splitter, 1)
        self._smooth_scroll_controllers = [
            attach_smooth_scroll(self.category_tree),
            attach_smooth_scroll(self.items_list),
            attach_smooth_scroll(self.relations_list),
            attach_smooth_scroll(self.entries_list),
        ]
        self.quick_category_btn.clicked.connect(self._open_quick_category_menu)
        self.quick_create_btn.clicked.connect(self._create_item_from_quick_form)
        self.quick_title_edit.returnPressed.connect(self._create_item_from_quick_form)
        self._set_quick_category(None)

        self._set_action_state(False)
        self.set_theme_mode("dark")

    def set_theme_mode(self, theme_mode: str) -> None:
        self._theme_mode = "light" if str(theme_mode).strip().lower() == "light" else "dark"
        palette = get_theme_palette(self._theme_mode)
        self._missing_entry_color = QColor(palette.muted_text)
        self.setStyleSheet(
            f"""
            QWidget#CollectionsWorkspace {{
                background: {palette.window_bg};
            }}
            QWidget {{
                color: {palette.text};
            }}
            QLabel#CollectionsTitle {{
                color: {palette.text};
                font-size: 20px;
                font-weight: 600;
            }}
            QLabel#CollectionsCategoriesTitle {{
                color: {palette.text};
                font-size: 13px;
                font-weight: 600;
            }}
            QLabel#CollectionsQuickCategory {{
                color: {palette.chart_muted};
                font-size: 11px;
            }}
            QTreeWidget {{
                background: {palette.window_bg};
                border: 1px solid {palette.border};
                border-radius: 10px;
                color: {palette.text};
            }}
            QTreeWidget::item {{
                padding: 6px 10px;
            }}
            QTreeWidget::item:selected {{
                background: {palette.selection_bg};
                color: {palette.selection_text};
            }}
            QListWidget {{
                background: {palette.window_bg};
                border: 1px solid {palette.border};
                border-radius: 10px;
                color: {palette.text};
            }}
            QListWidget::item {{
                padding: 8px 10px;
                border-bottom: 1px solid {palette.border};
            }}
            QListWidget::item:selected {{
                background: {palette.selection_bg};
                color: {palette.selection_text};
            }}
            QLineEdit, QComboBox {{
                background: {palette.input_bg};
                border: 1px solid {palette.border};
                border-radius: 6px;
                padding: 6px 10px;
                color: {palette.text};
                min-height: 26px;
            }}
            QCheckBox {{
                color: {palette.text};
            }}
            QToolButton {{
                background: {palette.elevated_bg};
                border: 1px solid {palette.border};
                border-radius: 6px;
                padding: 6px 12px;
                color: {palette.text};
            }}
            QLabel#CollectionsDetailsTitle {{
                color: {palette.text};
                font-size: 17px;
                font-weight: 600;
            }}
            QLabel#CollectionsDescription {{
                color: {palette.text};
            }}
            QLabel#CollectionsRelationsTitle {{
                color: {palette.text};
                font-size: 13px;
                font-weight: 600;
            }}
            """
        )
        if self._current_item_id is not None:
            self._refresh_entries()

    def _set_action_state(self, has_selection: bool) -> None:
        self.edit_button.setEnabled(has_selection)
        self.delete_button.setEnabled(has_selection)
        self.refresh_import_button.setEnabled(has_selection)
        self.link_button.setEnabled(has_selection)
        self.remove_relation_button.setEnabled(has_selection)
        self.remove_entry_button.setEnabled(False)
        if not has_selection:
            self.details_title.setText("Выберите элемент")
            self.details_type.setText("")
            self.details_category.setText("")
            self.details_topic.setText("")
            self.details_links.setText("")
            self.details_description.setText("")
            self.relations_list.clear()
            self.entries_list.clear()
            self._entries = []
            self._entries_by_id = {}
            return
        self._sync_entry_action_state()

    def _refresh_entries(self) -> None:
        if self._current_item_id is None:
            self.entries_list.clear()
            self._sync_entry_action_state()
            return
        self._entries = self._db.fetch_collection_entries(self._current_item_id)
        self._entries_by_id = {entry.id: entry for entry in self._entries}
        allow_kinds = set()
        if self.filter_images.isChecked():
            allow_kinds.add("image")
        if self.filter_videos.isChecked():
            allow_kinds.add("video")
        if self.filter_docs.isChecked():
            allow_kinds.add("document")
        if self.filter_other.isChecked():
            allow_kinds.add("other")

        def allowed(entry: CollectionEntryData) -> bool:
            kind = FolderCollectionImporter.classify_extension(entry.ext)
            return kind in allow_kinds

        entries = [entry for entry in self._entries if allowed(entry)]
        self.entries_list.blockSignals(True)
        self.entries_list.clear()
        if self.group_by_folder.isChecked():
            groups: Dict[str, List[CollectionEntryData]] = {}
            for entry in entries:
                folder = str(Path(entry.rel_path).parent)
                if folder == ".":
                    folder = "Корень"
                groups.setdefault(folder, []).append(entry)
            for folder in sorted(groups.keys()):
                header = QListWidgetItem(folder)
                header.setFlags(Qt.ItemFlag.ItemIsEnabled)
                header.setData(Qt.ItemDataRole.UserRole, ("header", folder))
                self.entries_list.addItem(header)
                for entry in groups[folder]:
                    self._add_entry_item(entry)
        else:
            for entry in entries:
                self._add_entry_item(entry)
        self.entries_list.blockSignals(False)

        if not entries:
            empty = QListWidgetItem("Нет элементов по текущим фильтрам.")
            empty.setFlags(Qt.ItemFlag.ItemIsEnabled)
            empty.setData(Qt.ItemDataRole.UserRole, ("empty", None))
            self.entries_list.addItem(empty)
        self._sync_entry_action_state()

    def _add_entry_item(self, entry: CollectionEntryData) -> None:
        label = entry.rel_path
        if entry.is_missing:
            label = f"[нет файла] {label}"
        item = QListWidgetItem(label)
        item.setData(Qt.ItemDataRole.UserRole, ("entry", entry.id))
        kind = FolderCollectionImporter.classify_extension(entry.ext)
        icon = self._entry_icon_for(entry, kind)
        item.setIcon(icon)
        if entry.is_missing:
            item.setForeground(self._missing_entry_color)
        self.entries_list.addItem(item)

    def _entry_icon_for(self, entry: CollectionEntryData, kind: str) -> QIcon:
        if kind in {"image", "video"} and entry.source_path:
            thumb_path = self._entry_thumb_path(entry)
            if thumb_path.exists():
                return QIcon(str(thumb_path))
            worker = _EntryThumbWorker(
                entry.id,
                entry.source_path,
                thumb_path,
                self._entry_thumb_size,
                self._entry_thumb_signals,
                kind,
            )
            self._entry_thumb_pool.start(worker)
            return self._entry_placeholder_icon(kind)
        return self._entry_placeholder_icon(kind)

    def _entry_thumb_path(self, entry: CollectionEntryData) -> Path:
        safe_name = str(entry.id)
        return self._entry_thumb_dir / f"{safe_name}.png"

    def _entry_placeholder_icon(self, kind: str) -> QIcon:
        key = f"__entry_{kind}__"
        cached = self._thumb_cache.get(key)
        if cached is not None:
            return cached
        color = {
            "image": "#2d6cdf",
            "video": "#c26b1d",
            "document": "#2f8f5b",
            "other": "#5a5f6b",
        }.get(kind, "#5a5f6b")
        pixmap = QPixmap(self._entry_thumb_size)
        pixmap.fill(QColor(color))
        painter = QPainter(pixmap)
        painter.setPen(Qt.GlobalColor.white)
        painter.drawRect(0, 0, self._entry_thumb_size.width() - 1, self._entry_thumb_size.height() - 1)
        painter.setBrush(Qt.GlobalColor.white)
        if kind == "video":
            w = self._entry_thumb_size.width()
            h = self._entry_thumb_size.height()
            points = [
                (w * 0.38, h * 0.28),
                (w * 0.38, h * 0.72),
                (w * 0.72, h * 0.5),
            ]
            painter.drawPolygon([QPointF(x, y) for x, y in points])
        elif kind == "document":
            w = self._entry_thumb_size.width()
            h = self._entry_thumb_size.height()
            rect_w = w * 0.5
            rect_h = h * 0.6
            x = (w - rect_w) / 2
            y = (h - rect_h) / 2
            painter.drawRect(int(x), int(y), int(rect_w), int(rect_h))
        painter.end()
        icon = QIcon(pixmap)
        self._thumb_cache[key] = icon
        return icon

    def _on_entry_thumb_ready(self, entry_id: int, thumb_path: str) -> None:
        for row in range(self.entries_list.count()):
            item = self.entries_list.item(row)
            payload = item.data(Qt.ItemDataRole.UserRole)
            if not payload or payload[0] != "entry":
                continue
            if payload[1] == entry_id:
                item.setIcon(QIcon(thumb_path))
                break

    def _on_entry_current_changed(self, current: Optional[QListWidgetItem], _previous: Optional[QListWidgetItem]) -> None:
        self._sync_entry_action_state(current)

    def _sync_entry_action_state(self, current: Optional[QListWidgetItem] = None) -> None:
        item = current if current is not None else self.entries_list.currentItem()
        if item is None or self._current_item_id is None:
            self.remove_entry_button.setEnabled(False)
            return
        payload = item.data(Qt.ItemDataRole.UserRole)
        self.remove_entry_button.setEnabled(bool(payload and payload[0] == "entry"))

    def _open_entry(self, item: QListWidgetItem) -> None:
        payload = item.data(Qt.ItemDataRole.UserRole)
        if not payload or payload[0] != "entry":
            return
        entry = self._entries_by_id.get(payload[1])
        if entry is None:
            return
        if entry.is_missing:
            QMessageBox.information(self, "Коллекции", "Файл помечен как отсутствующий.")
            return
        path = Path(entry.source_path)
        if not path.exists():
            QMessageBox.warning(self, "Коллекции", "Файл не найден.")
            return
        kind = FolderCollectionImporter.classify_extension(entry.ext)
        if kind in {"image", "video", "document"}:
            media_entries = [
                e
                for e in self._entries
                if FolderCollectionImporter.classify_extension(e.ext) in {"image", "video", "document"}
                and not e.is_missing
            ]
            try:
                start_index = next(i for i, e in enumerate(media_entries) if e.id == entry.id)
            except StopIteration:
                start_index = 0
            dialog = CollectionMediaPreviewDialog(media_entries, start_index=start_index, parent=self)
            dialog.exec()
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def _selected_category_id(self) -> Optional[int]:
        if not hasattr(self, "category_tree"):
            return None
        item = self.category_tree.currentItem()
        if item is None:
            return None
        return item.data(0, Qt.ItemDataRole.UserRole)

    def _set_quick_category(self, category_id: Optional[int]) -> None:
        if category_id is None:
            self.quick_category_label.setText("Все категории")
            self.quick_category_label.setProperty("quick_category_id", None)
            return
        category = self._categories_by_id.get(category_id)
        if category is None:
            self.quick_category_label.setText("Все категории")
            self.quick_category_label.setProperty("quick_category_id", None)
            return
        self.quick_category_label.setText(category.title)
        self.quick_category_label.setProperty("quick_category_id", category_id)

    def _on_category_tree_changed(self, current: Optional[QTreeWidgetItem], _previous: Optional[QTreeWidgetItem]) -> None:
        category_id = current.data(0, Qt.ItemDataRole.UserRole) if current is not None else None
        self._set_quick_category(category_id)
        self.refresh_collections()

    def _open_quick_category_menu(self) -> None:
        menu = QMenu(self)
        action_all = menu.addAction("Все категории")
        menu.addSeparator()
        actions: Dict[Any, Optional[int]] = {}
        for label, category_id in self._category_options():
            action = menu.addAction(label)
            actions[action] = category_id
        chosen = menu.exec(self.quick_category_btn.mapToGlobal(self.quick_category_btn.rect().bottomLeft()))
        if chosen is None:
            return
        if chosen == action_all:
            self._select_category_tree_item(None)
            return
        category_id = actions.get(chosen)
        self._select_category_tree_item(category_id)

    def _select_category_tree_item(self, category_id: Optional[int]) -> None:
        stack: List[QTreeWidgetItem] = [self.category_tree.topLevelItem(i) for i in range(self.category_tree.topLevelItemCount())]
        while stack:
            node = stack.pop(0)
            if node is None:
                continue
            if node.data(0, Qt.ItemDataRole.UserRole) == category_id:
                self.category_tree.setCurrentItem(node)
                return
            for idx in range(node.childCount()):
                stack.append(node.child(idx))

    def _create_item_from_quick_form(self) -> None:
        title = (self.quick_title_edit.text() or "").strip() or "Новая коллекция"
        entity_type = self.quick_type_combo.currentData() or "other"
        category_value = self.quick_category_label.property("quick_category_id")
        category_id = category_value if isinstance(category_value, int) else None
        try:
            item = self._db.create_collection_item(
                title=title,
                entity_type=entity_type,
                category_id=category_id,
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Коллекции", str(exc))
            return
        self.quick_title_edit.clear()
        self.refresh_collections()
        for row in range(self.items_list.count()):
            list_item = self.items_list.item(row)
            if list_item.data(Qt.ItemDataRole.UserRole) == item.id:
                self.items_list.setCurrentRow(row)
                self._on_item_selected(list_item, None)
                break

    def _category_children_map(self) -> Dict[Optional[int], List[CollectionCategoryData]]:
        children: Dict[Optional[int], List[CollectionCategoryData]] = {}
        for category in self._categories:
            children.setdefault(category.parent_id, []).append(category)
        for values in children.values():
            values.sort(key=lambda c: (c.sort_index, c.title.lower(), c.id))
        return children

    def _category_descendants(self, category_id: int) -> List[int]:
        children_map = self._category_children_map()
        result: List[int] = []
        stack = [category_id]
        while stack:
            current = stack.pop()
            for child in children_map.get(current, []):
                result.append(child.id)
                stack.append(child.id)
        return result

    def _category_filter_ids(self) -> Optional[List[int]]:
        category_id = self._selected_category_id()
        if category_id is None:
            return None
        if self.include_subcategories.isChecked():
            return [category_id] + self._category_descendants(category_id)
        return [category_id]

    def _category_options(self) -> List[tuple[str, Optional[int]]]:
        path_map = self._category_path_map()
        options = [(path, cat_id) for cat_id, path in path_map.items()]
        options.sort(key=lambda pair: pair[0].lower())
        return options

    def _category_path_map(self) -> Dict[int, str]:
        result: Dict[int, str] = {}
        for category in self._categories:
            parts = [category.title]
            parent_id = category.parent_id
            while parent_id is not None and parent_id in self._categories_by_id:
                parent = self._categories_by_id[parent_id]
                parts.append(parent.title)
                parent_id = parent.parent_id
            result[category.id] = " / ".join(reversed(parts))
        return result

    def _refresh_categories(self, selected_category_id: Optional[int]) -> None:
        self._categories = self._db.fetch_collection_categories()
        self._categories_by_id = {cat.id: cat for cat in self._categories}
        self._rebuild_category_tree(selected_category_id)

    def _find_category_tree_item(self, root: QTreeWidgetItem, category_id: int) -> Optional[QTreeWidgetItem]:
        if root.data(0, Qt.ItemDataRole.UserRole) == category_id:
            return root
        for idx in range(root.childCount()):
            child = root.child(idx)
            found = self._find_category_tree_item(child, category_id)
            if found is not None:
                return found
        return None

    def _rebuild_category_tree(self, selected_category_id: Optional[int]) -> None:
        if not hasattr(self, "category_tree"):
            return
        self.category_tree.blockSignals(True)
        self.category_tree.clear()
        root = QTreeWidgetItem(["Все коллекции"])
        root.setData(0, Qt.ItemDataRole.UserRole, None)
        self.category_tree.addTopLevelItem(root)
        children_map = self._category_children_map()

        def add_children(parent_item: QTreeWidgetItem, parent_id: Optional[int]) -> None:
            for category in children_map.get(parent_id, []):
                item = QTreeWidgetItem([category.title])
                item.setData(0, Qt.ItemDataRole.UserRole, category.id)
                parent_item.addChild(item)
                add_children(item, category.id)

        add_children(root, None)
        self.category_tree.expandToDepth(1)
        target_item = root
        if selected_category_id is not None:
            found = self._find_category_tree_item(root, selected_category_id)
            if found is not None:
                target_item = found
        self.category_tree.setCurrentItem(target_item)
        self.category_tree.blockSignals(False)

    def _open_category_menu(self, pos) -> None:
        item = self.category_tree.itemAt(pos)
        current_id = item.data(0, Qt.ItemDataRole.UserRole) if item is not None else None
        menu = QMenu(self)
        create_action = menu.addAction("Создать категорию")
        create_child_action = menu.addAction("Создать подкатегорию")
        rename_action = menu.addAction("Переименовать")
        move_action = menu.addAction("Переместить")
        delete_action = menu.addAction("Удалить")
        if item is None:
            create_child_action.setEnabled(False)
            rename_action.setEnabled(False)
            move_action.setEnabled(False)
            delete_action.setEnabled(False)
        elif current_id is None:
            create_child_action.setEnabled(True)
            rename_action.setEnabled(False)
            move_action.setEnabled(False)
            delete_action.setEnabled(False)
        action = menu.exec(self.category_tree.mapToGlobal(pos))
        if action is None:
            return
        if action == create_action:
            self._create_category(parent_id=None)
        elif action == create_child_action and current_id is not None:
            self._create_category(parent_id=current_id)
        elif action == rename_action and current_id is not None:
            self._rename_category(current_id)
        elif action == move_action and current_id is not None:
            self._move_category(current_id)
        elif action == delete_action and current_id is not None:
            self._delete_category(current_id)

    def _create_category(self, parent_id: Optional[int]) -> None:
        title, ok = QInputDialog.getText(self, "Категории", "Название категории:")
        if not ok:
            return
        title = (title or "").strip()
        if not title:
            return
        try:
            self._db.create_collection_category(title, parent_id=parent_id)
        except ValueError as exc:
            QMessageBox.warning(self, "Категории", str(exc))
            return
        self.refresh_collections()

    def _rename_category(self, category_id: int) -> None:
        category = self._categories_by_id.get(category_id)
        if category is None:
            return
        title, ok = QInputDialog.getText(self, "Категории", "Новое название:", text=category.title)
        if not ok:
            return
        title = (title or "").strip()
        if not title:
            return
        try:
            self._db.update_collection_category_title(category_id, title)
        except ValueError as exc:
            QMessageBox.warning(self, "Категории", str(exc))
            return
        self.refresh_collections()

    def _move_category(self, category_id: int) -> None:
        excluded = {category_id, *self._category_descendants(category_id)}
        options: List[tuple[str, Optional[int]]] = [("Корень", None)]
        for label, cat_id in self._category_options():
            if cat_id in excluded:
                continue
            options.append((label, cat_id))
        labels = [label for label, _ in options]
        choice, ok = QInputDialog.getItem(self, "Категории", "Новый родитель:", labels, 0, False)
        if not ok:
            return
        new_parent_id = dict(options).get(choice)
        if new_parent_id == category_id:
            return
        try:
            self._db.move_collection_category(category_id, new_parent_id)
        except ValueError as exc:
            QMessageBox.warning(self, "Категории", str(exc))
            return
        self.refresh_collections()

    def _delete_category(self, category_id: int) -> None:
        category = self._categories_by_id.get(category_id)
        if category is None:
            return
        dialog = ConfirmDialog(
            "Удалить категорию",
            f"Удалить категорию «{category.title}»?",
            parent=self,
            confirm_text="Удалить",
            cancel_text="Отмена",
        )
        if show_dialog_standard(dialog, self) != QDialog.DialogCode.Accepted:
            return
        try:
            self._db.delete_collection_category(category_id)
        except ValueError:
            dialog = ConfirmDialog(
                "Категория не пуста",
                "Перенести подкатегории и коллекции в корень и удалить категорию?",
                parent=self,
                confirm_text="Перенести и удалить",
                cancel_text="Отмена",
            )
            if show_dialog_standard(dialog, self) != QDialog.DialogCode.Accepted:
                return
            self._db.delete_collection_category(
                category_id,
                move_children_to_root=True,
                move_items_to_root=True,
            )
        self.refresh_collections()

    def refresh_collections(self) -> None:
        selected_id = self._current_item_id
        selected_category_id = self._selected_category_id()
        self._refresh_categories(selected_category_id)
        topics = self._db.fetch_collection_topics()
        current_topic = self.topic_filter.currentData() if self.topic_filter.count() else ""
        self.topic_filter.blockSignals(True)
        self.topic_filter.clear()
        self.topic_filter.addItem("Все темы", "")
        for topic in topics:
            self.topic_filter.addItem(topic, topic)
        idx = self.topic_filter.findData(current_topic)
        if idx >= 0:
            self.topic_filter.setCurrentIndex(idx)
        self.topic_filter.blockSignals(False)

        self._items = self._db.fetch_collection_items(
            search_text=self.search_edit.text(),
            topic=self.topic_filter.currentData() or None,
            entity_type=self.type_filter.currentData() or None,
            category_ids=self._category_filter_ids(),
        )
        self._items_by_id = {item.id: item for item in self._items}
        self._set_quick_category(self._selected_category_id())

        self.items_list.blockSignals(True)
        self.items_list.clear()
        grouped_items = group_collection_items_by_category(self._items, self._categories_by_id)
        for category_title, values in grouped_items:
            header_item = QListWidgetItem(category_title)
            header_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            header_item.setData(Qt.ItemDataRole.UserRole, ("category", category_title))
            header_item.setSizeHint(QSize(220, 30))
            self.items_list.addItem(header_item)
            for item in values:
                label = format_collection_item_row(item, self._categories_by_id)
                list_item = QListWidgetItem(label)
                list_item.setData(Qt.ItemDataRole.UserRole, item.id)
                list_item.setIcon(self._placeholder_icon())
                list_item.setSizeHint(QSize(220, 72))
                self.items_list.addItem(list_item)
                self._load_thumbnail(item.id, item.image_url)
        self.items_list.blockSignals(False)

        if not self._items:
            self._current_item_id = None
            self._set_action_state(False)
            return

        select_row = -1
        if selected_id is not None:
            for row in range(self.items_list.count()):
                if self.items_list.item(row).data(Qt.ItemDataRole.UserRole) == selected_id:
                    select_row = row
                    break
        if select_row < 0:
            for row in range(self.items_list.count()):
                payload = self.items_list.item(row).data(Qt.ItemDataRole.UserRole)
                if isinstance(payload, int):
                    select_row = row
                    break
        if select_row < 0:
            self._current_item_id = None
            self._set_action_state(False)
            return
        self.items_list.setCurrentRow(select_row)
        self._on_item_selected(self.items_list.currentItem(), None)

    def _export_collections_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Collections",
            "collections_export.csv",
            "CSV (*.csv)",
        )
        if not path:
            return
        rows = export_collections_rows(
            self._db.fetch_collection_items(),
            self._db.fetch_collection_categories(),
        )
        if not rows:
            QMessageBox.information(self, "Коллекции", "Нет данных для экспорта.")
            return
        try:
            self._csv_service.export_to_file(path, rows, fieldnames=COLLECTIONS_CSV_FIELDS)
        except CsvTransferError as exc:
            QMessageBox.warning(self, "Коллекции", f"Ошибка экспорта: {exc}")
            return
        QMessageBox.information(self, "Коллекции", "Экспорт завершен.")

    def _import_collections_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Collections",
            "",
            "CSV (*.csv)",
        )
        if not path:
            return
        try:
            rows = self._csv_service.import_from_file(path)
        except CsvTransferError as exc:
            QMessageBox.warning(self, "Коллекции", f"Ошибка импорта: {exc}")
            return
        result = import_collections_rows(self._db, rows)
        self.refresh_collections()
        QMessageBox.information(
            self,
            "Коллекции",
            f"Импорт завершен: {result.imported}, пропущено: {result.skipped}.",
        )

    def _on_item_selected(self, current: Optional[QListWidgetItem], _previous) -> None:
        if current is None:
            self._current_item_id = None
            self._set_action_state(False)
            return
        payload = current.data(Qt.ItemDataRole.UserRole)
        if not isinstance(payload, int):
            self._current_item_id = None
            self._set_action_state(False)
            return
        item_id = payload
        item = self._items_by_id.get(item_id)
        if item is None:
            self._current_item_id = None
            self._set_action_state(False)
            return

        self._current_item_id = item.id
        self.details_title.setText(item.title)
        category_title = "—"
        if item.category_id is not None:
            category = self._categories_by_id.get(item.category_id)
            if category is not None:
                category_title = category.title
        self.details_category.setText(f"Категория: {category_title}")
        self.details_type.setText(f"Тип: {ENTITY_LABELS.get(item.entity_type, item.entity_type)}")
        self.details_topic.setText(f"Тема: {item.topic or '—'}")
        links: List[str] = []
        if item.source_url:
            links.append(f"<a href='{item.source_url}'>Источник</a>")
        if item.image_url:
            links.append(f"<a href='{item.image_url}'>Изображение</a>")
        self.details_links.setText(" · ".join(links) if links else "Ссылки: —")
        self.details_description.setText(item.description or "Описание не задано.")

        self._relations = self._db.fetch_collection_relations(item.id)
        self.relations_list.clear()
        all_items = {it.id: it for it in self._db.fetch_collection_items()}
        for rel in self._relations:
            other_id = rel.right_item_id if rel.left_item_id == item.id else rel.left_item_id
            other = all_items.get(other_id)
            if other is None:
                continue
            text = f"{item.title} {rel.relation_kind} {other.title}"
            row = QListWidgetItem(text)
            row.setData(Qt.ItemDataRole.UserRole, rel.id)
            self.relations_list.addItem(row)
        self._set_action_state(True)
        self._refresh_entries()

    def _add_item(self) -> None:
        dialog = CollectionItemEditDialog(parent=self, category_options=self._category_options())
        if exec_with_overlay(dialog, self) != QDialog.DialogCode.Accepted:
            return
        try:
            self._db.create_collection_item(**dialog.values())
        except ValueError as exc:
            QMessageBox.warning(self, "Коллекции", str(exc))
            return
        self.refresh_collections()

    def _current_item(self) -> Optional[CollectionItemData]:
        if self._current_item_id is None:
            return None
        return next((item for item in self._items if item.id == self._current_item_id), None)

    def _edit_current_item(self) -> None:
        item = self._current_item()
        if item is None:
            return
        dialog = CollectionItemEditDialog(item=item, parent=self, category_options=self._category_options())
        if exec_with_overlay(dialog, self) != QDialog.DialogCode.Accepted:
            return
        try:
            self._db.update_collection_item(item.id, **dialog.values())
        except ValueError as exc:
            QMessageBox.warning(self, "Коллекции", str(exc))
            return
        self.refresh_collections()

    def _delete_current_item(self) -> None:
        item = self._current_item()
        if item is None:
            return
        dialog = ConfirmDialog(
            "Удалить элемент",
            f"Удалить элемент «{item.title}» и все его связи?",
            parent=self,
            confirm_text="Удалить",
            cancel_text="Отмена",
        )
        if show_dialog_standard(dialog, self) != QDialog.DialogCode.Accepted:
            return
        self._db.delete_collection_item(item.id)
        self.refresh_collections()

    def _update_from_folder(self) -> None:
        item = self._current_item()
        if item is None:
            return
        folder_path = (item.source_folder_path or "").strip()
        if not folder_path:
            QMessageBox.information(self, "Коллекции", "У этой коллекции нет исходной папки.")
            return
        folder = Path(folder_path)
        if not folder.exists() or not folder.is_dir():
            QMessageBox.warning(self, "Коллекции", "Папка коллекции недоступна.")
            return
        options = {}
        if item.import_options_json:
            try:
                options = json.loads(item.import_options_json)
            except json.JSONDecodeError:
                options = {}
        include_subfolders = bool(options.get("include_subfolders", True))
        files, list_errors = list_files(folder, include_subfolders=include_subfolders)
        if not self._confirm_large_folder(len(files)):
            return
        entries, errors = self._scan_with_progress(folder, files)
        errors = list_errors + errors
        payload = [
            {
                "source_path": entry.source_path,
                "rel_path": entry.rel_path,
                "title": entry.title,
                "ext": entry.ext,
                "mime": entry.mime,
                "size_bytes": entry.size_bytes,
                "meta_json": entry.meta_json,
            }
            for entry in entries
        ]
        self._db.sync_collection_entries(item.id, payload)
        if not payload:
            QMessageBox.information(
                self,
                "Коллекции",
                "Папка пуста. Коллекция обновлена без элементов.",
            )
        if errors:
            self._report_import_errors(errors, "Обновление коллекции")
        self._refresh_entries()

    def _confirm_large_folder(self, total: int) -> bool:
        if total <= 2000:
            return True
        if total >= 10000:
            QMessageBox.warning(
                self,
                "Коллекции",
                "В папке более 10k файлов. Обновление может занять длительное время.",
            )
        dialog = ConfirmDialog(
            "Большая папка",
            f"В папке {total} файлов. Продолжить импорт?",
            parent=self,
            confirm_text="Продолжить",
            cancel_text="Отмена",
        )
        return show_dialog_standard(dialog, self) == QDialog.DialogCode.Accepted

    def _scan_with_progress(
        self,
        folder_path: Path,
        files: List[Path],
    ) -> tuple[list, list]:
        progress = QProgressDialog("Сканирование файлов...", "Отмена", 0, max(1, len(files)), self)
        progress.setWindowTitle("Импорт коллекции")
        progress.setMinimumDuration(0)
        progress.setWindowModality(Qt.WindowModality.WindowModal)

        def progress_cb(index: int, total: int | None, _path: Path) -> None:
            progress.setMaximum(total or max(1, len(files)))
            progress.setValue(index)
            QApplication.processEvents()

        def cancel_cb() -> bool:
            return progress.wasCanceled()

        items, errors, cancelled = scan_files(
            folder_path,
            files,
            progress_cb=progress_cb,
            cancel_cb=cancel_cb,
        )
        progress.close()
        if cancelled:
            return [], []
        return items, errors

    def _report_import_errors(self, errors: List[str], context: str) -> None:
        if not errors:
            return
        log_path = Path.home() / ".mindnavigator" / "collection_import_errors.txt"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(f"\n[{datetime.now(timezone.utc).isoformat(timespec='seconds')}] {context}\n")
            for line in errors:
                handle.write(f"{line}\n")
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle("Коллекции")
        box.setText(f"Обновление завершено с ошибками ({len(errors)}).")
        box.setInformativeText(f"Лог: {log_path}")
        open_btn = box.addButton("Открыть лог", QMessageBox.ButtonRole.ActionRole)
        box.addButton("Ок", QMessageBox.ButtonRole.AcceptRole)
        box.exec()
        if box.clickedButton() == open_btn:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(log_path)))

    def _add_relation(self) -> None:
        item = self._current_item()
        if item is None:
            return
        candidates = [it for it in self._db.fetch_collection_items() if it.id != item.id]
        if not candidates:
            QMessageBox.information(self, "Связи", "Нет доступных элементов для связывания.")
            return
        dialog = CollectionRelationDialog(item, candidates, parent=self)
        if exec_with_overlay(dialog, self) != QDialog.DialogCode.Accepted:
            return
        values = dialog.values()
        try:
            self._db.create_collection_relation(item.id, int(values["target_id"]), values["relation_kind"])
        except ValueError as exc:
            QMessageBox.warning(self, "Связи", str(exc))
            return
        self.refresh_collections()

    def _remove_relation(self) -> None:
        if self._current_item_id is None:
            return
        current = self.relations_list.currentItem()
        if current is None:
            QMessageBox.information(self, "Связи", "Выберите связь для удаления.")
            return
        relation_id = current.data(Qt.ItemDataRole.UserRole)
        self._db.delete_collection_relation(int(relation_id))
        self.refresh_collections()

    def _remove_selected_entry(self) -> None:
        if self._current_item_id is None:
            return
        current = self.entries_list.currentItem()
        if current is None:
            QMessageBox.information(self, "Коллекции", "Выберите элемент коллекции для удаления.")
            return
        payload = current.data(Qt.ItemDataRole.UserRole)
        if not payload or payload[0] != "entry":
            QMessageBox.information(self, "Коллекции", "Выберите файл в списке элементов коллекции.")
            return
        entry_id = int(payload[1])
        entry = self._entries_by_id.get(entry_id)
        entry_label = entry.rel_path if entry is not None else str(entry_id)
        dialog = ConfirmDialog(
            "Удалить элемент коллекции",
            f"Удалить элемент «{entry_label}» из коллекции? Исходный файл удален не будет.",
            parent=self,
            confirm_text="Удалить",
            cancel_text="Отмена",
        )
        if show_dialog_standard(dialog, self) != QDialog.DialogCode.Accepted:
            return
        self._db.delete_collection_entry(entry_id)
        self._refresh_entries()

    def focus_item(self, item_id: int) -> None:
        self.refresh_collections()
        for row in range(self.items_list.count()):
            item = self.items_list.item(row)
            if item.data(Qt.ItemDataRole.UserRole) == item_id:
                self.items_list.setCurrentRow(row)
                self._on_item_selected(item, None)
                break

    def _placeholder_icon(self) -> QIcon:
        key = "__placeholder__"
        cached = self._thumb_cache.get(key)
        if cached is not None:
            return cached
        pixmap = QPixmap(self._thumb_size)
        pixmap.fill(QColor("#1f232a"))
        painter = QPainter(pixmap)
        painter.setPen(QColor("#3a3f4a"))
        painter.drawRect(0, 0, self._thumb_size.width() - 1, self._thumb_size.height() - 1)
        painter.end()
        icon = QIcon(pixmap)
        self._thumb_cache[key] = icon
        return icon

    def _load_thumbnail(self, item_id: int, image_url: str) -> None:
        url = (image_url or "").strip()
        if not url:
            return
        if url in self._thumb_cache:
            self._apply_thumbnail_icon(item_id, self._thumb_cache[url])
            return
        if url in self._thumb_pending_urls:
            return
        qurl = QUrl.fromUserInput(url)
        if not qurl.isValid() or qurl.isEmpty():
            return
        request = QNetworkRequest(qurl)
        reply = self._thumb_loader.get(request)
        reply.setProperty("collection_item_id", item_id)
        reply.setProperty("thumb_url", url)
        self._thumb_pending_urls.add(url)

    def _on_thumb_loaded(self, reply: QNetworkReply) -> None:
        url = str(reply.property("thumb_url") or "").strip()
        item_id = int(reply.property("collection_item_id") or 0)
        if url:
            self._thumb_pending_urls.discard(url)
        icon: Optional[QIcon] = None
        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = reply.readAll().data()
            pixmap = QPixmap()
            if pixmap.loadFromData(data):
                scaled = pixmap.scaled(
                    self._thumb_size,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
                cropped = QPixmap(self._thumb_size)
                cropped.fill(Qt.GlobalColor.transparent)
                painter = QPainter(cropped)
                x = (scaled.width() - self._thumb_size.width()) // 2
                y = (scaled.height() - self._thumb_size.height()) // 2
                painter.drawPixmap(-x, -y, scaled)
                painter.end()
                icon = QIcon(cropped)
        if icon is not None:
            if url:
                self._thumb_cache[url] = icon
            if item_id:
                self._apply_thumbnail_icon(item_id, icon)
        reply.deleteLater()

    def _apply_thumbnail_icon(self, item_id: int, icon: QIcon) -> None:
        for row in range(self.items_list.count()):
            item = self.items_list.item(row)
            if item.data(Qt.ItemDataRole.UserRole) == item_id:
                item.setIcon(icon)
                break

__all__ = ["CollectionsWorkspace"]
