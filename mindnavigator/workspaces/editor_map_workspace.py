from __future__ import annotations

from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QGraphicsScene
from PySide6.QtCore import Qt

from ..maps.map_view import MapGraphicsView
from ..maps.tiles_provider import TileProvider
from ..maps.pixmap_cache import PixmapLRUCache
from ..maps.tile_layer import TileLayer
from ..maps.marker_item import MarkerItem
from ..repositories.markers_repo import MarkersRepo
from ..repositories.tasks_repo import TasksRepo
from ..repositories.projects_repo import ProjectsRepo
from ..ui.dialogs.marker_dialog import MarkerDialog


class EditorMapWorkspace(QWidget):
    def __init__(self, db_path=None, parent=None):
        super().__init__(parent)
        self._db_path = db_path
        self._map_id: int | None = None

        self.markers_repo = MarkersRepo(db_path)
        self.tasks_repo = TasksRepo(db_path)
        self.projects_repo = ProjectsRepo(db_path)

        self.scene = QGraphicsScene(self)
        self.view = MapGraphicsView()
        self.view.setScene(self.scene)

        self.lbl = QLabel("x=0 y=0")
        self.btn_back = QPushButton("← Назад к списку")
        self.btn_add = QPushButton("Новая метка (центр)")
        self.btn_edit = QPushButton("Редактировать выбранную")
        self.btn_del = QPushButton("Удалить выбранную")

        right = QVBoxLayout()
        right.addWidget(self.btn_back)
        right.addWidget(self.btn_add)
        right.addWidget(self.btn_edit)
        right.addWidget(self.btn_del)
        right.addStretch(1)
        right.addWidget(self.lbl)

        lay = QHBoxLayout(self)
        lay.addWidget(self.view, 1)
        lay.addLayout(right)

        self._tile_layer: TileLayer | None = None
        self._markers: dict[int, MarkerItem] = {}

        self.view.mouseSceneMoved.connect(self._on_mouse)
        self.view.clickedScene.connect(self._on_click)
        self.view.viewChanged.connect(self._update_tiles)

        self.btn_add.clicked.connect(self._add_marker_center)
        self.btn_edit.clicked.connect(self._edit_selected)
        self.btn_del.clicked.connect(self._delete_selected)

    def open_map(self, map_id: int, tiles_path: str, tiles_x: int, tiles_y: int, tile_size: int):
        self._map_id = map_id
        self.scene.clear()
        self._markers.clear()

        provider = TileProvider(tiles_path, ext="png")
        cache = PixmapLRUCache(max_items=600)
        self._tile_layer = TileLayer(self.scene, provider, tiles_x, tiles_y, tile_size, cache)
        self.scene.setSceneRect(self._tile_layer.full_scene_rect())

        self._load_markers()
        self._update_tiles()

    def _load_markers(self):
        if self._map_id is None:
            return
        for m in self.markers_repo.list_markers(self._map_id):
            it = MarkerItem(m.id, m.title, m.x, m.y, m.color)
            self.scene.addItem(it)
            self._markers[m.id] = it

    def _update_tiles(self):
        if not self._tile_layer:
            return
        vr = self.view.viewport().rect()
        scene_rect = self.view.mapToScene(vr).boundingRect()
        self._tile_layer.update_visible(scene_rect, margin_tiles=1)

    def _on_mouse(self, x: float, y: float):
        self.lbl.setText(f"x={x:.2f}  y={y:.2f}")

    def _on_click(self, x: float, y: float):
        # Shift+Click create quick marker
        mods = self.view.window().windowHandle().keyboardModifiers() if self.view.window().windowHandle() else Qt.NoModifier
        if mods & Qt.ShiftModifier:
            self._create_marker_at(x, y)

    def _add_marker_center(self):
        c = self.view.viewport().rect().center()
        p = self.view.mapToScene(c)
        self._create_marker_at(float(p.x()), float(p.y()))

    def _create_marker_at(self, x: float, y: float):
        if self._map_id is None:
            return
        tasks = self.tasks_repo.list_tasks()
        projects = self.projects_repo.list_projects()

        dlg = MarkerDialog(
            self,
            initial={"title": "Новая метка", "x": x, "y": y, "note": ""},
            tasks_rows=[{"id": t.id, "title": t.title} for t in tasks],
            projects_rows=[{"id": p.id, "title": p.title} for p in projects],
            selected_task_ids=[],
            selected_project_ids=[],
        )
        if dlg.exec() != dlg.Accepted:
            return
        data = dlg.get_data()
        mid = self.markers_repo.create_marker(
            self._map_id, data["title"], data["x"], data["y"], data["color"], data["icon"], data["note"]
        )
        self.markers_repo.set_marker_tasks(mid, data["task_ids"])
        self.markers_repo.set_marker_projects(mid, data["project_ids"])
        it = MarkerItem(mid, data["title"], data["x"], data["y"], data["color"])
        self.scene.addItem(it)
        self._markers[mid] = it

    def _selected_marker_id(self) -> int | None:
        for it in self.scene.selectedItems():
            if hasattr(it, "marker_id"):
                return int(it.marker_id)
        return None

    def _edit_selected(self):
        mid = self._selected_marker_id()
        if mid is None:
            return
        m = self.markers_repo.get_marker(mid)
        if not m:
            return
        tasks = self.tasks_repo.list_tasks()
        projects = self.projects_repo.list_projects()
        dlg = MarkerDialog(
            self,
            initial={"title": m.title, "x": m.x, "y": m.y, "note": m.note, "color": m.color, "icon": m.icon},
            tasks_rows=[{"id": t.id, "title": t.title} for t in tasks],
            projects_rows=[{"id": p.id, "title": p.title} for p in projects],
            selected_task_ids=self.markers_repo.get_linked_task_ids(mid),
            selected_project_ids=self.markers_repo.get_linked_project_ids(mid),
        )
        if dlg.exec() != dlg.Accepted:
            return
        data = dlg.get_data()
        self.markers_repo.update_marker(mid, data["title"], data["x"], data["y"], data["color"], data["icon"], data["note"])
        self.markers_repo.set_marker_tasks(mid, data["task_ids"])
        self.markers_repo.set_marker_projects(mid, data["project_ids"])
        it = self._markers.get(mid)
        if it:
            it.title = data["title"]
            it.setPos(data["x"], data["y"])
            it.update()

    def _delete_selected(self):
        mid = self._selected_marker_id()
        if mid is None:
            return
        self.markers_repo.soft_delete_marker(mid)
        it = self._markers.pop(mid, None)
        if it:
            self.scene.removeItem(it)
