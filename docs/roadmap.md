# Roadmap

The detailed comparison with the archived Tkinter version is in
[feature-parity.md](feature-parity.md).

## 2.0.0 - PySide6 release

- [x] Complete PySide6 rewrite with QtCore, QtGui and QtWidgets
- [x] Main window, translation popup, OCR overlay and dialogs
- [x] Turkish and English interface
- [x] Translation engines, endpoint settings and fallback chain
- [x] History, saved words, search, CSV export and study mode
- [x] Global hotkeys, hotkey capture, tray, autostart and single instance
- [x] Clipboard monitoring, OCR and text-to-speech
- [x] Per-section settings save buttons and persistent window state
- [x] Optimized PyInstaller onedir and single-file portable builds
- [x] Optional Inno Setup installer
- [x] Automated tests, Ruff, CI and packaged selftest
- [x] Security policy, third-party notices and release guide

## Next

- [ ] Code signing for Windows SmartScreen reputation
- [ ] Real multi-monitor and mixed-DPI test pass
- [ ] Accessibility labels and full keyboard navigation
- [ ] Optional automatic update check with explicit user consent
- [ ] More engine integrations, considered case by case

## Quality backlog

- [ ] Deterministic UI screenshot tests
- [ ] Network integration tests behind an opt-in flag
- [ ] Crash reporting and log viewer
- [ ] Migration helper for archived Tkinter data
