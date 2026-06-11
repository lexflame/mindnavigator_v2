from __future__ import annotations

from scripts.run_workspace_memory_smoke import format_results, run_memory_smoke


def test_workspace_memory_smoke_releases_all_owners() -> None:
    results = run_memory_smoke(
        cycles=2,
        image_count=2,
        image_width=64,
        image_height=64,
    )

    assert [result.scenario for result in results] == [
        "files_preview",
        "map_preview",
        "map_canvas",
        "collections_workspace",
    ]
    assert all(result.cycles == 2 for result in results)
    assert all(result.alive_owners == 0 for result in results)
    assert "collections_workspace" in format_results(results)
