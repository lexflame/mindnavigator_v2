@echo off
setlocal enabledelayedexpansion

set "APP_NAME=MindNavigator"
set "TARGET_DIR=C:\Program Portable\MindNavigator"
set "FALLBACK_TARGET_DIR=.\artifacts\run"
set "DIST_SUBDIR=MindNavigator (windows 11 x64)"
set "DIST_DIR=dist\%DIST_SUBDIR%"
set "EXE_NAME=MindNavigator.exe"
set "DEBUG_BUILD_START=%DEBUG_BUILD_START%"

if not "%~1"=="" (
  set "TARGET_DIR=%~1"
)

if "%DEBUG_BUILD_START%"=="1" (
  echo [build_start_win][debug] APP_NAME=!APP_NAME!
  echo [build_start_win][debug] TARGET_DIR=!TARGET_DIR!
  echo [build_start_win][debug] DIST_DIR=!DIST_DIR!
)

call "%~dp0build_win.bat"
set "BUILD_EXIT=%ERRORLEVEL%"
if "%DEBUG_BUILD_START%"=="1" echo [build_start_win][debug] build_win exit=%BUILD_EXIT%

if not exist "%DIST_DIR%\%EXE_NAME%" (
  echo [build_start_win] Build output is missing: "%DIST_DIR%\%EXE_NAME%"
  exit /b 1
)

if not exist "!TARGET_DIR!" (
  mkdir "!TARGET_DIR!" 2>nul
  if errorlevel 1 (
    echo [build_start_win] Cannot create target directory: "!TARGET_DIR!"
    echo [build_start_win] Fallback to "!FALLBACK_TARGET_DIR!".
    set "TARGET_DIR=!FALLBACK_TARGET_DIR!"
    if not exist "!TARGET_DIR!" (
      mkdir "!TARGET_DIR!" 2>nul
      if errorlevel 1 (
        echo [build_start_win] Cannot create fallback target directory: "!TARGET_DIR!"
        exit /b 1
      )
    )
  )
)

echo [build_start_win] Syncing build to "%TARGET_DIR%"...
robocopy "%DIST_DIR%" "%TARGET_DIR%" /MIR /R:1 /W:1 >nul
set "ROBOCOPY_EXIT=%ERRORLEVEL%"
if "%DEBUG_BUILD_START%"=="1" echo [build_start_win][debug] robocopy exit=%ROBOCOPY_EXIT%
if errorlevel 8 (
  echo [build_start_win] Robocopy failed with code %ROBOCOPY_EXIT%.
  exit /b 1
)

if exist "%TARGET_DIR%\%EXE_NAME%" (
  echo [build_start_win] Starting %EXE_NAME%...
  start "" "%TARGET_DIR%\%EXE_NAME%"
  set "START_EXIT=!ERRORLEVEL!"
  if "%DEBUG_BUILD_START%"=="1" echo [build_start_win][debug] start exit=%START_EXIT%
  if not "%START_EXIT%"=="0" (
    echo [build_start_win] Warning: failed to start "%TARGET_DIR%\%EXE_NAME%".
    echo [build_start_win] Build and sync completed; launch step skipped.
  )
) else (
  echo [build_start_win] Executable not found: "%TARGET_DIR%\%EXE_NAME%"
  exit /b 1
)

exit /b 0
