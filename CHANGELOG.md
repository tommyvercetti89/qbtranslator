# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- OCR screen region overlay with worker-thread recognition and popup output
- Clipboard monitoring with filtering and translation popup
- Autostart synchronization with the Windows HKCU Run key
- Single instance mutex, `--background`, `--minimized`, `--quit` and `--selftest`
- Hotkey capture dialog with validation and rollback
- Engine settings panels for LibreTranslate, Lingva and LLM
- Settings for TTS rate, history limit, popup auto-hide, clipboard restore,
  autostart, OCR and OCR hotkey
- Source language and window geometry persistence
- History search, detail dialog, copy, save as word and delete tools
- Saved words search, delete, CSV export and card study mode
- About tab, status chips, reset defaults, hide to tray and quit buttons
- Accent-insensitive target language picker
- Global Escape and right-click close behavior for the translation popup
- Tests for dialogs, settings, history, words, clipboard, OCR, autostart,
  single instance and hotkey parsing

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
