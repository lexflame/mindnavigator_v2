from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from datetime import date

from ..db import connect


@dataclass(frozen=True)
class TaskDTO:
    id: int
    project_id: Optional[int]
    day: str
    time_text: str
    title: str
    priority: str
    done: bool


class TasksRepo:
    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path

    def list_tasks(self) -> List[TaskDTO]:
        conn = connect(self._db_path)
        try:
            rows = conn.execute(
                "SELECT id, project_id, day, time_text, title, priority, done "
                "FROM tasks ORDER BY day, time_text, id"
            ).fetchall()
            out: List[TaskDTO] = []
            for r in rows:
                out.append(
                    TaskDTO(
                        id=int(r["id"]),
                        project_id=(int(r["project_id"]) if r["project_id"] is not None else None),
                        day=str(r["day"]),
                        time_text=str(r["time_text"]),
                        title=str(r["title"]),
                        priority=str(r["priority"]),
                        done=bool(r["done"]),
                    )
                )
            return out
        finally:
            conn.close()

    def toggle_done(self, task_id: int) -> None:
        conn = connect(self._db_path)
        try:
            conn.execute(
                "UPDATE tasks SET done = CASE done WHEN 0 THEN 1 ELSE 0 END, "
                "updated_at=datetime('now') WHERE id=?",
                (task_id,),
            )
            conn.commit()
        finally:
            conn.close()

    def list_tasks_range(
        self,
        day_from: date,
        day_to: date,
        *,
        include_done: bool = False,
        project_id: Optional[int] = None,
    ) -> List[TaskDTO]:
        """List tasks in inclusive date range [day_from..day_to].

        Used by "План" view (day switcher).
        """
        conn = connect(self._db_path)
        try:
            clauses = ["day >= ?", "day <= ?"]
            params: list = [day_from.isoformat(), day_to.isoformat()]

            if not include_done:
                clauses.append("done = 0")
            if project_id is not None:
                clauses.append("project_id = ?")
                params.append(int(project_id))

            where = " AND ".join(clauses)
            rows = conn.execute(
                "SELECT id, project_id, day, time_text, title, priority, done "
                f"FROM tasks WHERE {where} "
                "ORDER BY day, time_text, id",
                params,
            ).fetchall()

            out: List[TaskDTO] = []
            for r in rows:
                out.append(
                    TaskDTO(
                        id=int(r["id"]),
                        project_id=(int(r["project_id"]) if r["project_id"] is not None else None),
                        day=str(r["day"]),
                        time_text=str(r["time_text"]),
                        title=str(r["title"]),
                        priority=str(r["priority"]),
                        done=bool(r["done"]),
                    )
                )
            return out
        finally:
            conn.close()
