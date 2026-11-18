# QBTranslator — derleme ve paketleme
# Kullanım:  powershell -ExecutionPolicy Bypass -File build_tools\build.ps1
#            powershell ... -File build_tools\build.ps1 -SkipInstaller

param(
    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "== 1/4: Ikon üretiliyor =="
python build_tools\make_icon.py

Write-Host "== 2/4: Eski çıktılar temizleniyor =="
Remove-Item -Recurse -Force build, dist, installer, portable -ErrorAction SilentlyContinue

Write-Host "== 3/4: PyInstaller (onedir, optimize=2, UPX kapalı) =="
python -m PyInstaller --noconfirm --clean build_tools\QBTranslator.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller başarısız (kod $LASTEXITCODE)" }

$exe = Join-Path $Root "dist\QBTranslator\QBTranslator.exe"
if (-not (Test-Path $exe)) { throw "EXE oluşmadı: $exe" }

# Lisans ve README'yi taşınabilir pakete/ kuruluma dahil et
foreach ($doc in @("README.md", "README.tr.md", "LICENSE", "THIRD_PARTY_NOTICES.md")) {
    $source = Join-Path $Root $doc
    if (Test-Path $source) {
        Copy-Item $source -Destination (Join-Path $Root "dist\QBTranslator") -Force
    }
}

$sizeMB = [math]::Round(((Get-ChildItem -Recurse (Join-Path $Root "dist\QBTranslator") -File | Measure-Object Length -Sum).Sum / 1MB), 1)
Write-Host ("Paket boyutu: {0} MB" -f $sizeMB)

Write-Host "== Portatif tek-dosya sürüm derleniyor =="
python -m PyInstaller --noconfirm --clean build_tools\QBTranslator-portable.spec
if ($LASTEXITCODE -ne 0) { throw "Portatif PyInstaller başarısız (kod $LASTEXITCODE)" }

$portableSource = Join-Path $Root "dist\QBTranslator-Portable.exe"
if (-not (Test-Path $portableSource)) { throw "Portatif EXE oluşmadı: $portableSource" }

$version = (python -c "from appinfo import APP_VERSION; print(APP_VERSION)").Trim()
$portableDir = Join-Path $Root "portable"
New-Item -ItemType Directory -Force -Path $portableDir | Out-Null
$portableTarget = Join-Path $portableDir ("QBTranslator-Portable-{0}.exe" -f $version)
Move-Item -Force $portableSource $portableTarget
Write-Host ("Portatif dosya: {0} ({1:N1} MB)" -f $portableTarget, ((Get-Item $portableTarget).Length / 1MB))

Write-Host "== 4/4: Paketli uygulama selftest =="
$env:QB_DATA_DIR = Join-Path $env:TEMP "qb_packaged_selftest"
$env:QB_DISABLE_AUTOSTART = "1"
Remove-Item -Recurse -Force $env:QB_DATA_DIR -ErrorAction SilentlyContinue
$proc = Start-Process -FilePath $exe -ArgumentList "--selftest" -Wait -PassThru
Write-Host "Selftest çıkış kodu: $($proc.ExitCode)"
$resultFile = Join-Path $env:QB_DATA_DIR "selftest_result.txt"
if (Test-Path $resultFile) {
    Get-Content $resultFile | ForEach-Object { Write-Host "  $_" }
}
if ($proc.ExitCode -ne 0) { throw "Selftest başarısız (kod $($proc.ExitCode))" }

Write-Host "== Portatif selftest =="
$env:QB_DATA_DIR = Join-Path $env:TEMP "qb_portable_selftest"
Remove-Item -Recurse -Force $env:QB_DATA_DIR -ErrorAction SilentlyContinue
$portableProc = Start-Process -FilePath $portableTarget -ArgumentList "--selftest" -Wait -PassThru
Write-Host "Portatif selftest çıkış kodu: $($portableProc.ExitCode)"
$portableResult = Join-Path $env:QB_DATA_DIR "selftest_result.txt"
if (Test-Path $portableResult) {
    Get-Content $portableResult | ForEach-Object { Write-Host "  $_" }
}
if ($portableProc.ExitCode -ne 0) { throw "Portatif selftest başarısız (kod $($portableProc.ExitCode))" }

if (-not $SkipInstaller) {
    Write-Host "== Inno Setup paketleniyor =="
    $isccCandidates = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
    )
    $iscc = $isccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $iscc) { throw "Inno Setup (ISCC.exe) bulunamadı." }
    & $iscc "build_tools\installer.iss"
    if ($LASTEXITCODE -ne 0) { throw "Inno Setup başarısız (kod $LASTEXITCODE)" }

    $setup = Get-ChildItem (Join-Path $Root "installer") -Filter "QBTranslator-Setup-*.exe" |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $setup) { throw "Kurulum dosyası üretilmedi." }
    Write-Host ("Kurulum dosyası: {0} ({1:N1} MB)" -f $setup.FullName, ($setup.Length / 1MB))
}

Write-Host "TAMAM"
