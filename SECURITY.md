# Security Policy

## Supported versions

| Version | Supported |
|---|---|
| 2.x | Yes |
| 1.x | No, archived Tkinter release |

## Reporting a vulnerability

Please do not open a public issue for security problems.

Use GitHub's private vulnerability reporting for this repository:

1. Open the repository Security tab.
2. Select "Report a vulnerability".
3. Include affected version, reproduction steps and impact.

If private reporting is unavailable, open a minimal public issue asking for a
private contact channel. Do not include exploit details, credentials, local file
paths or user data in the public issue.

## Scope

Relevant reports include:

- Remote code execution or command injection
- Unintended disclosure of local history, saved words or API keys
- Unsafe handling of OCR images, clipboard content or translation responses
- Privilege escalation through autostart, installer or update paths
- Dependency vulnerabilities with a practical impact on QBTranslator

## Data and credentials

QBTranslator is local-first and does not include telemetry. History, saved words,
settings and optional API keys are stored in the user's local data directory.
Translated text is sent only to the translation engine selected in Settings.

The release repository must never contain:

- API keys, tokens or passwords
- User history, saved words or OCR screenshots
- Personal file paths or author contact details
- Build output from a developer machine

## Release integrity

Release artifacts are published with SHA-256 checksums. The binaries are not
code-signed at this time, so Windows SmartScreen may show a warning. Verify the
published checksums before running a download.
