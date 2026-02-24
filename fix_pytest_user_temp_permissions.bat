@echo off
setlocal EnableExtensions

set "TMP_ROOT=%LOCALAPPDATA%\Temp"
set "PYTEST_ROOT=%TMP_ROOT%\pytest-of-%USERNAME%"

echo [INFO] Target temp root: "%PYTEST_ROOT%"

if exist "%PYTEST_ROOT%" (
  echo [STEP] Remove attrs...
  attrib -R -S -H "%PYTEST_ROOT%" /S /D 2>nul

  echo [STEP] Take ownership...
  takeown /f "%PYTEST_ROOT%" /r /d y >nul 2>&1

  echo [STEP] Enable inheritance and grant full control...
  icacls "%PYTEST_ROOT%" /inheritance:e >nul
  icacls "%PYTEST_ROOT%" /grant "%USERNAME%:(OI)(CI)F" /t >nul

  echo [STEP] Remove stale pytest temp tree...
  rmdir /s /q "%PYTEST_ROOT%"
)

echo [STEP] Recreate clean pytest temp root...
mkdir "%PYTEST_ROOT%" >nul 2>&1

echo [STEP] Re-apply ownership and ACL...
takeown /f "%PYTEST_ROOT%" /r /d y >nul 2>&1
icacls "%PYTEST_ROOT%" /inheritance:e >nul
icacls "%PYTEST_ROOT%" /grant "%USERNAME%:(OI)(CI)F" /t >nul

echo.
echo [DONE] User pytest temp permissions fixed.
echo [INFO] Verify:
echo        icacls "%PYTEST_ROOT%"

endlocal
exit /b 0
