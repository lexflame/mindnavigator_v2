
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from ..db import connect


@dataclass(frozen=True)
class MapDTO:
    id: int
    title: str
    tiles_path: str
    tiles_x: int
    tiles_y: int
    tile_size: int
    deleted: bool


class MapsRepo:
    def __init__(self, db_path=None):
        self._db_path = db_path

    def list_maps(self, include_deleted: bool = False, text: Optional[str] = None) -> List[MapDTO]:
        conn = connect(self._db_path)
        try:
            where = []
            params: list = []
            if not include_deleted:
                where.append("deleted_at IS NULL")
            if text:
                where.append("title LIKE ?")
                params.append(f"%{text}%")
            where_sql = ("WHERE " + " AND ".join(where)) if where else ""
            rows = conn.execute(
                f"SELECT id, title, tiles_path, tiles_x, tiles_y, tile_size, deleted_at FROM maps {where_sql} "
                "ORDER BY updated_at DESC, id DESC",
                params,
            ).fetchall()
            out: List[MapDTO] = []
            for r in rows:
                out.append(
                    MapDTO(
                        id=int(r["id"]),
                        title=str(r["title"]),
                        tiles_path=str(r["tiles_path"]),
                        tiles_x=int(r["tiles_x"]),
                        tiles_y=int(r["tiles_y"]),
                        tile_size=int(r["tile_size"]),
                        deleted=(r["deleted_at"] is not None),
                    )
                )
            return out
        finally:
            conn.close()

    def get_map(self, map_id: int, include_deleted: bool = False) -> Optional[MapDTO]:
        conn = connect(self._db_path)
        try:
            extra = "" if include_deleted else "AND deleted_at IS NULL"
            r = conn.execute(
                f"SELECT id, title, tiles_path, tiles_x, tiles_y, tile_size, deleted_at FROM maps "
                f"WHERE id=? {extra}",
                (map_id,),
            ).fetchone()
            if not r:
                return None
            return MapDTO(
                id=int(r["id"]),
                title=str(r["title"]),
                tiles_path=str(r["tiles_path"]),
                tiles_x=int(r["tiles_x"]),
                tiles_y=int(r["tiles_y"]),
                tile_size=int(r["tile_size"]),
                deleted=(r["deleted_at"] is not None),
            )
        finally:
            conn.close()

    def create_map(self, title: str, tiles_path: str, tiles_x: int, tiles_y: int, tile_size: int = 512) -> int:
        conn = connect(self._db_path)
        try:
            cur = conn.execute(
                "INSERT INTO maps(title, tiles_path, tiles_x, tiles_y, tile_size, updated_at, created_at, deleted_at) "
                "VALUES(?,?,?,?,?, datetime('now'), datetime('now'), NULL)",
                (title, tiles_path, tiles_x, tiles_y, tile_size),
            )
            conn.commit()
            return int(cur.lastrowid)
        finally:
            conn.close()

    def update_map(self, map_id: int, title: str, tiles_path: str, tiles_x: int, tiles_y: int, tile_size: int) -> None:
        conn = connect(self._db_path)
        try:
            conn.execute(
                "UPDATE maps SET title=?, tiles_path=?, tiles_x=?, tiles_y=?, tile_size=?, updated_at=datetime('now') "
                "WHERE id=? AND deleted_at IS NULL",
                (title, tiles_path, tiles_x, tiles_y, tile_size, map_id),
            )
            conn.commit()
        finally:
            conn.close()

    def soft_delete_map(self, map_id: int) -> None:
        conn = connect(self._db_path)
        try:
            conn.execute(
                "UPDATE maps SET deleted_at=datetime('now'), updated_at=datetime('now') WHERE id=? AND deleted_at IS NULL",
                (map_id,),
            )
            conn.commit()
        finally:
            conn.close()
