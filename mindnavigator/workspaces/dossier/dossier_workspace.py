"""Tasks-like shell workspace for Dossier mode."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403
from .dossier_item_delegate import DossierItemDelegate
from .dossier_list_model import DossierListModel
from .dossier_roles import DossierRoles


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
        links_layout.addWidget(QLabel("Связанные сущности"))
        self.preview_links = QListWidget()
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
        action_new.triggered.connect(self._create_dossier_from_toolbar)
        action_refresh = QAction("Обновить", self)
        action_refresh.triggered.connect(self.refresh)
        action_delete = QAction("Удалить", self)
        action_delete.triggered.connect(self._delete_selected)
        return {
            "new": action_new,
            "refresh": action_refresh,
            "delete": action_delete,
        }

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

    def _on_kind_filter_changed(self) -> None:
        self.set_filter("kind", self.kind_filter.currentData())

    def _on_status_filter_changed(self) -> None:
        self.set_filter("status", self.status_filter.currentData())

    def _on_rating_filter_changed(self) -> None:
        self.set_filter("rating", self.rating_filter.currentData())

    def _create_dossier_from_toolbar(self) -> None:
        self._create_dossier(
            title=(self.quick_title_input.text() or "").strip() or "Новое досье",
            kind=self.quick_kind.currentData() or self.kind_filter.currentData() or "book",
        )

    def _create_dossier_from_quick_form(self) -> None:
        self._create_dossier(
            title=(self.quick_title_input.text() or "").strip() or "Новое досье",
            kind=self.quick_kind.currentData() or "book",
        )
        self.quick_title_input.clear()

    def _create_dossier(self, *, title: str, kind: object) -> None:
        kind_value = str(kind or "book")
        status_value = self.status_filter.currentData()
        dossier = self._db.create_dossier(
            kind=kind_value,
            title=title,
            status=str(status_value) if isinstance(status_value, str) and status_value else "planned",
        )
        self._current_dossier_id = dossier.id
        self.refresh()
        self.set_status("Досье создано.")

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
        action_refresh = menu.addAction("Обновить")
        action_delete = None
        if index.isValid():
            action_delete = menu.addAction("Удалить")
        chosen = menu.exec(self.list_view.mapToGlobal(pos))
        if chosen == action_new:
            self._create_dossier_from_toolbar()
        elif chosen == action_refresh:
            self.refresh()
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
            self.preview_links.addItem(QListWidgetItem(label))
        if self.preview_links.count() == 0:
            placeholder = QListWidgetItem("Связей пока нет")
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            self.preview_links.addItem(placeholder)


__all__ = ["DossierWorkspace"]
