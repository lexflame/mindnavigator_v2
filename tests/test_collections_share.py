from mindnavigator.core.models.collection_item import CollectionItem
from mindnavigator.core.serializers.collections_share_v1 import (
    export_collections_share_v1,
    import_collections_share_v1,
)


def test_export_import_roundtrip() -> None:
    item = CollectionItem(
        title="City references",
        kind="link",
        url="https://example.com",
        tags=["city", "game"],
        links=[{"type": "city=game", "target_id": "obj-1"}],
    )
    payload = export_collections_share_v1([item])
    restored = import_collections_share_v1(payload)
    assert len(restored) == 1
    assert restored[0].title == "City references"
    assert restored[0].links[0]["type"] == "city=game"


def test_import_ignores_unknown_schema() -> None:
    assert import_collections_share_v1('{"schema":"other","items":[]}') == []
