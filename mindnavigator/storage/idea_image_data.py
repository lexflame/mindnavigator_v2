"""IdeaImageData storage data class."""

from __future__ import annotations

from ._model_shared import *  # noqa: F401,F403


@dataclass(frozen=True)
class IdeaImageData:
    id: int
    idea_id: int
    rel_path: str
    caption: str
    created_at: str
    updated_at: str


__all__ = ["IdeaImageData"]
