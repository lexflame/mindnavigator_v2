"""Read-only facade over legacy entity relation tables."""

from __future__ import annotations

from .entity_link_data import EntityLinkView, EntityRef


_ENTITY_KIND_ALIASES = {
    "collection": "collection_item",
    "cloud_file": "file",
}


class DatabaseEntityLinksMixin:
    def fetch_entity_links(
        self,
        entity_kind: str,
        entity_id: int,
        *,
        direction: str = "both",
    ) -> list[EntityLinkView]:
        entity = EntityRef(self._normalize_entity_link_kind(entity_kind), entity_id)
        normalized_direction = str(direction or "").strip().lower()
        if normalized_direction not in {"both", "incoming", "outgoing"}:
            raise ValueError("direction must be 'both', 'incoming', or 'outgoing'.")

        links = []
        links.extend(self._fetch_task_attachment_views(entity))
        links.extend(self._fetch_context_link_views(entity))
        links.extend(self._fetch_idea_relation_views(entity))
        links.extend(self._fetch_dossier_link_views(entity))
        links.extend(self._fetch_collection_relation_views(entity))
        links = [
            link
            for link in links
            if link.direction == "symmetric" or normalized_direction == "both" or link.direction == normalized_direction
        ]
        return sorted(links, key=lambda link: (link.created_at, link.origin, link.origin_id), reverse=True)

    @staticmethod
    def _normalize_entity_link_kind(kind: str) -> str:
        normalized = str(kind or "").strip().lower()
        return _ENTITY_KIND_ALIASES.get(normalized, normalized)

    def _fetch_task_attachment_views(self, entity: EntityRef) -> list[EntityLinkView]:
        rows = self._conn.execute(
            """
            SELECT id, task_id, kind, ref_id, created_at, comment
            FROM task_attachments
            WHERE (task_id = ?) OR (lower(kind) = ? AND ref_id = ?)
            ORDER BY created_at DESC, id DESC;
            """,
            (entity.id if entity.kind == "task" else -1, entity.kind, entity.id),
        ).fetchall()
        result = []
        for row in rows:
            target_kind = self._normalize_entity_link_kind(row["kind"])
            if target_kind == "image":
                continue
            result.append(
                self._legacy_link_view(
                    entity,
                    source=EntityRef("task", row["task_id"]),
                    target=EntityRef(target_kind, row["ref_id"]),
                    relation_kind="attached",
                    origin="task_attachments",
                    origin_id=row["id"],
                    created_at=row["created_at"],
                    metadata={"comment": str(row["comment"] or "")},
                )
            )
        return result

    def _fetch_context_link_views(self, entity: EntityRef) -> list[EntityLinkView]:
        rows = self._conn.execute(
            """
            SELECT id, source_type, source_id, target_type, target_id, anchor_text, source_field, created_at
            FROM context_entity_links
            WHERE (source_type = ? AND source_id = ?) OR (target_type = ? AND target_id = ?)
            ORDER BY created_at DESC, id DESC;
            """,
            (entity.kind, entity.id, entity.kind, entity.id),
        ).fetchall()
        return [
            self._legacy_link_view(
                entity,
                source=EntityRef(self._normalize_entity_link_kind(row["source_type"]), row["source_id"]),
                target=EntityRef(self._normalize_entity_link_kind(row["target_type"]), row["target_id"]),
                relation_kind="mentions",
                origin="context_entity_links",
                origin_id=row["id"],
                created_at=row["created_at"],
                metadata={
                    "anchor_text": str(row["anchor_text"] or ""),
                    "source_field": str(row["source_field"] or ""),
                },
            )
            for row in rows
        ]

    def _fetch_idea_relation_views(self, entity: EntityRef) -> list[EntityLinkView]:
        rows = self._conn.execute(
            """
            SELECT id, idea_id, entity_type, entity_id, relation_kind, created_at
            FROM idea_relations
            WHERE (idea_id = ?) OR (lower(entity_type) = ? AND entity_id = ?)
            ORDER BY created_at DESC, id DESC;
            """,
            (entity.id if entity.kind == "idea" else -1, entity.kind, entity.id),
        ).fetchall()
        return [
            self._legacy_link_view(
                entity,
                source=EntityRef("idea", row["idea_id"]),
                target=EntityRef(self._normalize_entity_link_kind(row["entity_type"]), row["entity_id"]),
                relation_kind=str(row["relation_kind"] or "related"),
                origin="idea_relations",
                origin_id=row["id"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def _fetch_dossier_link_views(self, entity: EntityRef) -> list[EntityLinkView]:
        rows = self._conn.execute(
            """
            SELECT id, dossier_id, entity_kind, entity_id, created_at
            FROM dossier_links
            WHERE (dossier_id = ?) OR (lower(entity_kind) = ? AND entity_id = ?)
            ORDER BY created_at DESC, id DESC;
            """,
            (entity.id if entity.kind == "dossier" else -1, entity.kind, entity.id),
        ).fetchall()
        return [
            self._legacy_link_view(
                entity,
                source=EntityRef("dossier", row["dossier_id"]),
                target=EntityRef(self._normalize_entity_link_kind(row["entity_kind"]), row["entity_id"]),
                relation_kind="attached",
                origin="dossier_links",
                origin_id=row["id"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def _fetch_collection_relation_views(self, entity: EntityRef) -> list[EntityLinkView]:
        if entity.kind != "collection_item":
            return []
        rows = self._conn.execute(
            """
            SELECT id, left_item_id, right_item_id, relation_kind, created_at
            FROM collection_relations
            WHERE left_item_id = ? OR right_item_id = ?
            ORDER BY created_at DESC, id DESC;
            """,
            (entity.id, entity.id),
        ).fetchall()
        result = []
        for row in rows:
            other_id = row["right_item_id"] if row["left_item_id"] == entity.id else row["left_item_id"]
            origin_id = int(row["id"])
            result.append(
                EntityLinkView(
                    link_id=f"collection_relations:{origin_id}",
                    entity=entity,
                    other_entity=EntityRef("collection_item", other_id),
                    direction="symmetric",
                    relation_kind="collection_relation",
                    origin="collection_relations",
                    origin_id=origin_id,
                    created_at=str(row["created_at"] or ""),
                    metadata={"legacy_relation_kind": str(row["relation_kind"] or "=")},
                )
            )
        return result

    @staticmethod
    def _legacy_link_view(
        entity: EntityRef,
        *,
        source: EntityRef,
        target: EntityRef,
        relation_kind: str,
        origin: str,
        origin_id: int,
        created_at: str,
        metadata: dict[str, object] | None = None,
    ) -> EntityLinkView:
        is_source = entity == source
        return EntityLinkView(
            link_id=f"{origin}:{int(origin_id)}",
            entity=entity,
            other_entity=target if is_source else source,
            direction="outgoing" if is_source else "incoming",
            relation_kind=str(relation_kind or "related"),
            origin=origin,
            origin_id=int(origin_id),
            created_at=str(created_at or ""),
            metadata=metadata or {},
        )


__all__ = ["DatabaseEntityLinksMixin"]
