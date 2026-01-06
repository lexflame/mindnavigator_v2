from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from .db import connect


def seed_if_empty(db_path: Optional[str] = None) -> None:
    conn = connect(db_path)
    try:
        cur = conn.execute("SELECT COUNT(*) AS c FROM projects")
        if int(cur.fetchone()["c"]) > 0:
            return

        projects = [
            ("SPACE", "MindNavigator v2", "High", 0),
            ("SPACE", "Синхронизация FastAPI + S3", "Medium", 0),
            ("TACMap", "Редактор слоёв / маркеров", "High", 0),
            ("MakerTask", "ProjectsWorkspace UI (прототип)", "Medium", 0),
            ("MakerTask", "Drag&Drop планировщика", "High", 1),
            ("Wiki", "Cities: Skylines → DokuWiki", "Low", 0),
            ("Misc", "Сбор референсов / moodboard", "Low", 0),
        ]
        for area, title, pr, arch in projects:
            conn.execute(
                "INSERT INTO projects(area,title,priority,archived) VALUES (?,?,?,?)",
                (area, title, pr, arch),
            )
        conn.commit()

        proj_ids = {r["title"]: r["id"] for r in conn.execute("SELECT id,title FROM projects")}

        t0 = date.today()
        days = [t0 - timedelta(days=1), t0, t0 + timedelta(days=1), t0 + timedelta(days=2)]
        tasks = [
            (proj_ids.get("MindNavigator v2"), days[0].isoformat(), "13:00", "BorderDev", "High", 0),
            (proj_ids.get("MindNavigator v2"), days[0].isoformat(), "14:00", "Wiki → Picture", "High", 0),

            (proj_ids.get("MindNavigator v2"), days[1].isoformat(), "15:00", "Подумать над DragAndDrop для списка задач в режиме план", "Medium", 0),
            (proj_ids.get("Сбор референсов / moodboard"), days[1].isoformat(), "16:00", "Билеты ПДД", "Low", 0),
            (proj_ids.get("Сбор референсов / moodboard"), days[1].isoformat(), "17:00", "Просмотреть FAV", "Medium", 0),
            (proj_ids.get("Сбор референсов / moodboard"), days[1].isoformat(), "19:00", "Просмотреть записи во всех каналах Избранного", "Medium", 0),

            (proj_ids.get("Cities: Skylines → DokuWiki"), days[2].isoformat(), "20:00", "SimCity Societies → KitBash → Здания усадьбы. Здание школы. Многоэтажка…", "High", 0),

            (proj_ids.get("Cities: Skylines → DokuWiki"), days[3].isoformat(), "22:00", "Stygian · Reign of the Old Ones", "High", 0),
            (proj_ids.get("Cities: Skylines → DokuWiki"), days[3].isoformat(), "23:00", "The Council", "High", 1),
        ]
        for project_id, day, time_text, title, pr, done in tasks:
            conn.execute(
                "INSERT INTO tasks(project_id,day,time_text,title,priority,done) VALUES (?,?,?,?,?,?)",
                (project_id, day, time_text, title, pr, done),
            )
        conn.commit()
    finally:
        conn.close()
