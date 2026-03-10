"""NoteData storage data class."""

from __future__ import annotations

from ._model_shared import *  # noqa: F401,F403

@dataclass(frozen=True)
class NoteData:
    id: int
    title: str
    preview: str
    tags: List[str]
    updated: datetime
    project: str
    favorite: bool = False
    attachment: bool = False
    locked: bool = False

__all__ = ["NoteData"]
