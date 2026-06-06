"""Normalized read models for links stored in legacy relation tables."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True, order=True)
class EntityRef:
    kind: str
    id: int

    def __post_init__(self) -> None:
        normalized_kind = str(self.kind or "").strip().lower()
        normalized_id = int(self.id)
        if not normalized_kind:
            raise ValueError("Entity kind cannot be empty.")
        if normalized_id <= 0:
            raise ValueError("Entity id must be positive.")
        object.__setattr__(self, "kind", normalized_kind)
        object.__setattr__(self, "id", normalized_id)


@dataclass(frozen=True)
class EntityLinkView:
    link_id: str
    entity: EntityRef
    other_entity: EntityRef
    direction: str
    relation_kind: str
    origin: str
    origin_id: int
    created_at: str
    metadata: Mapping[str, object] = field(default_factory=dict)


__all__ = ["EntityLinkView", "EntityRef"]
