
from __future__ import annotations
from collections import OrderedDict
from PySide6.QtGui import QPixmap


class PixmapLRUCache:
    def __init__(self, max_items: int = 400):
        self.max_items = max_items
        self._d: OrderedDict[tuple[int, int], QPixmap] = OrderedDict()

    def get(self, key: tuple[int, int]) -> QPixmap | None:
        pm = self._d.get(key)
        if pm is None:
            return None
        self._d.move_to_end(key)
        return pm

    def put(self, key: tuple[int, int], pm: QPixmap) -> None:
        self._d[key] = pm
        self._d.move_to_end(key)
        while len(self._d) > self.max_items:
            self._d.popitem(last=False)
