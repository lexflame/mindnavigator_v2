"""MapsListWorkspace class module for maps workspace."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403
from PySide6.QtGui import QKeySequence, QShortcut
from .map_edit_dialog import MapEditDialog
from .map_editor_workspace import MapEditorWorkspace
from .marker_search_model import MarkerSearchModel
from .maps_item_delegate import MapsItemDelegate
from .maps_list_view import MapsListView
from .maps_model import MapsModel
from mindnavigator.ui.styles import get_theme_palette


class MapsListWorkspace(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._theme_mode = "dark"
        self.setObjectName("MapsWorkspace")
        self._db = get_database()
        self._map_fullscreen_active = False

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        self.stack = QStackedWidget()
        root.addWidget(self.stack)

        list_page = self._build_list_page()
        editor_page = self._build_editor_page(list_page)
        self.stack.addWidget(list_page)
        self.stack.addWidget(editor_page)
        self.stack.setCurrentWidget(list_page)

        self.loading_overlay = QFrame(self)
        self.loading_overlay.setObjectName("MapsLoadingOverlay")
        self.loading_overlay.setVisible(False)
        self.loading_overlay.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        overlay_layout = QVBoxLayout(self.loading_overlay)
        overlay_layout.setContentsMargins(0, 0, 0, 0)
        overlay_layout.addStretch(1)

        overlay_card = QFrame()
        overlay_card.setObjectName("MapsLoadingCard")
        overlay_card_layout = QVBoxLayout(overlay_card)
        overlay_card_layout.setContentsMargins(24, 18, 24, 20)
        overlay_card_layout.setSpacing(12)
        self.loading_title = QLabel("Загрузка карты…")
        self.loading_title.setObjectName("MapsLoadingTitle")
        self.loading_hint = QLabel("Подготавливаем тайлы и маркеры")
        self.loading_hint.setObjectName("MapsLoadingHint")
        self.loading_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_bar = QProgressBar()
        self.loading_bar.setObjectName("MapsLoadingBar")
        self.loading_bar.setRange(0, 0)
        self.loading_bar.setTextVisible(False)
        self.loading_bar.setFixedHeight(8)
        overlay_card_layout.addWidget(self.loading_title, alignment=Qt.AlignmentFlag.AlignCenter)
        overlay_card_layout.addWidget(self.loading_hint, alignment=Qt.AlignmentFlag.AlignCenter)
        overlay_card_layout.addWidget(self.loading_bar)
        overlay_layout.addWidget(overlay_card, alignment=Qt.AlignmentFlag.AlignCenter)
        overlay_layout.addStretch(1)

        QShortcut(QKeySequence("Ctrl+F"), self, activated=self._focus_editor_search)
        self.set_theme_mode("dark")

    def _build_list_page(self) -> QWidget:
        list_page = QWidget()
        list_layout = QVBoxLayout(list_page)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(10)

        create = QFrame()
        create.setObjectName("MapsCreateBar")
        create_layout = QHBoxLayout(create)
        create_layout.setContentsMargins(10, 8, 10, 8)
        create_layout.setSpacing(8)

        self.new_title = QLineEdit()
        self.new_title.setPlaceholderText("Название карты…")
        self.new_desc = QLineEdit()
        self.new_desc.setPlaceholderText("Описание…")
        self.new_project = QComboBox()
        self.new_project.setFixedWidth(200)
        self._refresh_projects()
        self.new_tiles_path = QLineEdit()
        self.new_tiles_path.setPlaceholderText("Каталог хранения тайлов…")

        self.btn_tiles_path = QToolButton()
        self.btn_tiles_path.setText("…")
        self.btn_tiles_path.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tiles_path.clicked.connect(self._on_pick_tiles_path)

        tiles_block = QFrame()
        tiles_block.setObjectName("MapsTilesBlock")
        tiles_layout = QHBoxLayout(tiles_block)
        tiles_layout.setContentsMargins(6, 2, 6, 2)
        tiles_layout.setSpacing(6)
        tiles_layout.addWidget(QLabel("Тайлы"))
        tiles_layout.addWidget(QLabel("W"))
        self.tiles_w = QSpinBox()
        self.tiles_w.setRange(1, 512)
        self.tiles_w.setValue(24)
        self.tiles_w.setFixedWidth(70)
        self.tiles_h = QSpinBox()
        self.tiles_h.setRange(1, 512)
        self.tiles_h.setValue(18)
        self.tiles_h.setFixedWidth(70)
        tiles_layout.addWidget(self.tiles_w)
        tiles_layout.addWidget(QLabel("H"))
        tiles_layout.addWidget(self.tiles_h)

        self.btn_add = QToolButton()
        self.btn_add.setText("Создать")
        self.btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add.clicked.connect(self._on_create_map)

        for widget in (
            (self.new_title, 1),
            (self.new_desc, 1),
            (self.new_project, 0),
            (self.new_tiles_path, 1),
        ):
            create_layout.addWidget(widget[0], widget[1])
        create_layout.addWidget(self.btn_tiles_path)
        create_layout.addWidget(tiles_block)
        create_layout.addWidget(self.btn_add)
        list_layout.addWidget(create)

        top = QFrame()
        top.setObjectName("MapsTopbar")
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(10, 8, 10, 8)
        top_layout.setSpacing(8)

        self.tabs_group = QButtonGroup(self)
        self.tabs_group.setExclusive(True)

        def tab_btn(text: str) -> QToolButton:
            button = QToolButton()
            button.setText(text)
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setAutoRaise(True)
            self.tabs_group.addButton(button)
            return button

        self.tab_all = tab_btn("Все")
        self.tab_project = tab_btn("Проект")
        self.tab_all.setChecked(True)
        top_layout.addWidget(self.tab_all)
        top_layout.addWidget(self.tab_project)
        top_layout.addSpacing(12)

        self.filter_project = QComboBox()
        self.filter_project.setFixedWidth(200)
        self.filter_project.addItem("Все проекты")
        self.filter_project.addItems(self._project_titles())
        top_layout.addWidget(self.filter_project)
        top_layout.addStretch(1)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Поиск…")
        self.search.setFixedWidth(260)
        top_layout.addWidget(self.search)
        list_layout.addWidget(top)

        self.list = MapsListView()
        self.list.setObjectName("MapsList")
        self.list.setUniformItemSizes(False)
        self.list.setVerticalScrollMode(QListView.ScrollMode.ScrollPerPixel)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list.setSelectionMode(QListView.SelectionMode.SingleSelection)
        list_layout.addWidget(self.list, 1)

        self.model = MapsModel(self)
        self.list.setModel(self.model)
        self.delegate = MapsItemDelegate(self.list)
        self.list.setItemDelegate(self.delegate)

        for button in self.tabs_group.buttons():
            button.clicked.connect(self._on_tab_changed)
        self.search.textChanged.connect(self.model.set_search)
        self.filter_project.currentTextChanged.connect(self._on_project_changed)
        self.new_title.returnPressed.connect(self._on_create_map)
        self.list.editRequested.connect(self._on_edit_map)
        self.list.openRequested.connect(self._on_open_map)

        return list_page

    def _build_editor_page(self, list_page: QWidget) -> QWidget:
        self.editor_workspace = MapEditorWorkspace()
        self.editor_workspace.fullscreenToggled.connect(self._on_map_fullscreen_toggled)
        self.editor_workspace.markersChanged.connect(self._refresh_marker_search)

        self.editor_header = QFrame()
        self.editor_header.setObjectName("MapEditorHeader")
        header_layout = QHBoxLayout(self.editor_header)
        header_layout.setContentsMargins(12, 8, 12, 8)
        header_layout.setSpacing(10)

        self.btn_back = QToolButton()
        self.btn_back.setText("Назад к списку")
        self.btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_back.clicked.connect(lambda: self.stack.setCurrentWidget(list_page))
        header_layout.addWidget(self.btn_back)

        self.map_title = QLabel("Редактор карты")
        self.map_title.setObjectName("MapEditorTitle")
        self.map_status = QLabel("Сохранено")
        self.map_status.setObjectName("MapEditorStatus")
        title_layout = QVBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(2)
        title_layout.addWidget(self.map_title)
        title_layout.addWidget(self.map_status)
        header_layout.addLayout(title_layout, 1)

        self.marker_search = QLineEdit()
        self.marker_search.setObjectName("MapMarkerSearch")
        self.marker_search.setPlaceholderText("Поиск меток, объектов, связей...")
        self.marker_search.setFixedWidth(340)
        self.marker_search.setClearButtonEnabled(True)
        self.marker_search.installEventFilter(self)
        header_layout.addWidget(self.marker_search)

        self.map_type_filter = QComboBox()
        self.map_type_filter.setObjectName("MapEditorTypeFilter")
        self.map_type_filter.setFixedWidth(150)
        self.map_type_filter.addItem("Все типы", "all")
        self.map_type_filter.addItem("Метки", "marker")
        self.map_type_filter.addItem("Регионы", "region")
        self.map_type_filter.addItem("Маршруты", "path")
        header_layout.addWidget(self.map_type_filter)

        self.map_menu_btn = QToolButton()
        self.map_menu_btn.setText("⋯")
        self.map_menu_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.map_menu_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self._build_map_menu()
        header_layout.addWidget(self.map_menu_btn)

        self.marker_search_results = QListView(self)
        self.marker_search_results.setObjectName("MapMarkerSearchResults")
        self.marker_search_results.setFixedWidth(340)
        self.marker_search_results.setFixedHeight(220)
        self.marker_search_results.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.marker_search_results.setVisible(False)
        self.marker_search_results.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.marker_search_model = MarkerSearchModel(self.marker_search_results)
        self.marker_search_results.setModel(self.marker_search_model)

        self.marker_search.textChanged.connect(self._on_marker_search_changed)
        self.marker_search_results.clicked.connect(self._on_marker_search_selected)
        self.map_type_filter.currentIndexChanged.connect(self._on_map_type_filter_changed)

        editor_page = QWidget()
        editor_layout = QVBoxLayout(editor_page)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.setSpacing(8)
        editor_layout.addWidget(self.editor_header)
        editor_layout.addWidget(self.editor_workspace, 1)
        return editor_page

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "loading_overlay"):
            self.loading_overlay.setGeometry(self.rect())
        if hasattr(self, "marker_search_results") and self.marker_search_results.isVisible():
            self._position_marker_search_results()

    def set_theme_mode(self, theme_mode: str) -> None:
        self._theme_mode = "light" if str(theme_mode).strip().lower() == "light" else "dark"
        palette = get_theme_palette(self._theme_mode)
        overlay_color = "rgba(8, 9, 12, 0.75)" if self._theme_mode == "dark" else "rgba(235, 241, 250, 0.86)"
        self.setStyleSheet(
            f"""
            QWidget#MapsWorkspace {{ background: {palette.window_bg}; }}

            QFrame#MapsCreateBar,
            QFrame#MapsTopbar,
            QFrame#MapEditorHeader,
            QFrame#MapsLoadingCard {{
                background: {palette.panel_bg};
                border: 1px solid {palette.border};
            }}

            QFrame#MapsCreateBar,
            QFrame#MapsTopbar {{
                border-radius: 10px;
            }}

            QFrame#MapEditorHeader {{
                border-radius: 8px;
            }}

            QFrame#MapsCreateBar QLineEdit,
            QFrame#MapsCreateBar QComboBox {{
                background: {palette.input_alt_bg};
                border: 1px solid {palette.border};
                padding: 6px 8px;
                color: {palette.text};
            }}

            QFrame#MapsCreateBar QFrame#MapsTilesBlock {{
                background: {palette.input_alt_bg};
                border: 1px solid {palette.border};
                border-radius: 8px;
            }}

            QFrame#MapsCreateBar QFrame#MapsTilesBlock QLabel {{
                color: {palette.text};
                padding: 0 4px;
            }}

            QFrame#MapsCreateBar QFrame#MapsTilesBlock QSpinBox {{
                background: transparent;
                border: none;
                padding: 4px 6px;
                color: {palette.text};
            }}

            QFrame#MapsCreateBar QToolButton,
            QFrame#MapEditorHeader QToolButton {{
                background: {palette.elevated_bg};
                border: 1px solid {palette.border_strong};
                padding: 6px 10px;
                border-radius: 8px;
                color: {palette.text};
            }}

            QFrame#MapsCreateBar QToolButton:hover,
            QFrame#MapEditorHeader QToolButton:hover {{
                background: {palette.selection_bg};
                color: {palette.selection_text};
            }}

            QToolButton {{
                color: {palette.text};
                border: none;
                padding: 6px 8px;
            }}

            QToolButton:checked {{
                background: {palette.selection_bg};
                color: {palette.selection_text};
            }}

            QComboBox, QLineEdit {{
                background: {palette.input_bg};
                color: {palette.text};
                border: 1px solid {palette.border};
                padding: 6px 8px;
            }}

            QListView#MapsList {{
                background: {palette.window_bg};
                border: 1px solid {palette.border};
            }}

            QLineEdit#MapMarkerSearch {{
                background: {palette.input_bg};
                color: {palette.text};
                border: 1px solid {palette.border};
                padding: 6px 8px;
                border-radius: 8px;
            }}

            QListView#MapMarkerSearchResults {{
                background: {palette.elevated_bg};
                border: 1px solid {palette.border};
                border-radius: 8px;
                color: {palette.text};
            }}

            QListView#MapMarkerSearchResults::item {{
                padding: 8px 10px;
            }}

            QListView#MapMarkerSearchResults::item:selected {{
                background: {palette.selection_bg};
                color: {palette.selection_text};
            }}

            QLabel#MapEditorTitle {{
                color: {palette.text};
                font-size: 15px;
                font-weight: 700;
            }}

            QLabel#MapEditorStatus {{
                color: {palette.dim_text};
                font-size: 11px;
            }}

            QFrame#MapsLoadingOverlay {{
                background: {overlay_color};
            }}

            QFrame#MapsLoadingCard {{
                border-radius: 12px;
            }}

            QLabel#MapsLoadingTitle {{
                color: {palette.text};
                font-size: 16px;
                font-weight: 600;
            }}

            QLabel#MapsLoadingHint {{
                color: {palette.dim_text};
                font-size: 12px;
            }}

            QProgressBar#MapsLoadingBar {{
                background: {palette.border};
                border: none;
                border-radius: 4px;
            }}

            QProgressBar#MapsLoadingBar::chunk {{
                background: {palette.accent};
                border-radius: 4px;
            }}
            """
        )
        if hasattr(self.delegate, "set_theme_mode"):
            self.delegate.set_theme_mode(self._theme_mode)
        self.editor_workspace.set_theme_mode(self._theme_mode)

    @staticmethod
    def _project_titles() -> List[str]:
        projects = get_database().fetch_projects()
        return sorted({project.title for project in projects})

    def _refresh_projects(self) -> None:
        self.new_project.clear()
        titles = self._project_titles()
        self.new_project.addItems(titles or ["Без проекта"])

    def _cloud_storage_root(self) -> str:
        return self._db.get_setting("cloud_storage_path", default="")

    def _on_pick_tiles_path(self) -> None:
        current = self.new_tiles_path.text().strip()
        start_dir = current or self._cloud_storage_root() or str(Path.home())
        selected = QFileDialog.getExistingDirectory(
            self,
            "Выберите каталог хранения тайлов",
            start_dir,
        )
        if selected:
            self.new_tiles_path.setText(selected)

    def _on_tab_changed(self) -> None:
        if self.tab_project.isChecked():
            current = self.filter_project.currentText()
            if current != "Все проекты":
                self.model.set_project_filter(current)
                return
        self.model.set_project_filter(None)

    def _on_project_changed(self, text: str) -> None:
        if self.tab_project.isChecked() and text != "Все проекты":
            self.model.set_project_filter(text)
        else:
            self.model.set_project_filter(None)

    def set_project_filter(self, project: Optional[str]) -> None:
        if project:
            self.tab_project.setChecked(True)
            idx = self.filter_project.findText(project)
            if idx >= 0:
                self.filter_project.setCurrentIndex(idx)
            else:
                self.filter_project.addItem(project)
                self.filter_project.setCurrentText(project)
            self.model.set_project_filter(project)
        else:
            self.tab_all.setChecked(True)
            self.filter_project.setCurrentIndex(0)
            self.model.set_project_filter(None)

    def _on_create_map(self) -> None:
        self.model.add_map(
            self.new_title.text(),
            self.new_desc.text(),
            self.new_project.currentText(),
            self.new_tiles_path.text(),
            self.tiles_h.value(),
            self.tiles_w.value(),
        )
        self.new_title.clear()
        self.new_desc.clear()
        self.new_tiles_path.clear()
        self.new_title.setFocus()

    def _on_edit_map(self, index: QModelIndex) -> None:
        if not index.isValid():
            return
        map_row = MapRow(
            id=index.data(MapRoles.Id),
            title=index.data(MapRoles.Title) or "",
            description=index.data(MapRoles.Description) or "",
            project=index.data(MapRoles.Project) or "",
            tiles_path=index.data(MapRoles.TilesPath) or "",
            tiles_h=index.data(MapRoles.TilesHeight) or 0,
            tiles_w=index.data(MapRoles.TilesWidth) or 0,
        )
        dialog = MapEditDialog(map_row, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            values = dialog.values()
            self.model.update_map(
                map_row.id,
                values["title"],
                values["description"],
                values["project"],
                values["tiles_path"],
                values["tiles_h"],
                values["tiles_w"],
            )

    def _on_open_map(self, index: QModelIndex) -> None:
        if not index.isValid():
            return
        map_id = index.data(MapRoles.Id)
        title = index.data(MapRoles.Title) or "Карта"
        project = index.data(MapRoles.Project) or ""
        self.editor_workspace.set_map_context(title, project)
        self.map_title.setText(f"{title} · {project}" if project else title)
        self.map_status.setText("Сохранено")
        self.loading_title.setText(f"Загрузка карты «{title}»")
        self.stack.setCurrentIndex(1)
        self.marker_search.clear()
        self.marker_search_results.setVisible(False)
        tiles_path = index.data(MapRoles.TilesPath) or ""
        tiles_height = index.data(MapRoles.TilesHeight) or 0
        tiles_width = index.data(MapRoles.TilesWidth) or 0
        self._show_loading_overlay()
        QTimer.singleShot(
            0,
            lambda: self._load_map_with_overlay(map_id, tiles_path, tiles_height, tiles_width),
        )

    def _load_map_with_overlay(self, map_id: int, tiles_path: str, tiles_h: int, tiles_w: int) -> None:
        self.editor_workspace.load_map(map_id, tiles_path, tiles_h, tiles_w)
        QTimer.singleShot(0, self._hide_loading_overlay)

    def _show_loading_overlay(self) -> None:
        self.loading_overlay.setGeometry(self.rect())
        self.loading_overlay.raise_()
        self.loading_overlay.setVisible(True)
        self.loading_overlay.repaint()

    def _hide_loading_overlay(self) -> None:
        self.loading_overlay.setVisible(False)

    def _on_marker_search_changed(self, text: str) -> None:
        query = (text or "").strip()
        if not query:
            self.marker_search_model.set_markers([])
            self.marker_search_results.setVisible(False)
            return
        matches = self._filter_search_results(query)
        if not matches:
            matches = [
                {
                    "kind": "empty",
                    "display": "Ничего не найдено\nПопробуйте изменить запрос или сбросить фильтр типов.",
                }
            ]
        self.marker_search_model.set_markers(matches)
        self._show_marker_search_results()

    def _refresh_marker_search(self) -> None:
        text = self.marker_search.text()
        if text.strip():
            self._on_marker_search_changed(text)

    def _filter_search_results(self, query: str) -> List[dict[str, Any]]:
        filter_key = str(self.map_type_filter.currentData() or "all")
        return self.editor_workspace.search_objects(query, filter_key)

    def _on_marker_search_selected(self, index: QModelIndex) -> None:
        result = index.data(MarkerSearchModel.MarkerRole)
        if not result or (isinstance(result, dict) and result.get("kind") == "empty"):
            return
        self.editor_workspace.focus_search_result(result)
        self.marker_search_results.setVisible(False)

    def _on_map_type_filter_changed(self, _index: int) -> None:
        filter_key = str(self.map_type_filter.currentData() or "all")
        self.editor_workspace.set_visible_object_filter(filter_key)
        self._refresh_marker_search()

    def _on_map_fullscreen_toggled(self, enabled: bool) -> None:
        window = self.window()
        if window and hasattr(window, "set_map_fullscreen"):
            window.set_map_fullscreen(enabled)
        else:
            self.set_map_fullscreen_state(enabled)

    def set_map_fullscreen_state(self, enabled: bool) -> None:
        if self._map_fullscreen_active == enabled:
            return
        self._map_fullscreen_active = enabled
        if enabled:
            self.marker_search_results.setVisible(False)
        self.editor_workspace.set_fullscreen_state(enabled)

    def set_nav_collapsed_state(self, collapsed: bool) -> None:
        self.editor_workspace.set_nav_collapsed_state(collapsed)

    def _show_marker_search_results(self) -> None:
        self._position_marker_search_results()
        self.marker_search_results.setVisible(True)
        self.marker_search_results.raise_()

    def _position_marker_search_results(self) -> None:
        if not self.marker_search.isVisible():
            return
        self.marker_search_results.setFixedWidth(self.marker_search.width())
        global_pos = self.marker_search.mapToGlobal(QPoint(0, self.marker_search.height()))
        self.marker_search_results.move(global_pos)

    def _clear_marker_search(self) -> None:
        self.marker_search.clear()
        self.marker_search_results.setVisible(False)

    def _focus_editor_search(self) -> None:
        if self.stack.currentIndex() != 1:
            return
        self.marker_search.setFocus(Qt.FocusReason.ShortcutFocusReason)
        self.marker_search.selectAll()

    def _build_map_menu(self) -> None:
        menu = QMenu(self.map_menu_btn)
        act_reset = menu.addAction("Сбросить вид")
        act_show_all = menu.addAction("Показать все маркеры")
        menu.addSeparator()
        for text in (
            "Свойства карты",
            "Импорт",
            "Экспорт",
            "Показать / скрыть подписи",
            "Настройки сетки",
        ):
            action = menu.addAction(text)
            action.setEnabled(False)
        act_reset.triggered.connect(self.editor_workspace.reset_view)
        act_show_all.triggered.connect(self.editor_workspace.show_all_objects)
        self.map_menu_btn.setMenu(menu)

    def eventFilter(self, obj, event) -> bool:
        if obj is self.marker_search and event.type() == QEvent.Type.KeyPress and hasattr(event, "key"):
            if event.key() == Qt.Key.Key_Escape:
                if self.marker_search.text().strip() or self.marker_search_results.isVisible():
                    self._clear_marker_search()
                    return True
        return super().eventFilter(obj, event)


__all__ = ["MapsListWorkspace"]
