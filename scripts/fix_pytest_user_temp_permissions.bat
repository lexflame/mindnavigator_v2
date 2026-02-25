@echo off
setlocal EnableExtensions

set "SCRIPT_DIR=%~dp0"
set "REPO_ROOT=%SCRIPT_DIR%.."
cd /d "%REPO_ROOT%"

set "PYTEST_ROOT=.pytest_dir\user_tmp\pytest-of-%USERNAME%"

echo [INFO] Working directory: %CD%
echo [INFO] Target user temp root: "%PYTEST_ROOT%"

echo [STEP] Remove attrs...
attrib -R -S -H "%PYTEST_ROOT%" /S /D >nul 2>&1
if exist "%PYTEST_ROOT%" (
  echo [STEP] Remove stale pytest temp tree...
  rmdir /s /q "%PYTEST_ROOT%" >nul 2>&1
)

echo [STEP] Recreate clean pytest temp root...
mkdir "%PYTEST_ROOT%" >nul 2>&1

echo [STEP] Re-apply ownership and ACL...
takeown /f "%PYTEST_ROOT%" /r /d y >nul 2>&1
icacls "%PYTEST_ROOT%" /inheritance:e >nul 2>&1
icacls "%PYTEST_ROOT%" /grant "%USERNAME%:(OI)(CI)F" /t >nul 2>&1

echo.
echo [DONE] User pytest temp permissions fixed.
echo [INFO] Verify:
echo        icacls "%PYTEST_ROOT%"
echo [INFO] Optional one-shot run with local temp root:
echo        set PYTHONPATH=. ^&^& set TMP=.pytest_dir\user_tmp ^&^& set TEMP=.pytest_dir\user_tmp ^&^& pytest tests -q -p no:cacheprovider --basetemp .pytest_dir\run_tmp

endlocal
exit /b 0
