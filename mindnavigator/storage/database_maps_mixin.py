"""DatabaseMapsMixin for storage database operations."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403

class DatabaseMapsMixin:
    def fetch_maps(self) -> List[MapData]:
        """Возвращает список карт."""
        rows = self._conn.execute(
            "SELECT id, title, description, project, tiles_path, tiles_h, tiles_w FROM maps;"
        ).fetchall()
        maps = []
        for row in rows:
            maps.append(
                MapData(
                    id=row["id"],
                    title=row["title"],
                    description=row["description"] or "",
                    project=row["project"] or "",
                    tiles_path=row["tiles_path"] or "",
                    tiles_h=row["tiles_h"],
                    tiles_w=row["tiles_w"],
                )
            )
        return maps

    def create_map(
        self,
        title: str,
        description: str,
        project: str,
        tiles_path: str,
        tiles_h: int,
        tiles_w: int,
    ) -> MapData:
        """Создает карту."""
        title = validate_title(title, field_name="Название карты")
        description = (description or "").strip()
        project = (project or "").strip()
        tiles_path = (tiles_path or "").strip()
        if tiles_h <= 0 or tiles_w <= 0:
            raise ValueError("Размер сетки должен быть больше нуля.")

        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            cur = self._conn.execute(
                """
                INSERT INTO maps (title, description, project, tiles_path, tiles_h, tiles_w, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (title, description, project, tiles_path, tiles_h, tiles_w, now, now),
            )
        return MapData(cur.lastrowid, title, description, project, tiles_path, tiles_h, tiles_w)

    def update_map(
        self,
        map_id: int,
        title: str,
        description: str,
        project: str,
        tiles_path: str,
        tiles_h: int,
        tiles_w: int,
    ) -> MapData:
        """Обновляет свойства карты."""
        title = validate_title(title, field_name="Название карты")
        description = (description or "").strip()
        project = (project or "").strip()
        tiles_path = (tiles_path or "").strip()
        if tiles_h <= 0 or tiles_w <= 0:
            raise ValueError("Размер сетки должен быть больше нуля.")

        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                """
                UPDATE maps
                SET title = ?, description = ?, project = ?, tiles_path = ?, tiles_h = ?, tiles_w = ?, updated_at = ?
                WHERE id = ?;
                """,
                (title, description, project, tiles_path, tiles_h, tiles_w, now, map_id),
            )
        return MapData(map_id, title, description, project, tiles_path, tiles_h, tiles_w)

    def delete_map(self, map_id: int) -> None:
        """Удаляет карту и связанные с ней графические данные."""
        with self._conn:
            self._conn.execute("DELETE FROM map_markers WHERE map_id = ?;", (map_id,))
            self._conn.execute("DELETE FROM map_overlays WHERE map_id = ?;", (map_id,))
            self._conn.execute("DELETE FROM maps WHERE id = ?;", (map_id,))

    def fetch_map_markers(self, map_id: Optional[int] = None) -> List[MapMarkerData]:
        """Возвращает список меток карты."""
        if map_id is None:
            rows = self._conn.execute(
                """
                SELECT
                    id,
                    map_id,
                    name,
                    x,
                    y,
                    color,
                    type,
                    size,
                    description,
                    properties,
                    task_ids,
                    project_ids,
                    note_ids,
                    object_ids,
                    file_ids,
                    map_ids,
                    marker_ids,
                    parent_path,
                    image_path,
                    created_at,
                    updated_at
                FROM map_markers;
                """
            ).fetchall()
        else:
            rows = self._conn.execute(
                """
                SELECT
                    id,
                    map_id,
                    name,
                    x,
                    y,
                    color,
                    type,
                    size,
                    description,
                    properties,
                    task_ids,
                    project_ids,
                    note_ids,
                    object_ids,
                    file_ids,
                    map_ids,
                    marker_ids,
                    parent_path,
                    image_path,
                    created_at,
                    updated_at
                FROM map_markers
                WHERE map_id = ?;
                """,
                (map_id,),
            ).fetchall()
        markers = []
        for row in rows:
            markers.append(
                MapMarkerData(
                    id=row["id"],
                    map_id=row["map_id"],
                    name=row["name"],
                    x=row["x"],
                    y=row["y"],
                    color=row["color"],
                    type=row["type"],
                    size=row["size"],
                    description=row["description"] or "",
                    properties=row["properties"] or "",
                    task_ids=json.loads(row["task_ids"] or "[]"),
                    project_ids=json.loads(row["project_ids"] or "[]"),
                    note_ids=json.loads(row["note_ids"] or "[]"),
                    object_ids=json.loads(row["object_ids"] or "[]"),
                    file_ids=json.loads(row["file_ids"] or "[]"),
                    map_ids=json.loads(row["map_ids"] or "[]"),
                    marker_ids=json.loads(row["marker_ids"] or "[]"),
                    parent_path=row["parent_path"] or "",
                    image_path=row["image_path"] or "",
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
            )
        return markers

    def upsert_map_marker(
        self,
        marker_id: int,
        map_id: int,
        name: str,
        x: float,
        y: float,
        color: str,
        marker_type: str,
        size: float,
        description: str = "",
        properties: str = "",
        task_ids: Optional[List[int]] = None,
        project_ids: Optional[List[int]] = None,
        note_ids: Optional[List[int]] = None,
        object_ids: Optional[List[int]] = None,
        file_ids: Optional[List[int]] = None,
        map_ids: Optional[List[int]] = None,
        marker_ids: Optional[List[int]] = None,
        parent_path: str = "",
        image_path: str = "",
    ) -> MapMarkerData:
        """Создает или обновляет метку карты."""
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        task_ids = task_ids or []
        project_ids = project_ids or []
        note_ids = note_ids or []
        object_ids = object_ids or []
        file_ids = file_ids or []
        map_ids = map_ids or []
        marker_ids = marker_ids or []
        parent_path = (parent_path or "").strip()
        image_path = (image_path or "").strip()
        payload = (
            marker_id,
            map_id,
            name,
            x,
            y,
            color,
            marker_type,
            size,
            description,
            properties,
            json.dumps(task_ids, ensure_ascii=False),
            json.dumps(project_ids, ensure_ascii=False),
            json.dumps(note_ids, ensure_ascii=False),
            json.dumps(object_ids, ensure_ascii=False),
            json.dumps(file_ids, ensure_ascii=False),
            json.dumps(map_ids, ensure_ascii=False),
            json.dumps(marker_ids, ensure_ascii=False),
            parent_path,
            image_path,
            now,
            now,
        )
        if self._task_project_fk_needs_repair():
            self._repair_task_project_fk()
        self._ensure_map_marker_foreign_keys()
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO map_markers (
                    id,
                    map_id,
                    name,
                    x,
                    y,
                    color,
                    type,
                    size,
                    description,
                    properties,
                    task_ids,
                    project_ids,
                    note_ids,
                    object_ids,
                    file_ids,
                    map_ids,
                    marker_ids,
                    parent_path,
                    image_path,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    map_id = excluded.map_id,
                    name = excluded.name,
                    x = excluded.x,
                    y = excluded.y,
                    color = excluded.color,
                    type = excluded.type,
                    size = excluded.size,
                    description = excluded.description,
                    properties = excluded.properties,
                    task_ids = excluded.task_ids,
                    project_ids = excluded.project_ids,
                    note_ids = excluded.note_ids,
                    object_ids = excluded.object_ids,
                    file_ids = excluded.file_ids,
                    map_ids = excluded.map_ids,
                    marker_ids = excluded.marker_ids,
                    parent_path = excluded.parent_path,
                    image_path = excluded.image_path,
                    created_at = map_markers.created_at,
                    updated_at = excluded.updated_at;
                """,
                payload,
            )
        row = self._conn.execute(
            """
            SELECT
                id,
                map_id,
                name,
                x,
                y,
                color,
                type,
                size,
                description,
                properties,
                task_ids,
                project_ids,
                note_ids,
                object_ids,
                file_ids,
                map_ids,
                marker_ids,
                parent_path,
                image_path,
                created_at,
                updated_at
            FROM map_markers
            WHERE id = ?;
            """,
            (marker_id,),
        ).fetchone()
        return MapMarkerData(
            id=row["id"],
            map_id=row["map_id"],
            name=row["name"],
            x=row["x"],
            y=row["y"],
            color=row["color"],
            type=row["type"],
            size=row["size"],
            description=row["description"] or "",
            properties=row["properties"] or "",
            task_ids=json.loads(row["task_ids"] or "[]"),
            project_ids=json.loads(row["project_ids"] or "[]"),
            note_ids=json.loads(row["note_ids"] or "[]"),
            object_ids=json.loads(row["object_ids"] or "[]"),
            file_ids=json.loads(row["file_ids"] or "[]"),
            map_ids=json.loads(row["map_ids"] or "[]"),
            marker_ids=json.loads(row["marker_ids"] or "[]"),
            parent_path=row["parent_path"] or "",
            image_path=row["image_path"] or "",
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def delete_map_marker(self, marker_id: int) -> None:
        """Удаляет метку карты."""
        with self._conn:
            self._conn.execute("DELETE FROM map_markers WHERE id = ?;", (marker_id,))

    def fetch_map_overlays(self, map_id: Optional[int] = None) -> List[MapOverlayData]:
        """Возвращает список геометрий карты (области/пути)."""
        if map_id is None:
            rows = self._conn.execute(
                """
                SELECT id, map_id, kind, points, color, title, created_at, updated_at
                FROM map_overlays;
                """
            ).fetchall()
        else:
            rows = self._conn.execute(
                """
                SELECT id, map_id, kind, points, color, title, created_at, updated_at
                FROM map_overlays
                WHERE map_id = ?;
                """,
                (map_id,),
            ).fetchall()
        overlays: List[MapOverlayData] = []
        for row in rows:
            parsed = []
            try:
                raw_points = json.loads(row["points"] or "[]")
            except json.JSONDecodeError:
                raw_points = []
            for pair in raw_points:
                if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                    continue
                try:
                    parsed.append((float(pair[0]), float(pair[1])))
                except (TypeError, ValueError):
                    continue
            overlays.append(
                MapOverlayData(
                    id=row["id"],
                    map_id=row["map_id"],
                    kind=row["kind"],
                    points=parsed,
                    color=row["color"] or "#6cb5ff",
                    title=row["title"] or "",
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
            )
        return overlays

    def create_map_overlay(
        self,
        map_id: int,
        kind: str,
        points: List[Tuple[float, float]],
        color: str,
        title: str = "",
    ) -> MapOverlayData:
        """Создает геометрию карты и возвращает сохраненную запись."""
        overlay_kind = (kind or "").strip().lower()
        if overlay_kind not in {"region", "path"}:
            raise ValueError("Некорректный тип геометрии карты.")
        normalized: List[Tuple[float, float]] = []
        for pair in points or []:
            if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                continue
            try:
                normalized.append((float(pair[0]), float(pair[1])))
            except (TypeError, ValueError):
                continue
        min_points = 3 if overlay_kind == "region" else 2
        if len(normalized) < min_points:
            raise ValueError("Недостаточно точек для сохранения геометрии.")
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        color_value = (color or "").strip() or "#6cb5ff"
        title_value = (title or "").strip()
        with self._conn:
            cur = self._conn.execute(
                """
                INSERT INTO map_overlays (map_id, kind, points, color, title, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    map_id,
                    overlay_kind,
                    json.dumps([[x, y] for x, y in normalized], ensure_ascii=False),
                    color_value,
                    title_value,
                    now,
                    now,
                ),
            )
        return MapOverlayData(
            id=cur.lastrowid,
            map_id=map_id,
            kind=overlay_kind,
            points=normalized,
            color=color_value,
            title=title_value,
            created_at=now,
            updated_at=now,
        )

    def update_map_overlay(
        self,
        overlay_id: int,
        kind: str,
        points: List[Tuple[float, float]],
        color: str,
        title: str = "",
    ) -> MapOverlayData:
        """Обновляет геометрию карты и возвращает актуальную запись."""
        overlay_kind = (kind or "").strip().lower()
        if overlay_kind not in {"region", "path"}:
            raise ValueError("Некорректный тип геометрии карты.")
        normalized: List[Tuple[float, float]] = []
        for pair in points or []:
            if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                continue
            try:
                normalized.append((float(pair[0]), float(pair[1])))
            except (TypeError, ValueError):
                continue
        min_points = 3 if overlay_kind == "region" else 2
        if len(normalized) < min_points:
            raise ValueError("Недостаточно точек для сохранения геометрии.")
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        color_value = (color or "").strip() or "#6cb5ff"
        title_value = (title or "").strip()
        with self._conn:
            self._conn.execute(
                """
                UPDATE map_overlays
                SET kind = ?, points = ?, color = ?, title = ?, updated_at = ?
                WHERE id = ?;
                """,
                (
                    overlay_kind,
                    json.dumps([[x, y] for x, y in normalized], ensure_ascii=False),
                    color_value,
                    title_value,
                    now,
                    overlay_id,
                ),
            )
        row = self._conn.execute(
            """
            SELECT id, map_id, kind, points, color, title, created_at, updated_at
            FROM map_overlays
            WHERE id = ?;
            """,
            (overlay_id,),
        ).fetchone()
        if not row:
            raise ValueError("Геометрия карты не найдена.")
        parsed = []
        try:
            raw_points = json.loads(row["points"] or "[]")
        except json.JSONDecodeError:
            raw_points = []
        for pair in raw_points:
            if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                continue
            try:
                parsed.append((float(pair[0]), float(pair[1])))
            except (TypeError, ValueError):
                continue
        return MapOverlayData(
            id=row["id"],
            map_id=row["map_id"],
            kind=row["kind"],
            points=parsed,
            color=row["color"] or "#6cb5ff",
            title=row["title"] or "",
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def delete_map_overlay(self, overlay_id: int) -> None:
        """Удаляет геометрию карты."""
        with self._conn:
            self._conn.execute("DELETE FROM map_overlays WHERE id = ?;", (overlay_id,))

__all__ = ["DatabaseMapsMixin"]
