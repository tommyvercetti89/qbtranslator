# QBTranslator

[![English: current](https://img.shields.io/badge/English-current-2ea44f?style=for-the-badge)](README.md)
[![Türkçe](https://img.shields.io/badge/T%C3%BCrk%C3%A7e-README-d73a49?style=for-the-badge)](README.tr.md)

**English** · [Türkçe](README.tr.md)

A Windows desktop translation app. Translate text selected in any application with a
global hotkey and display the result next to the cursor; you can also translate a screen
region with OCR.

Inspired by the [MouseTooltipTranslator](https://github.com/ttop32/MouseTooltipTranslator)
browser extension.

> The application interface is currently Turkish. An English interface is planned.

---

## Features

- **Global hotkey** (default `Ctrl+Alt+T`): copies the selected text, translates it, and
  shows the result next to the cursor
- **OCR (screen translation)**: use a separate hotkey (default `Ctrl+Alt+O`) to select a
  screen region; the rest of the screen dims, the region is read, and the result appears
  in the same popup
- **Searchable language picker**: the "Target language" button in the popup searches both
  Turkish and English language names and tolerates missing Turkish diacritics
- **⇄ Swap**: turns the translated output into the new source and translates back to the
  previous source language for quick round-trip checks
- **Hotkey capture**: assign any combination with **Capture…** in Settings (manual entry is
  also supported)
- **Start with Windows**: optionally launches at sign-in **in the system tray** and keeps
  the hotkeys listening
- **System tray + background**: the X button does **not** quit the app; it minimizes to the
  tray. Quit completely from the tray menu or the large red button in Settings
- **Single instance**: launching the app again brings the existing window to the front;
  `--quit` cleanly closes the background instance
- **iOS-style switches**: Settings options use gradient on/off switches
- **Clipboard monitoring** (optional): automatically translates copied text
- **History + saved words**: search, card mode, and CSV export
- **Text-to-speech**: Windows SAPI; speech stops when the app closes
- **Multiple engines**: Google Translate (default), MyMemory, LibreTranslate, Lingva, and
  LLMs (Ollama / LM Studio / OpenAI-compatible)
- **Standard library only**: no `pip install` is required at runtime

---

## Requirements

- **Windows 10 / 11**
- **Python 3.9+** (only when running from source; includes `tkinter`)
- Internet connection (for translation)
- **For OCR**: a Windows OCR language/language pack (Settings → Time & Language → Language).
  If the Windows OCR engine is unavailable, **Tesseract CLI** is used as a fallback when
  installed.
- PowerShell for TTS (included with Windows)

---

## Running

| Method | Description |
|---|---|
| `baslat.bat` | Starts without a console window (`pythonw`) |
| `baslat_konsol.bat` | Starts with a console for troubleshooting |
| `python main.py` | Runs from a terminal |
| `python main.py --background` | Starts directly in the system tray/background |
| `python main.py --quit` | Cleanly closes a background QBTranslator instance |

The `data/` directory is created on first launch.

---

## Usage

### 1. Translating selected text

1. Select text in any application
2. Press **Ctrl+Alt+T**
3. The translation appears in a popup next to the cursor

Popup buttons: **Copy • Read • Save word • Close**. The popup is draggable and closes with
`Esc`, right-click, X, or the automatic timeout.

### Background / system tray

- **The X button does not quit the app.** The window minimizes to the system tray and the
  hotkeys keep listening.
- **Double-click** the **QBTranslator** tray icon to open the main window.
- **Right-click → Quit** fully exits the app.
- You can also use the large **QUIT APPLICATION** button in Settings.
- With autostart enabled, the app starts directly **in the system tray**; the main window
  is not shown.
- From the command line: `QBTranslator.exe --quit`.

### 2. OCR screen translation

1. Settings → enable **OCR mode**
2. Press **Ctrl+Alt+O** (or your configured hotkey)
3. Drag to select the area to translate — the outside dims and the selection stays clear
4. The region is read with Windows OCR and shown in the **same translation popup**

Press `Esc` or right-click to cancel the selection. No popup is shown during OCR, so the
captured screenshot is not obscured.

### 3. Changing language / swapping in the popup

- **Target language** button → searchable language picker (Turkish/English names, `ing`,
  `english`, `turkce`, etc.)
- **⇄** → the translated output becomes the new source and the target switches to the
  previous source language; press again to reverse
- The selection is synchronized with the main window, Settings, and future translations

### 4. Clipboard monitoring

Settings → **Monitor clipboard**. Copied text (except URLs) is translated automatically.
Disabled by default.

---

## Settings

### Hotkeys

- The **global hotkey** (selected text) and **OCR hotkey** are configured separately
- Type manually: `ctrl+alt+t`, `ctrl+shift+f2`, `alt+space`
- or click **Capture…**, press the combination, and click **Save**
- At least one modifier (Ctrl/Alt/Shift/Win) plus a letter/digit/F1–F12/Space/Tab/Enter/arrow
  key
- Global hotkeys are temporarily disabled while capturing
- Type combinations containing the Win key manually (Tk may not capture the Windows key)

### Autostart / background

- **Start with Windows** is enabled by default
- When settings are saved, a `QBTranslator` entry is written under
  `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`
- At sign-in the app starts in the **system tray** and continues listening for hotkeys
- It keeps running until you quit from the tray/Settings or Task Manager
- Launching it a second time brings the existing window to the front

### Appearance / audio

- Popup auto-hide delay (0 = never)
- TTS rate (-10…10) and history limit
- Target language, primary engine, and fallback engines

---

## OCR Details

- Screenshots are captured with PowerShell + `System.Drawing` with **DPI awareness**, and
  OCR is performed with **Windows.Media.Ocr**
- No popup is shown during OCR, so the loading window cannot cover the selected region
- OCR language: selected language → user profile languages → `en-US`; if the first engine
  returns nothing, other installed OCR languages are tried
- If the first OCR attempt is empty, the image is automatically:
  - upscaled 2× (3× for small regions),
  - color-inverted when a dark theme is detected,
  - retried with those variants
- If Windows OCR still fails and `tesseract` is on PATH, it is used as a fallback
- On OCR failure, the last screenshot is saved as `%TEMP%\QBTranslator_ocr_last.png` and its
  path is shown in the error popup; it is deleted after a successful OCR or when the app
  closes
- The selection overlay covers all monitors; the outside is dimmed to 35% and the selection
  area is “punched out” with the Windows region API
- Selections smaller than 12 px are treated as cancelled

---

## Data Storage

| Mode | Data directory |
|---|---|
| Running from source | `translatordesktop/data/` |
| PyInstaller / installed build | **`data/` next to the executable** |
| Executable directory is not writable (e.g. Program Files) | `%LOCALAPPDATA%\QBTranslator\data\` |
| Development/testing | Custom directory via the `QB_DATA_DIR` environment variable |

Files:

- `config.json` — settings (hotkeys, language, engine, LLM details)
- `history.json` — translation history
- `words.json` — saved words

> When installing with Inno Setup, a per-user installation (LocalAppData) or writable
> directory permissions are recommended. The app automatically falls back to LocalAppData
> when the executable directory is not writable.

---

## Translation Engines

| Engine | Notes |
|---|---|
| **Google Translate** | Default; free endpoint, no API key required |
| **MyMemory** | ~500 characters per request |
| **LibreTranslate** | Endpoint + optional API key |
| **Lingva** | Enter your own/working instance |
| **LLM** | OpenAI-compatible: Ollama `http://localhost:11434/v1`, LM Studio `http://localhost:1234/v1`, OpenAI, etc. |

Optional fallback chain: MyMemory → Lingva → LibreTranslate → Google.

---

## Privacy

- Translated text is sent only to the selected translation engine
- OCR screenshots are used only for local OCR; images are not uploaded anywhere
- History and saved words are stored only in the local `data/` directory
- No analytics or telemetry
- Clipboard monitoring is disabled by default
- LLM API keys are stored as plain text in `config.json`; do not share this file

---

## Troubleshooting

| Problem | Solution |
|---|---|
| **Hotkey could not be registered** | Another app may be using it; choose a different combination. Hotkeys are temporarily disabled during capture. |
| **Selection cannot be captured** | Some apps block Ctrl+C; use clipboard monitoring or the Translation tab. If the target app runs as administrator, run QBTranslator as administrator too. |
| **OCR cannot recognize text** | Select a larger/clearer area and install the Windows language/OCR pack. The app automatically tries upscaling, color inversion, and other OCR languages. Inspect the last screenshot path shown in the error popup (`%TEMP%\QBTranslator_ocr_last.png`). |
| **OCR hotkey does not work** | OCR mode may be off, or the hotkey conflicts with another app. Check Settings. |
| **Google 429** | Temporary under heavy use; enable fallback engines. |
| **Lingva 403/500** | Enter your own server. |
| **No sound** | Check Windows speech voices; corporate PowerShell restrictions may apply. |
| **Autostart does not work** | Enable and save it in Settings; check the `HKCU\...\Run\QBTranslator` registry entry. |
| **App does not start** | Run `baslat_konsol.bat` to see the error; a single-instance lock may already be running. |

---

## Project Structure

```
translatordesktop/
├── main.py            # entry: single instance, --background, DPI
├── appinfo.py         # QBTranslator name/version
├── mainwindow.py      # main window, tabs, OCR/hotkey/automation flows
├── popup.py           # translation popup (target language + ⇄)
├── langpicker.py      # searchable language picker
├── hotkeydialog.py    # keyboard hotkey capture
├── ocr.py             # screen region selection + Windows OCR
├── translator.py      # translation engines
├── win32util.py       # hotkey, clipboard, region/window APIs
├── autostart.py       # Windows startup registration
├── storage.py         # local JSON storage (install-dir support)
├── tts.py             # Windows SAPI
├── tray.py            # system tray and single-instance messaging
├── toggle.py          # gradient on/off switches
├── langs.py           # languages + search normalization
├── build_tools/       # PyInstaller / Inno Setup build artifacts
├── baslat.bat / baslat_konsol.bat
└── data/              # created at runtime
```

---

## Build and Packaging

Requirements (development machine only):

- Python 3.9+
- PyInstaller 6.x (`python -m pip install pyinstaller`)
- Inno Setup 6 (`ISCC.exe`)

Build + package with one command:

```bat
powershell -ExecutionPolicy Bypass -File build_tools\build.ps1
```

Build only the executable folder:

```bat
powershell -ExecutionPolicy Bypass -File build_tools\build.ps1 -SkipInstaller
```

Outputs:

| Output | Path |
|---|---|
| Portable onedir build | `dist\QBTranslator\QBTranslator.exe` |
| Single-file portable build | `portable\QBTranslator-Portable-1.0.0.exe` |
| Installer | `installer\QBTranslator-Setup-1.0.0.exe` |

### Size / performance choices

- **onedir** (not onefile): faster startup, lower RAM, no extraction to a temp directory
- `optimize=2`: smaller bytecode (drops docstrings/asserts)
- Unused modules excluded (test, pip, sqlite3, numpy, PIL, asyncio, multiprocessing,
  lzma/bz2, etc.)
- **UPX disabled**: avoids antivirus false positives and startup CPU overhead
- Measured on this build machine: package **27.3 MB**, installer **10.02 MB**, portable
  **11.56 MB**, startup **~0.3 s**, hidden working set **~39.5 MB**, private memory
  **~22.1 MB**

### Installation behavior

- Per-user install: `%LOCALAPPDATA%\Programs\QBTranslator` (no admin required, writable
  data directory)
- Data is stored under `data\` in the install directory and is **not removed** on uninstall
  (saved words/history are preserved)
- On first launch, the autostart registry entry is updated to point to the installed exe
- `--selftest` can be used to verify a package (Tk, imports, translation)

---

## GitHub and Releases

- **Repository:** https://github.com/tommyvercetti89/qbtranslator
- **Releases:** https://github.com/tommyvercetti89/qbtranslator/releases
- `.gitignore`: `data/`, `dist/`, `installer/`, `portable/`, `build/`, and caches are
  excluded; **user history/settings are never committed.**
- `.github/workflows/build-release.yml`: builds on a clean Windows runner with a `v*` tag
  and creates/updates the GitHub Release.
- `RELEASING.md`: versioning, testing, **code signing**, and release steps.
- `requirements-build.txt`: build-only dependency (`pyinstaller`).
- No pip dependency at runtime.

> Building releases on GitHub Actions instead of a local machine is recommended so build
> paths cannot contain a username or other machine-specific details.

## License

- Project code: **MIT** — see `LICENSE`
- Icons: MouseTooltipTranslator (MIT) — see `THIRD_PARTY_NOTICES.md`
- Python / Tcl-Tk / OpenSSL / PyInstaller / Inno Setup notices are in the same file.

---

[English](README.md) · [Türkçe](README.tr.md)
