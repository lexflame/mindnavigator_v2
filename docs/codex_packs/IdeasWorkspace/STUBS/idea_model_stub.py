"""Idea model stub.

Адаптируй под стиль проекта (dataclass/pydantic/ORM).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Literal

IdeaType = Literal['feature', 'story', 'art', 'research', 'tech', 'other']
IdeaStatus = Literal['inbox', 'work', 'ripe', 'done', 'archived']


@dataclass
class Idea:
    id: str
    project_id: Optional[str] = None

    title: str = ''
    summary: Optional[str] = None
    body_md: str = ''

    type: IdeaType = 'other'
    status: IdeaStatus = 'inbox'

    value_score: int = 3  # 1..5
    effort_score: int = 3  # 1..5

    source: Optional[str] = None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None
