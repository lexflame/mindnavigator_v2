from PySide6.QtCore import QMimeData, Qt
from PySide6.QtWidgets import QApplication

from mindnavigator.ui.linked_entities import (
    LinkedEntitiesListWidget,
    LinkedEntityListItem,
    LinkedEntityListSection,
)


def test_linked_entities_widget_renders_sections_and_payloads() -> None:
    _app = QApplication.instance() or QApplication([])
    widget = LinkedEntitiesListWidget()

    widget.set_sections(
        [
            LinkedEntityListSection(
                title="Задачи",
                items=(
                    LinkedEntityListItem(
                        text="  Связана · Задача: Проверить",
                        entity_kind="task",
                        entity_id=7,
                        origin_id=11,
                        tooltip="Открыть задачу",
                    ),
                ),
            )
        ],
        empty_text="Нет связей",
    )

    assert widget.count() == 2
    assert widget.item(0).text() == "Задачи · 1"
    assert widget.item(0).flags() == Qt.ItemFlag.NoItemFlags
    assert widget.item(1).data(Qt.ItemDataRole.UserRole) == 11
    assert widget.item(1).data(int(Qt.ItemDataRole.UserRole) + 1) == "task"
    assert widget.item(1).data(int(Qt.ItemDataRole.UserRole) + 2) == 7

    widget.set_sections([], empty_text="Нет связей")

    assert widget.count() == 1
    assert widget.item(0).text() == "Нет связей"


def test_linked_entities_widget_uses_configured_drop_callbacks() -> None:
    _app = QApplication.instance() or QApplication([])
    widget = LinkedEntitiesListWidget()
    handled: list[tuple[str, int]] = []
    widget.configure_drop(
        mime_type="application/x-test-entity",
        decoder=lambda _mime: ("task", 9),
        validator=lambda kind, entity_id: kind == "task" and entity_id > 0,
        handler=lambda kind, entity_id: not handled.append((kind, entity_id)),
    )
    mime_data = QMimeData()
    mime_data.setData("application/x-test-entity", b"9")

    class _DropEvent:
        def __init__(self) -> None:
            self.accepted = False

        def mimeData(self) -> QMimeData:
            return mime_data

        def acceptProposedAction(self) -> None:
            self.accepted = True

        def ignore(self) -> None:
            self.accepted = False

    event = _DropEvent()

    widget.dropEvent(event)  # type: ignore[arg-type]

    assert event.accepted is True
    assert handled == [("task", 9)]
