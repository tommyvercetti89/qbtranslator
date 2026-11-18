# Third-Party Notices

QBTranslator is distributed under the MIT License. The release packages include
third-party components with their own licenses. This file summarizes the main
components. Full license texts for the GNU licenses are included under `LICENSES/`.

## PySide6 and Qt

- Project: https://www.qt.io/qt-for-python
- Copyright: The Qt Company and contributors
- License: LGPLv3, GPLv3 or commercial Qt license

QBTranslator uses the open-source PySide6 bindings and the QtCore, QtGui and
QtWidgets modules under the LGPLv3 terms. The onedir package keeps Qt libraries as
separate replaceable files. The portable one-file build extracts the same libraries
to a temporary directory at runtime.

Qt and PySide6 source code are available from The Qt Company and the PySide6
project. See `LICENSES/LGPL-3.0.txt` and `LICENSES/GPL-3.0.txt`.

## Shiboken6

- Project: https://github.com/qtproject/pyside-pyside-setup
- Copyright: The Qt Company and contributors
- License: LGPLv3, GPLv3 or commercial Qt license

## Python

- Project: https://www.python.org
- Copyright: Python Software Foundation
- License: PSF License Agreement
- https://docs.python.org/3/license.html

## OpenSSL

- Project: https://www.openssl.org
- Copyright: The OpenSSL Project Authors
- License: Apache License 2.0
- https://www.openssl.org/source/license.html

The Windows packages include `libcrypto-3.dll` and `libssl-3.dll` from OpenSSL for
HTTPS connections made by the Python standard library.

## PyInstaller

- Project: https://pyinstaller.org
- Copyright: PyInstaller Development Team
- License: GPLv2 with a special exception for bootloaders
- https://pyinstaller.org/en/stable/license.html

PyInstaller is used only to produce the Windows executables.

## Inno Setup

- Project: https://jrsoftware.org/isinfo.php
- Copyright: Jordan Russell and Martijn Laan
- License: Inno Setup License
- https://jrsoftware.org/files/is/license.txt

Inno Setup is used only to produce the optional installer.

## Microsoft Visual C++ Runtime

The Windows packages include Microsoft Visual C++ runtime libraries required by
Python, Qt and PySide6. These files are redistributed under the Microsoft Visual
Studio license terms.

## Translation services

Google Translate, MyMemory, LibreTranslate, Lingva and user-configured LLM services
are not bundled with QBTranslator. They are contacted only when the user requests a
translation and remain subject to their own terms of service and privacy policies.

## Inspiration

The selection-translation and OCR workflow is inspired by the
[MouseTooltipTranslator](https://github.com/ttop32/MouseTooltipTranslator) browser
extension. No browser-extension code is included in QBTranslator.
