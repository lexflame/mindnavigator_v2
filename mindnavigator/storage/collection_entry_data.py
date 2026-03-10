"""CollectionEntryData storage data class."""

from __future__ import annotations

from ._model_shared import *  # noqa: F401,F403

@dataclass(frozen=True)
class CollectionEntryData:
    id: int
    collection_id: int
    source_path: str
    rel_path: str
    title: str
    ext: str
    mime: str
    size_bytes: int
    meta_json: str
    is_missing: bool
    created_at: str
    updated_at: str

__all__ = ["CollectionEntryData"]
