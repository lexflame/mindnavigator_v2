@echo off
setlocal EnableExtensions

set "DRY_RUN=False"
if /I "%~1"=="/dry-run" set "DRY_RUN=True"

echo [INFO] Installing IDE-like dark theme for PowerShell...
if /I "%DRY_RUN%"=="True" echo [INFO] Dry-run mode enabled. No files will be changed.

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference = 'Stop';" ^
  "$dryRun = [System.Convert]::ToBoolean($env:DRY_RUN);" ^
  "$startMarker = '# [codex ide dark theme begin]';" ^
  "$endMarker = '# [codex ide dark theme end]';" ^
  "$themeLines = @(" ^
  "'# [codex ide dark theme begin]'," ^
  "'function Set-MnIdeConsoleTheme {'," ^
  "'  try {'," ^
  "'    $rawUi = $Host.UI.RawUI'," ^
  "'    $rawUi.BackgroundColor = ''Black'''," ^
  "'    $rawUi.ForegroundColor = ''Gray'''," ^
  "'    $privateData = $Host.PrivateData'," ^
  "'    $privateData.ErrorForegroundColor = ''Red'''," ^
  "'    $privateData.WarningForegroundColor = ''Yellow'''," ^
  "'    $privateData.DebugForegroundColor = ''DarkYellow'''," ^
  "'    $privateData.VerboseForegroundColor = ''Cyan'''," ^
  "'    $privateData.ProgressForegroundColor = ''Gray'''," ^
  "'    $privateData.ProgressBackgroundColor = ''Black'''," ^
  "'  } catch {}'," ^
  "'}'," ^
  "''," ^
  "'function Set-MnIdeReadLineTheme {'," ^
  "'  try {'," ^
  "'    Set-PSReadLineOption -PredictionViewStyle InlineView'," ^
  "'    Set-PSReadLineOption -Colors @{'," ^
  "'      Default                = ""`e[38;2;171;178;191m""'," ^
  "'      Comment                = ""`e[38;2;92;99;112m""'," ^
  "'      Keyword                = ""`e[38;2;198;120;221m""'," ^
  "'      String                 = ""`e[38;2;152;195;121m""'," ^
  "'      Operator               = ""`e[38;2;86;182;194m""'," ^
  "'      Variable               = ""`e[38;2;224;108;117m""'," ^
  "'      Command                = ""`e[38;2;97;175;239m""'," ^
  "'      Parameter              = ""`e[38;2;209;154;102m""'," ^
  "'      Type                   = ""`e[38;2;229;192;123m""'," ^
  "'      Number                 = ""`e[38;2;209;154;102m""'," ^
  "'      Member                 = ""`e[38;2;86;182;194m""'," ^
  "'      Selection              = ""`e[48;2;49;54;63m`e[38;2;171;178;191m""'," ^
  "'      Emphasis               = ""`e[38;2;229;192;123m""'," ^
  "'      InlinePrediction       = ""`e[38;2;92;99;112m""'," ^
  "'      ListPrediction         = ""`e[38;2;92;99;112m""'," ^
  "'      ListPredictionSelected = ""`e[48;2;49;54;63m`e[38;2;97;175;239m""'," ^
  "'      ContinuationPrompt     = ""`e[38;2;92;99;112m""'," ^
  "'      Error                  = ""`e[38;2;224;108;117m""'," ^
  "'    }'," ^
  "'  } catch {}'," ^
  "'}'," ^
  "''," ^
  "'Set-MnIdeConsoleTheme'," ^
  "'Set-MnIdeReadLineTheme'," ^
  "'if (-not $script:MnOldPrompt) { $script:MnOldPrompt = $function:prompt }'," ^
  "'$function:prompt = {'," ^
  "'  Set-MnIdeConsoleTheme'," ^
  "'  & $script:MnOldPrompt'," ^
  "'}'," ^
  "'# [codex ide dark theme end]'" ^
  ");" ^
  "$newline = [Environment]::NewLine;" ^
  "$themeBlock = [string]::Join($newline, $themeLines) + $newline;" ^
  "$profilePath = $PROFILE.CurrentUserCurrentHost;" ^
  "$profileDir = Split-Path -Parent $profilePath;" ^
  "if (-not (Test-Path -LiteralPath $profileDir)) { New-Item -ItemType Directory -Path $profileDir -Force | Out-Null };" ^
  "$existing = '';" ^
  "if (Test-Path -LiteralPath $profilePath) { $existing = Get-Content -LiteralPath $profilePath -Raw };" ^
  "$escapedStart = [regex]::Escape($startMarker);" ^
  "$escapedEnd = [regex]::Escape($endMarker);" ^
  "$pattern = '(?ms)^' + $escapedStart + '\r?\n.*?^' + $escapedEnd + '\r?\n?';" ^
  "$clean = [regex]::Replace($existing, $pattern, '');" ^
  "if ($clean.Length -gt 0 -and -not $clean.EndsWith($newline)) { $clean += $newline };" ^
  "$updated = $clean + $themeBlock;" ^
  "if ($dryRun) { Write-Output ('[DRY-RUN] Profile: ' + $profilePath); Write-Output ('[DRY-RUN] Managed block length: ' + $themeBlock.Length); exit 0 };" ^
  "$timestamp = Get-Date -Format 'yyyyMMdd-HHmmss';" ^
  "if (Test-Path -LiteralPath $profilePath) { Copy-Item -LiteralPath $profilePath -Destination ($profilePath + '.bak-' + $timestamp) -Force };" ^
  "Set-Content -LiteralPath $profilePath -Value $updated -Encoding UTF8;" ^
  "Write-Output ('[DONE] Updated profile: ' + $profilePath);" ^
  "Write-Output '[INFO] Reopen PowerShell to apply the theme.';" ^
  "Write-Output '[INFO] If profiles are blocked, run: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned';"

set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" (
  echo [ERROR] Theme installation failed with exit code %EXIT_CODE%.
  exit /b %EXIT_CODE%
)

echo [DONE] PowerShell dark theme script finished successfully.
exit /b 0
