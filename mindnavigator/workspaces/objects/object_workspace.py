"""ObjectWorkspace class module for objects workspace."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403
from .objects_model import ObjectsModel
from .object_card_delegate import ObjectCardDelegate
from .object_edit_dialog import ObjectEditDialog
from .cloud_image_picker_dialog import CloudImagePickerDialog
from mindnavigator.ui.styles import get_theme_palette

class ObjectWorkspace(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("ObjectsWorkspace")
        self._db = get_database()
        self._csv_service = CsvTransferService()
        self._theme_mode = "dark"
        self._smooth_scroll_controllers: list[object] = []
        self._images: List[ObjectImageData] = []
        self._current_image_index = 0
        self._current_object_id: Optional[int] = None
        self._build_ui()
        self._refresh_catalogs()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header = QHBoxLayout()
        title = QLabel("Объекты")
        title.setObjectName("ObjectsTitle")
        header.addWidget(title)

        header.addStretch(1)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Поиск по объектам...")
        self.search_edit.textChanged.connect(self._on_search)
        self.search_edit.setObjectName("ObjectsSearch")

        self.add_button = QToolButton()
        self.add_button.setText("Добавить объект")
        self.add_button.setObjectName("ObjectsAddButton")
        self.add_button.clicked.connect(self._add_object)
        self.export_button = QToolButton()
        self.export_button.setText("Экспорт")
        self.export_button.setObjectName("ObjectsExportButton")
        self.export_button.clicked.connect(self._export_objects_csv)
        self.import_button = QToolButton()
        self.import_button.setText("Импорт")
        self.import_button.setObjectName("ObjectsImportButton")
        self.import_button.clicked.connect(self._import_objects_csv)

        header.addWidget(self.search_edit)
        header.addWidget(self.add_button)
        header.addWidget(self.export_button)
        header.addWidget(self.import_button)

        layout.addLayout(header)

        quick_row = QFrame()
        quick_row.setObjectName("ObjectsQuickRow")
        quick_layout = QHBoxLayout(quick_row)
        quick_layout.setContentsMargins(0, 0, 0, 0)
        quick_layout.setSpacing(6)
        self.quick_catalog_btn = QToolButton()
        self.quick_catalog_btn.setText("Категория")
        self.quick_catalog_btn.setObjectName("ObjectsQuickCatalogBtn")
        self.quick_catalog_label = QLabel("Все категории")
        self.quick_catalog_label.setObjectName("ObjectsQuickCatalog")
        self.quick_title_input = QLineEdit()
        self.quick_title_input.setObjectName("ObjectsQuickTitle")
        self.quick_title_input.setPlaceholderText("Быстрое создание объекта...")
        self.quick_create_btn = QToolButton()
        self.quick_create_btn.setText("Создать")
        self.quick_create_btn.setObjectName("ObjectsQuickCreateBtn")
        quick_layout.addWidget(self.quick_catalog_btn)
        quick_layout.addWidget(self.quick_catalog_label)
        quick_layout.addWidget(self.quick_title_input, 1)
        quick_layout.addWidget(self.quick_create_btn)
        layout.addWidget(quick_row)

        self.splitter = QSplitter()
        self.splitter.setObjectName("ObjectsSplitter")

        self.catalog_tree = QTreeWidget()
        self.catalog_tree.setObjectName("ObjectsCatalogs")
        self.catalog_tree.setHeaderHidden(True)
        self.catalog_tree.setFixedWidth(220)
        self.catalog_tree.itemSelectionChanged.connect(self._on_catalog_selected)

        self.model = ObjectsModel(self)
        self.card_list = QListView()
        self.card_list.setObjectName("ObjectsCards")
        self.card_list.setModel(self.model)
        self.card_list.setItemDelegate(ObjectCardDelegate(self.card_list))
        self.card_list.setSelectionMode(QListView.SelectionMode.SingleSelection)
        self.card_list.setViewMode(QListView.ViewMode.ListMode)
        self.card_list.setResizeMode(QListView.ResizeMode.Adjust)
        self.card_list.setUniformItemSizes(False)
        self.card_list.setSpacing(4)
        self.card_list.selectionModel().currentChanged.connect(self._on_object_selected)

        self.details_panel = QWidget()
        self.details_panel.setObjectName("ObjectsDetails")
        details_layout = QVBoxLayout(self.details_panel)
        details_layout.setContentsMargins(16, 16, 16, 16)
        details_layout.setSpacing(12)

        self.details_title = QLabel("Выберите объект")
        self.details_title.setObjectName("ObjectsDetailsTitle")

        self.details_meta = QLabel("")
        self.details_meta.setObjectName("ObjectsDetailsMeta")

        self.details_description = QLabel("")
        self.details_description.setWordWrap(True)
        self.details_description.setObjectName("ObjectsDetailsDescription")

        buttons_row = QHBoxLayout()
        self.edit_button = QToolButton()
        self.edit_button.setText("Редактировать")
        self.edit_button.clicked.connect(self._edit_current_object)
        self.edit_button.setObjectName("ObjectsEditButton")

        self.delete_button = QToolButton()
        self.delete_button.setText("Удалить")
        self.delete_button.clicked.connect(self._delete_current_object)
        self.delete_button.setObjectName("ObjectsDeleteButton")

        self.attach_button = QToolButton()
        self.attach_button.setText("Добавить изображения")
        self.attach_button.clicked.connect(self._attach_images)
        self.attach_button.setObjectName("ObjectsAttachButton")

        buttons_row.addWidget(self.edit_button)
        buttons_row.addWidget(self.attach_button)
        buttons_row.addStretch(1)
        buttons_row.addWidget(self.delete_button)

        self.image_frame = QFrame()
        self.image_frame.setObjectName("ObjectsImageFrame")
        image_layout = QVBoxLayout(self.image_frame)
        image_layout.setContentsMargins(12, 12, 12, 12)
        image_layout.setSpacing(8)

        nav_row = QHBoxLayout()
        self.prev_button = QToolButton()
        self.prev_button.setText("←")
        self.prev_button.clicked.connect(self._prev_image)
        self.next_button = QToolButton()
        self.next_button.setText("→")
        self.next_button.clicked.connect(self._next_image)
        self.image_counter = QLabel("0/0")
        self.preview_button = QToolButton()
        self.preview_button.setText("Просмотр")
        self.preview_button.clicked.connect(self._preview_image)

        nav_row.addWidget(self.prev_button)
        nav_row.addWidget(self.next_button)
        nav_row.addStretch(1)
        nav_row.addWidget(self.image_counter)
        nav_row.addWidget(self.preview_button)

        self.thumbnail_list = QListWidget()
        self.thumbnail_list.setObjectName("ObjectsImageThumbnails")
        self.thumbnail_list.setViewMode(QListView.ViewMode.IconMode)
        self.thumbnail_list.setFlow(QListView.Flow.LeftToRight)
        self.thumbnail_list.setResizeMode(QListView.ResizeMode.Adjust)
        self.thumbnail_list.setMovement(QListView.Movement.Static)
        self.thumbnail_list.setIconSize(QSize(64, 64))
        self.thumbnail_list.setGridSize(QSize(78, 78))
        self.thumbnail_list.setFixedHeight(92)
        self.thumbnail_list.setSpacing(6)
        self.thumbnail_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.thumbnail_list.currentRowChanged.connect(self._on_thumbnail_selected)

        self.image_label = QLabel("Нет изображений")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumHeight(220)
        self.image_label.setObjectName("ObjectsImage")

        self.image_comment = QPlainTextEdit()
        self.image_comment.setObjectName("ObjectsImageComment")
        self.image_comment.setPlaceholderText("Комментарий к изображению...")
        self.save_comment_button = QToolButton()
        self.save_comment_button.setText("Сохранить описание")
        self.save_comment_button.setObjectName("ObjectsImageCommentButton")
        self.save_comment_button.clicked.connect(self._save_image_comment)

        image_layout.addLayout(nav_row)
        image_layout.addWidget(self.thumbnail_list)
        image_layout.addWidget(self.image_label)
        image_layout.addWidget(self.image_comment)
        image_layout.addWidget(self.save_comment_button, 0, Qt.AlignmentFlag.AlignRight)

        details_layout.addWidget(self.details_title)
        details_layout.addWidget(self.details_meta)
        details_layout.addWidget(self.details_description)
        details_layout.addLayout(buttons_row)
        details_layout.addWidget(self.image_frame)
        details_layout.addStretch(1)

        right_splitter = QSplitter(Qt.Orientation.Vertical)
        right_splitter.addWidget(self.card_list)
        right_splitter.addWidget(self.details_panel)
        right_splitter.setStretchFactor(0, 3)
        right_splitter.setStretchFactor(1, 2)

        self.splitter.addWidget(self.catalog_tree)
        self.splitter.addWidget(right_splitter)
        self.splitter.setStretchFactor(1, 1)

        layout.addWidget(self.splitter, 1)
        self._smooth_scroll_controllers = [
            attach_smooth_scroll(self.catalog_tree),
            attach_smooth_scroll(self.card_list),
            attach_smooth_scroll(self.thumbnail_list),
            attach_smooth_scroll(self.image_comment),
        ]
        self.quick_create_btn.clicked.connect(self._create_object_from_quick_form)
        self.quick_catalog_btn.clicked.connect(self._open_quick_catalog_menu)
        self.quick_title_input.returnPressed.connect(self._create_object_from_quick_form)
        self._set_quick_catalog(None)

        self.set_theme_mode("dark")
        self._update_action_state(False)

    def set_theme_mode(self, theme_mode: str) -> None:
        self._theme_mode = "light" if str(theme_mode).strip().lower() == "light" else "dark"
        palette = get_theme_palette(self._theme_mode)
        self.setStyleSheet(
            f"""
            QWidget#ObjectsWorkspace {{
                background: {palette.window_bg};
            }}
            QWidget {{
                color: {palette.text};
            }}
            QLabel#ObjectsTitle {{
                color: {palette.text};
                font-size: 20px;
                font-weight: 600;
            }}
            QLabel#ObjectsQuickCatalog {{
                color: {palette.chart_muted};
                font-size: 11px;
            }}
            QLineEdit#ObjectsSearch,
            QLineEdit#ObjectsQuickTitle {{
                background: {palette.input_bg};
                border: 1px solid {palette.border};
                border-radius: 6px;
                padding: 6px 10px;
                color: {palette.text};
            }}
            QLineEdit#ObjectsSearch {{ min-width: 240px; }}
            QToolButton#ObjectsAddButton,
            QToolButton#ObjectsExportButton,
            QToolButton#ObjectsImportButton,
            QToolButton#ObjectsEditButton,
            QToolButton#ObjectsDeleteButton,
            QToolButton#ObjectsAttachButton,
            QToolButton#ObjectsImageCommentButton {{
                background: {palette.elevated_bg};
                border: 1px solid {palette.border};
                border-radius: 6px;
                padding: 6px 12px;
                color: {palette.text};
            }}
            QToolButton#ObjectsDeleteButton {{
                background: {palette.danger};
                border-color: {palette.danger};
                color: {palette.selection_text};
            }}
            QTreeWidget#ObjectsCatalogs {{
                background: {palette.panel_alt_bg};
                border: 1px solid {palette.border};
                border-radius: 10px;
                color: {palette.text};
                padding: 6px;
            }}
            QTreeWidget#ObjectsCatalogs::item {{
                padding: 8px 6px;
                border-radius: 6px;
            }}
            QTreeWidget#ObjectsCatalogs::item:selected {{
                background: {palette.selection_bg};
                color: {palette.selection_text};
            }}
            QListView#ObjectsCards {{
                background: {palette.window_bg};
                border: 1px solid {palette.border};
                border-radius: 12px;
            }}
            QWidget#ObjectsDetails {{
                background: {palette.panel_bg};
                border: 1px solid {palette.border};
                border-radius: 12px;
            }}
            QLabel#ObjectsDetailsTitle {{
                color: {palette.text};
                font-size: 16px;
                font-weight: 600;
            }}
            QLabel#ObjectsDetailsMeta {{
                color: {palette.chart_muted};
                font-size: 11px;
            }}
            QLabel#ObjectsDetailsDescription {{
                color: {palette.text};
                font-size: 12px;
            }}
            QFrame#ObjectsImageFrame {{
                background: {palette.elevated_bg};
                border: 1px solid {palette.border};
                border-radius: 10px;
            }}
            QLabel#ObjectsImage {{
                background: {palette.input_alt_bg};
                border: 1px dashed {palette.border};
                border-radius: 8px;
                color: {palette.muted_text};
            }}
            QListWidget#ObjectsImageThumbnails {{
                background: {palette.input_alt_bg};
                border: 1px solid {palette.border};
                border-radius: 8px;
            }}
            QListWidget#ObjectsImageThumbnails::item {{
                padding: 4px;
            }}
            QListWidget#ObjectsImageThumbnails::item:selected {{
                background: {palette.selection_bg};
                border-radius: 6px;
            }}
            QPlainTextEdit#ObjectsImageComment {{
                background: {palette.input_bg};
                border: 1px solid {palette.border};
                border-radius: 6px;
                padding: 6px;
                color: {palette.text};
            }}
            """
        )

    def _refresh_catalogs(self) -> None:
        current = self.catalog_tree.currentItem()
        current_name = current.data(0, Qt.ItemDataRole.UserRole) if current else None
        self.catalog_tree.clear()

        root = QTreeWidgetItem(["Все объекты"])
        root.setData(0, Qt.ItemDataRole.UserRole, None)
        self.catalog_tree.addTopLevelItem(root)

        tree_items: dict[tuple[str, ...], QTreeWidgetItem] = {(): root}
        for catalog in self.model.catalogs():
            parts = [part.strip() for part in catalog.split("/") if part.strip()]
            parent_key: tuple[str, ...] = ()
            for part in parts:
                key = parent_key + (part,)
                item = tree_items.get(key)
                if item is None:
                    parent = tree_items[parent_key]
                    item = QTreeWidgetItem([part])
                    item.setData(0, Qt.ItemDataRole.UserRole, "/".join(key))
                    parent.addChild(item)
                    tree_items[key] = item
                parent_key = key

        root.setExpanded(True)
        if current_name is None:
            self.catalog_tree.setCurrentItem(root)
            return

        for item in tree_items.values():
            if item.data(0, Qt.ItemDataRole.UserRole) == current_name:
                self.catalog_tree.setCurrentItem(item)
                return

        self.catalog_tree.setCurrentItem(root)

    def refresh_objects(self) -> None:
        current_id = self._current_object_id
        self.model.reload()
        self._refresh_catalogs()
        if current_id is None:
            self._update_action_state(False)
            return
        row = self.model.row_for_object_id(current_id)
        if row is None:
            self._update_action_state(False)
            return
        index = self.model.index(row)
        if index.isValid():
            self.card_list.setCurrentIndex(index)

    def set_project_filter(self, project_id: Optional[int]) -> None:
        self.model.set_project_filter(project_id)

    def set_task_filter(self, task_id: Optional[int]) -> None:
        self.model.set_task_filter(task_id)

    def set_marker_filter(self, marker_id: Optional[int]) -> None:
        self.model.set_marker_filter(marker_id)

    def _export_objects_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Objects",
            "objects_export.csv",
            "CSV (*.csv)",
        )
        if not path:
            return
        rows = export_objects_rows(self._db.fetch_objects())
        if not rows:
            QMessageBox.information(self, "Объекты", "Нет данных для экспорта.")
            return
        try:
            self._csv_service.export_to_file(path, rows, fieldnames=OBJECTS_CSV_FIELDS)
        except CsvTransferError as exc:
            QMessageBox.warning(self, "Объекты", f"Ошибка экспорта: {exc}")
            return
        QMessageBox.information(self, "Объекты", "Экспорт завершен.")

    def _import_objects_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Objects",
            "",
            "CSV (*.csv)",
        )
        if not path:
            return
        try:
            rows = self._csv_service.import_from_file(path)
        except CsvTransferError as exc:
            QMessageBox.warning(self, "Объекты", f"Ошибка импорта: {exc}")
            return
        result = import_objects_rows(self._db, rows)
        self.refresh_objects()
        QMessageBox.information(
            self,
            "Объекты",
            f"Импорт завершен: {result.imported}, пропущено: {result.skipped}.",
        )

    def _on_search(self, text: str) -> None:
        self.model.set_search(text)

    def _on_catalog_selected(self) -> None:
        item = self.catalog_tree.currentItem()
        catalog = item.data(0, Qt.ItemDataRole.UserRole) if item else None
        self.model.set_catalog_filter(catalog)
        self._set_quick_catalog(catalog if isinstance(catalog, str) else None)

    def _on_object_selected(self, current: QModelIndex, _previous: QModelIndex) -> None:
        if not current.isValid():
            self._current_object_id = None
            self._update_action_state(False)
            return
        obj = self.model.object_at(current.row())
        if not obj:
            self._current_object_id = None
            self._update_action_state(False)
            return
        self._current_object_id = obj.id
        self.details_title.setText(obj.title)
        meta_parts = [part for part in [obj.catalog, obj.object_type, obj.status] if part]
        self.details_meta.setText(" · ".join(meta_parts) if meta_parts else "Без каталога")
        self.details_description.setText(obj.description or "Описание не заполнено.")
        self._load_images(obj.id)
        self._update_action_state(True)

    def _update_action_state(self, enabled: bool) -> None:
        self.edit_button.setEnabled(enabled)
        self.delete_button.setEnabled(enabled)
        self.attach_button.setEnabled(enabled)
        self.prev_button.setEnabled(enabled)
        self.next_button.setEnabled(enabled)
        self.preview_button.setEnabled(enabled)
        self.image_comment.setEnabled(enabled)
        self.save_comment_button.setEnabled(enabled)
        self.thumbnail_list.setEnabled(enabled)
        if not enabled:
            self.details_title.setText("Выберите объект")
            self.details_meta.setText("")
            self.details_description.setText("")
            self.image_label.setText("Нет изображений")
            self.image_counter.setText("0/0")
            self.image_comment.setPlainText("")
            self.thumbnail_list.clear()

    def _set_quick_catalog(self, catalog: Optional[str]) -> None:
        normalized = (catalog or "").strip()
        if not normalized:
            self.quick_catalog_label.setText("Все категории")
            self.quick_catalog_label.setProperty("quick_catalog", None)
            return
        self.quick_catalog_label.setText(normalized)
        self.quick_catalog_label.setProperty("quick_catalog", normalized)

    def _open_quick_catalog_menu(self) -> None:
        menu = QMenu(self)
        action_all = menu.addAction("Все категории")
        menu.addSeparator()
        actions: Dict[Any, str] = {}
        for catalog in self.model.catalogs():
            action = menu.addAction(catalog)
            actions[action] = catalog
        chosen = menu.exec(self.quick_catalog_btn.mapToGlobal(self.quick_catalog_btn.rect().bottomLeft()))
        if chosen is None:
            return
        if chosen == action_all:
            self._select_catalog_tree_item(None)
            return
        catalog = actions.get(chosen)
        if catalog is None:
            return
        self._select_catalog_tree_item(catalog)

    def _select_catalog_tree_item(self, catalog: Optional[str]) -> None:
        stack: List[QTreeWidgetItem] = [self.catalog_tree.topLevelItem(i) for i in range(self.catalog_tree.topLevelItemCount())]
        while stack:
            item = stack.pop(0)
            if item is None:
                continue
            if item.data(0, Qt.ItemDataRole.UserRole) == catalog:
                self.catalog_tree.setCurrentItem(item)
                return
            for idx in range(item.childCount()):
                stack.append(item.child(idx))

    def _create_object_from_quick_form(self) -> None:
        title = (self.quick_title_input.text() or "").strip() or "Новый объект"
        quick_catalog = self.quick_catalog_label.property("quick_catalog")
        catalog = quick_catalog if isinstance(quick_catalog, str) else ""
        try:
            obj = self._db.create_object(
                title=title,
                catalog=catalog,
                object_type="",
                status="",
                description="",
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Объекты", str(exc))
            return
        self.model.add_object(obj)
        self._refresh_catalogs()
        row = self.model.row_for_object_id(obj.id)
        if row is not None:
            index = self.model.index(row)
            if index.isValid():
                self.card_list.setCurrentIndex(index)
        self.quick_title_input.clear()

    def _add_object(self) -> None:
        dialog = ObjectEditDialog(self)
        if show_dialog_standard(dialog, self) != QDialog.DialogCode.Accepted:
            return
        values = dialog.values()
        try:
            obj = self._db.create_object(**values)
        except ValueError as exc:
            QMessageBox.warning(self, "Объекты", str(exc))
            return
        self.model.add_object(obj)
        self._refresh_catalogs()

    def _edit_current_object(self) -> None:
        current = self.card_list.currentIndex()
        if not current.isValid():
            return
        obj = self.model.object_at(current.row())
        if not obj:
            return
        dialog = ObjectEditDialog(self, initial=obj)
        if show_dialog_standard(dialog, self) != QDialog.DialogCode.Accepted:
            return
        values = dialog.values()
        try:
            updated = self._db.update_object(obj.id, **values)
        except ValueError as exc:
            QMessageBox.warning(self, "Объекты", str(exc))
            return
        self.model.update_object(updated)
        self._refresh_catalogs()
        self.details_title.setText(updated.title)
        self.details_meta.setText(" · ".join(part for part in [updated.catalog, updated.object_type, updated.status] if part))
        self.details_description.setText(updated.description or "Описание не заполнено.")

    def _delete_current_object(self) -> None:
        current = self.card_list.currentIndex()
        if not current.isValid():
            return
        obj = self.model.object_at(current.row())
        if not obj:
            return
        confirm = QMessageBox.question(
            self,
            "Удаление",
            "Удалить объект и все связанные изображения?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self._db.delete_object(obj.id)
        self.model.delete_object(obj.id)
        self._refresh_catalogs()
        self._update_action_state(False)

    def _attach_images(self) -> None:
        if self._current_object_id is None:
            return
        dialog = CloudImagePickerDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        rel_paths = dialog.selected_rel_paths()
        for rel_path in rel_paths:
            try:
                self._db.add_object_image(self._current_object_id, rel_path)
            except ValueError:
                continue
        self._load_images(self._current_object_id)

    def _load_images(self, object_id: int) -> None:
        self._images = self._db.fetch_object_images(object_id)
        self._current_image_index = 0
        self._refresh_thumbnails()
        self._update_image_view()

    def _refresh_thumbnails(self) -> None:
        self.thumbnail_list.blockSignals(True)
        self.thumbnail_list.clear()
        cloud_root = self._db.get_setting("cloud_storage_path", default="").strip()
        for idx, image in enumerate(self._images):
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, idx)
            item.setToolTip(image.rel_path)
            if cloud_root:
                file_path = Path(cloud_root) / image.rel_path
                pixmap = _load_scaled_pixmap(file_path, self.thumbnail_list.iconSize())
                if not pixmap.isNull():
                    item.setIcon(pixmap)
            self.thumbnail_list.addItem(item)
        self.thumbnail_list.setEnabled(bool(self._images))
        if self._images:
            self.thumbnail_list.setCurrentRow(self._current_image_index)
        self.thumbnail_list.blockSignals(False)

    def _update_image_view(self) -> None:
        total = len(self._images)
        if total == 0:
            self.image_label.setText("Нет изображений")
            self.image_label.setPixmap(QPixmap())
            self.image_counter.setText("0/0")
            self.image_comment.setPlainText("")
            return

        self._current_image_index = max(0, min(self._current_image_index, total - 1))
        image = self._images[self._current_image_index]
        cloud_root = self._db.get_setting("cloud_storage_path", default="").strip()
        pixmap = QPixmap()
        if cloud_root:
            file_path = Path(cloud_root) / image.rel_path
            target_size = self.image_label.size()
            if not target_size.isValid() or target_size.width() < 10:
                target_size = QSize(720, 420)
            pixmap = _load_scaled_pixmap(file_path, target_size)
        if pixmap.isNull():
            self.image_label.setText("Изображение недоступно")
            self.image_label.setPixmap(QPixmap())
        else:
            self.image_label.setPixmap(pixmap)
            self.image_label.setText("")
        self.image_counter.setText(f"{self._current_image_index + 1}/{total}")
        self.image_comment.setPlainText(image.description)
        self.thumbnail_list.blockSignals(True)
        self.thumbnail_list.setCurrentRow(self._current_image_index)
        self.thumbnail_list.blockSignals(False)

    def _prev_image(self) -> None:
        if not self._images:
            return
        self._current_image_index = max(0, self._current_image_index - 1)
        self._update_image_view()

    def _next_image(self) -> None:
        if not self._images:
            return
        self._current_image_index = min(len(self._images) - 1, self._current_image_index + 1)
        self._update_image_view()

    def _save_image_comment(self) -> None:
        if not self._images:
            return
        image = self._images[self._current_image_index]
        text = self.image_comment.toPlainText()
        updated = self._db.update_object_image(image.id, text)
        self._images[self._current_image_index] = updated

    def _on_thumbnail_selected(self, row: int) -> None:
        if row < 0 or row >= len(self._images):
            return
        self._current_image_index = row
        self._update_image_view()

    def _preview_image(self) -> None:
        if not self._images:
            return
        image = self._images[self._current_image_index]
        cloud_root = self._db.get_setting("cloud_storage_path", default="").strip()
        if not cloud_root:
            return
        file_path = Path(cloud_root) / image.rel_path
        if not file_path.is_file():
            return
        dialog = QDialog(self)
        dialog.setWindowTitle(image.rel_path)
        dialog.setMinimumSize(800, 600)
        layout = QVBoxLayout(dialog)
        label = QLabel()
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pixmap = _load_scaled_pixmap(file_path, QSize(760, 540))
        if not pixmap.isNull():
            label.setPixmap(pixmap)
        layout.addWidget(label)
        dialog.exec()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._images:
            self._update_image_view()

__all__ = ["ObjectWorkspace"]
