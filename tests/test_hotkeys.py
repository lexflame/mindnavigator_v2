from pathlib import Path

from mindnavigator.hotkeys.manager import (
    HotkeyManager,
    HotkeyOverridesStore,
    load_commands_from_json,
    normalize_sequence,
)
from mindnavigator.hotkeys.models import HotkeyCommand


def _command(command_id: str, sequence: str, contexts: list[str], allow_in_text_inputs: bool = False) -> HotkeyCommand:
    return HotkeyCommand(
        id=command_id,
        title=command_id,
        description=command_id,
        default_sequence=sequence,
        contexts=contexts,
        allow_in_text_inputs=allow_in_text_inputs,
    )


def test_normalize_sequence():
    assert normalize_sequence("control + shift + q") == "Ctrl+Shift+Q"
    assert normalize_sequence("ctrl+,") == "Ctrl+,"


def test_context_priority_resolution():
    manager = HotkeyManager(
        [
            _command("global.action", "Ctrl+P", ["Global"]),
            _command("workspace.action", "Ctrl+P", ["Workspace:Tasks"]),
            _command("widget.action", "Ctrl+P", ["Widget:TaskList"]),
            _command("modal.action", "Ctrl+P", ["ModalOnly"]),
        ]
    )

    assert manager.resolve("Ctrl+P", False, ["Global", "Workspace:Tasks"]) == "workspace.action"
    assert manager.resolve("Ctrl+P", False, ["Global", "Workspace:Tasks", "Widget:TaskList"]) == "widget.action"
    assert (
        manager.resolve("Ctrl+P", False, ["Global", "Workspace:Tasks", "Widget:TaskList", "ModalOnly"])
        == "modal.action"
    )


def test_text_input_ignore_behavior():
    manager = HotkeyManager(
        [
            _command("tray.minimize", "Ctrl+X", ["Global"], allow_in_text_inputs=False),
            _command("tray.restore", "Ctrl+Shift+X", ["Global"], allow_in_text_inputs=True),
        ]
    )

    assert manager.resolve("Ctrl+X", True, ["Global"]) is None
    assert manager.resolve("Ctrl+Shift+X", True, ["Global"]) == "tray.restore"


def test_conflict_detection():
    manager = HotkeyManager(
        [
            _command("a", "Ctrl+P", ["Global"]),
            _command("b", "Ctrl+P", ["Global"]),
            _command("c", "Ctrl+P", ["Workspace:Tasks"]),
        ]
    )
    conflicts = manager.detect_conflicts()
    assert any(conflict.context == "Global" for conflict in conflicts)


def test_persistence_round_trip(tmp_path: Path):
    manager = HotkeyManager([_command("a", "Ctrl+P", ["Global"])])
    manager.bind("a", "Ctrl+Shift+P")
    manager.set_enabled("a", False)

    store = HotkeyOverridesStore(tmp_path / "hotkeys.overrides.json")
    store.save(manager)

    restored = HotkeyManager([_command("a", "Ctrl+P", ["Global"])])
    store.apply(restored)

    assert restored.bindings["a"].sequence == "Ctrl+Shift+P"
    assert restored.bindings["a"].enabled is False


def test_defaults_loader():
    commands = load_commands_from_json(Path("defaults/hotkeys.default.json"))
    ids = {command.id for command in commands}
    assert "task.create" in ids
    assert "ui.command_palette" in ids
