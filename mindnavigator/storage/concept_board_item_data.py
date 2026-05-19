"""ConceptBoardItemData compatibility alias over legacy mutaboard storage rows."""

from __future__ import annotations

from .mutaboard_item_data import MutaBoardItemData as ConceptBoardItemData

MutaBoardItemData = ConceptBoardItemData

__all__ = ["ConceptBoardItemData", "MutaBoardItemData"]
