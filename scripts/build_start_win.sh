#!/usr/bin/env bash
set -euo pipefail

APP_NAME="MindNavigator"
DIST_SUBDIR="MindNavigator (windows 11 x64)"
DIST_DIR="dist/${DIST_SUBDIR}"
TARGET_DIR="${TARGET_DIR:-/mnt/c/Program Portable/NAME_APP}"
EXE_NAME="MindNavigator.exe"

"$(dirname "$0")/build_win.sh"

mkdir -p "${TARGET_DIR}"
echo "[build_start_win.sh] Syncing build to ${TARGET_DIR}..."
rsync -a --delete "${DIST_DIR}/" "${TARGET_DIR}/"

if [[ -f "${TARGET_DIR}/${EXE_NAME}" ]]; then
  echo "[build_start_win.sh] Executable deployed: ${TARGET_DIR}/${EXE_NAME}"
else
  echo "[build_start_win.sh] Executable not found after sync." >&2
  exit 1
fi
