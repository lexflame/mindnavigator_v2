"""NoteWorkspace class module for notes workspace."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403
from .notes_model import NotesModel
from .notes_controller import NotesController
from .note_card_delegate import NoteCardDelegate

class NoteWorkspace(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._db = get_database()
        self._csv_service = CsvTransferService()
        self.setObjectName("NotesWorkspace")
        self._state = NoteWorkspaceState()
        self._smooth_scroll_controllers: list[object] = []

        self._build_ui()
        self._wire_logic()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        header = QFrame()
        header.setObjectName("NotesHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(10, 8, 10, 8)
        header_layout.setSpacing(8)

        self.btn_toggle_left = QToolButton()
        self.btn_toggle_left.setIcon(qta.icon("fa5s.columns", color="#cfcfcf"))
        self.btn_toggle_left.setAutoRaise(True)
        self.btn_toggle_left.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_toggle_right = QToolButton()
        self.btn_toggle_right.setIcon(qta.icon("fa5s.align-right", color="#cfcfcf"))
        self.btn_toggle_right.setAutoRaise(True)
        self.btn_toggle_right.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_zen = QToolButton()
        self.btn_zen.setIcon(qta.icon("fa5s.eye", color="#cfcfcf"))
        self.btn_zen.setAutoRaise(True)
        self.btn_zen.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_zen.setCheckable(True)

        header_layout.addWidget(self.btn_toggle_left)
        header_layout.addWidget(self.btn_toggle_right)
        header_layout.addWidget(self.btn_zen)
        header_layout.addStretch(1)

        header_title = QLabel("Note Workspace")
        header_title.setObjectName("NotesHeaderTitle")
        header_layout.addWidget(header_title)
        header_layout.addStretch(1)

        self.btn_new_note = QToolButton()
        self.btn_new_note.setIcon(qta.icon("fa5s.plus", color="#ffffff"))
        self.btn_new_note.setText("Новая")
        self.btn_new_note.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn_new_note.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export = QToolButton()
        self.btn_export.setText("Экспорт")
        self.btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_import = QToolButton()
        self.btn_import.setText("Импорт")
        self.btn_import.setCursor(Qt.CursorShape.PointingHandCursor)

        header_layout.addWidget(self.btn_new_note)
        header_layout.addWidget(self.btn_export)
        header_layout.addWidget(self.btn_import)
        root.addWidget(header)

        self.splitter = QSplitter()
        self.splitter.setObjectName("NotesSplitter")
        self.splitter.setChildrenCollapsible(False)
        root.addWidget(self.splitter, 1)

        self.nav_panel = self._build_nav_panel()
        self.list_panel = self._build_list_panel()
        self.editor_panel = self._build_editor_panel()

        self.splitter.addWidget(self.nav_panel)
        self.splitter.addWidget(self.list_panel)
        self.splitter.addWidget(self.editor_panel)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setStretchFactor(2, 1)
        self.splitter.setSizes([240, 520, 420])

        self.setStyleSheet("""
            QWidget#NotesWorkspace { background: #16171a; }

            QFrame#NotesHeader {
                background: #1b1c1f;
                border: 1px solid #2a2b2f;
                border-radius: 10px;
            }

            QLabel#NotesHeaderTitle {
                color: #d7d7d7;
                font-size: 12px;
                letter-spacing: 0.6px;
            }

            QToolButton {
                background: transparent;
                border: none;
                color: #cfcfcf;
                padding: 4px 8px;
            }

            QToolButton:checked {
                color: #ffffff;
                background: #20242b;
                border-radius: 6px;
            }

            QFrame#NotesNavPanel,
            QFrame#NotesListPanel,
            QFrame#NotesEditorPanel {
                background: #1a1c20;
                border: 1px solid #2a2b2f;
                border-radius: 12px;
            }

            QLineEdit {
                background: #131417;
                border: 1px solid #2a2b2f;
                padding: 6px 8px;
                color: #e6e6e6;
                border-radius: 8px;
            }

            QTextEdit {
                background: #131417;
                border: 1px solid #2a2b2f;
                color: #e6e6e6;
                padding: 10px;
                border-radius: 10px;
            }

            QListView#NotesGrid {
                background: transparent;
                outline: none;
            }

            QTreeWidget {
                background: transparent;
                border: none;
                color: #b5b9c0;
            }

            QTreeWidget::item:selected {
                background: #20242b;
                color: #ffffff;
                border-radius: 6px;
            }
        """)

    def _build_nav_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("NotesNavPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        title = QLabel("Навигация")
        title.setStyleSheet("color:#c7cbd3; font-size:12px; font-weight:600;")
        layout.addWidget(title)

        self.nav_search = QLineEdit()
        self.nav_search.setPlaceholderText("Поиск заметок…")
        layout.addWidget(self.nav_search)

        filters = QFrame()
        filters_layout = QVBoxLayout(filters)
        filters_layout.setContentsMargins(0, 0, 0, 0)
        filters_layout.setSpacing(6)

        self.filters_group = QButtonGroup(self)
        self.filters_group.setExclusive(True)

        def filter_btn(text: str) -> QToolButton:
            btn = QToolButton()
            btn.setText(text)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setAutoRaise(True)
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
            self.filters_group.addButton(btn)
            return btn

        self.btn_filter_all = filter_btn("Все")
        self.btn_filter_fav = filter_btn("Избранные ⭐")
        self.btn_filter_recent = filter_btn("Последние")
        self.btn_filter_project = filter_btn("По проекту")
        self.btn_filter_tag = filter_btn("По тегу")
        self.btn_filter_all.setChecked(True)

        filters_layout.addWidget(self.btn_filter_all)
        filters_layout.addWidget(self.btn_filter_fav)
        filters_layout.addWidget(self.btn_filter_recent)
        filters_layout.addWidget(self.btn_filter_project)
        filters_layout.addWidget(self.btn_filter_tag)
        layout.addWidget(filters)

        tree_label = QLabel("Структура")
        tree_label.setStyleSheet("color:#8c9097; font-size:11px;")
        layout.addWidget(tree_label)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(14)
        self.tree.setAnimated(True)
        self.tree.setDragDropMode(QAbstractItemView.DragDropMode.NoDragDrop)
        # TODO: поддержка drag & drop для вложенности и перемещения заметок.

        projects = QTreeWidgetItem(["Проекты"])
        projects.setExpanded(True)
        for name in ["MindNavigator", "Discovery", "Design", "Platform", "Delivery"]:
            projects.addChild(QTreeWidgetItem([name]))

        tags = QTreeWidgetItem(["Теги"])
        tags.setExpanded(True)
        for name in ["product", "ux", "backend", "sync", "release"]:
            tags.addChild(QTreeWidgetItem([f"#{name}"]))

        self.tree.addTopLevelItem(projects)
        self.tree.addTopLevelItem(tags)
        layout.addWidget(self.tree, 1)

        quick = QFrame()
        quick_layout = QHBoxLayout(quick)
        quick_layout.setContentsMargins(0, 0, 0, 0)
        quick_layout.setSpacing(6)
        quick_label = QLabel("Быстрые действия")
        quick_label.setStyleSheet("color:#8c9097; font-size:11px;")
        quick_layout.addWidget(quick_label)
        quick_layout.addStretch(1)
        quick_btn = QToolButton()
        quick_btn.setIcon(qta.icon("fa5s.plus", color="#cfcfcf"))
        quick_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        quick_btn.setAutoRaise(True)
        self.quick_new_btn = quick_btn
        quick_layout.addWidget(quick_btn)
        layout.addWidget(quick)

        return panel

    def _build_list_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("NotesListPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        header = QFrame()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        self.list_title = QLabel("Заметки")
        self.list_title.setStyleSheet("color:#c7cbd3; font-size:12px; font-weight:600;")
        header_layout.addWidget(self.list_title)
        header_layout.addStretch(1)

        self.list_hint = QLabel("Categories view")
        self.list_hint.setStyleSheet("color:#6e727a; font-size:10px;")
        header_layout.addWidget(self.list_hint)
        layout.addWidget(header)

        quick_row = QFrame()
        quick_row.setObjectName("NotesQuickRow")
        quick_layout = QHBoxLayout(quick_row)
        quick_layout.setContentsMargins(0, 0, 0, 0)
        quick_layout.setSpacing(6)

        self.quick_category_btn = QToolButton()
        self.quick_category_btn.setText("Категория")
        self.quick_category_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        self.quick_category_label = QLabel("Все категории")
        self.quick_category_label.setObjectName("NotesQuickCategory")
        self.quick_category_label.setStyleSheet("color:#9ea3ac; font-size:11px;")

        self.quick_title_input = QLineEdit()
        self.quick_title_input.setPlaceholderText("Быстрое создание заметки…")

        self.quick_create_btn = QToolButton()
        self.quick_create_btn.setText("Создать")
        self.quick_create_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        quick_layout.addWidget(self.quick_category_btn)
        quick_layout.addWidget(self.quick_category_label)
        quick_layout.addWidget(self.quick_title_input, 1)
        quick_layout.addWidget(self.quick_create_btn)
        layout.addWidget(quick_row)

        self.list_view = QListView()
        self.list_view.setObjectName("NotesGrid")
        self.list_view.setViewMode(QListView.ViewMode.ListMode)
        self.list_view.setResizeMode(QListView.ResizeMode.Adjust)
        self.list_view.setSpacing(6)
        self.list_view.setUniformItemSizes(False)
        self.list_view.setWordWrap(True)
        self.list_view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list_view.setVerticalScrollMode(QListView.ScrollMode.ScrollPerPixel)
        self.list_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list_view.setMouseTracking(True)
        self.list_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        layout.addWidget(self.list_view, 1)

        self.empty_state = QFrame()
        empty_layout = QVBoxLayout(self.empty_state)
        empty_layout.setContentsMargins(0, 0, 0, 0)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_title = QLabel("Нет заметок")
        empty_title.setStyleSheet("color:#c7cbd3; font-size:14px; font-weight:600;")
        empty_desc = QLabel(
            "Создайте заметку через + или используйте поиск, чтобы быстро найти нужное."
        )
        empty_desc.setStyleSheet("color:#7b7f86; font-size:11px;")
        empty_desc.setWordWrap(True)
        empty_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_desc.setMaximumWidth(220)
        empty_layout.addWidget(empty_title)
        empty_layout.addWidget(empty_desc)
        layout.addWidget(self.empty_state)
        self.empty_state.hide()

        return panel

    def _build_editor_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("NotesEditorPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self.editor_stack = QStackedWidget()
        layout.addWidget(self.editor_stack, 1)

        empty = QFrame()
        empty_layout = QVBoxLayout(empty)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_title = QLabel("Выберите заметку")
        empty_title.setStyleSheet("color:#c7cbd3; font-size:14px; font-weight:600;")
        empty_hint = QLabel(
            "Создайте новую заметку или выберите карточку слева. Zen-mode скрывает навигацию и список."
        )
        empty_hint.setStyleSheet("color:#7b7f86; font-size:11px;")
        empty_hint.setWordWrap(True)
        empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_hint.setMaximumWidth(260)
        empty_layout.addWidget(empty_title)
        empty_layout.addWidget(empty_hint)

        editor = QFrame()
        editor_layout = QVBoxLayout(editor)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.setSpacing(8)

        breadcrumbs = QLabel("Проект → Заметка")
        breadcrumbs.setStyleSheet("color:#7b7f86; font-size:10px;")
        self.breadcrumbs_label = breadcrumbs
        editor_layout.addWidget(breadcrumbs)

        title_row = QHBoxLayout()
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Заголовок заметки")
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("Теги: #ux #sync")
        self.tags_edit.setFixedWidth(180)
        title_row.addWidget(self.title_edit, 1)
        title_row.addWidget(self.tags_edit)
        editor_layout.addLayout(title_row)

        self.editor = QTextEdit()
        self.editor.setPlaceholderText(
            "Markdown (подготовка)\n- чекбоксы\n- ссылки [[note]]\n- code block"
        )
        editor_layout.addWidget(self.editor, 1)

        status_row = QHBoxLayout()
        self.autosave_label = QLabel("Автосохранение: включено")
        self.autosave_label.setStyleSheet("color:#6e727a; font-size:10px;")
        status_row.addWidget(self.autosave_label)
        status_row.addStretch(1)
        editor_layout.addLayout(status_row)

        self.editor_stack.addWidget(empty)
        self.editor_stack.addWidget(editor)

        return panel

    def _wire_logic(self):
        self.model = NotesModel(self)
        self.controller = NotesController(self.model, self._state, self)
        self.controller.note_open_requested.connect(self._load_note_into_editor)

        self.list_view.setModel(self.model)
        self.list_view.setItemDelegate(NoteCardDelegate(self.list_view))
        self._smooth_scroll_controllers = [
            attach_smooth_scroll(self.tree),
            attach_smooth_scroll(self.list_view),
            attach_smooth_scroll(self.editor),
        ]

        self.filters_group.buttonClicked.connect(self._on_filter_changed)

        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(250)
        self.nav_search.textChanged.connect(self._on_search_changed)
        self.search_timer.timeout.connect(self._apply_search)

        self.tree.itemClicked.connect(self._on_tree_item_clicked)
        self.list_view.customContextMenuRequested.connect(self._open_context_menu)
        self.list_view.clicked.connect(self._on_note_clicked)

        self.btn_new_note.clicked.connect(self.controller.create_note)
        self.quick_new_btn.clicked.connect(self.controller.create_note)
        self.quick_create_btn.clicked.connect(self._create_note_from_quick_form)
        self.quick_category_btn.clicked.connect(self._open_quick_category_menu)
        self.btn_export.clicked.connect(self._export_notes_csv)
        self.btn_import.clicked.connect(self._import_notes_csv)

        self.btn_toggle_left.clicked.connect(self._toggle_left_panel)
        self.btn_toggle_right.clicked.connect(self._toggle_right_panel)
        self.btn_zen.toggled.connect(self._toggle_zen_mode)

        QShortcut(QKeySequence("Ctrl+N"), self, self.controller.create_note)
        QShortcut(QKeySequence("Ctrl+F"), self, self.nav_search.setFocus)
        QShortcut(QKeySequence("Ctrl+S"), self, self._manual_save)

        self.title_edit.textChanged.connect(self._update_note_title)
        self.tags_edit.textChanged.connect(self._update_note_tags)
        self.editor.textChanged.connect(self._update_note_body)

        self.controller.initialize()
        self.controller.start_autosave()
        self._set_quick_category(None)

    def set_project_filter(self, project: Optional[str]) -> None:
        """Устанавливает фильтр по проекту из внешней навигации."""
        self.controller.set_project_filter(project)
        self._refresh_empty_state()

    def set_task_filter(self, task_id: Optional[int]) -> None:
        """Устанавливает фильтр по задаче из внешней навигации."""
        self.controller.set_task_filter(task_id)
        self._refresh_empty_state()

    def _on_filter_changed(self):
        btn = self.filters_group.checkedButton()
        if not btn:
            return
        self.controller.set_filter(btn.text().replace(" ⭐", ""))
        if btn is not self.btn_filter_project:
            self._set_quick_category(None)
        self._refresh_empty_state()

    def _on_search_changed(self):
        self.search_timer.start()

    def _apply_search(self):
        self.controller.set_search(self.nav_search.text())
        self._refresh_empty_state()

    def _on_tree_item_clicked(self, item: QTreeWidgetItem, column: int):
        text = item.text(column)
        parent = item.parent()
        if not parent:
            return
        if parent.text(0) == "Проекты":
            self.controller.set_project_filter(text)
            self.btn_filter_project.setChecked(True)
            self._set_quick_category(text)
        if parent.text(0) == "Теги":
            tag = text.lstrip("#")
            self.controller.set_tag_filter(tag)
            self.btn_filter_tag.setChecked(True)
            self._set_quick_category(None)
        self._refresh_empty_state()

    def _open_context_menu(self, point):
        index = self.list_view.indexAt(point)
        if not index.isValid() or index.data(NoteRoles.RowType) != "note":
            return
        note_id = index.data(NoteRoles.NoteId)
        menu = QMenu(self)
        open_action = menu.addAction("Открыть")
        rename_action = menu.addAction("Переименовать")
        fav_action = menu.addAction("В избранное")
        delete_action = menu.addAction("Удалить")

        action = menu.exec(self.list_view.mapToGlobal(point))
        if action == open_action:
            self.controller.open_note(note_id)
        elif action == rename_action:
            self.title_edit.setFocus()
        elif action == fav_action:
            self.controller.toggle_favorite(note_id)
        elif action == delete_action:
            self.controller.delete_note(note_id)
            self._refresh_empty_state()

    def _on_note_clicked(self, index: QModelIndex):
        if index.data(NoteRoles.RowType) != "note":
            return
        note_id = index.data(NoteRoles.NoteId)
        self.controller.open_note(note_id)

    def _load_note_into_editor(self, note_id: int):
        note = self.model.note_by_id(note_id)
        if not note:
            self.editor_stack.setCurrentIndex(0)
            return
        self.editor_stack.setCurrentIndex(1)
        self.title_edit.blockSignals(True)
        self.tags_edit.blockSignals(True)
        self.editor.blockSignals(True)

        self.breadcrumbs_label.setText(f"{note.project} → {note.title}")
        self.title_edit.setText(note.title)
        self.tags_edit.setText(" ".join(f"#{t}" for t in note.tags))
        self.editor.setPlainText(note.preview)

        self.title_edit.blockSignals(False)
        self.tags_edit.blockSignals(False)
        self.editor.blockSignals(False)

    def _update_note_title(self):
        if not self._state.selected_note_id:
            return
        self.controller.rename_note(self._state.selected_note_id, self.title_edit.text())

    def _update_note_tags(self):
        if not self._state.selected_note_id:
            return
        tags = [tag.strip("#") for tag in self.tags_edit.text().split() if tag.strip()]
        note = self.model.note_by_id(self._state.selected_note_id)
        if not note:
            return
        self.model.update_note(self._state.selected_note_id, note.title, note.preview, tags)

    def _update_note_body(self):
        if not self._state.selected_note_id:
            return
        note = self.model.note_by_id(self._state.selected_note_id)
        if not note:
            return
        preview = normalize_note_body(self.editor.toPlainText())
        self.model.update_note(self._state.selected_note_id, note.title, preview, note.tags)

    def _toggle_left_panel(self):
        self.nav_panel.setVisible(not self.nav_panel.isVisible())

    def _toggle_right_panel(self):
        self.editor_panel.setVisible(not self.editor_panel.isVisible())

    def _toggle_zen_mode(self, enabled: bool):
        if enabled:
            self.nav_panel.hide()
            self.list_panel.hide()
        else:
            self.nav_panel.show()
            self.list_panel.show()

    def _manual_save(self):
        self.autosave_label.setText("Автосохранение: сохранено")

    def _set_quick_category(self, category: Optional[str]) -> None:
        normalized = normalize_note_category(category or "") if category else None
        if normalized is None:
            self.quick_category_label.setText("Все категории")
            self.quick_category_label.setProperty("quick_category", None)
            return
        self.quick_category_label.setText(normalized)
        self.quick_category_label.setProperty("quick_category", normalized)

    def _open_quick_category_menu(self) -> None:
        menu = QMenu(self)
        action_all = menu.addAction("Все категории")
        menu.addSeparator()
        actions = {}
        for project in self.model.projects():
            action = menu.addAction(project)
            actions[action] = project
        chosen = menu.exec(self.quick_category_btn.mapToGlobal(self.quick_category_btn.rect().bottomLeft()))
        if chosen is None:
            return
        if chosen == action_all:
            self.controller.set_project_filter(None)
            self.btn_filter_all.setChecked(True)
            self._set_quick_category(None)
            self._refresh_empty_state()
            return
        selected_project = actions.get(chosen)
        if selected_project is None:
            return
        self.controller.set_project_filter(selected_project)
        self.btn_filter_project.setChecked(True)
        self._set_quick_category(selected_project)
        self._refresh_empty_state()

    def _create_note_from_quick_form(self) -> None:
        title = (self.quick_title_input.text() or "").strip() or "Новая заметка"
        quick_category = self.quick_category_label.property("quick_category")
        project = quick_category if isinstance(quick_category, str) and quick_category else "Inbox"
        self.controller.create_note(title=title, project=project)
        self.quick_title_input.clear()
        self._refresh_empty_state()

    def _refresh_empty_state(self):
        if self.model.rowCount() == 0 and not self.model.is_loading():
            self.empty_state.show()
        else:
            self.empty_state.hide()
        quick_category = self.quick_category_label.property("quick_category")
        if isinstance(quick_category, str) and quick_category not in self.model.projects():
            self._set_quick_category(None)

    def _export_notes_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Notes",
            "notes_export.csv",
            "CSV (*.csv)",
        )
        if not path:
            return
        rows = export_notes_rows(self._db.fetch_notes())
        if not rows:
            QMessageBox.information(self, "Notes", "Нет данных для экспорта.")
            return
        try:
            self._csv_service.export_to_file(path, rows, fieldnames=NOTES_CSV_FIELDS)
        except CsvTransferError as exc:
            QMessageBox.warning(self, "Notes", f"Export failed: {exc}")
            return
        QMessageBox.information(self, "Notes", "Экспорт завершен.")

    def _import_notes_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Notes",
            "",
            "CSV (*.csv)",
        )
        if not path:
            return
        try:
            rows = self._csv_service.import_from_file(path)
        except CsvTransferError as exc:
            QMessageBox.warning(self, "Notes", f"Import failed: {exc}")
            return
        result = import_notes_rows(self._db, rows)
        self.model.reload()
        self._refresh_empty_state()
        QMessageBox.information(
            self,
            "Notes",
            f"Импорт завершен: {result.imported}, пропущено: {result.skipped}.",
        )

__all__ = ["NoteWorkspace"]
