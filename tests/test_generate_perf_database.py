from __future__ import annotations

import sqlite3

import pytest

from scripts.generate_perf_database import generate_database


def test_generate_perf_database_creates_deterministic_fixture(unique_temp_path) -> None:
    first_path = unique_temp_path("perf_fixture_first", ".sqlite3")
    second_path = unique_temp_path("perf_fixture_second", ".sqlite3")

    first = generate_database(first_path, project_count=3, task_count=12, link_count=8, seed=17)
    second = generate_database(second_path, project_count=3, task_count=12, link_count=8, seed=17)

    assert (first.projects, first.tasks, first.links, first.seed) == (3, 12, 8, 17)
    with sqlite3.connect(first_path) as first_connection, sqlite3.connect(second_path) as second_connection:
        assert first_connection.execute("SELECT COUNT(*) FROM projects").fetchone()[0] == 3
        assert first_connection.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 12
        assert first_connection.execute("SELECT COUNT(*) FROM context_entity_links").fetchone()[0] == 8
        assert first_connection.execute("PRAGMA foreign_key_check").fetchall() == []
        first_sample = first_connection.execute(
            "SELECT title, day, priority, project_id, parent_id FROM tasks ORDER BY id"
        ).fetchall()
        second_sample = second_connection.execute(
            "SELECT title, day, priority, project_id, parent_id FROM tasks ORDER BY id"
        ).fetchall()
        assert first_sample == second_sample


def test_generate_perf_database_refuses_existing_target(unique_temp_path) -> None:
    output_path = unique_temp_path("perf_fixture_existing", ".sqlite3")
    generate_database(output_path, project_count=1, task_count=2, link_count=1)

    with pytest.raises(FileExistsError):
        generate_database(output_path, project_count=1, task_count=2, link_count=1)
