# Implementation Notes: TASK_B5B10AB6-FD2F-4AA1-9157-8E7AA32EA0CD

## Title
Global scrollbar stylesheet.

## Implemented
1. Global scrollbar QSS is generated from centralized tokens in `mindnavigator/ui/styles.py`:
- vertical and horizontal scrollbar states;
- hover/pressed/disabled handle states;
- corner styling.

2. Local duplicate scrollbar rules were removed to prevent style conflicts:
- `mindnavigator/ui/projects_nav.py`
- `mindnavigator/ui/dialogs/map_label_edit_dialog.py`

3. Result:
- one global scrollbar style source;
- local widgets keep layout/theme rules without duplicating scrollbar mechanics.
