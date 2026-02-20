# Implementation Notes: TASK_0F1733D2-3B9F-4E8D-BD6A-0C2F5F55189E

## Title
Build and release readiness.

## Implemented
1. Added Win64 build script:
- `scripts/build_win.bat`

2. Added Win64 build+deploy+run script:
- `scripts/build_start_win.bat`

3. Added *nix build script:
- `scripts/build_win.sh`

4. Added *nix build+deploy script:
- `scripts/build_start_win.sh`

5. Build scripts enforce compiled app structure:
- creates `lib`, `assets`, `conf`, `data`, `local_data`, `lang`, `defenition`
- adds DB cleanup script in build root (`cleanup_db.bat` / `cleanup_db.sh`)

## Notes
- Deployment target defaults to `C:\Program Portable\NAME_APP` on Windows scripts.
- *nix start script uses `TARGET_DIR` env var and defaults to `/mnt/c/Program Portable/NAME_APP`.
