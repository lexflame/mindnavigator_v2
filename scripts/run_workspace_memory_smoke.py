"""Measure workspace owner cleanup and Windows working-set stabilization."""

from __future__ import annotations

import argparse
import ctypes
import gc
import os
import tempfile
import weakref
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from mindnavigator.storage import CloudFileData, Database


@dataclass(frozen=True)
class MemorySmokeResult:
    scenario: str
    cycles: int
    start_mb: float | None
    midpoint_mb: float | None
    final_mb: float | None
    warm_growth_mb: float | None
    alive_owners: int


def run_memory_smoke(
    *,
    cycles: int = 20,
    image_count: int = 8,
    image_width: int = 1024,
    image_height: int = 768,
) -> list[MemorySmokeResult]:
    if cycles < 2:
        raise ValueError("cycles must be at least 2.")
    if image_count <= 0 or image_width <= 0 or image_height <= 0:
        raise ValueError("Image count and dimensions must be positive.")

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtGui import QImage
    from PySide6.QtWidgets import QApplication, QWidget
    from mindnavigator.workspaces.collections import collections_workspace as collection_module
    from mindnavigator.workspaces.files.image_preview_dialog import ImagePreviewDialog
    from mindnavigator.workspaces.maps.map_canvas import MapCanvas
    from mindnavigator.workspaces.maps.map_image_preview_dialog import MapImagePreviewDialog

    app = QApplication.instance() or QApplication([])
    _ = app
    with tempfile.TemporaryDirectory(prefix="mindnavigator_memory_smoke_") as temp_dir:
        root = Path(temp_dir)
        images: list[CloudFileData] = []
        for index in range(image_count):
            image_path = root / f"image_{index}.png"
            image = QImage(image_width, image_height, QImage.Format.Format_ARGB32)
            image.fill(0xFF000000 | ((index * 20) << 16) | ((index * 10) << 8))
            if not image.save(str(image_path), "PNG"):
                raise OSError(f"Could not create fixture image: {image_path}")
            images.append(
                CloudFileData(
                    id=index + 1,
                    rel_path=image_path.name,
                    name=image_path.name,
                    description="",
                    checksum="",
                    hash_value="",
                    size=image_path.stat().st_size,
                    is_image=True,
                    valid=True,
                    updated_at="",
                )
            )

        parent = QWidget()
        results = [
            _measure_scenario(
                "files_preview",
                lambda: ImagePreviewDialog(
                    parent,
                    images=images,
                    start_index=0,
                    cloud_root=root,
                    description_formatter=str,
                ),
                lambda dialog: _advance_preview(dialog, image_count - 1),
                cycles,
            ),
            _measure_scenario(
                "map_preview",
                lambda: MapImagePreviewDialog(
                    parent,
                    images=images,
                    start_index=0,
                    cloud_root=root,
                ),
                lambda dialog: _advance_preview(dialog, image_count - 1),
                cycles,
            ),
            _measure_scenario(
                "map_canvas",
                MapCanvas,
                lambda canvas: (canvas.resize(1200, 800), canvas.grab()),
                cycles,
            ),
        ]

        database = Database(path=root / "collections.sqlite3")
        original_get_database = collection_module.get_database
        collection_module.get_database = lambda: database
        try:
            results.append(
                _measure_scenario(
                    "collections_workspace",
                    collection_module.CollectionsWorkspace,
                    lambda workspace: workspace.refresh_collections(),
                    cycles,
                )
            )
        finally:
            collection_module.get_database = original_get_database
            database.close()
            parent.deleteLater()
            _flush_deferred_deletes()
        return results


def _measure_scenario(
    scenario: str,
    factory: Callable[[], object],
    exercise: Callable[[object], object],
    cycles: int,
) -> MemorySmokeResult:
    references: list[weakref.ReferenceType] = []
    samples: list[float | None] = []
    _flush_deferred_deletes()
    start_mb = _working_set_mb()
    for _index in range(cycles):
        owner = factory()
        references.append(weakref.ref(owner))
        exercise(owner)
        owner.close()
        owner.deleteLater()
        del owner
        _flush_deferred_deletes()
        samples.append(_working_set_mb())

    midpoint_index = max(0, cycles // 2 - 1)
    midpoint_mb = samples[midpoint_index]
    final_mb = samples[-1]
    warm_growth_mb = (
        final_mb - midpoint_mb
        if final_mb is not None and midpoint_mb is not None
        else None
    )
    return MemorySmokeResult(
        scenario=scenario,
        cycles=cycles,
        start_mb=start_mb,
        midpoint_mb=midpoint_mb,
        final_mb=final_mb,
        warm_growth_mb=warm_growth_mb,
        alive_owners=sum(reference() is not None for reference in references),
    )


def _advance_preview(dialog: object, count: int) -> None:
    from PySide6.QtCore import QEvent, Qt
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtWidgets import QApplication

    for _index in range(count):
        event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Right, Qt.KeyboardModifier.NoModifier)
        QApplication.sendEvent(dialog, event)


def _flush_deferred_deletes() -> None:
    from PySide6.QtCore import QCoreApplication, QEvent
    from PySide6.QtWidgets import QApplication

    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    QApplication.processEvents()
    gc.collect()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    QApplication.processEvents()


def _working_set_mb() -> float | None:
    if os.name != "nt":
        return None

    class ProcessMemoryCounters(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("page_fault_count", wintypes.DWORD),
            ("peak_working_set_size", ctypes.c_size_t),
            ("working_set_size", ctypes.c_size_t),
            ("quota_peak_paged_pool_usage", ctypes.c_size_t),
            ("quota_paged_pool_usage", ctypes.c_size_t),
            ("quota_peak_non_paged_pool_usage", ctypes.c_size_t),
            ("quota_non_paged_pool_usage", ctypes.c_size_t),
            ("pagefile_usage", ctypes.c_size_t),
            ("peak_pagefile_usage", ctypes.c_size_t),
            ("private_usage", ctypes.c_size_t),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(ProcessMemoryCounters),
        wintypes.DWORD,
    ]
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    counters = ProcessMemoryCounters()
    counters.cb = ctypes.sizeof(counters)
    if not psapi.GetProcessMemoryInfo(
        kernel32.GetCurrentProcess(),
        ctypes.byref(counters),
        counters.cb,
    ):
        raise OSError(ctypes.get_last_error(), "GetProcessMemoryInfo failed")
    return counters.working_set_size / (1024 * 1024)


def format_results(results: list[MemorySmokeResult]) -> str:
    lines = [
        "Scenario                 cycles  start MB  midpoint MB  final MB  warm growth  alive",
    ]
    for result in results:
        values = [result.start_mb, result.midpoint_mb, result.final_mb, result.warm_growth_mb]
        formatted = [f"{value:.2f}" if value is not None else "n/a" for value in values]
        lines.append(
            f"{result.scenario:<24} {result.cycles:>6} {formatted[0]:>9} "
            f"{formatted[1]:>12} {formatted[2]:>9} {formatted[3]:>12} "
            f"{result.alive_owners:>6}"
        )
    return "\n".join(lines)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cycles", type=int, default=20)
    parser.add_argument("--images", type=int, default=8)
    parser.add_argument("--image-width", type=int, default=1024)
    parser.add_argument("--image-height", type=int, default=768)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    results = run_memory_smoke(
        cycles=args.cycles,
        image_count=args.images,
        image_width=args.image_width,
        image_height=args.image_height,
    )
    print(format_results(results))
    return 1 if any(result.alive_owners for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
