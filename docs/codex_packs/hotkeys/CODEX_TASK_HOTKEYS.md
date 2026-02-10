# MindNavigator — Hotkeys Module (Codex-ready)

## Goal
Implement a configurable hotkey module for MindNavigator (PySide6). The module must provide:
- Single source of truth for commands and default bindings
- Context-aware dispatch (Global / Workspace / Widget / Modal)
- Safe behavior in text inputs (do not steal standard editing shortcuts unless explicitly allowed)
- Conflict detection + deterministic priority rules
- User overrides persistence (JSON or SQLite)
- Hotkeys Help (F1) and Command Palette (Ctrl+P)

> Notes (Qt/PySide6): Use `QKeySequence` for sequences and an application-level event filter (or action-based shortcuts where appropriate). `QKeySequence` is standard for shortcuts. 

---

## Default Hotkeys (v1)
This list includes the user’s initial bindings and a sane baseline.

### Global
- Ctrl+T — Create task
- Ctrl+X — Minimize to tray (do not intercept inside text inputs)
- Ctrl+Shift+X — Restore from tray
- Ctrl+P — Command Palette
- Ctrl+, — Settings
- F1 — Hotkeys Help overlay
- Esc — Close modal / cancel / clear focus (context dependent)

### Navigation: Workspaces / Modes
- Ctrl+Tab — Next workspace/mode
- Ctrl+Shift+Tab — Previous workspace/mode
- Ctrl+1..9 — Go to workspace #1..#9 (optional)

### Navigation: Entity Sheets inside workspace
- Ctrl+Q — Next entity sheet/tab
- Ctrl+Shift+Q — Previous entity sheet/tab
- Ctrl+W — Close current sheet/tab (if closeable)
- Ctrl+Shift+T — Reopen last closed sheet/tab (optional)

### Entity actions (operate on current selection)
- Enter — Open / Edit
- F2 — Rename
- Del — Delete
- Ctrl+D — Duplicate
- Ctrl+E — Inline edit (if supported)
- Ctrl+S — Save (for editors/forms)
- Ctrl+F — Focus local search/filter

### Tasks-only (TasksWorkspace)
- Ctrl+Enter — Toggle done
- Ctrl+Shift+D — Set due date
- Ctrl+Alt+Up / Ctrl+Alt+Down — Priority up/down (optional)

---

## Context + Priority Rules
### Context types
- **ModalOnly**: active only when a modal is open
- **Widget:<objectName>**: active only when focus is within that widget subtree
- **Workspace:<name>**: active only within a given workspace
- **Global**: always active unless blocked by text-input rule

### Priority order (highest wins)
1. ModalOnly
2. Widget
3. Workspace
4. Global

### Text-input rule
If current focus widget is editable (e.g., QLineEdit/QTextEdit/QPlainTextEdit/QComboBox editable):
- Do **not** intercept sequences that overlap standard editing (Cut/Copy/Paste/Undo/Redo/SelectAll) unless command explicitly has `allow_in_text_inputs=true`.
- Specifically for **Ctrl+X** (tray): must be ignored when in editable widgets.

---

## Data Model
### HotkeyCommand
Fields:
- `id: str` (stable)
- `title: str`
- `description: str`
- `default_sequence: str` (Qt key sequence string)
- `contexts: list[str]` (e.g. ["Global"], ["Workspace:Tasks"], ["Widget:TaskList"], ["ModalOnly"]) 
- `allow_in_text_inputs: bool` (default false)

### HotkeyBinding
Fields:
- `command_id: str`
- `sequence: str`
- `enabled: bool`
- `user_defined: bool`

---

## Step 1. Command Registry
Create a central registry (single source of truth) that defines **all commands** and their default bindings.

Acceptance:
- Commands are defined in one place.
- Defaults cover the “Default Hotkeys (v1)” list.

---

## Step 2. HotkeyManager Core
Implement `HotkeyManager` responsible for:
- `register_command(command)`
- `bind(command_id, sequence, user_defined=True)`
- `unbind(command_id)` (revert to default)
- `set_enabled(command_id, enabled)`
- `set_active_contexts(contexts)`
- `resolve(sequence, focus_widget, active_contexts) -> command_id | None`
- `detect_conflicts() -> list[Conflict]`

Acceptance:
- Active contexts affect what commands can be resolved.
- Conflicts are detectable.

---

## Step 3. Event Filter Integration (Application-level)
Install an event filter on `QApplication` (or main window) that:
1) Checks focused widget type
2) Applies text-input rule
3) Converts `QKeyEvent` into a `QKeySequence`
4) Asks `HotkeyManager.resolve(...)`
5) Executes the corresponding action callback

Acceptance:
- Ctrl+T creates a task.
- Ctrl+Tab cycles workspaces.
- Ctrl+Q cycles entity sheets.
- Ctrl+X minimizes to tray, but **not inside text inputs**.

---

## Step 4. Conflict Resolver
Rules:
- If multiple commands match the same sequence in the same effective context:
  - pick by priority (Modal > Widget > Workspace > Global)
  - if still ambiguous (same priority), mark conflict and do not execute

Acceptance:
- Conflicts are deterministic.
- Conflicts can be listed for UI.

---

## Step 5. Persistence (User Overrides)
Implement storage for overrides.

Option A: JSON file
- `hotkeys.overrides.json` containing only differences from defaults

Option B: SQLite settings table
- store overrides with `command_id`, `sequence`, `enabled`

Acceptance:
- Overrides persist after restart.
- Reset-to-default works per command and for all.

---

## Step 6. Settings UI: Hotkeys
Add Settings page “Hotkeys”:
- list commands (title, description, current sequence)
- search/filter by context
- record new key sequence (capture mode)
- show conflict badge
- buttons: Reset, Disable, Restore default

Acceptance:
- User can rebind a command.
- Conflicts are visible.

---

## Step 7. Help Overlay + Command Palette
- F1: show overlay with **currently active** hotkeys
- Ctrl+P: command palette to search commands and execute

Acceptance:
- Overlay shows correct keys for current context.
- Palette executes commands even without memorized keys.

---

## Step 8. Tests
Unit tests (no UI):
- key sequence parsing + normalization
- context priority resolution
- text-input ignore behavior
- conflict detection
- persistence round-trip

Acceptance:
- Core logic is test-covered.

---

## Deliverables
- `hotkeys/` module (manager, models, resolver)
- `defaults/hotkeys.default.json`
- `settings/ui_hotkeys.*` page (or widget)
- `docs/hotkeys.md` (this file or derived)
