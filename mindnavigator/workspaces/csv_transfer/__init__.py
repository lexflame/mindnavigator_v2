from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from typing import Mapping, Optional, Sequence

from mindnavigator.storage import (
    CollectionCategoryData,
    CollectionItemData,
    DossierData,
    IdeaData,
    NoteData,
    ObjectData,
    ProjectData,
    TaskData,
)

TASKS_CSV_FIELDS: tuple[str, ...] = (
    "id",
    "parent_id",
    "project_title",
    "day",
    "time_text",
    "title",
    "description",
    "priority",
    "done",
    "recurrence_kind",
    "recurrence_interval",
    "marker_color",
    "marker_theme",
    "project_task_type",
)

PROJECTS_CSV_FIELDS: tuple[str, ...] = (
    "id",
    "parent_project_id",
    "area",
    "title",
    "updated",
    "priority",
    "archived",
    "default_task_priority",
    "force_recurrence_kind",
    "linked_map_id",
    "linked_note_id",
    "linked_object_id",
    "marker_color",
    "marker_theme",
    "repository_catalog",
    "project_task_types_json",
    "project_display_properties_json",
    "related_project_ids",
    "related_task_ids",
    "repository_links_json",
    "wiki_links_json",
)

NOTES_CSV_FIELDS: tuple[str, ...] = (
    "title",
    "preview",
    "tags",
    "project",
    "favorite",
    "attachment",
    "locked",
)

IDEAS_CSV_FIELDS: tuple[str, ...] = (
    "title",
    "summary",
    "body_md",
    "type",
    "status",
    "value_score",
    "effort_score",
    "project_title",
    "source",
    "archived",
)

DOSSIER_CSV_FIELDS: tuple[str, ...] = (
    "kind",
    "title",
    "summary",
    "description",
    "tags",
    "status",
    "rating",
    "source",
    "cover_image",
    "metadata_json",
)

OBJECTS_CSV_FIELDS: tuple[str, ...] = (
    "title",
    "catalog",
    "object_type",
    "status",
    "description",
)

COLLECTIONS_CSV_FIELDS: tuple[str, ...] = (
    "title",
    "entity_type",
    "topic",
    "category_path",
    "image_url",
    "source_url",
    "description",
    "source_folder_path",
    "import_options_json",
)


@dataclass(frozen=True)
class CsvImportResult:
    imported: int
    skipped: int


def export_tasks_rows(tasks: Sequence[TaskData]) -> list[dict[str, object]]:
    return [
        {
            "id": task.id,
            "parent_id": task.parent_id if task.parent_id is not None else "",
            "project_title": task.project_title,
            "day": task.day.isoformat(),
            "time_text": task.time_text,
            "title": task.title,
            "description": task.description,
            "priority": task.priority,
            "done": _format_bool(task.done),
            "recurrence_kind": task.recurrence_kind,
            "recurrence_interval": task.recurrence_interval,
            "marker_color": task.marker_color,
            "marker_theme": task.marker_theme,
            "project_task_type": task.project_task_type_title,
        }
        for task in tasks
    ]


def export_projects_rows(projects: Sequence[ProjectData], db=None) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for project in projects:
        row: dict[str, object] = {
            "id": project.id,
            "parent_project_id": project.parent_project_id if project.parent_project_id is not None else "",
            "area": project.area,
            "title": project.title,
            "updated": project.updated.isoformat(),
            "priority": project.priority,
            "archived": _format_bool(project.archived),
            "default_task_priority": project.default_task_priority,
            "force_recurrence_kind": project.force_recurrence_kind,
            "linked_map_id": project.linked_map_id if project.linked_map_id is not None else "",
            "linked_note_id": project.linked_note_id if project.linked_note_id is not None else "",
            "linked_object_id": project.linked_object_id if project.linked_object_id is not None else "",
            "marker_color": project.marker_color,
            "marker_theme": project.marker_theme,
            "repository_catalog": project.repository_catalog,
            "project_task_types_json": "",
            "project_display_properties_json": "",
            "related_project_ids": "",
            "related_task_ids": "",
            "repository_links_json": "",
            "wiki_links_json": "",
        }
        if db is not None:
            row.update(_export_project_properties(db, int(project.id)))
        rows.append(row)
    return rows


