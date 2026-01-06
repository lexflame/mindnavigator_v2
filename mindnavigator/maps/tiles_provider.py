
from __future__ import annotations
import os
from PySide6.QtGui import QPixmap


class TileProvider:
    def __init__(self, tiles_path: str, ext: str = "png"):
        self.tiles_path = tiles_path
        self.ext = ext

    def tile_filepath(self, tx: int, ty: int) -> str:
        return os.path.join(self.tiles_path, f"{tx}_{ty}.{self.ext}")

    def load_pixmap(self, tx: int, ty: int) -> QPixmap:
        return QPixmap(self.tile_filepath(tx, ty))
