# Feature Parity: Tkinter 1.0.0 vs PySide6 2.0.0

This document compares the archived Tkinter application with the active PySide6
rewrite. Status values:

- `Var`: present and working
- `Kismi`: partially present or behaves differently
- `Yok`: missing in the PySide6 version
- `Farkli`: intentionally changed

## 1. Application shell and lifecycle

| Feature | Tkinter 1.0.0 | PySide6 2.0.0 | Status |
|---|---|---|---|
| Main tabs | Translate, History, Saved Words, Settings, About | Translate, History, Words, Settings, About | Var |
| About tab | Usage, privacy, data directory, engines | Usage, privacy, data directory, engines | Var |
| Header chips | Hotkey, clipboard monitor, OCR | Engine and target in header; hotkey, clipboard and OCR chips in sidebar | Var |
| Status bar | Engine, target, hotkey, clipboard, OCR | Engine, target, hotkey, clipboard and OCR status | Var |
| Window geometry persistence | Saved and restored, off-screen recovery | Saved and restored, off-screen recovery | Var |
| Minimum window size | 900 x 640 | 980 x 680 | Farkli |
| Single instance | Named mutex, show existing window | Named mutex, show existing window | Var |
| Background second launch | Silent when already running | Silent when already running | Var |
| `--background` / `--minimized` | Start in tray | Start in tray | Var |
| `--quit` | Quit a background instance | Quit a background instance | Var |
| `--selftest` | Tk, imports and mocked translation | Qt, imports and mocked translation | Var |
| DPI awareness | Explicit Win32 DPI setting | Qt high-DPI handling | Farkli |
| System tray | Show, open, quit, balloon | Show, open, quit, balloon | Var |
| X button hides to tray | Yes | Yes | Var |
| Autostart | HKCU Run entry | HKCU Run entry, UI toggle | Var |
| Tray icon setting | Config key, no UI | Settings toggle | Var |

## 2. Translate tab and manual workflow

| Feature | Tkinter 1.0.0 | PySide6 2.0.0 | Status |
|---|---|---|---|
| Source language combo | Auto plus languages | Auto plus languages | Var |
| Target language combo | Searchable list | Editable combo with completer and accent-insensitive picker | Var |
| Source selection persistence | Saved after selection | Saved after selection | Var |
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

| Feature | Tkinter 1.0.0 | PySide6 2.0.0 | Status |
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
| LibreTranslate endpoint/API key UI | Yes | Endpoint and optional API key fields | Var |
| Lingva endpoint UI | Yes | Endpoint field | Var |
| LLM endpoint, model and API key UI | Yes | Endpoint, model and optional API key fields | Var |
| Engine detail panels | Yes, dynamic per engine | Dynamic panel for each engine | Var |
| Engine labels in UI | Turkish only | Turkish and English | Farkli |
| Engine error localization | Turkish | Turkish and English | Var |

## 4. Global hotkey and selection capture

| Feature | Tkinter 1.0.0 | PySide6 2.0.0 | Status |
|---|---|---|---|
| Global hotkey listener | Yes | Yes | Var |
| Selected text capture with Ctrl+C | Yes | Yes | Var |
| Modifier release wait | Yes | Yes | Var |
| Clipboard restore | Yes | Core plus UI toggle | Var |
| Capture guard | Yes | Yes | Var |
| Hotkey registration result | Reported in chips | Reported in sidebar and status | Var |
| Hotkey conflict rollback | Yes | Yes | Var |
| Hotkey capture dialog | Yes | Dedicated capture dialog | Var |
| Parse and validate hotkey | Yes | Yes | Var |
| Pause hotkeys during capture | Yes | Yes | Var |
| OCR hotkey | Yes | Yes, separate global shortcut | Var |
| Hotkey chip | Header plus status | Sidebar plus status | Var |

## 5. Translation popup

| Feature | Tkinter 1.0.0 | PySide6 2.0.0 | Status |
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
| Escape to close | Usually when focused | Global Escape listener while popup is visible | Var |
| Right-click to close | Yes | Yes | Var |
| Auto-hide | Yes, configurable | Yes, configurable in settings | Var |
| Target language change | Yes | Yes | Var |
| Searchable target language picker | Dedicated picker with accent-insensitive search | Dedicated picker with accent-insensitive search | Var |
| Swap translation | Yes | Yes | Var |
| Target sync with main and settings | Yes | Yes | Var |

## 6. OCR

| Feature | Tkinter 1.0.0 | PySide6 2.0.0 | Status |
|---|---|---|---|
| OCR enable setting | Yes | Settings toggle | Var |
| Separate OCR hotkey | Yes | Yes, capture dialog | Var |
| OCR language setting | Yes | Yes | Var |
| Full-screen region selector | Yes | Yes, Qt overlay | Var |
| Dimmed outside selection | Yes | Yes | Var |
| Esc and right-click cancel | Yes | Yes | Var |
| Minimum selection size | 12 px | 12 px | Var |
| DPI-aware screen capture | Yes | Yes | Var |
| Windows OCR | Yes | Yes | Var |
| OCR language fallback | Yes | Yes | Var |
| Installed OCR language fallback | Yes | Yes | Var |
| Image upscale | 2x, 3x for small regions | 2x, 3x for small regions | Var |
| Dark theme inversion | Yes | Yes | Var |
| Tesseract fallback | Yes, with language | Yes, with language | Var |
| Failure screenshot path | Yes | Yes | Var |
| OCR result in popup | Yes | Yes | Var |

The OCR workflow is fully connected to the PySide6 interface: overlay selection,
recognition in a worker thread, error reporting and popup translation.

## 7. Clipboard monitoring

| Feature | Tkinter 1.0.0 | PySide6 2.0.0 | Status |
|---|---|---|---|
| Clipboard watcher | Yes | Yes, started from settings | Var |
| Enable/disable setting | Yes | Yes | Var |
| URL filtering | Yes | Yes | Var |
| Length filtering | Yes | Yes | Var |
| Suppress own clipboard writes | Yes | Yes | Var |
| Restore clipboard after capture | Yes | Yes | Var |
| Clipboard translation popup | Yes | Yes | Var |

## 8. History

| Feature | Tkinter 1.0.0 | PySide6 2.0.0 | Status |
|---|---|---|---|
| History storage | Yes | Yes | Var |
| History limit | Configurable in settings | Configurable in settings | Var |
| Search | Yes, Turkish-aware | Yes, Turkish-aware | Var |
| Refresh | Yes | Yes automatically | Var |
| Table columns | Date, source, translation, languages, engine | Single wrapped list | Kismi |
| Copy selected translation | Yes | Yes | Var |
| Save selected as word | Yes | Yes | Var |
| Delete selected record | Yes | Yes | Var |
| Clear all | Yes | Yes | Var |
| Detail window | Separate dialog | Separate dialog with copy and speak | Var |
| Open history item | Double click detail | Double click loads item | Farkli |
| Empty state | No explicit message | Yes | Var |

## 9. Saved words

| Feature | Tkinter 1.0.0 | PySide6 2.0.0 | Status |
|---|---|---|---|
| Add word | Yes | Yes | Var |
| Duplicate detection | Yes, Turkish-aware | Yes, Turkish-aware | Var |
| Search | Yes, Turkish-aware | Yes, Turkish-aware | Var |
| Table columns | Word, translation, languages, date | Single wrapped list | Kismi |
| Delete selected | Yes | Yes | Var |
| Clear all | Yes | Yes | Var |
| CSV export | UTF-8 BOM, Excel friendly | UTF-8 BOM, Excel friendly | Var |
| Card study mode | Yes, reveal, next, previous, speak | Reveal, next, previous and speak | Var |
| Keyboard navigation in cards | Space, Left, Right | Space, Left, Right | Var |
| Empty state | No explicit message | Yes | Var |

## 10. Settings

