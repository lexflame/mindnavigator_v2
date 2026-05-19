"""ConceptBoardColumnData compatibility alias over legacy mutaboard storage rows."""

from __future__ import annotations

from .mutaboard_column_data import MutaBoardColumnData as ConceptBoardColumnData

MutaBoardColumnData = ConceptBoardColumnData

__all__ = ["ConceptBoardColumnData", "MutaBoardColumnData"]
