"""TaskAttachmentData storage data class."""

from __future__ import annotations

from ._model_shared import *  # noqa: F401,F403

@dataclass(frozen=True)
class TaskAttachmentData:
    id: int
    task_id: int
    kind: str
    ref_id: int
    created_at: str

    SUPPORTED_KINDS: ClassVar[tuple[str, ...]] = (
        "note",
        "object",
        "map",
        "marker",
        "file",
        "image",
        "idea",
    )

    @classmethod
    def normalize_kind(cls, kind: str) -> str:
        normalized = (kind or "").strip().lower()
        if normalized not in cls.SUPPORTED_KINDS:
            supported = ", ".join(cls.SUPPORTED_KINDS)
            raise ValueError(f"РќРµРїРѕРґРґРµСЂР¶РёРІР°РµРјС‹Р№ С‚РёРї РІР»РѕР¶РµРЅРёСЏ: {kind!r}. РћР¶РёРґР°РµС‚СЃСЏ: {supported}.")
        return normalized

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "TaskAttachmentData":
        return cls(
            id=int(row["id"]),
            task_id=int(row["task_id"]),
            kind=cls.normalize_kind(str(row["kind"])),
            ref_id=int(row["ref_id"]),
            created_at=str(row["created_at"]),
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TaskAttachmentData":
        return cls(
            id=int(payload.get("id", 0)),
            task_id=int(payload["task_id"]),
            kind=cls.normalize_kind(str(payload["kind"])),
            ref_id=int(payload["ref_id"]),
            created_at=str(payload.get("created_at", "")),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "id": int(self.id),
            "task_id": int(self.task_id),
            "kind": self.kind,
            "ref_id": int(self.ref_id),
            "created_at": self.created_at,
        }

__all__ = ["TaskAttachmentData"]
