"""ConceptBoardData compatibility alias over legacy mutaboard storage rows."""

from __future__ import annotations

from .mutaboard_data import MutaBoardData as ConceptBoardData

MutaBoardData = ConceptBoardData

__all__ = ["ConceptBoardData", "MutaBoardData"]
