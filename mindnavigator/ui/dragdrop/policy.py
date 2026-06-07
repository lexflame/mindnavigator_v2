from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .model import DragPayload, Point


@dataclass(slots=True, frozen=True)
class DropZoneRect:
    zone_id: str
    x: int
    y: int
    width: int
    height: int
    priority: int = 0
    parent_zone_id: str | None = None

    def contains(self, point: Point) -> bool:
        px, py = point
        return self.x <= px <= self.x + self.width and self.y <= py <= self.y + self.height

    def area(self) -> int:
        return self.width * self.height


class DropValidator(Protocol):
    def validate(self, payload: DragPayload, zone_id: str) -> bool:
        ...


class DropExecutor(Protocol):
    def execute(self, payload: DragPayload, zone_id: str) -> bool:
        ...


class HitTestService(Protocol):
    def resolve_zone(self, pos_global: Point, zones: list[DropZoneRect]) -> str | None:
        ...


class DefaultHitTestService:
    @staticmethod
    def resolve_zone(pos_global: Point, zones: list[DropZoneRect]) -> str | None:
        for zone in zones:
            if zone.contains(pos_global):
                return zone.zone_id
        return None


class NestedHitTestService:
    """Resolves the most specific zone among nested/overlapping candidates."""

    @staticmethod
    def resolve_zone(pos_global: Point, zones: list[DropZoneRect]) -> str | None:
        candidates = [zone for zone in zones if zone.contains(pos_global)]
        if not candidates:
            return None

        # Higher priority wins; for equal priority, smaller area is treated as more specific.
        candidates.sort(key=lambda z: (z.priority, -z.area()), reverse=True)
        return candidates[0].zone_id


class AcceptAllValidator:
    @staticmethod
    def validate(_payload: DragPayload, _zone_id: str) -> bool:
        return True


class RuleBasedDropValidator:
    def __init__(self, allowed_map: dict[str, set[str]]) -> None:
        self._allowed_map = allowed_map

    def validate(self, payload: DragPayload, zone_id: str) -> bool:
        allowed = self._allowed_map.get(zone_id)
        if allowed is None:
            return False
        return payload.entity_type in allowed


class EntityLinkDropPolicy:
    """Defines entity pairs that may create links through drag and drop."""

    _ALLOWED_SOURCES_BY_TARGET = {
        "idea": {"task", "note", "object", "map", "marker", "concept_board"},
    }

    @classmethod
    def can_link(
        cls,
        source_kind: str,
        source_id: int,
        target_kind: str,
        target_id: int,
    ) -> bool:
        normalized_source = str(source_kind or "").strip().lower()
        normalized_target = str(target_kind or "").strip().lower()
        try:
            normalized_source_id = int(source_id)
            normalized_target_id = int(target_id)
        except (TypeError, ValueError):
            return False
        if normalized_source_id <= 0 or normalized_target_id <= 0:
            return False
        if normalized_source == normalized_target and normalized_source_id == normalized_target_id:
            return False
        return normalized_source in cls._ALLOWED_SOURCES_BY_TARGET.get(normalized_target, set())
