#!/usr/bin/env python3
"""Render OmaWord's original geometric icon; standard library only, no external assets."""
from pathlib import Path
import struct
import zlib

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'assets' / 'omaword-icon'
APP_ID = 'io.github.ustaaa.OmaWord'
INK = (25, 31, 41, 255)
TEAL = (112, 212, 187, 255)
PAPER = (235, 242, 240, 255)

def pixel(x, y):
    if not (12 <= x < 244 and 12 <= y < 244):
        return (0, 0, 0, 0)
    # Original paper tile, three unequal text strokes and a blue margin.
    cx, cy = min(max(x, 40), 216), min(max(y, 40), 216)
    if (x-cx)**2 + (y-cy)**2 > 28**2:
        return (0, 0, 0, 0)
    if 48 <= x < 208 and 44 <= y < 212:
        if 60 <= x < 70: return (120, 173, 245, 255)
        for y0, x1 in [(78,184),(112,172),(146,184),(180,150)]:
            if 88 <= x < x1 and y0 <= y < y0+9: return INK
        return PAPER
    return INK

def chunk(kind, data):
    return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))

def png(size):
    rows = bytearray()
    for y in range(size):
        rows.append(0)
        for x in range(size):
            rows.extend(pixel((x + .5) * 256 / size, (y + .5) * 256 / size))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 6, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(bytes(rows), 9)) + chunk(b'IEND', b''))

for size in (16, 24, 32, 48, 64, 128, 256, 512):
    folder = DEST / str(size)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f'{APP_ID}.png').write_bytes(png(size))
(DEST / f'{APP_ID}.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 256 256"><rect x="12" y="12" width="232" height="232" rx="28" fill="#191f29"/><path d="M48 44h160v168H48z" fill="#ebf2f0"/><path d="M60 44h10v168H60z" fill="#78adf5"/><path d="M88 78h96v9H88z M88 112h84v9H88z M88 146h96v9H88z M88 180h62v9H88z" fill="#191f29"/></svg>\n')
image = png(256)
(DEST / 'omaword.ico').write_bytes(struct.pack('<HHH', 0, 1, 1) + struct.pack('<BBBBHHII', 0, 0, 0, 0, 1, 32, len(image), 22) + image)