def export_notes_rows(notes: Sequence[NoteData]) -> list[dict[str, object]]:
    return [
        {
            "title": note.title,
            "preview": note.preview,
            "tags": "|".join(note.tags),
            "project": note.project,
            "favorite": _format_bool(note.favorite),
            "attachment": _format_bool(note.attachment),
            "locked": _format_bool(note.locked),
        }
        for note in notes
    ]


def export_ideas_rows(ideas: Sequence[IdeaData]) -> list[dict[str, object]]:
    return [
        {
            "title": idea.title,
            "summary": idea.summary,
            "body_md": idea.body_md,
            "type": idea.type,
            "status": idea.status,
            "value_score": idea.value_score,
            "effort_score": idea.effort_score,
            "project_title": idea.project_title,
            "source": idea.source,
            "archived": _format_bool(idea.archived_at is not None),
        }
        for idea in ideas
    ]


def export_dossiers_rows(dossiers: Sequence[DossierData]) -> list[dict[str, object]]:
    return [
        {
            "kind": dossier.kind,
            "title": dossier.title,
            "summary": dossier.summary,
            "description": dossier.description,
            "tags": "|".join(dossier.tags),
            "status": dossier.status,
            "rating": "" if dossier.rating is None else dossier.rating,
            "source": dossier.source,
            "cover_image": dossier.cover_image,
            "metadata_json": json.dumps(dossier.metadata, ensure_ascii=False, sort_keys=True),
        }
        for dossier in dossiers
    ]


def export_objects_rows(objects: Sequence[ObjectData]) -> list[dict[str, object]]:
    return [
        {
            "title": obj.title,
            "catalog": obj.catalog,
            "object_type": obj.object_type,
            "status": obj.status,
            "description": obj.description,
        }
        for obj in objects
    ]


def export_collections_rows(
    items: Sequence[CollectionItemData],
    categories: Sequence[CollectionCategoryData],
) -> list[dict[str, object]]:
    category_paths = build_category_path_map(categories)
    return [
        {
            "title": item.title,
            "entity_type": item.entity_type,
            "topic": item.topic,
            "category_path": category_paths.get(item.category_id, "") if item.category_id is not None else "",
            "image_url": item.image_url,
            "source_url": item.source_url,
            "description": item.description,
            "source_folder_path": item.source_folder_path,
            "import_options_json": item.import_options_json,
        }
        for item in items
    ]


def import_tasks_rows(db, rows: Sequence[Mapping[str, str]]) -> CsvImportResult:
    project_map = build_project_title_to_id(db.fetch_projects())
    imported = 0
    skipped = 0
    source_to_created_id: dict[int, int] = {}
    created_rows: list[tuple[TaskData, Optional[int], bool]] = []

    for row in rows:
        title = _text(row.get("title"))
        if not title:
            skipped += 1
            continue
        row_day = _parse_date(row.get("day"), default=date.today())
        project_title = _text(row.get("project_title"))
        project_id = project_map.get(_norm(project_title)) if project_title else None
        project_task_type_id = _project_task_type_id_by_title(db, project_id, _text(row.get("project_task_type")))
        recurrence_interval = _parse_int(row.get("recurrence_interval"), default=1, minimum=1)
        done = _parse_bool(row.get("done"), default=False)
        source_id = _parse_optional_int(row.get("id"))
        parent_source_id = _parse_optional_int(row.get("parent_id"))
        try:
            created = db.create_task(
                title=title,
                description=_text(row.get("description")),
                day=row_day,
                time_text=_text(row.get("time_text")),
                priority=_text(row.get("priority")) or "Medium",
                project_id=project_id,
                recurrence_kind=_text(row.get("recurrence_kind")).lower(),
                recurrence_interval=recurrence_interval,
                marker_color=_text(row.get("marker_color")),
                marker_theme=_text(row.get("marker_theme")).lower(),
                project_task_type_id=project_task_type_id,
            )
        except ValueError:
            skipped += 1
            continue
        imported += 1
        if source_id is not None:
            source_to_created_id[source_id] = created.id
        created_rows.append((created, parent_source_id, done))

    for created, parent_source_id, done in created_rows:
        new_parent_id = source_to_created_id.get(parent_source_id) if parent_source_id is not None else None
        if new_parent_id == created.id:
            new_parent_id = None
        if new_parent_id is None and not done:
            continue
        try:
            db.update_task(
                task_id=created.id,
                title=created.title,
                description=created.description,
                day=created.day,
                time_text=created.time_text,
                priority=created.priority,
                done=done,
                project_id=created.project_id,
                parent_id=new_parent_id,
                recurrence_kind=created.recurrence_kind,
                recurrence_interval=created.recurrence_interval,
                marker_color=created.marker_color,
                marker_theme=created.marker_theme,
                project_task_type_id=created.project_task_type_id,
            )
        except ValueError:
            skipped += 1
    return CsvImportResult(imported=imported, skipped=skipped)


