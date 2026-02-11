# CODEX TASK: Labels: Redesign View Form + Parse Data from Notes

## Goal
Redesign the label view form and implement parsing of structured label-related data from linked notes to display inside the form.

## Definition of Done
- Label view form v2 UI is implemented.
- Parser extracts structured data from notes.
- Label view displays parsed data and handles missing/malformed notes gracefully.

---

## Step 1: Define label view form v2 layout
**Create/Modify:** `mindnavigator/ui/forms/label_view_form.py` (or actual module)

Redesign goals:
- Two-column layout: left = label preview + quick actions, right = parsed details.
- Header includes label name, color, size, and map coordinate summary.
- Right side shows 'Extracted from Note' section (table-like).

Keep style consistent with dark UI reference.

**Acceptance check:**
- Form layout compiles and opens.
- Label preview is visible and readable.


---

## Step 2: Implement note parsing pipeline for label metadata
**Create:** `mindnavigator/core/parsers/label_note_parser.py`

Parse structured blocks from note text, for example:
- Lines `key: value` under a heading `# Label` OR fenced block ```label```. (Choose one and document.)

Extract fields:
- `description`, `tags`, `links`, `refs` (ids), arbitrary key-values into dict.

**Acceptance check:**
- Parser extracts structured data from a sample note text reliably.
- Unknown keys are preserved in an `extra` dict.


---

## Step 3: Connect label view to linked note
**Modify:** label model or controller where label has `note_id` or reference.

On opening label view:
- If note exists: load note text and run parser.
- Render extracted fields in UI.
- Provide 'Open Note' button (if NoteWorkspace exists).

**Acceptance check:**
- Opening a label with a linked note shows parsed data.
- No crashes if note missing or malformed.
