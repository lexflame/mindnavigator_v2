"""DossierLinkData storage data class."""

from __future__ import annotations

from ._model_shared import *  # noqa: F401,F403


@dataclass(frozen=True)
class DossierLinkData:
    id: int
    dossier_id: int
    entity_kind: str
    entity_id: int
    created_at: str

    SUPPORTED_ENTITY_KINDS: ClassVar[tuple[str, ...]] = (
        "task",
        "map",
        "marker",
        "note",
        "idea",
        "object",
        "character",
    )

    @classmethod
    def normalize_entity_kind(cls, entity_kind: str) -> str:
        normalized = str(entity_kind or "").strip().lower()
        if normalized not in cls.SUPPORTED_ENTITY_KINDS:
            supported = ", ".join(cls.SUPPORTED_ENTITY_KINDS)
            raise ValueError(f"Unsupported dossier link kind: {entity_kind!r}. Expected one of: {supported}.")
        return normalized

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "DossierLinkData":
        return cls(
            id=int(row["id"]),
            dossier_id=int(row["dossier_id"]),
            entity_kind=cls.normalize_entity_kind(str(row["entity_kind"])),
            entity_id=int(row["entity_id"]),
            created_at=str(row["created_at"] or ""),
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "DossierLinkData":
        return cls(
            id=int(payload.get("id", 0)),
            dossier_id=int(payload["dossier_id"]),
            entity_kind=cls.normalize_entity_kind(str(payload["entity_kind"])),
            entity_id=int(payload["entity_id"]),
            created_at=str(payload.get("created_at", "") or ""),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "id": int(self.id),
            "dossier_id": int(self.dossier_id),
            "entity_kind": self.entity_kind,
            "entity_id": int(self.entity_id),
            "created_at": self.created_at,
        }


__all__ = ["DossierLinkData"]