def import_projects_rows(db, rows: Sequence[Mapping[str, str]]) -> CsvImportResult:
    parsed_rows: list[dict[str, object]] = []
    for row in rows:
        title = _text(row.get("title"))
        if not title:
            continue
        parsed_rows.append(
            {
                "source_id": _parse_optional_int(row.get("id")),
                "parent_source_id": _parse_optional_int(row.get("parent_project_id")),
                "area": _text(row.get("area")) or "General",
                "title": title,
                "updated": _parse_date(row.get("updated"), default=date.today()),
                "priority": _text(row.get("priority")) or "Medium",
                "archived": _parse_bool(row.get("archived"), default=False),
                "default_task_priority": _text(row.get("default_task_priority")),
                "force_recurrence_kind": _normalize_recurrence(_text(row.get("force_recurrence_kind"))),
                "linked_map_id": _parse_optional_int(row.get("linked_map_id")),
                "linked_note_id": _parse_optional_int(row.get("linked_note_id")),
                "linked_object_id": _parse_optional_int(row.get("linked_object_id")),
                "marker_color": _text(row.get("marker_color")),
                "marker_theme": _text(row.get("marker_theme")).lower(),
                "repository_catalog": _text(row.get("repository_catalog")),
                "project_task_types": _parse_json_list(row.get("project_task_types_json")),
                "project_display_properties": _parse_json_list(row.get("project_display_properties_json")),
                "related_project_source_ids": _parse_pipe_ints(row.get("related_project_ids")),
                "related_task_ids": _parse_pipe_ints(row.get("related_task_ids")),
                "repository_links": _parse_json_list(row.get("repository_links_json")),
                "wiki_links": _parse_json_list(row.get("wiki_links_json")),
            }
        )

    imported = 0
    skipped = 0
    source_to_created_id: dict[int, int] = {}
    pending = list(parsed_rows)

    while pending:
        progressed = False
        next_pending: list[dict[str, object]] = []
        for row in pending:
            parent_source_id = row["parent_source_id"]
            parent_id: Optional[int] = None
            if isinstance(parent_source_id, int):
                if parent_source_id not in source_to_created_id:
                    next_pending.append(row)
                    continue
                parent_id = source_to_created_id[parent_source_id]
            try:
                created = db.create_project(
                    area=str(row["area"]),
                    title=str(row["title"]),
                    updated=row["updated"],
                    priority=str(row["priority"]),
                    archived=bool(row["archived"]),
                    parent_project_id=parent_id,
                    default_task_priority=str(row["default_task_priority"]),
                    force_recurrence_kind=str(row["force_recurrence_kind"]),
                    linked_map_id=row["linked_map_id"],
                    linked_note_id=row["linked_note_id"],
                    linked_object_id=row["linked_object_id"],
                    marker_color=str(row["marker_color"]),
                    marker_theme=str(row["marker_theme"]),
                    repository_catalog=str(row["repository_catalog"]),
                )
            except ValueError:
                skipped += 1
                progressed = True
                continue
            imported += 1
            source_id = row["source_id"]
            if isinstance(source_id, int):
                source_to_created_id[source_id] = created.id
            _apply_imported_project_properties(db, created.id, row, source_to_created_id)
            progressed = True
        if not progressed:
            break
        pending = next_pending

    for row in pending:
        try:
            created = db.create_project(
                area=str(row["area"]),
                title=str(row["title"]),
                updated=row["updated"],
                priority=str(row["priority"]),
                archived=bool(row["archived"]),
                parent_project_id=None,
                default_task_priority=str(row["default_task_priority"]),
                force_recurrence_kind=str(row["force_recurrence_kind"]),
                linked_map_id=row["linked_map_id"],
                linked_note_id=row["linked_note_id"],
                linked_object_id=row["linked_object_id"],
                marker_color=str(row["marker_color"]),
                marker_theme=str(row["marker_theme"]),
                repository_catalog=str(row["repository_catalog"]),
            )
            _apply_imported_project_properties(db, created.id, row, source_to_created_id)
            imported += 1
        except ValueError:
            skipped += 1

    return CsvImportResult(imported=imported, skipped=skipped)


