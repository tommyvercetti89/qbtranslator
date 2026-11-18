"""
ocr.py - Ekran bölgesi seçimi ve Windows OCR.

Bölge seçimi PySide6 arayüzünde (ui/region_selector.py) yapılır; bu modül
yalnızca yakalama ve OCR işlemlerini sağlar.

OCR: Windows 10/11'in yerleşik Windows.Media.Ocr motoru (PowerShell
üzerinden). Motor yoksa, kuruluysa Tesseract CLI'ye düşer.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from qbtranslator.i18n import t

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

CAPTURE_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public static class DpiAwareness {
    [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
}
"@
[DpiAwareness]::SetProcessDPIAware() | Out-Null
$x = [int]$env:QB_OCR_X
$y = [int]$env:QB_OCR_Y
$w = [int]$env:QB_OCR_W
$h = [int]$env:QB_OCR_H
if ($w -le 0 -or $h -le 0) { throw 'Gecersiz bolge' }

# Negatif koordinatlı ikincil monitörlerde CopyFromScreen sorun çıkarabildiği
# için önce tüm sanal ekranı yakalayıp seçilen bölgeyi kırpıyoruz.
$vs = [System.Windows.Forms.SystemInformation]::VirtualScreen
if ($x -lt $vs.X -or $y -lt $vs.Y -or ($x + $w) -gt ($vs.X + $vs.Width) -or ($y + $h) -gt ($vs.Y + $vs.Height)) {
    throw 'Secim sanal ekranin disinda'
}
$full = New-Object System.Drawing.Bitmap($vs.Width, $vs.Height)
$g = [System.Drawing.Graphics]::FromImage($full)
$g.CopyFromScreen($vs.X, $vs.Y, 0, 0, $full.Size)
$rect = New-Object System.Drawing.Rectangle(($x - $vs.X), ($y - $vs.Y), $w, $h)
$crop = $full.Clone($rect, $full.PixelFormat)
$crop.Save($env:QB_OCR_IMAGE, [System.Drawing.Imaging.ImageFormat]::Png)
$crop.Dispose()
$g.Dispose()
$full.Dispose()
"""

PREPROCESS_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$src = [System.Drawing.Bitmap]::FromFile($env:QB_OCR_IMAGE)
$mode = $env:QB_OCR_MODE
$scale = [int]$env:QB_OCR_SCALE
if ($scale -lt 1) { $scale = 2 }

# Ortalama parlaklık (koyu tema tespiti)
$sum = 0.0
$count = 0
$stepX = [Math]::Max(1, [int]($src.Width / 40))
$stepY = [Math]::Max(1, [int]($src.Height / 40))
for ($py = 0; $py -lt $src.Height; $py += $stepY) {
    for ($px = 0; $px -lt $src.Width; $px += $stepX) {
        $c = $src.GetPixel($px, $py)
        $sum += (0.299 * $c.R + 0.587 * $c.G + 0.114 * $c.B)
        $count++
    }
}
$avg = if ($count -gt 0) { $sum / $count } else { 255 }
if ($mode -eq 'invert') { $invert = $true }
elseif ($mode -eq 'normal') { $invert = $false }
else { $invert = ($avg -lt 110) }

$destW = [Math]::Min(6000, $src.Width * $scale)
$destH = [Math]::Min(6000, $src.Height * $scale)
$dst = New-Object System.Drawing.Bitmap($destW, $destH)
$g = [System.Drawing.Graphics]::FromImage($dst)
$g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
$g.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
$g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
$g.Clear([System.Drawing.Color]::White)
$rect = New-Object System.Drawing.Rectangle(0, 0, $destW, $destH)

