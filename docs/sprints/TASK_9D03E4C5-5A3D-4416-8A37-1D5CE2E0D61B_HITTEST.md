# Implementation Notes: TASK_9D03E4C5-5A3D-4416-8A37-1D5CE2E0D61B

## Title
Hit testing and drop validation improvements.

## Implemented
1. Extended `DropZoneRect`:
- `priority`
- `parent_zone_id`
- `area()` helper

2. Added `NestedHitTestService`:
- resolves overlapping/nested zones;
- priority-first selection;
- area-based specificity fallback.

3. Added `RuleBasedDropValidator`:
- zone-level entity-type allow-list validation.

4. Added tests:
- `tests/test_dragdrop_policy.py` for nested hit testing and validator behavior.

## Validation Result
- `python -m compileall mindnavigator/ui/dragdrop tests/test_dragdrop_policy.py` passed.
- `python -m pytest tests/test_dragdrop_policy.py -q` blocked: `No module named pytest`.
