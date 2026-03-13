"""DossierData storage data class."""

from __future__ import annotations

import json

from ._model_shared import *  # noqa: F401,F403


@dataclass(frozen=True)
class DossierData:
    id: int
    kind: str
    title: str
    summary: str
    description: str
    tags: List[str]
    status: str
    rating: Optional[int]
    source: str
    cover_image: str
    metadata: dict[str, object]
    created_at: str
    updated_at: str

    SUPPORTED_KINDS: ClassVar[tuple[str, ...]] = ("book", "film", "game", "writer")
    SUPPORTED_STATUSES: ClassVar[tuple[str, ...]] = ("planned", "active", "completed", "on_hold", "archived")
    METADATA_FIELDS: ClassVar[dict[str, dict[str, str]]] = {
        "book": {
            "author_display": "str",
            "original_title": "str",
            "publication_year": "int",
            "genre": "str",
            "language": "str",
            "pages": "int",
            "publisher": "str",
            "series": "str",
            "isbn": "str",
        },
        "film": {
            "director": "str",
            "release_year": "int",
            "runtime_minutes": "int",
            "country": "str",
            "franchise": "str",
            "format": "str",
            "age_rating": "str",
            "genre": "str",
        },
        "game": {
            "developer": "str",
            "publisher": "str",
            "release_year": "int",
            "platforms": "list",
            "engine": "str",
            "genre": "str",
            "play_status": "str",
            "playtime_hours": "int",
            "series": "str",
        },
        "writer": {
            "birth_year": "int",
            "death_year": "int",
            "country": "str",
            "languages": "list",
            "primary_genres": "list",
            "notable_works_summary": "str",
        },
    }

    @classmethod
    def normalize_kind(cls, kind: str) -> str:
        normalized = str(kind or "").strip().lower()
        if normalized not in cls.SUPPORTED_KINDS:
            supported = ", ".join(cls.SUPPORTED_KINDS)
            raise ValueError(f"Unsupported dossier kind: {kind!r}. Expected one of: {supported}.")
        return normalized

    @classmethod
    def normalize_status(cls, status: str) -> str:
        normalized = str(status or "").strip().lower() or "planned"
        if normalized not in cls.SUPPORTED_STATUSES:
            supported = ", ".join(cls.SUPPORTED_STATUSES)
            raise ValueError(f"Unsupported dossier status: {status!r}. Expected one of: {supported}.")
        return normalized

    @staticmethod
    def normalize_tags(tags: Optional[List[str]]) -> List[str]:
        if not tags:
            return []
        normalized: List[str] = []
        for raw_tag in tags:
            tag = str(raw_tag or "").strip()
            if tag and tag not in normalized:
                normalized.append(tag)
        return normalized

    @staticmethod
    def normalize_rating(rating: Any) -> Optional[int]:
        if rating in (None, ""):
            return None
        value = int(rating)
        if value < 1 or value > 10:
            raise ValueError("Dossier rating must be between 1 and 10.")
        return value

    @staticmethod
    def _normalize_list_value(value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, str):
            raw_items = value.split(",")
        elif isinstance(value, (list, tuple, set)):
            raw_items = list(value)
        else:
            raw_items = [value]
        normalized: List[str] = []
        for raw_item in raw_items:
            item = str(raw_item or "").strip()
            if item and item not in normalized:
                normalized.append(item)
        return normalized

    @classmethod
    def normalize_metadata(
        cls,
        kind: str,
        metadata: Optional[Mapping[str, Any]],
        *,
        strict: bool = True,
    ) -> dict[str, object]:
        normalized_kind = cls.normalize_kind(kind)
        if metadata is None:
            return {}
        if not isinstance(metadata, Mapping):
            raise ValueError("Dossier metadata must be a mapping.")
        allowed = cls.METADATA_FIELDS[normalized_kind]
        normalized: dict[str, object] = {}
        for raw_key, raw_value in metadata.items():
            key = str(raw_key or "").strip()
            if key not in allowed:
                if not strict:
                    continue
                supported = ", ".join(sorted(allowed))
                raise ValueError(f"Unsupported metadata field for {normalized_kind}: {key!r}. Expected: {supported}.")
            field_type = allowed[key]
            if field_type == "int":
                if raw_value in (None, ""):
                    continue
                try:
                    value = int(raw_value)
                except (TypeError, ValueError):
                    if strict:
                        raise ValueError(f"Metadata field {key!r} must be an integer.") from None
                    continue
                if value < 0:
                    if not strict:
                        continue
                    raise ValueError(f"Metadata field {key!r} must not be negative.")
                normalized[key] = value
                continue
            if field_type == "list":
                items = cls._normalize_list_value(raw_value)
                if items:
                    normalized[key] = items
                continue
            text = str(raw_value or "").strip()
            if text:
                normalized[key] = text
        return normalized

    @classmethod
    def _load_tags(cls, raw_tags: Any) -> List[str]:
        try:
            parsed = json.loads(raw_tags or "[]")
        except (TypeError, json.JSONDecodeError):
            return []
        if not isinstance(parsed, list):
            return []
        return cls.normalize_tags([str(item) for item in parsed])

    @classmethod
    def _load_metadata(cls, kind: str, raw_metadata: Any) -> dict[str, object]:
        try:
            parsed = json.loads(raw_metadata or "{}")
        except (TypeError, json.JSONDecodeError):
            parsed = {}
        if not isinstance(parsed, Mapping):
            parsed = {}
        return cls.normalize_metadata(kind, parsed, strict=False)

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "DossierData":
        kind = cls.normalize_kind(str(row["kind"]))
        return cls(
            id=int(row["id"]),
            kind=kind,
            title=str(row["title"] or ""),
            summary=str(row["summary"] or ""),
            description=str(row["description"] or ""),
            tags=cls._load_tags(row["tags"]),
            status=cls.normalize_status(str(row["status"] or "")),
            rating=cls.normalize_rating(row["rating"]),
            source=str(row["source"] or ""),
            cover_image=str(row["cover_image"] or ""),
            metadata=cls._load_metadata(kind, row["metadata_json"]),
            created_at=str(row["created_at"] or ""),
            updated_at=str(row["updated_at"] or ""),
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "DossierData":
        kind = cls.normalize_kind(str(payload["kind"]))
        return cls(
            id=int(payload.get("id", 0)),
            kind=kind,
            title=str(payload["title"] or ""),
            summary=str(payload.get("summary", "") or ""),
            description=str(payload.get("description", "") or ""),
            tags=cls.normalize_tags(payload.get("tags", [])),
            status=cls.normalize_status(str(payload.get("status", "") or "planned")),
            rating=cls.normalize_rating(payload.get("rating")),
            source=str(payload.get("source", "") or ""),
            cover_image=str(payload.get("cover_image", "") or ""),
            metadata=cls.normalize_metadata(kind, payload.get("metadata", {})),
            created_at=str(payload.get("created_at", "") or ""),
            updated_at=str(payload.get("updated_at", "") or ""),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "id": int(self.id),
            "kind": self.kind,
            "title": self.title,
            "summary": self.summary,
            "description": self.description,
            "tags": list(self.tags),
            "status": self.status,
            "rating": self.rating,
            "source": self.source,
            "cover_image": self.cover_image,
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


__all__ = ["DossierData"]