if ($invert) {
    $cm = New-Object System.Drawing.Imaging.ColorMatrix
    $cm.Matrix00 = -1
    $cm.Matrix11 = -1
    $cm.Matrix22 = -1
    $cm.Matrix33 = 1
    $cm.Matrix40 = 1
    $cm.Matrix41 = 1
    $cm.Matrix42 = 1
    $ia = New-Object System.Drawing.Imaging.ImageAttributes
    $ia.SetColorMatrix($cm)
    $g.DrawImage($src, $rect, 0, 0, $src.Width, $src.Height, [System.Drawing.GraphicsUnit]::Pixel, $ia)
    $ia.Dispose()
} else {
    $g.DrawImage($src, $rect, 0, 0, $src.Width, $src.Height, [System.Drawing.GraphicsUnit]::Pixel)
}

$dst.Save($env:QB_OCR_IMAGE_OUT, [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose()
$dst.Dispose()
$src.Dispose()
"""

OCR_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType=WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Foundation, ContentType=WindowsRuntime]
$null = [Windows.Storage.StorageFile, Windows.Foundation, ContentType=WindowsRuntime]
$null = [Windows.Storage.FileAccessMode, Windows.Foundation, ContentType=WindowsRuntime]
$null = [Windows.Globalization.Language, Windows.Foundation, ContentType=WindowsRuntime]

$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
})[0]

function Await($WinRtTask, $ResultType) {
    $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
    $netTask = $asTask.Invoke($null, @($WinRtTask))
    $netTask.Wait(-1) | Out-Null
    $netTask.Result
}

$file = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($env:QB_OCR_IMAGE)) ([Windows.Storage.StorageFile])
$stream = Await ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
$decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
$bitmap = Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])

$engine = $null
$lang = $env:QB_OCR_LANG
if ($lang -and $lang -ne 'auto') {
    $language = [Windows.Globalization.Language]::new($lang)
    $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($language)
}
if (-not $engine) {
    $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
}
if (-not $engine) {
    $language = [Windows.Globalization.Language]::new('en-US')
    $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($language)
}
if (-not $engine) { throw 'Windows OCR motoru bulunamadi (dil paketi eksik olabilir)' }

function Get-OcrText($ocrEngine) {
    $r = Await ($ocrEngine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
    $outLines = @()
    foreach ($line in $r.Lines) { $outLines += $line.Text }
    return ($outLines -join "`n")
}

$text = Get-OcrText $engine

# Birincil motor boş dönerse kurulu diğer OCR dillerini dene
if (-not $text -or $text.Trim().Length -eq 0) {
    $tried = @()
    try {
        foreach ($available in [Windows.Media.Ocr.OcrEngine]::AvailableRecognizerLanguages) {
            $tag = $available.LanguageTag
            if ($tried -contains $tag) { continue }
            $tried += $tag
            try {
                $fallbackEngine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($available)
                if ($fallbackEngine) {
                    $candidate = Get-OcrText $fallbackEngine
                    if ($candidate -and $candidate.Trim().Length -gt 0) {
                        $text = $candidate
                        break
                    }
                }
            } catch { }
        }
    } catch { }
}

[IO.File]::WriteAllText($env:QB_OCR_OUT, $text, (New-Object System.Text.UTF8Encoding($false)))
"""


# ----------------------------------------------------------------------
# OCR
# ----------------------------------------------------------------------
def _run_powershell(script: str, env: dict, timeout: int) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            script,
        ],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        creationflags=CREATE_NO_WINDOW,
    )


def capture_region_to_png(x: int, y: int, width: int, height: int, path: str) -> str:
    """Ekranın belirtilen bölgesini PNG olarak kaydeder. Hata varsa mesaj döndürür."""
    env = os.environ.copy()
    env.update(
        {
            "QB_OCR_X": str(int(x)),
            "QB_OCR_Y": str(int(y)),
            "QB_OCR_W": str(int(width)),
            "QB_OCR_H": str(int(height)),
            "QB_OCR_IMAGE": path,
        }
    )
    try:
        result = _run_powershell(CAPTURE_SCRIPT, env, timeout=30)
    except Exception as error:
        return str(error)
    if result.returncode != 0 or not os.path.exists(path):
        return (result.stderr or result.stdout or t("ocr.error.capture")).strip()
    return ""


