"""DatabaseCoreMixin for storage database operations."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403

class DatabaseCoreMixin:
    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path) if path else default_db_path()
        self._conn = sqlite3.connect(
            self.path,
            check_same_thread=False,
            timeout=SQLITE_BUSY_TIMEOUT_MS / 1000,
        )
        self._conn.row_factory = sqlite3.Row
        self._closed = False
        self._init_db()

    def reindex(self) -> None:
        """РџРµСЂРµРёРЅРґРµРєСЃРёСЂСѓРµС‚ С‚Р°Р±Р»РёС†С‹ Р±Р°Р·С‹ РґР°РЅРЅС‹С…."""
        with self._conn:
            self._conn.execute("REINDEX;")

    def backup_to(self, destination_path: Path) -> Path:
        """РЎРѕР·РґР°РµС‚ РєРѕРЅСЃРёСЃС‚РµРЅС‚РЅСѓСЋ РєРѕРїРёСЋ Р±Р°Р·С‹ РґР°РЅРЅС‹С… РІ СѓРєР°Р·Р°РЅРЅС‹Р№ С„Р°Р№Р»."""
        destination_path = Path(destination_path)
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        if destination_path.resolve() == self.path.resolve():
            return destination_path
        tmp_target = destination_path.with_suffix(f"{destination_path.suffix}.tmp")
        if tmp_target.exists():
            tmp_target.unlink()
        with self._conn:
            self._conn.execute("PRAGMA wal_checkpoint(FULL);")
        target_conn = sqlite3.connect(tmp_target)
        try:
            self._conn.backup(target_conn)
            target_conn.commit()
        finally:
            target_conn.close()
        tmp_target.replace(destination_path)
        return destination_path

    def close(self) -> None:
        """Р—Р°РєСЂС‹РІР°РµС‚ СЃРѕРµРґРёРЅРµРЅРёРµ СЃ Р±Р°Р·РѕР№ РґР°РЅРЅС‹С…."""
        if self._closed:
            return
        self._conn.close()
        self._closed = True

__all__ = ["DatabaseCoreMixin"]
