
from __future__ import annotations
import math
from PySide6.QtCore import QRectF
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QGraphicsPixmapItem, QGraphicsScene

from .tiles_provider import TileProvider
from .pixmap_cache import PixmapLRUCache


class TileLayer:
    def __init__(self, scene: QGraphicsScene, provider: TileProvider, tiles_x: int, tiles_y: int, tile_size: int,
                 cache: PixmapLRUCache | None = None):
        self.scene = scene
        self.provider = provider
        self.tiles_x = tiles_x
        self.tiles_y = tiles_y
        self.tile_size = tile_size
        self.cache = cache or PixmapLRUCache()
        self._items: dict[tuple[int, int], QGraphicsPixmapItem] = {}

    def full_scene_rect(self) -> QRectF:
        return QRectF(0, 0, self.tiles_x * self.tile_size, self.tiles_y * self.tile_size)

    def update_visible(self, scene_rect: QRectF, margin_tiles: int = 1):
        ts = self.tile_size
        tx0 = math.floor(scene_rect.left() / ts) - margin_tiles
        ty0 = math.floor(scene_rect.top() / ts) - margin_tiles
        tx1 = math.floor(scene_rect.right() / ts) + margin_tiles
        ty1 = math.floor(scene_rect.bottom() / ts) + margin_tiles

        tx0 = max(0, min(self.tiles_x - 1, tx0))
        ty0 = max(0, min(self.tiles_y - 1, ty0))
        tx1 = max(0, min(self.tiles_x - 1, tx1))
        ty1 = max(0, min(self.tiles_y - 1, ty1))

        needed = {(tx, ty) for ty in range(ty0, ty1 + 1) for tx in range(tx0, tx1 + 1)}

        # remove
        for key in list(self._items.keys()):
            if key not in needed:
                it = self._items.pop(key)
                self.scene.removeItem(it)

        # add
        for key in needed:
            if key in self._items:
                continue
            tx, ty = key
            pm = self.cache.get(key)
            if pm is None:
                pm = self.provider.load_pixmap(tx, ty)
                if pm.isNull():
                    pm = QPixmap(ts, ts)
                    pm.fill()
                self.cache.put(key, pm)
            it = QGraphicsPixmapItem(pm)
            it.setPos(tx * ts, ty * ts)
            it.setZValue(0)
            self.scene.addItem(it)
            self._items[key] = it