def ocr_image_file(path: str, language: str = "auto") -> tuple[str, str]:
    """Bir görüntü dosyasındaki metni Windows OCR ile tanır: (metin, hata)."""
    out_path = path + ".txt"
    env = os.environ.copy()
    env.update(
        {
            "QB_OCR_IMAGE": path,
            "QB_OCR_OUT": out_path,
            "QB_OCR_LANG": language or "auto",
        }
    )
    try:
        result = _run_powershell(OCR_SCRIPT, env, timeout=60)
    except Exception as error:
        return "", str(error)

    if os.path.exists(out_path):
        try:
            with open(out_path, "r", encoding="utf-8", errors="replace") as handle:
                text = handle.read()
            return text.strip(), ""
        except OSError as error:
            return "", str(error)
        finally:
            try:
                os.remove(out_path)
            except OSError:
                pass

    error_message = (result.stderr or result.stdout or "").strip()
    if not error_message:
        error_message = t("ocr.error.engine_missing")
    return "", error_message.splitlines()[-1] if error_message else t("ocr.error.generic")


def _tesseract_fallback(path: str, language: str = "auto") -> tuple[str, str]:
    executable = shutil.which("tesseract")
    if not executable:
        return "", t("ocr.error.tesseract_missing")

    tesseract_lang = _tesseract_language(language)

    def run(args: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            creationflags=CREATE_NO_WINDOW,
        )

    attempts: list[list[str]] = []
    if tesseract_lang:
        attempts.append([executable, "-l", tesseract_lang, path, "stdout"])
    attempts.append([executable, path, "stdout"])

    last_error = ""
    for args in attempts:
        try:
            result = run(args)
        except Exception as error:
            return "", str(error)
        text = (result.stdout or "").strip()
        if text:
            return text, ""
        last_error = (result.stderr or "").strip()

    return "", (last_error or t("ocr.error.tesseract_empty"))


LAST_CAPTURE_PATH = Path(tempfile.gettempdir()) / "QBTranslator_ocr_last.png"

# Tesseract dil eşlemesi (Windows OCR kodları -> Tesseract traineddata)
_TESSERACT_LANGS = {
    "tr": "tur",
    "en": "eng",
    "de": "deu",
    "fr": "fra",
    "es": "spa",
    "it": "ita",
    "ru": "rus",
    "ar": "ara",
    "fa": "fas",
    "ur": "urd",
    "el": "ell",
    "bg": "bul",
    "ro": "ron",
    "uk": "ukr",
    "az": "aze",
    "kk": "kaz",
    "uz": "uzb",
    "hi": "hin",
    "bn": "ben",
    "zh-cn": "chi_sim",
    "zh-tw": "chi_tra",
    "ja": "jpn",
    "ko": "kor",
    "vi": "vie",
    "th": "tha",
    "id": "ind",
    "ms": "msa",
    "nl": "nld",
    "sv": "swe",
    "no": "nor",
    "da": "dan",
    "fi": "fin",
    "pl": "pol",
    "cs": "ces",
    "sk": "slk",
    "hu": "hun",
    "hr": "hrv",
    "sr": "srp",
    "sl": "slv",
    "lt": "lit",
    "lv": "lav",
    "et": "est",
    "he": "heb",
    "pt": "por",
    "pt-br": "por",
    "gl": "glg",
    "ca": "cat",
    "eu": "eus",
    "ga": "gle",
    "is": "isl",
    "sq": "sqi",
    "mk": "mkd",
    "bs": "bos",
    "ka": "kat",
    "hy": "hye",
    "sw": "swa",
    "af": "afr",
    "tl": "tgl",
    "ne": "nep",
    "si": "sin",
    "km": "khm",
    "lo": "lao",
    "my": "mya",
    "mn": "mon",
    "tg": "tgk",
    "ky": "kir",
    "be": "bel",
    "mt": "mlt",
    "lb": "ltz",
    "cy": "cym",
    "gd": "gla",
    "eo": "epo",
    "la": "lat",
    "haw": "haw",
    "mi": "mri",
    "sm": "smo",
    "yi": "yid",
}


