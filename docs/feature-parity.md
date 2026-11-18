# Feature Parity: Tkinter 1.0.0 vs PySide6 0.1.0

This document compares the archived Tkinter application with the active PySide6
rewrite. Status values:

- `Var`: present and working
- `Kismi`: partially present or behaves differently
- `Yok`: missing in the PySide6 version
- `Farkli`: intentionally changed

## 1. Application shell and lifecycle

| Feature | Tkinter 1.0.0 | PySide6 0.1.0 | Status |
|---|---|---|---|
| Main tabs | Translate, History, Saved Words, Settings, About | Translate, History, Words, Settings | Kismi |
| About tab | Usage, privacy, data directory, engines | Missing | Yok |
| Header chips | Hotkey, clipboard monitor, OCR | Engine, target | Kismi |
| Status bar | Engine, target, hotkey, clipboard, OCR | Engine, target, hotkey | Kismi |
| Window geometry persistence | Saved and restored, off-screen recovery | Missing | Yok |
| Minimum window size | 900 x 640 | 980 x 680 | Farkli |
| Single instance | Named mutex, show existing window | Missing | Yok |
| Background second launch | Silent when already running | Missing | Yok |
| `--background` / `--minimized` | Start in tray | Missing | Yok |
| `--quit` | Quit a background instance | Missing | Yok |
| `--selftest` | Tk, imports and mocked translation | Missing, only smoke flags | Yok |
| DPI awareness | Explicit Win32 DPI setting | Qt high-DPI handling | Farkli |
| System tray | Show, open, quit, balloon | Show, open, quit, balloon | Var |
| X button hides to tray | Yes | Yes | Var |
| Autostart | HKCU Run entry | Missing | Yok |
| Tray icon setting | Config key, no UI | Config key, no UI | Kismi |

## 2. Translate tab and manual workflow

| Feature | Tkinter 1.0.0 | PySide6 0.1.0 | Status |
|---|---|---|---|
| Source language combo | Auto plus languages | Auto plus languages | Var |
| Target language combo | Searchable list | Editable combo with completer | Kismi |
| Source selection persistence | Saved after selection | Not saved to config | Yok |
| Target selection persistence | Saved and synchronized | Saved and synchronized | Var |
| Source/target swap | Yes | Yes | Var |
| Manual input | Yes | Yes | Var |
| Paste button | Yes | Yes | Var |
| Clear button | Yes | Yes | Var |
| Ctrl+Enter shortcut | Yes | Yes | Var |
| Character counter | Yes | Yes | Var |
| Output copy | Yes | Yes | Var |
| Output read aloud | Yes | Yes | Var |
| Save word from output | Yes | Yes | Var |
| Error output state | Yes, does not save errors | Yes | Var |
| Input edit invalidates result | Yes | Yes | Var |
| Result status | Engine, latency, languages | Engine, latency, languages | Var |
| Empty state text | No | Placeholder text | Farkli |
| Recent translations card | No, only full history tab | Yes | Farkli |

## 3. Translation engines and validation

| Feature | Tkinter 1.0.0 | PySide6 0.1.0 | Status |
|---|---|---|---|
| Google Translate | Yes, default | Yes, default | Var |
| MyMemory | Yes | Yes | Var |
| LibreTranslate | Yes | Yes | Var |
| Lingva | Yes | Yes | Var |
| LLM OpenAI-compatible | Yes | Yes | Var |
| Fallback chain | Yes | Yes | Var |
| Translation cache | Yes | Yes | Var |
| MyMemory autodetect | Yes | Yes | Var |
| MyMemory response validation | Yes | Yes | Var |
| Same-language short circuit | Yes | Yes | Var |
| Long text chunking | Yes | Yes | Var |
| LibreTranslate endpoint/API key UI | Yes | Missing | Yok |
| Lingva endpoint UI | Yes | Missing | Yok |
| LLM endpoint, model and API key UI | Yes | Missing | Yok |
| Engine detail panels | Yes, dynamic per engine | Missing | Yok |
| Engine labels in UI | Turkish only | Turkish and English | Farkli |
| Engine error localization | Turkish | Turkish and English | Var |

## 4. Global hotkey and selection capture

| Feature | Tkinter 1.0.0 | PySide6 0.1.0 | Status |
|---|---|---|---|
| Global hotkey listener | Yes | Yes | Var |
| Selected text capture with Ctrl+C | Yes | Yes | Var |
| Modifier release wait | Yes | Yes | Var |
| Clipboard restore | Yes | Core exists, UI toggle missing | Kismi |
| Capture guard | Yes | Yes | Var |
| Hotkey registration result | Reported in chips | Reported in sidebar and status | Kismi |
| Hotkey conflict rollback | Yes | Yes | Var |
| Hotkey capture dialog | Yes | Missing | Yok |
| Parse and validate hotkey | Yes | Yes | Var |
| Pause hotkeys during capture | Yes | Not applicable without dialog | Yok |
| OCR hotkey | Yes | Missing | Yok |
| Hotkey chip | Header plus status | Sidebar plus status | Kismi |

