"""MapEditorWorkspace class module for maps workspace."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403
from .map_canvas import MapCanvas
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QGridLayout
from mindnavigator.ui.styles import get_theme_palette


class MapEditorWorkspace(QWidget):
    fullscreenToggled = Signal(bool)
    markersChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("MapEditorWorkspace")
        self._theme_mode = "dark"
        self._db = get_database()
        self._tasks: List[Any] = []
        self._projects: List[Any] = []
        self._notes: List[Any] = []
        self._objects: List[Any] = []
        self._files: List[Any] = []
        self._maps: List[Any] = []
        self._tasks_by_id: dict[int, Any] = {}
        self._projects_by_id: dict[int, Any] = {}
        self._notes_by_id: dict[int, Any] = {}
        self._objects_by_id: dict[int, Any] = {}
        self._files_by_id: dict[int, Any] = {}
        self._maps_by_id: dict[int, Any] = {}
        self._markers_by_id: dict[int, Any] = {}
        self._fullscreen_active = False
        self._nav_collapsed = False
        self._current_map_id: Optional[int] = None
        self._current_map_title = ""
        self._current_map_project = ""
        self._current_selection_kind = "map"
        self._current_marker_id: Optional[int] = None
        self._current_overlay_id: Optional[int] = None
        self._visible_filter = "all"
        self._info_panel_default_width = 320
        self._info_panel_expand_delta = 60
        self._info_panel_expanded_width = 380
        self._info_panel_fullscreen_ratio = 0.30
        self._info_panel_block_save = False
        try:
            saved_width = int(self._db.get_setting("map_info_panel_width", default="").strip() or 0)
        except ValueError:
            saved_width = 0
        if saved_width >= 260:
            self._info_panel_default_width = saved_width
            self._info_panel_expanded_width = saved_width + self._info_panel_expand_delta

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        content_row = QHBoxLayout()
        content_row.setContentsMargins(0, 0, 0, 0)
        content_row.setSpacing(0)

        self.canvas = MapCanvas()
        self.canvas.setObjectName("MapCanvas")
        self.toolbar = self._build_toolbar()
        self.canvas_frame = QFrame()
        self.canvas_frame.setObjectName("MapCanvasFrame")
        canvas_layout = QVBoxLayout(self.canvas_frame)
        canvas_layout.setContentsMargins(0, 0, 0, 0)
        canvas_layout.setSpacing(0)
        canvas_layout.addWidget(self.canvas)

        self.legend_card = self._build_legend_card(self.canvas)
        self.legend_card.raise_()

        self.info_panel = self._build_info_panel()
        self.center_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.center_splitter.setObjectName("MapInfoSplitter")
        self.center_splitter.setHandleWidth(6)
        self.center_splitter.setChildrenCollapsible(False)
        self.center_splitter.addWidget(self.canvas_frame)
        self.center_splitter.addWidget(self.info_panel)
        self.center_splitter.setStretchFactor(0, 1)
        self.center_splitter.setStretchFactor(1, 0)
        self.center_splitter.splitterMoved.connect(self._on_info_splitter_moved)

        content_row.addWidget(self.toolbar)
        content_row.addWidget(self.center_splitter, 1)

        content_wrap = QWidget()
        content_wrap.setLayout(content_row)
        root.addWidget(content_wrap, 1)

        self.status_bar = self._build_status_bar()
        root.addWidget(self.status_bar)

        self._load_attachment_sources()
        self._set_tool(MapTool.SELECT)
        self._show_map_summary()
        self._setup_shortcuts()
        self._connect_canvas()
        self.set_theme_mode("dark")

    def _build_toolbar(self) -> QFrame:
        toolbar = QFrame()
        toolbar.setObjectName("MapToolbar")
        toolbar.setFixedWidth(68)
        layout = QVBoxLayout(toolbar)
        layout.setContentsMargins(10, 12, 10, 12)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.tool_group = QButtonGroup(self)
        self.tool_group.setExclusive(True)

        def tool_button(icon_name: str, tooltip: str, tool: Optional[MapTool]) -> QToolButton:
            button = QToolButton()
            button.setIcon(qta.icon(icon_name, color="#d7dce8"))
            button.setIconSize(QSize(20, 20))
            button.setCheckable(True)
            button.setToolTip(tooltip)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setAutoRaise(False)
            if tool is not None:
                self.tool_group.addButton(button)
                button.clicked.connect(lambda checked=False, t=tool: self._set_tool(t))
            return button

        self.btn_select = tool_button("fa5s.mouse-pointer", "Выбор — выбрать и редактировать объекты на карте", MapTool.SELECT)
        self.btn_marker = tool_button("fa5s.map-marker-alt", "Метка — добавить маркер", MapTool.ADD_MARKER)
        self.btn_region = tool_button("fa5s.draw-polygon", "Регион — добавить регион", MapTool.ADD_REGION)
        self.btn_measure = tool_button("fa5s.ruler", "Маршрут — рисовать путь", MapTool.MEASURE)
        self.btn_grid = tool_button("fa5s.border-all", "Сетка — показать или скрыть сетку", None)
        self.btn_grid.setCheckable(True)
        self.btn_grid.setChecked(True)
        self.btn_grid.clicked.connect(self.canvas.set_grid_enabled)
        self.btn_fullscreen = tool_button("fa5s.expand", "На весь экран — полноэкранный режим", None)
        self.btn_fullscreen.setCheckable(True)
        self.btn_fullscreen.clicked.connect(self._on_fullscreen_toggled)
        self.btn_camera = tool_button("fa5s.camera", "Снимок — сделать снимок карты", None)
        self.btn_camera.setCheckable(False)
        self.btn_camera.clicked.connect(self._save_snapshot)

        self._tool_buttons = {
            MapTool.SELECT: self.btn_select,
            MapTool.ADD_MARKER: self.btn_marker,
            MapTool.ADD_REGION: self.btn_region,
            MapTool.MEASURE: self.btn_measure,
        }

        for button in (self.btn_select, self.btn_marker, self.btn_region, self.btn_measure):
            layout.addWidget(button)
        divider = QFrame()
        divider.setObjectName("MapToolbarDivider")
        divider.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(divider)
        for button in (self.btn_grid, self.btn_fullscreen, self.btn_camera):
            layout.addWidget(button)
        layout.addStretch(1)
        return toolbar

    def _build_info_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("MapInfoPanel")
        panel.setMinimumWidth(260)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        self.info_title = QLabel("Карта")
        self.info_title.setObjectName("MapInfoTitle")
        self.info_subtitle = QLabel("Выберите объект на карте, чтобы увидеть свойства.")
        self.info_subtitle.setObjectName("MapInfoSubtitle")
        self.info_subtitle.setWordWrap(True)
        layout.addWidget(self.info_title)
        layout.addWidget(self.info_subtitle)

        actions_row = QHBoxLayout()
        actions_row.setSpacing(8)
        self.info_open_btn = QPushButton("Открыть")
        self.info_edit_btn = QPushButton("Редактировать")
        self.info_delete_btn = QPushButton("Удалить")
        self.info_add_link_btn = QToolButton()
        self.info_add_link_btn.setText("+")
        self.info_add_link_btn.setToolTip("Добавление связей доступно через редактирование маркера.")
        self.info_add_link_btn.setEnabled(False)
        for button in (self.info_open_btn, self.info_edit_btn, self.info_delete_btn):
            button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.info_open_btn.clicked.connect(self._on_open_current)
        self.info_edit_btn.clicked.connect(self._on_edit_current)
        self.info_delete_btn.clicked.connect(self._on_delete_current)
        actions_row.addWidget(self.info_open_btn)
        actions_row.addWidget(self.info_edit_btn)
        actions_row.addWidget(self.info_delete_btn)
        actions_row.addStretch(1)
        actions_row.addWidget(self.info_add_link_btn)
        layout.addLayout(actions_row)

        self.info_scroll = QScrollArea()
        self.info_scroll.setObjectName("MapInfoScroll")
        self.info_scroll.setWidgetResizable(True)
        self.info_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.info_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        body = QWidget()
        body.setObjectName("MapInfoScrollBody")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(10)

        self.info_preview_card = QFrame()
        self.info_preview_card.setObjectName("MapInfoCard")
        preview_layout = QVBoxLayout(self.info_preview_card)
        preview_layout.setContentsMargins(12, 12, 12, 12)
        preview_layout.setSpacing(8)
        self.info_preview = QLabel("Нет изображения")
        self.info_preview.setObjectName("MapInfoPreview")
        self.info_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_preview.setFixedHeight(154)
        self.info_type_chip = QLabel("Объект")
        self.info_type_chip.setObjectName("MapInfoTypeChip")
        preview_layout.addWidget(self.info_preview)
        preview_layout.addWidget(self.info_type_chip, alignment=Qt.AlignmentFlag.AlignLeft)

        self.info_summary_card = QFrame()
        self.info_summary_card.setObjectName("MapInfoCard")
        summary_layout = QVBoxLayout(self.info_summary_card)
        summary_layout.setContentsMargins(12, 12, 12, 12)
        summary_layout.setSpacing(8)
        summary_title = QLabel("Контекст")
        summary_title.setObjectName("MapInfoSectionTitle")
        summary_layout.addWidget(summary_title)
        summary_grid = QGridLayout()
        summary_grid.setContentsMargins(0, 0, 0, 0)
        summary_grid.setHorizontalSpacing(8)
        summary_grid.setVerticalSpacing(8)
        self.summary_value_labels: dict[str, QLabel] = {}
        for index, (key, title) in enumerate(
            [
                ("primary", "Маркеры"),
                ("secondary", "Регионы"),
                ("tertiary", "Маршруты"),
                ("quaternary", "Связи"),
            ]
        ):
            card = QFrame()
            card.setObjectName("MapStatCard")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(10, 8, 10, 8)
            card_layout.setSpacing(2)
            title_label = QLabel(title)
            title_label.setObjectName("MapStatTitle")
            value_label = QLabel("—")
            value_label.setObjectName("MapStatValue")
            card_layout.addWidget(title_label)
            card_layout.addWidget(value_label)
            summary_grid.addWidget(card, index // 2, index % 2)
            self.summary_value_labels[key] = value_label
        summary_layout.addLayout(summary_grid)

        self.info_details_card = QFrame()
        self.info_details_card.setObjectName("MapInfoCard")
        details_layout = QVBoxLayout(self.info_details_card)
        details_layout.setContentsMargins(12, 12, 12, 12)
        details_layout.setSpacing(8)
        details_title = QLabel("Свойства")
        details_title.setObjectName("MapInfoSectionTitle")
        details_layout.addWidget(details_title)
        details_form = QFormLayout()
        details_form.setSpacing(8)
        details_form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.detail_labels: dict[str, QLabel] = {}
        for key, title in (
            ("id", "ID"),
            ("type", "Тип"),
            ("coords", "Координаты"),
            ("size", "Размер"),
            ("parent", "Контекст"),
            ("extra", "Дополнительно"),
        ):
            value = QLabel("—")
            value.setObjectName("MapInfoValue")
            value.setWordWrap(True)
            value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            label = QLabel(title)
            label.setObjectName("MapInfoFormLabel")
            details_form.addRow(label, value)
            self.detail_labels[key] = value
        details_layout.addLayout(details_form)

        self.info_links_card = QFrame()
        self.info_links_card.setObjectName("MapInfoCard")
        links_layout = QVBoxLayout(self.info_links_card)
        links_layout.setContentsMargins(12, 12, 12, 12)
        links_layout.setSpacing(8)
        links_title = QLabel("Связи")
        links_title.setObjectName("MapInfoSectionTitle")
        self.info_links_value = QLabel("Нет связанных элементов")
        self.info_links_value.setObjectName("MapInfoLinks")
        self.info_links_value.setWordWrap(True)
        self.info_links_value.setTextFormat(Qt.TextFormat.RichText)
        self.info_links_value.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        self.info_links_value.setOpenExternalLinks(False)
        self.info_links_value.linkActivated.connect(self._handle_info_link)
        links_layout.addWidget(links_title)
        links_layout.addWidget(self.info_links_value)

        self.info_notes_card = QFrame()
        self.info_notes_card.setObjectName("MapInfoCard")
        notes_layout = QVBoxLayout(self.info_notes_card)
        notes_layout.setContentsMargins(12, 12, 12, 12)
        notes_layout.setSpacing(8)
        notes_title = QLabel("Описание")
        notes_title.setObjectName("MapInfoSectionTitle")
        self.info_description = QLabel("Нет описания")
        self.info_description.setObjectName("MapInfoText")
        self.info_description.setWordWrap(True)
        self.info_description.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        important_title = QLabel("Дополнительные свойства")
        important_title.setObjectName("MapInfoSectionTitle")
        self.info_important = QLabel("—")
        self.info_important.setObjectName("MapInfoText")
        self.info_important.setWordWrap(True)
        self.info_important.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        notes_layout.addWidget(notes_title)
        notes_layout.addWidget(self.info_description)
        notes_layout.addWidget(important_title)
        notes_layout.addWidget(self.info_important)

        for widget in (
            self.info_preview_card,
            self.info_summary_card,
            self.info_details_card,
            self.info_links_card,
            self.info_notes_card,
        ):
            body_layout.addWidget(widget)
        body_layout.addStretch(1)

        self.info_scroll.setWidget(body)
        layout.addWidget(self.info_scroll, 1)
        return panel

    def _build_status_bar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("MapStatusBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(12)
        self.status_cursor = QLabel("X: —  Y: —")
        self.status_zoom = QLabel("Zoom: 100%")
        self.status_grid = QLabel("Сетка: —")
        self.status_markers = QLabel("Маркеров: 0")
        self.status_regions = QLabel("Регионов: 0")
        self.status_routes = QLabel("Маршрутов: 0")
        self.status_hint = QLabel("Esc — отменить текущий инструмент")
        self.status_hint.setObjectName("MapStatusHint")
        for label in (
            self.status_cursor,
            self.status_zoom,
            self.status_grid,
            self.status_markers,
            self.status_regions,
            self.status_routes,
            self.status_hint,
        ):
            label.setObjectName("MapStatusLabel")
            layout.addWidget(label)
        layout.addStretch(1)
        return bar

    def _build_legend_card(self, parent: QWidget) -> QFrame:
        card = QFrame(parent)
        card.setObjectName("MapLegendCard")
        card.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)
        title = QLabel("Легенда")
        title.setObjectName("MapLegendTitle")
        layout.addWidget(title)
        for text in (
            "Выбранный объект",
            "Метки",
            "Регионы",
            "Маршруты",
        ):
            row = QLabel(text)
            row.setObjectName("MapLegendItem")
            layout.addWidget(row)
        card.adjustSize()
        return card

    def _connect_canvas(self) -> None:
        self.canvas.markerSelected.connect(self._on_marker_selected)
        self.canvas.markerDoubleClicked.connect(self._on_marker_double_clicked)
        self.canvas.markerAdded.connect(self._on_marker_added)
        self.canvas.markerUpdated.connect(self._on_marker_updated)
        self.canvas.markerRemoved.connect(self._on_marker_removed)
        self.canvas.overlayAdded.connect(self._on_overlay_added)
        self.canvas.overlayUpdated.connect(self._on_overlay_updated)
        self.canvas.overlayRemoved.connect(self._on_overlay_removed)
        self.canvas.overlaySelected.connect(self._on_overlay_selected)
        self.canvas.cursorWorldPositionChanged.connect(self._on_cursor_world_position_changed)
        self.canvas.zoomChanged.connect(self._on_zoom_changed)
        self.canvas.gridChanged.connect(self._on_grid_changed)

    def _setup_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+0"), self, activated=self.reset_view)

    def set_theme_mode(self, theme_mode: str) -> None:
        self._theme_mode = "light" if str(theme_mode).strip().lower() == "light" else "dark"
        palette = get_theme_palette(self._theme_mode)
        panel_bg = palette.panel_bg
        elevated_bg = palette.elevated_bg
        border = palette.border
        border_strong = palette.border_strong
        text = palette.text
        dim = palette.dim_text
        accent = palette.accent
        selection_bg = palette.selection_bg
        selection_text = palette.selection_text
        self.setStyleSheet(
            f"""
            QWidget#MapEditorWorkspace {{
                background: {palette.window_bg};
            }}

            QFrame#MapToolbar {{
                background: {panel_bg};
                border-right: 1px solid {border};
            }}

            QFrame#MapToolbar QToolButton {{
                background: transparent;
                border: 1px solid transparent;
                border-radius: 10px;
                padding: 9px;
            }}

            QFrame#MapToolbar QToolButton:hover {{
                background: {elevated_bg};
                border-color: {border};
            }}

            QFrame#MapToolbar QToolButton:checked {{
                background: {selection_bg};
                color: {selection_text};
                border-color: {border_strong};
            }}

            QFrame#MapToolbarDivider {{
                background: {border};
                max-height: 1px;
                min-height: 1px;
                border: none;
            }}

            QFrame#MapCanvasFrame {{
                background: {palette.window_bg};
            }}

            QFrame#MapInfoPanel {{
                background: rgba(20, 22, 30, 0.96);
                border-left: 1px solid {border};
            }}

            QSplitter#MapInfoSplitter::handle {{
                background: {border};
            }}

            QSplitter#MapInfoSplitter::handle:hover {{
                background: {border_strong};
            }}

            QScrollArea#MapInfoScroll {{
                background: transparent;
                border: none;
            }}

            QWidget#MapInfoScrollBody,
            QScrollArea#MapInfoScroll QWidget#qt_scrollarea_viewport,
            QScrollArea#MapInfoScroll > QWidget,
            QScrollArea#MapInfoScroll > QWidget > QWidget {{
                background: transparent;
            }}

            QFrame#MapInfoCard, QFrame#MapLegendCard {{
                background: rgba(22, 24, 32, 0.92);
                border: 1px solid {border};
                border-radius: 12px;
            }}

            QLabel#MapInfoTitle {{
                color: {text};
                font-size: 17px;
                font-weight: 700;
            }}

            QLabel#MapInfoSubtitle {{
                color: {dim};
                font-size: 12px;
            }}

            QLabel#MapInfoSectionTitle {{
                color: {text};
                font-size: 12px;
                font-weight: 600;
            }}

            QLabel#MapInfoFormLabel {{
                color: {dim};
            }}

            QLabel#MapInfoValue, QLabel#MapInfoText, QLabel#MapInfoLinks {{
                color: {text};
                font-size: 12px;
            }}

            QLabel#MapInfoLinks a {{
                color: {text};
                text-decoration: none;
            }}

            QLabel#MapInfoPreview {{
                border: 1px dashed {border_strong};
                border-radius: 10px;
                color: {dim};
                background: {elevated_bg};
            }}

            QLabel#MapInfoTypeChip {{
                color: {selection_text};
                background: {selection_bg};
                border: 1px solid {border_strong};
                border-radius: 8px;
                padding: 4px 8px;
            }}

            QFrame#MapStatCard {{
                background: {elevated_bg};
                border: 1px solid {border};
                border-radius: 10px;
            }}

            QLabel#MapStatTitle {{
                color: {dim};
                font-size: 11px;
            }}

            QLabel#MapStatValue {{
                color: {text};
                font-size: 15px;
                font-weight: 700;
            }}

            QFrame#MapStatusBar {{
                background: {panel_bg};
                border-top: 1px solid {border};
            }}

            QLabel#MapStatusLabel {{
                color: {text};
                font-size: 11px;
            }}

            QLabel#MapStatusHint {{
                color: {dim};
            }}

            QPushButton, QToolButton {{
                background: {elevated_bg};
                color: {text};
                border: 1px solid {border_strong};
                border-radius: 8px;
                padding: 6px 10px;
            }}

            QPushButton:hover, QToolButton:hover {{
                background: {selection_bg};
                color: {selection_text};
            }}

            QPushButton:disabled, QToolButton:disabled {{
                background: {panel_bg};
                color: {dim};
                border-color: {border};
            }}

            QLabel#MapLegendTitle {{
                color: {text};
                font-weight: 600;
            }}

            QLabel#MapLegendItem {{
                color: {dim};
                font-size: 11px;
            }}
            """
        )

    def set_map_context(self, title: str, project: str = "") -> None:
        self._current_map_title = (title or "").strip()
        self._current_map_project = (project or "").strip()
        if self._current_selection_kind == "map":
            self._show_map_summary()

    def search_objects(self, query: str, filter_key: str = "all") -> List[dict[str, Any]]:
        needle = (query or "").strip().lower()
        filter_value = (filter_key or "all").strip().lower()
        results: list[dict[str, Any]] = []
        if not needle:
            return results
        if filter_value in {"all", "marker"}:
            for marker in self.canvas.markers():
                search_text = " ".join(
                    [
                        marker.name,
                        marker.type,
                        marker.description,
                        marker.properties,
                        self._linked_titles_text(marker),
                    ]
                ).lower()
                if needle not in search_text:
                    continue
                results.append(
                    {
                        "kind": "marker",
                        "payload": marker,
                        "display": (
                            f"{marker.name or 'Без названия'} · {marker.type or 'Объект'} · "
                            f"X: {marker.x:.0f}  Y: {marker.y:.0f}  Связи: {self._marker_link_count(marker)}"
                        ),
                    }
                )
        if filter_value in {"all", "region", "path"}:
            for overlay in self.canvas.overlays():
                if filter_value != "all" and overlay.kind != filter_value:
                    continue
                title = overlay.title or ("Регион" if overlay.kind == "region" else "Маршрут")
                kind_label = "Регион" if overlay.kind == "region" else "Маршрут"
                points_count = len(overlay.points)
                search_text = f"{title} {kind_label}".lower()
                if needle not in search_text:
                    continue
                coords = self._overlay_bounds_text(overlay)
                results.append(
                    {
                        "kind": "overlay",
                        "payload": overlay,
                        "display": f"{title} · {kind_label} · {coords}  Точек: {points_count}",
                    }
                )
        return results

    def focus_search_result(self, result: dict[str, Any]) -> None:
        kind = result.get("kind")
        payload = result.get("payload")
        if kind == "marker" and isinstance(payload, Marker):
            self.focus_marker(payload, zoom_boost=3.0)
        elif kind == "overlay" and isinstance(payload, MapOverlay):
            self.focus_overlay(payload, zoom_boost=1.5)

    def set_visible_object_filter(self, filter_key: str) -> None:
        self._visible_filter = (filter_key or "all").strip().lower() or "all"
        self.canvas.set_visible_object_filter(self._visible_filter)
        if self._current_selection_kind == "marker":
            marker = self._current_marker()
            if marker is None:
                self._show_map_summary()
        elif self._current_selection_kind == "overlay":
            overlay = self._current_overlay()
            if overlay is None:
                self._show_map_summary()

    def visible_object_filter(self) -> str:
        return self._visible_filter

    def reset_view(self) -> None:
        self.canvas.reset_view()
        self.canvas.update()

    def show_all_objects(self) -> None:
        self.set_visible_object_filter("all")
        self.reset_view()

    def markers(self) -> List[Marker]:
        return self.canvas.markers()

    def overlays(self) -> List[MapOverlay]:
        return self.canvas.overlays()

    def focus_marker(self, marker: Marker, zoom_boost: float = 4.0) -> None:
        self.canvas.focus_on_marker(marker, zoom_boost=zoom_boost)

    def focus_marker_by_id(self, marker_id: int, zoom_boost: float = 4.0) -> bool:
        marker = self._markers_by_id.get(marker_id)
        if not isinstance(marker, Marker):
            return False
        self.focus_marker(marker, zoom_boost=zoom_boost)
        return True

    def focus_overlay(self, overlay: MapOverlay, zoom_boost: float = 2.0) -> None:
        self.canvas.focus_on_overlay(overlay, zoom_boost=zoom_boost)

    def set_fullscreen_state(self, enabled: bool) -> None:
        self.btn_fullscreen.blockSignals(True)
        self.btn_fullscreen.setChecked(enabled)
        self.btn_fullscreen.blockSignals(False)
        if self._fullscreen_active == enabled:
            return
        self._fullscreen_active = enabled
        self._update_info_panel_width()
        self._reposition_canvas_overlays()

    def set_nav_collapsed_state(self, collapsed: bool) -> None:
        if self._nav_collapsed == collapsed:
            return
        self._nav_collapsed = collapsed
        self._update_info_panel_width()

    def _set_tool(self, tool: MapTool) -> None:
        button = self._tool_buttons.get(tool)
        if button is not None:
            button.setChecked(True)
        self.canvas.set_tool(tool)

    def _on_fullscreen_toggled(self, checked: bool) -> None:
        self.fullscreenToggled.emit(checked)

    def _on_marker_selected(self, marker: Optional[Marker]) -> None:
        if marker is None:
            if self._current_selection_kind != "overlay":
                self._show_map_summary()
            return
        self._current_selection_kind = "marker"
        self._current_marker_id = marker.id
        self._current_overlay_id = None
        self._update_info_panel_width()
        self._apply_marker_info(marker)

    def _on_overlay_selected(self, overlay: Optional[MapOverlay]) -> None:
        if overlay is None:
            if self._current_selection_kind != "marker":
                self._show_map_summary()
            return
        self._current_selection_kind = "overlay"
        self._current_overlay_id = overlay.id
        self._current_marker_id = None
        self._update_info_panel_width()
        self._apply_overlay_info(overlay)

    def _on_marker_double_clicked(self, marker: Optional[Marker]) -> None:
        if marker is not None:
            self.canvas.edit_marker(marker)

    def _on_marker_added(self, marker: Marker) -> None:
        self._sync_marker(marker)
        self._markers_by_id[marker.id] = marker
        self.markersChanged.emit()
        self._refresh_status_bar()
        self._apply_marker_info(marker)
        if self.canvas.tool() == MapTool.ADD_MARKER:
            self._set_tool(MapTool.SELECT)

    def _on_marker_updated(self, marker: Marker) -> None:
        self._sync_marker(marker)
        self._markers_by_id[marker.id] = marker
        self.markersChanged.emit()
        self._refresh_status_bar()
        if self._current_marker_id == marker.id:
            self._apply_marker_info(marker)

    def _on_marker_removed(self, marker_id: int) -> None:
        if self._current_map_id is not None:
            self._db.delete_map_marker(marker_id)
        self._markers_by_id.pop(marker_id, None)
        self.markersChanged.emit()
        self._refresh_status_bar()
        if self._current_marker_id == marker_id:
            self._show_map_summary()

    def _on_overlay_added(self, overlay: MapOverlay) -> None:
        saved = self._sync_overlay(overlay)
        if saved is not None:
            self.canvas.apply_saved_overlay_id(overlay, saved.id)
            overlay = self._current_overlay() or overlay
        self._refresh_status_bar()
        self._apply_overlay_info(overlay)

    def _on_overlay_updated(self, overlay: MapOverlay) -> None:
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
            return
        self._refresh_status_bar()
        if self._current_overlay_id == overlay.id:
            self._apply_overlay_info(overlay)

    def _on_overlay_removed(self, overlay_id: int) -> None:
        if self._current_map_id is not None:
            self._db.delete_map_overlay(overlay_id)
        self._refresh_status_bar()
        if self._current_overlay_id == overlay_id:
            self._show_map_summary()

    def _on_cursor_world_position_changed(self, point: Optional[QPointF]) -> None:
        if point is None:
            self.status_cursor.setText("X: —  Y: —")
            return
        self.status_cursor.setText(f"X: {point.x():.0f}  Y: {point.y():.0f}")

    def _on_zoom_changed(self, scale: float) -> None:
        self.status_zoom.setText(f"Zoom: {max(1, int(round(scale * 100)))}%")

    def _on_grid_changed(self, enabled: bool) -> None:
        grid_w, grid_h = self.canvas.grid_spacing()
        status = f"{grid_w}x{grid_h} px" if enabled else "выкл"
        self.status_grid.setText(f"Сетка: {status}")

    def _load_attachment_sources(self) -> None:
        self._tasks = self._db.fetch_tasks()
        self._projects = self._db.fetch_projects()
        self._notes = self._db.fetch_notes()
        self._objects = self._db.fetch_objects()
        self._files = self._db.fetch_cloud_files()
        self._maps = self._db.fetch_maps()
        markers = self._db.fetch_map_markers()
        self._tasks_by_id = {item.id: item for item in self._tasks}
        self._projects_by_id = {item.id: item for item in self._projects}
        self._notes_by_id = {item.id: item for item in self._notes}
        self._objects_by_id = {item.id: item for item in self._objects}
        self._files_by_id = {item.id: item for item in self._files}
        self._maps_by_id = {item.id: item for item in self._maps}
        self._markers_by_id = {item.id: item for item in markers}
        self.canvas.set_attachment_sources(
            self._tasks,
            self._projects,
            self._notes,
            self._objects,
            self._files,
            self._maps,
            markers,
        )

    def load_map(self, map_id: int, tiles_path: str, tiles_h: int, tiles_w: int) -> None:
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
            defaults = self.canvas.default_markers()
            self.canvas.set_markers(defaults)
            for marker in defaults:
                self._sync_marker(marker)
                self._markers_by_id[marker.id] = marker
            self.markersChanged.emit()
        else:
            loaded_markers: list[Marker] = []
            for marker in markers:
                loaded_markers.append(
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
            self.canvas.set_markers(loaded_markers)
            for marker in loaded_markers:
                self._markers_by_id[marker.id] = marker
            self.markersChanged.emit()
        self._refresh_status_bar()
        self._show_map_summary()
        self._update_info_panel_width()

    def _show_map_summary(self) -> None:
        self._current_selection_kind = "map"
        self._current_marker_id = None
        self._current_overlay_id = None
        title = self._current_map_title or "Карта"
        self.info_title.setText("Карта")
        subtitle = title
        if self._current_map_project:
            subtitle = f"{title} · {self._current_map_project}"
        self.info_subtitle.setText(subtitle)
        self.info_type_chip.setText("Рабочая область")
        self.info_preview.setPixmap(QPixmap())
        self.info_preview.setText("Выберите объект на карте")
        self._set_summary_values(
            primary=str(len(self.canvas.markers())),
            secondary=str(self._overlay_count("region")),
            tertiary=str(self._overlay_count("path")),
            quaternary=str(self._total_map_links()),
        )
        self._set_detail_values(
            id=str(self._current_map_id or "—"),
            type="Карта",
            coords="—",
            size=self._map_size_text(),
            parent=self._current_map_project or "Без проекта",
            extra=f"Фильтр: {self._filter_title(self._visible_filter)}",
        )
        self.info_links_value.setText("Нет связанных элементов")
        self.info_description.setText("Выберите объект на карте, чтобы увидеть свойства и связи.")
        self.info_important.setText("Маркеры, регионы и маршруты редактируются прямо на карте.")
        self._set_action_state(open_enabled=False, edit_enabled=False, delete_enabled=False)

    def _apply_marker_info(self, marker: Marker) -> None:
        self.info_title.setText(marker.name or "Без названия")
        self.info_subtitle.setText(marker.type or "Объект")
        self.info_type_chip.setText(marker_type_for_color(marker.color).label)
        self._update_info_preview(marker)
        self._set_summary_values(
            primary=f"{marker.x:.0f}",
            secondary=f"{marker.y:.0f}",
            tertiary=f"{marker.size:.1f}",
            quaternary=str(self._marker_link_count(marker)),
        )
        self._set_detail_values(
            id=str(marker.id),
            type=marker.type or "Объект",
            coords=f"X: {marker.x:.0f}  Y: {marker.y:.0f}",
            size=f"{marker.size:.1f} px",
            parent=marker.parent_path or (self._current_map_project or "Без проекта"),
            extra=marker_type_for_color(marker.color).label,
        )
        self.info_links_value.setText(self._format_links_html(marker))
        self.info_description.setText(self._format_text(marker.description, "Нет описания"))
        self.info_important.setText(self._format_text(_format_marker_properties_text(marker.properties), "—"))
        self._set_action_state(open_enabled=True, edit_enabled=True, delete_enabled=True)

    def _apply_overlay_info(self, overlay: MapOverlay) -> None:
        kind_title = "Регион" if overlay.kind == "region" else "Маршрут"
        self.info_title.setText(overlay.title or kind_title)
        self.info_subtitle.setText(kind_title)
        self.info_type_chip.setText(kind_title)
        self.info_preview.setPixmap(QPixmap())
        self.info_preview.setText(kind_title)
        self._set_summary_values(
            primary=str(len(overlay.points)),
            secondary=self._overlay_bounds_text(overlay),
            tertiary=self._overlay_metric_text(overlay),
            quaternary="0",
        )
        self._set_detail_values(
            id=str(overlay.id),
            type=kind_title,
            coords=self._overlay_bounds_text(overlay),
            size=self._overlay_metric_text(overlay),
            parent=self._current_map_title or "Карта",
            extra=f"Точек: {len(overlay.points)}",
        )
        self.info_links_value.setText("Нет связанных элементов")
        self.info_description.setText("Для выбранной геометрии доступны название, форма и цвет.")
        self.info_important.setText("Связи для регионов и маршрутов пока не настроены.")
        self._set_action_state(open_enabled=True, edit_enabled=True, delete_enabled=True)

    def _set_summary_values(self, *, primary: str, secondary: str, tertiary: str, quaternary: str) -> None:
        self.summary_value_labels["primary"].setText(primary or "—")
        self.summary_value_labels["secondary"].setText(secondary or "—")
        self.summary_value_labels["tertiary"].setText(tertiary or "—")
        self.summary_value_labels["quaternary"].setText(quaternary or "—")

    def _set_detail_values(self, **values: str) -> None:
        for key, label in self.detail_labels.items():
            label.setText(values.get(key, "—") or "—")

    def _set_action_state(self, *, open_enabled: bool, edit_enabled: bool, delete_enabled: bool) -> None:
        self.info_open_btn.setEnabled(open_enabled)
        self.info_edit_btn.setEnabled(edit_enabled)
        self.info_delete_btn.setEnabled(delete_enabled)
        self.info_add_link_btn.setEnabled(False)

    def _refresh_status_bar(self) -> None:
        self.status_markers.setText(f"Маркеров: {len(self.canvas.markers())}")
        self.status_regions.setText(f"Регионов: {self._overlay_count('region')}")
        self.status_routes.setText(f"Маршрутов: {self._overlay_count('path')}")
        self.status_zoom.setText(f"Zoom: {self.canvas.zoom_percent()}%")
        self._on_grid_changed(self.canvas.grid_enabled())

    def _overlay_count(self, kind: str) -> int:
        return sum(1 for overlay in self.canvas.overlays() if overlay.kind == kind)

    def _total_map_links(self) -> int:
        return sum(self._marker_link_count(marker) for marker in self.canvas.markers())

    def _map_size_text(self) -> str:
        grid_w, grid_h = self.canvas.grid_spacing()
        return f"Сетка {grid_w}x{grid_h} px"

    def _filter_title(self, filter_key: str) -> str:
        return {
            "all": "Все типы",
            "marker": "Метки",
            "region": "Регионы",
            "path": "Маршруты",
        }.get(filter_key, "Все типы")

    def _overlay_bounds_text(self, overlay: MapOverlay) -> str:
        if not overlay.points:
            return "—"
        xs = [point.x() for point in overlay.points]
        ys = [point.y() for point in overlay.points]
        return f"X: {min(xs):.0f}–{max(xs):.0f}  Y: {min(ys):.0f}–{max(ys):.0f}"

    def _overlay_metric_text(self, overlay: MapOverlay) -> str:
        if not overlay.points:
            return "—"
        xs = [point.x() for point in overlay.points]
        ys = [point.y() for point in overlay.points]
        return f"{abs(max(xs) - min(xs)):.0f} x {abs(max(ys) - min(ys)):.0f}"

    def _current_marker(self) -> Optional[Marker]:
        if self._current_marker_id is None:
            return None
        for marker in self.canvas.markers():
            if marker.id == self._current_marker_id:
                return marker
        return None

    def _current_overlay(self) -> Optional[MapOverlay]:
        if self._current_overlay_id is None:
            return None
        for overlay in self.canvas.overlays():
            if overlay.id == self._current_overlay_id:
                return overlay
        return None

    @staticmethod
    def _marker_link_count(marker: Marker) -> int:
        return sum(
            len(item_ids)
            for item_ids in (
                marker.task_ids,
                marker.project_ids,
                marker.note_ids,
                marker.object_ids,
                marker.file_ids,
                marker.map_ids,
                marker.marker_ids,
            )
        )

    def _linked_titles_text(self, marker: Marker) -> str:
        groups = [
            self._titles_for_ids(marker.task_ids, self._tasks_by_id),
            self._titles_for_ids(marker.project_ids, self._projects_by_id),
            self._titles_for_ids(marker.note_ids, self._notes_by_id),
            self._titles_for_ids(marker.object_ids, self._objects_by_id),
            self._titles_for_ids(marker.file_ids, self._files_by_id),
            self._titles_for_ids(marker.map_ids, self._maps_by_id),
            self._titles_for_ids(marker.marker_ids, self._markers_by_id),
        ]
        return " ".join(part for part in groups if part)

    @staticmethod
    def _titles_for_ids(item_ids: List[int], source: dict[int, Any]) -> str:
        titles = []
        for item_id in item_ids:
            item = source.get(item_id)
            if item is None:
                continue
            title = getattr(item, "title", None) or getattr(item, "name", None) or getattr(item, "rel_path", "")
            if title:
                titles.append(title)
        return " ".join(titles)

    def _format_links_html(self, marker: Marker) -> str:
        sections: list[str] = []
        for kind, label, item_ids, source in (
            ("task", "Задачи", marker.task_ids, self._tasks_by_id),
            ("project", "Проекты", marker.project_ids, self._projects_by_id),
            ("note", "Заметки", marker.note_ids, self._notes_by_id),
            ("object", "Объекты", marker.object_ids, self._objects_by_id),
            ("file", "Файлы", marker.file_ids, self._files_by_id),
            ("map", "Карты", marker.map_ids, self._maps_by_id),
            ("marker", "Метки", marker.marker_ids, self._markers_by_id),
        ):
            chips = []
            for item_id in item_ids:
                item = source.get(item_id)
                if item is None:
                    continue
                title = getattr(item, "title", None) or getattr(item, "name", None) or getattr(item, "rel_path", "—")
                chips.append(f'<a href="{kind}:{item_id}">{html.escape(str(title))}</a>')
            if chips:
                sections.append(f"<b>{label}</b>: " + ", ".join(chips))
        return "<br>".join(sections) if sections else "Нет связанных элементов"

    @staticmethod
    def _format_text(value: str, fallback: str) -> str:
        text = (value or "").strip()
        return text if text and text != "—" else fallback

    def _update_info_preview(self, marker: Marker) -> None:
        preview_size = QSize(max(self.info_preview.width(), 1), max(self.info_preview.height(), 1))
        pixmap = self._load_marker_preview(marker, preview_size)
        if pixmap is not None:
            self.info_preview.setPixmap(pixmap)
            self.info_preview.setText("")
        else:
            self.info_preview.setPixmap(QPixmap())
            self.info_preview.setText("Нет изображения" if not marker.image_path else "Изображение недоступно")
        self.info_preview.setToolTip(marker.image_path or "")

    @staticmethod
    def _load_marker_preview(marker: Marker, target: QSize) -> QPixmap | None:
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
        return pixmap.scaled(
            target,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )

    def _on_open_current(self) -> None:
        marker = self._current_marker()
        if marker is not None:
            self.canvas.view_marker(marker)
            return
        overlay = self._current_overlay()
        if overlay is not None:
            self.focus_overlay(overlay, zoom_boost=0.0)

    def _on_edit_current(self) -> None:
        marker = self._current_marker()
        if marker is not None:
            self.canvas.edit_marker(marker)
            return
        overlay = self._current_overlay()
        if overlay is not None:
            self.canvas.edit_overlay(overlay)

    def _on_delete_current(self) -> None:
        marker = self._current_marker()
        if marker is not None:
            self.canvas.remove_marker(marker)
            return
        overlay = self._current_overlay()
        if overlay is not None:
            self.canvas.remove_overlay(overlay)

    def _save_snapshot(self) -> None:
        suggested = (self._current_map_title or "map").replace(" ", "_")
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить снимок карты",
            f"{suggested}.png",
            "PNG Images (*.png)",
        )
        if not path:
            return
        self.canvas.grab().save(path, "PNG")
        QMessageBox.information(self, "Снимок карты", "Снимок карты сохранён.")

    def _sync_marker(self, marker: Marker) -> None:
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

    def _handle_info_link(self, link: str) -> None:
        if ":" not in link:
            return
        kind, item_id = link.split(":", 1)
        try:
            parsed_id = int(item_id)
        except ValueError:
            return
        self._open_attachment_view(kind, parsed_id)

    def _open_attachment_view(self, kind: str, item_id: int) -> None:
        self.canvas.open_attachment_view(kind, item_id)

    def open_attachment_view(self, kind: str, item_id: int) -> None:
        self._open_attachment_view(kind, item_id)

    def _update_info_panel_width(self) -> None:
        if self._fullscreen_active:
            width = max(int(self.width() * self._info_panel_fullscreen_ratio), 1)
        else:
            width = self._info_panel_expanded_width if self._nav_collapsed else self._info_panel_default_width
        self._set_info_panel_width(width)

    def _set_info_panel_width(self, width: int) -> None:
        total = self.center_splitter.size().width()
        if total <= 0:
            self.info_panel.setFixedWidth(width)
            return
        min_panel = self.info_panel.minimumWidth() or 260
        width = max(min(width, total - 260), min_panel)
        self._info_panel_block_save = True
        self.center_splitter.setSizes([max(total - width, 260), width])
        self._info_panel_block_save = False

    def _on_info_splitter_moved(self, _pos: int, _index: int) -> None:
        if self._info_panel_block_save or self._fullscreen_active:
            return
        sizes = self.center_splitter.sizes()
        if len(sizes) < 2:
            return
        panel_width = sizes[1]
        if panel_width < 260:
            return
        self._info_panel_default_width = panel_width
        self._info_panel_expanded_width = panel_width + self._info_panel_expand_delta
        self._db.set_setting("map_info_panel_width", str(panel_width))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._fullscreen_active:
            self._update_info_panel_width()
        self._reposition_canvas_overlays()

    def _reposition_canvas_overlays(self) -> None:
        if not hasattr(self, "legend_card"):
            return
        margin = 14
        self.legend_card.adjustSize()
        x = margin
        y = max(margin, self.canvas.height() - self.legend_card.height() - margin)
        self.legend_card.move(x, y)


__all__ = ["MapEditorWorkspace"]
