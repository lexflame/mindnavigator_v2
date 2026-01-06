
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from ..db import connect


@dataclass(frozen=True)
class FileItemDTO:
    id: int
    parent_id: Optional[int]
    is_dir: bool
    name: str
    ext: Optional[str]
    mime: Optional[str]
    size_bytes: Optional[int]
    local_path: Optional[str]
    preview_path: Optional[str]
    deleted: bool


class FilesRepo:
    def __init__(self, db_path=None):
        self._db_path = db_path

    def list_children(self, parent_id: Optional[int], text: Optional[str] = None, include_deleted: bool = False) -> List[FileItemDTO]:
        conn = connect(self._db_path)
        try:
            where = []
            params: list = []
            if not include_deleted:
                where.append("deleted_at IS NULL")
            if parent_id is None:
                where.append("parent_id IS NULL")
            else:
                where.append("parent_id = ?")
                params.append(parent_id)
            if text:
                where.append("name LIKE ?")
                params.append(f"%{text}%")
            where_sql = "WHERE " + " AND ".join(where)
            rows = conn.execute(
                f"SELECT id, parent_id, is_dir, name, ext, mime, size_bytes, local_path, preview_path, deleted_at "
                f"FROM files {where_sql} ORDER BY is_dir DESC, name COLLATE NOCASE ASC, id DESC",
                params,
            ).fetchall()
            out: List[FileItemDTO] = []
            for r in rows:
                out.append(
                    FileItemDTO(
                        id=int(r["id"]),
                        parent_id=(int(r["parent_id"]) if r["parent_id"] is not None else None),
                        is_dir=bool(r["is_dir"]),
                        name=str(r["name"]),
                        ext=(str(r["ext"]) if r["ext"] is not None else None),
                        mime=(str(r["mime"]) if r["mime"] is not None else None),
                        size_bytes=(int(r["size_bytes"]) if r["size_bytes"] is not None else None),
                        local_path=(str(r["local_path"]) if r["local_path"] is not None else None),
                        preview_path=(str(r["preview_path"]) if r["preview_path"] is not None else None),
                        deleted=(r["deleted_at"] is not None),
                    )
                )
            return out
        finally:
            conn.close()

    def create_folder(self, parent_id: Optional[int], name: str) -> int:
        conn = connect(self._db_path)
        try:
            cur = conn.execute(
                "INSERT INTO files(parent_id, is_dir, name, updated_at, created_at, deleted_at) "
                "VALUES(?, 1, ?, datetime('now'), datetime('now'), NULL)",
                (parent_id, name),
            )
            conn.commit()
            return int(cur.lastrowid)
        finally:
            conn.close()

    def create_file(self, parent_id: Optional[int], name: str, ext: Optional[str] = None, mime: Optional[str] = None,
                    size_bytes: Optional[int] = None, local_path: Optional[str] = None, preview_path: Optional[str] = None,
                    hash_summ_name: Optional[str] = None, hash_summ_data: Optional[str] = None, s3_key: Optional[str] = None) -> int:
        conn = connect(self._db_path)
        try:
            cur = conn.execute(
                "INSERT INTO files(parent_id, is_dir, name, ext, mime, size_bytes, local_path, preview_path, "
                "hash_summ_name, hash_summ_data, s3_key, updated_at, created_at, deleted_at) "
                "VALUES(?, 0, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'), NULL)",
                (parent_id, name, ext, mime, size_bytes, local_path, preview_path, hash_summ_name, hash_summ_data, s3_key),
            )
            conn.commit()
            return int(cur.lastrowid)
        finally:
            conn.close()

    def rename_item(self, file_id: int, new_name: str, new_ext: Optional[str] = None) -> None:
        conn = connect(self._db_path)
        try:
            conn.execute(
                "UPDATE files SET name=?, ext=?, updated_at=datetime('now') WHERE id=? AND deleted_at IS NULL",
                (new_name, new_ext, file_id),
            )
            conn.commit()
        finally:
            conn.close()

    def count_active_children(self, file_id: int) -> int:
        conn = connect(self._db_path)
        try:
            r = conn.execute("SELECT COUNT(1) AS c FROM files WHERE parent_id=? AND deleted_at IS NULL", (file_id,)).fetchone()
            return int(r["c"]) if r else 0
        finally:
            conn.close()

    def soft_delete_item(self, file_id: int) -> None:
        conn = connect(self._db_path)
        try:
            conn.execute(
                "UPDATE files SET deleted_at=datetime('now'), updated_at=datetime('now') WHERE id=? AND deleted_at IS NULL",
                (file_id,),
            )
            conn.commit()
        finally:
            conn.close()