## 5. Translation popup

| Feature | Tkinter 1.0.0 | PySide6 0.1.0 | Status |
|---|---|---|---|
| Frameless popup | Yes | Yes | Var |
| Always on top | Yes | Yes | Var |
| Draggable | Yes | Yes | Var |
| Position near cursor | Yes, primary screen initially | Yes, multi-monitor aware | Var |
| Loading state | Yes | Yes | Var |
| Source text display | Yes | Yes | Var |
| Result text | Yes | Yes | Var |
| Engine and language status | Yes | Yes | Var |
| Error state | Yes | Yes | Var |
| Copy | Yes | Yes | Var |
| Read aloud | Yes | Yes | Var |
| Save word | Yes | Yes | Var |
| Close button | Yes | Yes | Var |
| Escape to close | Usually when focused | Only when focused | Kismi |
| Right-click to close | Yes | Missing | Yok |
| Auto-hide | Yes, configurable | Yes, config default, no UI | Kismi |
| Target language change | Yes | Yes | Var |
| Searchable target language picker | Dedicated picker with accent-insensitive search | Combo with completer, no accent folding | Kismi |
| Swap translation | Yes | Yes | Var |
| Target sync with main and settings | Yes | Yes | Var |

## 6. OCR

| Feature | Tkinter 1.0.0 | PySide6 0.1.0 | Status |
|---|---|---|---|
| OCR enable setting | Yes | Missing | Yok |
| Separate OCR hotkey | Yes | Missing | Yok |
| OCR language setting | Yes | Field exists, no OCR action | Kismi |
| Full-screen region selector | Yes | Missing | Yok |
| Dimmed outside selection | Yes | Missing | Yok |
| Esc and right-click cancel | Yes | Missing | Yok |
| Minimum selection size | 12 px | Missing | Yok |
| DPI-aware screen capture | Yes | Core exists | Kismi |
| Windows OCR | Yes | Core exists | Kismi |
| OCR language fallback | Yes | Core exists | Kismi |
| Installed OCR language fallback | Yes | Core exists | Kismi |
| Image upscale | 2x, 3x for small regions | Core exists | Kismi |
| Dark theme inversion | Yes | Core exists | Kismi |
| Tesseract fallback | Yes, with language | Core exists | Kismi |
| Failure screenshot path | Yes | Core exists | Kismi |
| OCR result in popup | Yes | Missing | Yok |

The OCR core module is present, but no PySide6 overlay or OCR workflow uses it
yet. This is the largest missing feature group.

## 7. Clipboard monitoring

| Feature | Tkinter 1.0.0 | PySide6 0.1.0 | Status |
|---|---|---|---|
| Clipboard watcher | Yes | Core class exists, not started | Yok |
| Enable/disable setting | Yes | Missing | Yok |
| URL filtering | Yes | Missing | Yok |
| Length filtering | Yes | Missing | Yok |
| Suppress own clipboard writes | Yes | Missing in main window | Yok |
| Restore clipboard after capture | Yes | Core setting used, no UI | Kismi |
| Clipboard translation popup | Yes | Missing | Yok |

## 8. History

| Feature | Tkinter 1.0.0 | PySide6 0.1.0 | Status |
|---|---|---|---|
| History storage | Yes | Yes | Var |
| History limit | Configurable in settings | Storage enforces config, no UI | Kismi |
| Search | Yes, Turkish-aware | Missing | Yok |
| Refresh | Yes | Yes automatically | Var |
| Table columns | Date, source, translation, languages, engine | Single wrapped list | Kismi |
| Copy selected translation | Yes | Missing | Yok |
| Save selected as word | Yes | Missing | Yok |
| Delete selected record | Yes | Missing | Yok |
| Clear all | Yes | Yes | Var |
| Detail window | Separate dialog | Loads record into translate tab | Kismi |
| Open history item | Double click detail | Double click loads item | Farkli |
| Empty state | No explicit message | Yes | Var |

## 9. Saved words

| Feature | Tkinter 1.0.0 | PySide6 0.1.0 | Status |
|---|---|---|---|
| Add word | Yes | Yes | Var |
| Duplicate detection | Yes, Turkish-aware | Yes, Turkish-aware | Var |
| Search | Yes, Turkish-aware | Missing | Yok |
| Table columns | Word, translation, languages, date | Single wrapped list | Kismi |
| Delete selected | Yes | Missing | Yok |
| Clear all | Yes | Yes | Var |
| CSV export | UTF-8 BOM, Excel friendly | Missing | Yok |
| Card study mode | Yes, reveal, next, previous, speak | Missing | Yok |
| Keyboard navigation in cards | Space, Left, Right | Missing | Yok |
| Empty state | No explicit message | Yes | Var |

## 10. Settings