def import_notes_rows(db, rows: Sequence[Mapping[str, str]]) -> CsvImportResult:
    imported = 0
    skipped = 0
    for row in rows:
        title = _text(row.get("title"))
        if not title:
            skipped += 1
            continue
        tags = _parse_tags(row.get("tags"))
        try:
            db.create_note(
                title=title,
                preview=_text(row.get("preview")),
                tags=tags,
                project=_text(row.get("project")),
                favorite=_parse_bool(row.get("favorite"), default=False),
                attachment=_parse_bool(row.get("attachment"), default=False),
                locked=_parse_bool(row.get("locked"), default=False),
            )
            imported += 1
        except ValueError:
            skipped += 1
    return CsvImportResult(imported=imported, skipped=skipped)


def import_ideas_rows(db, rows: Sequence[Mapping[str, str]]) -> CsvImportResult:
    project_map = build_project_title_to_id(db.fetch_projects())
    imported = 0
    skipped = 0
    for row in rows:
        title = _text(row.get("title"))
        if not title:
            skipped += 1
            continue
        project_title = _text(row.get("project_title"))
        project_id = project_map.get(_norm(project_title)) if project_title else None
        try:
            created = db.create_idea(
                title=title,
                summary=_text(row.get("summary")),
                body_md=_text(row.get("body_md")),
                idea_type=_text(row.get("type")) or "other",
                status=_text(row.get("status")) or "inbox",
                value_score=_parse_int(row.get("value_score"), default=3, minimum=1),
                effort_score=_parse_int(row.get("effort_score"), default=3, minimum=1),
                project_id=project_id,
                source=_text(row.get("source")),
            )
            if _parse_bool(row.get("archived"), default=False):
                db.set_idea_archived(created.id, True)
            imported += 1
        except ValueError:
            skipped += 1
    return CsvImportResult(imported=imported, skipped=skipped)


def import_dossiers_rows(db, rows: Sequence[Mapping[str, str]]) -> CsvImportResult:
    imported = 0
    skipped = 0
    for row in rows:
        title = _text(row.get("title"))
        if not title:
            skipped += 1
            continue
        metadata = _parse_json_mapping(row.get("metadata_json"))
        if metadata is None:
            skipped += 1
            continue
        try:
            db.create_dossier(
                kind=_text(row.get("kind")) or "book",
                title=title,
                summary=_text(row.get("summary")),
                description=_text(row.get("description")),
                tags=_parse_tags(row.get("tags")),
                status=_text(row.get("status")) or "planned",
                rating=_parse_optional_int(row.get("rating")),
                source=_text(row.get("source")),
                cover_image=_text(row.get("cover_image")),
                metadata=metadata,
            )
            imported += 1
        except ValueError:
            skipped += 1
    return CsvImportResult(imported=imported, skipped=skipped)


