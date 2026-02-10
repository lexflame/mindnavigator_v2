# Hotkeys module

## Source of truth
- Defaults file: `defaults/hotkeys.default.json`.
- Runtime command model: `mindnavigator.hotkeys.models.HotkeyCommand`.
- Manager: `mindnavigator.hotkeys.manager.HotkeyManager`.

## Contexts and priority
Resolution priority:
1. `ModalOnly`
2. `Widget:*`
3. `Workspace:*`
4. `Global`

If same sequence maps to several commands in the same priority bucket, command execution is blocked and exposed as a conflict by `detect_conflicts()`.

## Text input safety
When focus is in editable widgets (`QLineEdit`, `QTextEdit`, `QPlainTextEdit`, editable `QComboBox`), editing shortcuts are not intercepted unless command explicitly allows it.

Protected defaults:
- Ctrl+X
- Ctrl+C
- Ctrl+V
- Ctrl+Z
- Ctrl+Y
- Ctrl+A

## Persistence
`HotkeyOverridesStore` writes only diffs from defaults into:
- `~/.mindnavigator/hotkeys.overrides.json`

Per-command reset is done by `HotkeyManager.unbind(command_id)`.

## Application integration
- `HotkeyEventFilter` is attached to `QApplication`.
- `MainWindow` loads defaults, applies overrides, updates active contexts on workspace changes.
- F1 shows context-sensitive help.
- Ctrl+P opens lightweight command list.
