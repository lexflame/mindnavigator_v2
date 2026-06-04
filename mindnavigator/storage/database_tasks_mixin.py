"""DatabaseTasksMixin for storage database operations."""

from __future__ import annotations

import re

from ._shared import *  # noqa: F401,F403


_TASK_REFERENCE_RE = re.compile(r"(?<![A-Za-z0-9_])(?:MN-|#)(?P<id>\d+)(?![A-Za-z0-9_])", re.IGNORECASE)


class DatabaseTasksMixin:
    @staticmethod
    def _default_task_estimate_minutes(title: str, description: str, priority: str) -> int:
        text = f"{title or ''} {description or ''}".lower()
        words = len((description or "").split())
        base = 50
        if priority == "High":
            base = 90
        elif priority == "Low":
            base = 35
        elif priority == DEFERRED_PRIORITY:
            base = 25
        complexity_markers = [
            "исследование", "архитектура", "интеграция", "рефакторинг", "оптимизация",
            "debug", "тест", "документация", "design", "api", "sql",
            "миграция", "парсинг", "настройка", "синхрон",
        ]
        marker_hits = sum(1 for marker in complexity_markers if marker in text)
        raw = base + words * 2 + marker_hits * 15
        return max(15, min(8 * 60, int(round(raw / 5.0) * 5)))

    def fetch_tasks(self) -> List[TaskData]:
        """Возвращает список всех задач."""
        rows = self._conn.execute(
            """
            SELECT
                t.id,
                t.day,
                t.time_text,
                t.title,
                t.description,
                t.priority,
                t.importance,
                t.board_column,
                t.done,
                t.completion_delay_minutes,
                t.gantt_estimate_minutes,
                t.gantt_forecasted,
                t.started_at,
                t.finished_at,
                t.actual_minutes,
                t.project_id,
                t.is_plan_task,
                t.plan_order,
                t.marker_color,
                t.marker_theme,
                t.project_task_type_id,
                t.postponed_reason,
                t.postponed_by_project_task_type_id,
                t.created_at,
                t.updated_at,
                ptt.title AS project_task_type_title,
                ptt.value AS project_task_type_value,
                ptt.color_marker AS project_task_type_color,
                ptt.theme_marker AS project_task_type_theme,
                ptt.priority AS project_task_type_priority,
                ptt.importance AS project_task_type_importance,
                ptt.is_plan_task AS project_task_type_is_plan_task,
                ptt.concept_board_id AS project_task_type_concept_board_id,
                CASE
                    WHEN pp.id IS NOT NULL THEN COALESCE(pp.title, '') || ' / ' || COALESCE(p.title, '')
                    ELSE COALESCE(p.title, '')
                END AS project_title,
                COALESCE(p.area, '') AS project_area,
                t.parent_id,
                t.recurrence_kind,
                t.recurrence_interval
            FROM tasks t
            LEFT JOIN projects p ON p.id = t.project_id
            LEFT JOIN projects pp ON pp.id = p.parent_project_id
            LEFT JOIN project_task_types ptt ON ptt.id = t.project_task_type_id;
            """
        ).fetchall()
        tasks = []
        for row in rows:
            tasks.append(
                TaskData(
                    id=row["id"],
                    day=date.fromisoformat(row["day"]),
                    time_text=row["time_text"],
                    title=row["title"],
                    description=row["description"] or "",
                    priority=row["priority"],
                    importance=max(1, min(5, int(row["importance"] or 3))),
                    board_column=normalize_board_column(row["board_column"]),
                    done=bool(row["done"]),
                    completion_delay_minutes=max(0, int(row["completion_delay_minutes"] or 0)),
                    gantt_estimate_minutes=max(0, int(row["gantt_estimate_minutes"] or 0)),
                    gantt_forecasted=bool(row["gantt_forecasted"]),
                    started_at=(row["started_at"] or "").strip(),
                    finished_at=(row["finished_at"] or "").strip(),
                    actual_minutes=max(0, int(row["actual_minutes"] or 0)),
                    project_id=row["project_id"],
                    project_title=row["project_title"] or "",
                    project_area=row["project_area"] or "",
                    parent_id=row["parent_id"],
                    recurrence_kind=row["recurrence_kind"] or "",
                    recurrence_interval=max(1, int(row["recurrence_interval"] or 1)),
                    is_plan_task=bool(row["is_plan_task"]),
                    plan_order=max(0, int(row["plan_order"] or 0)),
                    marker_color=(row["marker_color"] or "").strip(),
                    marker_theme=(row["marker_theme"] or "").strip(),
                    project_task_type_id=row["project_task_type_id"],
                    project_task_type_title=(row["project_task_type_title"] or "").strip(),
                    project_task_type_value=(row["project_task_type_value"] or "").strip().upper(),
                    project_task_type_color=(row["project_task_type_color"] or "").strip(),
                    project_task_type_theme=(row["project_task_type_theme"] or "").strip(),
                    project_task_type_priority=(row["project_task_type_priority"] or "").strip(),
                    project_task_type_importance=max(1, min(5, int(row["project_task_type_importance"] or 3))),
                    project_task_type_is_plan_task=bool(row["project_task_type_is_plan_task"]),
                    project_task_type_concept_board_id=row["project_task_type_concept_board_id"],
                    postponed_reason=(row["postponed_reason"] or "").strip(),
                    postponed_by_project_task_type_id=row["postponed_by_project_task_type_id"],
                    created_at=(row["created_at"] or "").strip(),
                    updated_at=(row["updated_at"] or "").strip(),
                )
            )
        return tasks

    def _fetch_task_by_id(self, task_id: int) -> Optional[TaskData]:
        normalized_task_id = int(task_id)
        return next((task for task in self.fetch_tasks() if task.id == normalized_task_id), None)

    def _normalize_task_project_type_id(
        self,
        project_id: Optional[int],
        project_task_type_id: Optional[int],
    ) -> Optional[int]:
        if project_id is None or project_task_type_id is None:
            return None
        row = self._conn.execute(
            """
            SELECT id
            FROM project_task_types
            WHERE id = ? AND project_id = ? AND active = 1
            LIMIT 1;
            """,
            (int(project_task_type_id), int(project_id)),
        ).fetchone()
        return int(row["id"]) if row is not None else None

    def _project_task_type_defaults(self, project_task_type_id: Optional[int]) -> dict[str, object]:
        if project_task_type_id is None:
            return {}
        row = self._conn.execute(
            """
            SELECT color_marker, theme_marker, priority, importance, is_plan_task, concept_board_id
            FROM project_task_types
            WHERE id = ? AND active = 1;
            """,
            (int(project_task_type_id),),
        ).fetchone()
        if row is None:
            return {}
        result: dict[str, object] = {
            "importance": max(1, min(5, int(row["importance"] or 3))),
            "is_plan_task": bool(row["is_plan_task"]),
        }
        if (row["color_marker"] or "").strip():
            result["marker_color"] = (row["color_marker"] or "").strip()
        if (row["theme_marker"] or "").strip():
            result["marker_theme"] = (row["theme_marker"] or "").strip().lower()
        if (row["priority"] or "").strip():
            result["priority"] = normalize_priority(row["priority"])
        if row["concept_board_id"] is not None:
            result["concept_board_id"] = int(row["concept_board_id"])
        return result

    def _attach_project_task_type_concept_board(
        self,
        task_id: int,
        project_task_type_id: Optional[int],
    ) -> None:
        defaults = self._project_task_type_defaults(project_task_type_id)
        concept_board_id = defaults.get("concept_board_id")
        if concept_board_id is None:
            return
        self.attach_concept_board_item(int(concept_board_id), "task", int(task_id))

    def apply_project_task_type_defaults_to_task_tree(self, project_task_type_id: Optional[int]) -> None:
        if project_task_type_id is None:
            return
        task_type_id = int(project_task_type_id)
        row = self._conn.execute(
            """
            SELECT id, project_id, priority, importance, is_plan_task, color_marker, theme_marker, concept_board_id
            FROM project_task_types
            WHERE id = ? AND active = 1;
            """,
            (task_type_id,),
        ).fetchone()
        if row is None:
            return
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        affected_rows = self._conn.execute(
            """
            WITH RECURSIVE affected(id) AS (
                SELECT id FROM tasks WHERE project_task_type_id = ?
                UNION
                SELECT t.id FROM tasks t
                JOIN affected a ON t.parent_id = a.id
            )
            SELECT id FROM affected;
            """,
            (task_type_id,),
        ).fetchall()
        affected_ids = [int(item["id"]) for item in affected_rows]
        if not affected_ids:
            return
        assignments = [
            "project_id = ?",
            "project_task_type_id = ?",
            "importance = ?",
            "is_plan_task = ?",
            "updated_at = ?",
        ]
        params: list[object] = [
            int(row["project_id"]),
            task_type_id,
            max(1, min(5, int(row["importance"] or 3))),
            int(bool(row["is_plan_task"])),
            now,
        ]
        priority = (row["priority"] or "").strip()
        if priority:
            assignments.append("priority = ?")
            params.append(normalize_priority(priority))
        marker_color = (row["color_marker"] or "").strip()
        if marker_color:
            assignments.append("marker_color = ?")
            params.append(marker_color)
        marker_theme = (row["theme_marker"] or "").strip().lower()
        if marker_theme:
            assignments.append("marker_theme = ?")
            params.append(marker_theme)
        placeholders = ",".join("?" for _ in affected_ids)
        params.extend(affected_ids)
        with self._conn:
            self._conn.execute(
                f"""
                UPDATE tasks
                SET {", ".join(assignments)}
                WHERE id IN ({placeholders});
                """,
                params,
            )
        concept_board_id = row["concept_board_id"]
        if concept_board_id is not None:
            for task_id in affected_ids:
                self.attach_concept_board_item(int(concept_board_id), "task", int(task_id))

    def create_task(
        self,
        title: str,
        description: str,
        day: date,
        time_text: str,
        priority: str,
        project_id: Optional[int] = None,
        parent_id: Optional[int] = None,
        recurrence_kind: str = "",
        recurrence_interval: int = 1,
        is_plan_task: bool = False,
        plan_order: Optional[int] = None,
        marker_color: str = "",
        marker_theme: str = "",
        project_task_type_id: Optional[int] = None,
        importance: int = 3,
    ) -> TaskData:
        """Создает задачу в базе данных."""
        title = validate_title(title)
        description = (description or "").strip()
        time_text = validate_time_text(time_text)
        priority = normalize_priority(priority)
        recurrence_kind = (recurrence_kind or "").strip().lower()
        recurrence_interval = max(1, int(recurrence_interval or 1))
        is_plan_task = bool(is_plan_task)
        marker_color = (marker_color or "").strip()
        marker_theme = (marker_theme or "").strip().lower()
        project_task_type_id = self._normalize_task_project_type_id(project_id, project_task_type_id)
        importance = max(1, min(5, int(importance or 3)))
        type_defaults = self._project_task_type_defaults(project_task_type_id)
        priority = str(type_defaults.get("priority", priority))
        marker_color = str(type_defaults.get("marker_color", marker_color))
        marker_theme = str(type_defaults.get("marker_theme", marker_theme))
        importance = int(type_defaults.get("importance", importance))
        is_plan_task = bool(type_defaults.get("is_plan_task", is_plan_task))
        if not isinstance(day, date):
            raise ValueError("Дата задачи некорректна.")
        if plan_order is None:
            plan_order = self._next_task_plan_order(parent_id)
        plan_order = max(0, int(plan_order))

        project_title = ""
        project_area = ""
        project_links: List[Tuple[str, int]] = []
        if project_id is not None:
            row = self._conn.execute(
                """
                SELECT
                    p.area, p.title, pp.title AS parent_title, p.default_task_priority, p.force_recurrence_kind,
                    p.linked_map_id, p.linked_note_id, p.linked_object_id
                FROM projects p
                LEFT JOIN projects pp ON pp.id = p.parent_project_id
                WHERE p.id = ?;
                """,
                (project_id,),
            ).fetchone()
            if row:
                project_area = row["area"]
                project_title = f'{row["parent_title"]} / {row["title"]}' if row["parent_title"] else row["title"]
                forced_priority = (row["default_task_priority"] or "").strip()
                forced_recurrence = (row["force_recurrence_kind"] or "").strip().lower()
                if forced_priority:
                    priority = normalize_priority(forced_priority)
                if forced_recurrence in {"daily", "weekly", "monthly"}:
                    recurrence_kind = forced_recurrence
                    recurrence_interval = max(1, recurrence_interval)
                for kind, ref_id in (
                    ("map", row["linked_map_id"]),
                    ("note", row["linked_note_id"]),
                    ("object", row["linked_object_id"]),
                ):
                    if ref_id is not None:
                        project_links.append((kind, int(ref_id)))

        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        board_column = BOARD_COLUMN_QUEUE
        with self._conn:
            cur = self._conn.execute(
                """
                INSERT INTO tasks (
                    title, description, day, time_text, priority, importance, board_column, done, project_id, parent_id,
                    recurrence_kind, recurrence_interval, is_plan_task, plan_order, marker_color, marker_theme,
                    project_task_type_id, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    title,
                    description,
                    day.isoformat(),
                    time_text,
                    priority,
                    importance,
                    board_column,
                    project_id,
                    parent_id,
                    recurrence_kind,
                    recurrence_interval,
                    int(is_plan_task),
                    plan_order,
                    marker_color,
                    marker_theme,
                    project_task_type_id,
                    now,
                    now,
                ),
            )
        for kind, ref_id in project_links:
            self.add_task_attachment(cur.lastrowid, kind, ref_id)
        self._attach_project_task_type_concept_board(cur.lastrowid, project_task_type_id)
        self._sync_task_text_attachments(cur.lastrowid, title, description)
        plan_root_id = self._plan_root_id_for_parent(parent_id)
        if plan_root_id is not None:
            self._ensure_task_estimate(cur.lastrowid, title, description, priority)
            self._ensure_active_plan_item_state(plan_root_id)
        created = self._fetch_task_by_id(cur.lastrowid)
        if created is not None:
            return created
        return TaskData(
            id=cur.lastrowid,
            day=day,
            time_text=time_text,
            title=title,
            description=description,
            priority=priority,
            importance=importance,
            done=False,
            board_column=board_column,
            project_id=project_id,
            project_title=project_title,
            project_area=project_area,
            parent_id=parent_id,
            recurrence_kind=recurrence_kind,
            recurrence_interval=recurrence_interval,
            completion_delay_minutes=0,
            gantt_estimate_minutes=0,
            gantt_forecasted=False,
            started_at="",
            finished_at="",
            actual_minutes=0,
            is_plan_task=is_plan_task,
            plan_order=plan_order,
            marker_color=marker_color,
            marker_theme=marker_theme,
            project_task_type_id=project_task_type_id,
            created_at=now,
            updated_at=now,
        )

    def update_task(
        self,
        task_id: int,
        title: str,
        description: str,
        day: date,
        time_text: str,
        priority: str,
        done: bool,
        project_id: Optional[int] = None,
        parent_id: Optional[int] = None,
        recurrence_kind: str = "",
        recurrence_interval: int = 1,
        is_plan_task: Optional[bool] = None,
        plan_order: Optional[int] = None,
        marker_color: str = "",
        marker_theme: str = "",
        project_task_type_id: Optional[int] = None,
        importance: Optional[int] = None,
    ) -> TaskData:
        """Обновляет задачу."""
        prev_row = self._conn.execute(
            """
            SELECT priority, importance, board_column, parent_id, is_plan_task, plan_order, postponed_reason,
                   postponed_by_project_task_type_id
            FROM tasks
            WHERE id = ?;
            """,
            (task_id,),
        ).fetchone()
        prev_priority = prev_row["priority"] if prev_row else priority
        prev_importance = int(prev_row["importance"] or 3) if prev_row else 3
        prev_board_column = prev_row["board_column"] if prev_row else BOARD_COLUMN_QUEUE
        prev_parent_id = prev_row["parent_id"] if prev_row else parent_id
        prev_plan_root_id = self._plan_root_id_for_parent(prev_parent_id)
        prev_is_plan_task = bool(prev_row["is_plan_task"]) if prev_row else False
        prev_plan_order = max(0, int(prev_row["plan_order"] or 0)) if prev_row else 0
        title = validate_title(title)
        description = (description or "").strip()
        time_text = validate_time_text(time_text)
        priority = normalize_priority(priority)
        if importance is None:
            importance = prev_importance
        importance = max(1, min(5, int(importance or 3)))
        recurrence_kind = (recurrence_kind or "").strip().lower()
        recurrence_interval = max(1, int(recurrence_interval or 1))
        if is_plan_task is None:
            is_plan_task = prev_is_plan_task
        is_plan_task = bool(is_plan_task)
        if plan_order is None:
            if parent_id != prev_parent_id:
                plan_order = self._next_task_plan_order(parent_id, exclude_task_id=task_id)
            else:
                plan_order = prev_plan_order
        plan_order = max(0, int(plan_order))
        marker_color = (marker_color or "").strip()
        marker_theme = (marker_theme or "").strip().lower()
        project_task_type_id = self._normalize_task_project_type_id(project_id, project_task_type_id)
        type_defaults = self._project_task_type_defaults(project_task_type_id)
        priority = str(type_defaults.get("priority", priority))
        marker_color = str(type_defaults.get("marker_color", marker_color))
        marker_theme = str(type_defaults.get("marker_theme", marker_theme))
        importance = int(type_defaults.get("importance", importance))
        is_plan_task = bool(type_defaults.get("is_plan_task", is_plan_task))
        postponed_reason = (prev_row["postponed_reason"] or "").strip() if prev_row else ""
        postponed_by_type_id = prev_row["postponed_by_project_task_type_id"] if prev_row else None
        if postponed_reason == "project_task_type_deactivated" and postponed_by_type_id is not None:
            priority = DEFERRED_PRIORITY
            board_column = BOARD_COLUMN_DEFERRED
        if not isinstance(day, date):
            raise ValueError("Дата задачи некорректна.")

        project_title = ""
        project_area = ""
        project_links: List[Tuple[str, int]] = []
        if project_id is not None:
            row = self._conn.execute(
                """
                SELECT p.area, p.title, pp.title AS parent_title, p.default_task_priority, p.force_recurrence_kind
                FROM projects p
                LEFT JOIN projects pp ON pp.id = p.parent_project_id
                WHERE p.id = ?;
                """,
                (project_id,),
            ).fetchone()
            if row:
                project_area = row["area"]
                project_title = f'{row["parent_title"]} / {row["title"]}' if row["parent_title"] else row["title"]
                forced_priority = (row["default_task_priority"] or "").strip()
                forced_recurrence = (row["force_recurrence_kind"] or "").strip().lower()
                if forced_priority:
                    priority = normalize_priority(forced_priority)
                if forced_recurrence in {"daily", "weekly", "monthly"}:
                    recurrence_kind = forced_recurrence
                    recurrence_interval = max(1, recurrence_interval)
            links_row = self._conn.execute(
                """
                SELECT linked_map_id, linked_note_id, linked_object_id
                FROM projects
                WHERE id = ?;
                """,
                (project_id,),
            ).fetchone()
            if links_row:
                for kind, ref_id in (
                    ("map", links_row["linked_map_id"]),
                    ("note", links_row["linked_note_id"]),
                    ("object", links_row["linked_object_id"]),
                ):
                    if ref_id is not None:
                        project_links.append((kind, int(ref_id)))

        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        board_column = normalize_board_column(prev_board_column)
        with self._conn:
            self._conn.execute(
                """
                UPDATE tasks
                SET title = ?, description = ?, day = ?, time_text = ?, priority = ?, importance = ?, board_column = ?, done = ?, project_id = ?, parent_id = ?,
                    recurrence_kind = ?, recurrence_interval = ?, is_plan_task = ?, plan_order = ?, marker_color = ?, marker_theme = ?,
                    project_task_type_id = ?, updated_at = ?
                WHERE id = ?;
                """,
                (
                    title,
                    description,
                    day.isoformat(),
                    time_text,
                    priority,
                    importance,
                    board_column,
                    int(done),
                    project_id,
                    parent_id,
                    recurrence_kind,
                    recurrence_interval,
                    int(is_plan_task),
                    plan_order,
                    marker_color,
                    marker_theme,
                    project_task_type_id,
                    now,
                    task_id,
                ),
            )
            cascade_priority = None
            if priority == DEFERRED_PRIORITY and prev_priority != DEFERRED_PRIORITY:
                cascade_priority = priority
            elif prev_priority == DEFERRED_PRIORITY and priority != DEFERRED_PRIORITY:
                cascade_priority = priority
            if cascade_priority is not None:
                self._conn.execute(
                    """
                    WITH RECURSIVE descendants(id) AS (
                        SELECT id FROM tasks WHERE parent_id = ?
                        UNION ALL
                        SELECT t.id FROM tasks t
                        JOIN descendants d ON t.parent_id = d.id
                    )
                    UPDATE tasks
                    SET priority = ?, updated_at = ?
                    WHERE id IN (SELECT id FROM descendants);
                    """,
                    (task_id, cascade_priority, now),
                )
        for kind, ref_id in project_links:
            self.add_task_attachment(task_id, kind, ref_id)
        self._attach_project_task_type_concept_board(task_id, project_task_type_id)
        self.apply_project_task_type_defaults_to_task_tree(project_task_type_id)
        self._sync_task_text_attachments(task_id, title, description)
        new_plan_root_id = self._plan_root_id_for_parent(parent_id)
        if new_plan_root_id is not None:
            self._ensure_task_estimate(task_id, title, description, priority)
        if prev_plan_root_id is not None:
            self._ensure_active_plan_item_state(prev_plan_root_id)
        if new_plan_root_id is not None and new_plan_root_id != prev_plan_root_id:
            self._ensure_active_plan_item_state(new_plan_root_id)
        updated = self._fetch_task_by_id(task_id)
        if updated is not None:
            return updated
        return TaskData(
            id=task_id,
            day=day,
            time_text=time_text,
            title=title,
            description=description,
            priority=priority,
            importance=importance,
            done=bool(done),
            board_column=board_column,
            project_id=project_id,
            project_title=project_title,
            project_area=project_area,
            parent_id=parent_id,
            recurrence_kind=recurrence_kind,
            recurrence_interval=recurrence_interval,
            completion_delay_minutes=0,
            gantt_estimate_minutes=0,
            gantt_forecasted=False,
            started_at="",
            finished_at="",
            actual_minutes=0,
            is_plan_task=is_plan_task,
            plan_order=plan_order,
            marker_color=marker_color,
            marker_theme=marker_theme,
            project_task_type_id=project_task_type_id,
            postponed_reason=postponed_reason,
            postponed_by_project_task_type_id=postponed_by_type_id,
            updated_at=now,
        )

    def set_task_done(self, task_id: int, done: bool) -> None:
        """Обновляет статус выполнения задачи."""
        row = self._conn.execute(
            """
            SELECT
                id, title, description, day, time_text, priority, board_column, done, project_id, parent_id,
                recurrence_kind, recurrence_interval, is_plan_task, plan_order, marker_color, marker_theme,
                project_task_type_id,
                started_at, finished_at, actual_minutes, gantt_estimate_minutes, gantt_forecasted
            FROM tasks
            WHERE id = ?;
            """,
            (task_id,),
        ).fetchone()
        if row is None:
            return
        prev_done = bool(row["done"])
        plan_root_id = self._plan_root_id_for_task(task_id)
        recurrence_kind = (row["recurrence_kind"] or "").strip().lower()
        recurrence_interval = max(1, int(row["recurrence_interval"] or 1))
        completed_utc = datetime.now(timezone.utc)
        now_utc = completed_utc.isoformat(timespec="seconds")
        completed_local = datetime.now()
        planned_day = date.fromisoformat(row["day"])
        planned_time_text = (row["time_text"] or "").strip()
        try:
            if planned_time_text:
                planned_dt = datetime.strptime(
                    f"{planned_day.isoformat()} {planned_time_text}",
                    "%Y-%m-%d %H:%M",
                )
            else:
                planned_dt = datetime.combine(planned_day, datetime.min.time())
        except ValueError:
            planned_dt = datetime.combine(planned_day, datetime.min.time())
        completion_delay_minutes = 0
        if done:
            delta_minutes = int((completed_local - planned_dt).total_seconds() // 60)
            if delta_minutes > 0:
                completion_delay_minutes = delta_minutes
        is_plan_item = self._task_is_plan_item(task_id)
        started_at = (row["started_at"] or "").strip()
        estimate_minutes = max(
            1,
            int(row["gantt_estimate_minutes"] or 0)
            or self._default_task_estimate_minutes(row["title"], row["description"] or "", row["priority"]),
        )
        actual_minutes = max(0, int(row["actual_minutes"] or 0))
        finished_at = ""
        if done and is_plan_item:
            if not started_at:
                started_at = now_utc
            try:
                started_dt = datetime.fromisoformat(started_at)
                actual_minutes = max(1, int(round((completed_utc - started_dt).total_seconds() / 60.0)))
            except ValueError:
                actual_minutes = estimate_minutes
            finished_at = now_utc
        with self._conn:
            if done:
                if is_plan_item:
                    self._conn.execute(
                        """
                        UPDATE tasks
                        SET done = ?, completion_delay_minutes = 0, started_at = ?, finished_at = ?, actual_minutes = ?, updated_at = ?
                        WHERE id = ?;
                        """,
                        (
                            int(done),
                            started_at,
                            finished_at,
                            actual_minutes,
                            now_utc,
                            task_id,
                        ),
                    )
                else:
                    self._conn.execute(
                        """
                        UPDATE tasks
                        SET done = ?, day = ?, time_text = ?, completion_delay_minutes = ?, updated_at = ?
                        WHERE id = ?;
                        """,
                        (
                            int(done),
                            completed_local.date().isoformat(),
                            completed_local.strftime("%H:%M"),
                            completion_delay_minutes,
                            now_utc,
                            task_id,
                        ),
                    )
            else:
                self._conn.execute(
                    """
                    UPDATE tasks
                    SET done = ?, completion_delay_minutes = 0, finished_at = '', actual_minutes = 0, updated_at = ?
                    WHERE id = ?;
                    """,
                    (int(done), now_utc, task_id),
                )
            if done and not prev_done and recurrence_kind:
                current_day = planned_day
                next_day = self._next_recurrence_day(current_day, recurrence_kind, recurrence_interval)
                cur = self._conn.execute(
                    """
                    INSERT INTO tasks (
                        title, description, day, time_text, priority, board_column, done, project_id, parent_id,
                        recurrence_kind, recurrence_interval, is_plan_task, plan_order, marker_color, marker_theme,
                        project_task_type_id, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        row["title"],
                        row["description"] or "",
                        next_day.isoformat(),
                        row["time_text"] or "",
                        row["priority"],
                        normalize_board_column(row["board_column"]),
                        row["project_id"],
                        row["parent_id"],
                        recurrence_kind,
                        recurrence_interval,
                        int(bool(row["is_plan_task"])),
                        self._next_task_plan_order(row["parent_id"]),
                        row["marker_color"] or "",
                        row["marker_theme"] or "",
                        row["project_task_type_id"],
                        now_utc,
                        now_utc,
                    ),
                )
                self._sync_task_text_attachments(cur.lastrowid, row["title"], row["description"] or "")
        if done and is_plan_item and plan_root_id is not None:
            self._reforecast_plan_branch(plan_root_id, task_id, actual_minutes, estimate_minutes)
            self._ensure_active_plan_item_state(plan_root_id)
        elif not done and plan_root_id is not None:
            self._ensure_active_plan_item_state(plan_root_id)

    def _plan_root_id_for_parent(self, parent_id: Optional[int]) -> Optional[int]:
        if parent_id is None:
            return None
        row = self._conn.execute(
            "SELECT id FROM tasks WHERE id = ? AND is_plan_task = 1 LIMIT 1;",
            (int(parent_id),),
        ).fetchone()
        return int(row["id"]) if row is not None else None

    def _plan_root_id_for_task(self, task_id: int) -> Optional[int]:
        row = self._conn.execute(
            """
            SELECT parent.id AS root_id
            FROM tasks child
            JOIN tasks parent ON parent.id = child.parent_id
            WHERE child.id = ?
              AND parent.is_plan_task = 1
            LIMIT 1;
            """,
            (int(task_id),),
        ).fetchone()
        return int(row["root_id"]) if row is not None else None

    def _first_open_plan_item_id(self, root_id: int) -> Optional[int]:
        row = self._conn.execute(
            """
            SELECT id
            FROM tasks
            WHERE parent_id = ?
              AND done = 0
            ORDER BY plan_order, id
            LIMIT 1;
            """,
            (int(root_id),),
        ).fetchone()
        return int(row["id"]) if row is not None else None

    def _ensure_task_estimate(self, task_id: int, title: str, description: str, priority: str) -> int:
        row = self._conn.execute(
            "SELECT gantt_estimate_minutes FROM tasks WHERE id = ? LIMIT 1;",
            (int(task_id),),
        ).fetchone()
        current_estimate = max(0, int(row["gantt_estimate_minutes"] or 0)) if row is not None else 0
        if current_estimate > 0:
            return current_estimate
        estimate = self._default_task_estimate_minutes(title, description, priority)
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                """
                UPDATE tasks
                SET gantt_estimate_minutes = ?, gantt_forecasted = 1, updated_at = ?
                WHERE id = ?;
                """,
                (estimate, now, int(task_id)),
            )
        return estimate

    def _ensure_active_plan_item_state(self, root_id: int) -> Optional[int]:
        active_task_id = self._first_open_plan_item_id(root_id)
        if active_task_id is None:
            return None
        row = self._conn.execute(
            """
            SELECT id, title, description, priority, started_at
            FROM tasks
            WHERE id = ?;
            """,
            (active_task_id,),
        ).fetchone()
        if row is None:
            return None
        self._ensure_task_estimate(
            active_task_id,
            row["title"],
            row["description"] or "",
            row["priority"],
        )
        if not (row["started_at"] or "").strip():
            now = datetime.now(timezone.utc).isoformat(timespec="seconds")
            with self._conn:
                self._conn.execute(
                    """
                    UPDATE tasks
                    SET started_at = ?, updated_at = ?
                    WHERE id = ?
                      AND COALESCE(started_at, '') = ''
                      AND done = 0;
                    """,
                    (now, now, active_task_id),
                )
        return active_task_id

    def _reforecast_plan_branch(
        self,
        root_id: int,
        completed_task_id: int,
        actual_minutes: int,
        estimate_minutes: int,
    ) -> None:
        if actual_minutes <= 0 or estimate_minutes <= 0:
            return
        rows = self._conn.execute(
            """
            SELECT id, title, description, priority, done, gantt_estimate_minutes, gantt_forecasted
            FROM tasks
            WHERE parent_id = ?
            ORDER BY plan_order, id;
            """,
            (int(root_id),),
        ).fetchall()
        ratio = max(0.1, min(8.0, float(actual_minutes) / float(estimate_minutes)))
        apply_changes = False
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        seen_completed = False
        for row in rows:
            if int(row["id"]) == int(completed_task_id):
                seen_completed = True
                continue
            if not seen_completed or bool(row["done"]) or not bool(row["gantt_forecasted"]):
                continue
            base_estimate = max(
                5,
                int(row["gantt_estimate_minutes"] or 0)
                or self._default_task_estimate_minutes(row["title"], row["description"] or "", row["priority"]),
            )
            recalculated = max(5, min(8 * 60, int(round((base_estimate * ratio) / 5.0) * 5)))
            if recalculated == int(row["gantt_estimate_minutes"] or 0):
                continue
            if not apply_changes:
                apply_changes = True
            self._conn.execute(
                """
                UPDATE tasks
                SET gantt_estimate_minutes = ?, updated_at = ?
                WHERE id = ?;
                """,
                (recalculated, now, int(row["id"])),
            )

    def _next_task_plan_order(
        self,
        parent_id: Optional[int],
        exclude_task_id: Optional[int] = None,
    ) -> int:
        if exclude_task_id is None:
            row = self._conn.execute(
                """
                SELECT COALESCE(MAX(plan_order), -1) AS max_order
                FROM tasks
                WHERE parent_id IS ?;
                """,
                (parent_id,),
            ).fetchone()
        else:
            row = self._conn.execute(
                """
                SELECT COALESCE(MAX(plan_order), -1) AS max_order
                FROM tasks
                WHERE parent_id IS ?
                  AND id != ?;
                """,
                (parent_id, exclude_task_id),
            ).fetchone()
        return int(row["max_order"]) + 1 if row is not None else 0

    def reorder_task_siblings(self, parent_id: Optional[int], ordered_task_ids: List[int]) -> None:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            for plan_order, task_id in enumerate(int(task_id) for task_id in ordered_task_ids):
                self._conn.execute(
                    """
                    UPDATE tasks
                    SET plan_order = ?, updated_at = ?
                    WHERE id = ? AND parent_id IS ?;
                    """,
                    (plan_order, now, task_id, parent_id),
                )
        plan_root_id = self._plan_root_id_for_parent(parent_id)
        if plan_root_id is not None:
            self._ensure_active_plan_item_state(plan_root_id)

    def _task_is_plan_item(self, task_id: int) -> bool:
        row = self._conn.execute(
            """
            SELECT 1
            FROM tasks child
            JOIN tasks parent ON parent.id = child.parent_id
            WHERE child.id = ?
              AND parent.is_plan_task = 1
            LIMIT 1;
            """,
            (task_id,),
        ).fetchone()
        return row is not None

    def set_task_board_column(self, task_id: int, board_column: str) -> None:
        """Обновляет локальную board-колонку задачи без влияния на приоритет."""
        if self._conn.execute("SELECT 1 FROM tasks WHERE id = ?;", (task_id,)).fetchone() is None:
            return
        requested_board_column = str(board_column or "").strip().lower()
        normalized_board_column = normalize_board_column(requested_board_column)
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                """
                UPDATE tasks
                SET board_column = ?, updated_at = ?
                WHERE id = ?;
                """,
                (normalized_board_column, now, task_id),
            )

    def set_task_gantt_estimate(self, task_id: int, minutes: int, forecasted: bool = True) -> None:
        """Сохраняет оценку времени задачи для режима диаграммы Ганта."""
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        safe_minutes = max(0, int(minutes or 0))
        with self._conn:
            self._conn.execute(
                """
                UPDATE tasks
                SET gantt_estimate_minutes = ?, gantt_forecasted = ?, updated_at = ?
                WHERE id = ?;
                """,
                (safe_minutes, int(bool(forecasted)), now, task_id),
            )

    def _next_recurrence_day(self, base_day: date, recurrence_kind: str, recurrence_interval: int) -> date:
        interval = max(1, int(recurrence_interval or 1))
        if recurrence_kind == "daily":
            return base_day + timedelta(days=interval)
        if recurrence_kind == "weekly":
            return base_day + timedelta(days=7 * interval)
        if recurrence_kind == "monthly":
            return self._add_months(base_day, interval)
        return base_day

    @staticmethod
    def _add_months(base_day: date, months: int) -> date:
        month0 = base_day.month - 1 + max(1, months)
        year = base_day.year + month0 // 12
        month = month0 % 12 + 1
        if month == 2:
            leap = (year % 400 == 0) or (year % 4 == 0 and year % 100 != 0)
            max_day = 29 if leap else 28
        elif month in {4, 6, 9, 11}:
            max_day = 30
        else:
            max_day = 31
        day = min(base_day.day, max_day)
        return date(year, month, day)

    def delete_task(self, task_id: int) -> None:
        """Удаляет задачу по id."""
        with self._conn:
            self._conn.execute(
                """
                WITH RECURSIVE descendants(id) AS (
                    SELECT id FROM tasks WHERE id = ?
                    UNION ALL
                    SELECT t.id FROM tasks t
                    JOIN descendants d ON t.parent_id = d.id
                )
                DELETE FROM tasks WHERE id IN (SELECT id FROM descendants);
                """,
                (task_id,),
            )

    def fetch_task_attachments(self, task_id: int) -> List[TaskAttachmentData]:
        """Возвращает список вложений задачи."""
        task_id = int(task_id)
        rows = self._conn.execute(
            """
            SELECT id, task_id, kind, ref_id, created_at, comment
            FROM task_attachments
            WHERE task_id = ?
            ORDER BY created_at ASC;
            """,
            (task_id,),
        ).fetchall()
        return [TaskAttachmentData.from_row(row) for row in rows]

    @staticmethod
    def _extract_task_reference_ids(*texts: str) -> list[int]:
        seen: set[int] = set()
        result: list[int] = []
        for text in texts:
            for match in _TASK_REFERENCE_RE.finditer(text or ""):
                task_id = int(match.group("id"))
                if task_id <= 0 or task_id in seen:
                    continue
                seen.add(task_id)
                result.append(task_id)
        return result

    def _sync_task_text_attachments(self, task_id: int, title: str, description: str) -> None:
        mentioned_ids = [
            linked_task_id
            for linked_task_id in self._extract_task_reference_ids(title, description)
            if linked_task_id != int(task_id)
        ]
        if not mentioned_ids:
            return
        placeholders = ",".join("?" for _ in mentioned_ids)
        rows = self._conn.execute(
            f"SELECT id FROM tasks WHERE id IN ({placeholders});",
            tuple(mentioned_ids),
        ).fetchall()
        existing_ids = {int(row["id"]) for row in rows}
        for linked_task_id in mentioned_ids:
            if linked_task_id in existing_ids:
                self.add_task_attachment(task_id, "task", linked_task_id)

    def add_task_attachment(self, task_id: int, kind: str, ref_id: int) -> TaskAttachmentData:
        """Добавляет вложение к задаче."""
        task_id = int(task_id)
        if task_id <= 0:
            raise ValueError("Идентификатор задачи должен быть положительным.")
        ref_id = int(ref_id)
        if ref_id <= 0:
            raise ValueError("Идентификатор вложенного элемента должен быть положительным.")
        kind = TaskAttachmentData.normalize_kind(kind)
        if kind == "task" and task_id == ref_id:
            raise ValueError("Нельзя прикрепить задачу к самой себе.")
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                """
                INSERT OR IGNORE INTO task_attachments (task_id, kind, ref_id, created_at)
                VALUES (?, ?, ?, ?);
                """,
                (task_id, kind, ref_id, now),
            )
        row = self._conn.execute(
            """
            SELECT id, task_id, kind, ref_id, created_at, comment
            FROM task_attachments
            WHERE task_id = ? AND kind = ? AND ref_id = ?;
            """,
            (task_id, kind, ref_id),
        ).fetchone()
        return TaskAttachmentData.from_row(row)

    def update_task_attachment_comment(self, attachment_id: int, comment: str) -> TaskAttachmentData:
        """Updates the comment stored for one attachment inside its task."""
        attachment_id = int(attachment_id)
        if attachment_id <= 0:
            raise ValueError("Идентификатор вложения должен быть положительным.")
        comment = (comment or "").strip()
        with self._conn:
            self._conn.execute(
                "UPDATE task_attachments SET comment = ? WHERE id = ?;",
                (comment, attachment_id),
            )
        row = self._conn.execute(
            "SELECT id, task_id, kind, ref_id, created_at, comment FROM task_attachments WHERE id = ?;",
            (attachment_id,),
        ).fetchone()
        if row is None:
            raise ValueError("Вложение задачи не найдено.")
        return TaskAttachmentData.from_row(row)

    def delete_task_attachment(self, attachment_id: int) -> None:
        """Удаляет вложение задачи."""
        with self._conn:
            self._conn.execute("DELETE FROM task_attachments WHERE id = ?;", (attachment_id,))

__all__ = ["DatabaseTasksMixin"]
