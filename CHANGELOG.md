# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [2.0.0] - 2026-11-18

This release replaces the archived Tkinter application with the complete PySide6
rewrite. The Tkinter 1.0.0 release remains available under the `v1.0.0` tag.

### Added

- OCR screen-region overlay with Windows OCR, Tesseract fallback and popup output
- Clipboard monitoring with URL and length filtering
- Autostart synchronization with the Windows HKCU Run key
- Single instance mutex, `--background`, `--minimized`, `--quit` and `--selftest`
- Hotkey capture dialog with validation and rollback
- Engine settings panels for LibreTranslate, Lingva and LLM
- Settings for TTS rate, history limit, popup auto-hide, clipboard restore,
  autostart, OCR, OCR hotkey and tray icon
- Source language and window geometry persistence
- History search, detail dialog, copy, save as word and delete tools
- Saved words search, delete, CSV export and card study mode
- About tab, status chips, reset defaults, hide to tray and quit buttons
- Accent-insensitive target language picker
- Global Escape and right-click close behavior for the translation popup
- Medium weight Segoe UI typography with smoother antialiasing
- Per-section settings save buttons that stay disabled until a change
- Explicit save hint and unsaved changes status in settings
- Optimized PyInstaller onedir and single-file portable builds
- Optional Inno Setup per-user installer
- Security policy, third-party notices and release guide

### Changed

- Active application rewritten with PySide6, QtCore, QtGui and QtWidgets
- Data path is now `%LOCALAPPDATA%\QBTranslator\data`, with `QB_DATA_DIR` override
- The About tab shows a portable `%LOCALAPPDATA%` path instead of an expanded
  user profile path
- Release packaging excludes QML, Quick, WebEngine, Multimedia, Network, SQL,
  PrintSupport, software OpenGL helpers and development tooling

### Fixed

- History word saving called a missing method
- OCR region selection now reports physical screen coordinates and works with
  display scaling
- Translation popup Escape handling now works without keyboard focus
- Settings saves no longer discard unsaved changes in other sections
- Checkbox checked state is visible in the dark theme
- Engine settings panel no longer leaves a large empty area

### Performance

- Optimized onedir package is about 59.6 MB and about 24.3 MB as a ZIP
- Single-file portable executable is about 24.3 MB
- Onedir is recommended for faster startup and lower runtime disk I/O
- Unused Qt modules and plugins are excluded from the build

## [1.0.0] - 2026-11-18

Archived Tkinter release. See the `v1.0.0` tag and GitHub release for the original
application and downloads.

## [0.1.0] - 2026-11-18

### Added

- Initial PySide6 application structure
- Modern dark main window and translation popup
- Turkish and English interface catalogs
- Translation engine layer with Google, MyMemory, LibreTranslate, Lingva and LLM support
- JSON storage with backup and validation
- Global hotkey, system tray and text-to-speech integration
- Translation history and saved words views
- Automated tests for translation, storage, languages, i18n and UI state
