from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from ..db import connect


@dataclass(frozen=True)
class ProjectDTO:
    id: int
    area: str
    title: str
    priority: str
    archived: bool
    updated_at: str


class ProjectsRepo:
    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path

    def list_projects(self) -> List[ProjectDTO]:
        conn = connect(self._db_path)
        try:
            rows = conn.execute(
                "SELECT id, area, title, priority, archived, updated_at "
                "FROM projects ORDER BY lower(area), lower(title), id"
            ).fetchall()
            return [
                ProjectDTO(
                    id=int(r["id"]),
                    area=str(r["area"]),
                    title=str(r["title"]),
                    priority=str(r["priority"]),
                    archived=bool(r["archived"]),
                    updated_at=str(r["updated_at"]),
                )
                for r in rows
            ]
        finally:
            conn.close()

    def toggle_archived(self, project_id: int) -> None:
        conn = connect(self._db_path)
        try:
            conn.execute(
                "UPDATE projects SET archived = CASE archived WHEN 0 THEN 1 ELSE 0 END, "
                "updated_at=datetime('now') WHERE id=?",
                (project_id,),
            )
            conn.commit()
        finally:
            conn.close()

    def list_areas(self) -> List[str]:
        conn = connect(self._db_path)
        try:
            rows = conn.execute("SELECT DISTINCT area FROM projects ORDER BY lower(area)").fetchall()
            return [str(r["area"]) for r in rows]
        finally:
            conn.close()
