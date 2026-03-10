"""ObjectData storage data class."""

from __future__ import annotations

from ._model_shared import *  # noqa: F401,F403

@dataclass(frozen=True)
class ObjectData:
    id: int
    title: str
    catalog: str
    object_type: str
    status: str
    description: str
    created_at: str
    updated_at: str

__all__ = ["ObjectData"]
