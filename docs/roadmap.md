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

- [ ] Connect OCR screen selection to the Qt UI
- [ ] OCR enable, hotkey and language settings
- [ ] Clipboard monitoring and settings
- [ ] Autostart settings and registry synchronization
- [ ] Single instance behavior and `--background`, `--minimized`, `--quit`
- [ ] Hotkey capture dialog
- [ ] LibreTranslate, Lingva and LLM settings panels
- [ ] TTS rate, history limit, popup auto-hide and clipboard restore settings
- [ ] Source language and window geometry persistence
- [ ] History search, copy, save, delete and detail dialog
- [ ] Saved words search, delete, CSV export and study mode
- [ ] About tab and background behavior panel
- [ ] Reset defaults, hide to tray and quit buttons
- [ ] Accent-insensitive language picker
- [ ] Right-click popup close and robust Escape handling

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