def _tesseract_language(language: str) -> str:
    code = (language or "").strip().lower()
    if not code or code == "auto":
        return ""
    return _TESSERACT_LANGS.get(code, _TESSERACT_LANGS.get(code.split("-")[0], ""))


def last_capture_path() -> str:
    """Tanı için son başarısız OCR ekran görüntüsünün yolunu döndürür."""
    return str(LAST_CAPTURE_PATH) if LAST_CAPTURE_PATH.exists() else ""


def clear_last_capture() -> None:
    """Önceki oturumdan kalan OCR ekran görüntüsünü siler (gizlilik)."""
    try:
        LAST_CAPTURE_PATH.unlink()
    except OSError:
        pass


def cleanup_temp_captures() -> None:
    """Çökmelerden kalan geçici OCR görüntülerini temizler (gizlilik)."""
    try:
        temp_root = Path(tempfile.gettempdir())
        for path in temp_root.glob("qb_ocr_*"):
            try:
                if path.is_dir():
                    shutil.rmtree(path, ignore_errors=True)
                else:
                    path.unlink()
            except OSError:
                pass
    except Exception:
        pass


def preprocess_image(
    source: str, target: str, mode: str = "auto", scale: int = 2
) -> str:
    """OCR öncesi görüntüyü büyütür / renkleri çevirir. Hata mesajı döndürür."""
    env = os.environ.copy()
    env.update(
        {
            "QB_OCR_IMAGE": source,
            "QB_OCR_IMAGE_OUT": target,
            "QB_OCR_MODE": mode,
            "QB_OCR_SCALE": str(max(1, int(scale))),
        }
    )
    try:
        result = _run_powershell(PREPROCESS_SCRIPT, env, timeout=60)
    except Exception as error:
        return str(error)
    if result.returncode != 0 or not os.path.exists(target):
        return (result.stderr or result.stdout or t("ocr.error.preprocess")).strip()
    return ""


def recognize_region(
    x: int, y: int, width: int, height: int, language: str = "auto"
) -> tuple[str, str]:
    """
    Ekran bölgesini yakalar ve OCR uygular.
    Dönüş: (metin, hata_mesajı). Başarılıysa hata boştur.
    """
    if width <= 0 or height <= 0:
        return "", t("ocr.error.invalid_region")

    # Seçim katmanı kapandıktan sonra ekranın yenilenmesini bekle
    time.sleep(0.3)

    clear_last_capture()

    temp_dir = Path(tempfile.mkdtemp(prefix="qb_ocr_"))
    image_path = str(temp_dir / "capture.png")
    first_error = ""
    try:
        error = capture_region_to_png(x, y, width, height, image_path)
        if error:
            return "", t("ocr.error.capture_detail", error=error)

        text, error = ocr_image_file(image_path, language)
        if text:
            return text, ""
        first_error = error

        # İlk deneme boşsa görüntüyü büyüt ve renk modlarını dene
        scale = 3 if width < 450 or height < 140 else 2
        processed_paths: list[str] = []
        for index, mode in enumerate(("auto", "invert", "normal")):
            processed = str(temp_dir / f"processed_{index}.png")
            if preprocess_image(image_path, processed, mode, scale):
                continue
            processed_paths.append(processed)
            candidate, _ = ocr_image_file(processed, language)
            if candidate:
                return candidate, ""

        # Windows OCR hâlâ boşsa Tesseract yedeğini dene
        for candidate_path in [image_path] + processed_paths[:2]:
            fallback_text, _fallback_error = _tesseract_fallback(candidate_path, language)
            if fallback_text:
                return fallback_text, ""

        # Yalnızca başarısız OCR'da teşhis görüntüsünü kalıcı bırak.
        try:
            shutil.copyfile(image_path, LAST_CAPTURE_PATH)
        except OSError:
            pass
        return "", first_error or t("ocr.error.no_text")
    finally:
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass
