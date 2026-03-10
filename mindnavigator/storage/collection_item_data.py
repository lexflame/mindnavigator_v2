"""CollectionItemData storage data class."""

from __future__ import annotations

from ._model_shared import *  # noqa: F401,F403

@dataclass(frozen=True)
class CollectionItemData:
    id: int
    title: str
    category_id: Optional[int]
    entity_type: str
    topic: str
    image_url: str
    source_url: str
    description: str
    source_folder_path: str
    import_options_json: str
    created_at: str
    updated_at: str

__all__ = ["CollectionItemData"]
