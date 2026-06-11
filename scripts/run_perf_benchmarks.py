"""Measure key MindNavigator read operations on an existing database."""

from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Sequence

from mindnavigator.services import GlobalSearchService
from mindnavigator.storage import Database

_QT_APP = None


@dataclass(frozen=True)
class BenchmarkResult:
    operation: str
    iterations: int
    result_count: int
    min_ms: float
    p50_ms: float
    p95_ms: float
    max_ms: float
    mean_ms: float


@dataclass(frozen=True)
class BenchmarkReport:
    database: str
    generated_at: str
    python: str
    platform: str
    warmup: int
    results: list[BenchmarkResult]


def percentile(values: Sequence[float], quantile: float) -> float:
    if not values:
        raise ValueError("Cannot calculate a percentile for an empty sequence.")
    if not 0 <= quantile <= 1:
        raise ValueError("quantile must be between 0 and 1.")
    ordered = sorted(float(value) for value in values)
    position = (len(ordered) - 1) * quantile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def measure_operation(
    operation: str,
    callback: Callable[[int], object],
    *,
    iterations: int,
    warmup: int,
) -> BenchmarkResult:
    if iterations <= 0:
        raise ValueError("iterations must be positive.")
    if warmup < 0:
        raise ValueError("warmup cannot be negative.")

    for index in range(warmup):
        callback(index)

    durations_ms: list[float] = []
    result_count = 0
    for index in range(iterations):
        started = time.perf_counter()
        result = callback(index)
        durations_ms.append((time.perf_counter() - started) * 1000)
        result_count = len(result) if hasattr(result, "__len__") else 0

    return BenchmarkResult(
        operation=operation,
        iterations=iterations,
        result_count=result_count,
        min_ms=min(durations_ms),
        p50_ms=percentile(durations_ms, 0.50),
        p95_ms=percentile(durations_ms, 0.95),
        max_ms=max(durations_ms),
        mean_ms=statistics.fmean(durations_ms),
    )


def run_benchmarks(
    database_path: Path,
    *,
    iterations: int = 10,
    warmup: int = 2,
    queries: Sequence[str] = ("Performance task", "Generated task", "Area 00"),
) -> BenchmarkReport:
    database_path = Path(database_path)
    if not database_path.is_file():
        raise FileNotFoundError(f"Database does not exist: {database_path}")
    normalized_queries = tuple(query.strip() for query in queries if query.strip())
    if not normalized_queries:
        raise ValueError("At least one non-empty search query is required.")

    database = Database(path=database_path)
    model = None
    delegate = None
    try:
        search_service = GlobalSearchService(database)
        model = _create_tasks_model(database)
        delegate, delegate_option, delegate_indexes = _create_tasks_delegate_benchmark(model)
        task_sample = database.fetch_tasks()[0]
        project_sample = database.fetch_projects()[0]

        def reload_tasks_model(_index: int) -> range:
            model.refresh()
            return range(model.rowCount())

        def load_task_attachment_summaries(_index: int) -> list[object]:
            from mindnavigator.workspaces.tasks.task_roles import TaskRoles

            model.invalidate_attachment_summary_cache()
            return [
                model.index(row, 0).data(TaskRoles.AttachmentSummary)
                for row in range(model.rowCount())
            ]

        def calculate_task_delegate_size_hints(_index: int) -> list[object]:
            return [delegate.sizeHint(delegate_option, index) for index in delegate_indexes]

        def open_task_form(_index: int) -> tuple[str]:
            dialog = _create_task_edit_dialog(database, task_sample)
            result = (dialog.objectName(),)
            _dispose_widget(dialog)
            return result

        def open_project_form(_index: int) -> tuple[str]:
            dialog = _create_project_edit_dialog(database, project_sample)
            result = (dialog.objectName(),)
            _dispose_widget(dialog)
            return result

        results = [
            measure_operation(
                "fetch_tasks",
                lambda _index: database.fetch_tasks(),
                iterations=iterations,
                warmup=warmup,
            ),
            measure_operation(
                "global_search",
                lambda index: search_service.search(normalized_queries[index % len(normalized_queries)]),
                iterations=iterations,
                warmup=warmup,
            ),
            measure_operation(
                "tasks_model_reload",
                reload_tasks_model,
                iterations=iterations,
                warmup=warmup,
            ),
            measure_operation(
                "task_attachment_summaries",
                load_task_attachment_summaries,
                iterations=iterations,
                warmup=warmup,
            ),
            measure_operation(
                "tasks_delegate_size_hints",
                calculate_task_delegate_size_hints,
                iterations=iterations,
                warmup=warmup,
            ),
            measure_operation(
                "task_edit_dialog_open",
                open_task_form,
                iterations=iterations,
                warmup=warmup,
            ),
            measure_operation(
                "project_edit_dialog_open",
                open_project_form,
                iterations=iterations,
                warmup=warmup,
            ),
        ]
    finally:
        if delegate is not None:
            delegate.deleteLater()
        if model is not None:
            model.deleteLater()
        database.close()

    return BenchmarkReport(
        database=str(database_path.resolve()),
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        python=platform.python_version(),
        platform=platform.platform(),
        warmup=warmup,
        results=results,
    )