| Feature | Tkinter 1.0.0 | PySide6 0.1.0 | Status |
|---|---|---|---|
| Hotkey text field | Yes | Yes | Var |
| Hotkey capture button | Yes | Missing | Yok |
| Autostart toggle | Yes | Missing | Yok |
| Clipboard monitor toggle | Yes | Missing | Yok |
| Restore clipboard toggle | Yes | Missing | Yok |
| OCR enable toggle | Yes | Missing | Yok |
| OCR hotkey field | Yes | Missing | Yok |
| OCR language field | Yes | Yes, but OCR missing | Kismi |
| Default target language | Yes | Yes | Var |
| Primary engine | Yes | Yes | Var |
| Backup engines toggle | Yes | Yes | Var |
| LibreTranslate endpoint and key | Yes | Missing | Yok |
| Lingva endpoint | Yes | Missing | Yok |
| LLM endpoint, model and key | Yes | Missing | Yok |
| Popup auto-hide seconds | Yes | Config used, no UI | Kismi |
| TTS rate | Yes | Config used, no UI | Kismi |
| History limit | Yes | Config used, no UI | Kismi |
| UI language | No | Turkish, English, System | Farkli |
| Save and apply | Yes | Yes | Var |
| Reset to defaults | Yes | Missing | Yok |
| Background behavior banner | Yes | Missing | Yok |
| Hide to tray button | Yes | Missing | Yok |
| Quit application button | Yes | Missing | Yok |
| Settings status text | Yes | Yes, via status bar | Kismi |

## 11. TTS and audio

| Feature | Tkinter 1.0.0 | PySide6 0.1.0 | Status |
|---|---|---|---|
| Windows SAPI speech | Yes | Yes | Var |
| Speak from popup | Yes | Yes | Var |
| Speak from manual output | Yes | Yes | Var |
| Speak from history detail | Yes | Not available | Yok |
| Speak from study cards | Yes | Study mode missing | Yok |
| Stop current speech | Yes | Yes | Var |
| TTS rate setting | Yes | No UI | Kismi |
| Kill speech process on exit | Job Object | Job Object | Var |
| Voice selection | No | No | Ayni |

## 12. Storage and data

| Feature | Tkinter 1.0.0 | PySide6 0.1.0 | Status |
|---|---|---|---|
| JSON config, history, words | Yes | Yes | Var |
| Atomic writes | Yes | Yes | Var |
| `.bak` backups | Yes | Yes | Var |
| Config type validation | Yes | Yes | Var |
| Duplicate record id recovery | Yes | Yes | Var |
| Source-relative data directory | Yes | No | Farkli |
| LocalAppData fallback | Yes | Always LocalAppData | Farkli |
| `QB_DATA_DIR` override | Yes | Yes | Var |
| Window geometry persistence | Yes | Missing | Yok |
| Migration from old data | Not applicable | Missing | Yok |

The data path change is intentional for the packaged application, but existing
Tkinter data is not migrated automatically. The old source data remains in the
archive.

## 13. Tray, background and Windows integration

| Feature | Tkinter 1.0.0 | PySide6 0.1.0 | Status |
|---|---|---|---|
| Tray icon | Yes | Yes | Var |
| Tray open/quit menu | Yes | Yes, localized | Var |
| Tray balloon | Yes | Yes | Var |
| Explorer restart icon restore | Yes | Yes | Var |
| Hide to tray on X | Yes | Yes | Var |
| Explicit hide/quit UI | Yes | Missing | Yok |
| Autostart registry | Yes | Missing | Yok |
| Single instance messaging | Yes | Missing | Yok |
| Window activation by title | Yes | Missing | Yok |

## 14. New behavior in the PySide6 version

These are improvements or intentional changes, not regressions:

- Modern Qt interface with dark theme and high-DPI handling
- Turkish and English interface catalogs
- Interface language setting
- English language labels and search aliases
- Qt signal/slot based worker updates
- Responsive recent translations card on the translate tab
- Automated tests, Ruff, CI configuration and local Git history
- Automated em dash and en dash style check
- More robust hotkey registration and fallback rollback
- Better JSON backup and malformed record recovery
- New placeholder states for empty history and word lists
- No em dash in the active project UI or documentation

## 15. Recommended restoration order

### P0: Core parity

1. OCR selection overlay and OCR workflow
2. Clipboard monitoring and settings
3. Autostart, single instance and CLI flags
4. Hotkey capture dialog
5. Engine settings panels for LibreTranslate, Lingva and LLM
6. Settings fields for TTS rate, history limit, popup auto-hide and clipboard restore
7. Source language persistence and window geometry persistence

### P1: Workflow parity

8. History search, copy, save, delete and detail dialog
9. Saved words search, delete, CSV export and study mode
10. About tab
11. Reset defaults, hide to tray and quit buttons
12. Status chips for clipboard and OCR
13. Right-click popup close and robust Escape handling
14. Accent-insensitive language picker identical to the old picker

### P2: Distribution and polish

15. Background and quit command-line behavior
16. Packaging and installer
17. Data migration from Tkinter
18. Real multi-monitor and mixed-DPI test pass
19. Accessibility and keyboard navigation
