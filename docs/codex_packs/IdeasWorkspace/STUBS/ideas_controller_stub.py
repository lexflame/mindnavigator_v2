"""Ideas controller/repository stub.

Подключи к твоему DB-слою (SQLite), паттерну MVC и системе синхронизации.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .idea_model_stub import Idea


class IdeasController:
    def __init__(self, db: Any):
        self.db = db

    def list(self, project_id: Optional[str] = None, search: Optional[str] = None,
             status: Optional[str] = None, type_: Optional[str] = None,
             tags: Optional[List[str]] = None, archived: bool = False) -> List[Idea]:
        """Return ideas sorted by updated_at DESC."""
        raise NotImplementedError

    def get(self, idea_id: str) -> Optional[Idea]:
        raise NotImplementedError

    def create(self, payload: Dict[str, Any]) -> Idea:
        raise NotImplementedError

    def update(self, idea_id: str, payload: Dict[str, Any]) -> Idea:
        raise NotImplementedError

    def archive(self, idea_id: str) -> None:
        raise NotImplementedError

    def unarchive(self, idea_id: str) -> None:
        raise NotImplementedError

    def delete(self, idea_id: str) -> None:
        raise NotImplementedError

    # Optional helpers for links/tags/relations
    def add_link(self, idea_id: str, url: str, title: Optional[str] = None) -> None:
        raise NotImplementedError

    def add_tag(self, idea_id: str, tag_text: str) -> None:
        raise NotImplementedError

    def add_relation(self, idea_id: str, entity_type: str, entity_id: str) -> None:
        raise NotImplementedError
