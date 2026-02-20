@echo off
setlocal enabledelayedexpansion

set "APP_NAME=MindNavigator"
set "TARGET_DIR=C:\Program Portable\NAME_APP"
set "DIST_SUBDIR=MindNavigator (windows 11 x64)"
set "DIST_DIR=dist\%DIST_SUBDIR%"
set "EXE_NAME=MindNavigator.exe"

call "%~dp0build_win.bat"
if errorlevel 1 exit /b 1

if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%"

echo [build_start_win] Syncing build to "%TARGET_DIR%"...
robocopy "%DIST_DIR%" "%TARGET_DIR%" /MIR >nul
if errorlevel 8 (
  echo [build_start_win] Robocopy failed.
  exit /b 1
)

if exist "%TARGET_DIR%\%EXE_NAME%" (
  echo [build_start_win] Starting %EXE_NAME%...
  start "" "%TARGET_DIR%\%EXE_NAME%"
) else (
  echo [build_start_win] Executable not found: "%TARGET_DIR%\%EXE_NAME%"
  exit /b 1
)

exit /b 0
