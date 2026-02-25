@echo off
setlocal

set "PROMPT_TEXT=%~1"
set "TOKEN_FILE=%~dp0ghp_token"

if not exist "%TOKEN_FILE%" exit /b 1

set /p TOKEN=<"%TOKEN_FILE%"

echo %PROMPT_TEXT% | findstr /I "Username" >nul
if not errorlevel 1 (
    echo x-access-token
    exit /b 0
)

echo %PROMPT_TEXT% | findstr /I "Password" >nul
if not errorlevel 1 (
    echo %TOKEN%
    exit /b 0
)

echo %TOKEN%
exit /b 0