def import_objects_rows(db, rows: Sequence[Mapping[str, str]]) -> CsvImportResult:
    imported = 0
    skipped = 0
    for row in rows:
        title = _text(row.get("title"))
        if not title:
            skipped += 1
            continue
        try:
            db.create_object(
                title=title,
                catalog=_text(row.get("catalog")),
                object_type=_text(row.get("object_type")),
                status=_text(row.get("status")),
                description=_text(row.get("description")),
            )
            imported += 1
        except ValueError:
            skipped += 1
    return CsvImportResult(imported=imported, skipped=skipped)


def import_collections_rows(db, rows: Sequence[Mapping[str, str]]) -> CsvImportResult:
    imported = 0
    skipped = 0
    for row in rows:
        title = _text(row.get("title"))
        if not title:
            skipped += 1
            continue
        category_id = None
        category_path = _text(row.get("category_path"))
        if category_path:
            category_id = db.ensure_collection_category_path(category_path)
        try:
            db.create_collection_item(
                title=title,
                entity_type=_text(row.get("entity_type")) or "other",
                category_id=category_id,
                topic=_text(row.get("topic")),
                image_url=_text(row.get("image_url")),
                source_url=_text(row.get("source_url")),
                description=_text(row.get("description")),
                source_folder_path=_text(row.get("source_folder_path")),
                import_options_json=_text(row.get("import_options_json")),
            )
            imported += 1
        except ValueError:
            skipped += 1
    return CsvImportResult(imported=imported, skipped=skipped)


def build_project_title_to_id(projects: Sequence[ProjectData]) -> dict[str, int]:
    if not projects:
        return {}
    by_id = {project.id: project for project in projects}
    full_title_by_id: dict[int, str] = {}
    title_counts: dict[str, int] = {}

    def full_title(project_id: int, seen: Optional[set[int]] = None) -> str:
        project = by_id.get(project_id)
        if project is None:
            return ""
        cached = full_title_by_id.get(project_id)
        if cached is not None:
            return cached
        visited = seen or set()
        if project_id in visited:
            return project.title
        visited.add(project_id)
        parent_id = project.parent_project_id
        if parent_id is None or parent_id not in by_id:
            value = project.title
        else:
            parent_title = full_title(parent_id, visited)
            value = f"{parent_title} / {project.title}" if parent_title else project.title
        full_title_by_id[project_id] = value
        return value

    for project in projects:
        title_counts[project.title] = title_counts.get(project.title, 0) + 1
        full_title(project.id)

    mapping: dict[str, int] = {}
    for project in projects:
        full = full_title_by_id.get(project.id, project.title)
        mapping[_norm(full)] = project.id
        if title_counts.get(project.title, 0) == 1:
            mapping[_norm(project.title)] = project.id
    return mapping


def build_category_path_map(categories: Sequence[CollectionCategoryData]) -> dict[int, str]:
    by_id = {category.id: category for category in categories}
    path_cache: dict[int, str] = {}

    def path_for(category_id: int, seen: Optional[set[int]] = None) -> str:
        category = by_id.get(category_id)
        if category is None:
            return ""
        cached = path_cache.get(category_id)
        if cached is not None:
            return cached
        visited = seen or set()
        if category_id in visited:
            return category.title
        visited.add(category_id)
        parent_id = category.parent_id
        if parent_id is None or parent_id not in by_id:
            value = category.title
        else:
            parent_path = path_for(parent_id, visited)
            value = f"{parent_path} / {category.title}" if parent_path else category.title
        path_cache[category_id] = value
        return value

    for category in categories:
        path_for(category.id)
    return path_cache


def _norm(value: str) -> str:
    return (value or "").strip().lower()


def _text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _format_bool(value: bool) -> str:
    return "1" if value else "0"


def _parse_bool(value: object, *, default: bool) -> bool:
    text = _norm(str(value) if value is not None else "")
    if not text:
        return default
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _parse_int(value: object, *, default: int, minimum: Optional[int] = None) -> int:
    text = _text(value)
    if not text:
        parsed = default
    else:
        try:
            parsed = int(text)
        except ValueError:
            parsed = default
    if minimum is not None:
        return max(minimum, parsed)
    return parsed


