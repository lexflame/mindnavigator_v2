#!/usr/bin/env bash
set -euo pipefail

APP_NAME="MindNavigator"
DIST_SUBDIR="MindNavigator (windows 11 x64)"
DIST_DIR="dist/${DIST_SUBDIR}"

echo "[build_win.sh] Building executable..."
python -m PyInstaller --noconfirm pyinstaller.spec

if [[ ! -d "${DIST_DIR}" ]]; then
  echo "[build_win.sh] Dist directory not found: ${DIST_DIR}" >&2
  exit 1
fi

for d in lib assets conf data local_data lang defenition; do
  mkdir -p "${DIST_DIR}/${d}"
done

cat > "${DIST_DIR}/cleanup_db.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
rm -f "data/app.db" "local_data/app.db"
echo "Database cleanup completed."
EOF
chmod +x "${DIST_DIR}/cleanup_db.sh"

echo "[build_win.sh] Done: ${DIST_DIR}"
