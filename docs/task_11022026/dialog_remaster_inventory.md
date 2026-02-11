STEP 0 — Inventory QDialog usage (mindnavigator_v2)

You are working inside the repo: mindnavigator_v2.

GOAL
Create a complete inventory of all dialogs created via QDialog across the whole app (all workspaces), including:
- where dialogs are defined (class files)
- where dialogs are instantiated and shown (exec/open/show)
- any existing geometry/positioning/titlebar customizations
- any existing frameless/overlay-like implementations

OUTPUT FILE (must be created/updated)
docs/dev/dialog_remaster_inventory.md

SEARCH INSTRUCTIONS
Scan the repository for:
- "QDialog" subclasses and direct instantiation: "QDialog(", "class .*\\(.*QDialog"
- showing dialogs: ".exec(", ".exec_(", ".open(", ".show("
- window/title/flags/geometry: "setWindowTitle", "setWindowFlags", "FramelessWindowHint", "Qt.Dialog", "setModal"
- sizing/positioning: "resize(", "setFixedSize(", "setMinimumSize(", "setMaximumSize(", "setGeometry(", "move(", "center"
- overlays/backdrops: "overlay", "backdrop", "dim", "opacity", "QGraphicsOpacityEffect", "WA_TranslucentBackground"

INVENTORY FORMAT (in the markdown file)
1) Summary
- total dialogs found
- total call-sites found
- any existing base dialog helpers/patterns detected

2) Table: Dialog classes
Columns:
- Dialog class name
- File path
- Parent (QDialog/QWidget/etc.)
- How it is shown (exec/open/show) if known
- Notes (flags/titlebar/overlay hints)

3) Table: Dialog call-sites
Columns:
- Dialog class (or QDialog)
- File path + function/method name
- Show method (exec/open/show)
- Parent passed? (yes/no/unknown)
- Local geometry/positioning code present? (yes/no + snippet reference)
- Notes

4) Special cases
- dialogs that are already frameless/custom titlebar
- dialogs that must stay non-modal or have unique size/behavior

REQUIREMENTS
- Do not change app behavior in this step (inventory only).
- Only add the markdown file (and optionally small helper notes if absolutely necessary, but avoid code edits).
- Be precise with file paths and class names.

VALIDATION
Ru
::contentReference[oaicite:0]{index=0}