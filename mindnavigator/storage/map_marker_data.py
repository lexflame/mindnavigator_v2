"""MapMarkerData storage data class."""

from __future__ import annotations

from ._model_shared import *  # noqa: F401,F403

@dataclass(frozen=True)
class MapMarkerData:
    id: int
    map_id: int
    name: str
    x: float
    y: float
    color: str
    type: str
    size: float
    description: str
    properties: str
    task_ids: List[int]
    project_ids: List[int]
    note_ids: List[int]
    object_ids: List[int]
    file_ids: List[int]
    map_ids: List[int]
    marker_ids: List[int]
    parent_path: str
    image_path: str
    created_at: str
    updated_at: str

__all__ = ["MapMarkerData"]
