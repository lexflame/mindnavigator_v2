@echo off
setlocal enabledelayedexpansion

set "APP_NAME=MindNavigator"
set "DIST_SUBDIR=MindNavigator (windows 11 x64)"
set "DIST_DIR=dist\%DIST_SUBDIR%"

echo [build_win] Building executable...
python -m PyInstaller --noconfirm pyinstaller.spec
if errorlevel 1 (
  echo [build_win] Build failed.
  exit /b 1
)

if not exist "%DIST_DIR%" (
  echo [build_win] Dist directory not found: %DIST_DIR%
  exit /b 1
)

for %%D in (lib assets conf data local_data lang defenition) do (
  if not exist "%DIST_DIR%\%%D" mkdir "%DIST_DIR%\%%D"
)

(
  echo @echo off
  echo setlocal
  echo if exist "data\app.db" del /f /q "data\app.db"
  echo if exist "local_data\app.db" del /f /q "local_data\app.db"
  echo echo Database cleanup completed.
) > "%DIST_DIR%\cleanup_db.bat"

echo [build_win] Done: %DIST_DIR%
exit /b 0
