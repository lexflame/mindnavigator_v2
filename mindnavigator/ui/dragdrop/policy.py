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

    def contains(self, point: Point) -> bool:
        px, py = point
        return self.x <= px <= self.x + self.width and self.y <= py <= self.y + self.height


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
    def resolve_zone(self, pos_global: Point, zones: list[DropZoneRect]) -> str | None:
        for zone in zones:
            if zone.contains(pos_global):
                return zone.zone_id
        return None


class AcceptAllValidator:
    def validate(self, payload: DragPayload, zone_id: str) -> bool:
        return True
