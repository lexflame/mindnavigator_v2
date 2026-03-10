"""DatabaseProjectsMixin for storage database operations."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403

class DatabaseProjectsMixin:
    def fetch_projects(self) -> List[ProjectData]:
        """Р’РѕР·РІСЂР°С‰Р°РµС‚ СЃРїРёСЃРѕРє РїСЂРѕРµРєС‚РѕРІ."""
        rows = self._conn.execute(
            """
            SELECT
                id, area, title, updated, priority, archived,
                parent_project_id, default_task_priority, force_recurrence_kind,
                linked_map_id, linked_note_id, linked_object_id,
                repository_catalog,
                marker_color, marker_theme,
                COALESCE(sort_order, 0) AS sort_order
            FROM projects
            ORDER BY parent_project_id, sort_order, id;
            """
        ).fetchall()
        projects = []
        for row in rows:
            projects.append(
                ProjectData(
                    id=row["id"],
                    area=row["area"],
                    title=row["title"],
                    updated=date.fromisoformat(row["updated"]),
                    priority=row["priority"],
                    archived=bool(row["archived"]),
                    parent_project_id=row["parent_project_id"],
                    default_task_priority=row["default_task_priority"] or "",
                    force_recurrence_kind=(row["force_recurrence_kind"] or "").strip().lower(),
                    linked_map_id=row["linked_map_id"],
                    linked_note_id=row["linked_note_id"],
                    linked_object_id=row["linked_object_id"],
                    sort_order=int(row["sort_order"] or 0),
                    marker_color=(row["marker_color"] or "").strip(),
                    marker_theme=(row["marker_theme"] or "").strip(),
                    repository_catalog=(row["repository_catalog"] or "").strip(),
                )
            )
        return projects

    def create_project(
        self,
        area: str,
        title: str,
        updated: date,
        priority: str,
        archived: bool = False,
        parent_project_id: Optional[int] = None,
        sort_order: Optional[int] = None,
        default_task_priority: str = "",
        force_recurrence_kind: str = "",
        linked_map_id: Optional[int] = None,
        linked_note_id: Optional[int] = None,
        linked_object_id: Optional[int] = None,
        repository_catalog: str = "",
        marker_color: str = "",
        marker_theme: str = "",
    ) -> ProjectData:
        """РЎРѕР·РґР°РµС‚ РїСЂРѕРµРєС‚ РІ Р±Р°Р·Рµ РґР°РЅРЅС‹С…."""
        area = validate_area(area)
        title = validate_title(title, field_name="РќР°Р·РІР°РЅРёРµ РїСЂРѕРµРєС‚Р°")
        priority = normalize_priority(priority)
        default_task_priority = normalize_priority(default_task_priority) if default_task_priority else ""
        force_recurrence_kind = (force_recurrence_kind or "").strip().lower()
        repository_catalog = (repository_catalog or "").strip()
        marker_color = (marker_color or "").strip()
        marker_theme = (marker_theme or "").strip().lower()
        if force_recurrence_kind not in {"", "daily", "weekly", "monthly"}:
            raise ValueError("РќРµРєРѕСЂСЂРµРєС‚РЅР°СЏ РїРµСЂРёРѕРґРёС‡РЅРѕСЃС‚СЊ РїСЂРѕРµРєС‚Р°.")
        if not isinstance(updated, date):
            raise ValueError("Р”Р°С‚Р° РїСЂРѕРµРєС‚Р° РЅРµРєРѕСЂСЂРµРєС‚РЅР°.")

        if sort_order is None:
            sort_order = self._next_project_sort_order(parent_project_id)
        sort_order = max(0, int(sort_order))

        with self._conn:
            cur = self._conn.execute(
                """
                INSERT INTO projects (
                    area, title, updated, priority, archived,
                    parent_project_id, sort_order, default_task_priority, force_recurrence_kind,
                    linked_map_id, linked_note_id, linked_object_id, repository_catalog, marker_color, marker_theme
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    area,
                    title,
                    updated.isoformat(),
                    priority,
                    int(archived),
                    parent_project_id,
                    sort_order,
                    default_task_priority,
                    force_recurrence_kind,
                    linked_map_id,
                    linked_note_id,
                    linked_object_id,
                    repository_catalog,
                    marker_color,
                    marker_theme,
                ),
            )
        return ProjectData(
            cur.lastrowid,
            area,
            title,
            updated,
            priority,
            bool(archived),
            parent_project_id=parent_project_id,
            default_task_priority=default_task_priority,
            force_recurrence_kind=force_recurrence_kind,
            linked_map_id=linked_map_id,
            linked_note_id=linked_note_id,
            linked_object_id=linked_object_id,
            sort_order=sort_order,
            marker_color=marker_color,
            marker_theme=marker_theme,
            repository_catalog=repository_catalog,
        )

    def update_project(
        self,
        project_id: int,
        area: str,
        title: str,
        updated: date,
        priority: str,
        archived: bool,
        parent_project_id: Optional[int] = None,
        sort_order: Optional[int] = None,
        default_task_priority: str = "",
        force_recurrence_kind: str = "",
        linked_map_id: Optional[int] = None,
        linked_note_id: Optional[int] = None,
        linked_object_id: Optional[int] = None,
        repository_catalog: str = "",
        marker_color: str = "",
        marker_theme: str = "",
    ) -> ProjectData:
        """РћР±РЅРѕРІР»СЏРµС‚ РґР°РЅРЅС‹Рµ РїСЂРѕРµРєС‚Р°."""
        area = validate_area(area)
        title = validate_title(title, field_name="РќР°Р·РІР°РЅРёРµ РїСЂРѕРµРєС‚Р°")
        priority = normalize_priority(priority)
        default_task_priority = normalize_priority(default_task_priority) if default_task_priority else ""
        force_recurrence_kind = (force_recurrence_kind or "").strip().lower()
        repository_catalog = (repository_catalog or "").strip()
        marker_color = (marker_color or "").strip()
        marker_theme = (marker_theme or "").strip().lower()
        if force_recurrence_kind not in {"", "daily", "weekly", "monthly"}:
            raise ValueError("РќРµРєРѕСЂСЂРµРєС‚РЅР°СЏ РїРµСЂРёРѕРґРёС‡РЅРѕСЃС‚СЊ РїСЂРѕРµРєС‚Р°.")
        if not isinstance(updated, date):
            raise ValueError("Р”Р°С‚Р° РїСЂРѕРµРєС‚Р° РЅРµРєРѕСЂСЂРµРєС‚РЅР°.")
        current_row = self._conn.execute(
            "SELECT parent_project_id, COALESCE(sort_order, 0) AS sort_order FROM projects WHERE id = ?;",
            (project_id,),
        ).fetchone()
        if parent_project_id == project_id:
            parent_project_id = None
        if parent_project_id is not None:
            cursor = parent_project_id
            seen: set[int] = set()
            while cursor is not None and cursor not in seen:
                if cursor == project_id:
                    raise ValueError("Р¦РёРєР»РёС‡РµСЃРєР°СЏ СЃРІСЏР·СЊ РїСЂРѕРµРєС‚РѕРІ РЅРµ РґРѕРїСѓСЃРєР°РµС‚СЃСЏ.")
                seen.add(cursor)
                row = self._conn.execute(
                    "SELECT parent_project_id FROM projects WHERE id = ?;",
                    (cursor,),
                ).fetchone()
                cursor = row["parent_project_id"] if row is not None else None
        if sort_order is None:
            if current_row is None:
                sort_order = 0
            elif current_row["parent_project_id"] == parent_project_id:
                sort_order = int(current_row["sort_order"] or 0)
            else:
                sort_order = self._next_project_sort_order(parent_project_id, exclude_id=project_id)
        sort_order = max(0, int(sort_order))

        with self._conn:
            self._conn.execute(
                """
                UPDATE projects
                SET area = ?, title = ?, updated = ?, priority = ?, archived = ?,
                    parent_project_id = ?, sort_order = ?, default_task_priority = ?, force_recurrence_kind = ?,
                    linked_map_id = ?, linked_note_id = ?, linked_object_id = ?, repository_catalog = ?, marker_color = ?, marker_theme = ?
                WHERE id = ?;
                """,
                (
                    area,
                    title,
                    updated.isoformat(),
                    priority,
                    int(archived),
                    parent_project_id,
                    sort_order,
                    default_task_priority,
                    force_recurrence_kind,
                    linked_map_id,
                    linked_note_id,
                    linked_object_id,
                    repository_catalog,
                    marker_color,
                    marker_theme,
                    project_id,
                ),
            )
        return ProjectData(
            project_id,
            area,
            title,
            updated,
            priority,
            bool(archived),
            parent_project_id=parent_project_id,
            default_task_priority=default_task_priority,
            force_recurrence_kind=force_recurrence_kind,
            linked_map_id=linked_map_id,
            linked_note_id=linked_note_id,
            linked_object_id=linked_object_id,
            sort_order=sort_order,
            marker_color=marker_color,
            marker_theme=marker_theme,
            repository_catalog=repository_catalog,
        )

    def fetch_project_tree(self) -> List[ProjectData]:
        """Р’РѕР·РІСЂР°С‰Р°РµС‚ РїСЂРѕРµРєС‚С‹ РІ РїРѕСЂСЏРґРєРµ РѕР±С…РѕРґР° РїРѕ parent/sort_order."""
        return self.fetch_projects()

    def fetch_project_children(self, parent_project_id: Optional[int]) -> List[ProjectData]:
        """Р’РѕР·РІСЂР°С‰Р°РµС‚ РґРѕС‡РµСЂРЅРёРµ РїСЂРѕРµРєС‚С‹ РґР»СЏ СѓРєР°Р·Р°РЅРЅРѕРіРѕ СЂРѕРґРёС‚РµР»СЏ."""
        rows = self._conn.execute(
            """
            SELECT
                id, area, title, updated, priority, archived,
                parent_project_id, default_task_priority, force_recurrence_kind,
                linked_map_id, linked_note_id, linked_object_id,
                repository_catalog,
                marker_color, marker_theme,
                COALESCE(sort_order, 0) AS sort_order
            FROM projects
            WHERE parent_project_id IS ?
            ORDER BY sort_order, id;
            """,
            (parent_project_id,),
        ).fetchall()
        children: List[ProjectData] = []
        for row in rows:
            children.append(
                ProjectData(
                    id=row["id"],
                    area=row["area"],
                    title=row["title"],
                    updated=date.fromisoformat(row["updated"]),
                    priority=row["priority"],
                    archived=bool(row["archived"]),
                    parent_project_id=row["parent_project_id"],
                    default_task_priority=row["default_task_priority"] or "",
                    force_recurrence_kind=(row["force_recurrence_kind"] or "").strip().lower(),
                    linked_map_id=row["linked_map_id"],
                    linked_note_id=row["linked_note_id"],
                    linked_object_id=row["linked_object_id"],
                    sort_order=int(row["sort_order"] or 0),
                    marker_color=(row["marker_color"] or "").strip(),
                    marker_theme=(row["marker_theme"] or "").strip(),
                    repository_catalog=(row["repository_catalog"] or "").strip(),
                )
            )
        return children

    def _reindex_project_group(self, parent_project_id: Optional[int]) -> None:
        """РџРµСЂРµСЃРѕР±РёСЂР°РµС‚ РЅРµРїСЂРµСЂС‹РІРЅС‹Р№ sort_order РґР»СЏ РіСЂСѓРїРїС‹ РґРѕС‡РµСЂРЅРёС… РїСЂРѕРµРєС‚РѕРІ."""
        rows = self._conn.execute(
            """
            SELECT id
            FROM projects
            WHERE parent_project_id IS ?
            ORDER BY COALESCE(sort_order, 0), id;
            """,
            (parent_project_id,),
        ).fetchall()
        for idx, row in enumerate(rows):
            self._conn.execute(
                "UPDATE projects SET sort_order = ? WHERE id = ?;",
                (idx, row["id"]),
            )

    def move_project(self, project_id: int, new_parent_project_id: Optional[int], new_sort_order: Optional[int] = None) -> None:
        """РџРµСЂРµРјРµС‰Р°РµС‚ РїСЂРѕРµРєС‚ РІ РЅРѕРІСѓСЋ РІРµС‚РєСѓ Рё/РёР»Рё РїРѕР·РёС†РёСЋ СЃСЂРµРґРё siblings."""
        if new_parent_project_id == project_id:
            raise ValueError("Р¦РёРєР»РёС‡РµСЃРєР°СЏ СЃРІСЏР·СЊ РїСЂРѕРµРєС‚РѕРІ РЅРµ РґРѕРїСѓСЃРєР°РµС‚СЃСЏ.")

        row = self._conn.execute(
            """
            SELECT parent_project_id, COALESCE(sort_order, 0) AS sort_order
            FROM projects
            WHERE id = ?;
            """,
            (project_id,),
        ).fetchone()
        if row is None:
            raise ValueError("РџСЂРѕРµРєС‚ РЅРµ РЅР°Р№РґРµРЅ.")
        old_parent = row["parent_project_id"]

        if new_parent_project_id is not None:
            cursor = new_parent_project_id
            seen: set[int] = set()
            while cursor is not None and cursor not in seen:
                if cursor == project_id:
                    raise ValueError("Р¦РёРєР»РёС‡РµСЃРєР°СЏ СЃРІСЏР·СЊ РїСЂРѕРµРєС‚РѕРІ РЅРµ РґРѕРїСѓСЃРєР°РµС‚СЃСЏ.")
                seen.add(cursor)
                parent_row = self._conn.execute(
                    "SELECT parent_project_id FROM projects WHERE id = ?;",
                    (cursor,),
                ).fetchone()
                if parent_row is None:
                    raise ValueError("РќРѕРІС‹Р№ СЂРѕРґРёС‚РµР»СЊСЃРєРёР№ РїСЂРѕРµРєС‚ РЅРµ РЅР°Р№РґРµРЅ.")
                cursor = parent_row["parent_project_id"]

        siblings_count_row = self._conn.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM projects
            WHERE parent_project_id IS ?
              AND id != ?;
            """,
            (new_parent_project_id, project_id),
        ).fetchone()
        siblings_count = int(siblings_count_row["cnt"] if siblings_count_row is not None else 0)
        if new_sort_order is None:
            new_sort_order = siblings_count
        else:
            new_sort_order = max(0, min(int(new_sort_order), siblings_count))

        with self._conn:
            self._conn.execute(
                """
                UPDATE projects
                SET parent_project_id = ?, sort_order = ?
                WHERE id = ?;
                """,
                (new_parent_project_id, new_sort_order, project_id),
            )
            self._reindex_project_group(old_parent)
            self._reindex_project_group(new_parent_project_id)

    def reorder_project(self, project_id: int, new_sort_order: int) -> None:
        """РњРµРЅСЏРµС‚ РїРѕСЂСЏРґРѕРє РїСЂРѕРµРєС‚Р° СЃСЂРµРґРё siblings Р±РµР· СЃРјРµРЅС‹ СЂРѕРґРёС‚РµР»СЏ."""
        row = self._conn.execute(
            "SELECT parent_project_id FROM projects WHERE id = ?;",
            (project_id,),
        ).fetchone()
        if row is None:
            raise ValueError("РџСЂРѕРµРєС‚ РЅРµ РЅР°Р№РґРµРЅ.")
        parent_project_id = row["parent_project_id"]
        self.move_project(project_id, parent_project_id, new_sort_order=new_sort_order)

    def delete_project(self, project_id: int) -> None:
        """РЈРґР°Р»СЏРµС‚ РїСЂРѕРµРєС‚ РїРѕ id."""
        with self._conn:
            self._conn.execute("DELETE FROM projects WHERE id = ?;", (project_id,))

    def set_project_archived(self, project_id: int, archived: bool) -> None:
        """РћР±РЅРѕРІР»СЏРµС‚ СЃС‚Р°С‚СѓСЃ Р°СЂС…РёРІРёСЂРѕРІР°РЅРёСЏ РїСЂРѕРµРєС‚Р°."""
        with self._conn:
            self._conn.execute(
                "UPDATE projects SET archived = ? WHERE id = ?;",
                (int(archived), project_id),
            )

    def set_projects_archived_for_area(self, area: str, archived: bool) -> None:
        """РђСЂС…РёРІРёСЂСѓРµС‚ РІСЃРµ РїСЂРѕРµРєС‚С‹ РІ РѕР±Р»Р°СЃС‚Рё."""
        area = validate_area(area)
        with self._conn:
            self._conn.execute(
                "UPDATE projects SET archived = ? WHERE area = ?;",
                (int(archived), area),
            )

    def delete_projects_by_area(self, area: str) -> None:
        """РЈРґР°Р»СЏРµС‚ РІСЃРµ РїСЂРѕРµРєС‚С‹ РІ РѕР±Р»Р°СЃС‚Рё."""
        area = validate_area(area)
        with self._conn:
            self._conn.execute("DELETE FROM projects WHERE area = ?;", (area,))

    def rename_project_area(self, area: str, new_area: str) -> None:
        """РџРµСЂРµРёРјРµРЅРѕРІС‹РІР°РµС‚ РѕР±Р»Р°СЃС‚СЊ РїСЂРѕРµРєС‚РѕРІ."""
        area = validate_area(area)
        new_area = validate_area(new_area)
        with self._conn:
            self._conn.execute(
                "UPDATE projects SET area = ? WHERE area = ?;",
                (new_area, area),
            )

    def project_areas(self) -> List[str]:
        """Р’РѕР·РІСЂР°С‰Р°РµС‚ РѕС‚СЃРѕСЂС‚РёСЂРѕРІР°РЅРЅС‹Р№ СЃРїРёСЃРѕРє РѕР±Р»Р°СЃС‚РµР№ РїСЂРѕРµРєС‚Р°."""
        rows = self._conn.execute("SELECT DISTINCT area FROM projects ORDER BY area;").fetchall()
        return [row["area"] for row in rows]

__all__ = ["DatabaseProjectsMixin"]
