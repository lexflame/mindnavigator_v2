"""ConceptBoardSolutionData storage data class."""

from __future__ import annotations

from ._model_shared import *  # noqa: F401,F403


@dataclass(frozen=True)
class ConceptBoardSolutionData:
    id: int
    concept_board_id: int
    title: str
    summary: str
    why_selected: str
    rejected_text: str
    next_steps_text: str
    status: str
    selected_version_id: int | None
    decided_at: str
    created_at: datetime
    updated_at: datetime


__all__ = ["ConceptBoardSolutionData"]