def _create_tasks_model(database):
    global _QT_APP
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from mindnavigator.workspaces.tasks import tasks_model as tasks_model_module

    _QT_APP = QApplication.instance() or QApplication([])
    original_get_database = tasks_model_module.get_database
    tasks_model_module.get_database = lambda: database
    try:
        return tasks_model_module.TasksModel()
    finally:
        tasks_model_module.get_database = original_get_database


def _create_tasks_delegate_benchmark(model, sample_size: int = 250):
    from PySide6.QtCore import QRect
    from PySide6.QtWidgets import QStyleOptionViewItem
    from mindnavigator.workspaces.tasks.task_roles import TaskRoles
    from mindnavigator.workspaces.tasks.tasks_item_delegate import TasksItemDelegate

    delegate = TasksItemDelegate()
    option = QStyleOptionViewItem()
    option.rect = QRect(0, 0, 1200, 96)
    indexes = []
    for row in range(model.rowCount()):
        index = model.index(row, 0)
        if not index.data(TaskRoles.TaskId):
            continue
        model.toggle_expanded_by_row(row)
        indexes.append(index)
        if len(indexes) >= sample_size:
            break
    return delegate, option, indexes


def _create_task_edit_dialog(database, task):
    from mindnavigator.workspaces.tasks import task_edit_dialog as task_dialog_module

    original_get_database = task_dialog_module.get_database
    task_dialog_module.get_database = lambda: database
    try:
        return task_dialog_module.TaskEditDialog(task)
    finally:
        task_dialog_module.get_database = original_get_database


def _create_project_edit_dialog(database, project):
    from mindnavigator.workspaces.projects import project_edit_dialog as project_dialog_module

    original_get_database = project_dialog_module.get_database
    project_dialog_module.get_database = lambda: database
    try:
        return project_dialog_module.ProjectEditDialog(project)
    finally:
        project_dialog_module.get_database = original_get_database


def _dispose_widget(widget) -> None:
    from PySide6.QtCore import QCoreApplication, QEvent
    from PySide6.QtWidgets import QApplication

    widget.close()
    widget.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    QApplication.processEvents()


def write_report(report: BenchmarkReport, output_path: Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(asdict(report), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path


def format_report(report: BenchmarkReport) -> str:
    lines = [
        f"Database: {report.database}",
        f"Warmup: {report.warmup}",
        "Operation                  iterations  results      p50 ms      p95 ms       mean",
    ]
    for result in report.results:
        lines.append(
            f"{result.operation:<26} {result.iterations:>10} {result.result_count:>8} "
            f"{result.p50_ms:>11.3f} {result.p95_ms:>11.3f} {result.mean_ms:>10.3f}"
        )
    return "\n".join(lines)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path, help="Existing SQLite database to benchmark.")
    parser.add_argument("--iterations", type=int, default=10, help="Measured runs per operation (default: 10).")
    parser.add_argument("--warmup", type=int, default=2, help="Warmup runs per operation (default: 2).")
    parser.add_argument(
        "--query",
        action="append",
        dest="queries",
        help="Global-search query; repeat for multiple queries.",
    )
    parser.add_argument("--json-output", type=Path, help="Optional path for the JSON report.")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    report = run_benchmarks(
        args.database,
        iterations=args.iterations,
        warmup=args.warmup,
        queries=args.queries or ("Performance task", "Generated task", "Area 00"),
    )
    print(format_report(report))
    if args.json_output is not None:
        output_path = write_report(report, args.json_output)
        print(f"JSON report: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
