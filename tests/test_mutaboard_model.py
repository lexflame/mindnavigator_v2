from __future__ import annotations

from datetime import date, datetime, timezone

from mindnavigator.storage import (
    CloudFileData,
    IdeaData,
    IdeaRelationData,
    MapData,
    MapMarkerData,
    NoteData,
    ObjectData,
    ProjectData,
    TaskAttachmentData,
    TaskData,
)
from mindnavigator.workspaces.mutaboard.module_impl import MutaBoardModel


class _MutaBoardDbStub:
    def __init__(self) -> None:
        now = datetime(2026, 5, 17, 12, 0, tzinfo=timezone.utc)
        self._tasks = [
            TaskData(
                id=1,
                day=date(2026, 5, 17),
                time_text="09:00",
                title="Task Alpha",
                description="Capture a board integration task",
                priority="Medium",
                done=False,
                board_column="queue",
                project_id=7,
                project_title="Project Seven",
            )
        ]
        self._ideas_active = [
            IdeaData(
                id=11,
                project_id=7,
                title="Idea Signal",
                summary="Planning idea",
                body_md="",
                type="feature",
                status="ripe",
                value_score=3,
                effort_score=2,
                source="",
                created_at=now,
                updated_at=now,
                archived_at=None,
                project_title="Project Seven",
            )
        ]
        self._ideas_archived: list[IdeaData] = []
        self._objects = [
            ObjectData(
                id=21,
                title="Object Delta",
                catalog="Infra",
                object_type="service",
                status="active",
                description="Service object",
                created_at="2026-05-17T10:00:00+00:00",
                updated_at="2026-05-17T11:00:00+00:00",
            )
        ]
        self._notes = [
            NoteData(
                id=31,
                title="Note Pulse",
                preview="Quick note preview",
                tags=["alpha", "beta"],
                updated=now,
                project="Workspace Project",
            )
        ]
        self._projects = [
            ProjectData(
                id=7,
                area="Ops",
                title="Project Seven",
                updated=date(2026, 5, 17),
                priority="High",
                archived=False,
                linked_map_id=41,
                linked_note_id=31,
                linked_object_id=21,
            )
        ]
        self._maps = [
            MapData(
                id=41,
                title="Map Echo",
                description="Map description",
                project="Workspace Project",
                tiles_path="",
                tiles_h=4,
                tiles_w=4,
            )
        ]
        self._markers = [
            MapMarkerData(
                id=51,
                map_id=41,
                name="Marker Flux",
                x=10.0,
                y=20.0,
                color="#fff",
                type="poi",
                size=1.0,
                description="Marker description",
                properties="",
                task_ids=[1],
                project_ids=[7],
                note_ids=[31],
                object_ids=[21],
                file_ids=[61],
                map_ids=[],
                marker_ids=[],
                parent_path="",
                image_path="",
                created_at="2026-05-17T10:00:00+00:00",
                updated_at="2026-05-17T11:00:00+00:00",
            )
        ]
        self._images = [
            CloudFileData(
                id=61,
                rel_path="gallery/sample.png",
                name="Sample Image",
                description="Image description",
                checksum="",
                hash_value="",
                size=1024,
                is_image=True,
                valid=True,
                updated_at="2026-05-17T11:00:00+00:00",
            )
        ]
        self._task_attachments = {
            1: [TaskAttachmentData(id=101, task_id=1, kind="idea", ref_id=11, created_at="2026-05-17T12:00:00+00:00")]
        }
        self._idea_relations = {
            11: [IdeaRelationData(id=201, idea_id=11, entity_type="object", entity_id=21, created_at=now)]
        }

    def fetch_tasks(self):
        return list(self._tasks)

    def fetch_ideas(self, archived=True):
        return list(self._ideas_archived if archived else self._ideas_active)

    def fetch_objects(self):
        return list(self._objects)

    def fetch_notes(self):
        return list(self._notes)

    def fetch_projects(self):
        return list(self._projects)

    def fetch_maps(self):
        return list(self._maps)

    def fetch_map_markers(self, map_id=None):
        if map_id is None:
            return list(self._markers)
        return [marker for marker in self._markers if marker.map_id == map_id]

    def fetch_cloud_files(self):
        return list(self._images)

    def fetch_task_attachments(self, task_id: int):
        return list(self._task_attachments.get(task_id, []))

    def fetch_idea_relations(self, idea_id: int):
        return list(self._idea_relations.get(idea_id, []))


def test_mutaboard_model_builds_catalog_cards_for_supported_kinds() -> None:
    model = MutaBoardModel(db=_MutaBoardDbStub())

    cards = model.reload()
    kinds = {(card.entity_kind, card.title) for card in cards}

    assert ("task", "Task Alpha") in kinds
    assert ("idea", "Idea Signal") in kinds
    assert ("image", "Sample Image") in kinds
    assert ("map", "Map Echo") in kinds
    assert ("marker", "Marker Flux") in kinds
    assert ("note", "Note Pulse") in kinds
    assert ("project", "Project Seven") in kinds
    assert ("object", "Object Delta") in kinds


def test_mutaboard_model_filters_catalog_by_kind_query_and_project() -> None:
    model = MutaBoardModel(db=_MutaBoardDbStub())
    model.reload()

    image_cards = model.filtered_cards(entity_kind="image")
    assert [card.title for card in image_cards] == ["Sample Image"]

    project_cards = model.filtered_cards(project_id=7)
    assert {card.title for card in project_cards} == {"Task Alpha", "Idea Signal", "Project Seven"}

    query_cards = model.filtered_cards(query="marker description")
    assert [card.title for card in query_cards] == ["Marker Flux"]


def test_mutaboard_model_counts_relations_for_selected_entities() -> None:
    model = MutaBoardModel(db=_MutaBoardDbStub())
    cards = {card.title: card for card in model.reload()}

    assert cards["Task Alpha"].total_linked_count == 1
    assert cards["Idea Signal"].linked_object_count == 1
    assert cards["Object Delta"].linked_idea_count == 1
    assert cards["Marker Flux"].total_linked_count == 5
    assert cards["Map Echo"].total_linked_count == 1
