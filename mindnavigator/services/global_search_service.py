"""Application-wide entity search independent from Qt widgets."""

from __future__ import annotations


_COLLECTION_ENTITY_LABELS = {
    "building": "Здание",
    "city": "Город",
    "film": "Фильм",
    "game": "Игра",
    "character": "Персонаж",
    "other": "Другое",
}


class GlobalSearchService:
    def __init__(self, database) -> None:
        self._db = database

    @staticmethod
    def _matches(query: str, *values: str) -> bool:
        needle = query.lower()
        return any(needle in (value or "").lower() for value in values)

    def search(self, query: str) -> list[dict]:
        normalized_query = (query or "").strip().lower()
        if not normalized_query:
            return []

        matches: list[dict] = []
        search_full_text = getattr(self._db, "search_full_text", None)
        indexed_matches = search_full_text(normalized_query) if callable(search_full_text) else None
        indexed_by_entity: dict[str, list[dict]] = {}
        if indexed_matches is not None:
            for item in indexed_matches:
                indexed_by_entity.setdefault(str(item["entity"]), []).append(item)

        if indexed_matches is None:
            for task in self._db.fetch_tasks():
                if not self._matches(normalized_query, task.title, task.description, task.project_title, task.project_area):
                    continue
                matches.append(
                    {
                        "entity": "task",
                        "label": f"Задача: {task.title}",
                        "tooltip": task.description or task.project_title,
                        "id": task.id,
                    }
                )
        else:
            matches.extend(
                {
                    "entity": "task",
                    "label": f"Задача: {item['title']}",
                    "tooltip": str(item["detail"]),
                    "id": int(item["id"]),
                }
                for item in indexed_by_entity.get("task", [])
            )
            matches.extend(
                {
                    "entity": "idea",
                    "label": f"Идея: {item['title']}",
                    "tooltip": str(item["detail"]),
                    "id": int(item["id"]),
                }
                for item in indexed_by_entity.get("idea", [])
            )
        for project in self._db.fetch_projects():
            if self._matches(normalized_query, project.title, project.area):
                matches.append(
                    {
                        "entity": "project",
                        "label": f"Проект: {project.title}",
                        "tooltip": project.area,
                        "id": project.id,
                    }
                )
        maps = self._db.fetch_maps()
        map_titles = {item.id: item.title for item in maps}
        for map_item in maps:
            if self._matches(normalized_query, map_item.title, map_item.description, map_item.project):
                matches.append(
                    {
                        "entity": "map",
                        "label": f"Карта: {map_item.title}",
                        "tooltip": map_item.project or map_item.description,
                        "id": map_item.id,
                    }
                )
        for marker in self._db.fetch_map_markers():
            if self._matches(normalized_query, marker.name, marker.description, marker.properties):
                map_title = map_titles.get(marker.map_id, "")
                matches.append(
                    {
                        "entity": "marker",
                        "label": f"Метка: {marker.name}",
                        "tooltip": f"Карта: {map_title}" if map_title else "",
                        "id": marker.id,
                        "map_id": marker.map_id,
                    }
                )
        if indexed_matches is None:
            for note in self._db.fetch_notes():
                tags = " ".join(note.tags or [])
                if not self._matches(normalized_query, note.title, note.preview, tags, note.project):
                    continue
                matches.append(
                    {
                        "entity": "note",
                        "label": f"Заметка: {note.title}",
                        "tooltip": note.project or note.preview,
                        "id": note.id,
                    }
                )
        else:
            matches.extend(
                {
                    "entity": "note",
                    "label": f"Заметка: {item['title']}",
                    "tooltip": str(item["detail"]),
                    "id": int(item["id"]),
                }
                for item in indexed_by_entity.get("note", [])
            )
        for file_item in self._db.fetch_cloud_files():
            if self._matches(normalized_query, file_item.name, file_item.rel_path, file_item.description):
                matches.append(
                    {
                        "entity": "file",
                        "label": f"Файл: {file_item.name}",
                        "tooltip": file_item.rel_path or file_item.description,
                        "id": file_item.id,
                    }
                )
        if indexed_matches is None:
            for obj in self._db.fetch_objects():
                if not self._matches(normalized_query, obj.title, obj.catalog, obj.object_type, obj.status, obj.description):
                    continue
                tooltip = " · ".join(part for part in (obj.catalog, obj.object_type, obj.status) if part)
                matches.append(
                    {
                        "entity": "object",
                        "label": f"Объект: {obj.title}",
                        "tooltip": tooltip,
                        "id": obj.id,
                    }
                )
        else:
            matches.extend(
                {
                    "entity": "object",
                    "label": f"Объект: {item['title']}",
                    "tooltip": str(item["detail"]),
                    "id": int(item["id"]),
                }
                for item in indexed_by_entity.get("object", [])
            )
        for character in self._db.fetch_characters(search_text=normalized_query):
            tooltip = " · ".join(
                part for part in (character.role, ", ".join(character.tags), character.description) if part
            )
            matches.append(
                {
                    "entity": "character",
                    "label": f"Персонаж: {character.name}",
                    "tooltip": tooltip,
                    "id": character.id,
                }
            )
        for collection in self._db.fetch_collection_items(search_text=normalized_query):
            entity_label = _COLLECTION_ENTITY_LABELS.get(collection.entity_type, collection.entity_type)
            tooltip = " · ".join(
                part for part in (entity_label, collection.topic, collection.source_url) if part
            )
            matches.append(
                {
                    "entity": "collection",
                    "label": f"Коллекция: {collection.title}",
                    "tooltip": tooltip,
                    "id": collection.id,
                }
            )
        return matches


__all__ = ["GlobalSearchService"]
