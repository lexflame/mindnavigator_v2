"""TasksModel class module for tasks workspace."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403
from mindnavigator.ui.dialogs.task_dialog_debug import debug_task_dialog
class TasksModel(QAbstractListModel):
    task_moved = Signal(int)

    def __init__(self, parent=None):
        """Создает модель данных задач для списка."""
        super().__init__(parent)
        self._db = get_database()
        self._all_rows: List[Row] = []
        self._rows: List[Row] = []
        self._task_depths: dict[int, int] = {}
        self._task_children: dict[int, List[TaskRow]] = {}
        self._task_is_plan_item: dict[int, bool] = {}
        self._task_plan_branch: dict[int, bool] = {}
        self._task_plan_numbers: dict[int, str] = {}
        self._current_plan_item_ids: set[int] = set()
        self._filter_mode = "Все"      # Все | План | Сегодня | Выполнено | Отложенные
        self._search = ""
        self._focus_day: Optional[date] = None
        self._project_filter_id: Optional[int] = None
        self._priority_filter: Optional[str] = None
        self._sort_key = "priority"  # date | title | priority
        self._sort_asc = True
        self._drag_enabled = False
        self._expanded_task_ids: set[int] = set()
        self._collapsed_subtask_ids: set[int] = set()
        self._subtask_state_initialized: set[int] = set()
        self._reload_from_db()

    def _reload_from_db(self):
        """Обновляет список задач из базы данных."""
        tasks = self._db.fetch_tasks()
        self._all_rows = [self._row_from_task_data(task) for task in tasks]
        self._recompute_plan_meta()
        self._prune_state()
        self._rebuild()

    @staticmethod
    def _row_from_task_data(task: TaskData) -> TaskRow:
        return TaskRow(
            id=task.id,
            day=task.day,
            time_text=task.time_text,
            title=task.title,
            description=task.description,
            priority=task.priority,
            done=task.done,
            board_column=task.board_column,
            project_id=task.project_id,
            project_title=task.project_title,
            project_area=task.project_area,
            parent_id=task.parent_id,
            recurrence_kind=task.recurrence_kind,
            recurrence_interval=task.recurrence_interval,
            completion_delay_minutes=task.completion_delay_minutes,
            started_at=task.started_at,
            finished_at=task.finished_at,
            actual_minutes=task.actual_minutes,
            marker_color=task.marker_color,
            marker_theme=task.marker_theme,
            is_plan_task=task.is_plan_task,
            plan_order=task.plan_order,
        )

    def _recompute_plan_meta(self) -> None:
        by_parent: dict[Optional[int], list[TaskRow]] = {}
        for row in self._all_rows:
            if not isinstance(row, TaskRow):
                continue
            by_parent.setdefault(row.parent_id, []).append(row)

        self._task_is_plan_item = {}
        self._task_plan_branch = {}
        self._task_plan_numbers = {}
        self._current_plan_item_ids = set()

        for row in self._all_rows:
            if not isinstance(row, TaskRow) or not row.is_plan_task:
                continue
            open_children = [
                child for child in by_parent.get(row.id, [])
                if not child.done
            ]
            open_children.sort(key=lambda item: (item.plan_order, item.id))
            if open_children:
                self._current_plan_item_ids.add(open_children[0].id)

        def visit(task: TaskRow, parent_is_plan_task: bool, number_path: list[int]) -> None:
            is_plan_item = parent_is_plan_task
            current_branch_active = bool(task.is_plan_task)
            self._task_is_plan_item[task.id] = is_plan_item
            self._task_plan_branch[task.id] = current_branch_active
            self._task_plan_numbers[task.id] = (
                ".".join(str(part) for part in number_path) + "."
                if is_plan_item and number_path
                else ""
            )

            child_rows = by_parent.get(task.id, [])
            if current_branch_active:
                child_rows = sorted(child_rows, key=lambda item: (item.plan_order, item.id))
            else:
                child_rows = sorted(child_rows, key=lambda item: (item.day, item.time_text or "", item.id))
            for child_index, child in enumerate(child_rows, start=1):
                child_number_path = [child_index] if current_branch_active else []
                visit(child, current_branch_active, child_number_path)

        root_rows = sorted(
            by_parent.get(None, []),
            key=lambda item: (item.day, item.time_text or "", item.id),
        )
        for root in root_rows:
            visit(root, False, [])

    def refresh(self) -> None:
        """Перезагружает данные задач из базы."""
        self._reload_from_db()

    def _prune_state(self) -> None:
        """Очищает локальные состояния раскрытия для удаленных задач."""
        task_ids = {it.id for it in self._all_rows if isinstance(it, TaskRow)}
        self._expanded_task_ids &= task_ids
        self._collapsed_subtask_ids &= task_ids
        self._subtask_state_initialized &= task_ids

    def rowCount(self, parent=QModelIndex()) -> int:
        """Возвращает количество строк с учетом фильтрации."""
        if parent.isValid():
            return 0
        return len(self._rows)

    def data(self, index: QModelIndex, role: int = int(Qt.ItemDataRole.DisplayRole)) -> Any:
        """Отдает данные для делегата в зависимости от роли."""
        if not index.isValid():
            return None
        r = self._rows[index.row()]

        if role == TaskRoles.RowType:
            if isinstance(r, HeaderRow):
                return "header"
            if isinstance(r, SortHeaderRow):
                return "sort_header"
            return "task"

        if isinstance(r, HeaderRow):
            if role == TaskRoles.Day:
                return r.day
            if role == Qt.ItemDataRole.DisplayRole:
                return r.day.isoformat()
            return None

        if isinstance(r, SortHeaderRow):
            if role == TaskRoles.SortKey:
                return self._sort_key
            if role == TaskRoles.SortDirection:
                return "asc" if self._sort_asc else "desc"
            if role == Qt.ItemDataRole.DisplayRole:
                return "sort_header"
            return None

        if role == TaskRoles.TaskId:
            return r.id
        if role == TaskRoles.Day:
            return r.day
        if role == TaskRoles.TimeText:
            return r.time_text
        if role == TaskRoles.DisplayTime:
            return self._display_time_text(r)
        if role == TaskRoles.Title:
            return r.title
        if role == TaskRoles.Description:
            return r.description
        if role == TaskRoles.Priority:
            return r.priority
        if role == TaskRoles.Done:
            return r.done
        if role == TaskRoles.BoardColumn:
            return r.board_column
        if role == TaskRoles.Expanded:
            return r.id in self._expanded_task_ids
        if role == TaskRoles.ProjectTitle:
            return r.project_title
        if role == TaskRoles.ProjectArea:
            return r.project_area
        if role == TaskRoles.HasSubtasks:
            return bool(self._task_children.get(r.id))
        if role == TaskRoles.SubtasksExpanded:
            return r.id not in self._collapsed_subtask_ids
        if role == TaskRoles.SubtaskDepth:
            return self._task_depths.get(r.id, 0)
        if role == TaskRoles.AttachmentSummary:
            return self._attachment_summary(r.id)
        if role == TaskRoles.RecurrenceKind:
            return r.recurrence_kind
        if role == TaskRoles.CompletionDelayMinutes:
            return r.completion_delay_minutes
        if role == TaskRoles.ParentTaskId:
            return r.parent_id
        if role == TaskRoles.IsPlanTask:
            return r.is_plan_task
        if role == TaskRoles.IsPlanItem:
            return self._task_is_plan_item.get(r.id, False)
        if role == TaskRoles.IsCurrentPlanItem:
            return r.id in self._current_plan_item_ids
        if role == TaskRoles.PlanNumber:
            return self._task_plan_numbers.get(r.id, "")
        if role == TaskRoles.PlanOrder:
            return r.plan_order
        if role == TaskRoles.StartedAt:
            return r.started_at
        if role == TaskRoles.FinishedAt:
            return r.finished_at
        if role == TaskRoles.ActualMinutes:
            return r.actual_minutes
        if role == TaskRoles.MarkerColor:
            return r.marker_color
        if role == TaskRoles.MarkerTheme:
            return r.marker_theme
        if role == Qt.ItemDataRole.DisplayRole:
            return format_task_list_title(r.id, r.title)
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        """Задает флаги взаимодействия для строки."""
        if not index.isValid():
            return Qt.ItemFlags(Qt.ItemFlag.NoItemFlags)
        r = self._rows[index.row()]
        if isinstance(r, HeaderRow):
            flags = Qt.ItemFlags(Qt.ItemFlag.ItemIsEnabled)
            if self._drag_enabled:
                flags |= Qt.ItemFlags(Qt.ItemFlag.ItemIsDropEnabled)
            return flags
        if isinstance(r, SortHeaderRow):
            return Qt.ItemFlags(Qt.ItemFlag.ItemIsEnabled)
        flags = Qt.ItemFlags(Qt.ItemFlag.ItemIsEnabled)
        flags |= Qt.ItemFlag.ItemIsSelectable
        if self._drag_enabled:
            flags |= Qt.ItemFlag.ItemIsDragEnabled
            flags |= Qt.ItemFlag.ItemIsDropEnabled
        return flags

    def set_filter_mode(self, mode: str):
        """Устанавливает фильтр по режиму и перестраивает список."""
        self._filter_mode = mode
        self._drag_enabled = (mode == "План")
        self._rebuild()

    def filter_mode(self) -> str:
        """Возвращает текущий режим фильтра."""
        return self._filter_mode

    def set_search(self, text: str):
        """Обновляет строку поиска и перестраивает список."""
        self._search = (text or "").strip().lower()
        self._rebuild()

    def set_focus_day(self, d: Optional[date]):
        """Фиксирует конкретный день для отображения задач."""
        self._focus_day = d
        self._rebuild()

    def set_project_filter(self, project_id: Optional[int]):
        """Устанавливает фильтр по проекту."""
        self._project_filter_id = project_id
        self._rebuild()

    def set_priority_filter(self, priority: Optional[str]):
        """Устанавливает фильтр по приоритету."""
        self._priority_filter = priority
        self._rebuild()

    def add_task(
        self,
        title: str,
        day: date,
        time_text: str,
        priority: str,
        description: str = "",
        project_id: Optional[int] = None,
        parent_id: Optional[int] = None,
        recurrence_kind: str = "",
        recurrence_interval: int = 1,
        is_plan_task: bool = False,
        marker_color: str = "",
        marker_theme: str = "",
    ):
        """Добавляет новую задачу и перестраивает текущий список."""
        task = self._db.create_task(
            title=title,
            description=description,
            day=day,
            time_text=time_text,
            priority=priority,
            project_id=project_id,
            parent_id=parent_id,
            recurrence_kind=recurrence_kind,
            recurrence_interval=recurrence_interval,
            is_plan_task=is_plan_task,
            marker_color=marker_color,
            marker_theme=marker_theme,
        )
        self._all_rows.append(self._row_from_task_data(task))
        self._recompute_plan_meta()
        self._rebuild()
        return task

    def quick_add_subtask(self, parent_task_id: int) -> None:
        parent_task = next(
            (it for it in self._all_rows if isinstance(it, TaskRow) and it.id == parent_task_id),
            None,
        )
        if parent_task is None:
            return
        return self.add_task(
            title="Новая подзадача",
            description="",
            day=parent_task.day,
            time_text=parent_task.time_text,
            priority="Medium" if self._task_plan_branch.get(parent_task.id, False) else (parent_task.priority or "Medium"),
            project_id=parent_task.project_id,
            parent_id=parent_task.id,
            recurrence_kind="",
            recurrence_interval=1,
            marker_color=parent_task.marker_color,
            marker_theme=parent_task.marker_theme,
        )

    def quick_add_task_for_day(self, target_day: date) -> None:
        return self.add_task(
            title="Новая задача",
            description="",
            day=target_day,
            time_text="",
            priority="Medium",
        )

    def set_sort(self, key: str):
        """Устанавливает сортировку для режима «Все»."""
        if key == self._sort_key:
            self._sort_asc = not self._sort_asc
        else:
            self._sort_key = key
            self._sort_asc = True
        self._rebuild()

    def task_at_row(self, row_idx: int) -> Optional[TaskRow]:
        """Возвращает задачу по индексу строки или None."""
        if row_idx < 0 or row_idx >= len(self._rows):
            return None
        r = self._rows[row_idx]
        if isinstance(r, (HeaderRow, SortHeaderRow)):
            return None
        return r

    def row_for_task_id(self, task_id: int) -> int:
        """Возвращает индекс текущей видимой строки задачи или -1."""
        for idx, row in enumerate(self._rows):
            if isinstance(row, TaskRow) and row.id == task_id:
                return idx
        return -1

    @staticmethod
    def _unique_task_ids(task_ids: List[int]) -> List[int]:
        unique_ids: List[int] = []
        seen: set[int] = set()
        for task_id in task_ids:
            if task_id in seen:
                continue
            seen.add(task_id)
            unique_ids.append(task_id)
        return unique_ids

    @staticmethod
    def _task_update_payload(task: TaskRow) -> dict[str, Any]:
        return {
            "title": task.title,
            "description": task.description,
            "day": task.day,
            "time_text": task.time_text,
            "priority": task.priority,
            "done": task.done,
            "project_id": task.project_id,
            "parent_id": task.parent_id,
            "recurrence_kind": task.recurrence_kind,
            "recurrence_interval": task.recurrence_interval,
            "is_plan_task": task.is_plan_task,
            "plan_order": task.plan_order,
            "marker_color": task.marker_color,
            "marker_theme": task.marker_theme,
        }

    def _apply_task_updates_by_ids(self, task_ids: List[int], update_builder) -> int:
        changed = 0
        for task_id in self._unique_task_ids(task_ids):
            task = self.task_by_id(task_id)
            if task is None:
                continue
            changes = update_builder(task)
            if not changes:
                continue
            payload = self._task_update_payload(task)
            payload.update(changes)
            self._db.update_task(task_id=task.id, **payload)
            changed += 1
        if changed:
            self._reload_from_db()
        return changed

    def update_task_by_row(
        self,
        row_idx: int,
        title: str,
        description: str,
        day: date,
        time_text: str,
        priority: str,
        done: bool,
        project_id: Optional[int],
        recurrence_kind: str,
        recurrence_interval: int,
        gantt_estimate_minutes: Optional[int] = None,
        is_plan_task: Optional[bool] = None,
        marker_color: str = "",
        marker_theme: str = "",
    ):
        """Обновляет задачу по индексу строки."""
        r = self.task_at_row(row_idx)
        if r is None:
            debug_task_dialog(f"tasks_model update_task_by_row skipped_invalid_row row={row_idx}")
            return
        resolved_project_id = project_id
        if self._task_is_plan_item.get(r.id, False):
            resolved_project_id = self._inherited_project_id_for_plan_item(r)
        debug_task_dialog(
            f"tasks_model update_task_by_row start row={row_idx} task_id={r.id} "
            f"from_day={r.day.isoformat()} to_day={day.isoformat()} "
            f"title={title!r} time={time_text!r} priority={priority!r} done={done}"
        )
        updated = self._db.update_task(
            task_id=r.id,
            title=title,
            description=description,
            day=day,
            time_text=time_text,
            priority=priority,
            done=done,
            project_id=resolved_project_id,
            parent_id=r.parent_id,
            recurrence_kind=recurrence_kind,
            recurrence_interval=recurrence_interval,
            is_plan_task=r.is_plan_task if is_plan_task is None else bool(is_plan_task),
            plan_order=r.plan_order,
            marker_color=marker_color,
            marker_theme=marker_theme,
        )
        if gantt_estimate_minutes is not None:
            self._db.set_task_gantt_estimate(updated.id, gantt_estimate_minutes, forecasted=True)
        debug_task_dialog(
            f"tasks_model update_task_by_row db_result task_id={updated.id} "
            f"day={updated.day.isoformat()} time={updated.time_text!r} "
            f"priority={updated.priority!r} done={updated.done}"
        )
        priority_changed = r.priority != updated.priority
        cascade_needed = (
            (r.priority == "Отложенная" and updated.priority != "Отложенная")
            or (r.priority != "Отложенная" and updated.priority == "Отложенная")
        )
        if priority_changed and cascade_needed:
            debug_task_dialog(
                f"tasks_model update_task_by_row reload_for_cascade task_id={updated.id}"
            )
            self._reload_from_db()
            return

        updated_row = self._row_from_task_data(updated)
        self._all_rows = [
            updated_row if isinstance(it, TaskRow) and it.id == r.id else it
            for it in self._all_rows
        ]
        self._recompute_plan_meta()
        if updated.is_plan_task and (updated.project_id != r.project_id or not r.is_plan_task):
            if self._sync_plan_descendant_projects(updated.id, updated.project_id):
                debug_task_dialog(
                    f"tasks_model update_task_by_row sync_plan_projects task_id={updated.id} project_id={updated.project_id}"
                )
                return

        if is_marker_only_task_update(r, updated_row):
            changed_row_idx = -1
            new_rows: List[Row] = []
            for idx, it in enumerate(self._rows):
                if isinstance(it, TaskRow) and it.id == r.id:
                    changed_row_idx = idx
                    new_rows.append(updated_row)
                else:
                    new_rows.append(it)
            self._rows = new_rows
            if changed_row_idx >= 0:
                idx = self.index(changed_row_idx, 0)
                if idx.isValid():
                    self.dataChanged.emit(
                        idx,
                        idx,
                        [
                            TaskRoles.MarkerColor,
                            TaskRoles.MarkerTheme,
                            TaskRoles.ProjectTitle,
                            Qt.ItemDataRole.DisplayRole,
                        ],
                    )
                    debug_task_dialog(
                        f"tasks_model update_task_by_row marker_only_refresh task_id={updated.id} row={changed_row_idx}"
                    )
                    return
        debug_task_dialog(f"tasks_model update_task_by_row rebuild task_id={updated.id}")
        self._rebuild()

    def toggle_done_by_row(self, row_idx: int):
        """Переключает статус выполнения задачи по индексу строки."""
        if row_idx < 0 or row_idx >= len(self._rows):
            return
        r = self._rows[row_idx]
        if isinstance(r, (HeaderRow, SortHeaderRow)):
            return

        new_done = not r.done
        self._db.set_task_done(r.id, new_done)
        self._reload_from_db()

    def cycle_priority_by_row(self, row_idx: int) -> None:
        """Циклически переключает приоритет задачи в строке."""
        task = self.task_at_row(row_idx)
        if task is None:
            return
        cycle = ["Low", "Medium", "High", "Отложенная"]
        if self._task_is_plan_item.get(task.id, False):
            return
        try:
            current_index = cycle.index(task.priority)
        except ValueError:
            current_index = 1
        next_priority = cycle[(current_index + 1) % len(cycle)]
        self.update_task_by_row(
            row_idx,
            title=task.title,
            description=task.description,
            day=task.day,
            time_text=task.time_text,
            priority=next_priority,
            done=task.done,
            project_id=task.project_id,
            recurrence_kind=task.recurrence_kind,
            recurrence_interval=task.recurrence_interval,
            marker_color=task.marker_color,
            marker_theme=task.marker_theme,
        )

    def step_priority_by_row(self, row_idx: int, direction: int) -> None:
        """Сдвигает приоритет вверх или вниз без циклического перехода."""
        task = self.task_at_row(row_idx)
        if task is None:
            return
        ordered_priorities = ["Отложенная", "Low", "Medium", "High"]
        if self._task_is_plan_item.get(task.id, False):
            return
        try:
            current_index = ordered_priorities.index(task.priority)
        except ValueError:
            current_index = ordered_priorities.index("Medium")
        next_index = max(0, min(len(ordered_priorities) - 1, current_index + int(direction)))
        next_priority = ordered_priorities[next_index]
        if next_priority == task.priority:
            return
        self.update_task_by_row(
            row_idx,
            title=task.title,
            description=task.description,
            day=task.day,
            time_text=task.time_text,
            priority=next_priority,
            done=task.done,
            project_id=task.project_id,
            recurrence_kind=task.recurrence_kind,
            recurrence_interval=task.recurrence_interval,
            marker_color=task.marker_color,
            marker_theme=task.marker_theme,
        )

    def can_step_plan_item_order(self, task_id: int, direction: int) -> bool:
        task = self.task_by_id(task_id)
        if task is None or not self._task_is_plan_item.get(task.id, False):
            return False
        siblings = self._plan_sibling_rows(task.parent_id)
        sibling_ids = [sibling.id for sibling in siblings]
        try:
            current_index = sibling_ids.index(task.id)
        except ValueError:
            return False
        next_index = current_index + int(direction)
        return 0 <= next_index < len(sibling_ids)

    def step_plan_item_order_by_row(self, row_idx: int, direction: int) -> None:
        task = self.task_at_row(row_idx)
        if task is None or not self._task_is_plan_item.get(task.id, False):
            return
        siblings = self._plan_sibling_rows(task.parent_id)
        sibling_ids = [sibling.id for sibling in siblings]
        try:
            current_index = sibling_ids.index(task.id)
        except ValueError:
            return
        next_index = current_index + int(direction)
        if next_index < 0 or next_index >= len(sibling_ids):
            return
        sibling_ids[current_index], sibling_ids[next_index] = sibling_ids[next_index], sibling_ids[current_index]
        self._db.reorder_task_siblings(task.parent_id, sibling_ids)
        self._reload_from_db()
        self.task_moved.emit(task.id)

    def step_board_column_by_row(self, row_idx: int, direction: int) -> None:
        """Сдвигает стадию BOARD вперед или назад без циклического перехода."""
        task = self.task_at_row(row_idx)
        if task is None:
            return
        ordered_columns = [
            BOARD_COLUMN_DEFERRED,
            BOARD_COLUMN_QUEUE,
            BOARD_COLUMN_IN_PROGRESS,
            BOARD_COLUMN_COMPLETED,
        ]
        current_column = normalize_board_column(task.board_column, task.priority)
        try:
            current_index = ordered_columns.index(current_column)
        except ValueError:
            current_index = ordered_columns.index(BOARD_COLUMN_QUEUE)
        next_index = max(0, min(len(ordered_columns) - 1, current_index + int(direction)))
        next_column = ordered_columns[next_index]
        if next_column == current_column:
            return
        self._db.set_task_board_column(task.id, next_column)
        self._reload_from_db()

    def delete_task_by_row(self, row_idx: int):
        """Удаляет задачу по индексу строки."""
        if row_idx < 0 or row_idx >= len(self._rows):
            return
        r = self._rows[row_idx]
        if isinstance(r, (HeaderRow, SortHeaderRow)):
            return

        self._db.delete_task(r.id)
        self._reload_from_db()

    def set_done_by_ids(self, task_ids: List[int], done: bool) -> int:
        changed = 0
        for task_id in self._unique_task_ids(task_ids):
            task = self.task_by_id(task_id)
            if task is None or task.done == done:
                continue
            self._db.set_task_done(task.id, done)
            changed += 1
        if changed:
            self._reload_from_db()
        return changed

    def delete_tasks_by_ids(self, task_ids: List[int]) -> int:
        changed = 0
        for task_id in self._unique_task_ids(task_ids):
            task = self.task_by_id(task_id)
            if task is None:
                continue
            self._db.delete_task(task.id)
            changed += 1
        if changed:
            self._reload_from_db()
        return changed

    def move_tasks_to_day_by_ids(self, task_ids: List[int], new_day: date) -> int:
        return self._apply_task_updates_by_ids(
            task_ids,
            lambda task: None if task.day == new_day else {"day": new_day},
        )

    def move_tasks_to_tomorrow_by_ids(self, task_ids: List[int]) -> int:
        return self._apply_task_updates_by_ids(
            task_ids,
            lambda task: {"day": self.next_day_for_task(task)},
        )

    def step_priority_by_ids(self, task_ids: List[int], direction: int) -> int:
        ordered_priorities = [DEFERRED_PRIORITY, "Low", "Medium", "High"]

        def update_builder(task: TaskRow) -> Optional[dict[str, Any]]:
            if self._task_is_plan_item.get(task.id, False):
                return None
            try:
                current_index = ordered_priorities.index(task.priority)
            except ValueError:
                current_index = ordered_priorities.index("Medium")
            next_index = max(0, min(len(ordered_priorities) - 1, current_index + int(direction)))
            next_priority = ordered_priorities[next_index]
            if next_priority == task.priority:
                return None
            return {"priority": next_priority}

        return self._apply_task_updates_by_ids(task_ids, update_builder)

    def set_priority_by_ids(self, task_ids: List[int], priority: str) -> int:
        normalized_priority = normalize_priority(priority)
        return self._apply_task_updates_by_ids(
            task_ids,
            lambda task: None if self._task_is_plan_item.get(task.id, False) or task.priority == normalized_priority else {"priority": normalized_priority},
        )

    def set_project_by_ids(self, task_ids: List[int], project_id: Optional[int]) -> int:
        return self._apply_task_updates_by_ids(
            task_ids,
            lambda task: None if self._task_is_plan_item.get(task.id, False) or task.project_id == project_id else {"project_id": project_id},
        )

    def set_marker_color_by_ids(self, task_ids: List[int], marker_color: str) -> int:
        normalized_color = (marker_color or "").strip()
        return self._apply_task_updates_by_ids(
            task_ids,
            lambda task: None if (task.marker_color or "").strip() == normalized_color else {"marker_color": normalized_color},
        )

    def set_marker_theme_by_ids(self, task_ids: List[int], marker_theme: str) -> int:
        normalized_theme = (marker_theme or "").strip().lower()
        return self._apply_task_updates_by_ids(
            task_ids,
            lambda task: None if (task.marker_theme or "").strip().lower() == normalized_theme else {"marker_theme": normalized_theme},
        )

    def move_task_to_day(self, task_id: int, new_day: date, parent_id=_PARENT_UNSET) -> bool:
        """Переносит задачу на новую дату."""
        task = next((it for it in self._all_rows if isinstance(it, TaskRow) and it.id == task_id), None)
        if task is None:
            return False
        if self._task_is_plan_item.get(task.id, False):
            return False
        if task.day == new_day and parent_id is _PARENT_UNSET:
            return False

        current_parent_id = task.parent_id if parent_id is _PARENT_UNSET else parent_id
        updated = self._db.update_task(
            task_id=task.id,
            title=task.title,
            description=task.description,
            day=new_day,
            time_text=task.time_text,
            priority=task.priority,
            done=task.done,
            project_id=task.project_id,
            parent_id=current_parent_id,
            recurrence_kind=task.recurrence_kind,
            recurrence_interval=task.recurrence_interval,
            is_plan_task=task.is_plan_task,
            plan_order=task.plan_order,
            marker_color=task.marker_color,
            marker_theme=task.marker_theme,
        )
        new_all: List[Row] = []
        for it in self._all_rows:
            if isinstance(it, TaskRow) and it.id == task.id:
                it = self._row_from_task_data(updated)
            new_all.append(it)
        self._all_rows = new_all
        self._recompute_plan_meta()
        self._rebuild()
        self.task_moved.emit(task.id)
        return True

    def next_day_for_task(self, task: TaskRow) -> date:
        """Возвращает дату для переноса задачи на следующий рабочий день."""
        target = task.day + timedelta(days=1)
        if target.weekday() == 5:
            target += timedelta(days=2)
        elif target.weekday() == 6:
            target += timedelta(days=6)

        if self._tasks_count_on_day(target, exclude_task_id=task.id) > 4:
            target += timedelta(days=1)
        return target

    def move_task_to_parent(self, task_id: int, parent_id: Optional[int]) -> bool:
        """Переносит задачу в подзадачу или возвращает в корень."""
        task = next((it for it in self._all_rows if isinstance(it, TaskRow) and it.id == task_id), None)
        if task is None:
            return False
        if parent_id == task.id:
            return False
        if self._task_is_plan_item.get(task.id, False) and parent_id != task.parent_id:
            return False

        target_project_id = task.project_id
        if parent_id is not None:
            parent_task = next(
                (it for it in self._all_rows if isinstance(it, TaskRow) and it.id == parent_id),
                None,
            )
            if parent_task is None:
                return False
            if self._is_descendant(parent_id, task.id):
                return False
            target_project_id = self._resolve_top_parent_project_id(parent_task)

        updated = self._db.update_task(
            task_id=task.id,
            title=task.title,
            description=task.description,
            day=task.day,
            time_text=task.time_text,
            priority=task.priority,
            done=task.done,
            project_id=target_project_id,
            parent_id=parent_id,
            recurrence_kind=task.recurrence_kind,
            recurrence_interval=task.recurrence_interval,
            is_plan_task=task.is_plan_task,
            marker_color=task.marker_color,
            marker_theme=task.marker_theme,
        )
        new_all: List[Row] = []
        for it in self._all_rows:
            if isinstance(it, TaskRow) and it.id == task.id:
                it = self._row_from_task_data(updated)
            new_all.append(it)
        self._all_rows = new_all
        self._recompute_plan_meta()
        self._rebuild()
        self.task_moved.emit(task.id)
        return True

    def task_by_id(self, task_id: int) -> Optional[TaskRow]:
        """Возвращает задачу по идентификатору или None."""
        return next((it for it in self._all_rows if isinstance(it, TaskRow) and it.id == task_id), None)

    def _inherited_project_id_for_plan_item(self, task: TaskRow) -> Optional[int]:
        if not self._task_is_plan_item.get(task.id, False):
            return task.project_id
        if task.parent_id is None:
            return task.project_id
        parent_task = self.task_by_id(task.parent_id)
        if parent_task is None:
            return task.project_id
        return self._resolve_top_parent_project_id(parent_task)

    def _plan_descendant_ids(self, parent_task_id: int) -> List[int]:
        by_parent: dict[Optional[int], List[TaskRow]] = {}
        for row in self._all_rows:
            if not isinstance(row, TaskRow):
                continue
            by_parent.setdefault(row.parent_id, []).append(row)
        descendant_ids: List[int] = []
        stack = list(by_parent.get(parent_task_id, []))
        while stack:
            child = stack.pop()
            stack.extend(by_parent.get(child.id, []))
            if self._task_is_plan_item.get(child.id, False):
                descendant_ids.append(child.id)
        return descendant_ids

    def _sync_plan_descendant_projects(self, parent_task_id: int, project_id: Optional[int]) -> bool:
        descendant_ids = self._plan_descendant_ids(parent_task_id)
        if not descendant_ids:
            return False
        changed = self._apply_task_updates_by_ids(
            descendant_ids,
            lambda task: None if task.project_id == project_id else {"project_id": project_id},
        )
        return changed > 0

    def is_plan_item(self, task_id: int) -> bool:
        return self._task_is_plan_item.get(task_id, False)

    def plan_number(self, task_id: int) -> str:
        return self._task_plan_numbers.get(task_id, "")

    def _resolve_top_parent_project_id(self, parent_task: TaskRow) -> Optional[int]:
        """Возвращает project_id верхнего родителя в цепочке parent_id."""
        by_id = {it.id: it for it in self._all_rows if isinstance(it, TaskRow)}
        current = parent_task
        seen: set[int] = set()
        while current.parent_id is not None and current.parent_id in by_id and current.id not in seen:
            seen.add(current.id)
            current = by_id[current.parent_id]
        return current.project_id

    def move_task_to_parent_schedule(self, task_id: int, parent_task_id: int) -> bool:
        """Переносит задачу на дату и время родительской задачи."""
        task = self.task_by_id(task_id)
        parent_task = self.task_by_id(parent_task_id)
        if task is None or parent_task is None:
            return False
        if task.id == parent_task.id:
            return False
        if task.day == parent_task.day and task.time_text == parent_task.time_text:
            return False

        updated = self._db.update_task(
            task_id=task.id,
            title=task.title,
            description=task.description,
            day=parent_task.day,
            time_text=parent_task.time_text,
            priority=task.priority,
            done=task.done,
            project_id=task.project_id,
            parent_id=task.parent_id,
            recurrence_kind=task.recurrence_kind,
            recurrence_interval=task.recurrence_interval,
            is_plan_task=task.is_plan_task,
            plan_order=task.plan_order,
            marker_color=task.marker_color,
            marker_theme=task.marker_theme,
        )
        new_all: List[Row] = []
        for it in self._all_rows:
            if isinstance(it, TaskRow) and it.id == task.id:
                it = self._row_from_task_data(updated)
            new_all.append(it)
        self._all_rows = new_all
        self._recompute_plan_meta()
        self._rebuild()
        self.task_moved.emit(task.id)
        return True

    def _is_descendant(self, task_id: int, ancestor_id: int) -> bool:
        """Проверяет, является ли задача потомком другой."""
        parent_map = {
            it.id: it.parent_id for it in self._all_rows if isinstance(it, TaskRow)
        }
        current = parent_map.get(task_id)
        while current is not None:
            if current == ancestor_id:
                return True
            current = parent_map.get(current)
        return False

    def _tasks_count_on_day(self, day_value: date, exclude_task_id: Optional[int] = None) -> int:
        """Считает количество невыполненных задач на конкретный день."""
        count = 0
        for it in self._all_rows:
            if not isinstance(it, TaskRow):
                continue
            if exclude_task_id is not None and it.id == exclude_task_id:
                continue
            if it.day == day_value and not it.done:
                count += 1
        return count

    def _rebuild(self):
        """Перестраивает список задач с учетом фильтров и поиска."""
        today = date.today()

        def is_today(d: date) -> bool:
            """Проверяет, соответствует ли дата сегодняшнему дню."""
            return d == today

        search = self._search
        all_tasks_by_id = {
            it.id: it for it in self._all_rows if isinstance(it, TaskRow)
        }

        def keep_done_plan_item(task_item: TaskRow) -> bool:
            if not task_item.done:
                return False
            if not self._task_is_plan_item.get(task_item.id, False):
                return False
            parent_task = all_tasks_by_id.get(task_item.parent_id)
            return parent_task is not None and not parent_task.done

        def has_done_plan_ancestor(task_item: TaskRow) -> bool:
            current_parent_id = task_item.parent_id
            seen: set[int] = set()
            while current_parent_id is not None and current_parent_id not in seen:
                seen.add(current_parent_id)
                parent_task = all_tasks_by_id.get(current_parent_id)
                if parent_task is None:
                    return False
                if parent_task.done:
                    return True
                current_parent_id = parent_task.parent_id
            return False

        base_tasks: List[TaskRow] = []
        search_hits: set[int] = set()
        for it in self._all_rows:
            if not isinstance(it, TaskRow):
                continue

            if self._focus_day is not None and it.day != self._focus_day:
                continue

            if self._project_filter_id is not None and it.project_id != self._project_filter_id:
                continue

            if self._priority_filter is not None and (
                self._task_is_plan_item.get(it.id, False) or it.priority != self._priority_filter
            ):
                continue

            if self._filter_mode == "Сегодня":
                if not is_today(it.day):
                    continue
                if it.done and not keep_done_plan_item(it):
                    continue
                if it.priority == "Отложенная":
                    continue
            elif self._filter_mode == "Все":
                if it.done and not keep_done_plan_item(it):
                    continue
                if it.priority == "Отложенная":
                    continue
            elif self._filter_mode == "Выполнено":
                if not it.done:
                    continue
                if it.priority == "Отложенная":
                    continue
            elif self._filter_mode == "План":
                if it.done and not keep_done_plan_item(it):
                    continue
                if (
                    it.priority == "Отложенная"
                    and not it.is_plan_task
                    and not self._task_is_plan_item.get(it.id, False)
                ):
                    continue
            elif self._filter_mode == "Отложенные":
                if it.priority != "Отложенная":
                    continue

            base_tasks.append(it)
            if not search or search in it.title.lower():
                search_hits.add(it.id)

        def time_key(t: str):
            """Преобразует строку времени в ключ сортировки."""
            try:
                return datetime.strptime(t, "%H:%M").time()
            except ValueError:
                return datetime.min.time()

        priority_order = {"high": 0, "medium": 1, "low": 2, "отложенная": 3}

        def sort_key(task_item: TaskRow):
            if self._sort_key == "title":
                return task_item.title.lower(), task_item.day, time_key(task_item.time_text), task_item.id
            if self._sort_key == "priority":
                if self._filter_mode == "Все":
                    return (
                        priority_order.get(task_item.priority.lower(), 4),
                        task_item.day,
                        time_key(task_item.time_text),
                        task_item.id,
                    )
                return (
                    task_item.day,
                    priority_order.get(task_item.priority.lower(), 4),
                    time_key(task_item.time_text),
                    task_item.id,
                )
            return task_item.day, time_key(task_item.time_text), task_item.id

        task_ids = {t.id for t in base_tasks}
        children_map: dict[Optional[int], List[TaskRow]] = {}
        for base_task in base_tasks:
            parent_id = base_task.parent_id if base_task.parent_id in task_ids else None
            children_map.setdefault(parent_id, []).append(base_task)
        for parent_id, parent_children in children_map.items():
            if parent_id is None or not parent_children:
                continue
            if parent_id not in self._subtask_state_initialized:
                if self._filter_mode != "Сегодня":
                    self._collapsed_subtask_ids.add(parent_id)
                self._subtask_state_initialized.add(parent_id)

        include_cache: dict[int, bool] = {}

        def should_include(task_item: TaskRow) -> bool:
            if not search:
                return True
            cached = include_cache.get(task_item.id)
            if cached is not None:
                return cached
            if task_item.id in search_hits:
                include_cache[task_item.id] = True
                return True
            for child in children_map.get(task_item.id, []):
                if should_include(child):
                    include_cache[task_item.id] = True
                    return True
            include_cache[task_item.id] = False
            return False

        def sorted_children(task_item: TaskRow) -> List[TaskRow]:
            children = [child for child in children_map.get(task_item.id, []) if should_include(child)]
            children.sort(key=sort_key, reverse=(self._filter_mode == "Все" and not self._sort_asc))
            if self._task_plan_branch.get(task_item.id, False):
                children.sort(key=lambda child: (child.plan_order, child.id))
            return children

        new_rows: List[Row] = []
        self._task_children = {}
        self._task_depths = {}

        def append_task(task_item: TaskRow, depth: int) -> None:
            self._task_depths[task_item.id] = depth
            child_rows = sorted_children(task_item)
            if child_rows:
                self._task_children[task_item.id] = child_rows
            new_rows.append(task_item)
            if task_item.id in self._collapsed_subtask_ids and not is_today(task_item.day):
                return
            for child in child_rows:
                append_task(child, depth + 1)

        if self._filter_mode == "Все":
            new_rows.append(SortHeaderRow())
            roots = [t for t in children_map.get(None, []) if should_include(t)]
            roots.sort(key=sort_key, reverse=not self._sort_asc)
            for root_task in roots:
                append_task(root_task, 0)
        else:
            current_day: Optional[date] = None
            roots = [t for t in children_map.get(None, []) if should_include(t)]
            roots.sort(key=sort_key)
            if self._filter_mode == "Выполнено":
                # Показываем свежие завершенные дни сверху, сохраняя порядок задач внутри дня.
                roots.sort(key=lambda task_item: task_item.day, reverse=True)
            for root_task in roots:
                if current_day != root_task.day:
                    current_day = root_task.day
                    new_rows.append(HeaderRow(current_day))
                append_task(root_task, 0)

        self.beginResetModel()
        self._rows = new_rows
        self.endResetModel()

    def _display_time_text(self, task: TaskRow) -> str:
        """Формирует отображаемое время с учетом режима."""
        if self._filter_mode == "Все":
            if task.time_text:
                return f"{task.time_text} · {task.day.isoformat()}"
            return task.day.isoformat()
        return task.time_text

    def _attachment_summary(self, task_id: int) -> List[str]:
        attachments = self._db.fetch_task_attachments(task_id)
        if not attachments:
            return []
        counts: Dict[str, int] = {}
        for attachment in attachments:
            counts[attachment.kind] = counts.get(attachment.kind, 0) + 1
        ordered = [kind for kind in ATTACHMENT_KIND_ORDER if kind in counts]
        ordered.extend(kind for kind in counts.keys() if kind not in ATTACHMENT_KIND_ORDER)
        summary = []
        for kind in ordered:
            label = attachment_kind_label(kind)
            count = counts[kind]
            if count > 1:
                summary.append(f"{label} ×{count}")
            else:
                summary.append(label)
        return summary

    def toggle_expanded_by_row(self, row_idx: int) -> None:
        """Переключает раскрытие задачи по индексу строки."""
        task = self.task_at_row(row_idx)
        if task is None:
            return
        if task.id in self._expanded_task_ids:
            self._expanded_task_ids.remove(task.id)
        else:
            self._expanded_task_ids.add(task.id)
        idx = self.index(row_idx)
        if idx.isValid():
            self.dataChanged.emit(idx, idx, [TaskRoles.Expanded, Qt.ItemDataRole.SizeHintRole])

    def toggle_subtasks_expanded_by_row(self, row_idx: int) -> None:
        """Переключает раскрытие списка подзадач."""
        task = self.task_at_row(row_idx)
        if task is None:
            return
        if task.id in self._collapsed_subtask_ids:
            self._collapsed_subtask_ids.remove(task.id)
        else:
            self._collapsed_subtask_ids.add(task.id)
        self._rebuild()

    def expand_subtasks_tree_by_row(self, row_idx: int) -> None:
        """?????????? ??? ????????? ????????? ??? ????????? ??????."""
        task = self.task_at_row(row_idx)
        if task is None:
            return
        by_parent: dict[Optional[int], list[int]] = {}
        for item in self._all_rows:
            if isinstance(item, TaskRow):
                by_parent.setdefault(item.parent_id, []).append(item.id)

        to_expand: set[int] = {task.id}
        stack = list(by_parent.get(task.id, []))
        while stack:
            current_id = stack.pop()
            if current_id in to_expand:
                continue
            to_expand.add(current_id)
            stack.extend(by_parent.get(current_id, []))

        changed = False
        for task_id in to_expand:
            if task_id in self._collapsed_subtask_ids:
                self._collapsed_subtask_ids.remove(task_id)
                changed = True
        if changed:
            self._rebuild()


    def _plan_sibling_rows(self, parent_id: Optional[int]) -> List[TaskRow]:
        siblings = [
            it for it in self._all_rows
            if isinstance(it, TaskRow) and it.parent_id == parent_id
        ]
        siblings.sort(key=lambda item: (item.plan_order, item.id))
        return siblings

    def reorder_plan_task_before(self, task_id: int, target_task_id: int) -> bool:
        task = self.task_by_id(task_id)
        target_task = self.task_by_id(target_task_id)
        if task is None or target_task is None:
            return False
        if task.id == target_task.id:
            return False
        if task.parent_id != target_task.parent_id:
            return False
        sibling_ids = [
            sibling.id for sibling in self._plan_sibling_rows(task.parent_id)
            if sibling.id != task.id
        ]
        try:
            insert_index = sibling_ids.index(target_task.id)
        except ValueError:
            return False
        sibling_ids.insert(insert_index, task.id)
        self._db.reorder_task_siblings(task.parent_id, sibling_ids)
        self._reload_from_db()
        self.task_moved.emit(task.id)
        return True

    def mimeTypes(self) -> List[str]:
        """Возвращает поддерживаемые типы данных для drag and drop."""
        return ["application/x-mindnavigator-task-id"]

    def mimeData(self, indexes) -> QMimeData:
        """Создает mime-данные для перетаскивания задачи."""
        mime_data = QMimeData()
        if not indexes:
            return mime_data
        idx = indexes[0]
        task = self.task_at_row(idx.row())
        if task is None:
            return mime_data
        mime_data.setData("application/x-mindnavigator-task-id", str(task.id).encode("utf-8"))
        return mime_data

    def supportedDropActions(self) -> Qt.DropAction:
        """Разрешает перенос с изменением позиции."""
        return Qt.DropAction.MoveAction

    def dropMimeData(self, data, action, row, column, parent) -> bool:
        """Обрабатывает перенос задачи между днями."""
        if action == Qt.DropAction.IgnoreAction:
            return True
        if not self._drag_enabled:
            return False
        if not data.hasFormat("application/x-mindnavigator-task-id"):
            return False

        task_id_bytes = data.data("application/x-mindnavigator-task-id")
        try:
            task_id_payload = bytes(task_id_bytes.data())
            task_id = int(task_id_payload.decode("utf-8"))
        except ValueError:
            return False

        target_row = row
        if target_row < 0 and parent.isValid():
            target_row = parent.row()
        if target_row < 0:
            target_row = len(self._rows) - 1

        if target_row < 0 or target_row >= len(self._rows):
            return False

        dragged_task = self.task_by_id(task_id)
        if dragged_task is None:
            return False
        target_item = self._rows[target_row]
        if self._task_is_plan_item.get(task_id, False):
            if not isinstance(target_item, TaskRow):
                return False
            if target_item.parent_id != dragged_task.parent_id:
                return False
            return self.reorder_plan_task_before(task_id, target_item.id)
        if isinstance(target_item, TaskRow):
            return self.move_task_to_parent(task_id, target_item.id)
        if isinstance(target_item, HeaderRow):
            return self.move_task_to_day(task_id, target_item.day, parent_id=None)

        target_day = self._drop_target_day(target_row)
        if target_day is None:
            return False

        return self.move_task_to_day(task_id, target_day, parent_id=None)

    def _drop_target_day(self, row_idx: int) -> Optional[date]:
        """Определяет дату для переноса по позиции drop."""
        if not self._rows:
            return None
        if row_idx >= len(self._rows):
            row_idx = len(self._rows) - 1

        for idx in range(row_idx, -1, -1):
            r = self._rows[idx]
            if isinstance(r, HeaderRow):
                return r.day
            if isinstance(r, TaskRow):
                return r.day
        return None

__all__ = ["TasksModel"]
