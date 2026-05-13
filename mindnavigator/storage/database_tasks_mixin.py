"""DatabaseTasksMixin for storage database operations."""

from __future__ import annotations

import re

from ._shared import *  # noqa: F401,F403


_TASK_REFERENCE_RE = re.compile(r"(?<![A-Za-z0-9_])(?:MN-|#)(?P<id>\d+)(?![A-Za-z0-9_])", re.IGNORECASE)


class DatabaseTasksMixin:
    def fetch_tasks(self) -> List[TaskData]:
        """Р’РѕР·РІСЂР°С‰Р°РµС‚ СЃРїРёСЃРѕРє РІСЃРµС… Р·Р°РґР°С‡."""
        rows = self._conn.execute(
            """
            SELECT
                t.id,
                t.day,
                t.time_text,
                t.title,
                t.description,
                t.priority,
                t.board_column,
                t.done,
                t.completion_delay_minutes,
                t.gantt_estimate_minutes,
                t.gantt_forecasted,
                t.project_id,
                t.is_plan_task,
                t.plan_order,
                t.marker_color,
                t.marker_theme,
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
            LEFT JOIN projects pp ON pp.id = p.parent_project_id;
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
                    board_column=normalize_board_column(row["board_column"], row["priority"]),
                    done=bool(row["done"]),
                    completion_delay_minutes=max(0, int(row["completion_delay_minutes"] or 0)),
                    gantt_estimate_minutes=max(0, int(row["gantt_estimate_minutes"] or 0)),
                    gantt_forecasted=bool(row["gantt_forecasted"]),
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
                )
            )
        return tasks

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
    ) -> TaskData:
        """РЎРѕР·РґР°РµС‚ Р·Р°РґР°С‡Сѓ РІ Р±Р°Р·Рµ РґР°РЅРЅС‹С…."""
        title = validate_title(title)
        description = (description or "").strip()
        time_text = validate_time_text(time_text)
        priority = normalize_priority(priority)
        recurrence_kind = (recurrence_kind or "").strip().lower()
        recurrence_interval = max(1, int(recurrence_interval or 1))
        is_plan_task = bool(is_plan_task)
        marker_color = (marker_color or "").strip()
        marker_theme = (marker_theme or "").strip().lower()
        if not isinstance(day, date):
            raise ValueError("Р”Р°С‚Р° Р·Р°РґР°С‡Рё РЅРµРєРѕСЂСЂРµРєС‚РЅР°.")
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
        board_column = BOARD_COLUMN_DEFERRED if priority == DEFERRED_PRIORITY else BOARD_COLUMN_QUEUE
        with self._conn:
            cur = self._conn.execute(
                """
                INSERT INTO tasks (
                    title, description, day, time_text, priority, board_column, done, project_id, parent_id,
                    recurrence_kind, recurrence_interval, is_plan_task, plan_order, marker_color, marker_theme, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    title,
                    description,
                    day.isoformat(),
                    time_text,
                    priority,
                    board_column,
                    project_id,
                    parent_id,
                    recurrence_kind,
                    recurrence_interval,
                    int(is_plan_task),
                    plan_order,
                    marker_color,
                    marker_theme,
                    now,
                    now,
                ),
            )
        for kind, ref_id in project_links:
            self.add_task_attachment(cur.lastrowid, kind, ref_id)
        self._sync_task_text_attachments(cur.lastrowid, title, description)
        return TaskData(
            id=cur.lastrowid,
            day=day,
            time_text=time_text,
            title=title,
            description=description,
            priority=priority,
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
            is_plan_task=is_plan_task,
            plan_order=plan_order,
            marker_color=marker_color,
            marker_theme=marker_theme,
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
    ) -> TaskData:
        """РћР±РЅРѕРІР»СЏРµС‚ Р·Р°РґР°С‡Сѓ."""
        prev_row = self._conn.execute(
            "SELECT priority, board_column, parent_id, is_plan_task, plan_order FROM tasks WHERE id = ?;",
            (task_id,),
        ).fetchone()
        prev_priority = prev_row["priority"] if prev_row else priority
        prev_board_column = prev_row["board_column"] if prev_row else BOARD_COLUMN_QUEUE
        prev_parent_id = prev_row["parent_id"] if prev_row else parent_id
        prev_is_plan_task = bool(prev_row["is_plan_task"]) if prev_row else False
        prev_plan_order = max(0, int(prev_row["plan_order"] or 0)) if prev_row else 0
        title = validate_title(title)
        description = (description or "").strip()
        time_text = validate_time_text(time_text)
        priority = normalize_priority(priority)
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
        if not isinstance(day, date):
            raise ValueError("Р”Р°С‚Р° Р·Р°РґР°С‡Рё РЅРµРєРѕСЂСЂРµРєС‚РЅР°.")

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
        if priority == DEFERRED_PRIORITY:
            board_column = BOARD_COLUMN_DEFERRED
        else:
            board_column = normalize_board_column(prev_board_column, priority)
        with self._conn:
            self._conn.execute(
                """
                UPDATE tasks
                SET title = ?, description = ?, day = ?, time_text = ?, priority = ?, board_column = ?, done = ?, project_id = ?, parent_id = ?,
                    recurrence_kind = ?, recurrence_interval = ?, is_plan_task = ?, plan_order = ?, marker_color = ?, marker_theme = ?, updated_at = ?
                WHERE id = ?;
                """,
                (
                    title,
                    description,
                    day.isoformat(),
                    time_text,
                    priority,
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
        self._sync_task_text_attachments(task_id, title, description)
        return TaskData(
            id=task_id,
            day=day,
            time_text=time_text,
            title=title,
            description=description,
            priority=priority,
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
            is_plan_task=is_plan_task,
            plan_order=plan_order,
            marker_color=marker_color,
            marker_theme=marker_theme,
        )

    def set_task_done(self, task_id: int, done: bool) -> None:
        """РћР±РЅРѕРІР»СЏРµС‚ СЃС‚Р°С‚СѓСЃ РІС‹РїРѕР»РЅРµРЅРёСЏ Р·Р°РґР°С‡Рё."""
        row = self._conn.execute(
            """
            SELECT
                id, title, description, day, time_text, priority, board_column, done, project_id, parent_id,
                recurrence_kind, recurrence_interval, is_plan_task, plan_order, marker_color, marker_theme
            FROM tasks
            WHERE id = ?;
            """,
            (task_id,),
        ).fetchone()
        if row is None:
            return
        prev_done = bool(row["done"])
        recurrence_kind = (row["recurrence_kind"] or "").strip().lower()
        recurrence_interval = max(1, int(row["recurrence_interval"] or 1))
        now_utc = datetime.now(timezone.utc).isoformat(timespec="seconds")
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
        with self._conn:
            if done:
                if is_plan_item:
                    self._conn.execute(
                        """
                        UPDATE tasks
                        SET done = ?, completion_delay_minutes = 0, updated_at = ?
                        WHERE id = ?;
                        """,
                        (
                            int(done),
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
                    SET done = ?, completion_delay_minutes = 0, updated_at = ?
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
                        recurrence_kind, recurrence_interval, is_plan_task, plan_order, marker_color, marker_theme, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        row["title"],
                        row["description"] or "",
                        next_day.isoformat(),
                        row["time_text"] or "",
                        row["priority"],
                        BOARD_COLUMN_DEFERRED if row["priority"] == DEFERRED_PRIORITY else BOARD_COLUMN_QUEUE,
                        row["project_id"],
                        row["parent_id"],
                        recurrence_kind,
                        recurrence_interval,
                        int(bool(row["is_plan_task"])),
                        self._next_task_plan_order(row["parent_id"]),
                        row["marker_color"] or "",
                        row["marker_theme"] or "",
                        now_utc,
                        now_utc,
                    ),
                )
                self._sync_task_text_attachments(cur.lastrowid, row["title"], row["description"] or "")

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
        """Обновляет канбан-колонку задачи без изменения done-статуса."""
        row = self._conn.execute(
            "SELECT priority FROM tasks WHERE id = ?;",
            (task_id,),
        ).fetchone()
        if row is None:
            return
        current_priority = normalize_priority(row["priority"])
        requested_board_column = str(board_column or "").strip().lower()
        if requested_board_column == BOARD_COLUMN_DEFERRED:
            normalized_board_column = BOARD_COLUMN_DEFERRED
        elif requested_board_column in {BOARD_COLUMN_QUEUE, BOARD_COLUMN_IN_PROGRESS, BOARD_COLUMN_COMPLETED}:
            normalized_board_column = requested_board_column
        else:
            normalized_board_column = BOARD_COLUMN_QUEUE
        next_priority = (
            DEFERRED_PRIORITY
            if normalized_board_column == BOARD_COLUMN_DEFERRED
            else ("Medium" if current_priority == DEFERRED_PRIORITY else current_priority)
        )
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                """
                UPDATE tasks
                SET priority = ?, board_column = ?, updated_at = ?
                WHERE id = ?;
                """,
                (next_priority, normalized_board_column, now, task_id),
            )

    def set_task_gantt_estimate(self, task_id: int, minutes: int, forecasted: bool = True) -> None:
        """РЎРѕС…СЂР°РЅСЏРµС‚ РѕС†РµРЅРєСѓ РІСЂРµРјРµРЅРё Р·Р°РґР°С‡Рё РґР»СЏ СЂРµР¶РёРјР° РґРёР°РіСЂР°РјРјС‹ Р“Р°РЅС‚Р°."""
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
        """РЈРґР°Р»СЏРµС‚ Р·Р°РґР°С‡Сѓ РїРѕ id."""
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
        """Р’РѕР·РІСЂР°С‰Р°РµС‚ СЃРїРёСЃРѕРє РІР»РѕР¶РµРЅРёР№ Р·Р°РґР°С‡Рё."""
        task_id = int(task_id)
        rows = self._conn.execute(
            """
            SELECT id, task_id, kind, ref_id, created_at
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
        """Р”РѕР±Р°РІР»СЏРµС‚ РІР»РѕР¶РµРЅРёРµ Рє Р·Р°РґР°С‡Рµ."""
        task_id = int(task_id)
        if task_id <= 0:
            raise ValueError("РРґРµРЅС‚РёС„РёРєР°С‚РѕСЂ Р·Р°РґР°С‡Рё РґРѕР»Р¶РµРЅ Р±С‹С‚СЊ РїРѕР»РѕР¶РёС‚РµР»СЊРЅС‹Рј.")
        ref_id = int(ref_id)
        if ref_id <= 0:
            raise ValueError("РРґРµРЅС‚РёС„РёРєР°С‚РѕСЂ РІР»РѕР¶РµРЅРЅРѕРіРѕ СЌР»РµРјРµРЅС‚Р° РґРѕР»Р¶РµРЅ Р±С‹С‚СЊ РїРѕР»РѕР¶РёС‚РµР»СЊРЅС‹Рј.")
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
            SELECT id, task_id, kind, ref_id, created_at
            FROM task_attachments
            WHERE task_id = ? AND kind = ? AND ref_id = ?;
            """,
            (task_id, kind, ref_id),
        ).fetchone()
        return TaskAttachmentData.from_row(row)

    def delete_task_attachment(self, attachment_id: int) -> None:
        """РЈРґР°Р»СЏРµС‚ РІР»РѕР¶РµРЅРёРµ Р·Р°РґР°С‡Рё."""
        with self._conn:
            self._conn.execute("DELETE FROM task_attachments WHERE id = ?;", (attachment_id,))

__all__ = ["DatabaseTasksMixin"]
