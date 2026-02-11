# CODEX TASK: UI: Hide Standard Window Title Bar for Forms

## Goal
Provide a frameless window option to hide the standard OS header for certain forms, using a custom title bar.

## Definition of Done
- Target forms open without standard title bar.
- User can move and close the window reliably.
- No regressions in focus/shortcuts.

---

## Step 1: Introduce frameless form option
**Modify:** base dialog/form class if exists (e.g., `mindnavigator/ui/widgets/base_dialog.py`)

Add an option to hide standard window title bar:
- Set window flags: `Qt.FramelessWindowHint` (and keep `Qt.Dialog` / `Qt.Window`).
- Add a custom title bar widget (reuse existing TitleBar pattern if project has one).

Rules:
- Must still allow moving the window (mouse drag on title bar).
- Provide close/minimize buttons consistent with app style.

**Acceptance check:**
- Forms can run in frameless mode without losing close/move capability.


---

## Step 2: Apply to selected forms
**Modify:** target forms (e.g., task edit form, label view form) to use frameless option.

**Acceptance check:**
- Selected forms open without OS title bar and remain usable.
