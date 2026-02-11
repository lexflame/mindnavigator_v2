# CODEX TASK: Periodic Tasks Scheduler (RRULE/Cron-like) + UI

## Goal
Implement a periodic task scheduler that can run actions on a schedule, and provide minimal UI to manage periodic tasks.

## Definition of Done
- Scheduler can compute and trigger due tasks without blocking UI.
- Periodic tasks are manageable via UI (add/edit/enable).
- Schedule persists between restarts (DB or settings fallback).

---

## Step 1: Define periodic task model + scheduler interface
**Create:** `mindnavigator/core/scheduler/periodic_task.py`

Add model:
- `id`, `title`, `rrule` (iCal RRULE string) OR simplified cron-like string
- `enabled: bool`
- `last_run_at`, `next_run_at`
- `action: str` (e.g., `sync`, `backup`, `cleanup`) + `payload` dict

**Create:** `mindnavigator/core/scheduler/scheduler.py`
- Interface/class `Scheduler` with `tick(now)` and `register(task)` and `due_tasks(now)`.

**Acceptance check:**
- Scheduler module imports without errors.
- Can compute due tasks for a given `now` with a simple rule (daily/hourly).


---

## Step 2: Add app-level timer tick
**Modify:** app bootstrap (e.g., `mindnavigator/app.py` or main window)

Create a `QTimer` ticking every 30–60 seconds:
- Calls scheduler.tick(datetime.now())
- If any tasks due: dispatch action handlers (stub allowed).

Rules:
- Do not block UI; if actions are heavy, dispatch via worker/thread if repo has it; otherwise just log TODO.

**Acceptance check:**
- Timer runs without crashing.
- Due tasks are detected and dispatched (at least logged).


---

## Step 3: Add UI: Periodic Tasks settings page (minimal)
**Create:** `mindnavigator/ui/dialogs/periodic_tasks_dialog.py`

Dialog shows list of periodic tasks with enable toggle and schedule string edit.
Actions: Add / Edit / Delete.

**Acceptance check:**
- User can add a periodic task, enable it, and it persists in storage (if storage exists) or in settings JSON (fallback).
