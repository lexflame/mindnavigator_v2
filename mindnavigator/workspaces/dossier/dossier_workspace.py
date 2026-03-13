"""Tasks-like shell workspace for Dossier mode."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403
from .dossier_details_dialog import DossierDetailsDialog
from .dossier_editor_dialog import DossierCreateDialog, DossierEditDialog
from .dossier_item_delegate import DossierItemDelegate
from .dossier_list_model import DossierListModel
from .dossier_roles import DossierRoles

LINK_ID_ROLE = int(Qt.ItemDataRole.UserRole)
LINK_ENTITY_KIND_ROLE = LINK_ID_ROLE + 1
LINK_ENTITY_ID_ROLE = LINK_ID_ROLE + 2


class DossierLinkDialog(QDialog):
    def __init__(self, database, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._db = database
        self.setWindowTitle("Добавить связь")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        form = QFormLayout()

        self.kind_combo = QComboBox(self)
        for label, kind in DOSSIER_LINK_KIND_OPTIONS:
            self.kind_combo.addItem(label, kind)

        self.search_edit = QLineEdit(self)
        self.search_edit.setPlaceholderText("Фильтр по названию сущности")

        self.entity_combo = QComboBox(self)

        form.addRow("Тип сущности", self.kind_combo)
        form.addRow("Поиск", self.search_edit)
        form.addRow("Сущность", self.entity_combo)
        layout.addLayout(form)

        buttons = QDialogButtonBox(self)
        self._ok_button = buttons.addButton(QDialogButtonBox.StandardButton.Ok)
        buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.kind_combo.currentIndexChanged.connect(self._fill_entities)
        self.search_edit.textChanged.connect(self._fill_entities)
        self._fill_entities()

    def _fill_entities(self) -> None:
        self.entity_combo.clear()
        options = self._db.fetch_dossier_link_options(str(self.kind_combo.currentData() or ""), self.search_edit.text())
        if not options:
            self.entity_combo.addItem("— нет доступных —", None)
            self._ok_button.setEnabled(False)
            return
        for entity_id, label in options:
            self.entity_combo.addItem(label, entity_id)
        self._ok_button.setEnabled(True)

    def values(self) -> dict[str, object]:
        return {
            "entity_kind": str(self.kind_combo.currentData() or ""),
            "entity_id": self.entity_combo.currentData(),
        }


class DossierWorkspace(BaseWorkspace):
    workspace_id = "dossier"
    workspace_title = "Досье"

    def __init__(self, parent: QWidget | None = None) -> None:
        self._db = get_database()
        self._current_dossier_id: Optional[int] = None
        super().__init__(parent)
        self.setObjectName("DossierWorkspace")
        self.search_input.setPlaceholderText("Поиск по названию, описанию, тегам, источнику...")
        self.refresh()

    def _build_ui(self) -> None:
        super()._build_ui()

        self.kind_filter = QComboBox()
        for label, value in DOSSIER_KIND_OPTIONS:
            self.kind_filter.addItem(label, value)
        self.kind_filter.currentIndexChanged.connect(self._on_kind_filter_changed)

        self.status_filter = QComboBox()
        for label, value in DOSSIER_STATUS_OPTIONS:
            self.status_filter.addItem(label, value)
        self.status_filter.currentIndexChanged.connect(self._on_status_filter_changed)

        self.rating_filter = QComboBox()
        for label, value in DOSSIER_RATING_OPTIONS:
            self.rating_filter.addItem(label, value)
        self.rating_filter.currentIndexChanged.connect(self._on_rating_filter_changed)

        self.filter_layout.addWidget(QLabel("Вид"))
        self.filter_layout.addWidget(self.kind_filter)
        self.filter_layout.addWidget(QLabel("Статус"))
        self.filter_layout.addWidget(self.status_filter)
        self.filter_layout.addWidget(QLabel("Рейтинг"))
        self.filter_layout.addWidget(self.rating_filter)
        self.filter_layout.addStretch(1)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("DossierSplitter")

        list_host = QWidget()
        list_layout = QVBoxLayout(list_host)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(8)

        quick_row = QWidget()
        quick_layout = QHBoxLayout(quick_row)
        quick_layout.setContentsMargins(0, 0, 0, 0)
        quick_layout.setSpacing(6)

        self.quick_kind = QComboBox()
        for label, value in DOSSIER_KIND_OPTIONS[1:]:
            self.quick_kind.addItem(label, value)
        self.quick_title_input = QLineEdit()
        self.quick_title_input.setPlaceholderText("Быстро создать новое досье...")
        self.quick_create_btn = QToolButton()
        self.quick_create_btn.setText("Создать")
        self.quick_create_btn.clicked.connect(self._create_dossier_from_quick_form)
        self.quick_title_input.returnPressed.connect(self._create_dossier_from_quick_form)

        quick_layout.addWidget(self.quick_kind)
        quick_layout.addWidget(self.quick_title_input, 1)
        quick_layout.addWidget(self.quick_create_btn)
        list_layout.addWidget(quick_row)

        self.list_view = QListView()
        self.list_view.setObjectName("DossierList")
        self.list_view.setModel(DossierListModel(self.list_view))
        self.list_view.setItemDelegate(DossierItemDelegate(self.list_view))
        self.list_view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list_view.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.list_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list_view.selectionModel().selectionChanged.connect(self._on_selection_changed)
        self.list_view.doubleClicked.connect(self._open_details_dialog)
        self.list_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_view.customContextMenuRequested.connect(self._show_context_menu)
        list_layout.addWidget(self.list_view, 1)
        splitter.addWidget(list_host)

        preview_splitter = QSplitter(Qt.Orientation.Vertical)
        preview_splitter.setChildrenCollapsible(False)

        preview_host = QWidget()
        preview_layout = QVBoxLayout(preview_host)
        preview_layout.setContentsMargins(14, 12, 14, 12)
        preview_layout.setSpacing(10)

        self.preview_title_label = QLabel("Досье не выбрано")
        self.preview_title_label.setObjectName("DossierPreviewTitle")
        self.preview_title_label.setWordWrap(True)

        self.preview_meta_label = QLabel("Выберите карточку слева, чтобы посмотреть краткое описание.")
        self.preview_meta_label.setObjectName("DossierPreviewMeta")
        self.preview_meta_label.setWordWrap(True)

        self.preview_summary_label = QLabel("")
        self.preview_summary_label.setObjectName("DossierPreviewSummary")
        self.preview_summary_label.setWordWrap(True)

        self.preview_description = QPlainTextEdit()
        self.preview_description.setReadOnly(True)
        self.preview_description.setPlaceholderText("Описание появится после выбора досье.")

        self.preview_tags_label = QLabel("")
        self.preview_tags_label.setWordWrap(True)

        self.preview_source_label = QLabel("")
        self.preview_source_label.setWordWrap(True)

        self.preview_metadata_label = QLabel("")
        self.preview_metadata_label.setWordWrap(True)

        preview_layout.addWidget(self.preview_title_label)
        preview_layout.addWidget(self.preview_meta_label)
        preview_layout.addWidget(self.preview_summary_label)
        preview_layout.addWidget(self.preview_description, 1)
        preview_layout.addWidget(self.preview_tags_label)
        preview_layout.addWidget(self.preview_source_label)
        preview_layout.addWidget(self.preview_metadata_label)

        links_host = QFrame()
        links_host.setObjectName("DossierLinksCard")
        links_layout = QVBoxLayout(links_host)
        links_layout.setContentsMargins(14, 12, 14, 12)
        links_layout.setSpacing(8)
        links_header = QWidget()
        links_header_layout = QHBoxLayout(links_header)
        links_header_layout.setContentsMargins(0, 0, 0, 0)
        links_header_layout.setSpacing(6)
        links_header_layout.addWidget(QLabel("Связанные сущности"))
        links_header_layout.addStretch(1)
        self.add_link_button = QToolButton()
        self.add_link_button.setText("Привязать")
        self.add_link_button.clicked.connect(self._open_add_link_dialog)
        self.remove_link_button = QToolButton()
        self.remove_link_button.setText("Убрать")
        self.remove_link_button.clicked.connect(self._remove_selected_link)
        links_header_layout.addWidget(self.add_link_button)
        links_header_layout.addWidget(self.remove_link_button)
        links_layout.addWidget(links_header)
        self.preview_links = QListWidget()
        self.preview_links.itemSelectionChanged.connect(self._update_link_action_states)
        links_layout.addWidget(self.preview_links, 1)

        preview_splitter.addWidget(preview_host)
        preview_splitter.addWidget(links_host)
        preview_splitter.setStretchFactor(0, 4)
        preview_splitter.setStretchFactor(1, 2)

        splitter.addWidget(preview_splitter)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        self.set_content(splitter)

        self.setStyleSheet(
            """
            QWidget#DossierWorkspace {
                background: #15161a;
            }
            QWidget#DossierWorkspace QLabel {
                color: #d5d8de;
            }
            QWidget#DossierWorkspace QWidget#WorkspaceToolbar,
            QWidget#DossierWorkspace QWidget#WorkspaceSearch,
            QWidget#DossierWorkspace QWidget#WorkspaceFilters {
                background: #1b1c21;
                border: 1px solid #2a2c33;
                border-radius: 10px;
                padding: 6px;
            }
            QWidget#DossierWorkspace QToolButton,
            QWidget#DossierWorkspace QComboBox,
            QWidget#DossierWorkspace QLineEdit,
            QWidget#DossierWorkspace QPlainTextEdit,
            QWidget#DossierWorkspace QListWidget,
            QWidget#DossierWorkspace QListView {
                background: #1d1f25;
                color: #d5d8de;
                border: 1px solid #2e3138;
                border-radius: 8px;
                padding: 6px 8px;
            }
            QWidget#DossierWorkspace QToolButton:hover {
                background: #272a33;
            }
            QWidget#DossierWorkspace QToolButton:disabled {
                color: #71757f;
                background: #191a1f;
            }
            QLabel#DossierPreviewTitle {
                font-size: 18px;
                font-weight: 700;
                color: #f3f5f8;
            }
            QLabel#DossierPreviewMeta {
                color: #aeb6c2;
            }
            QLabel#DossierPreviewSummary {
                color: #dfe4eb;
            }
            QFrame#DossierLinksCard {
                background: #1a1c21;
                border: 1px solid #2a2c33;
                border-radius: 10px;
            }
            """
        )

    def create_actions(self) -> dict[str, QAction]:
        action_new = QAction("+ Досье", self)
        action_new.triggered.connect(self._open_create_dialog)
        action_edit = QAction("Изменить", self)
        action_edit.triggered.connect(self._open_edit_dialog)
        action_details = QAction("Карточка", self)
        action_details.triggered.connect(self._open_details_dialog)
        action_refresh = QAction("Обновить", self)
        action_refresh.triggered.connect(self.refresh)
        action_delete = QAction("Удалить", self)
        action_delete.triggered.connect(self._delete_selected)
        return {
            "new": action_new,
            "edit": action_edit,
            "details": action_details,
            "refresh": action_refresh,
            "delete": action_delete,
        }

    def update_action_states(self) -> None:
        super().update_action_states()
        details_action = self.actions.get("details")
        if details_action is not None:
            details_action.setEnabled(self.get_selection() is not None and not self._busy)
        self._update_link_action_states()

    def restore_state(self) -> None:
        super().restore_state()
        self._sync_filter_controls()

    def get_selection(self) -> Optional[int]:
        index = self.list_view.currentIndex()
        if not index.isValid():
            return None
        value = index.data(DossierRoles.DossierId)
        return int(value) if isinstance(value, int) else None

    def _sync_filter_controls(self) -> None:
        self._set_combo_value(self.kind_filter, self.get_filters().get("kind"))
        self._set_combo_value(self.status_filter, self.get_filters().get("status"))
        self._set_combo_value(self.rating_filter, self.get_filters().get("rating"))

    @staticmethod
    def _set_combo_value(combo: QComboBox, value: object) -> None:
        for index in range(combo.count()):
            if combo.itemData(index) == value:
                combo.blockSignals(True)
                combo.setCurrentIndex(index)
                combo.blockSignals(False)
                return

    def _update_link_action_states(self) -> None:
        if not hasattr(self, "add_link_button") or not hasattr(self, "preview_links"):
            return
        dossier_selected = self.get_selection() is not None and not self._busy
        self.add_link_button.setEnabled(dossier_selected)
        current_item = self.preview_links.currentItem()
        link_id = current_item.data(LINK_ID_ROLE) if current_item is not None else None
        self.remove_link_button.setEnabled(dossier_selected and link_id is not None)

    def _on_kind_filter_changed(self) -> None:
        self.set_filter("kind", self.kind_filter.currentData())

    def _on_status_filter_changed(self) -> None:
        self.set_filter("status", self.status_filter.currentData())

    def _on_rating_filter_changed(self) -> None:
        self.set_filter("rating", self.rating_filter.currentData())

    def _open_create_dialog(self, checked: bool = False) -> None:
        _ = checked
        dialog = DossierCreateDialog(
            parent=self,
            seed_kind=str(self.quick_kind.currentData() or self.kind_filter.currentData() or "book"),
            seed_title=(self.quick_title_input.text() or "").strip(),
        )
        if show_dialog_standard(dialog, self) != QDialog.DialogCode.Accepted:
            return
        try:
            dossier = self._db.create_dossier(**dialog.values())
        except ValueError as exc:
            QMessageBox.warning(self, "Досье", str(exc))
            return
        self._current_dossier_id = dossier.id
        self.quick_title_input.clear()
        self.refresh()
        self.set_status("Досье создано.")

    def _create_dossier_from_quick_form(self) -> None:
        self._open_create_dialog()

    def _open_edit_dialog(self, checked: bool = False) -> None:
        _ = checked
        dossier_id = self.get_selection()
        if dossier_id is None:
            return
        dossier = self._db.get_dossier(dossier_id)
        if dossier is None:
            return
        dialog = DossierEditDialog(dossier, parent=self)
        if show_dialog_standard(dialog, self) != QDialog.DialogCode.Accepted:
            return
        try:
            updated = self._db.update_dossier(dossier_id=dossier_id, **dialog.values())
        except ValueError as exc:
            QMessageBox.warning(self, "Досье", str(exc))
            return
        self._current_dossier_id = updated.id
        self.refresh()
        self.set_status("Досье обновлено.")

    def _open_details_dialog(self, checked: bool = False) -> None:
        _ = checked
        dossier_id = self.get_selection()
        if dossier_id is None:
            return
        dossier = self._db.get_dossier(dossier_id)
        if dossier is None:
            return
        dialog = DossierDetailsDialog(dossier, parent=self)
        show_dialog_standard(dialog, self)

    def _open_add_link_dialog(self, checked: bool = False) -> None:
        _ = checked
        dossier_id = self.get_selection()
        if dossier_id is None:
            return
        dialog = DossierLinkDialog(self._db, parent=self)
        if show_dialog_standard(dialog, self) != QDialog.DialogCode.Accepted:
            return
        values = dialog.values()
        entity_id = values.get("entity_id")
        if entity_id is None:
            QMessageBox.warning(self, "Досье", "Нет доступной сущности для привязки.")
            return
        try:
            self._db.add_dossier_link(dossier_id, str(values.get("entity_kind") or ""), int(entity_id))
        except ValueError as exc:
            QMessageBox.warning(self, "Досье", str(exc))
            return
        self._load_preview(dossier_id)
        self.set_status("Связь добавлена.")

    def _remove_selected_link(self, checked: bool = False) -> None:
        _ = checked
        dossier_id = self.get_selection()
        if dossier_id is None:
            return
        item = self.preview_links.currentItem()
        if item is None:
            return
        link_id = item.data(LINK_ID_ROLE)
        if link_id is None:
            return
        self._db.delete_dossier_link(int(link_id))
        self._load_preview(dossier_id)
        self.set_status("Связь удалена.")

    def _delete_selected(self, checked: bool = False, *, require_confirmation: bool = True) -> None:
        _ = checked
        dossier_id = self.get_selection()
        if dossier_id is None:
            return
        if require_confirmation:
            dialog = ConfirmDialog(
                "Удалить досье",
                "Это действие нельзя отменить. Удалить выбранное досье?",
                parent=self,
                confirm_text="Удалить",
                cancel_text="Отмена",
            )
            if exec_with_overlay(dialog, self) != QDialog.DialogCode.Accepted:
                return
        self._db.delete_dossier(dossier_id)
        self._current_dossier_id = None
        self.refresh()
        self.set_status("Досье удалено.")

    def _show_context_menu(self, pos) -> None:
        index = self.list_view.indexAt(pos)
        menu = QMenu(self)
        action_new = menu.addAction("Создать")
        action_edit = None
        action_details = None
        action_refresh = menu.addAction("Обновить")
        action_delete = None
        if index.isValid():
            action_edit = menu.addAction("Изменить")
            action_details = menu.addAction("Карточка")
            action_delete = menu.addAction("Удалить")
        chosen = menu.exec(self.list_view.mapToGlobal(pos))
        if chosen == action_new:
            self._open_create_dialog()
        elif chosen == action_refresh:
            self.refresh()
        elif action_edit is not None and chosen == action_edit:
            self.list_view.setCurrentIndex(index)
            self._open_edit_dialog()
        elif action_details is not None and chosen == action_details:
            self.list_view.setCurrentIndex(index)
            self._open_details_dialog()
        elif action_delete is not None and chosen == action_delete:
            self.list_view.setCurrentIndex(index)
            self._delete_selected()

    def apply_query(self, query: str) -> None:
        self.refresh()

    def apply_filters(self, filters: dict[str, object]) -> None:
        self.refresh()

    def refresh(self) -> None:
        filters = self.get_filters()
        items = self._db.fetch_dossiers(
            kind=filters.get("kind") if isinstance(filters.get("kind"), str) else None,
            status=filters.get("status") if isinstance(filters.get("status"), str) else None,
            search_text=self._query,
        )
        rating_filter = filters.get("rating")
        if isinstance(rating_filter, int):
            items = [item for item in items if item.rating == rating_filter]
        model = self.list_view.model()
        if isinstance(model, DossierListModel):
            model.set_items(items)
        self.status_row.setText(f"Найдено досье: {len(items)}")
        self._sync_selection()

    def _sync_selection(self) -> None:
        model = self.list_view.model()
        if not isinstance(model, DossierListModel):
            return
        if self._current_dossier_id is None:
            if model.rowCount() > 0:
                self.list_view.setCurrentIndex(model.index(0, 0))
            else:
                self._clear_preview()
                self.update_action_states()
            return
        index = model.index_for_id(self._current_dossier_id)
        if index.isValid():
            self.list_view.setCurrentIndex(index)
            return
        self._current_dossier_id = None
        if model.rowCount() > 0:
            self.list_view.setCurrentIndex(model.index(0, 0))
            return
        self._clear_preview()
        self.update_action_states()

    def _on_selection_changed(self) -> None:
        dossier_id = self.get_selection()
        self._current_dossier_id = dossier_id
        if dossier_id is None:
            self._clear_preview()
            self.update_action_states()
            return
        self._load_preview(dossier_id)
        self.update_action_states()

    def _clear_preview(self) -> None:
        self.preview_title_label.setText("Досье не выбрано")
        self.preview_meta_label.setText("Выберите карточку слева, чтобы посмотреть краткое описание.")
        self.preview_summary_label.clear()
        self.preview_description.clear()
        self.preview_tags_label.clear()
        self.preview_source_label.clear()
        self.preview_metadata_label.clear()
        self.preview_links.clear()
        self._update_link_action_states()

    def _load_preview(self, dossier_id: int) -> None:
        dossier = self._db.get_dossier(dossier_id)
        if dossier is None:
            self._clear_preview()
            return
        self.preview_title_label.setText(dossier.title or "Без названия")
        self.preview_meta_label.setText(dossier_secondary_line(dossier))
        self.preview_summary_label.setText(dossier.summary or "Краткое описание пока не заполнено.")
        self.preview_description.setPlainText(dossier.description or "")
        self.preview_tags_label.setText(f"Теги: {dossier_tags_text(dossier.tags)}")
        self.preview_source_label.setText(f"Источник: {dossier.source or 'Не указан'}")
        self.preview_metadata_label.setText(f"Типовые поля: {dossier_metadata_preview(dossier, max_parts=6)}")
        self.preview_links.clear()
        for link in self._db.fetch_dossier_links(dossier_id):
            label = self._db.describe_dossier_link_target(link.entity_kind, link.entity_id)
            item = QListWidgetItem(label)
            item.setData(LINK_ID_ROLE, link.id)
            item.setData(LINK_ENTITY_KIND_ROLE, link.entity_kind)
            item.setData(LINK_ENTITY_ID_ROLE, link.entity_id)
            self.preview_links.addItem(item)
        if self.preview_links.count() == 0:
            placeholder = QListWidgetItem("Связей пока нет")
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            self.preview_links.addItem(placeholder)
        self._update_link_action_states()


__all__ = ["DossierLinkDialog", "DossierWorkspace"]
