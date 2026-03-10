"""CharacterLinkData storage data class."""

from __future__ import annotations

from ._model_shared import *  # noqa: F401,F403

@dataclass(frozen=True)
class CharacterLinkData:
    id: int
    character_id: int
    entity_kind: str
    entity_id: int
    created_at: str

__all__ = ["CharacterLinkData"]
