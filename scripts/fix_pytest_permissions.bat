@echo off
setlocal EnableExtensions

set "SCRIPT_DIR=%~dp0"
set "REPO_ROOT=%SCRIPT_DIR%.."
cd /d "%REPO_ROOT%"
echo [INFO] Working directory: %CD%
echo [INFO] Script location: %SCRIPT_DIR%

set "PYTEST_ROOT=.pytest_dir"
set "TARGET1=%PYTEST_ROOT%\tmp"
set "TARGET2=%PYTEST_ROOT%\run_tmp"
set "LEGACY_TARGET1=.pytest_tmp"
set "LEGACY_TARGET2=.pytest_run_tmp"

echo [STEP] Remove read-only/system/hidden attributes (if present)...
attrib -R -S -H "%PYTEST_ROOT%" /S /D >nul 2>&1
attrib -R -S -H "%TARGET1%" /S /D >nul 2>&1
attrib -R -S -H "%TARGET2%" /S /D >nul 2>&1
attrib -R -S -H "%LEGACY_TARGET1%" /S /D >nul 2>&1
attrib -R -S -H "%LEGACY_TARGET2%*" /S /D >nul 2>&1

echo [STEP] Take ownership (if folders exist)...
if exist "%TARGET1%" takeown /f "%TARGET1%" /r /d y >nul 2>&1
if exist "%TARGET2%" takeown /f "%TARGET2%" /r /d y >nul 2>&1
if exist "%LEGACY_TARGET1%" takeown /f "%LEGACY_TARGET1%" /r /d y >nul 2>&1
if exist "%LEGACY_TARGET2%" takeown /f "%LEGACY_TARGET2%" /r /d y >nul 2>&1

echo [STEP] Enable inheritance and grant full control to current user...
if exist "%PYTEST_ROOT%" icacls "%PYTEST_ROOT%" /inheritance:e >nul 2>&1
if exist "%PYTEST_ROOT%" icacls "%PYTEST_ROOT%" /grant "%USERNAME%:(OI)(CI)F" /t >nul 2>&1
if exist "%TARGET1%" icacls "%TARGET1%" /inheritance:e >nul 2>&1
if exist "%TARGET1%" icacls "%TARGET1%" /grant "%USERNAME%:(OI)(CI)F" /t >nul 2>&1
if exist "%TARGET2%" icacls "%TARGET2%" /inheritance:e >nul 2>&1
if exist "%TARGET2%" icacls "%TARGET2%" /grant "%USERNAME%:(OI)(CI)F" /t >nul 2>&1
if exist "%LEGACY_TARGET1%" icacls "%LEGACY_TARGET1%" /inheritance:e >nul 2>&1
if exist "%LEGACY_TARGET1%" icacls "%LEGACY_TARGET1%" /grant "%USERNAME%:(OI)(CI)F" /t >nul 2>&1
if exist "%LEGACY_TARGET2%" icacls "%LEGACY_TARGET2%" /inheritance:e >nul 2>&1
if exist "%LEGACY_TARGET2%" icacls "%LEGACY_TARGET2%" /grant "%USERNAME%:(OI)(CI)F" /t >nul 2>&1

echo [STEP] Remove stale local pytest folders...
if exist "%LEGACY_TARGET1%" rmdir /s /q "%LEGACY_TARGET1%" >nul 2>&1
for /d %%D in (%LEGACY_TARGET2%*) do rmdir /s /q "%%D" >nul 2>&1
if exist "%TARGET1%" rmdir /s /q "%TARGET1%" >nul 2>&1
if exist "%TARGET2%" rmdir /s /q "%TARGET2%" >nul 2>&1

echo [STEP] Recreate local pytest folder layout...
mkdir "%PYTEST_ROOT%" >nul 2>&1
mkdir "%TARGET1%" >nul 2>&1
mkdir "%TARGET2%" >nul 2>&1

echo [STEP] Re-apply ownership and ACL to fresh folders...
takeown /f "%PYTEST_ROOT%" /r /d y >nul 2>&1
takeown /f "%TARGET1%" /r /d y >nul 2>&1
takeown /f "%TARGET2%" /r /d y >nul 2>&1
icacls "%PYTEST_ROOT%" /inheritance:e >nul 2>&1
icacls "%PYTEST_ROOT%" /grant "%USERNAME%:(OI)(CI)F" /t >nul 2>&1
icacls "%TARGET1%" /inheritance:e >nul 2>&1
icacls "%TARGET1%" /grant "%USERNAME%:(OI)(CI)F" /t >nul 2>&1
icacls "%TARGET2%" /inheritance:e >nul 2>&1
icacls "%TARGET2%" /grant "%USERNAME%:(OI)(CI)F" /t >nul 2>&1

echo [STEP] Repoint old pytest names to .pytest_dir...
if exist "%LEGACY_TARGET1%" rmdir /s /q "%LEGACY_TARGET1%" >nul 2>&1
if exist "%LEGACY_TARGET2%" rmdir /s /q "%LEGACY_TARGET2%" >nul 2>&1
mklink /J "%LEGACY_TARGET1%" "%TARGET1%" >nul 2>&1
mklink /J "%LEGACY_TARGET2%" "%TARGET2%" >nul 2>&1

echo.
echo [DONE] Permissions were updated.
echo [INFO] Verify:
echo        icacls "%PYTEST_ROOT%"
echo        icacls "%TARGET1%"
echo        icacls "%TARGET2%"
echo [INFO] Then run tests:
echo        set PYTHONPATH=.
echo        pytest tests -q -p no:cacheprovider --basetemp .pytest_dir\run_tmp

endlocal
exit /b 0
