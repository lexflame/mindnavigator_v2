from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog

from mindnavigator.hotkeys import HotkeyBinding, HotkeyCommand
from mindnavigator.ui.command_palette import CommandPaletteDialog, PaletteCommand


class _SearchService:
    def __init__(self) -> None:
        self.queries: list[str] = []

    def search(self, query: str) -> list[dict]:
        self.queries.append(query)
        return [
            {
                "entity": "idea",
                "id": 9,
                "label": "Идея: Индексный поиск",
                "tooltip": "Описание",
            }
        ]


def _palette_command(command_id: str, title: str, sequence: str) -> PaletteCommand:
    return PaletteCommand(
        HotkeyCommand(
            id=command_id,
            title=title,
            description=f"Описание {title}",
            default_sequence=sequence,
            contexts=["Global"],
        ),
        HotkeyBinding(command_id=command_id, sequence=sequence),
    )


def test_command_palette_shows_commands_before_search() -> None:
    _app = QApplication.instance() or QApplication([])
    service = _SearchService()
    dialog = CommandPaletteDialog(
        search_service=service,
        commands=[
            _palette_command("task.create", "Создать задачу", "Ctrl+T"),
            _palette_command("ui.settings.open", "Открыть настройки", "Ctrl+,"),
        ],
    )

    assert dialog.results.count() == 2
    assert service.queries == []
    assert dialog.results.item(0).data(Qt.ItemDataRole.UserRole) == ("command", "task.create")


def test_command_palette_filters_commands_and_activates_search_result() -> None:
    _app = QApplication.instance() or QApplication([])
    service = _SearchService()
    dialog = CommandPaletteDialog(
        search_service=service,
        commands=[_palette_command("task.create", "Создать задачу", "Ctrl+T")],
    )
    activations: list[tuple[str, object]] = []
    dialog.itemActivated.connect(lambda kind, payload: activations.append((kind, payload)))

    dialog.input.setText("индекс")

    assert service.queries == ["индекс"]
    assert dialog.results.count() == 1
    assert dialog.results.currentItem().text() == "Идея: Индексный поиск"

    dialog.input.returnPressed.emit()

    assert activations == [
        (
            "entity",
            {"entity": "idea", "id": 9, "label": "Идея: Индексный поиск", "tooltip": "Описание"},
        )
    ]


def test_command_palette_supports_keyboard_selection_and_escape() -> None:
    _app = QApplication.instance() or QApplication([])
    dialog = CommandPaletteDialog(
        search_service=_SearchService(),
        commands=[
            _palette_command("task.create", "Создать задачу", "Ctrl+T"),
            _palette_command("ui.settings.open", "Открыть настройки", "Ctrl+,"),
        ],
    )
    dialog.show()
    dialog.input.setFocus()

    assert dialog.results.currentRow() == 0
    QTest.keyClick(dialog.input, Qt.Key.Key_Down)
    assert dialog.results.currentRow() == 1
    QTest.keyClick(dialog.input, Qt.Key.Key_Up)
    assert dialog.results.currentRow() == 0

    QTest.keyClick(dialog.input, Qt.Key.Key_Escape)
    assert dialog.result() == QDialog.DialogCode.Rejected
