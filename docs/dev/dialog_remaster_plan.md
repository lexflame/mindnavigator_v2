# Dialog Remaster Plan

## Step 1 (foundation)
- Introduce shared base class `MNBaseDialog` (`QDialog`) with:
  - frameless window (`Qt.FramelessWindowHint`)
  - default initial size `1450x812`
  - centering on active parent window (fallback: parent screen / primary screen)
- Introduce standard runner `show_dialog_standard(dialog, parent)`:
  - applies app backdrop overlay over parent window
  - opens dialog modally
  - removes backdrop on `accepted` / `rejected` / `finished`
  - calls dialog centering hook when available (`center_on_active_parent`)
- Migrate 12 representative call-sites from inventory (proof slice only).

## Step 2 (core dialog classes)
- Migrate high-traffic edit/view dialogs to `MNBaseDialog`:
  - task/project/map/object edit and detail dialogs
  - keep special minimum-size policies where needed
- Replace remaining direct `dialog.exec()` calls for migrated flows with `show_dialog_standard`.

## Step 3 (ad-hoc dialogs)
- Convert ad-hoc `QDialog(self)` constructions to dedicated dialog classes.
- Move shared form fragments to reusable helpers to avoid copy-paste divergence.

## Step 4 (special-case handling)
- Preserve popup/anchored behavior for dialogs like `EntityPickerDialog` (`Qt.Popup`).
- Keep fullscreen preview flows (`TaskImagePreviewDialog`, `MapImagePreviewDialog`, `ImagePreviewDialog`) on dedicated behavior paths while still using consistent backdrop rules where appropriate.

## Step 5 (styling and interaction consistency)
- Introduce shared surface spacing, button rows, and typography tokens for dialogs.
- Standardize keyboard behavior (`Esc`, Enter/accept, focus defaults) and dirty-state confirmation patterns.

## Step 6 (full migration and cleanup)
- Migrate all remaining dialog call-sites from inventory to the standard runner.
- Remove legacy direct overlay invocation patterns where superseded.
- Keep compatibility alias only if external modules rely on old API.

## Step 7 (verification)
- Compile and smoke-test all workspace dialog flows.
- Validate centering/backdrop behavior across multi-monitor and resized parent windows.
- Add targeted tests for runner behavior and lifecycle cleanup where practical.
