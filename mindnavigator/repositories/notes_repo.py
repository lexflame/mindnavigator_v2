
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from ..db import connect


@dataclass(frozen=True)
class NoteDTO:
    id: int
    project_id: Optional[int]
    title: str
    content: str
    cover_path: Optional[str]
    source_url: Optional[str]
    folder: str
    deleted: bool


class NotesRepo:
    def __init__(self, db_path=None):
        self._db_path = db_path

    def list_notes(self, text: Optional[str] = None, folder: Optional[str] = None,
                   project_id: Optional[int] = None, include_deleted: bool = False) -> List[NoteDTO]:
        conn = connect(self._db_path)
        try:
            where = []
            params: list = []
            if not include_deleted:
                where.append("deleted_at IS NULL")
            if folder is not None and folder != "":
                where.append("folder = ?")
                params.append(folder)
            if project_id is not None:
                where.append("project_id = ?")
                params.append(project_id)
            if text:
                where.append("(title LIKE ? OR content LIKE ? OR source_url LIKE ?)")
                like = f"%{text}%"
                params.extend([like, like, like])
            where_sql = ("WHERE " + " AND ".join(where)) if where else ""
            rows = conn.execute(
                f"SELECT id, project_id, title, content, cover_path, source_url, folder, deleted_at "
                f"FROM notes {where_sql} ORDER BY updated_at DESC, id DESC",
                params,
            ).fetchall()
            out: List[NoteDTO] = []
            for r in rows:
                out.append(
                    NoteDTO(
                        id=int(r["id"]),
                        project_id=(int(r["project_id"]) if r["project_id"] is not None else None),
                        title=str(r["title"]),
                        content=str(r["content"] or ""),
                        cover_path=(str(r["cover_path"]) if r["cover_path"] is not None else None),
                        source_url=(str(r["source_url"]) if r["source_url"] is not None else None),
                        folder=str(r["folder"] or ""),
                        deleted=(r["deleted_at"] is not None),
                    )
                )
            return out
        finally:
            conn.close()

    def get_note(self, note_id: int, include_deleted: bool = False) -> Optional[NoteDTO]:
        conn = connect(self._db_path)
        try:
            extra = "" if include_deleted else "AND deleted_at IS NULL"
            r = conn.execute(
                f"SELECT id, project_id, title, content, cover_path, source_url, folder, deleted_at "
                f"FROM notes WHERE id=? {extra}",
                (note_id,),
            ).fetchone()
            if not r:
                return None
            return NoteDTO(
                id=int(r["id"]),
                project_id=(int(r["project_id"]) if r["project_id"] is not None else None),
                title=str(r["title"]),
                content=str(r["content"] or ""),
                cover_path=(str(r["cover_path"]) if r["cover_path"] is not None else None),
                source_url=(str(r["source_url"]) if r["source_url"] is not None else None),
                folder=str(r["folder"] or ""),
                deleted=(r["deleted_at"] is not None),
            )
        finally:
            conn.close()

    def create_note(self, title: str, content: str = "", project_id: Optional[int] = None,
                    cover_path: Optional[str] = None, source_url: Optional[str] = None, folder: str = "") -> int:
        conn = connect(self._db_path)
        try:
            cur = conn.execute(
                "INSERT INTO notes(project_id, title, content, cover_path, source_url, folder, updated_at, created_at, deleted_at) "
                "VALUES(?,?,?,?,?,?, datetime('now'), datetime('now'), NULL)",
                (project_id, title, content, cover_path, source_url, folder),
            )
            conn.commit()
            return int(cur.lastrowid)
        finally:
            conn.close()

    def update_note(self, note_id: int, title: str, content: str, project_id: Optional[int],
                    cover_path: Optional[str], source_url: Optional[str], folder: str) -> None:
        conn = connect(self._db_path)
        try:
            conn.execute(
                "UPDATE notes SET project_id=?, title=?, content=?, cover_path=?, source_url=?, folder=?, updated_at=datetime('now') "
                "WHERE id=? AND deleted_at IS NULL",
                (project_id, title, content, cover_path, source_url, folder, note_id),
            )
            conn.commit()
        finally:
            conn.close()

    def soft_delete_note(self, note_id: int) -> None:
        conn = connect(self._db_path)
        try:
            conn.execute(
                "UPDATE notes SET deleted_at=datetime('now'), updated_at=datetime('now') WHERE id=? AND deleted_at IS NULL",
                (note_id,),
            )
            conn.commit()
        finally:
            conn.close()
