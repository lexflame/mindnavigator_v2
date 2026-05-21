@echo off
setlocal enabledelayedexpansion

set "APP_NAME=MindNavigator"
set "TARGET_DIR=C:\Program Portable\MindNavigator"
set "FALLBACK_TARGET_DIR=.\artifacts\run"
set "DIST_SUBDIR=MindNavigator (windows 11 x64)"
set "DIST_DIR=dist\%DIST_SUBDIR%"
set "EXE_NAME=MindNavigator.exe"
set "APP_CONFIG_NAME=app_config.json"
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

set "TARGET_APP_CONFIG=!TARGET_DIR!\%APP_CONFIG_NAME%"
set "DIST_APP_CONFIG=%DIST_DIR%\%APP_CONFIG_NAME%"
set "APP_CONFIG_STAGED=0"

if exist "!TARGET_APP_CONFIG!" (
  echo [build_start_win] Preserving "%APP_CONFIG_NAME%" from "!TARGET_DIR!"...
  copy /Y "!TARGET_APP_CONFIG!" "!DIST_APP_CONFIG!" >nul
  if errorlevel 1 (
    echo [build_start_win] Failed to stage "%APP_CONFIG_NAME%" into "%DIST_DIR%".
    exit /b 1
  )
  set "APP_CONFIG_STAGED=1"
) else (
  if exist "!DIST_APP_CONFIG!" (
    del /F /Q "!DIST_APP_CONFIG!" >nul 2>&1
  )
)

tasklist /FI "IMAGENAME eq %EXE_NAME%" | find /I "%EXE_NAME%" >nul 2>&1
if "%ERRORLEVEL%"=="0" (
  echo [build_start_win] Stopping running %EXE_NAME%...
  taskkill /IM "%EXE_NAME%" /F >nul 2>&1
)

echo [build_start_win] Syncing build to "%TARGET_DIR%"...
robocopy "%DIST_DIR%" "%TARGET_DIR%" /MIR /R:1 /W:1 >nul
set "ROBOCOPY_EXIT=%ERRORLEVEL%"
if "%DEBUG_BUILD_START%"=="1" echo [build_start_win][debug] robocopy exit=%ROBOCOPY_EXIT%
if errorlevel 8 (
  echo [build_start_win] Robocopy failed with code %ROBOCOPY_EXIT%.
  exit /b 1
)

if "!APP_CONFIG_STAGED!"=="1" if exist "!DIST_APP_CONFIG!" (
  move /Y "!DIST_APP_CONFIG!" "!TARGET_APP_CONFIG!" >nul
  if errorlevel 1 (
    echo [build_start_win] Warning: failed to move "%APP_CONFIG_NAME%" back to "!TARGET_DIR!".
  )
)

set "FOLDER_ICON_REL=assets\icon.ico"
set "FOLDER_ICON_ABS=%TARGET_DIR%\%FOLDER_ICON_REL%"
if not exist "%FOLDER_ICON_ABS%" (
  if exist "%TARGET_DIR%\_internal\assets\icon.ico" (
    if not exist "%TARGET_DIR%\assets" mkdir "%TARGET_DIR%\assets" >nul 2>&1
    copy /Y "%TARGET_DIR%\_internal\assets\icon.ico" "%FOLDER_ICON_ABS%" >nul
  )
)
if exist "%FOLDER_ICON_ABS%" (
  >"%TARGET_DIR%\desktop.ini" (
    echo [.ShellClassInfo]
    echo IconResource=%FOLDER_ICON_REL%,0
  )
  attrib +h +s "%TARGET_DIR%\desktop.ini" >nul 2>&1
  attrib +s "%TARGET_DIR%" >nul 2>&1
  if "%DEBUG_BUILD_START%"=="1" echo [build_start_win][debug] folder icon configured: %FOLDER_ICON_REL%
) else (
  echo [build_start_win] Warning: folder icon source not found.
)

if exist "%TARGET_DIR%\%EXE_NAME%" (
  echo [build_start_win] Starting %EXE_NAME%...
  powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ^
    "try { Start-Process -FilePath '%TARGET_DIR%\%EXE_NAME%' -WorkingDirectory '%TARGET_DIR%' -ErrorAction Stop; exit 0 } catch { Write-Host $_.Exception.Message; exit 1 }"
  set "START_EXIT=%ERRORLEVEL%"
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
