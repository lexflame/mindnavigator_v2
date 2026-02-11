"""Collection item model for thematic links/images and cross-links."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

ALLOWED_COLLECTION_KINDS = ("image", "link", "note", "object")


def utc_now_iso() -> str:
    """Return current UTC timestamp in ISO-8601 format."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class CollectionItem:
    """Represents one collection item with flexible cross-links."""

    id: str = field(default_factory=lambda: str(uuid4()))
    title: str = ""
    kind: str = "link"
    url: str | None = None
    tags: list[str] = field(default_factory=list)
    links: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def __post_init__(self) -> None:
        self.title = (self.title or "").strip()
        self.kind = (self.kind or "link").strip().lower()
        if self.kind not in ALLOWED_COLLECTION_KINDS:
            raise ValueError(
                f"Collection kind must be one of {', '.join(ALLOWED_COLLECTION_KINDS)}."
            )
        self.url = (self.url or "").strip() or None
        self.tags = [str(tag).strip() for tag in self.tags if str(tag).strip()]

    def touch(self) -> None:
        """Update `updated_at` timestamp."""
        self.updated_at = utc_now_iso()

    def to_dict(self) -> dict[str, Any]:
        """Serialize item to JSON-friendly dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "kind": self.kind,
            "url": self.url,
            "tags": list(self.tags),
            "links": list(self.links),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CollectionItem":
        """Build item from a dictionary and ignore unknown fields."""
        return cls(
            id=str(payload.get("id") or uuid4()),
            title=str(payload.get("title") or ""),
            kind=str(payload.get("kind") or "link"),
            url=payload.get("url"),
            tags=payload.get("tags") if isinstance(payload.get("tags"), list) else [],
            links=payload.get("links") if isinstance(payload.get("links"), list) else [],
            created_at=str(payload.get("created_at") or utc_now_iso()),
            updated_at=str(payload.get("updated_at") or utc_now_iso()),
        )
