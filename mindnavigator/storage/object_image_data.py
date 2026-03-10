"""ObjectImageData storage data class."""

from __future__ import annotations

from ._model_shared import *  # noqa: F401,F403

@dataclass(frozen=True)
class ObjectImageData:
    id: int
    object_id: int
    rel_path: str
    description: str
    created_at: str
    updated_at: str

__all__ = ["ObjectImageData"]
