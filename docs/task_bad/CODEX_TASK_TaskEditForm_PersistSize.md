# CODEX TASK: Persist Task Edit Form Size (QSettings)

## Goal
Remember what size the user set for the task edit form and restore it on next open/restart.

## Definition of Done
- Task edit form restores last geometry across app restarts.
- Optional splitters restore sizes (if present).
- No crashes on missing settings.

---

## Step 1: Introduce settings key for Task Edit Form geometry
**Modify:** `mindnavigator/ui/forms/task_edit_form.py` (or the actual task edit dialog module)

Add persistent storage using `QSettings`:
- On show/after init, call `restoreGeometry()` from key `ui/task_edit_form/geometry` (bytes).
- On close/teardown, save `saveGeometry()` into same key.

Rules:
- Only persist if the window has been shown at least once.
- Do not crash if setting missing.
- Keep existing min/max size constraints intact (if present).

**Acceptance check:**
- Resizing the task edit form, closing it, and re-opening restores the size/position.
- No errors when key is missing (fresh install).


---

## Step 2: Persist splitter sizes inside Task Edit Form (if present)
**Modify:** same module as Step 1

If the form contains `QSplitter` (e.g., left meta / right description), persist splitter sizes:
- Save `splitter.sizes()` to key `ui/task_edit_form/splitter_sizes` (JSON list of ints).
- Restore on init after widgets created.

**Acceptance check:**
- Splitter sizes restore after restart (if splitter exists).
- If no splitter exists, task remains a no-op (safe).


---

## Step 3: Quality gate
- Remove debug prints.
- Ensure key names are stable and documented in code comment.

**Acceptance check:**
- App launches, task edit form opens, no regressions in layout.