def _parse_optional_int(value: object) -> Optional[int]:
    text = _text(value)
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _parse_date(value: object, *, default: date) -> date:
    text = _text(value)
    if not text:
        return default
    try:
        return date.fromisoformat(text)
    except ValueError:
        return default


def _parse_tags(value: object) -> list[str]:
    text = _text(value)
    if not text:
        return []
    normalized = text.replace(",", "|")
    tags = [part.strip().lstrip("#") for part in normalized.split("|")]
    return [tag for tag in tags if tag]


def _parse_json_mapping(value: object) -> Optional[dict[str, object]]:
    text = _text(value)
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _parse_json_list(value: object) -> list[dict[str, object]]:
    text = _text(value)
    if not text:
        return []
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [item for item in parsed if isinstance(item, dict)]


def _parse_pipe_ints(value: object) -> list[int]:
    text = _text(value)
    if not text:
        return []
    result: list[int] = []
    for part in text.replace(",", "|").split("|"):
        part = part.strip()
        if not part:
            continue
        try:
            result.append(int(part))
        except ValueError:
            continue
    return result


def _export_project_properties(db, project_id: int) -> dict[str, object]:
    return {
        "project_task_types_json": json.dumps(
            [
                {
                    "title": item.title,
                    "value": item.value,
                    "color_marker": item.color_marker,
                    "theme_marker": item.theme_marker,
                    "priority": item.priority,
                    "importance": item.importance,
                    "is_plan_task": item.is_plan_task,
                    "concept_board_id": item.concept_board_id,
                    "active": item.active,
                }
                for item in db.fetch_project_task_types(project_id, include_inactive=True)
            ],
            ensure_ascii=False,
        ),
        "project_display_properties_json": json.dumps(
            [
                {"name": item.name, "url": item.url, "display_mode": item.display_mode}
                for item in db.fetch_project_display_properties(project_id)
            ],
            ensure_ascii=False,
        ),
        "related_project_ids": "|".join(
            str(item.related_project_id) for item in db.fetch_project_related_projects(project_id)
        ),
        "related_task_ids": "|".join(str(item.task_id) for item in db.fetch_project_related_tasks(project_id)),
        "repository_links_json": json.dumps(
            [{"title": item.title, "url": item.url} for item in db.fetch_project_repository_links(project_id)],
            ensure_ascii=False,
        ),
        "wiki_links_json": json.dumps(
            [{"title": item.title, "url": item.url} for item in db.fetch_project_wiki_links(project_id)],
            ensure_ascii=False,
        ),
    }


def _project_task_type_id_by_title(db, project_id: Optional[int], title: str) -> Optional[int]:
    if project_id is None or not title:
        return None
    fetch_types = getattr(db, "fetch_project_task_types", None)
    if not callable(fetch_types):
        return None
    normalized = " ".join(title.strip().upper().split())
    for item in fetch_types(int(project_id), include_inactive=False):
        if item.title == normalized:
            return item.id
    return None


def _apply_imported_project_properties(db, project_id: int, row: Mapping[str, object], source_to_created_id: Mapping[int, int]) -> None:
    try:
        db.replace_project_task_types(project_id, list(row.get("project_task_types") or []))
        db.replace_project_display_properties(project_id, list(row.get("project_display_properties") or []))
        related_project_ids = [
            source_to_created_id[source_id]
            for source_id in row.get("related_project_source_ids", [])
            if source_id in source_to_created_id
        ]
        db.replace_project_related_projects(project_id, related_project_ids)
        db.replace_project_related_tasks(project_id, list(row.get("related_task_ids") or []))
        db.replace_project_repository_links(project_id, list(row.get("repository_links") or []))
        db.replace_project_wiki_links(project_id, list(row.get("wiki_links") or []))
    except ValueError:
        return


def _normalize_recurrence(value: str) -> str:
    rec = _norm(value)
    if rec in {"daily", "weekly", "monthly"}:
        return rec
    return ""
