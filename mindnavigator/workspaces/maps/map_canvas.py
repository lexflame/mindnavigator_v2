"""MapCanvas class module for maps workspace."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403
from .map_image_preview_dialog import MapImagePreviewDialog
from .overlay_edit_dialog import OverlayEditDialog

class MapCanvas(QWidget):
    # Класс отрисовки маркеров на карте
    markerSelected = Signal(object)
    markerDoubleClicked = Signal(object)
    markerAdded = Signal(object)
    markerRemoved = Signal(int)
    markerUpdated = Signal(object)
    overlayAdded = Signal(object)
    overlayUpdated = Signal(object)
    overlayRemoved = Signal(int)

    GRID_COLOR = QColor(70, 74, 82, 120)
    GRID_TEXT = QColor(150, 155, 160, 180)
    CREATE_DEFAULT_MARKER_SIZE = 60.0 # Изначальный размер маркера при создании
    DEFAULT_MARKER_SIZE = 8.0 
    MIN_MARKER_SIZE = 10.0
    MAX_MARKER_SIZE = 240.0
    RESIZE_FRAME_PADDING = 8.0
    HANDLE_PIXEL_SIZE = 12.0

    def __init__(self, parent=None):
        # Инициализация канвы карты.
        super().__init__(parent)
        # Настройки взаимодействия и базовых параметров карты.
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self._scale = 1.0
        self._absolute_min_scale = 0.1
        self._min_scale = 0.5
        self._max_scale = 6.0
        self._offset = QPointF(80, 60)
        self._panning = False
        self._last_pos = QPointF()
        self._grid_enabled = True
        self._tool = MapTool.SELECT
        self._simple_mouse_mode = True
        self._background = QPixmap(resource_path("assets/splash.jpg"))
        self._tiles_path = ""
        self._tiles_w = 0
        self._tiles_h = 0
        self._tile_size = QSize(80, 80)
        self._map_pixmap = QPixmap()
        self._markers: List[Marker] = []
        self._next_id = 1
        self._selected: Optional[Marker] = None
        self._resize_marker_id: Optional[int] = None
        self._resize_handle_regions: Dict[str, QRectF] = {}
        self._active_resize_handle: Optional[str] = None
        self._resize_dragging = False
        self._resize_drag_offset = QPointF()
        self._resize_start_pos = QPointF()
        self._resize_start_rect = QRectF()
        self._resize_start_marker_size = 0.0
        self._preview_pos: Optional[QPointF] = None
        self._dragging_marker_id: Optional[int] = None
        self._tasks = []
        self._projects = []
        self._notes = []
        self._objects = []
        self._files = []
        self._maps = []
        self._marker_items = []
        self._tasks_by_id = {}
        self._projects_by_id = {}
        self._notes_by_id = {}
        self._objects_by_id = {}
        self._files_by_id = {}
        self._maps_by_id = {}
        self._marker_items_by_id = {}
        self._marker_icon_cache: Dict[tuple[str, int], QPixmap] = {}
        self._overlays: List[MapOverlay] = []
        self._next_overlay_id = 1
        self._overlay_draft_points: List[QPointF] = []
        self._selected_overlay_id: Optional[int] = None
        # Инициализируем стартовый набор маркеров.
        self._seed_markers()

    @staticmethod
    def default_markers() -> List[Marker]:
        # Базовые маркеры, используемые при первом открытии карты.
        marker_types = marker_type_options()
        blue = marker_types[0]
        green = marker_types[1]
        orange = marker_types[2]
        return [
            Marker(1, "Outpost", 320, 240, blue.color, "Base", MapCanvas.DEFAULT_MARKER_SIZE, "Опорный пункт"),
            Marker(2, "Echo", 520, 360, green.color, "Point", MapCanvas.DEFAULT_MARKER_SIZE, "Контрольная точка"),
            Marker(3, "Delta", 220, 420, orange.color, "Risk", MapCanvas.DEFAULT_MARKER_SIZE, "Зона риска"),
        ]

    def _seed_markers(self) -> None:
        # Заполняем список маркеров значениями по умолчанию.
        self._markers = self.default_markers()
        self._next_id = max((m.id for m in self._markers), default=0) + 1

    def set_markers(self, markers: List[Marker]) -> None:
        # Полностью заменяем список маркеров и сбрасываем выделение.
        self._markers = list(markers)
        self._selected = None
        self._resize_marker_id = None
        self._next_id = max((m.id for m in self._markers), default=0) + 1
        self.markerSelected.emit(None)
        self.update()

    def markers(self) -> List[Marker]:
        # Возвращаем копию списка маркеров.
        return list(self._markers)

    def set_overlays(self, overlays: List[MapOverlay]) -> None:
        # Полностью заменяем список геометрий карты.
        self._overlays = list(overlays)
        self._next_overlay_id = max((item.id for item in self._overlays), default=0) + 1
        self._overlay_draft_points = []
        self._selected_overlay_id = None
        self.update()

    def apply_saved_overlay_id(self, transient_overlay: MapOverlay, saved_id: int) -> None:
        # После сохранения в БД заменяем временный id геометрии на постоянный.
        for idx, item in enumerate(self._overlays):
            if item is transient_overlay or item == transient_overlay:
                self._overlays[idx] = MapOverlay(
                    id=saved_id,
                    kind=item.kind,
                    points=item.points,
                    color=item.color,
                    title=item.title,
                )
                if self._selected_overlay_id == item.id:
                    self._selected_overlay_id = saved_id
                self._next_overlay_id = max(self._next_overlay_id, saved_id + 1)
                self.update()
                return

    def set_attachment_sources(self, tasks, projects, notes, objects, files, maps, markers) -> None:
        # Сохраняем источники данных и создаем словари быстрого доступа.
        self._tasks = list(tasks)
        self._projects = list(projects)
        self._notes = list(notes)
        self._objects = list(objects)
        self._files = list(files)
        self._maps = list(maps)
        self._marker_items = list(markers)
        self._tasks_by_id = {item.id: item for item in tasks}
        self._projects_by_id = {item.id: item for item in projects}
        self._notes_by_id = {item.id: item for item in notes}
        self._objects_by_id = {item.id: item for item in objects}
        self._files_by_id = {item.id: item for item in files}
        self._maps_by_id = {item.id: item for item in maps}
        self._marker_items_by_id = {item.id: item for item in markers}

    def _collect_image_attachments(self, fallback_item: CloudFileData) -> List[CloudFileData]:
        # Собираем изображения из привязанных файлов или fallback.
        if self._selected:
            images = [
                self._files_by_id[file_id]
                for file_id in self._selected.file_ids
                if file_id in self._files_by_id and self._files_by_id[file_id].is_image
            ]
            if images:
                return images
        return [fallback_item] if fallback_item.is_image else []

    def _open_image_attachment(self, file_item: CloudFileData) -> None:
        # Открываем диалог просмотра изображения для файлов/привязок.
        cloud_root = get_database().get_setting("cloud_storage_path", default="").strip()
        if not cloud_root:
            QMessageBox.warning(self, "Изображение", "Папка облачного хранилища не настроена.")
            return
        images = self._collect_image_attachments(file_item)
        if not images:
            QMessageBox.warning(self, "Изображение", "Привязанные изображения не найдены.")
            return
        try:
            start_index = next(idx for idx, item in enumerate(images) if item.id == file_item.id)
        except StopIteration:
            start_index = 0
        dialog = MapImagePreviewDialog(
            self,
            images=images,
            start_index=start_index,
            cloud_root=Path(cloud_root),
        )
        dialog.exec()

    def _open_attachment_view(self, kind: str, item_id: int) -> None:
        # Показываем диалог с данными привязанной сущности.
        sources = {
            "task": self._tasks_by_id,
            "project": self._projects_by_id,
            "note": self._notes_by_id,
            "object": self._objects_by_id,
            "file": self._files_by_id,
            "map": self._maps_by_id,
            "marker": self._marker_items_by_id,
        }
        item = sources.get(kind, {}).get(item_id)
        if not item:
            QMessageBox.warning(self, "Элемент не найден", "Не удалось найти выбранный элемент.")
            return

        # Создаем диалог и формируем содержание.
        dialog = QDialog(self)
        dialog.setObjectName("MapAttachmentDialog")
        dialog.setWindowTitle("Просмотр вложения")
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(12, 12, 12, 12)
        form = QFormLayout()

        def add_row(label: str, value: str, wrap: bool = False) -> None:
            # Упрощенный конструктор строк формы.
            value_label = QLabel(value or "—")
            if wrap:
                value_label.setWordWrap(True)
            form.addRow(label, value_label)

        if kind == "task":
            dialog.setWindowTitle("Задача на карте")
            add_row("Название", item.title)
            add_row("Проект", item.project_title or "—")
            add_row("Дата", item.day.strftime("%d.%m.%Y") if item.day else "—")
            add_row("Время", item.time_text or "—")
            add_row("Приоритет", item.priority or "—")
            add_row("Статус", "Выполнена" if item.done else "В работе")
            add_row("Описание", item.description or "—", wrap=True)
        elif kind == "project":
            dialog.setWindowTitle("Проект на карте")
            add_row("Название", item.title)
            add_row("Область", item.area or "—")
            add_row(
                "Обновлен",
                item.updated.strftime("%d.%m.%Y") if item.updated else "—",
            )
            add_row("Приоритет", item.priority or "—")
            add_row("Архив", "Да" if item.archived else "Нет")
        elif kind == "note":
            dialog.setWindowTitle("Заметка на карте")
            add_row("Название", item.title)
            add_row("Проект", item.project or "—")
            updated = item.updated.strftime("%d.%m.%Y %H:%M") if isinstance(item.updated, datetime) else str(item.updated)
            add_row("Обновлено", updated)
            add_row("Теги", ", ".join(item.tags) if item.tags else "—")
            add_row("Избранное", "Да" if item.favorite else "Нет")
            add_row("Вложения", "Да" if item.attachment else "Нет")
            add_row("Описание", item.preview or "—", wrap=True)
        elif kind == "object":
            dialog.setWindowTitle("Объект на карте")
            add_row("Название", item.title)
            add_row("Каталог", item.catalog or "—")
            add_row("Тип", item.object_type or "—")
            add_row("Статус", item.status or "—")
            add_row("Создан", item.created_at or "—")
            add_row("Обновлен", item.updated_at or "—")
            add_row("Описание", item.description or "—", wrap=True)
        elif kind == "map":
            dialog.setWindowTitle("Карта")
            add_row("Название", item.title)
            add_row("Проект", item.project or "—")
            add_row("Описание", item.description or "—", wrap=True)
        elif kind == "marker":
            dialog.setWindowTitle("Метка карты")
            map_title = self._maps_by_id.get(item.map_id).title if item.map_id in self._maps_by_id else "—"
            add_row("Название", item.name)
            add_row("Карта", map_title)
        elif kind == "file":
            dialog.setWindowTitle("Файл на карте")
            if item.is_image:
                # Для изображений используем полноэкранный просмотр.
                self._open_image_attachment(item)
                return
            add_row("Название", item.name or "—")
            add_row("Путь", item.rel_path or "—", wrap=True)
            add_row("Описание", item.description or "—", wrap=True)
            add_row("Размер", f"{item.size:,} байт")
            add_row("Хэш", item.hash_value or "—", wrap=True)

        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(dialog.reject)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)

        # Стилизация диалога.
        dialog.setStyleSheet(f"""
            QDialog#MapAttachmentDialog {{
                {MATH_PHYS_BACKGROUND}
            }}
            QDialog#MapAttachmentDialog QLabel {{
                color: #cfcfcf;
            }}
            QDialog#MapAttachmentDialog QDialogButtonBox QPushButton {{
                background: #2a2b2f;
                color: #e6e6e6;
                border: 1px solid #3a3b40;
                padding: 6px 12px;
                border-radius: 6px;
            }}
        """)
        dialog.exec()

    def open_attachment_view(self, kind: str, item_id: int) -> None:
        self._open_attachment_view(kind, item_id)


    def set_tool(self, tool: MapTool) -> None:
        # Переключаем активный инструмент на канве.
        self._tool = tool
        self._preview_pos = None
        if tool not in (MapTool.ADD_REGION, MapTool.MEASURE):
            self._overlay_draft_points = []
        self.update()

    def tool(self) -> MapTool:
        # Текущий активный инструмент.
        return self._tool

    def set_simple_mouse_mode(self, enabled: bool) -> None:
        self._simple_mouse_mode = bool(enabled)
        if self._simple_mouse_mode:
            self._dragging_marker_id = None
            self._resize_dragging = False

    def _is_marker_drag_allowed(self) -> bool:
        return marker_drag_allowed(self._tool, self._simple_mouse_mode)

    def set_grid_enabled(self, enabled: bool) -> None:
        # Включаем или выключаем сетку и перерисовываем.
        self._grid_enabled = enabled
        self.update()

    def set_tiles(self, tiles_path: str, tiles_h: int, tiles_w: int) -> None:
        # Обновляем параметры тайлов и перестраиваем карту.
        self._tiles_path = (tiles_path or "").strip()
        self._tiles_h = max(0, int(tiles_h or 0))
        self._tiles_w = max(0, int(tiles_w or 0))
        self._load_tiles()
        self.reset_view()
        self.update()

    def reset_view(self) -> None:
        # Подгоняем масштаб под виджет и центрируем карту.
        fit_scale = self._fit_scale_to_view()
        self._min_scale = min(self._absolute_min_scale, fit_scale)
        self._scale = min(1.0, fit_scale) if fit_scale > 0 else 1.0
        self._offset = self._center_offset_for_scale(self._scale)

    def _content_bounds(self) -> QRectF:
        # Возвращаем границы содержимого, которое нужно вписать.
        map_bounds = self._map_bounds()
        if not map_bounds.isNull():
            return map_bounds
        if not self._background.isNull():
            return QRectF(QPointF(0, 0), self._background.size())
        return QRectF(0, 0, 1200, 800)

    def _fit_scale_to_view(self) -> float:
        # Рассчитываем масштаб, при котором контент помещается в виджет.
        bounds = self._content_bounds()
        if bounds.isNull():
            return 1.0
        padding = 40
        view_w = max(1, self.width() - padding)
        view_h = max(1, self.height() - padding)
        scale_x = view_w / bounds.width()
        scale_y = view_h / bounds.height()
        return max(0.01, min(scale_x, scale_y))

    def _center_offset_for_scale(self, scale: float) -> QPointF:
        # Вычисляем смещение, чтобы центр содержимого оказался в центре вида.
        bounds = self._content_bounds()
        center_world = bounds.center()
        view_center = QPointF(self.width() / 2, self.height() / 2)
        return view_center - center_world * scale

    def paintEvent(self, event):
        # Отрисовка содержимого канвы.
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.fillRect(self.rect(), QColor("#1a1c20"))

        # Применяем трансформации для масштаба и смещения.
        painter.save()
        painter.translate(self._offset)
        painter.scale(self._scale, self._scale)

        # Основные слои: фон, сетка, маркеры, предпросмотр.
        self._draw_background(painter)
        if self._grid_enabled:
            self._draw_grid(painter)
        self._draw_overlays(painter)
        self._draw_markers(painter)
        if self._preview_pos and self._tool == MapTool.ADD_MARKER:
            self._draw_preview(painter)
        if self._tool in (MapTool.ADD_REGION, MapTool.MEASURE):
            self._draw_overlay_draft(painter)

        painter.restore()

    def resizeEvent(self, event):
        # Сохраняем мировую точку центра и корректируем масштаб после ресайза.
        world_center = self._map_to_world(QPointF(self.width() / 2, self.height() / 2))
        super().resizeEvent(event)
        fit_scale = self._fit_scale_to_view()
        self._min_scale = min(self._absolute_min_scale, fit_scale)
        if self._scale < self._min_scale:
            self._scale = self._min_scale
        self._offset = QPointF(self.width() / 2, self.height() / 2) - world_center * self._scale

    def _draw_background(self, painter: QPainter) -> None:
        # Отрисовываем загруженную карту или фон по умолчанию.
        if not self._map_pixmap.isNull():
            painter.setOpacity(1.0)
            painter.drawPixmap(QPointF(0, 0), self._map_pixmap)
            return
        if not self._map_bounds().isNull():
            painter.fillRect(self._map_bounds(), QColor("#3a3f36"))
            return
        if self._background.isNull():
            painter.fillRect(QRectF(0, 0, 1200, 800), QColor("#3a3f36"))
            return
        painter.setOpacity(0.9)
        painter.drawPixmap(QPointF(0, 0), self._background)
        painter.setOpacity(1.0)

    def _draw_grid(self, painter: QPainter) -> None:
        # Рисуем сетку поверх карты.
        spacing_x = max(1, self._tile_size.width())
        spacing_y = max(1, self._tile_size.height())
        rect = self._world_view_rect()
        map_bounds = self._map_bounds()
        if not map_bounds.isNull():
            rect = rect.intersected(map_bounds)
            if rect.isEmpty():
                return

        left = int(rect.left() // spacing_x * spacing_x)
        top = int(rect.top() // spacing_y * spacing_y)
        right = int(rect.right())
        bottom = int(rect.bottom())

        pen = QPen(self.GRID_COLOR)
        pen.setWidthF(1.0 / self._scale)
        painter.setPen(pen)

        # Основные линии сетки.
        for x in range(left, right + spacing_x, spacing_x):
            painter.drawLine(x, top, x, bottom)
        for y in range(top, bottom + spacing_y, spacing_y):
            painter.drawLine(left, y, right, y)

        # Подписи координат.
        painter.setPen(self.GRID_TEXT)
        painter.setFont(QFont("Segoe UI", 8))
        for x in range(left, right + spacing_x, spacing_x):
            painter.drawText(QPointF(x + 4, top + 14), f"{x}")
        for y in range(top, bottom + spacing_y, spacing_y):
            painter.drawText(QPointF(left + 4, y - 4), f"{y}")

    def _marker_icon_pixmap(self, marker: Marker, size: int) -> QPixmap | None:
        # Получаем иконку маркера с учетом выбранного типа.
        option = marker_type_for_color(marker.color)
        cache_key = (option.key, size)
        cached = self._marker_icon_cache.get(cache_key)
        if cached is not None:
            return cached
        pixmap = marker_type_pixmap(option, QSize(size, size))
        if pixmap is None:
            return None
        self._marker_icon_cache[cache_key] = pixmap
        return pixmap

    def _draw_markers(self, painter: QPainter) -> None:
        # Рисуем все маркеры и рамку выделения.
        self._resize_handle_regions = {}
        for marker in self._markers:
            is_selected = self._selected and marker.id == self._selected.id
            radius = marker.size + (2.0 if is_selected else 0.0)
            icon_size = max(12, int(marker.size * 2))
            icon_pixmap = self._marker_icon_pixmap(marker, icon_size)
            if icon_pixmap is not None:
                top_left = QPointF(marker.x - icon_size / 2, marker.y - icon_size / 2)
                painter.drawPixmap(top_left, icon_pixmap)
            else:
                painter.setBrush(marker.color)
                painter.setPen(QPen(QColor("#111111"), max(1.0, 1.0 / self._scale)))
                painter.drawEllipse(QPointF(marker.x, marker.y), radius, radius)
            if is_selected:
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.setPen(QPen(QColor("#dfe7f0"), max(1.0, 1.4 / self._scale)))
                painter.drawEllipse(QPointF(marker.x, marker.y), radius + 2, radius + 2)
            painter.setPen(QColor("#e5e5e5"))
            painter.setFont(QFont("Segoe UI", self._marker_label_font_size(marker)))
            painter.drawText(
                QPointF(marker.x + marker.size + 6.0, marker.y - (marker.size + 2.0)),
                marker.name,
            )
            # При активном режиме изменения размера рисуем ручки.
            if self._resize_marker_id == marker.id:
                self._draw_resize_handles(painter, marker)

    def _draw_overlays(self, painter: QPainter) -> None:
        # Отрисовываем полигоны областей и пути сообщения.
        for overlay in self._overlays:
            if len(overlay.points) < 2:
                continue
            is_selected = overlay.id == self._selected_overlay_id
            pen_width = 3.0 / self._scale if is_selected else 2.0 / self._scale
            pen = QPen(overlay.color, max(1.0, pen_width))
            painter.setPen(pen)
            if overlay.kind == "region":
                poly = QPolygonF(overlay.points)
                fill = QColor(overlay.color)
                fill.setAlpha(95 if is_selected else 55)
                painter.setBrush(fill)
                painter.drawPolygon(poly)
            else:
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawPolyline(QPolygonF(overlay.points))
            if is_selected and overlay.points:
                painter.setBrush(QColor("#ffffff"))
                painter.setPen(QPen(QColor("#101216"), max(1.0, 1.0 / self._scale)))
                for point in overlay.points:
                    painter.drawEllipse(point, 3.0 / self._scale, 3.0 / self._scale)

    def _overlay_by_id(self, overlay_id: int) -> Optional[MapOverlay]:
        for overlay in self._overlays:
            if overlay.id == overlay_id:
                return overlay
        return None

    def _overlay_at(self, world_pos: QPointF) -> Optional[MapOverlay]:
        # Проверяем попадание в область или в линию пути.
        tolerance = max(6.0, 8.0 / self._scale)
        for overlay in reversed(self._overlays):
            points = overlay.points
            if len(points) < 2:
                continue
            if overlay.kind == "region":
                polygon = QPolygonF(points)
                if polygon.containsPoint(world_pos, Qt.FillRule.OddEvenFill):
                    return overlay
                if self._distance_to_polyline(world_pos, points, closed=True) <= tolerance:
                    return overlay
            else:
                if self._distance_to_polyline(world_pos, points, closed=False) <= tolerance:
                    return overlay
        return None

    @staticmethod
    def _distance_to_polyline(point: QPointF, points: List[QPointF], closed: bool) -> float:
        if len(points) < 2:
            return float("inf")
        min_distance = float("inf")
        segment_count = len(points)
        end_index = segment_count if closed else segment_count - 1
        for i in range(end_index):
            a = points[i]
            b = points[(i + 1) % segment_count]
            distance = MapCanvas._distance_to_segment(point, a, b)
            if distance < min_distance:
                min_distance = distance
        return min_distance

    @staticmethod
    def _distance_to_segment(p: QPointF, a: QPointF, b: QPointF) -> float:
        ax, ay = a.x(), a.y()
        bx, by = b.x(), b.y()
        px, py = p.x(), p.y()
        abx = bx - ax
        aby = by - ay
        denom = abx * abx + aby * aby
        if denom <= 0.0:
            dx = px - ax
            dy = py - ay
            return (dx * dx + dy * dy) ** 0.5
        t = ((px - ax) * abx + (py - ay) * aby) / denom
        t = max(0.0, min(1.0, t))
        cx = ax + abx * t
        cy = ay + aby * t
        dx = px - cx
        dy = py - cy
        return (dx * dx + dy * dy) ** 0.5

    def _draw_overlay_draft(self, painter: QPainter) -> None:
        # Отрисовываем черновую линию/область при режиме рисования.
        if not self._overlay_draft_points:
            return
        preview_color = QColor("#67b9ff") if self._tool == MapTool.MEASURE else QColor("#f2c26d")
        pen = QPen(preview_color, max(1.0, 2.0 / self._scale))
        pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)
        if len(self._overlay_draft_points) == 1:
            p = self._overlay_draft_points[0]
            painter.drawEllipse(p, 4.0 / self._scale, 4.0 / self._scale)
            return
        poly = QPolygonF(self._overlay_draft_points)
        if self._tool == MapTool.ADD_REGION and len(self._overlay_draft_points) >= 3:
            fill = QColor(preview_color)
            fill.setAlpha(40)
            painter.setBrush(fill)
            painter.drawPolygon(poly)
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPolyline(poly)

    def _draw_preview(self, painter: QPainter) -> None:
        # Предпросмотр размещения нового маркера.
        if not self._preview_pos:
            return
        painter.setPen(QPen(QColor("#cfd8dc"), 1.0 / self._scale))
        painter.setBrush(QColor(200, 200, 200, 60))
        painter.drawEllipse(self._preview_pos, self.CREATE_DEFAULT_MARKER_SIZE, self.CREATE_DEFAULT_MARKER_SIZE)

    def _world_view_rect(self) -> QRectF:
        # Рассчитываем видимую область в мировых координатах.
        inv_scale = 1.0 / self._scale
        top_left = (QPointF(0, 0) - self._offset) * inv_scale
        bottom_right = (QPointF(self.width(), self.height()) - self._offset) * inv_scale
        return QRectF(top_left, bottom_right).normalized()

    def _map_to_world(self, pos: QPointF) -> QPointF:
        # Перевод координат из экранных в мировые.
        pos_f = QPointF(pos)
        delta = pos_f - self._offset
        return QPointF(delta.x() / self._scale, delta.y() / self._scale)

    def _map_from_world(self, pos: QPointF) -> QPointF:
        # Перевод координат из мировых в экранные.
        return pos * self._scale + self._offset

    def _map_bounds(self) -> QRectF:
        # Границы карты на основе размера тайлов.
        if self._tiles_w <= 0 or self._tiles_h <= 0:
            return QRectF()
        width = self._tile_size.width() * self._tiles_w
        height = self._tile_size.height() * self._tiles_h
        return QRectF(0, 0, float(width), float(height))

    def _load_tiles(self) -> None:
        # Загружаем тайлы карты и собираем единый QPixmap.
        self._map_pixmap = QPixmap()
        base = Path(self._tiles_path)
        tile_size = QSize(0, 0)
        if self._tiles_w <= 0 or self._tiles_h <= 0:
            return
        if base and base.exists():
            for row in range(1, self._tiles_h + 1):
                for col in range(1, self._tiles_w + 1):
                    tile_path = base / f"{row}_{col}.png"
                    if not tile_path.exists():
                        continue
                    pixmap = QPixmap(str(tile_path))
                    if pixmap.isNull():
                        continue
                    tile_size = pixmap.size()
                    break
                if tile_size.width() > 0:
                    break
        if tile_size.isEmpty():
            # Если тайлы не найдены, используем размер по умолчанию.
            tile_size = QSize(80, 80)
        self._tile_size = tile_size
        map_width = tile_size.width() * self._tiles_w
        map_height = tile_size.height() * self._tiles_h
        if map_width <= 0 or map_height <= 0:
            return
        self._map_pixmap = QPixmap(map_width, map_height)
        self._map_pixmap.fill(QColor(0, 0, 0, 0))
        painter = QPainter(self._map_pixmap)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        if base and base.exists():
            # Проходим по плиткам и рисуем их в общий холст.
            for row in range(1, self._tiles_h + 1):
                for col in range(1, self._tiles_w + 1):
                    tile_path = base / f"{row}_{col}.png"
                    if not tile_path.exists():
                        continue
                    pixmap = QPixmap(str(tile_path))
                    if pixmap.isNull():
                        continue
                    if pixmap.size() != tile_size:
                        pixmap = pixmap.scaled(tile_size, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    x = (col - 1) * tile_size.width()
                    y = (row - 1) * tile_size.height()
                    painter.drawPixmap(QPointF(x, y), pixmap)
        painter.end()

    def _marker_at(self, world_pos: QPointF) -> Optional[Marker]:
        # Проверяем попадание в маркер или его подпись.
        for marker in reversed(self._markers):
            dist = (QPointF(marker.x, marker.y) - world_pos)
            hit_radius = max(10.0, marker.size + 6.0)
            if dist.manhattanLength() <= hit_radius:
                return marker
            label_rect = self._marker_label_rect(marker)
            if label_rect.contains(world_pos):
                return marker
        return None

    def _marker_by_id(self, marker_id: int) -> Optional[Marker]:
        # Ищем маркер по идентификатору.
        for marker in self._markers:
            if marker.id == marker_id:
                return marker
        return None

    def _set_marker(self, updated: Marker) -> None:
        # Обновляем маркер в списке и уведомляем подписчиков.
        self._markers = [updated if m.id == updated.id else m for m in self._markers]
        self._selected = updated
        self.markerSelected.emit(updated)
        self.markerUpdated.emit(updated)
        self.update()

    def _draw_resize_handles(self, painter: QPainter, marker: Marker) -> None:
        # Рисуем рамку выделения и ручки изменения размера.
        selection_rect = self._selection_rect(marker)
        handle_size = max(8.0 / self._scale, self.HANDLE_PIXEL_SIZE / self._scale)
        half = handle_size / 2
        self._resize_handle_regions = {}

        pen = QPen(QColor("#67c7ff"), max(1.0, 2.0 / self._scale))
        painter.save()
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(pen)
        painter.drawRect(selection_rect)

        painter.setBrush(QColor("#2b2f36"))
        painter.setPen(QPen(QColor("#dfe7f0"), max(1.0, 1.2 / self._scale)))

        cx = selection_rect.center().x()
        cy = selection_rect.center().y()
        left = selection_rect.left()
        right = selection_rect.right()
        top = selection_rect.top()
        bottom = selection_rect.bottom()
        positions = {
            "nw": QPointF(left, top),
            "n": QPointF(cx, top),
            "ne": QPointF(right, top),
            "e": QPointF(right, cy),
            "se": QPointF(right, bottom),
            "s": QPointF(cx, bottom),
            "sw": QPointF(left, bottom),
            "w": QPointF(left, cy),
        }
        for name, center in positions.items():
            rect = QRectF(center.x() - half, center.y() - half, handle_size, handle_size)
            painter.drawRect(rect)
            self._resize_handle_regions[name] = rect
        painter.restore()

    def _marker_label_font_size(self, marker: Marker) -> int:
        # Размер шрифта подписи зависит от размера маркера.
        size = int(round(8.0 * (marker.size / self.DEFAULT_MARKER_SIZE)))
        return max(6, size)

    def _marker_label_rect(self, marker: Marker) -> QRectF:
        # Рассчитываем область, занимаемую подписью маркера.
        font = QFont("Segoe UI", self._marker_label_font_size(marker))
        metrics = QFontMetricsF(font)
        text = marker.name
        width = metrics.horizontalAdvance(text)
        height = metrics.height()
        pos = QPointF(marker.x + marker.size + 6.0, marker.y - (marker.size + 2.0))
        top = pos.y() - metrics.ascent()
        return QRectF(pos.x(), top, width, height)

    def _selection_rect(self, marker: Marker) -> QRectF:
        # Возвращаем квадратную рамку выделения вокруг маркера и подписи.
        marker_rect = QRectF(
            marker.x - marker.size,
            marker.y - marker.size,
            marker.size * 2.0,
            marker.size * 2.0,
        )
        label_rect = self._marker_label_rect(marker)
        combined = marker_rect.united(label_rect)
        padding = self.RESIZE_FRAME_PADDING / self._scale
        combined = combined.adjusted(-padding, -padding, padding, padding)
        size = max(combined.width(), combined.height())
        center = combined.center()
        return QRectF(center.x() - size / 2, center.y() - size / 2, size, size)

    def _resize_handle_at(self, world_pos: QPointF) -> Optional[str]:
        # Определяем, в какую ручку попадает курсор.
        for direction, rect in self._resize_handle_regions.items():
            if rect.contains(world_pos):
                return direction
        return None

    @staticmethod
    def _resize_handle_cursor(handle: str) -> Qt.CursorShape:
        # Возвращаем курсор для конкретной ручки изменения размера.
        if handle in ("nw", "se"):
            return Qt.CursorShape.SizeFDiagCursor
        if handle in ("ne", "sw"):
            return Qt.CursorShape.SizeBDiagCursor
        if handle in ("n", "s"):
            return Qt.CursorShape.SizeVerCursor
        if handle in ("e", "w"):
            return Qt.CursorShape.SizeHorCursor
        return Qt.CursorShape.SizeAllCursor

    @staticmethod
    def _resize_scale_delta(handle: str, delta: QPointF) -> float:
        # Преобразуем смещение мыши в изменение масштаба маркера.
        dirs = {
            "n": (0, -1),
            "s": (0, 1),
            "e": (1, 0),
            "w": (-1, 0),
            "nw": (-1, -1),
            "ne": (1, -1),
            "sw": (-1, 1),
            "se": (1, 1),
        }
        dir_x, dir_y = dirs.get(handle, (0, 0))
        if dir_x and dir_y:
            return max(delta.x() * dir_x, delta.y() * dir_y)
        if dir_x:
            return delta.x() * dir_x
        return delta.y() * dir_y

    def _enable_resize_mode(self, marker_id: int) -> None:
        # Включаем режим изменения размера выбранного маркера.
        marker = self._marker_by_id(marker_id)
        if not marker:
            return
        self._selected = marker
        self.markerSelected.emit(marker)
        self._resize_marker_id = marker_id
        self._active_resize_handle = None
        self._resize_dragging = False
        self.update()

    def _zoom_to_marker(self, marker: Marker) -> None:
        # Приближаем камеру к выбранному маркеру.
        target_scale = min(self._max_scale, max(self._min_scale, self._scale * 1.4))
        view_center = QPointF(self.width() / 2, self.height() / 2)
        self._scale = target_scale
        self._offset = view_center - QPointF(marker.x, marker.y) * self._scale
        self.update()

    def focus_on_marker(self, marker: Marker, zoom_boost: float = 4.0) -> None:
        # Центрируемся на маркере и увеличиваем масштаб.
        target_scale = min(self._max_scale, max(self._min_scale, self._scale + zoom_boost))
        view_center = QPointF(self.width() / 2, self.height() / 2)
        self._selected = marker
        self.markerSelected.emit(marker)
        self._scale = target_scale
        self._offset = view_center - QPointF(marker.x, marker.y) * self._scale
        self.setFocus(Qt.FocusReason.OtherFocusReason)
        self.update()

    def _adjust_marker_size(self, marker: Marker, delta: float) -> None:
        # Изменяем размер маркера в пределах допустимых значений.
        new_size = min(self.MAX_MARKER_SIZE, max(self.MIN_MARKER_SIZE, marker.size + delta))
        if new_size == marker.size:
            return
        self._set_marker(
            Marker(
                marker.id,
                marker.name,
                marker.x,
                marker.y,
                marker.color,
                marker.type,
                new_size,
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

    def mousePressEvent(self, event):
        # Обработка кликов мыши на канве.
        if event.button() == Qt.MouseButton.RightButton:
            if self._tool in (MapTool.ADD_REGION, MapTool.MEASURE):
                if self._overlay_draft_points:
                    self._finalize_overlay()
                else:
                    self._open_context_menu(event.pos())
                return
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                # Ctrl + ПКМ — открыть карточку выбранного маркера.
                world_pos = self._map_to_world(event.position())
                marker = self._marker_at(world_pos)
                if marker:
                    self._selected = marker
                    self.markerSelected.emit(marker)
                    self._view_marker(marker)
                return
            # Обычный ПКМ открывает контекстное меню.
            self._open_context_menu(event.pos())
            return

        if event.button() == Qt.MouseButton.LeftButton:
            if self._tool in (MapTool.ADD_REGION, MapTool.MEASURE):
                self._append_overlay_point(self._map_to_world(event.position()))
                return
            # ЛКМ — выбор, перемещение, добавление маркеров или панорамирование.
            world_pos = self._map_to_world(event.position())
            if self._resize_marker_id is not None:
                handle = self._resize_handle_at(world_pos)
                if handle:
                    marker = self._marker_by_id(self._resize_marker_id)
                    if marker:
                        self._active_resize_handle = handle
                        self._resize_start_pos = world_pos
                        self._resize_start_rect = self._selection_rect(marker)
                        self._resize_start_marker_size = marker.size
                    return
                # Если зажали рамку, включаем перемещение маркера.
                marker = self._marker_by_id(self._resize_marker_id)
                if marker and self._selection_rect(marker).contains(world_pos):
                    if self._simple_mouse_mode:
                        return
                    self._resize_dragging = True
                    self._resize_drag_offset = world_pos - QPointF(marker.x, marker.y)
                    return
                self._resize_marker_id = None
                self._active_resize_handle = None
            if self._tool == MapTool.ADD_MARKER:
                # Добавляем новый маркер.
                self._add_marker(world_pos)
                return
            marker = self._marker_at(world_pos)
            if marker:
                # Выделяем маркер и готовимся к перетаскиванию.
                self._selected = marker
                self._selected_overlay_id = None
                self.markerSelected.emit(marker)
                self._dragging_marker_id = marker.id if self._is_marker_drag_allowed() else None
                self.update()
                return
            overlay = self._overlay_at(world_pos)
            if overlay is not None:
                self._selected_overlay_id = overlay.id
                self._selected = None
                self.markerSelected.emit(None)
                self.update()
                return
            # Снимаем выделение и включаем панорамирование.
            self._selected = None
            self._selected_overlay_id = None
            self.markerSelected.emit(None)
            self._dragging_marker_id = None
            self._panning = True
            self._last_pos = event.position()
            self.update()

    def mouseMoveEvent(self, event):
        # Обработка движения мыши для ресайза, перетаскивания и панорамирования.
        if self._resize_marker_id is not None:
            world_pos = self._map_to_world(event.position())
            marker = self._marker_by_id(self._resize_marker_id)
            if marker and self._active_resize_handle:
                delta = world_pos - self._resize_start_pos
                size_delta = self._resize_scale_delta(self._active_resize_handle, delta)
                if self._resize_start_rect.width() > 0:
                    new_frame = max(8.0, self._resize_start_rect.width() + 2 * size_delta)
                    scale_factor = new_frame / self._resize_start_rect.width()
                    new_size = self._resize_start_marker_size * scale_factor
                    new_size = min(self.MAX_MARKER_SIZE, max(self.MIN_MARKER_SIZE, new_size))
                    updated = Marker(
                        marker.id,
                        marker.name,
                        marker.x,
                        marker.y,
                        marker.color,
                        marker.type,
                        new_size,
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
                    self._set_marker(updated)
                    return
            if marker and self._resize_dragging:
                # Перемещаем маркер в режиме изменения размера.
                new_center = world_pos - self._resize_drag_offset
                updated = Marker(
                    marker.id,
                    marker.name,
                    new_center.x(),
                    new_center.y(),
                    marker.color,
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
                self._set_marker(updated)
                return
            if marker:
                # Обновляем курсор при наведении на ручки.
                handle = self._resize_handle_at(world_pos)
                if handle:
                    self.setCursor(self._resize_handle_cursor(handle))
                    return
                if self._selection_rect(marker).contains(world_pos):
                    if self._is_marker_drag_allowed():
                        self.setCursor(Qt.CursorShape.SizeAllCursor)
                    else:
                        self.unsetCursor()
                    return
            self.unsetCursor()
        if self._dragging_marker_id is not None and self._is_marker_drag_allowed():
            # Перетаскиваем выбранный маркер.
            world_pos = self._map_to_world(event.position())
            marker = self._marker_by_id(self._dragging_marker_id)
            if marker:
                updated = Marker(
                    marker.id,
                    marker.name,
                    world_pos.x(),
                    world_pos.y(),
                    marker.color,
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
                self._set_marker(updated)
                return
        if self._panning:
            # Панорамируем карту.
            delta = event.position() - self._last_pos
            self._offset += delta
            self._last_pos = event.position()
            self.update()
            return
        if self._tool == MapTool.ADD_MARKER:
            # Обновляем предпросмотр при добавлении маркера.
            self._preview_pos = self._map_to_world(event.position())
            self.update()

    def mouseReleaseEvent(self, event):
        # Сбрасываем состояния после отпускания кнопки мыши.
        if event.button() == Qt.MouseButton.LeftButton:
            self._panning = False
            self._dragging_marker_id = None
            self._active_resize_handle = None
            self._resize_dragging = False

    def mouseDoubleClickEvent(self, event):
        # Двойной клик по маркеру — фокусируем и увеличиваем. В режимах рисования завершает контур.
        if event.button() == Qt.MouseButton.LeftButton:
            if self._tool in (MapTool.ADD_REGION, MapTool.MEASURE):
                self._append_overlay_point(self._map_to_world(event.position()))
                self._finalize_overlay()
                return
            world_pos = self._map_to_world(event.position())
            marker = self._marker_at(world_pos)
            if marker:
                self._selected = marker
                self.markerSelected.emit(marker)
                self._zoom_to_marker(marker)
                self.markerDoubleClicked.emit(marker)
                return
        super().mouseDoubleClickEvent(event)

    def _append_overlay_point(self, point: QPointF) -> None:
        # Добавляем вершину чернового контура.
        self._overlay_draft_points.append(point)
        self.update()

    def _finalize_overlay(self) -> None:
        # Завершаем построение области/пути и переносим в список геометрий.
        points = list(self._overlay_draft_points)
        if self._tool == MapTool.ADD_REGION and len(points) >= 3:
            overlay = MapOverlay(
                id=self._next_overlay_id,
                kind="region",
                points=points,
                color=QColor("#e2a84e"),
                title=f"Область {self._next_overlay_id}",
            )
            self._next_overlay_id += 1
            self._overlays.append(overlay)
            self.overlayAdded.emit(overlay)
        elif self._tool == MapTool.MEASURE and len(points) >= 2:
            overlay = MapOverlay(
                id=self._next_overlay_id,
                kind="path",
                points=points,
                color=QColor("#6cb5ff"),
                title=f"Путь {self._next_overlay_id}",
            )
            self._next_overlay_id += 1
            self._overlays.append(overlay)
            self.overlayAdded.emit(overlay)
        self._overlay_draft_points = []
        self.update()

    def wheelEvent(self, event):
        # Обрабатываем масштабирование и изменение размера маркера.
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            cursor_pos = event.position()
            world_pos = self._map_to_world(cursor_pos)
            marker = self._marker_at(world_pos)
            if marker:
                # Ctrl + колесо меняет размер маркера.
                delta = 1.0 if event.angleDelta().y() > 0 else -1.0
                self._adjust_marker_size(marker, delta)
                return
        delta = event.angleDelta().y()
        if delta == 0:
            return
        factor = 1.15 if delta > 0 else 1 / 1.15
        new_scale = max(self._min_scale, min(self._max_scale, self._scale * factor))
        if new_scale == self._scale:
            return
        cursor_pos = event.position()
        world_before = self._map_to_world(cursor_pos)
        self._scale = new_scale
        self._offset = cursor_pos - world_before * self._scale
        self.update()

    def _add_marker(self, world_pos: QPointF) -> None:
        # Создаем новый маркер с дефолтными параметрами.
        default_type = default_marker_type()
        marker = Marker(
            self._next_id,
            f"Marker {self._next_id}",
            float(world_pos.x()),
            float(world_pos.y()),
            default_type.color,
            "Point",
            self.CREATE_DEFAULT_MARKER_SIZE,
            "",
            "",
            [],
            [],
            [],
            [],
            [],
            [],
            [],
            "",
            "",
        )
        self._next_id += 1
        self._markers.append(marker)
        self._selected = marker
        self.markerAdded.emit(marker)
        self.markerSelected.emit(marker)
        self._preview_pos = None
        self.update()

    def _remove_marker(self, marker: Marker) -> None:
        # Удаляем маркер и сбрасываем выделение при необходимости.
        self._markers = [m for m in self._markers if m.id != marker.id]
        self.markerRemoved.emit(marker.id)
        if self._selected and self._selected.id == marker.id:
            self._selected = None
            self.markerSelected.emit(None)
        self.update()

    def _set_overlay(self, updated: MapOverlay) -> None:
        # Обновляем оверлей в списке и уведомляем подписчиков.
        self._overlays = [updated if item.id == updated.id else item for item in self._overlays]
        self._selected_overlay_id = updated.id
        self.overlayUpdated.emit(updated)
        self.update()

    def _remove_overlay(self, overlay: MapOverlay) -> None:
        # Удаляем область/путь.
        self._overlays = [item for item in self._overlays if item.id != overlay.id]
        if self._selected_overlay_id == overlay.id:
            self._selected_overlay_id = None
        self.overlayRemoved.emit(overlay.id)
        self.update()

    def _edit_overlay(self, overlay: MapOverlay) -> None:
        # Редактируем параметры области/пути через отдельный диалог.
        dialog = OverlayEditDialog(overlay, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        title, kind, color = dialog.values()
        self._set_overlay(
            MapOverlay(
                id=overlay.id,
                kind=kind,
                points=overlay.points,
                color=color,
                title=title,
            )
        )

    def _edit_marker(self, marker: Marker) -> None:
        # Открываем диалог редактирования маркера.
        def task_label(item: object) -> str:
            # Отображение задачи в списке.
            task_title = str(getattr(item, "title", "") or "")
            project_title = str(getattr(item, "project_title", "") or "")
            return f"{task_title} · {project_title}" if project_title else task_title

        def project_label(item: object) -> str:
            # Отображение проекта в списке.
            project_title = str(getattr(item, "title", "") or "")
            project_area = str(getattr(item, "area", "") or "")
            return f"{project_title} · {project_area}" if project_area else project_title

        def note_label(item: object) -> str:
            # Отображение заметки в списке.
            note_title = str(getattr(item, "title", "") or "")
            note_project = str(getattr(item, "project", "") or "")
            return f"{note_title} · {note_project}" if note_project else note_title

        def object_label(item: object) -> str:
            # Отображение объекта в списке.
            object_title = str(getattr(item, "title", "") or "")
            object_catalog = str(getattr(item, "catalog", "") or "")
            return f"{object_title} · {object_catalog}" if object_catalog else object_title

        def file_label(item: object) -> str:
            # Отображение файла в списке.
            file_name = str(getattr(item, "name", "") or "")
            rel_path = str(getattr(item, "rel_path", "") or "")
            return file_name or rel_path

        def map_label(item: object) -> str:
            # Отображение карты в списке.
            map_title = str(getattr(item, "title", "") or "")
            map_project = str(getattr(item, "project", "") or "")
            return f"{map_title} · {map_project}" if map_project else map_title

        def marker_label(item: object) -> str:
            # Отображение метки в списке.
            map_id = getattr(item, "map_id", None)
            marker_name = str(getattr(item, "name", "") or "")
            map_title = self._maps_by_id.get(map_id).title if map_id in self._maps_by_id else ""
            return f"{marker_name} · {map_title}" if map_title else marker_name

        # Источники сущностей для привязок.
        entity_sources = {
            "task": MapLabelEntitySource(
                "Задачи",
                self._tasks,
                task_label,
                "Привязать задачу...",
                "fa5s.tasks",
                "task",
            ),
            "project": MapLabelEntitySource(
                "Проекты",
                self._projects,
                project_label,
                "Привязать проект...",
                "fa5s.folder-open",
                "project",
            ),
            "note": MapLabelEntitySource(
                "Заметки",
                self._notes,
                note_label,
                "Привязать заметку...",
                "fa5s.sticky-note",
                "note",
            ),
            "object": MapLabelEntitySource(
                "Объекты",
                self._objects,
                object_label,
                "Привязать объект...",
                "fa5s.cube",
                "object",
            ),
            "file": MapLabelEntitySource(
                "Файлы",
                self._files,
                file_label,
                "Привязать файл...",
                "fa5s.paperclip",
                "file",
            ),
            "map": MapLabelEntitySource(
                "Карты",
                self._maps,
                map_label,
                "Привязать карту...",
                "fa5s.map-marked-alt",
                "map",
            ),
            "marker": MapLabelEntitySource(
                "Метки",
                self._marker_items,
                marker_label,
                "Привязать метку...",
                "fa5s.map-pin",
                "marker",
            ),
        }
        type_suggestions = sorted({item.type for item in self._markers if item.type})

        # Создаем и показываем диалог редактирования.
        dialog = MapLabelEditDialog(
            marker,
            entity_sources,
            type_suggestions=type_suggestions,
            mode="edit",
            size_range=(self.MIN_MARKER_SIZE, self.MAX_MARKER_SIZE),
            parent=self,
        )

        # Пример использования результата: dialog.result_marker(), dialog.image_path(), dialog.parent_path().
        if dialog.exec() == QDialog.DialogCode.Accepted:
            updated = dialog.result_marker()
            self._set_marker(updated)
            if dialog.resize_requested():
                self._enable_resize_mode(updated.id)

    def edit_marker(self, marker: Marker) -> None:
        self._edit_marker(marker)

    @staticmethod
    def _load_marker_preview(marker: Marker, target: QSize) -> QPixmap | None:
        # Загружаем превью изображения маркера для карточки.
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

    def _view_marker(self, marker: Marker) -> None:
        # Показываем окно просмотра данных маркера.
        dialog = QDialog(self)
        dialog.setWindowTitle("Метка на карте")
        dialog.setObjectName("MapLabelViewDialog")
        dialog.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        dialog.resize(980, 680)
        dialog.setMinimumSize(760, 520)

        # Корневой layout диалога.
        root_layout = QVBoxLayout(dialog)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(10)

        # Заголовок с кнопками.
        header = QFrame()
        header.setObjectName("MapLabelHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 10, 12, 10)
        header_layout.setSpacing(12)

        title = QLabel("Метка на карте")
        title.setObjectName("MapLabelTitle")
        header_layout.addWidget(title)
        header_layout.addItem(
            QSpacerItem(
                20,
                0,
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Minimum,
            )
        )

        edit_btn = QPushButton("Редактировать")
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.clicked.connect(lambda _checked=False: (dialog.accept(), self._edit_marker(marker)))

        close_btn = QToolButton()
        close_btn.setObjectName("MapLabelClose")
        close_btn.setText("✕")
        close_btn.clicked.connect(dialog.reject)

        header_layout.addWidget(edit_btn)
        header_layout.addWidget(close_btn)

        # Основное тело диалога.
        body = QFrame()
        body.setObjectName("MapLabelBody")
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(14)

        left_panel = QFrame()
        left_panel.setObjectName("MapLabelCard")
        left_panel.setFixedWidth(300)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(12)

        preview_title = QLabel("Превью")
        preview_title.setObjectName("MapLabelSectionTitle")
        preview_label = QLabel("Нет изображения")
        preview_label.setObjectName("MapLabelPreview")
        preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_label.setFixedHeight(168)
        preview_size = QSize(left_panel.width() - 24, 168)
        preview_pixmap = self._load_marker_preview(marker, preview_size)
        if preview_pixmap is not None:
            preview_label.setPixmap(preview_pixmap)
            preview_label.setText("")
        elif marker.image_path:
            preview_label.setText("Изображение недоступно")
        if marker.image_path:
            preview_label.setToolTip(marker.image_path)

        marker_type_title = QLabel("Тип метки")
        marker_type_title.setObjectName("MapLabelSectionTitle")
        marker_type_preview = QLabel()
        marker_type_preview.setObjectName("MapLabelMarkerPreview")
        marker_type_preview.setFixedSize(28, 28)
        marker_type_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        marker_type_value = QLabel()
        marker_type_value.setObjectName("MapLabelValue")
        marker_type_value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        marker_type = marker_type_for_color(marker.color)
        marker_type_value.setText(marker_type.label)
        marker_type_icon_pixmap = marker_type_pixmap(marker_type, marker_type_preview.size())
        if marker_type_icon_pixmap is not None:
            marker_type_preview.setPixmap(marker_type_icon_pixmap)
            marker_type_preview.setText("")
        else:
            marker_type_preview.setPixmap(QPixmap())
            marker_type_preview.setText(marker_type.label)

        marker_type_row = QHBoxLayout()
        marker_type_row.addWidget(marker_type_preview)
        marker_type_row.addWidget(marker_type_value)
        marker_type_row.addStretch(1)

        coords_title = QLabel("Координаты")
        coords_title.setObjectName("MapLabelSectionTitle")
        coords_value = QLabel(f"{marker.x:.0f}, {marker.y:.0f}")
        coords_value.setObjectName("MapLabelValue")
        coords_value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        size_title = QLabel("Размер")
        size_title.setObjectName("MapLabelSectionTitle")
        size_value = QLabel(f"{marker.size:.1f}")
        size_value.setObjectName("MapLabelValue")
        size_value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        left_layout.addWidget(preview_title)
        left_layout.addWidget(preview_label)
        left_layout.addWidget(marker_type_title)
        left_layout.addLayout(marker_type_row)
        left_layout.addSpacing(6)
        left_layout.addWidget(coords_title)
        left_layout.addWidget(coords_value)
        left_layout.addSpacing(6)
        left_layout.addWidget(size_title)
        left_layout.addWidget(size_value)
        left_layout.addStretch(1)

        # Правая панель с подробностями и привязками.
        right_panel = QFrame()
        right_panel.setObjectName("MapLabelFormContainer")
        right_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(16)

        main_section = QFrame()
        main_section.setObjectName("MapLabelSection")
        main_layout = QVBoxLayout(main_section)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)
        main_title = QLabel("Основное")
        main_title.setObjectName("MapLabelSectionTitle")
        main_layout.addWidget(main_title)

        main_form = QFormLayout()
        main_form.setSpacing(10)
        main_form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        main_form.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        name_label = QLabel("Название")
        name_label.setObjectName("MapLabelFormLabel")
        name_value = QLabel(marker.name)
        name_value.setObjectName("MapLabelValue")
        name_value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        type_label = QLabel("Тип")
        type_label.setObjectName("MapLabelFormLabel")
        type_value = QLabel(marker.type or "—")
        type_value.setObjectName("MapLabelValue")
        type_value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        main_form.addRow(name_label, name_value)
        main_form.addRow(type_label, type_value)
        main_layout.addLayout(main_form)

        # Секция привязок.
        links_section = QFrame()
        links_section.setObjectName("MapLabelSection")
        links_layout = QVBoxLayout(links_section)
        links_layout.setContentsMargins(12, 12, 12, 12)
        links_layout.setSpacing(10)
        links_title = QLabel("Привязки")
        links_title.setObjectName("MapLabelSectionTitle")
        links_layout.addWidget(links_title)
        links_form = QFormLayout()
        links_form.setSpacing(10)
        links_form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        def handle_link(link: str) -> None:
            # Обрабатываем клики по ссылкам привязок.
            if ":" not in link:
                return
            kind, item_id = link.split(":", 1)
            try:
                parsed_id = int(item_id)
            except ValueError:
                return
            self._open_attachment_view(kind, parsed_id)

        def attachment_label(kind: str, item_ids: List[int], source: dict) -> QLabel:
            # Формируем HTML-ссылки для списка привязок.
            label = QLabel()
            label.setObjectName("MapLabelValue")
            label.setTextFormat(Qt.TextFormat.RichText)
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
            label.setOpenExternalLinks(False)
            label.setStyleSheet(
                "QLabel a {"
                "background-color: #f1f3f6;"
                "border-radius: 4px;"
                "padding: 1px 4px;"
                "}"
            )
            if not item_ids:
                label.setText("—")
                return label
            links = []
            for item_id in item_ids:
                item = source.get(item_id)
                if not item:
                    links.append("не найдено")
                    continue
                item_title = getattr(item, "title", None) or getattr(item, "name", None) or getattr(item, "rel_path", "—")
                links.append(f'<a style="background:#CCC;border-radius:4px;" href="{kind}:{item_id}">{item_title}</a>')
            label.setText("<br>".join(links))
            label.linkActivated.connect(handle_link)
            return label

        task_link = attachment_label("task", marker.task_ids, self._tasks_by_id)
        project_link = attachment_label("project", marker.project_ids, self._projects_by_id)
        note_link = attachment_label("note", marker.note_ids, self._notes_by_id)
        object_link = attachment_label("object", marker.object_ids, self._objects_by_id)
        file_link = attachment_label("file", marker.file_ids, self._files_by_id)
        map_link = attachment_label("map", marker.map_ids, self._maps_by_id)
        marker_link = attachment_label("marker", marker.marker_ids, self._marker_items_by_id)

        def add_link_row(label_text: str, widget: QLabel) -> None:
            # Утилита для добавления строки формы.
            label = QLabel(label_text)
            label.setObjectName("MapLabelFormLabel")
            links_form.addRow(label, widget)

        add_link_row("Задачи", task_link)
        add_link_row("Проекты", project_link)
        add_link_row("Заметки", note_link)
        add_link_row("Объекты", object_link)
        add_link_row("Файлы", file_link)
        add_link_row("Карты", map_link)
        add_link_row("Метки", marker_link)

        links_layout.addLayout(links_form)

        # Секция текстовых полей.
        text_section = QFrame()
        text_section.setObjectName("MapLabelSection")
        text_layout = QVBoxLayout(text_section)
        text_layout.setContentsMargins(12, 12, 12, 12)
        text_layout.setSpacing(10)
        text_title = QLabel("Текст заметок")
        text_title.setObjectName("MapLabelSectionTitle")
        text_layout.addWidget(text_title)

        desc_label = QLabel("Описание")
        desc_label.setObjectName("MapLabelFieldLabel")
        desc_value = QLabel(marker.description or "—")
        desc_value.setObjectName("MapLabelValue")
        desc_value.setWordWrap(True)
        desc_value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        props_wrap = QFrame()
        props_wrap.setObjectName("MapLabelImportant")
        props_layout = QVBoxLayout(props_wrap)
        props_layout.setContentsMargins(10, 8, 10, 8)
        props_layout.setSpacing(6)

        props_header = QHBoxLayout()
        props_icon = QLabel("⚑")
        props_icon.setObjectName("MapLabelImportantIcon")
        props_label = QLabel("Важные пометки")
        props_label.setObjectName("MapLabelFieldLabel")
        props_header.addWidget(props_icon)
        props_header.addWidget(props_label)
        props_header.addStretch(1)

        props_value = QLabel(_format_marker_properties_text(marker.properties))
        props_value.setObjectName("MapLabelValue")
        props_value.setWordWrap(True)
        props_value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        props_layout.addLayout(props_header)
        props_layout.addWidget(props_value)

        text_layout.addWidget(desc_label)
        text_layout.addWidget(desc_value)
        text_layout.addWidget(props_wrap)

        right_layout.addWidget(main_section)
        right_layout.addWidget(links_section)
        right_layout.addWidget(text_section)
        right_layout.addStretch(1)

        right_scroll = QScrollArea()
        right_scroll.setObjectName("MapLabelViewScroll")
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QFrame.Shape.NoFrame)
        right_scroll.setWidget(right_panel)

        body_layout.addWidget(left_panel, 0)
        body_layout.addWidget(right_scroll, 1)

        root_layout.addWidget(header)
        root_layout.addWidget(body, 1)

        # Стили диалога просмотра.
        dialog.setStyleSheet(
            f"""
            QDialog#MapLabelViewDialog {{
                {MATH_PHYS_BACKGROUND}
            }}
            QFrame#MapLabelHeader {{
                background: rgba(20, 22, 30, 0.92);
                border: 1px solid #2a2b2f;
                border-radius: 10px;
            }}
            QLabel#MapLabelTitle {{
                color: #f0f0f0;
                font-size: 16px;
                font-weight: 600;
            }}
            QFrame#MapLabelCard, QFrame#MapLabelSection {{
                background: rgba(22, 24, 32, 0.92);
                border: 1px solid #2a2b2f;
                border-radius: 10px;
            }}
            QFrame#MapLabelBody {{
                background: transparent;
            }}
            QLabel#MapLabelSectionTitle {{
                color: #d9d9d9;
                font-weight: 600;
            }}
            QLabel#MapLabelFieldLabel {{
                color: #b9bcc4;
            }}
            QLabel#MapLabelFormLabel {{
                color: #b9bcc4;
            }}
            QLabel#MapLabelValue {{
                color: #a8abb3;
            }}
            QLabel#MapLabelValue a {{
                color: #a8abb3;
            }}
            QLabel#MapLabelPreview {{
                border: 1px dashed #3a3b40;
                border-radius: 8px;
                color: #8e919a;
                background: #1b1d24;
            }}
            QScrollArea#MapLabelViewScroll {{
                background: transparent;
                border: none;
            }}
            QScrollArea#MapLabelViewScroll QWidget#qt_scrollarea_viewport {{
                background: transparent;
            }}
            QScrollArea#MapLabelViewScroll > QWidget {{
                background: transparent;
            }}
            QScrollArea#MapLabelViewScroll > QWidget > QWidget {{
                background: transparent;
            }}
            QToolButton, QPushButton {{
                background: #2a2b2f;
                color: #e6e6e6;
                border: 1px solid #3a3b40;
                padding: 6px 12px;
                border-radius: 6px;
            }}
            QToolButton:hover, QPushButton:hover {{
                background: #34363b;
            }}
            QToolButton#MapLabelClose {{
                padding: 4px 8px;
                min-width: 28px;
            }}
            QLabel#MapLabelMarkerPreview {{
                border: 1px solid #2a2b2f;
                border-radius: 6px;
            }}
            QFrame#MapLabelImportant {{
                border-left: 3px solid #d59d35;
                background: rgba(29, 31, 39, 0.85);
                border-radius: 8px;
            }}
            """
        )
        dialog.exec()

    def _open_context_menu(self, pos) -> None:
        # Контекстное меню для быстрых действий с маркером.
        world_pos = self._map_to_world(pos)
        marker = self._marker_at(world_pos)
        overlay = self._overlay_at(world_pos) if marker is None else None
        menu = QMenu(self)
        act_add = menu.addAction("Добавить маркер")
        act_view = menu.addAction("Просмотреть метку")
        type_menu = menu.addMenu("Тип маркера")
        type_actions = {}
        for option in marker_type_options():
            action = type_menu.addAction(marker_type_icon(option), option.label)
            type_actions[action] = option
        act_bigger = menu.addAction("Увеличить маркер")
        act_smaller = menu.addAction("Уменьшить маркер")
        act_resize = menu.addAction("Изменить размер")
        act_edit = menu.addAction("Редактировать маркер")
        act_delete = menu.addAction("Удалить маркер")
        menu.addSeparator()
        overlay_kind = "область" if overlay and overlay.kind == "region" else "путь"
        act_overlay_edit = menu.addAction(f"Редактировать {overlay_kind}")
        act_overlay_delete = menu.addAction(f"Удалить {overlay_kind}")
        act_view.setEnabled(marker is not None)
        type_menu.setEnabled(marker is not None)
        act_bigger.setEnabled(marker is not None)
        act_smaller.setEnabled(marker is not None)
        act_resize.setEnabled(marker is not None)
        act_edit.setEnabled(marker is not None)
        act_delete.setEnabled(marker is not None)
        act_overlay_edit.setEnabled(overlay is not None)
        act_overlay_delete.setEnabled(overlay is not None)
        chosen = menu.exec(QCursor.pos())
        if chosen == act_add:
            self._add_marker(world_pos)
        elif chosen == act_view and marker:
            self._view_marker(marker)
        elif chosen in type_actions and marker:
            option = type_actions[chosen]
            self._set_marker(
                Marker(
                    marker.id,
                    marker.name,
                    marker.x,
                    marker.y,
                    option.color,
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
        elif chosen == act_bigger and marker:
            self._adjust_marker_size(marker, 1.5)
        elif chosen == act_smaller and marker:
            self._adjust_marker_size(marker, -1.5)
        elif chosen == act_resize and marker:
            self._enable_resize_mode(marker.id)
        elif chosen == act_edit and marker:
            self._edit_marker(marker)
        elif chosen == act_delete and marker:
            self._remove_marker(marker)
        elif chosen == act_overlay_edit and overlay:
            self._edit_overlay(overlay)
        elif chosen == act_overlay_delete and overlay:
            confirm = QMessageBox.question(
                self,
                "Удаление геометрии",
                f"Удалить {overlay_kind}?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if confirm == QMessageBox.StandardButton.Yes:
                self._remove_overlay(overlay)

__all__ = ["MapCanvas"]