| Feature | Tkinter 1.0.0 | PySide6 2.0.0 | Status |
|---|---|---|---|
| Hotkey text field | Yes | Yes | Var |
| Hotkey capture button | Yes | Yes | Var |
| Autostart toggle | Yes | Yes | Var |
| Clipboard monitor toggle | Yes | Yes | Var |
| Restore clipboard toggle | Yes | Yes | Var |
| OCR enable toggle | Yes | Yes | Var |
| OCR hotkey field | Yes | Yes, with capture | Var |
| OCR language field | Yes | Yes | Var |
| Default target language | Yes | Yes | Var |
| Primary engine | Yes | Yes | Var |
| Backup engines toggle | Yes | Yes | Var |
| LibreTranslate endpoint and key | Yes | Yes | Var |
| Lingva endpoint | Yes | Yes | Var |
| LLM endpoint, model and key | Yes | Yes | Var |
| Popup auto-hide seconds | Yes | Yes | Var |
| TTS rate | Yes | Yes | Var |
| History limit | Yes | Yes | Var |
| UI language | No | Turkish, English, System | Farkli |
| Save and apply | Yes | Per-section Save buttons, enabled only after a change | Var |
| Reset to defaults | Yes | Yes | Var |
| Background behavior banner | Yes | Yes | Var |
| Hide to tray button | Yes | Yes | Var |
| Quit application button | Yes | Yes | Var |
| Settings status text | Yes | Yes, in settings and status bar | Var |

## 11. TTS and audio

| Feature | Tkinter 1.0.0 | PySide6 2.0.0 | Status |
|---|---|---|---|
| Windows SAPI speech | Yes | Yes | Var |
| Speak from popup | Yes | Yes | Var |
| Speak from manual output | Yes | Yes | Var |
| Speak from history detail | Yes | Yes | Var |
| Speak from study cards | Yes | Yes | Var |
| Stop current speech | Yes | Yes | Var |
| TTS rate setting | Yes | Yes | Var |
| Kill speech process on exit | Job Object | Job Object | Var |
| Voice selection | No | No | Ayni |

## 12. Storage and data

| Feature | Tkinter 1.0.0 | PySide6 2.0.0 | Status |
|---|---|---|---|
| JSON config, history, words | Yes | Yes | Var |
| Atomic writes | Yes | Yes | Var |
| `.bak` backups | Yes | Yes | Var |
| Config type validation | Yes | Yes | Var |
| Duplicate record id recovery | Yes | Yes | Var |
| Source-relative data directory | Yes | No | Farkli |
| LocalAppData fallback | Yes | Always LocalAppData | Farkli |
| `QB_DATA_DIR` override | Yes | Yes | Var |
| Window geometry persistence | Yes | Saved and restored | Var |
| Migration from old data | Not applicable | Missing | Yok |

The data path change is intentional for the packaged application, but existing
Tkinter data is not migrated automatically. The old source data remains in the
archive.

## 13. Tray, background and Windows integration

| Feature | Tkinter 1.0.0 | PySide6 2.0.0 | Status |
|---|---|---|---|
| Tray icon | Yes | Yes | Var |
| Tray open/quit menu | Yes | Yes, localized | Var |
| Tray balloon | Yes | Yes | Var |
| Explorer restart icon restore | Yes | Yes | Var |
| Hide to tray on X | Yes | Yes | Var |
| Explicit hide/quit UI | Yes | Yes | Var |
| Autostart registry | Yes | Yes | Var |
| Single instance messaging | Yes | Yes | Var |
| Window activation by title | Yes | Yes | Var |

## 14. New behavior in the PySide6 version

These are improvements or intentional changes, not regressions:

- Modern Qt interface with dark theme and high-DPI handling
- Medium weight Segoe UI typography for thicker and smoother text
- Per-section settings save buttons with disabled and dirty states
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
- OCR overlay, clipboard monitoring, history and word tools, card study mode
- Autostart, single instance and background command line lifecycle
- No em dash in the active project UI or documentation

## 15. Restoration order and remaining work

### Completed

1. OCR selection overlay and OCR workflow
2. Clipboard monitoring and settings
3. Autostart, single instance and CLI flags
4. Hotkey capture dialog
5. Engine settings panels for LibreTranslate, Lingva and LLM
6. Settings fields for TTS rate, history limit, popup auto-hide and clipboard restore
7. Source language persistence and window geometry persistence
8. History search, copy, save, delete and detail dialog
9. Saved words search, delete, CSV export and study mode
10. About tab
11. Reset defaults, hide to tray and quit buttons
12. Status chips for clipboard and OCR
13. Right-click popup close and global Escape handling
14. Accent-insensitive language picker
15. Background and quit command-line behavior

### Remaining

16. Packaging and installer
17. Data migration from Tkinter
18. Real multi-monitor and mixed-DPI test pass
19. Accessibility and keyboard navigation
