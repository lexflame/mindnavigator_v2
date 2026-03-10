"""ProjectsModel class module for projects workspace."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403
from .repository_probe import RepositoryProbe

class ProjectsModel(QAbstractListModel):
    def __init__(self, parent=None):
        """Создает модель данных проектов."""
        super().__init__(parent)
        self._db = get_database()
        self._all_rows: List[Row] = []
        self._rows: List[Row] = []
        self._project_title_cache: Dict[int, str] = {}
        self._project_depth_cache: Dict[int, int] = {}
        self._project_has_children_cache: Dict[int, bool] = {}
        self._project_attachment_summary: Dict[int, List[tuple[str, int]]] = {}
        self._attachment_summary_dirty = True
        self._repository_probe = RepositoryProbe()
        self._collapsed_project_ids: set[int] = set()
        self._collapsed_state_key = "projects_workspace.collapsed_ids"
        self._load_collapsed_state()
        self._filter_mode = "Все"      # Все | Активные | Архив
        self._search = ""
        self._area_focus: Optional[str] = None
        self._task_filter_id: Optional[int] = None
        self._priority_filter: Optional[str] = None
        self._reload_from_db()

    def _reload_from_db(self):
        """Обновляет список проектов из базы данных."""
        projects = self._db.fetch_projects()
        self._all_rows = [
            ProjectRow(
                p.id,
                p.area,
                p.title,
                p.updated,
                p.priority,
                p.archived,
                p.parent_project_id,
                p.default_task_priority,
                p.force_recurrence_kind,
                p.linked_map_id,
                p.linked_note_id,
                p.linked_object_id,
                p.marker_color,
                p.marker_theme,
                p.repository_catalog,
            )
            for p in projects
        ]
        valid_ids = {p.id for p in projects}
        before = set(self._collapsed_project_ids)
        self._collapsed_project_ids = {pid for pid in self._collapsed_project_ids if pid in valid_ids}
        if before != self._collapsed_project_ids:
            self._save_collapsed_state()
        self._attachment_summary_dirty = True
        self._rebuild()

    def refresh(self) -> None:
        """Перезагружает данные проектов из базы."""
        self._reload_from_db()

    def rowCount(self, parent=QModelIndex()) -> int:
        """Возвращает количество строк в модели."""
        if parent.isValid():
            return 0
        return len(self._rows)

    def data(
        self,
        index: QModelIndex,
        role: int = int(Qt.ItemDataRole.DisplayRole),
    ) -> Any:
        """Отдает данные для делегата по ролям."""
        if not index.isValid():
            return None
        r = self._rows[index.row()]

        if role == ProjectRoles.RowType:
            return "header" if isinstance(r, HeaderRow) else "project"

        if isinstance(r, HeaderRow):
            if role == ProjectRoles.Area:
                return r.area
            if role == Qt.ItemDataRole.DisplayRole:
                return r.area
            return None

        if role == ProjectRoles.ProjectId:
            return r.id
        if role == ProjectRoles.Area:
            return r.area
        if role == ProjectRoles.Title:
            return r.title
        if role == ProjectRoles.Updated:
            return format_project_date(r.updated)
        if role == ProjectRoles.UpdatedDate:
            return r.updated
        if role == ProjectRoles.Priority:
            return r.priority
        if role == ProjectRoles.Archived:
            return r.archived
        if role == ProjectRoles.Depth:
            return self._project_depth_cache.get(r.id, 0)
        if role == ProjectRoles.HasChildren:
            return self._project_has_children_cache.get(r.id, False)
        if role == ProjectRoles.IsCollapsed:
            return r.id in self._collapsed_project_ids
        if role == ProjectRoles.MarkerColor:
            return r.marker_color
        if role == ProjectRoles.MarkerTheme:
            return r.marker_theme
        if role == ProjectRoles.AttachmentSummary:
            return self._project_attachment_summary.get(r.id, [])
        if role == ProjectRoles.RepositoryCatalog:
            return r.repository_catalog
        if role == Qt.ItemDataRole.DisplayRole:
            return r.title
        return None

    def toggle_project_collapsed(self, project_id: int) -> None:
        if project_id in self._collapsed_project_ids:
            self._collapsed_project_ids.remove(project_id)
        else:
            self._collapsed_project_ids.add(project_id)
        self._save_collapsed_state()
        self._rebuild()

    def toggle_project_collapsed_by_row(self, row_idx: int) -> None:
        row = self.project_at_row(row_idx)
        if row is None:
            return
        if not self._project_has_children_cache.get(row.id, False):
            return
        self.toggle_project_collapsed(row.id)

    def _load_collapsed_state(self) -> None:
        raw = self._db.get_setting(self._collapsed_state_key, "[]")
        try:
            payload = json.loads(raw) if raw else []
        except json.JSONDecodeError:
            payload = []
        self._collapsed_project_ids = {int(v) for v in payload if isinstance(v, int)}

    def _save_collapsed_state(self) -> None:
        payload = sorted(self._collapsed_project_ids)
        self._db.set_setting(self._collapsed_state_key, json.dumps(payload, ensure_ascii=False))

    def flags(self, index: QModelIndex) -> Any:
        """Устанавливает флаги взаимодействия для строки."""
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        r = self._rows[index.row()]
        if isinstance(r, HeaderRow):
            return Qt.ItemFlag.ItemIsEnabled
        flags = cast(Any, Qt.ItemFlag.ItemIsEnabled)
        flags |= Qt.ItemFlag.ItemIsSelectable
        flags |= Qt.ItemFlag.ItemIsDragEnabled
        flags |= Qt.ItemFlag.ItemIsDropEnabled
        return flags

    def move_project_by_drop(
        self,
        source_project_id: int,
        target_project_id: int,
        drop_after: bool,
        as_child: bool,
    ) -> bool:
        """Перемещает проект относительно target в пределах его sibling-группы."""
        projects = self._db.fetch_projects()
        by_id = {p.id: p for p in projects}
        source = by_id.get(source_project_id)
        target = by_id.get(target_project_id)
        if source is None or target is None:
            return False
        if source_project_id == target_project_id:
            return False

        if as_child:
            try:
                self._db.move_project(source_project_id, target_project_id, None)
            except ValueError:
                return False
            self.refresh()
            return True

        parent_id = target.parent_project_id
        siblings = self._db.fetch_project_children(parent_id)
        sibling_ids = [p.id for p in siblings if p.id != source_project_id]
        if target_project_id not in sibling_ids:
            return False
        index = sibling_ids.index(target_project_id)
        if drop_after:
            index += 1
        try:
            self._db.move_project(source_project_id, parent_id, index)
        except ValueError:
            return False
        self.refresh()
        return True

    def set_filter_mode(self, mode: str):
        """Обновляет режим фильтрации."""
        self._filter_mode = mode
        self._rebuild()

    def set_search(self, text: str):
        """Устанавливает строку поиска."""
        self._search = (text or "").strip().lower()
        self._rebuild()

    def set_area_focus(self, area: Optional[str]):
        """Фиксирует активную область проектов."""
        self._area_focus = area
        self._rebuild()

    def set_task_filter(self, task_id: Optional[int]):
        """Фильтрует проекты по выбранной задаче."""
        self._task_filter_id = task_id
        self._rebuild()

    def set_priority_filter(self, priority: Optional[str]) -> None:
        if priority is None:
            self._priority_filter = None
        else:
            self._priority_filter = normalize_priority(priority)
        self._rebuild()

    def add_project(
        self,
        area: str,
        title: str,
        updated: date,
        priority: str,
        archived: bool,
        parent_project_id: Optional[int] = None,
        default_task_priority: str = "",
        force_recurrence_kind: str = "",
        linked_map_id: Optional[int] = None,
        linked_note_id: Optional[int] = None,
        linked_object_id: Optional[int] = None,
        marker_color: str = "",
        marker_theme: str = "",
        repository_catalog: str = "",
    ):
        """Добавляет новый проект и пересобирает список."""
        project = self._db.create_project(
            area=area,
            title=title,
            updated=updated,
            priority=priority,
            archived=archived,
            parent_project_id=parent_project_id,
            default_task_priority=default_task_priority,
            force_recurrence_kind=force_recurrence_kind,
            linked_map_id=linked_map_id,
            linked_note_id=linked_note_id,
            linked_object_id=linked_object_id,
            marker_color=marker_color,
            marker_theme=marker_theme,
            repository_catalog=repository_catalog,
        )
        self._all_rows.append(
            ProjectRow(
                project.id,
                project.area,
                project.title,
                project.updated,
                project.priority,
                project.archived,
                project.parent_project_id,
                project.default_task_priority,
                project.force_recurrence_kind,
                project.linked_map_id,
                project.linked_note_id,
                project.linked_object_id,
                project.marker_color,
                project.marker_theme,
                project.repository_catalog,
            )
        )
        self._attachment_summary_dirty = True
        self._rebuild()

    def quick_add_project(
        self,
        area: str,
        parent_project_id: Optional[int] = None,
        title: str = "Новый проект",
    ) -> None:
        self.add_project(
            area=area,
            title=title,
            updated=date.today(),
            priority="Medium",
            archived=False,
            parent_project_id=parent_project_id,
        )

    def area_has_active(self, area: str) -> bool:
        """Проверяет наличие активных проектов в области."""
        return any(
            isinstance(it, ProjectRow) and it.area == area and not it.archived
            for it in self._all_rows
        )

    def set_area_archived(self, area: str, archived: bool):
        """Архивирует или восстанавливает все проекты области."""
        self._db.set_projects_archived_for_area(area, archived)
        new_all: List[Row] = []
        for it in self._all_rows:
            if isinstance(it, ProjectRow) and it.area == area:
                it = ProjectRow(
                    it.id,
                    it.area,
                    it.title,
                    it.updated,
                    it.priority,
                    archived,
                    it.parent_project_id,
                    it.default_task_priority,
                    it.force_recurrence_kind,
                    it.linked_map_id,
                    it.linked_note_id,
                    it.linked_object_id,
                    it.marker_color,
                    it.marker_theme,
                    it.repository_catalog,
                )
            new_all.append(it)
        self._all_rows = new_all
        self._rebuild()

    def delete_area(self, area: str):
        """Удаляет все проекты в области."""
        self._db.delete_projects_by_area(area)
        self._all_rows = [
            it for it in self._all_rows if not (isinstance(it, ProjectRow) and it.area == area)
        ]
        if self._area_focus == area:
            self._area_focus = None
        self._attachment_summary_dirty = True
        self._rebuild()

    def rename_area(self, area: str, new_area: str):
        """Переименовывает область проектов."""
        self._db.rename_project_area(area, new_area)
        new_all: List[Row] = []
        for it in self._all_rows:
            if isinstance(it, ProjectRow) and it.area == area:
                it = ProjectRow(
                    it.id,
                    new_area,
                    it.title,
                    it.updated,
                    it.priority,
                    it.archived,
                    it.parent_project_id,
                    it.default_task_priority,
                    it.force_recurrence_kind,
                    it.linked_map_id,
                    it.linked_note_id,
                    it.linked_object_id,
                    it.marker_color,
                    it.marker_theme,
                    it.repository_catalog,
                )
            new_all.append(it)
        self._all_rows = new_all
        if self._area_focus == area:
            self._area_focus = new_area
        self._attachment_summary_dirty = True
        self._rebuild()

    def project_at_row(self, row_idx: int) -> Optional[ProjectRow]:
        """Возвращает проект по индексу строки или None."""
        if row_idx < 0 or row_idx >= len(self._rows):
            return None
        r = self._rows[row_idx]
        if isinstance(r, HeaderRow):
            return None
        return r

    def update_project_by_row(
        self,
        row_idx: int,
        area: str,
        title: str,
        updated: date,
        priority: str,
        archived: bool,
        parent_project_id: Optional[int] = None,
        default_task_priority: str = "",
        force_recurrence_kind: str = "",
        linked_map_id: Optional[int] = None,
        linked_note_id: Optional[int] = None,
        linked_object_id: Optional[int] = None,
        marker_color: str = "",
        marker_theme: str = "",
        repository_catalog: str = "",
    ):
        """Обновляет проект по индексу строки."""
        r = self.project_at_row(row_idx)
        if r is None:
            return
        updated_project = self._db.update_project(
            project_id=r.id,
            area=area,
            title=title,
            updated=updated,
            priority=priority,
            archived=archived,
            parent_project_id=parent_project_id,
            default_task_priority=default_task_priority,
            force_recurrence_kind=force_recurrence_kind,
            linked_map_id=linked_map_id,
            linked_note_id=linked_note_id,
            linked_object_id=linked_object_id,
            marker_color=marker_color,
            marker_theme=marker_theme,
            repository_catalog=repository_catalog,
        )

        new_all: List[Row] = []
        for it in self._all_rows:
            if isinstance(it, ProjectRow) and it.id == r.id:
                it = ProjectRow(
                    updated_project.id,
                    updated_project.area,
                    updated_project.title,
                    updated_project.updated,
                    updated_project.priority,
                    updated_project.archived,
                    updated_project.parent_project_id,
                    updated_project.default_task_priority,
                    updated_project.force_recurrence_kind,
                    updated_project.linked_map_id,
                    updated_project.linked_note_id,
                    updated_project.linked_object_id,
                    updated_project.marker_color,
                    updated_project.marker_theme,
                    updated_project.repository_catalog,
                )
            new_all.append(it)

        self._all_rows = new_all
        self._attachment_summary_dirty = True
        self._rebuild()

    def cycle_priority_by_row(self, row_idx: int) -> None:
        project_row = self.project_at_row(row_idx)
        if project_row is None:
            return
        current = normalize_priority(project_row.priority)
        if current not in PROJECT_PRIORITY_SEQUENCE:
            next_priority = "Medium"
        else:
            next_index = (PROJECT_PRIORITY_SEQUENCE.index(current) + 1) % len(PROJECT_PRIORITY_SEQUENCE)
            next_priority = PROJECT_PRIORITY_SEQUENCE[next_index]
        updated_project = self._db.update_project(
            project_id=project_row.id,
            area=project_row.area,
            title=project_row.title,
            updated=project_row.updated,
            priority=next_priority,
            archived=project_row.archived,
            parent_project_id=project_row.parent_project_id,
            default_task_priority=project_row.default_task_priority,
            force_recurrence_kind=project_row.force_recurrence_kind,
            linked_map_id=project_row.linked_map_id,
            linked_note_id=project_row.linked_note_id,
            linked_object_id=project_row.linked_object_id,
            marker_color=project_row.marker_color,
            marker_theme=project_row.marker_theme,
            repository_catalog=project_row.repository_catalog,
        )
        new_all: List[Row] = []
        for row in self._all_rows:
            if isinstance(row, ProjectRow) and row.id == project_row.id:
                row = ProjectRow(
                    updated_project.id,
                    updated_project.area,
                    updated_project.title,
                    updated_project.updated,
                    updated_project.priority,
                    updated_project.archived,
                    updated_project.parent_project_id,
                    updated_project.default_task_priority,
                    updated_project.force_recurrence_kind,
                    updated_project.linked_map_id,
                    updated_project.linked_note_id,
                    updated_project.linked_object_id,
                    updated_project.marker_color,
                    updated_project.marker_theme,
                    updated_project.repository_catalog,
                )
            new_all.append(row)
        self._all_rows = new_all
        self._rebuild()

    def repository_probe_by_row(self, row_idx: int) -> RepositoryProbeState:
        project_row = self.project_at_row(row_idx)
        if project_row is None:
            return RepositoryProbeState(False, message="Проект не найден.")
        return self._repository_probe.inspect(project_row.repository_catalog)

    def toggle_archive_by_row(self, row_idx: int):
        """Переключает архивный статус проекта по строке."""
        if row_idx < 0 or row_idx >= len(self._rows):
            return
        r = self._rows[row_idx]
        if isinstance(r, HeaderRow):
            return

        new_archived = not r.archived
        self._db.set_project_archived(r.id, new_archived)
        new_all: List[Row] = []
        for it in self._all_rows:
            if isinstance(it, ProjectRow) and it.id == r.id:
                it = ProjectRow(
                    it.id,
                    it.area,
                    it.title,
                    it.updated,
                    it.priority,
                    new_archived,
                    it.parent_project_id,
                    it.default_task_priority,
                    it.force_recurrence_kind,
                    it.linked_map_id,
                    it.linked_note_id,
                    it.linked_object_id,
                    it.marker_color,
                    it.marker_theme,
                    it.repository_catalog,
                )
            new_all.append(it)

        self._all_rows = new_all
        self._rebuild()

    def delete_project_by_row(self, row_idx: int):
        """Удаляет проект по индексу строки."""
        r = self.project_at_row(row_idx)
        if r is None:
            return
        self._db.delete_project(r.id)
        self._all_rows = [it for it in self._all_rows if not (isinstance(it, ProjectRow) and it.id == r.id)]
        self._attachment_summary_dirty = True
        self._rebuild()

    def _rebuild(self):
        """Пересобирает список проектов с учетом фильтров."""
        self._rebuild_project_title_cache()
        if self._attachment_summary_dirty:
            self._rebuild_attachment_summary_cache()
        search = self._search
        task_project_id = None
        if self._task_filter_id is not None:
            for task in self._db.fetch_tasks():
                if task.id == self._task_filter_id:
                    task_project_id = task.project_id
                    break

        projects: List[ProjectRow] = []
        project_map = {
            row.id: row for row in self._all_rows
            if isinstance(row, ProjectRow)
        }

        def is_hidden_by_collapsed_parent(project: ProjectRow) -> bool:
            parent_id = project.parent_project_id
            seen: set[int] = set()
            while isinstance(parent_id, int) and parent_id not in seen:
                if parent_id in self._collapsed_project_ids:
                    return True
                seen.add(parent_id)
                parent = project_map.get(parent_id)
                if parent is None:
                    break
                parent_id = parent.parent_project_id
            return False
        for it in self._all_rows:
            if not isinstance(it, ProjectRow):
                continue

            if self._task_filter_id is not None:
                if task_project_id is None or it.id != task_project_id:
                    continue

            if self._area_focus is not None and it.area != self._area_focus:
                continue
            if self._priority_filter is not None and normalize_priority(it.priority) != self._priority_filter:
                continue

            if self._filter_mode in ("Все", "Активные") and it.archived:
                continue
            if self._filter_mode == "Архив" and not it.archived:
                continue

            display_title = self._project_title_cache.get(it.id, it.title).lower()
            if search and search not in it.title.lower() and search not in display_title and search not in it.area.lower():
                continue
            if is_hidden_by_collapsed_parent(it):
                continue

            projects.append(it)

        priority_order = {"High": 0, "Medium": 1, "Low": 2, "Отложенная": 3}

        def priority_key(priority: str) -> int:
            return priority_order[normalize_priority(priority)]

        projects.sort(
            key=lambda x: (
                x.area.lower(),
                priority_key(x.priority),
                self._project_title_cache.get(x.id, x.title).lower(),
                x.id,
            )
        )

        new_rows: List[Row] = []
        cur: Optional[str] = None
        for p in projects:
            if cur != p.area:
                cur = p.area
                new_rows.append(HeaderRow(cur))
            new_rows.append(p)

        self.beginResetModel()
        self._rows = new_rows
        self.endResetModel()

    def _rebuild_project_title_cache(self) -> None:
        project_map = {
            row.id: row for row in self._all_rows
            if isinstance(row, ProjectRow)
        }
        cache: Dict[int, str] = {}
        depth_cache: Dict[int, int] = {}
        has_children_cache: Dict[int, bool] = {}

        for project_row in project_map.values():
            has_children_cache[project_row.id] = False
        for project_row in project_map.values():
            if project_row.parent_project_id in project_map:
                has_children_cache[project_row.parent_project_id] = True

        def resolve_title(node: ProjectRow, seen: Optional[set[int]] = None) -> str:
            cached = cache.get(node.id)
            if cached is not None:
                return cached

            seen_set = seen or set()
            if node.id in seen_set:
                cache[node.id] = node.title
                return node.title

            if node.parent_project_id is None:
                cache[node.id] = node.title
                return node.title

            parent = project_map.get(node.parent_project_id)
            if parent is None:
                cache[node.id] = node.title
                return node.title

            nested = f"{resolve_title(parent, seen_set | {node.id})} / {node.title}"
            cache[node.id] = nested
            return nested

        def resolve_depth(node: ProjectRow, seen: Optional[set[int]] = None) -> int:
            cached = depth_cache.get(node.id)
            if cached is not None:
                return cached
            seen_set = seen or set()
            if node.id in seen_set:
                depth_cache[node.id] = 0
                return 0
            if node.parent_project_id is None:
                depth_cache[node.id] = 0
                return 0
            parent = project_map.get(node.parent_project_id)
            if parent is None:
                depth_cache[node.id] = 0
                return 0
            depth = resolve_depth(parent, seen_set | {node.id}) + 1
            depth_cache[node.id] = depth
            return depth

        for project_row in project_map.values():
            resolve_title(project_row)
            resolve_depth(project_row)

        self._project_title_cache = cache
        self._project_depth_cache = depth_cache
        self._project_has_children_cache = has_children_cache

    def _rebuild_attachment_summary_cache(self) -> None:
        project_map = {
            row.id: row for row in self._all_rows
            if isinstance(row, ProjectRow)
        }
        children_map: Dict[int, List[int]] = {}
        for project_row in project_map.values():
            parent_id = project_row.parent_project_id
            if isinstance(parent_id, int) and parent_id in project_map:
                children_map.setdefault(parent_id, []).append(project_row.id)

        direct_counts: Dict[int, Dict[str, int]] = {}
        for task in self._db.fetch_tasks():
            project_id = task.project_id
            if not isinstance(project_id, int):
                continue
            attachments = self._db.fetch_task_attachments(task.id)
            if not attachments:
                continue
            project_counts = direct_counts.setdefault(project_id, {})
            for attachment in attachments:
                kind = (attachment.kind or "").strip().lower()
                if not kind:
                    continue
                project_counts[kind] = project_counts.get(kind, 0) + 1

        aggregate_cache: Dict[int, Dict[str, int]] = {}

        def aggregate(project_id: int, seen: set[int]) -> Dict[str, int]:
            cached = aggregate_cache.get(project_id)
            if cached is not None:
                return cached
            if project_id in seen:
                return {}
            counts = dict(direct_counts.get(project_id, {}))
            for child_id in children_map.get(project_id, []):
                child_counts = aggregate(child_id, seen | {project_id})
                for kind, value in child_counts.items():
                    counts[kind] = counts.get(kind, 0) + value
            aggregate_cache[project_id] = counts
            return counts

        summary_cache: Dict[int, List[tuple[str, int]]] = {}
        for project_id in project_map.keys():
            counts = aggregate(project_id, set())
            if not counts:
                continue
            ordered_kinds = [kind for kind in ATTACHMENT_BADGE_ORDER if kind in counts]
            ordered_kinds.extend(
                kind for kind in sorted(counts.keys())
                if kind not in ATTACHMENT_BADGE_ORDER
            )
            badges = [
                (kind, int(counts[kind]))
                for kind in ordered_kinds
                if int(counts.get(kind, 0)) > 0
            ]
            if badges:
                summary_cache[project_id] = badges

        self._project_attachment_summary = summary_cache
        self._attachment_summary_dirty = False

__all__ = ["ProjectsModel"]
