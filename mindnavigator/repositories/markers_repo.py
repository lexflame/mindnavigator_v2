
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from ..db import connect


@dataclass(frozen=True)
class MarkerDTO:
    id: int
    map_id: int
    title: str
    color: Optional[str]
    icon: Optional[str]
    x: float
    y: float
    note: str
    deleted: bool


class MarkersRepo:
    def __init__(self, db_path=None):
        self._db_path = db_path

    def list_markers(self, map_id: int, include_deleted: bool = False) -> List[MarkerDTO]:
        conn = connect(self._db_path)
        try:
            extra = "" if include_deleted else "AND deleted_at IS NULL"
            rows = conn.execute(
                f"SELECT id, map_id, title, color, icon, x, y, note, deleted_at FROM map_markers "
                f"WHERE map_id=? {extra} ORDER BY updated_at DESC, id DESC",
                (map_id,),
            ).fetchall()
            out: List[MarkerDTO] = []
            for r in rows:
                out.append(
                    MarkerDTO(
                        id=int(r["id"]),
                        map_id=int(r["map_id"]),
                        title=str(r["title"]),
                        color=(str(r["color"]) if r["color"] is not None else None),
                        icon=(str(r["icon"]) if r["icon"] is not None else None),
                        x=float(r["x"]),
                        y=float(r["y"]),
                        note=str(r["note"] or ""),
                        deleted=(r["deleted_at"] is not None),
                    )
                )
            return out
        finally:
            conn.close()

    def get_marker(self, marker_id: int) -> Optional[MarkerDTO]:
        conn = connect(self._db_path)
        try:
            r = conn.execute(
                "SELECT id, map_id, title, color, icon, x, y, note, deleted_at FROM map_markers WHERE id=?",
                (marker_id,),
            ).fetchone()
            if not r:
                return None
            return MarkerDTO(
                id=int(r["id"]),
                map_id=int(r["map_id"]),
                title=str(r["title"]),
                color=(str(r["color"]) if r["color"] is not None else None),
                icon=(str(r["icon"]) if r["icon"] is not None else None),
                x=float(r["x"]),
                y=float(r["y"]),
                note=str(r["note"] or ""),
                deleted=(r["deleted_at"] is not None),
            )
        finally:
            conn.close()

    def create_marker(self, map_id: int, title: str, x: float, y: float, color: Optional[str]=None,
                      icon: Optional[str]=None, note: str="") -> int:
        conn = connect(self._db_path)
        try:
            cur = conn.execute(
                "INSERT INTO map_markers(map_id, title, color, icon, x, y, note, updated_at, created_at, deleted_at) "
                "VALUES(?,?,?,?,?,?,?, datetime('now'), datetime('now'), NULL)",
                (map_id, title, color, icon, x, y, note),
            )
            conn.commit()
            return int(cur.lastrowid)
        finally:
            conn.close()

    def update_marker(self, marker_id: int, title: str, x: float, y: float, color: Optional[str],
                      icon: Optional[str], note: str) -> None:
        conn = connect(self._db_path)
        try:
            conn.execute(
                "UPDATE map_markers SET title=?, color=?, icon=?, x=?, y=?, note=?, updated_at=datetime('now') "
                "WHERE id=? AND deleted_at IS NULL",
                (title, color, icon, x, y, note, marker_id),
            )
            conn.commit()
        finally:
            conn.close()

    def soft_delete_marker(self, marker_id: int) -> None:
        conn = connect(self._db_path)
        try:
            conn.execute(
                "UPDATE map_markers SET deleted_at=datetime('now'), updated_at=datetime('now') "
                "WHERE id=? AND deleted_at IS NULL",
                (marker_id,),
            )
            conn.commit()
        finally:
            conn.close()

    # links
    def get_linked_task_ids(self, marker_id: int) -> List[int]:
        conn = connect(self._db_path)
        try:
            rows = conn.execute(
                "SELECT task_id FROM marker_tasks WHERE marker_id=? ORDER BY task_id",
                (marker_id,),
            ).fetchall()
            return [int(r["task_id"]) for r in rows]
        finally:
            conn.close()

    def set_marker_tasks(self, marker_id: int, task_ids: List[int]) -> None:
        conn = connect(self._db_path)
        try:
            conn.execute("DELETE FROM marker_tasks WHERE marker_id=?", (marker_id,))
            for tid in task_ids:
                conn.execute(
                    "INSERT OR IGNORE INTO marker_tasks(marker_id, task_id, created_at) VALUES(?,?, datetime('now'))",
                    (marker_id, int(tid)),
                )
            conn.commit()
        finally:
            conn.close()

    def get_linked_project_ids(self, marker_id: int) -> List[int]:
        conn = connect(self._db_path)
        try:
            rows = conn.execute(
                "SELECT project_id FROM marker_projects WHERE marker_id=? ORDER BY project_id",
                (marker_id,),
            ).fetchall()
            return [int(r["project_id"]) for r in rows]
        finally:
            conn.close()

    def set_marker_projects(self, marker_id: int, project_ids: List[int]) -> None:
        conn = connect(self._db_path)
        try:
            conn.execute("DELETE FROM marker_projects WHERE marker_id=?", (marker_id,))
            for pid in project_ids:
                conn.execute(
                    "INSERT OR IGNORE INTO marker_projects(marker_id, project_id, created_at) VALUES(?,?, datetime('now'))",
                    (marker_id, int(pid)),
                )
            conn.commit()
        finally:
            conn.close()
