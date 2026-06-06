"""Generate a deterministic MindNavigator database for local performance checks."""

from __future__ import annotations

import argparse
import random
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from mindnavigator.storage import Database


@dataclass(frozen=True)
class GenerationSummary:
    path: Path
    projects: int
    tasks: int
    links: int
    seed: int


def generate_database(
    output_path: Path,
    *,
    project_count: int = 100,
    task_count: int = 5_000,
    link_count: int = 1_000,
    seed: int = 20260607,
    overwrite: bool = False,
) -> GenerationSummary:
    output_path = Path(output_path)
    _validate_counts(project_count, task_count, link_count)
    if output_path.exists():
        if not overwrite:
            raise FileExistsError(f"Database already exists: {output_path}")
        output_path.unlink()
        for suffix in ("-wal", "-shm"):
            sidecar = Path(f"{output_path}{suffix}")
            if sidecar.exists():
                sidecar.unlink()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    Database(path=output_path).close()
    connection = sqlite3.connect(output_path)
    try:
        connection.execute("PRAGMA foreign_keys=ON;")
        rng = random.Random(seed)
        generated_at = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=seed % 86_400)
        now = generated_at.isoformat(timespec="seconds")
        base_day = date(2026, 1, 1)

        project_rows = []
        for index in range(project_count):
            parent_id = index if index > 0 and index % 5 == 0 else None
            project_rows.append(
                (
                    f"Area {index % 12:02d}",
                    f"Performance project {index + 1:05d}",
                    (base_day + timedelta(days=index % 365)).isoformat(),
                    ("Low", "Medium", "High")[index % 3],
                    parent_id,
                    index,
                )
            )

        task_rows = []
        for index in range(task_count):
            task_id = index + 1
            project_id = (index % project_count) + 1 if project_count else None
            parent_id = task_id - 1 if index > 0 and index % 10 == 0 else None
            done = int(index % 7 == 0)
            task_rows.append(
                (
                    f"Performance task {task_id:06d}",
                    f"Generated task {task_id} for repeatable local performance checks.",
                    (base_day + timedelta(days=rng.randrange(366))).isoformat(),
                    f"{8 + index % 10:02d}:{(index * 7) % 60:02d}",
                    ("Low", "Medium", "High")[index % 3],
                    1 + index % 5,
                    "completed" if done else ("in_progress" if index % 11 == 0 else "queue"),
                    done,
                    project_id,
                    parent_id,
                    int(index % 13 == 0),
                    index,
                    now,
                    now,
                )
            )

        link_rows = []
        for index in range(link_count):
            source_id = index % task_count + 1
            offset = index // task_count + 1
            target_id = (source_id - 1 + offset) % task_count + 1
            link_rows.append(("task", source_id, "task", target_id, "generated", "description", now))

        with connection:
            connection.execute("DELETE FROM context_entity_links;")
            connection.execute("DELETE FROM tasks;")
            connection.execute("DELETE FROM projects;")
            connection.execute(
                "DELETE FROM sqlite_sequence WHERE name IN ('context_entity_links', 'tasks', 'projects');"
            )
            connection.executemany(
                """
                INSERT INTO projects (area, title, updated, priority, parent_project_id, sort_order)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                project_rows,
            )
            connection.executemany(
                """
                INSERT INTO tasks (
                    title, description, day, time_text, priority, importance, board_column, done,
                    project_id, parent_id, is_plan_task, plan_order, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                task_rows,
            )
            connection.executemany(
                """
                INSERT INTO context_entity_links (
                    source_type, source_id, target_type, target_id, anchor_text, source_field, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                link_rows,
            )
            connection.execute("ANALYZE;")
    finally:
        connection.close()

    return GenerationSummary(output_path, project_count, task_count, link_count, seed)


def _validate_counts(project_count: int, task_count: int, link_count: int) -> None:
    if project_count < 0 or task_count < 0 or link_count < 0:
        raise ValueError("Entity counts cannot be negative.")
    if task_count and not project_count:
        raise ValueError("At least one project is required when tasks are generated.")
    max_links = task_count * max(0, task_count - 1)
    if link_count > max_links:
        raise ValueError(f"link_count cannot exceed {max_links} for {task_count} tasks.")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="Target SQLite database path.")
    parser.add_argument("--projects", type=int, default=100, help="Number of projects (default: 100).")
    parser.add_argument("--tasks", type=int, default=5_000, help="Number of tasks (default: 5000).")
    parser.add_argument("--links", type=int, default=1_000, help="Number of context links (default: 1000).")
    parser.add_argument("--seed", type=int, default=20260607, help="Deterministic random seed.")
    parser.add_argument("--overwrite", action="store_true", help="Replace an existing target database.")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    summary = generate_database(
        args.output,
        project_count=args.projects,
        task_count=args.tasks,
        link_count=args.links,
        seed=args.seed,
        overwrite=args.overwrite,
    )
    print(
        f"Created {summary.path} with {summary.projects} projects, "
        f"{summary.tasks} tasks, and {summary.links} links (seed={summary.seed})."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
