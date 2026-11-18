"""make_icon.py — assets/icons/*.png dosyalarından çok boyutlu ICO üretir."""

from __future__ import annotations

import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ICON_DIR = ROOT / "assets" / "icons"
OUTPUT = ROOT / "assets" / "QBTranslator.ico"
SIZES = (16, 32, 48, 128)


def main() -> None:
    entries = []
    payload = bytearray()
    header_size = 6 + 16 * len(SIZES)
    offset = header_size

    images = []
    for size in SIZES:
        path = ICON_DIR / f"icon_{size}.png"
        if not path.exists():
            raise SystemExit(f"Eksik ikon: {path}")
        data = path.read_bytes()
        images.append((size, data))

    header = struct.pack("<HHH", 0, 1, len(images))
    for size, data in images:
        width = 0 if size >= 256 else size
        height = 0 if size >= 256 else size
        entries.append(
            struct.pack(
                "<BBBBHHII",
                width,
                height,
                0,
                0,
                1,
                32,
                len(data),
                offset,
            )
        )
        payload.extend(data)
        offset += len(data)

    OUTPUT.write_bytes(header + b"".join(entries) + bytes(payload))
    print(f"Ikon yazıldı: {OUTPUT} ({OUTPUT.stat().st_size} bayt)")


if __name__ == "__main__":
    main()
