from __future__ import annotations

import json

import pytest

from scripts.generate_perf_database import generate_database
from scripts.run_perf_benchmarks import format_report, percentile, run_benchmarks, write_report


def test_percentile_interpolates_sorted_values() -> None:
    values = [40.0, 10.0, 30.0, 20.0]

    assert percentile(values, 0.50) == 25.0
    assert percentile(values, 0.95) == pytest.approx(38.5)


def test_run_perf_benchmarks_and_write_report(unique_temp_path) -> None:
    database_path = unique_temp_path("perf_benchmark", ".sqlite3")
    report_path = unique_temp_path("perf_benchmark_report", ".json")
    generate_database(database_path, project_count=3, task_count=20, link_count=5, seed=17)

    report = run_benchmarks(
        database_path,
        iterations=2,
        warmup=1,
        queries=("Performance task 000001",),
    )

    assert [result.operation for result in report.results] == [
        "fetch_tasks",
        "global_search",
        "tasks_model_reload",
    ]
    assert report.results[0].result_count == 20
    assert report.results[1].result_count == 1
    assert report.results[2].result_count > 0
    assert all(result.iterations == 2 and result.p50_ms >= 0 for result in report.results)
    assert "fetch_tasks" in format_report(report)

    write_report(report, report_path)
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["database"] == str(database_path.resolve())
    assert payload["results"][1]["operation"] == "global_search"
