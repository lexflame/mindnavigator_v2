"""WishlistData storage data class."""

from __future__ import annotations

from ._model_shared import *  # noqa: F401,F403

@dataclass(frozen=True)
class WishlistData:
    id: int
    title: str
    notes: str

__all__ = ["WishlistData"]
