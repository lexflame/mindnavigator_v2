"""MapsListWorkspace class module for maps workspace."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403
from .map_edit_dialog import MapEditDialog
from .map_editor_workspace import MapEditorWorkspace
from .marker_search_model import MarkerSearchModel
from .maps_item_delegate import MapsItemDelegate
from .maps_list_view import MapsListView
from .maps_model import MapsModel

class MapsListWorkspace(QWidget):
    def __init__(self, parent=None):
        # Инициализируем рабочую область списка карт.
        super().__init__(parent)
        # Основные настройки рабочей области списка карт.
        self.setObjectName("MapsWorkspace")

        self._db = get_database()
        self._map_fullscreen_active = False

        # Вертикальная компоновка всего экрана.
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        self.stack = QStackedWidget()
        root.addWidget(self.stack)

        # Страница со списком карт.
        list_page = QWidget()
        list_layout = QVBoxLayout(list_page)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(10)

        # Блок создания новой карты.
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

        # Блок выбора размеров тайлов.
        tiles_block = QFrame()
        tiles_block.setObjectName("MapsTilesBlock")
        tiles_layout = QHBoxLayout(tiles_block)
        tiles_layout.setContentsMargins(6, 2, 6, 2)
        tiles_layout.setSpacing(6)

        tiles_label = QLabel("Тайлы")
        tiles_label.setObjectName("MapsTilesLabel")

        self.tiles_w = QSpinBox()
        self.tiles_w.setRange(1, 512)
        self.tiles_w.setValue(24)
        self.tiles_w.setFixedWidth(70)

        self.tiles_h = QSpinBox()
        self.tiles_h.setRange(1, 512)
        self.tiles_h.setValue(18)
        self.tiles_h.setFixedWidth(70)

        tiles_layout.addWidget(tiles_label)
        tiles_layout.addWidget(QLabel("W"))
        tiles_layout.addWidget(self.tiles_w)
        tiles_layout.addWidget(QLabel("H"))
        tiles_layout.addWidget(self.tiles_h)

        self.btn_add = QToolButton()
        self.btn_add.setText("Создать")
        self.btn_add.setCursor(Qt.CursorShape.PointingHandCursor)

        create_layout.addWidget(self.new_title, 1)
        create_layout.addWidget(self.new_desc, 1)
        create_layout.addWidget(self.new_project)
        create_layout.addWidget(self.new_tiles_path, 1)
        create_layout.addWidget(self.btn_tiles_path)
        create_layout.addWidget(tiles_block)
        create_layout.addWidget(self.btn_add)

        list_layout.addWidget(create)

        # Верхняя панель фильтров.
        top = QFrame()
        top.setObjectName("MapsTopbar")
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(10, 8, 10, 8)
        top_layout.setSpacing(8)

        self.tabs_group = QButtonGroup(self)
        self.tabs_group.setExclusive(True)

        def tab_btn(text: str) -> QToolButton:
            # Создает кнопку вкладки фильтра.
            tab_button = QToolButton()
            tab_button.setText(text)
            tab_button.setCheckable(True)
            tab_button.setCursor(Qt.CursorShape.PointingHandCursor)
            tab_button.setAutoRaise(True)
            self.tabs_group.addButton(tab_button)
            return tab_button

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

        # Список карт.
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

        for b in self.tabs_group.buttons():
            b.clicked.connect(self._on_tab_changed)

        self.search.textChanged.connect(self.model.set_search)
        self.filter_project.currentTextChanged.connect(self._on_project_changed)
        self.btn_add.clicked.connect(self._on_create_map)
        self.new_title.returnPressed.connect(self._on_create_map)
        self.list.editRequested.connect(self._on_edit_map)
        self.list.openRequested.connect(self._on_open_map)
        # Страница редактора карты.
        self.editor_workspace = MapEditorWorkspace()
        self.editor_workspace.fullscreenToggled.connect(self._on_map_fullscreen_toggled)
        self.editor_workspace.markersChanged.connect(self._refresh_marker_search)
        self.editor_header = QFrame()
        self.editor_header.setObjectName("MapEditorHeader")
        header_layout = QHBoxLayout(self.editor_header)
        header_layout.setContentsMargins(10, 6, 10, 6)
        header_layout.setSpacing(8)

        self.btn_back = QToolButton()
        self.btn_back.setText("Назад к списку")
        self.btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_back.clicked.connect(lambda: self.stack.setCurrentWidget(list_page))
        self.map_title = QLabel("Редактор карты")
        self.map_title.setObjectName("MapEditorTitle")
        header_layout.addWidget(self.btn_back)
        # Поиск по маркерам на карте.
        self.marker_search = QLineEdit()
        self.marker_search.setObjectName("MapMarkerSearch")
        self.marker_search.setPlaceholderText("Поиск меток…")
        self.marker_search.setFixedWidth(260)
        self.marker_search.setClearButtonEnabled(True)
        self.marker_search.installEventFilter(self)

        # Выпадающий список результатов поиска.
        self.marker_search_results = QListView(self)
        self.marker_search_results.setObjectName("MapMarkerSearchResults")
        self.marker_search_results.setFixedWidth(260)
        self.marker_search_results.setFixedHeight(180)
        self.marker_search_results.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.marker_search_results.setVisible(False)
        self.marker_search_results.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.marker_search_model = MarkerSearchModel(self.marker_search_results)
        self.marker_search_results.setModel(self.marker_search_model)

        search_container = QFrame()
        search_container.setObjectName("MapMarkerSearchContainer")
        search_layout = QVBoxLayout(search_container)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(4)
        search_layout.addWidget(self.marker_search)
        header_layout.addWidget(search_container)
        header_layout.addWidget(self.map_title)
        header_layout.addStretch(1)

        self.marker_search.textChanged.connect(self._on_marker_search_changed)
        self.marker_search_results.clicked.connect(self._on_marker_search_selected)

        editor_page = QWidget()
        editor_layout = QVBoxLayout(editor_page)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.setSpacing(8)
        editor_layout.addWidget(self.editor_header)
        editor_layout.addWidget(self.editor_workspace, 1)

        self.stack.addWidget(list_page)
        self.stack.addWidget(editor_page)
        self.stack.setCurrentWidget(list_page)

        # Оверлей загрузки карты.
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

        # Стили рабочей области.
        self.setStyleSheet("""
            QWidget#MapsWorkspace { background: #16171a; }

            QFrame#MapsCreateBar {
                background: #1b1c1f;
                border: 1px solid #2a2b2f;
            }

            QFrame#MapsCreateBar QLineEdit {
                background: #131417;
                border: 1px solid #2a2b2f;
                padding: 6px 8px;
                color: #e6e6e6;
            }

            QFrame#MapsCreateBar QComboBox {
                background: #131417;
                border: 1px solid #2a2b2f;
                padding: 4px 6px;
                color: #e6e6e6;
            }

            QFrame#MapsCreateBar QFrame#MapsTilesBlock {
                background: #131417;
                border: 1px solid #2a2b2f;
                border-radius: 8px;
            }

            QFrame#MapsCreateBar QFrame#MapsTilesBlock QLabel {
                color: #cfcfcf;
                padding: 0 4px;
            }

            QFrame#MapsCreateBar QFrame#MapsTilesBlock QSpinBox {
                background: transparent;
                border: none;
                padding: 4px 6px;
                color: #e6e6e6;
            }

            QFrame#MapsCreateBar QToolButton {
                background: #2a2b2f;
                border: 1px solid #3a3b40;
                padding: 6px 10px;
                border-radius: 6px;
            }
            QFrame#MapsCreateBar QToolButton:hover { background: #34363b; }

            QFrame#MapsTopbar {
                background: #1b1c1f;
                border: 1px solid #2a2b2f;
            }

            QToolButton {
                color: #cfcfcf;
                border: none;
                padding: 6px 8px;
            }
            QToolButton:checked {
                background: #2a2b2f;
            }

            QComboBox, QLineEdit {
                background: #202127;
                color: #cfcfcf;
                border: 1px solid #2a2b2f;
                padding: 6px 8px;
            }

            QListView#MapsList {
                background: #16171a;
                border: 1px solid #2a2b2f;
            }

            QFrame#MapEditorHeader {
                background: #1b1c1f;
                border: 1px solid #2a2b2f;
                border-radius: 6px;
            }

            QFrame#MapEditorHeader QToolButton {
                background: #2a2b2f;
                border: 1px solid #3a3b40;
                padding: 6px 10px;
                border-radius: 6px;
                color: #e6e6e6;
            }

            QLineEdit#MapMarkerSearch {
                background: #202127;
                color: #cfcfcf;
                border: 1px solid #2a2b2f;
                padding: 6px 8px;
                border-radius: 6px;
            }

            QListView#MapMarkerSearchResults {
                background: #1b1c1f;
                border: 1px solid #2a2b2f;
                border-radius: 6px;
                color: #e6e6e6;
            }

            QListView#MapMarkerSearchResults::item {
                padding: 6px 8px;
            }

            QListView#MapMarkerSearchResults::item:selected {
                background: #2a2b2f;
            }

            QLabel#MapEditorTitle {
                color: #e6e6e6;
                font-size: 14px;
                font-weight: 600;
            }

            QFrame#MapsLoadingOverlay {
                background: rgba(8, 9, 12, 0.75);
            }

            QFrame#MapsLoadingCard {
                background: #1b1c1f;
                border: 1px solid #2a2b2f;
                border-radius: 12px;
            }

            QLabel#MapsLoadingTitle {
                color: #f2f2f2;
                font-size: 16px;
                font-weight: 600;
            }

            QLabel#MapsLoadingHint {
                color: #cfcfcf;
                font-size: 12px;
            }

            QProgressBar#MapsLoadingBar {
                background: #2a2b2f;
                border: none;
                border-radius: 4px;
            }

            QProgressBar#MapsLoadingBar::chunk {
                background: #5fa8ff;
                border-radius: 4px;
            }
        """)

    def resizeEvent(self, event):
        # Обновляем геометрию оверлея и позицию выпадающего списка.
        super().resizeEvent(event)
        if hasattr(self, "loading_overlay"):
            self.loading_overlay.setGeometry(self.rect())
        if hasattr(self, "marker_search_results") and self.marker_search_results.isVisible():
            self._position_marker_search_results()

    @staticmethod
    def _project_titles() -> List[str]:
        # Получаем список названий проектов для фильтра.
        projects = get_database().fetch_projects()
        titles = sorted({p.title for p in projects})
        return titles

    def _refresh_projects(self) -> None:
        # Обновляем список проектов в комбобоксе создания.
        self.new_project.clear()
        titles = self._project_titles()
        self.new_project.addItems(titles or ["Без проекта"])

    def _cloud_storage_root(self) -> str:
        # Корневая папка облачного хранилища.
        return self._db.get_setting("cloud_storage_path", default="")

    def _on_pick_tiles_path(self) -> None:
        # Открываем диалог выбора каталога тайлов.
        current = self.new_tiles_path.text().strip()
        start_dir = current or self._cloud_storage_root() or str(Path.home())
        selected = QFileDialog.getExistingDirectory(
            self,
            "Выберите каталог хранения тайлов",
            start_dir,
        )
        if not selected:
            return
        self.new_tiles_path.setText(selected)

    def _on_tab_changed(self) -> None:
        # Применяем фильтрацию по вкладкам.
        if self.tab_project.isChecked():
            current = self.filter_project.currentText()
            if current != "Все проекты":
                self.model.set_project_filter(current)
                return
        self.model.set_project_filter(None)

    def _on_project_changed(self, text: str) -> None:
        # Реагируем на смену проекта в фильтре.
        if self.tab_project.isChecked() and text != "Все проекты":
            self.model.set_project_filter(text)
        else:
            self.model.set_project_filter(None)

    def set_project_filter(self, project: Optional[str]) -> None:
        """Устанавливает фильтр карт из внешней навигации."""
        # Синхронизируем фильтр и вкладки с внешним выбором.
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
        # Создаем карту по введенным данным.
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
        # Открываем диалог редактирования выбранной карты.
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
        # Открываем редактор карты и запускаем загрузку.
        if not index.isValid():
            return
        map_id = index.data(MapRoles.Id)
        title = index.data(MapRoles.Title) or "Карта"
        project = index.data(MapRoles.Project) or ""
        if project:
            self.map_title.setText(f"{title} · {project}")
            self.loading_title.setText(f"Загрузка карты «{title}»")
        else:
            self.map_title.setText(title)
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
            lambda: self._load_map_with_overlay(
                map_id,
                tiles_path,
                tiles_height,
                tiles_width,
            ),
        )

    def _load_map_with_overlay(self, map_id: int, tiles_path: str, tiles_h: int, tiles_w: int) -> None:
        # Загружаем карту и скрываем оверлей после подготовки.
        self.editor_workspace.load_map(map_id, tiles_path, tiles_h, tiles_w)
        QTimer.singleShot(0, self._hide_loading_overlay)

    def _show_loading_overlay(self) -> None:
        # Показываем оверлей ожидания.
        self.loading_overlay.setGeometry(self.rect())
        self.loading_overlay.raise_()
        self.loading_overlay.setVisible(True)
        self.loading_overlay.repaint()

    def _hide_loading_overlay(self) -> None:
        # Скрываем оверлей ожидания.
        self.loading_overlay.setVisible(False)

    def _on_marker_search_changed(self, text: str) -> None:
        # Фильтруем маркеры по строке поиска.
        query = (text or "").strip()
        if not query:
            self.marker_search_model.set_markers([])
            self.marker_search_results.setVisible(False)
            return
        matches = self._filter_markers(query)
        self.marker_search_model.set_markers(matches)
        if matches:
            self._show_marker_search_results()
        else:
            self.marker_search_results.setVisible(False)

    def _refresh_marker_search(self) -> None:
        # Обновляем результаты поиска, если строка не пуста.
        text = self.marker_search.text()
        if text.strip():
            self._on_marker_search_changed(text)

    def _filter_markers(self, query: str) -> List[Marker]:
        # Возвращаем список маркеров, соответствующих запросу.
        needle = query.lower()
        matches = []
        for marker in self.editor_workspace.markers():
            hay = f"{marker.name} {marker.type} {marker.description} {marker.properties}".lower()
            if needle in hay:
                matches.append(marker)
        return matches

    def _on_marker_search_selected(self, index: QModelIndex) -> None:
        # Фокусируемся на выбранном маркере.
        marker = index.data(MarkerSearchModel.MarkerRole)
        if not marker:
            return
        self.editor_workspace.focus_marker(marker, zoom_boost=4.0)
        self.marker_search_results.setVisible(False)

    def _on_map_fullscreen_toggled(self, enabled: bool) -> None:
        # Переключаем полноэкранный режим у окна или локально.
        window = self.window()
        if window and hasattr(window, "set_map_fullscreen"):
            window.set_map_fullscreen(enabled)
        else:
            self.set_map_fullscreen_state(enabled)

    def set_map_fullscreen_state(self, enabled: bool) -> None:
        # Сохраняем локальное состояние полноэкранного режима.
        if self._map_fullscreen_active == enabled:
            return
        self._map_fullscreen_active = enabled
        self.editor_header.setVisible(True)
        if enabled:
            self.marker_search_results.setVisible(False)
        self.editor_workspace.set_fullscreen_state(enabled)

    def set_nav_collapsed_state(self, collapsed: bool) -> None:
        # Обновляем параметры редактора карты при сворачивании навигации.
        self.editor_workspace.set_nav_collapsed_state(collapsed)

    def _show_marker_search_results(self) -> None:
        # Показываем выпадающий список результатов.
        self._position_marker_search_results()
        self.marker_search_results.setVisible(True)
        self.marker_search_results.raise_()

    def _position_marker_search_results(self) -> None:
        # Позиционируем результаты под полем поиска.
        if not self.marker_search.isVisible():
            return
        self.marker_search_results.setFixedWidth(self.marker_search.width())
        global_pos = self.marker_search.mapToGlobal(QPoint(0, self.marker_search.height()))
        self.marker_search_results.move(global_pos)

    def _clear_marker_search(self) -> None:
        # Очищаем строку поиска и скрываем результаты.
        self.marker_search.clear()
        self.marker_search_results.setVisible(False)

    def eventFilter(self, obj, event) -> bool:
        # Обрабатываем Esc в поле поиска, чтобы скрыть результаты.
        if obj is self.marker_search and event.type() == QEvent.Type.KeyPress and hasattr(event, "key"):
            if event.key() == Qt.Key.Key_Escape:
                if self.marker_search.text().strip() or self.marker_search_results.isVisible():
                    self._clear_marker_search()
                    return True
        return super().eventFilter(obj, event)

__all__ = ["MapsListWorkspace"]
