# Release Guide

This document describes the repeatable release process for QBTranslator. Release
builds must be produced from a clean path that does not contain a developer
username. GitHub Actions is preferred because its workspace path is neutral. A
local build can use a directory such as `C:\Users\Public\qbtranslator-build` or a
CI runner workspace.

## 1. Version updates

Update the version in all of these locations:

- `src/qbtranslator/core/appinfo.py`
- `pyproject.toml`
- `build_tools/version_info.txt`
- `CHANGELOG.md`
- `README.md` release references, if any
- `build_tools/installer.iss` default, if the build script does not pass it

The build script passes the version to Inno Setup with `/DMyAppVersion`.

## 2. Preflight checks

```powershell
python -m pytest -o addopts="" -q
python -m ruff check src tests
python -m compileall -q src tests
python run.py --selftest
```

Verify that no local or sensitive files are staged:

```powershell
git status --short
git diff --check
```

Search for personal paths, credentials and tokens before committing:

```powershell
rg -n "C:\\\\Users\\\\|/Users/|ghp_|github_pat_|sk-[A-Za-z0-9]" .
```

The expected match set is empty except for documentation placeholders such as
`C:\path\to\QBTranslator`.

## 3. Build

Install the build tools:

```powershell
python -m pip install pyinstaller==6.20.0
```

Run:

```powershell
powershell -ExecutionPolicy Bypass -File build_tools\build.ps1
```

Add `-SkipInstaller` when Inno Setup is not available, or `-SkipPortable` to build
only the recommended onedir package.

The script performs these steps:

1. Cleans previous output.
2. Builds the onedir package with unused Qt modules excluded.
3. Copies documentation and license files into the package.
4. Runs the packaged `--selftest`.
5. Creates `release/QBTranslator-<version>-windows-x64.zip`.
6. Builds and selftests the portable single-file executable.
7. Builds the installer when Inno Setup 6 is present.
8. Writes `release/SHA256SUMS.txt`.

## 4. Validate the artifacts

- Confirm that the onedir and portable selftests print `assets=OK`.
- Launch the onedir build and run a manual translation.
- Open Settings, change one field, and confirm only that section's Save button
  becomes active.
- Test OCR on a region with readable text.
- Verify that no personal path appears in the About tab. It must show
  `%LOCALAPPDATA%\QBTranslator\data` unless `QB_DATA_DIR` is set.
- Check release file sizes and hashes.
- Install the optional installer in a clean user profile and uninstall it.

## 5. Commit and tag

Use the generic project identity for release commits:

```powershell
git config user.name "QBTranslator"
git config user.email "qbtranslator@users.noreply.github.com"
git add -A
git commit -m "release: QBTranslator <version>"
git tag -a "v<version>" -m "QBTranslator <version>"
```

## 6. Push

```powershell
git push origin main
git push origin "v<version>"
```

The repository history keeps the archived Tkinter release under the `v1.0.0`
tag. Do not rewrite or delete existing release tags.

## 7. Create the GitHub release

```powershell
gh release create "v<version>" `
  "release/QBTranslator-Setup-<version>.exe" `
  "release/QBTranslator-<version>-windows-x64.zip" `
  "release/QBTranslator-Portable-<version>.exe" `
  "release/SHA256SUMS.txt" `
  --title "QBTranslator v<version>" `
  --notes-file "release/RELEASE_NOTES.md" `
  --latest
```

Release notes must include:

- Summary of new features
- Downloads table with file sizes and SHA-256 hashes
- Windows and OCR requirements
- Privacy and unsigned-build notes
- Known limitations
- Upgrade or compatibility notes

## 8. Post-release checks

- Open the release page while signed out and verify every asset downloads.
- Verify the SHA-256 checksums from a clean shell.
- Confirm that the release is marked latest.
- Confirm that the tag points to the intended release commit.

## Signing

The current builds are unsigned. Code signing is recommended before broad
distribution. Use a hardware token, cloud HSM or an open-source signing service.
Do not store certificate private keys or signing passwords in the repository.
