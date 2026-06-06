from __future__ import annotations

from types import SimpleNamespace

from mindnavigator.services import GlobalSearchService


class _SearchDb:
    def fetch_tasks(self):
        return [SimpleNamespace(id=1, title="Release", description="Search target", project_title="Core", project_area="Dev")]

    def fetch_projects(self):
        return [SimpleNamespace(id=2, title="Core", area="Search target")]

    def fetch_maps(self):
        return [SimpleNamespace(id=3, title="World", description="Search target", project="Core")]

    def fetch_map_markers(self):
        return [SimpleNamespace(id=4, map_id=3, name="Gate", description="Search target", properties="")]

    def fetch_notes(self):
        return [SimpleNamespace(id=5, title="Memo", preview="Search target", tags=["tag"], project="Core")]

    def fetch_cloud_files(self):
        return [SimpleNamespace(id=6, name="spec.txt", rel_path="Search target", description="")]

    def fetch_objects(self):
        return [
            SimpleNamespace(
                id=7,
                title="Artifact",
                catalog="Search target",
                object_type="Document",
                status="Active",
                description="",
            )
        ]

    def fetch_characters(self, search_text: str = ""):
        assert search_text == "search target"
        return [SimpleNamespace(id=8, name="Alex", role="Lead", tags=["search"], description="target")]

    def fetch_collection_items(self, search_text: str = ""):
        assert search_text == "search target"
        return [SimpleNamespace(id=9, title="Reference", entity_type="film", topic="Search target", source_url="")]


def test_global_search_service_preserves_entity_payload_order() -> None:
    matches = GlobalSearchService(_SearchDb()).search("  SEARCH TARGET  ")

    assert [match["entity"] for match in matches] == [
        "task",
        "project",
        "map",
        "marker",
        "note",
        "file",
        "object",
        "character",
        "collection",
    ]
    assert matches[0] == {"entity": "task", "label": "Задача: Release", "tooltip": "Search target", "id": 1}
    assert matches[3]["map_id"] == 3
    assert matches[-1]["tooltip"] == "Фильм · Search target"


def test_global_search_service_skips_storage_for_empty_query() -> None:
    class _FailingDb:
        def __getattr__(self, name):
            raise AssertionError(f"Unexpected storage access: {name}")

    assert GlobalSearchService(_FailingDb()).search("   ") == []
