from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog

from mindnavigator.hotkeys import HotkeyBinding, HotkeyCommand
from mindnavigator.services import SearchRecentsService
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


class _Settings:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def get_setting(self, key: str, default: str = "") -> str:
        return self.values.get(key, default)

    def set_setting(self, key: str, value: str) -> None:
        self.values[key] = value


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


def test_command_palette_shows_recent_actions_and_entities_before_commands() -> None:
    _app = QApplication.instance() or QApplication([])
    recents = SearchRecentsService(_Settings())
    recents.record_command("task.create")
    recents.record_result_action(
        "open",
        {"entity": "idea", "id": 9, "label": "Идея: Индексный поиск"},
    )
    recents.record_entity({"entity": "idea", "id": 9, "label": "Идея: Индексный поиск"})
    dialog = CommandPaletteDialog(
        search_service=_SearchService(),
        commands=[_palette_command("task.create", "Создать задачу", "Ctrl+T")],
        recents_service=recents,
    )

    assert dialog.results.count() == 3
    assert dialog.results.item(0).text().startswith("Недавнее действие: Перейти")
    assert dialog.results.item(1).text().startswith("Недавнее действие: Создать задачу")
    assert dialog.results.item(2).text() == "Недавнее: Идея: Индексный поиск"


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
    assert dialog.results.count() == 2
    assert dialog.results.currentItem().text() == "Идея: Индексный поиск"

    dialog.input.returnPressed.emit()

    assert activations == [
        (
            "entity",
            {"entity": "idea", "id": 9, "label": "Идея: Индексный поиск", "tooltip": "Описание"},
        )
    ]


def test_command_palette_activates_search_result_action() -> None:
    _app = QApplication.instance() or QApplication([])
    dialog = CommandPaletteDialog(search_service=_SearchService(), commands=[])
    activations: list[tuple[str, object]] = []
    dialog.itemActivated.connect(lambda kind, payload: activations.append((kind, payload)))

    dialog.input.setText("индекс")
    dialog.results.setCurrentRow(1)
    dialog.input.returnPressed.emit()

    assert activations == [
        (
            "action",
            {
                "action_id": "open",
                "payload": {
                    "entity": "idea",
                    "id": 9,
                    "label": "Идея: Индексный поиск",
                    "tooltip": "Описание",
                },
            },
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
