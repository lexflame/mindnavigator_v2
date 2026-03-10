"""MapEditorWorkspace class module for maps workspace."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403
from .map_canvas import MapCanvas

class MapEditorWorkspace(QWidget):
    fullscreenToggled = Signal(bool)
    markersChanged = Signal()

    def __init__(self, parent=None):
        # Инициализируем рабочую область редактора карты.
        super().__init__(parent)
        # Основные параметры состояния редактора карты.
        self.setObjectName("MapEditorWorkspace")
        self._db = get_database()
        self._tasks_by_id = {}
        self._projects_by_id = {}
        self._notes_by_id = {}
        self._objects_by_id = {}
        self._info_panel_was_visible = False
        self._fullscreen_active = False
        self._nav_collapsed = False
        self._current_map_id: Optional[int] = None
        self._info_marker_id: Optional[int] = None
        self._info_panel_default_width = 520
        self._info_panel_expand_delta = 80
        self._info_panel_expanded_width = 600
        self._info_panel_fullscreen_ratio = 0.35
        self._info_panel_block_save = False
        try:
            saved_width = int(self._db.get_setting("map_info_panel_width", default="").strip() or 0)
        except ValueError:
            saved_width = 0
        if saved_width >= 280:
            self._info_panel_default_width = saved_width
            self._info_panel_expanded_width = saved_width + self._info_panel_expand_delta

        # Корневая компоновка редактора.
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Левая панель с инструментами.
        self.toolbar = QFrame()
        self.toolbar.setObjectName("MapToolbar")
        self.toolbar.setFixedWidth(54)
        toolbar_layout = QVBoxLayout(self.toolbar)
        toolbar_layout.setContentsMargins(6, 8, 6, 8)
        toolbar_layout.setSpacing(8)
        toolbar_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.tool_group = QButtonGroup(self)
        self.tool_group.setExclusive(True)

        def tool_button(icon_name: str, tooltip: str, tool: Optional[MapTool]) -> QToolButton:
            # Вспомогательная функция для создания кнопки инструмента.
            tool_btn_widget = QToolButton()
            tool_btn_widget.setIcon(qta.icon(icon_name, color="#d7d7d7"))
            tool_btn_widget.setIconSize(QSize(20, 20))
            tool_btn_widget.setCheckable(True)
            tool_btn_widget.setToolTip(tooltip)
            tool_btn_widget.setCursor(Qt.CursorShape.PointingHandCursor)
            if tool is not None:
                self.tool_group.addButton(tool_btn_widget)
                tool_btn_widget.clicked.connect(lambda checked=False, t=tool: self._set_tool(t))
            return tool_btn_widget

        # Кнопки инструментов.
        self.btn_select = tool_button("fa5s.mouse-pointer", "Выбрать", MapTool.SELECT)
        self.btn_marker = tool_button("fa5s.map-marker-alt", "Добавить маркер", MapTool.ADD_MARKER)
        self.btn_region = tool_button("fa5s.draw-polygon", "Добавить регион", MapTool.ADD_REGION)
        self.btn_measure = tool_button("fa5s.ruler", "Рисовать путь", MapTool.MEASURE)
        self.btn_grid = tool_button("fa5s.border-all", "Сетка", None)
        self.btn_grid.setCheckable(True)
        self.btn_grid.setChecked(True)
        self.btn_grid.clicked.connect(lambda checked: self.canvas.set_grid_enabled(checked))

        self.btn_fullscreen = tool_button("fa5s.expand", "Полноэкранный режим", None)
        self.btn_fullscreen.setCheckable(True)
        self.btn_fullscreen.clicked.connect(self._on_fullscreen_toggled)

        self.btn_camera = tool_button("fa5s.camera", "Скриншот", None)
        self.btn_camera.setCheckable(False)

        self._tool_buttons = {
            MapTool.SELECT: self.btn_select,
            MapTool.ADD_MARKER: self.btn_marker,
            MapTool.ADD_REGION: self.btn_region,
            MapTool.MEASURE: self.btn_measure,
        }

        # Добавляем кнопки в тулбар.
        for btn in [
            self.btn_select,
            self.btn_marker,
            self.btn_region,
            self.btn_measure,
            self.btn_grid,
            self.btn_fullscreen,
            self.btn_camera,
        ]:
            toolbar_layout.addWidget(btn)

        # Центральная канва карты.
        self.canvas = MapCanvas()
        self.canvas.setObjectName("MapCanvas")
        self._load_attachment_sources()

        # Активируем инструмент выбора по умолчанию.
        self._set_tool(MapTool.SELECT)

        # Правая панель с краткой информацией по маркеру.
        self.info_panel = QFrame()
        self.info_panel.setObjectName("MapInfoPanel")
        self.info_panel.setMinimumWidth(280)
        info_layout = QVBoxLayout(self.info_panel)
        info_layout.setContentsMargins(10, 10, 10, 10)
        info_layout.setSpacing(0)

        self.info_title = QLabel("Данные объекта")
        self.info_title.setObjectName("MapInfoTitle")
        info_layout.addWidget(self.info_title)

        self.info_scroll = QScrollArea()
        self.info_scroll.setObjectName("MapInfoScroll")
        self.info_scroll.setWidgetResizable(True)
        self.info_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.info_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        info_body = QWidget()
        info_body.setObjectName("FormBox")
        info_body_layout = QHBoxLayout(info_body)
        info_body_layout.setContentsMargins(0, 0, 0, 0)
        info_body_layout.setSpacing(12)

        self.info_scroll.setStyleSheet(
            """
            QWidget#FormBox {
                background: #24262c;
            }
            QScrollArea#MapInfoScroll {
                background: #24262c;
            }
            QWidget {
            }
            """
        )

        left_panel = QFrame()
        left_panel.setObjectName("MapInfoCard")
        left_panel.setFixedWidth(220)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(10)

        self.info_preview_title = QLabel("Превью")
        self.info_preview_title.setObjectName("MapInfoSectionTitle")
        self.info_preview = QLabel("Нет изображения")
        self.info_preview.setObjectName("MapInfoPreview")
        self.info_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_preview.setFixedHeight(140)

        self.info_marker_type_title = QLabel("Тип метки")
        self.info_marker_type_title.setObjectName("MapInfoSectionTitle")
        self.info_marker_type_preview = QLabel()
        self.info_marker_type_preview.setObjectName("MapInfoMarkerPreview")
        self.info_marker_type_preview.setFixedSize(28, 28)
        self.info_marker_type_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_marker_type_value = QLabel("—")
        self.info_marker_type_value.setObjectName("MapInfoValue")

        marker_type_row = QHBoxLayout()
        marker_type_row.setSpacing(8)
        marker_type_row.addWidget(self.info_marker_type_preview)
        marker_type_row.addWidget(self.info_marker_type_value)
        marker_type_row.addStretch(1)

        left_layout.addWidget(self.info_preview_title)
        left_layout.addWidget(self.info_preview)
        left_layout.addSpacing(6)
        left_layout.addWidget(self.info_marker_type_title)
        left_layout.addLayout(marker_type_row)
        left_layout.addStretch(1)

        right_panel = QFrame()
        right_panel.setObjectName("MapInfoFormContainer")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        main_section = QFrame()
        main_section.setObjectName("MapInfoSection")
        main_layout = QVBoxLayout(main_section)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)

        main_title = QLabel("Основное")
        main_title.setObjectName("MapInfoSectionTitle")
        main_layout.addWidget(main_title)

        main_form = QFormLayout()
        main_form.setSpacing(8)
        main_form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.info_name = QLabel("—")
        self.info_type = QLabel("—")
        self.info_size = QLabel("—")
        self.info_coords = QLabel("—")
        self.info_parent = QLabel("—")
        for label in [self.info_name, self.info_type, self.info_size, self.info_coords, self.info_parent]:
            label.setObjectName("MapInfoValue")
            label.setWordWrap(True)
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        name_label = QLabel("Название")
        type_label = QLabel("Тип")
        size_label = QLabel("Размер")
        coords_label = QLabel("Координаты")
        parent_label = QLabel("Родительский каталог")
        for label in [name_label, type_label, size_label, coords_label, parent_label]:
            label.setObjectName("MapInfoFormLabel")

        main_form.addRow(name_label, self.info_name)
        main_form.addRow(type_label, self.info_type)
        main_form.addRow(size_label, self.info_size)
        main_form.addRow(coords_label, self.info_coords)
        main_form.addRow(parent_label, self.info_parent)
        main_layout.addLayout(main_form)

        links_section = QFrame()
        links_section.setObjectName("MapInfoSection")
        links_layout = QVBoxLayout(links_section)
        links_layout.setContentsMargins(12, 12, 12, 12)
        links_layout.setSpacing(8)

        links_title = QLabel("Привязки")
        links_title.setObjectName("MapInfoSectionTitle")
        links_layout.addWidget(links_title)

        links_form = QFormLayout()
        links_form.setSpacing(8)
        links_form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        self.info_task = QLabel("—")
        self.info_project = QLabel("—")
        self.info_note = QLabel("—")
        self.info_object = QLabel("—")
        self.info_file = QLabel("—")
        self.info_map = QLabel("—")
        self.info_marker = QLabel("—")
        for label in [
            self.info_task,
            self.info_project,
            self.info_note,
            self.info_object,
            self.info_file,
            self.info_map,
            self.info_marker,
        ]:
            label.setObjectName("MapInfoValue")
            label.setWordWrap(True)
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.info_file.setTextFormat(Qt.TextFormat.RichText)
        self.info_file.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        self.info_file.setOpenExternalLinks(False)
        self.info_file.linkActivated.connect(self._handle_info_link)

        task_label = QLabel("Задачи")
        project_label = QLabel("Проекты")
        note_label = QLabel("Заметки")
        object_label = QLabel("Объекты")
        file_label = QLabel("Файлы")
        map_label = QLabel("Карты")
        marker_label = QLabel("Метки")
        for label in [task_label, project_label, note_label, object_label, file_label, map_label, marker_label]:
            label.setObjectName("MapInfoFormLabel")

        links_form.addRow(task_label, self.info_task)
        links_form.addRow(project_label, self.info_project)
        links_form.addRow(note_label, self.info_note)
        links_form.addRow(object_label, self.info_object)
        links_form.addRow(file_label, self.info_file)
        links_form.addRow(map_label, self.info_map)
        links_form.addRow(marker_label, self.info_marker)
        links_layout.addLayout(links_form)

        text_section = QFrame()
        text_section.setObjectName("MapInfoSection")
        text_layout = QVBoxLayout(text_section)
        text_layout.setContentsMargins(12, 12, 12, 12)
        text_layout.setSpacing(8)

        text_title = QLabel("Пометки! - ВАЖНО")
        text_title.setObjectName("MapInfoSectionTitle")
        text_layout.addWidget(text_title)

        desc_label = QLabel("Текст пометок")
        desc_label.setObjectName("MapInfoFormLabel")
        self.info_description = QLabel("—")
        self.info_description.setObjectName("MapInfoText")
        self.info_description.setWordWrap(True)
        self.info_description.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        text_layout.addWidget(desc_label)
        text_layout.addWidget(self.info_description)

        important_wrap = QFrame()
        important_wrap.setObjectName("MapInfoImportant")
        important_layout = QVBoxLayout(important_wrap)
        important_layout.setContentsMargins(10, 8, 10, 8)
        important_layout.setSpacing(6)

        important_header = QHBoxLayout()
        important_icon = QLabel("⚑")
        important_icon.setObjectName("MapInfoImportantIcon")
        important_label = QLabel("Важные пометки")
        important_label.setObjectName("MapInfoFormLabel")
        important_header.addWidget(important_icon)
        important_header.addWidget(important_label)
        important_header.addStretch(1)

        self.info_important = QLabel("—")
        self.info_important.setObjectName("MapInfoText")
        self.info_important.setWordWrap(True)
        self.info_important.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        important_layout.addLayout(important_header)
        important_layout.addWidget(self.info_important)

        text_layout.addWidget(important_wrap)

        right_layout.addWidget(main_section)
        right_layout.addWidget(links_section)
        right_layout.addWidget(text_section)
        right_layout.addStretch(1)

        info_body_layout.addWidget(left_panel)
        info_body_layout.addWidget(right_panel, 1)

        self.info_scroll.setWidget(info_body)
        info_layout.addWidget(self.info_scroll)

        # Собираем основные панели.
        self.center_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.center_splitter.setObjectName("MapInfoSplitter")
        self.center_splitter.setHandleWidth(6)
        self.center_splitter.setChildrenCollapsible(False)
        self.center_splitter.addWidget(self.canvas)
        self.center_splitter.addWidget(self.info_panel)
        self.center_splitter.setStretchFactor(0, 1)
        self.center_splitter.setStretchFactor(1, 0)
        self.center_splitter.splitterMoved.connect(self._on_info_splitter_moved)

        root.addWidget(self.toolbar)
        root.addWidget(self.center_splitter, 1)

        self.info_panel.hide()

        # Подключаем сигналы от канвы.
        self.canvas.markerSelected.connect(self._on_marker_selected)
        self.canvas.markerDoubleClicked.connect(self._on_marker_double_clicked)
        self.canvas.markerAdded.connect(self._on_marker_added)
        self.canvas.markerUpdated.connect(self._on_marker_updated)
        self.canvas.markerRemoved.connect(self._on_marker_removed)
        self.canvas.overlayAdded.connect(self._on_overlay_added)
        self.canvas.overlayUpdated.connect(self._on_overlay_updated)
        self.canvas.overlayRemoved.connect(self._on_overlay_removed)

        # Стили для редактора.
        self.setStyleSheet("""
            QWidget#MapEditorWorkspace {
                background: #15171b;
            }

            QFrame#MapToolbar {
                background: #1b1d22;
                border-right: 1px solid #2a2b2f;
            }

            QFrame#MapToolbar QToolButton {
                background: transparent;
                border: 1px solid transparent;
                border-radius: 6px;
                padding: 6px;
            }

            QFrame#MapToolbar QToolButton:checked {
                background: #2a2d33;
                border: 1px solid #3a3b40;
            }

            QFrame#MapToolbar QToolButton:hover {
                background: #24262c;
            }

            QFrame#MapInfoPanel {
                background: rgba(20, 22, 30, 0.92);
                border-left: 1px solid #2a2b2f;
            }

            QSplitter#MapInfoSplitter::handle {
                background: #2a2b2f;
            }
            QSplitter#MapInfoSplitter::handle:hover {
                background: #3a3b40;
            }

            QScrollArea#MapInfoScroll {
                background: #24262c;
            }

            QFrame#MapInfoCard, QFrame#MapInfoSection {
                background: rgba(22, 24, 32, 0.92);
                border: 1px solid #2a2b2f;
                border-radius: 10px;
            }

            QLabel#MapInfoTitle {
                color: #f0f0f0;
                font-size: 15px;
                font-weight: 600;
            }

            QLabel#MapInfoSectionTitle {
                color: #d9d9d9;
                font-size: 12px;
                font-weight: 600;
            }

            QLabel#MapInfoFormLabel {
                color: #b9bcc4;
            }

            QLabel#MapInfoValue {
                color: #a8abb3;
                font-size: 12px;
            }

            QLabel#MapInfoText {
                color: #a8abb3;
                font-size: 12px;
            }

            QLabel#MapInfoPreview {
                border: 1px dashed #3a3b40;
                border-radius: 8px;
                color: #8e919a;
                background: #1b1d24;
            }

            QLabel#MapInfoMarkerPreview {
                border: 1px solid #2a2b2f;
                border-radius: 6px;
            }

            QFrame#MapInfoImportant {
                border-left: 3px solid #d59d35;
                background: rgba(29, 31, 39, 0.85);
                border-radius: 8px;
            }

            QLabel#MapInfoImportantIcon {
                color: #d59d35;
            }
        """)

    def _set_tool(self, tool: MapTool) -> None:
        # Активируем инструмент и обновляем состояние кнопок.
        button = self._tool_buttons.get(tool)
        if button is not None:
            button.setChecked(True)
        self.canvas.set_tool(tool)

    def set_fullscreen_state(self, enabled: bool) -> None:
        # Синхронизируем кнопку и скрываем/показываем инфо-панель.
        self.btn_fullscreen.blockSignals(True)
        self.btn_fullscreen.setChecked(enabled)
        self.btn_fullscreen.blockSignals(False)
        if self._fullscreen_active == enabled:
            return
        self._fullscreen_active = enabled
        if enabled:
            self._info_panel_was_visible = self.info_panel.isVisible()
        self._update_info_panel_width()
        if not enabled and self._info_panel_was_visible:
            self.info_panel.show()

    def set_nav_collapsed_state(self, collapsed: bool) -> None:
        # Обновляем ширину инфо-панели при сворачивании навигации.
        if self._nav_collapsed == collapsed:
            return
        self._nav_collapsed = collapsed
        self._update_info_panel_width()

    def _update_info_panel_width(self) -> None:
        # Подстраиваем ширину панели в зависимости от состояния навигации.
        if not self._info_widgets_alive():
            return
        if self._fullscreen_active:
            width = max(int(self.width() * self._info_panel_fullscreen_ratio), 1)
        else:
            width = self._info_panel_expanded_width if self._nav_collapsed else self._info_panel_default_width
        self._set_info_panel_width(width)
        if self._info_marker_id is not None:
            marker = self._markers_by_id.get(self._info_marker_id)
            if marker:
                self._update_info_preview(marker)

    def _set_info_panel_width(self, width: int) -> None:
        if not hasattr(self, "center_splitter") or self.center_splitter is None:
            self.info_panel.setFixedWidth(width)
            return
        total = self.center_splitter.size().width()
        if total <= 0:
            return
        min_panel = self.info_panel.minimumWidth() or 240
        width = max(min(width, total - 200), min_panel)
        self._info_panel_block_save = True
        self.center_splitter.setSizes([max(total - width, 200), width])
        self._info_panel_block_save = False

    def _on_info_splitter_moved(self, _pos: int, _index: int) -> None:
        if self._info_panel_block_save or self._fullscreen_active:
            return
        if not self.info_panel.isVisible():
            return
        sizes = self.center_splitter.sizes()
        if len(sizes) < 2:
            return
        panel_width = sizes[1]
        if panel_width < 280:
            return
        self._info_panel_default_width = panel_width
        self._info_panel_expanded_width = panel_width + self._info_panel_expand_delta
        self._db.set_setting("map_info_panel_width", str(panel_width))

    def _on_fullscreen_toggled(self, checked: bool) -> None:
        # Пробрасываем сигнал о полноэкранном режиме.
        self.fullscreenToggled.emit(checked)

    def _on_marker_selected(self, marker: Optional[Marker]) -> None:
        # Отображаем данные выбранного маркера в правой панели.
        if not self._info_widgets_alive():
            return
        if not marker:
            self._info_marker_id = None
            self.info_panel.hide()
            if hasattr(self, "center_splitter") and self.center_splitter is not None:
                self._info_panel_block_save = True
                self.center_splitter.setSizes([1, 0])
                self._info_panel_block_save = False
            return
        self._update_info_panel_width()
        self.info_panel.show()
        self._apply_marker_info(marker)

    def _on_marker_double_clicked(self, marker: Optional[Marker]) -> None:
        if not marker:
            return
        self.canvas.edit_marker(marker)

    def _apply_marker_info(self, marker: Marker) -> None:
        # Обновляем значения в инфо-панели.
        if not self._info_widgets_alive():
            return
        self._info_marker_id = marker.id
        self.info_name.setText(self._format_value(marker.name))
        self.info_type.setText(self._format_value(marker.type))
        self.info_size.setText(f"{marker.size:.1f} px / ед.")
        self.info_coords.setText(f"{marker.x:.0f}, {marker.y:.0f}")
        self.info_parent.setText(self._format_value(marker.parent_path))
        self.info_task.setText(self._format_links(marker.task_ids, self._tasks_by_id))
        self.info_project.setText(self._format_links(marker.project_ids, self._projects_by_id))
        self.info_note.setText(self._format_links(marker.note_ids, self._notes_by_id))
        self.info_object.setText(self._format_links(marker.object_ids, self._objects_by_id))
        self.info_file.setText(self._format_file_links(marker.file_ids, self._files_by_id))
        self.info_map.setText(self._format_links(marker.map_ids, self._maps_by_id))
        self.info_marker.setText(self._format_links(marker.marker_ids, self._markers_by_id))
        self.info_description.setText(self._format_value(marker.description))
        self.info_important.setText(_format_marker_properties_text(marker.properties))
        self._apply_marker_type_info(marker)
        self._update_info_preview(marker)

    def _apply_marker_type_info(self, marker: Marker) -> None:
        # Обновляем данные по типу маркера в инфо-панели.
        option = marker_type_for_color(marker.color)
        self.info_marker_type_value.setText(option.label)
        pixmap = marker_type_pixmap(option, self.info_marker_type_preview.size())
        if pixmap is not None:
            self.info_marker_type_preview.setPixmap(pixmap)
            self.info_marker_type_preview.setText("")
        else:
            self.info_marker_type_preview.setPixmap(QPixmap())
            self.info_marker_type_preview.setText(option.label)
        self.info_marker_type_preview.setToolTip(option.label)

    def _info_widgets_alive(self) -> bool:
        # Проверяем, что виджеты инфо-панели ещё существуют.
        return bool(
            isValid(self.info_panel)
            and isValid(self.info_name)
            and isValid(self.info_preview)
            and isValid(self.info_marker_type_preview)
        )

    def _update_info_preview(self, marker: Any) -> None:
        # Обновляем превью изображения маркера.
        if not self._info_widgets_alive():
            return
        preview_size = QSize(
            max(self.info_preview.width(), 1),
            max(self.info_preview.height(), 1),
        )
        pixmap = self._load_marker_preview(marker, preview_size)
        if pixmap is not None:
            self.info_preview.setPixmap(pixmap)
            self.info_preview.setText("")
        else:
            self.info_preview.setPixmap(QPixmap())
            if marker.image_path:
                self.info_preview.setText("Изображение недоступно")
            else:
                self.info_preview.setText("Нет изображения")
        self.info_preview.setToolTip(marker.image_path or "")

    @staticmethod
    def _load_marker_preview(marker: Marker, target: QSize) -> QPixmap | None:
        # Загружаем превью изображения маркера для инфо-панели.
        image_path = (marker.image_path or "").strip()
        if not image_path:
            return None
        path = Path(image_path)
        file_path = path if path.is_file() else None
        if file_path is None:
            cloud_root = get_database().get_setting("cloud_storage_path", default="").strip()
            if cloud_root:
                candidate = Path(cloud_root) / image_path
                if candidate.is_file():
                    file_path = candidate
        if not file_path:
            return None
        pixmap = QPixmap(str(file_path))
        if pixmap.isNull():
            return None
        return pixmap.scaled(target, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)

    def resizeEvent(self, event) -> None:
        # Подстраиваем ширину панели в полноэкранном режиме.
        super().resizeEvent(event)
        if self._fullscreen_active:
            self._update_info_panel_width()

    def _load_attachment_sources(self) -> None:
        # Загружаем источники данных из базы и передаем их канве.
        tasks = self._db.fetch_tasks()
        projects = self._db.fetch_projects()
        notes = self._db.fetch_notes()
        objects = self._db.fetch_objects()
        files = self._db.fetch_cloud_files()
        maps = self._db.fetch_maps()
        markers = self._db.fetch_map_markers()
        self._tasks_by_id = {task.id: task for task in tasks}
        self._projects_by_id = {project.id: project for project in projects}
        self._notes_by_id = {note.id: note for note in notes}
        self._objects_by_id = {item.id: item for item in objects}
        self._files_by_id = {item.id: item for item in files}
        self._maps_by_id = {item.id: item for item in maps}
        self._markers_by_id = {item.id: item for item in markers}
        self.canvas.set_attachment_sources(tasks, projects, notes, objects, files, maps, markers)

    def load_map(self, map_id: int, tiles_path: str, tiles_h: int, tiles_w: int) -> None:
        # Загружаем карту и синхронизируем маркеры из базы.
        self._current_map_id = map_id
        self.canvas.set_tiles(tiles_path, tiles_h, tiles_w)
        overlays = self._db.fetch_map_overlays(map_id)
        loaded_overlays = [
            MapOverlay(
                id=item.id,
                kind=item.kind,
                points=[QPointF(x, y) for x, y in item.points],
                color=QColor(item.color),
                title=item.title,
            )
            for item in overlays
        ]
        self.canvas.set_overlays(loaded_overlays)
        markers = self._db.fetch_map_markers(map_id)
        if not markers:
            # Если маркеров нет, создаем дефолтные.
            defaults = self.canvas.default_markers()
            self.canvas.set_markers(defaults)
            for marker in defaults:
                self._sync_marker(marker)
            self.markersChanged.emit()
            return
        loaded = []
        # Преобразуем записи базы в объекты Marker.
        for marker in markers:
            loaded.append(
                Marker(
                    marker.id,
                    marker.name,
                    marker.x,
                    marker.y,
                    QColor(marker.color),
                    marker.type,
                    marker.size,
                    marker.description,
                    marker.properties,
                    marker.task_ids,
                    marker.project_ids,
                    marker.note_ids,
                    marker.object_ids,
                    marker.file_ids,
                    marker.map_ids,
                    marker.marker_ids,
                    marker.parent_path,
                    marker.image_path,
                )
            )
        self.canvas.set_markers(loaded)
        self.markersChanged.emit()

    def markers(self) -> List[Marker]:
        # Возвращаем текущие маркеры канвы.
        return self.canvas.markers()

    def focus_marker(self, marker: Marker, zoom_boost: float = 4.0) -> None:
        # Делегируем фокусировку на канву.
        self.canvas.focus_on_marker(marker, zoom_boost=zoom_boost)

    def _sync_marker(self, marker: Marker) -> None:
        # Сохраняем маркер в базе, если карта выбрана.
        if self._current_map_id is None:
            return
        self._db.upsert_map_marker(
            marker_id=marker.id,
            map_id=self._current_map_id,
            name=marker.name,
            x=marker.x,
            y=marker.y,
            color=marker.color.name(),
            marker_type=marker.type,
            size=marker.size,
            description=marker.description,
            properties=marker.properties,
            task_ids=marker.task_ids,
            project_ids=marker.project_ids,
            note_ids=marker.note_ids,
            object_ids=marker.object_ids,
            file_ids=marker.file_ids,
            map_ids=marker.map_ids,
            marker_ids=marker.marker_ids,
            parent_path=marker.parent_path,
            image_path=marker.image_path,
        )

    def _sync_overlay(self, overlay: MapOverlay):
        # Сохраняем геометрию карты в базе, если карта выбрана.
        if self._current_map_id is None:
            return None
        points = [(point.x(), point.y()) for point in overlay.points]
        return self._db.create_map_overlay(
            map_id=self._current_map_id,
            kind=overlay.kind,
            points=points,
            color=overlay.color.name(),
            title=overlay.title,
        )

    def _on_marker_added(self, marker: Marker) -> None:
        # Реакция на добавление маркера.
        self._sync_marker(marker)
        self.markersChanged.emit()
        if self.canvas.tool() == MapTool.ADD_MARKER:
            self._set_tool(MapTool.SELECT)

    def _on_marker_updated(self, marker: Marker) -> None:
        # Реакция на обновление маркера.
        self._sync_marker(marker)
        if self._info_marker_id == marker.id:
            self._apply_marker_info(marker)
        self.markersChanged.emit()

    def _on_marker_removed(self, marker_id: int) -> None:
        # Удаляем маркер из базы по идентификатору.
        if self._current_map_id is None:
            return
        self._db.delete_map_marker(marker_id)
        self.markersChanged.emit()

    def _on_overlay_added(self, overlay: MapOverlay) -> None:
        # Реакция на добавление области/пути: сохраняем в БД и фиксируем id.
        saved = self._sync_overlay(overlay)
        if saved is None:
            return
        self.canvas.apply_saved_overlay_id(overlay, saved.id)

    def _on_overlay_updated(self, overlay: MapOverlay) -> None:
        # Реакция на изменение области/пути: обновляем запись в БД.
        if self._current_map_id is None:
            return
        points = [(point.x(), point.y()) for point in overlay.points]
        try:
            self._db.update_map_overlay(
                overlay_id=overlay.id,
                kind=overlay.kind,
                points=points,
                color=overlay.color.name(),
                title=overlay.title,
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Проверка", str(exc))

    def _on_overlay_removed(self, overlay_id: int) -> None:
        # Реакция на удаление области/пути: удаляем запись из БД.
        if self._current_map_id is None:
            return
        self._db.delete_map_overlay(overlay_id)

    @staticmethod
    def _format_value(value: str) -> str:
        # Приводим значение к отображаемому виду.
        text = (value or "").strip()
        return text if text else "—"

    @staticmethod
    def _format_links(item_ids: List[int], source: dict) -> str:
        # Формируем строку с названиями привязанных сущностей.
        if not item_ids:
            return "—"
        titles = []
        for item_id in item_ids:
            item = source.get(item_id)
            if not item:
                titles.append("не найдено")
                continue
            item_title = getattr(item, "title", None) or getattr(item, "name", None) or getattr(item, "rel_path", "—")
            titles.append(item_title)
        return ", ".join(titles)

    @staticmethod
    def _format_file_links(item_ids: List[int], source: dict) -> str:
        # Формируем кликабельные ссылки для изображений.
        if not item_ids:
            return "—"
        parts = []
        for item_id in item_ids:
            item = source.get(item_id)
            if not item:
                parts.append("не найдено")
                continue
            item_title = getattr(item, "title", None) or getattr(item, "name", None) or getattr(item, "rel_path", "—")
            safe_title = html.escape(item_title)
            if getattr(item, "is_image", False):
                parts.append(f'<a href="file:{item_id}">{safe_title}</a>')
            else:
                parts.append(safe_title)
        return "<br>".join(parts)

    def _handle_info_link(self, link: str) -> None:
        # Обрабатываем клики по ссылкам файлов в панели данных.
        if ":" not in link:
            return
        kind, item_id = link.split(":", 1)
        if kind != "file":
            return
        try:
            parsed_id = int(item_id)
        except ValueError:
            return
        self._open_attachment_view(kind, parsed_id)

    def _open_attachment_view(self, kind: str, item_id: int) -> None:
        # Делегируем открытие вложения канве карты.
        self.canvas.open_attachment_view(kind, item_id)

    def open_attachment_view(self, kind: str, item_id: int) -> None:
        self._open_attachment_view(kind, item_id)

__all__ = ["MapEditorWorkspace"]
