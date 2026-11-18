# QBTranslator

Modern Windows desktop translator built with Python and PySide6.

## Status

Development version `0.1.0`. This is the PySide6 rewrite of the original Tkinter
application. The original application, the browser extension and the UI prototypes
are preserved in the sibling `HEPSİ` folder and `HEPSİ.zip` archive.

## Features

- Modern dark desktop interface
- Global shortcut to translate selected text
- Frameless translation popup near the cursor
- Global Escape and right-click close behavior for the popup
- Turkish and English interface
- Translation engines: Google Translate, MyMemory, LibreTranslate, Lingva and
  OpenAI-compatible LLM endpoints
- Engine-specific endpoint, model and API key settings
- OCR screen region selection with Windows OCR and Tesseract fallback
- Clipboard monitoring with URL and length filtering
- Hotkey capture dialog and separate OCR shortcut
- Translation history with search, detail, copy, save and delete tools
- Saved words with search, CSV export, deletion and card study mode
- Autostart, single instance, background start and quit command line flags
- Window geometry and source language persistence
- System tray support
- Local JSON storage under `%LOCALAPPDATA%\QBTranslator\data`

## Requirements

- Windows 10 or Windows 11
- Python 3.11 or newer
- PySide6 6.10 or newer
- OCR needs a Windows OCR language pack. Tesseract is an optional fallback.

## Development

```powershell
cd C:\Users\TOSHIBA\Desktop\translator\QBTranslator
python -m pip install -e ".[dev]"
python -m qbtranslator
```

From a source checkout without installing the package:

```powershell
python run.py
```

Command line options:

```text
--background, --minimized   Start hidden in the system tray
--quit                      Quit a running background instance
--selftest                  Run Qt, import and mocked translation checks
```

For a throwaway development data directory:

```powershell
$env:QB_DATA_DIR = "$env:TEMP\qbtranslator-dev"
python -m qbtranslator
```

## Tests

```powershell
python -m pytest
```

## Quality rules

- No em dash characters in UI text, translations or documentation.
- All user-facing text must come from the locale catalogs.
- Network work must never block the Qt main thread.
- Settings must be validated before they are written to disk.

## Feature parity

The archived Tkinter version and the current PySide6 version are compared in
[docs/feature-parity.md](docs/feature-parity.md). It lists every known feature,
its current status and the recommended restoration order.

## Packaging

Packaging is intentionally not configured yet. It will be added after the
application behavior and UI are stable. The target is a small PySide6 bundle
using QtWidgets only, with unused Qt modules excluded.

## License

MIT. See `LICENSE`.
