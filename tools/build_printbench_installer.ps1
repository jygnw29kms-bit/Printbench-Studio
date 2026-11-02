param(
    [string]$BuildDir = "",
    [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if ([string]::IsNullOrWhiteSpace($BuildDir)) {
    $BuildDir = Join-Path $Root "app\orcaslicer\build-printbench-check"
}
if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $OutputDir = Join-Path $Root "dist\windows"
}

$CPack = "C:\Program Files\CMake\bin\cpack.exe"
if (-not (Test-Path $CPack)) {
    $CPackCommand = Get-Command cpack.exe -ErrorAction Stop
    $CPack = $CPackCommand.Source
}
$VersionText = (& $CPack --version | Select-Object -First 1)
if ($VersionText -notmatch '([0-9]+)\.([0-9]+)') {
    throw "Unable to determine CPack version from: $VersionText"
}
if ([int]$Matches[1] -lt 4) {
    throw "PRINTBENCH installer packaging requires CPack 4.x+ for the Visual Studio 18 generator. Found: $VersionText"
}

$NsisDir = "C:\Program Files (x86)\NSIS"
$MakeNsis = Join-Path $NsisDir "makensis.exe"
if (-not (Test-Path $MakeNsis)) {
    throw "NSIS compiler missing: $MakeNsis"
}
$env:PATH = "$NsisDir;$([IO.Path]::GetDirectoryName($CPack));$env:PATH"

$Config = Join-Path $BuildDir "CPackConfig.cmake"
if (-not (Test-Path $Config)) {
    throw "CPackConfig.cmake missing. Build PRINTBENCH first: $Config"
}

$StageDir = Join-Path $env:LOCALAPPDATA "PB\pkg"
Remove-Item $StageDir -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $StageDir -Force | Out-Null

Push-Location $BuildDir
try {
    & $CPack -G NSIS -C Release -B $StageDir
    if ($LASTEXITCODE -ne 0) { throw "CPack/NSIS failed with exit code $LASTEXITCODE" }
}
finally {
    Pop-Location
}

$Installer = Get-ChildItem $StageDir -File -Filter "135er-PRINTBENCH*.exe" |
    Sort-Object LastWriteTimeUtc -Descending |
    Select-Object -First 1
if (-not $Installer) {
    throw "PRINTBENCH installer was not produced under $StageDir"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
$Final = Join-Path $OutputDir $Installer.Name
Copy-Item $Installer.FullName $Final -Force
$Hash = (Get-FileHash $Final -Algorithm SHA256).Hash
Write-Host "PRINTBENCH installer complete."
Write-Host "Installer: $Final"
Write-Host "SHA256:    $Hash"
