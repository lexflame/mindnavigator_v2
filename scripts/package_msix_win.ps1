param(
    [string]$DistDir = "dist\MindNavigator (windows 11 x64)",
    [string]$OutputDir = "dist\msix",
    [string]$PackageName = "MindNavigator.Desktop",
    [string]$Publisher = "CN=MindNavigator",
    [string]$PublisherDisplayName = "MindNavigator",
    [string]$DisplayName = "MindNavigator",
    [string]$Description = "MindNavigator desktop workspace",
    [string]$Version = "1.0.0.0",
    [string]$MakeAppxPath = "",
    [switch]$SkipBuild,
    [switch]$StageOnly
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$manifestTemplate = Join-Path $repoRoot "packaging\msix\AppxManifest.xml.in"
$resolvedDistDir = Join-Path $repoRoot $DistDir
$resolvedOutputDir = Join-Path $repoRoot $OutputDir
$stagingRoot = Join-Path $resolvedOutputDir "staging"
$outputPackage = Join-Path $resolvedOutputDir "MindNavigator.msix"

function ConvertTo-XmlText {
    param([string]$Value)
    return [System.Security.SecurityElement]::Escape($Value)
}

function Find-MakeAppx {
    param([string]$ExplicitPath)

    if ($ExplicitPath) {
        if (-not (Test-Path -LiteralPath $ExplicitPath)) {
            throw "MakeAppx.exe not found: $ExplicitPath"
        }
        return (Resolve-Path $ExplicitPath).Path
    }

    $sdkBin = Join-Path ${env:ProgramFiles(x86)} "Windows Kits\10\bin"
    if (Test-Path -LiteralPath $sdkBin) {
        $candidate = Get-ChildItem -LiteralPath $sdkBin -Recurse -Filter "makeappx.exe" -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -match "\\x64\\makeappx\.exe$" } |
            Sort-Object FullName -Descending |
            Select-Object -First 1
        if ($candidate) {
            return $candidate.FullName
        }
    }

    $certKit = Join-Path ${env:ProgramFiles(x86)} "Windows Kits\10\App Certification Kit\makeappx.exe"
    if (Test-Path -LiteralPath $certKit) {
        return (Resolve-Path $certKit).Path
    }

    throw "MakeAppx.exe not found. Install Windows 10/11 SDK or pass -MakeAppxPath."
}

function Save-PngLogo {
    param(
        [System.Drawing.Icon]$Icon,
        [string]$Path,
        [int]$Width,
        [int]$Height
    )

    $bitmap = New-Object System.Drawing.Bitmap $Width, $Height
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    try {
        $graphics.Clear([System.Drawing.Color]::Transparent)
        $targetRect = New-Object System.Drawing.Rectangle 0, 0, $Width, $Height
        $graphics.DrawIcon($Icon, $targetRect)
        $bitmap.Save($Path, [System.Drawing.Imaging.ImageFormat]::Png)
    }
    finally {
        $graphics.Dispose()
        $bitmap.Dispose()
    }
}

if (-not $SkipBuild) {
    $buildScript = Join-Path $repoRoot "scripts\build_win.bat"
    & $buildScript
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller build failed with exit code $LASTEXITCODE."
    }
}

if (-not (Test-Path -LiteralPath $resolvedDistDir)) {
    throw "Dist directory not found: $resolvedDistDir"
}

$exePath = Join-Path $resolvedDistDir "MindNavigator.exe"
if (-not (Test-Path -LiteralPath $exePath)) {
    throw "Executable not found: $exePath"
}

if (Test-Path -LiteralPath $stagingRoot) {
    Remove-Item -LiteralPath $stagingRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $stagingRoot -Force | Out-Null

Copy-Item -Path (Join-Path $resolvedDistDir "*") -Destination $stagingRoot -Recurse -Force

$assetsDir = Join-Path $stagingRoot "Assets"
New-Item -ItemType Directory -Path $assetsDir -Force | Out-Null

$iconPath = Join-Path $repoRoot "assets\icon.ico"
if (-not (Test-Path -LiteralPath $iconPath)) {
    throw "Icon not found: $iconPath"
}

Add-Type -AssemblyName System.Drawing
$icon = New-Object System.Drawing.Icon $iconPath
try {
    Save-PngLogo -Icon $icon -Path (Join-Path $assetsDir "StoreLogo.png") -Width 50 -Height 50
    Save-PngLogo -Icon $icon -Path (Join-Path $assetsDir "Square44x44Logo.png") -Width 44 -Height 44
    Save-PngLogo -Icon $icon -Path (Join-Path $assetsDir "Square71x71Logo.png") -Width 71 -Height 71
    Save-PngLogo -Icon $icon -Path (Join-Path $assetsDir "Square150x150Logo.png") -Width 150 -Height 150
    Save-PngLogo -Icon $icon -Path (Join-Path $assetsDir "Wide310x150Logo.png") -Width 310 -Height 150
    Save-PngLogo -Icon $icon -Path (Join-Path $assetsDir "Square310x310Logo.png") -Width 310 -Height 310
}
finally {
    $icon.Dispose()
}

$manifest = Get-Content -LiteralPath $manifestTemplate -Raw
$replacements = @{
    "{{PackageName}}" = $PackageName
    "{{Publisher}}" = $Publisher
    "{{Version}}" = $Version
    "{{DisplayName}}" = $DisplayName
    "{{PublisherDisplayName}}" = $PublisherDisplayName
    "{{Description}}" = $Description
}

foreach ($placeholder in $replacements.Keys) {
    $manifest = $manifest.Replace($placeholder, (ConvertTo-XmlText $replacements[$placeholder]))
}

$manifestPath = Join-Path $stagingRoot "AppxManifest.xml"
Set-Content -LiteralPath $manifestPath -Value $manifest -Encoding UTF8

Write-Host "[package_msix_win] Staged package root: $stagingRoot"

if ($StageOnly) {
    Write-Host "[package_msix_win] StageOnly requested; skipping MakeAppx."
    exit 0
}

New-Item -ItemType Directory -Path $resolvedOutputDir -Force | Out-Null
$makeAppx = Find-MakeAppx -ExplicitPath $MakeAppxPath

& $makeAppx pack /o /v /h SHA256 /d $stagingRoot /p $outputPackage
if ($LASTEXITCODE -ne 0) {
    throw "MakeAppx failed with exit code $LASTEXITCODE."
}

Write-Host "[package_msix_win] Created: $outputPackage"
