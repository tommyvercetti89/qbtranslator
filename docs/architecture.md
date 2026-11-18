# Architecture

## Layers

```text
application.py
    Creates QApplication, single instance guard, CLI flags and the main window.

ui/
    main_window.py    Main window, navigation, translation workflow, tray/hotkey wiring.
    popup.py          Frameless translation popup near the cursor.
    hotkey_dialog.py  Shortcut capture dialog.
    language_picker.py Searchable, accent-insensitive target language picker.
    region_selector.py Full-screen OCR region overlay.
    detail_dialog.py  History detail dialog.
    study_dialog.py   Saved word card mode.
    theme.py          Colors and Qt stylesheet.

core/
    translator.py    Translation engines, fallback chain and response validation.
    storage.py       Validated JSON persistence with backups.
    langs.py         Language catalog, labels and search normalization.
    paths.py         Application data and asset paths.
    win32util.py     Global hotkeys, clipboard, monitor and window APIs.
    single_instance.py Named mutex based single instance guard.
    autostart.py     HKCU Run entry synchronization.
    tray.py          Native Win32 tray icon.
    tts.py           Windows SAPI speech through PowerShell.
    ocr.py           Screen capture, Windows OCR and Tesseract fallback.

i18n.py
    Small dependency-free catalog loader and translation helper.
```

## Threading

- Qt runs the UI on the main thread.
- Translation work runs in `QThreadPool` through `TranslateTask`.
- Selection capture runs in `QThreadPool` through `CaptureTask`.
- OCR capture and recognition run in `QThreadPool` through `OCRTask`.
- Clipboard monitoring runs in a daemon thread and emits a Qt signal.
- TTS runs in a daemon thread and uses a Windows Job Object to clean up child
  processes when the application exits.
- Worker code never touches Qt widgets directly. Results return through Qt signals.

## Translation flow

1. The global hotkey listener runs in its own Win32 message thread.
2. The listener emits a Qt signal to the main thread.
3. A capture task sends Ctrl+C to the foreground window and reads the clipboard.
4. A translation task calls `core.translator.translate()` with a snapshot of the
   current settings.
5. The result returns to the main thread, is added to history and is rendered in
   the popup.

Text entered in the main window follows the same translation task path but writes
to the main output panel instead of the popup.

## OCR flow

1. The OCR hotkey triggers the full-screen Qt region selector.
2. The overlay reports a physical screen rectangle, independent of Qt scaling.
3. An `OCRTask` captures and recognizes the region in `QThreadPool`.
4. The recognized text is translated through the normal popup path.

## Clipboard flow

1. `ClipboardWatcher` polls the Windows clipboard sequence number.
2. Short text, URLs and the application's own writes are filtered.
3. Accepted text is passed to the Qt main thread through a signal and translated
   in the popup.

## Data

Settings, history and saved words are stored as JSON under
`%LOCALAPPDATA%\QBTranslator\data`. Writes use a temporary file and atomic replace.
The previous file is kept as a `.bak` file. Invalid settings fall back to defaults
instead of breaking startup.

## i18n

`core.langs` provides language names and labels for both Turkish and English.
UI strings live in `locales/tr.json` and `locales/en.json`. The interface language
is resolved from the `ui_language` setting or the Windows UI language. A language
change is applied on the next application start.
