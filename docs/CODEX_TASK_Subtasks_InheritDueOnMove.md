# CODEX TASK: Subtasks: Inherit Due Date/Time on Move

## Goal
Ensure that when a task is moved under a parent (becomes a subtask), it inherits the parent's due date and time based on a clear rule.

## Definition of Done
- Due date+time inheritance works on move-to-subtask.
- Explicit due datetime is not overwritten unexpectedly.
- Optional UI toggle exists for manual control.

---

## Step 1: Define rule: moving task under parent inherits due datetime
**Modify:** task move operation (drag&drop handler or 'Move to' action)

When a task is moved to become a subtask of another task:
- If moved task has no explicit due datetime OR if a new flag `inherit_due_from_parent` is true: set due datetime = parent's due datetime.
- Also inherit due time (not just date).

Rules:
- Do not overwrite explicit due datetime unless user opted-in (or define project policy).
- Record inheritance source in meta (optional) to allow later decouple.

**Acceptance check:**
- Moving a task under a parent assigns due date+time from parent when appropriate.
- No overwrite when task already had explicit due datetime (unless policy says so).


---

## Step 2: Add UI toggle (optional) for inheritance
**Modify:** task edit form

Add checkbox: `Наследовать срок от родителя` (visible only when task has parent).

**Acceptance check:**
- User can toggle inheritance behavior explicitly.
