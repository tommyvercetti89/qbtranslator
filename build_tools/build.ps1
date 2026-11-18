# QBTranslator build and packaging script.
# Usage:
#   powershell -ExecutionPolicy Bypass -File build_tools\build.ps1
#   powershell -ExecutionPolicy Bypass -File build_tools\build.ps1 -SkipInstaller
#   powershell -ExecutionPolicy Bypass -File build_tools\build.ps1 -SkipPortable -SkipInstaller

param(
    [switch]$SkipPortable,
    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$ReleaseDir = Join-Path $Root "release"
$env:PYTHONPATH = Join-Path $Root "src"
$Version = (python -c "from qbtranslator import APP_VERSION; print(APP_VERSION)").Trim()
Set-Location $Root

function Get-DirectorySizeMB([string]$Path) {
    if (-not (Test-Path $Path)) { return 0 }
    $sum = (Get-ChildItem -Recurse -File $Path | Measure-Object Length -Sum).Sum
    return [math]::Round($sum / 1MB, 1)
}

function Invoke-Selftest([string]$Executable, [string]$Name) {
    $dataDir = Join-Path $env:TEMP ("qb_selftest_" + $Name)
    Remove-Item -Recurse -Force $dataDir -ErrorAction SilentlyContinue
    $env:QB_DATA_DIR = $dataDir
    $env:QB_DISABLE_AUTOSTART = "1"
    $process = Start-Process -FilePath $Executable -ArgumentList "--selftest" -Wait -PassThru
    $resultFile = Join-Path $dataDir "selftest_result.txt"
    if (Test-Path $resultFile) {
        Get-Content $resultFile | ForEach-Object { Write-Host "  $_" }
    }
    if ($process.ExitCode -ne 0) {
        throw "$Name selftest failed with exit code $($process.ExitCode)"
    }
    Write-Host "$Name selftest: OK"
}

Write-Host "== QBTranslator $Version build =="
Write-Host "== Cleaning previous output =="
Remove-Item -Recurse -Force "$Root\build", "$Root\dist", "$Root\installer", "$Root\release" -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $ReleaseDir | Out-Null

Write-Host "== Building onedir package =="
python -m PyInstaller --noconfirm --clean "build_tools\QBTranslator.spec"
if ($LASTEXITCODE -ne 0) { throw "PyInstaller onedir build failed" }

$onedir = Join-Path $Root "dist\QBTranslator"
$exe = Join-Path $onedir "QBTranslator.exe"
if (-not (Test-Path $exe)) { throw "Onedir executable was not created" }

foreach ($doc in @("README.md", "README.tr.md", "CHANGELOG.md", "LICENSE", "THIRD_PARTY_NOTICES.md", "SECURITY.md", "RELEASING.md")) {
    $source = Join-Path $Root $doc
    if (Test-Path $source) {
        Copy-Item $source -Destination $onedir -Force
    }
}
if (Test-Path (Join-Path $Root "docs")) {
    Copy-Item (Join-Path $Root "docs") -Destination $onedir -Recurse -Force
}
if (Test-Path (Join-Path $Root "LICENSES")) {
    Copy-Item (Join-Path $Root "LICENSES") -Destination $onedir -Recurse -Force
}

Write-Host ("Onedir size: {0} MB" -f (Get-DirectorySizeMB $onedir))
Invoke-Selftest $exe "onedir"

$zipPath = Join-Path $ReleaseDir ("QBTranslator-{0}-windows-x64.zip" -f $Version)
Write-Host "== Creating onedir ZIP =="
Compress-Archive -Path $onedir -DestinationPath $zipPath -CompressionLevel Optimal -Force
Write-Host ("ZIP: {0} ({1:N1} MB)" -f $zipPath, ((Get-Item $zipPath).Length / 1MB))

if (-not $SkipPortable) {
    Write-Host "== Building single-file portable package =="
    python -m PyInstaller --noconfirm --clean "build_tools\QBTranslator-portable.spec"
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller portable build failed" }
    $portableSource = Join-Path $Root "dist\QBTranslator-Portable.exe"
    if (-not (Test-Path $portableSource)) { throw "Portable executable was not created" }
    $portableTarget = Join-Path $ReleaseDir ("QBTranslator-Portable-{0}.exe" -f $Version)
    Move-Item -Force $portableSource $portableTarget
    Write-Host ("Portable: {0} ({1:N1} MB)" -f $portableTarget, ((Get-Item $portableTarget).Length / 1MB))
    Invoke-Selftest $portableTarget "portable"
}

if (-not $SkipInstaller) {
    $isccCandidates = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
    )
    $iscc = $isccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
    if ($iscc) {
        Write-Host "== Building installer =="
        & $iscc "/DMyAppVersion=$Version" "build_tools\installer.iss"
        if ($LASTEXITCODE -ne 0) { throw "Inno Setup build failed" }
        $setup = Get-ChildItem (Join-Path $Root "installer") -Filter "QBTranslator-Setup-*.exe" |
            Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if (-not $setup) { throw "Installer was not created" }
        Copy-Item $setup.FullName -Destination $ReleaseDir -Force
        Write-Host ("Installer: {0} ({1:N1} MB)" -f $setup.FullName, ($setup.Length / 1MB))
    } else {
        Write-Host "Inno Setup not found; skipping installer."
    }
}

$hashFile = Join-Path $ReleaseDir "SHA256SUMS.txt"
Get-ChildItem $ReleaseDir -File | Where-Object { $_.Name -ne "SHA256SUMS.txt" } |
    ForEach-Object {
        $hash = (Get-FileHash $_.FullName -Algorithm SHA256).Hash
        "{0}  {1}" -f $hash, $_.Name
    } | Set-Content -Path $hashFile -Encoding ascii

Write-Host "== Release artifacts =="
Get-ChildItem $ReleaseDir -File | Select-Object Name, @{Name = "MB"; Expression = { [math]::Round($_.Length / 1MB, 1) } }
Write-Host "DONE"
