"""CharacterData storage data class."""

from __future__ import annotations

from ._model_shared import *  # noqa: F401,F403

@dataclass(frozen=True)
class CharacterData:
    id: int
    name: str
    role: str
    description: str
    tags: List[str]
    created_at: str
    updated_at: str

__all__ = ["CharacterData"]
