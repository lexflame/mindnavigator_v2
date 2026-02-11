# CODEX TASK: Task Edit: Ctrl+Enter saves form

## Goal
Implement keyboard shortcut Ctrl+Enter to save task edit form data.

## Definition of Done
- Ctrl+Enter triggers save reliably from anywhere in the form.
- No change to normal Enter behavior in text areas.

---

## Step 1: Wire Ctrl+Enter shortcut to Save in Task Edit Form
**Modify:** `mindnavigator/ui/forms/task_edit_form.py`

Add `QShortcut` or action with shortcut `Ctrl+Return` and `Ctrl+Enter` variants:
- Connect to the same handler as Save button (`on_save_clicked()` or equivalent).

Rules:
- Should work when focus is inside description field (QTextEdit) too.
- If form has validation, shortcut must respect it.

**Acceptance check:**
- Pressing Ctrl+Enter saves the form (same as clicking Save).
- Works from inside multi-line description field.


---

## Step 2: Prevent accidental save on Enter alone
Ensure plain Enter in multi-line fields inserts newline as before.

**Acceptance check:**
- Enter still creates newline in description; only Ctrl+Enter saves.
