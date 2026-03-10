"""DatabaseSettingsCloudMixin for storage database operations."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403

class DatabaseSettingsCloudMixin:
    def get_setting(self, key: str, default: str = "") -> str:
        """Р’РѕР·РІСЂР°С‰Р°РµС‚ Р·РЅР°С‡РµРЅРёРµ РЅР°СЃС‚СЂРѕР№РєРё."""
        key = (key or "").strip()
        if not key:
            raise ValueError("РљР»СЋС‡ РЅР°СЃС‚СЂРѕР№РєРё РЅРµ РґРѕР»Р¶РµРЅ Р±С‹С‚СЊ РїСѓСЃС‚С‹Рј.")
        cur = self._conn.execute("SELECT value FROM settings WHERE key = ?;", (key,))
        row = cur.fetchone()
        if not row:
            return default
        return row["value"]

    def set_setting(self, key: str, value: str) -> None:
        """РЎРѕС…СЂР°РЅСЏРµС‚ Р·РЅР°С‡РµРЅРёРµ РЅР°СЃС‚СЂРѕР№РєРё."""
        key = (key or "").strip()
        if not key:
            raise ValueError("РљР»СЋС‡ РЅР°СЃС‚СЂРѕР№РєРё РЅРµ РґРѕР»Р¶РµРЅ Р±С‹С‚СЊ РїСѓСЃС‚С‹Рј.")
        value = (value or "").strip()
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO settings (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value;
                """,
                (key, value),
            )

    def upsert_cloud_file(
        self,
        *,
        rel_path: str,
        name: str,
        description: str,
        checksum: str,
        hash_value: str,
        size: int,
        is_image: bool,
        valid: bool,
    ) -> CloudFileData:
        """РЎРѕР·РґР°РµС‚ РёР»Рё РѕР±РЅРѕРІР»СЏРµС‚ Р·Р°РїРёСЃСЊ Рѕ С„Р°Р№Р»Рµ РѕР±Р»Р°РєР°."""
        rel_path = (rel_path or "").strip()
        if not rel_path:
            raise ValueError("РџСѓС‚СЊ С„Р°Р№Р»Р° РЅРµ РґРѕР»Р¶РµРЅ Р±С‹С‚СЊ РїСѓСЃС‚С‹Рј.")
        name = (name or "").strip()
        checksum = (checksum or "").strip()
        if not name or not checksum:
            raise ValueError("РРјСЏ С„Р°Р№Р»Р° Рё РєРѕРЅС‚СЂРѕР»СЊРЅР°СЏ СЃСѓРјРјР° РѕР±СЏР·Р°С‚РµР»СЊРЅС‹.")
        description = (description or "").strip()
        hash_value = (hash_value or "").strip()
        size = max(0, int(size))
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")

        with self._conn:
            self._conn.execute(
                """
                INSERT INTO cloud_files (rel_path, name, description, checksum, hash_value, size, is_image, valid, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(rel_path) DO UPDATE SET
                    name = excluded.name,
                    description = excluded.description,
                    checksum = excluded.checksum,
                    hash_value = excluded.hash_value,
                    size = excluded.size,
                    is_image = excluded.is_image,
                    valid = excluded.valid,
                    updated_at = excluded.updated_at;
                """,
                (
                    rel_path,
                    name,
                    description,
                    checksum,
                    hash_value,
                    size,
                    int(bool(is_image)),
                    int(bool(valid)),
                    now,
                ),
            )
        row = self._conn.execute(
            """
            SELECT id, rel_path, name, description, checksum, hash_value, size, is_image, valid, updated_at
            FROM cloud_files
            WHERE rel_path = ?;
            """,
            (rel_path,),
        ).fetchone()
        return CloudFileData(
            row["id"],
            row["rel_path"],
            row["name"],
            row["description"],
            row["checksum"],
            row["hash_value"],
            row["size"],
            bool(row["is_image"]),
            bool(row["valid"]),
            row["updated_at"],
        )

    def fetch_cloud_files(self) -> List[CloudFileData]:
        """Р’РѕР·РІСЂР°С‰Р°РµС‚ СЃРїРёСЃРѕРє С„Р°Р№Р»РѕРІ РѕР±Р»Р°РєР°."""
        rows = self._conn.execute(
            """
            SELECT id, rel_path, name, description, checksum, hash_value, size, is_image, valid, updated_at
            FROM cloud_files
            ORDER BY rel_path;
            """
        ).fetchall()
        return [
            CloudFileData(
                row["id"],
                row["rel_path"],
                row["name"],
                row["description"],
                row["checksum"],
                row["hash_value"],
                row["size"],
                bool(row["is_image"]),
                bool(row["valid"]),
                row["updated_at"],
            )
            for row in rows
        ]

    def remove_missing_cloud_files(self, rel_paths: Iterable[str]) -> None:
        """РЈРґР°Р»СЏРµС‚ Р·Р°РїРёСЃРё Рѕ С„Р°Р№Р»Р°С…, РєРѕС‚РѕСЂС‹С… РЅРµС‚ РІ РѕР±Р»Р°С‡РЅРѕРј РєР°С‚Р°Р»РѕРіРµ."""
        rel_paths = [path for path in rel_paths if path]
        with self._conn:
            if not rel_paths:
                self._conn.execute("DELETE FROM cloud_files;")
                return
            placeholders = ",".join("?" for _ in rel_paths)
            self._conn.execute(
                f"DELETE FROM cloud_files WHERE rel_path NOT IN ({placeholders});",
                rel_paths,
            )

__all__ = ["DatabaseSettingsCloudMixin"]
