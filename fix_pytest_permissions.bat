@echo off
setlocal EnableExtensions

cd /d "%~dp0"
echo [INFO] Working directory: %CD%

set "TARGET1=.pytest_tmp"
set "TARGET2=.pytest_run_tmp"

echo [STEP] Remove read-only/system/hidden attributes (if present)...
attrib -R -S -H "%TARGET1%" /S /D 2>nul
attrib -R -S -H ".pytest_run_tmp*" /S /D 2>nul

echo [STEP] Take ownership (if folders exist)...
if exist "%TARGET1%" takeown /f "%TARGET1%" /r /d y >nul 2>&1
if exist "%TARGET2%" takeown /f "%TARGET2%" /r /d y >nul 2>&1

echo [STEP] Enable inheritance and grant full control to current user...
if exist "%TARGET1%" icacls "%TARGET1%" /inheritance:e >nul
if exist "%TARGET1%" icacls "%TARGET1%" /grant "%USERNAME%:(OI)(CI)F" /t >nul
if exist "%TARGET2%" icacls "%TARGET2%" /inheritance:e >nul
if exist "%TARGET2%" icacls "%TARGET2%" /grant "%USERNAME%:(OI)(CI)F" /t >nul

echo [STEP] Remove stale pytest temp folders...
if exist "%TARGET1%" rmdir /s /q "%TARGET1%"
for /d %%D in (.pytest_run_tmp*) do rmdir /s /q "%%D"

echo [STEP] Recreate clean temp folders...
mkdir "%TARGET1%" >nul 2>&1
mkdir "%TARGET2%" >nul 2>&1

echo [STEP] Re-apply ownership and ACL to fresh folders...
takeown /f "%TARGET1%" /r /d y >nul 2>&1
takeown /f "%TARGET2%" /r /d y >nul 2>&1
icacls "%TARGET1%" /inheritance:e >nul
icacls "%TARGET1%" /grant "%USERNAME%:(OI)(CI)F" /t >nul
icacls "%TARGET2%" /inheritance:e >nul
icacls "%TARGET2%" /grant "%USERNAME%:(OI)(CI)F" /t >nul

echo.
echo [DONE] Permissions were updated.
echo [INFO] Verify:
echo        icacls "%TARGET1%"
echo        icacls "%TARGET2%"
echo [INFO] Then run tests:
echo        set PYTHONPATH=.
echo        pytest tests -q -p no:cacheprovider --basetemp .pytest_run_tmp

endlocal
exit /b 0
