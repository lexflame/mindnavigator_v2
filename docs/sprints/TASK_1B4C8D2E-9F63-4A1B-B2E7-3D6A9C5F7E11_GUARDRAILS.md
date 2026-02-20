# Guardrails Notes: TASK_1B4C8D2E-9F63-4A1B-B2E7-3D6A9C5F7E11

## Title
Validation and guardrails for project Drag&Drop.

## Implemented
1. Rejection of forbidden drop targets:
- Drop to non-project pseudo-items (`clear`, `section`, `empty`) is blocked.
- Root-area drop is still allowed for move-to-root.

2. Structural validation before persistence:
- Block self-parenting and descendant-parenting (cycle prevention).
- Validate source/target existence before attempting storage update.
- Keep existing storage-side validation as final safety layer.

3. Depth limit validation:
- Enforced max hierarchy depth of 4 levels (`0..3` depth index).
- Validation accounts for full moved subtree height, not only root node.

4. User-facing rejected-drop feedback:
- Added tooltip feedback near cursor with concrete rejection reason.
- Provided specific messages for invalid target, cycle, and depth overflow.

## Validation
1. `python -m compileall mindnavigator/ui/projects_nav.py` passed.
