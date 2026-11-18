# Roadmap

The detailed comparison with the archived Tkinter version is in
[feature-parity.md](feature-parity.md).

## 0.1.0 - Foundation

- [x] PySide6 project structure
- [x] Main window and translation popup
- [x] Turkish and English interface
- [x] Translation engines and fallback chain
- [x] History and saved words
- [x] Global hotkey and tray
- [x] Validation, logging and tests

## 0.2.0 - Feature parity

- [x] Connect OCR screen selection to the Qt UI
- [x] OCR enable, hotkey and language settings
- [x] Clipboard monitoring and settings
- [x] Autostart settings and registry synchronization
- [x] Single instance behavior and `--background`, `--minimized`, `--quit`
- [x] Hotkey capture dialog
- [x] LibreTranslate, Lingva and LLM settings panels
- [x] TTS rate, history limit, popup auto-hide and clipboard restore settings
- [x] Source language and window geometry persistence
- [x] History search, copy, save, delete and detail dialog
- [x] Saved words search, delete, CSV export and study mode
- [x] About tab and background behavior panel
- [x] Reset defaults, hide to tray and quit buttons
- [x] Accent-insensitive language picker
- [x] Right-click popup close and robust Escape handling
- [x] `--selftest` and background start smoke coverage

## 0.3.0 - Packaging

- [ ] PyInstaller onedir build
- [ ] Unused Qt module exclusion
- [ ] Inno Setup installer
- [ ] Code signing
- [ ] Portable build

## Quality backlog

- [ ] Real multi-monitor and mixed DPI testing
- [ ] Accessibility labels and keyboard navigation
- [ ] Crash reporting and rotating log viewer
- [ ] Deterministic UI screenshot tests
- [ ] Network integration tests behind an opt-in flag
