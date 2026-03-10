"""MapOverlayData storage data class."""

from __future__ import annotations

from ._model_shared import *  # noqa: F401,F403

@dataclass(frozen=True)
class MapOverlayData:
    id: int
    map_id: int
    kind: str
    points: List[Tuple[float, float]]
    color: str
    title: str
    created_at: str
    updated_at: str

__all__ = ["MapOverlayData"]
