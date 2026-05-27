"""Project custom properties storage mixin."""

from __future__ import annotations

import re

from ._shared import *  # noqa: F401,F403
from .project_property_data import (
    ProjectLinkData,
    ProjectRelatedProjectData,
    ProjectRelatedTaskData,
    ProjectTaskTypeData,
)

PROJECT_TASK_TYPE_DEACTIVATED_REASON = "project_task_type_deactivated"
_SPACE_RE = re.compile(r"\s+")


def normalize_project_task_type_title(title: str) -> str:
    normalized = _SPACE_RE.sub(" ", (title or "").strip()).upper()
    if not normalized:
        raise ValueError("Название типа задачи не должно быть пустым.")
    return normalized


class DatabaseProjectPropertiesMixin:
    def fetch_project_task_types(self, project_id: int, include_inactive: bool = True) -> list[ProjectTaskTypeData]:
        sql = """
            SELECT id, project_id, title, color_marker, theme_marker, active, sort_order, created_at, updated_at
            FROM project_task_types
            WHERE project_id = ?
        """
        params: list[object] = [int(project_id)]
        if not include_inactive:
            sql += " AND active = 1"
        sql += " ORDER BY sort_order, title, id;"
        rows = self._conn.execute(sql, params).fetchall()
        return [
            ProjectTaskTypeData(
                id=int(row["id"]),
                project_id=int(row["project_id"]),
                title=(row["title"] or "").strip(),
                color_marker=(row["color_marker"] or "").strip(),
                theme_marker=(row["theme_marker"] or "").strip(),
                active=bool(row["active"]),
                sort_order=max(0, int(row["sort_order"] or 0)),
                created_at=(row["created_at"] or "").strip(),
                updated_at=(row["updated_at"] or "").strip(),
            )
            for row in rows
        ]

    def fetch_project_task_type(self, task_type_id: int) -> Optional[ProjectTaskTypeData]:
        row = self._conn.execute(
            """
            SELECT id, project_id, title, color_marker, theme_marker, active, sort_order, created_at, updated_at
            FROM project_task_types
            WHERE id = ?;
            """,
            (int(task_type_id),),
        ).fetchone()
        if row is None:
            return None
        return ProjectTaskTypeData(
            id=int(row["id"]),
            project_id=int(row["project_id"]),
            title=(row["title"] or "").strip(),
            color_marker=(row["color_marker"] or "").strip(),
            theme_marker=(row["theme_marker"] or "").strip(),
            active=bool(row["active"]),
            sort_order=max(0, int(row["sort_order"] or 0)),
            created_at=(row["created_at"] or "").strip(),
            updated_at=(row["updated_at"] or "").strip(),
        )

    def add_project_task_type(
        self,
        project_id: int,
        title: str,
        color_marker: str = "",
        theme_marker: str = "",
        active: bool = True,
    ) -> ProjectTaskTypeData:
        project_id = int(project_id)
        title = normalize_project_task_type_title(title)
        self._ensure_unique_project_task_type_title(project_id, title)
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        sort_order = self._next_project_property_sort_order("project_task_types", project_id)
        with self._conn:
            cur = self._conn.execute(
                """
                INSERT INTO project_task_types (
                    project_id, title, color_marker, theme_marker, active, sort_order, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    project_id,
                    title,
                    (color_marker or "").strip(),
                    (theme_marker or "").strip().lower(),
                    int(bool(active)),
                    sort_order,
                    now,
                    now,
                ),
            )
        created = self.fetch_project_task_type(int(cur.lastrowid))
        if created is None:
            raise ValueError("Не удалось создать тип задач проекта.")
        return created

    def update_project_task_type(
        self,
        task_type_id: int,
        title: str,
        color_marker: str = "",
        theme_marker: str = "",
        active: bool = True,
    ) -> ProjectTaskTypeData:
        existing = self.fetch_project_task_type(int(task_type_id))
        if existing is None:
            raise ValueError("Тип задач проекта не найден.")
        title = normalize_project_task_type_title(title)
        self._ensure_unique_project_task_type_title(existing.project_id, title, exclude_id=existing.id)
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                """
                UPDATE project_task_types
                SET title = ?, color_marker = ?, theme_marker = ?, active = ?, updated_at = ?
                WHERE id = ?;
                """,
                (
                    title,
                    (color_marker or "").strip(),
                    (theme_marker or "").strip().lower(),
                    int(bool(active)),
                    now,
                    existing.id,
                ),
            )
        if bool(active) != existing.active:
            self.set_project_task_type_active(existing.id, bool(active))
        updated = self.fetch_project_task_type(existing.id)
        if updated is None:
            raise ValueError("Тип задач проекта не найден.")
        return updated

    def set_project_task_type_active(self, task_type_id: int, active: bool) -> None:
        task_type = self.fetch_project_task_type(int(task_type_id))
        if task_type is None:
            raise ValueError("Тип задач проекта не найден.")
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                "UPDATE project_task_types SET active = ?, updated_at = ? WHERE id = ?;",
                (int(bool(active)), now, task_type.id),
            )
            if active:
                self._conn.execute(
                    """
                    UPDATE tasks
                    SET postponed_reason = '',
                        postponed_by_project_task_type_id = NULL,
                        board_column = ?,
                        priority = CASE WHEN priority = ? THEN 'Medium' ELSE priority END,
                        updated_at = ?
                    WHERE project_task_type_id = ?
                      AND postponed_reason = ?
                      AND postponed_by_project_task_type_id = ?;
                    """,
                    (
                        BOARD_COLUMN_QUEUE,
                        DEFERRED_PRIORITY,
                        now,
                        task_type.id,
                        PROJECT_TASK_TYPE_DEACTIVATED_REASON,
                        task_type.id,
                    ),
                )
            else:
                self._conn.execute(
                    """
                    UPDATE tasks
                    SET priority = ?,
                        board_column = ?,
                        postponed_reason = ?,
                        postponed_by_project_task_type_id = ?,
                        updated_at = ?
                    WHERE project_task_type_id = ?;
                    """,
                    (
                        DEFERRED_PRIORITY,
                        BOARD_COLUMN_DEFERRED,
                        PROJECT_TASK_TYPE_DEACTIVATED_REASON,
                        task_type.id,
                        now,
                        task_type.id,
                    ),
                )

    def delete_project_task_type(self, task_type_id: int) -> None:
        task_type_id = int(task_type_id)
        if self.project_task_type_in_use(task_type_id):
            raise ValueError("Тип используется задачами. Деактивируйте тип вместо удаления.")
        with self._conn:
            self._conn.execute("DELETE FROM project_task_types WHERE id = ?;", (task_type_id,))

    def project_task_type_in_use(self, task_type_id: int) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM tasks WHERE project_task_type_id = ? LIMIT 1;",
            (int(task_type_id),),
        ).fetchone()
        return row is not None

    def replace_project_task_types(self, project_id: int, task_types: list[dict[str, object]]) -> None:
        project_id = int(project_id)
        existing = {item.title: item for item in self.fetch_project_task_types(project_id, include_inactive=True)}
        seen_titles: set[str] = set()
        for sort_order, item in enumerate(task_types):
            title = normalize_project_task_type_title(str(item.get("title") or ""))
            if title in seen_titles:
                raise ValueError(f"Дублирующий тип задач: {title}")
            seen_titles.add(title)
            active = bool(item.get("active", True))
            color_marker = str(item.get("color_marker") or "").strip()
            theme_marker = str(item.get("theme_marker") or "").strip().lower()
            current = existing.get(title)
            if current is None:
                current = self.add_project_task_type(project_id, title, color_marker, theme_marker, active)
            else:
                self.update_project_task_type(current.id, title, color_marker, theme_marker, active)
            with self._conn:
                self._conn.execute(
                    "UPDATE project_task_types SET sort_order = ? WHERE id = ?;",
                    (sort_order, current.id),
                )
        for title, current in existing.items():
            if title not in seen_titles and not self.project_task_type_in_use(current.id):
                self.delete_project_task_type(current.id)

    def fetch_project_related_projects(self, project_id: int) -> list[ProjectRelatedProjectData]:
        rows = self._conn.execute(
            """
            SELECT r.id, r.project_id, r.related_project_id, r.sort_order, r.created_at,
                   p.title, p.area, p.archived
            FROM project_related_projects r
            JOIN projects p ON p.id = r.related_project_id
            WHERE r.project_id = ?
            ORDER BY r.sort_order, p.area, p.title, r.id;
            """,
            (int(project_id),),
        ).fetchall()
        return [
            ProjectRelatedProjectData(
                id=int(row["id"]),
                project_id=int(row["project_id"]),
                related_project_id=int(row["related_project_id"]),
                title=(row["title"] or "").strip(),
                area=(row["area"] or "").strip(),
                archived=bool(row["archived"]),
                sort_order=max(0, int(row["sort_order"] or 0)),
                created_at=(row["created_at"] or "").strip(),
            )
            for row in rows
        ]

    def replace_project_related_projects(self, project_id: int, related_project_ids: list[int]) -> None:
        project_id = int(project_id)
        unique_ids = self._unique_existing_ids("projects", related_project_ids)
        if project_id in unique_ids:
            raise ValueError("Проект нельзя связать с самим собой.")
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute("DELETE FROM project_related_projects WHERE project_id = ?;", (project_id,))
            for sort_order, related_id in enumerate(unique_ids):
                self._conn.execute(
                    """
                    INSERT OR IGNORE INTO project_related_projects (
                        project_id, related_project_id, sort_order, created_at
                    )
                    VALUES (?, ?, ?, ?);
                    """,
                    (project_id, related_id, sort_order, now),
                )

    def fetch_project_related_tasks(self, project_id: int) -> list[ProjectRelatedTaskData]:
        rows = self._conn.execute(
            """
            SELECT r.id, r.project_id, r.task_id, r.sort_order, r.created_at,
                   t.title, t.priority, t.done
            FROM project_related_tasks r
            JOIN tasks t ON t.id = r.task_id
            WHERE r.project_id = ?
            ORDER BY r.sort_order, t.id;
            """,
            (int(project_id),),
        ).fetchall()
        return [
            ProjectRelatedTaskData(
                id=int(row["id"]),
                project_id=int(row["project_id"]),
                task_id=int(row["task_id"]),
                title=(row["title"] or "").strip(),
                priority=(row["priority"] or "").strip(),
                done=bool(row["done"]),
                sort_order=max(0, int(row["sort_order"] or 0)),
                created_at=(row["created_at"] or "").strip(),
            )
            for row in rows
        ]

    def replace_project_related_tasks(self, project_id: int, task_ids: list[int]) -> None:
        project_id = int(project_id)
        unique_ids = self._unique_existing_ids("tasks", task_ids)
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute("DELETE FROM project_related_tasks WHERE project_id = ?;", (project_id,))
            for sort_order, task_id in enumerate(unique_ids):
                self._conn.execute(
                    """
                    INSERT OR IGNORE INTO project_related_tasks (project_id, task_id, sort_order, created_at)
                    VALUES (?, ?, ?, ?);
                    """,
                    (project_id, task_id, sort_order, now),
                )

    def fetch_project_repository_links(self, project_id: int) -> list[ProjectLinkData]:
        return self._fetch_project_links("project_repository_links", project_id)

    def replace_project_repository_links(self, project_id: int, links: list[dict[str, str]]) -> None:
        self._replace_project_links("project_repository_links", int(project_id), links)

    def fetch_project_wiki_links(self, project_id: int) -> list[ProjectLinkData]:
        return self._fetch_project_links("project_wiki_links", project_id)

    def replace_project_wiki_links(self, project_id: int, links: list[dict[str, str]]) -> None:
        self._replace_project_links("project_wiki_links", int(project_id), links)

    def _fetch_project_links(self, table_name: str, project_id: int) -> list[ProjectLinkData]:
        rows = self._conn.execute(
            f"""
            SELECT id, project_id, title, url, sort_order, created_at, updated_at
            FROM {table_name}
            WHERE project_id = ?
            ORDER BY sort_order, title, id;
            """,
            (int(project_id),),
        ).fetchall()
        return [
            ProjectLinkData(
                id=int(row["id"]),
                project_id=int(row["project_id"]),
                title=(row["title"] or "").strip(),
                url=(row["url"] or "").strip(),
                sort_order=max(0, int(row["sort_order"] or 0)),
                created_at=(row["created_at"] or "").strip(),
                updated_at=(row["updated_at"] or "").strip(),
            )
            for row in rows
        ]

    def _replace_project_links(self, table_name: str, project_id: int, links: list[dict[str, str]]) -> None:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(f"DELETE FROM {table_name} WHERE project_id = ?;", (project_id,))
            seen_urls: set[str] = set()
            for sort_order, item in enumerate(links):
                url = str(item.get("url") or "").strip()
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                title = str(item.get("title") or "").strip()
                self._conn.execute(
                    f"""
                    INSERT INTO {table_name} (project_id, title, url, sort_order, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?);
                    """,
                    (project_id, title, url, sort_order, now, now),
                )

    def _ensure_unique_project_task_type_title(
        self,
        project_id: int,
        title: str,
        exclude_id: Optional[int] = None,
    ) -> None:
        params: list[object] = [int(project_id), title]
        sql = "SELECT id FROM project_task_types WHERE project_id = ? AND title = ?"
        if exclude_id is not None:
            sql += " AND id <> ?"
            params.append(int(exclude_id))
        sql += " LIMIT 1;"
        if self._conn.execute(sql, params).fetchone() is not None:
            raise ValueError(f"Тип задач уже существует: {title}")

    def _next_project_property_sort_order(self, table_name: str, project_id: int) -> int:
        row = self._conn.execute(
            f"SELECT COALESCE(MAX(sort_order), -1) AS max_order FROM {table_name} WHERE project_id = ?;",
            (int(project_id),),
        ).fetchone()
        return int(row["max_order"] or -1) + 1 if row is not None else 0

    def _unique_existing_ids(self, table_name: str, ids: list[int]) -> list[int]:
        result: list[int] = []
        seen: set[int] = set()
        for raw_id in ids:
            try:
                item_id = int(raw_id)
            except (TypeError, ValueError):
                continue
            if item_id in seen:
                continue
            if self._conn.execute(f"SELECT 1 FROM {table_name} WHERE id = ?;", (item_id,)).fetchone() is None:
                continue
            seen.add(item_id)
            result.append(item_id)
        return result


__all__ = [
    "DatabaseProjectPropertiesMixin",
    "PROJECT_TASK_TYPE_DEACTIVATED_REASON",
    "normalize_project_task_type_title",
]
