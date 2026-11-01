#!/usr/bin/env python3
"""Render the original OmaCraft icon family without third-party art or dependencies."""
from pathlib import Path
import struct
import zlib
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'assets/omaword-icon'
APP_ID = 'io.github.ustaaa.OmaWord'
ACCENT = '#5b8fe0'
VARIANT = 'word'
SIZES = (16, 24, 32, 48, 64, 128, 256, 512)


def scene():
    # Shared dark tile, paper silhouette, and folded corner establish the family.
    shapes = [
        ('roundrect', (8, 8, 240, 240, 48), '#171c27'),
        ('roundrect', (52, 48, 154, 168, 19), '#10151e'),  # quiet depth behind the sheet
        ('roundrect', (48, 42, 154, 168, 17), '#f2f2ee'),
        ('polygon', ([(158, 42), (202, 42), (202, 86)],), '#d9dfe3'),
        ('polygon', ([(158, 42), (158, 86), (202, 86)],), '#e8e9e5'),
    ]
    if VARIANT == 'grid':
        # A compact table with a single softly selected cell.
        shapes += [
            ('roundrect', (66, 91, 118, 92, 9), '#e1e5e2'),
            ('rect', (66, 91, 118, 9), ACCENT),
            ('rect', (66, 109, 118, 8), '#d8dedb'),
            ('rect', (66, 129, 118, 8), '#d8dedb'),
            ('rect', (66, 149, 118, 8), '#d8dedb'),
            ('rect', (66, 169, 118, 8), '#d8dedb'),
            ('rect', (66, 189, 118, 8), '#d8dedb'),
            ('rect', (91, 109, 7, 88), '#d8dedb'),
            ('rect', (116, 109, 7, 88), '#d8dedb'),
            ('rect', (141, 109, 7, 88), '#d8dedb'),
            ('roundrect', (151, 132, 29, 29, 5), ACCENT),
            ('rect', (157, 138, 17, 5), '#eff7f2'),
            ('rect', (157, 146, 17, 5), '#eff7f2'),
        ]
    elif VARIANT == 'deck':
        # Three offset slide cards read as a small presentation stack.
        shapes += [
            ('roundrect', (58, 70, 128, 105, 12), '#9a5367'),
            ('roundrect', (64, 63, 128, 105, 12), '#c98591'),
            ('roundrect', (70, 56, 128, 105, 12), '#f7f3ef'),
            ('roundrect', (82, 69, 104, 19, 7), ACCENT),
            ('rect', (84, 104, 80, 7), '#d5d9dc'),
            ('rect', (84, 120, 63, 7), '#d5d9dc'),
            ('rect', (84, 136, 80, 7), '#d5d9dc'),
            ('polygon', ([(127, 168), (141, 168), (145, 183), (123, 183)],), '#e4e2de'),
            ('roundrect', (106, 181, 56, 9, 4), '#c98591'),
        ]
    elif VARIANT == 'word':
        # Calm manuscript lines and a blue margin accent.
        shapes += [
            ('roundrect', (66, 90, 118, 104, 8), '#e1e5e8'),
            ('rect', (66, 90, 8, 104), ACCENT),
            ('roundrect', (87, 103, 81, 8, 4), '#596474'),
            ('roundrect', (87, 123, 69, 8, 4), '#8a939c'),
            ('roundrect', (87, 143, 81, 8, 4), '#8a939c'),
            ('roundrect', (87, 163, 52, 8, 4), '#8a939c'),
            ('roundrect', (87, 183, 69, 8, 4), '#8a939c'),
        ]
    else:
        # Notes gets an unmistakable binding rail and a few generous writing strokes.
        shapes += [
            ('roundrect', (65, 88, 120, 105, 8), '#e2e2e7'),
            ('roundrect', (64, 87, 14, 107, 7), ACCENT),
            ('roundrect', (90, 105, 78, 9, 4), '#596474'),
            ('roundrect', (90, 127, 78, 9, 4), '#8a8995'),
            ('roundrect', (90, 149, 64, 9, 4), '#8a8995'),
            ('roundrect', (90, 171, 78, 9, 4), '#8a8995'),
            ('roundrect', (90, 193, 48, 7, 3), '#8a8995'),
            ('roundrect', (67, 105, 8, 7, 3), '#f4eefa'),
            ('roundrect', (67, 127, 8, 7, 3), '#f4eefa'),
            ('roundrect', (67, 149, 8, 7, 3), '#f4eefa'),
            ('roundrect', (67, 171, 8, 7, 3), '#f4eefa'),
        ]
    return shapes


def inside(shape, x, y):
    kind, data, _ = shape
    if kind == 'rect':
        a, b, w, h = data
        return a <= x < a+w and b <= y < b+h
    if kind == 'roundrect':
        a, b, w, h, r = data
        if not (a <= x < a+w and b <= y < b+h):
            return False
        qx = max(a+r-x, 0, x-(a+w-r))
        qy = max(b+r-y, 0, y-(b+h-r))
        return qx*qx + qy*qy <= r*r
    if kind == 'polygon':
        (points,) = data
        hit = False
        j = len(points)-1
        for i, (xi, yi) in enumerate(points):
            xj, yj = points[j]
            if (yi > y) != (yj > y) and x < (xj-xi)*(y-yi)/(yj-yi)+xi:
                hit = not hit
            j = i
        return hit
    return False


def chunk(kind, data):
    return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))


def png(size, shapes):
    # 2x2 coverage sampling keeps even the 16 px output crisp and deterministic.
    rows = bytearray()
    steps = 2
    for py in range(size):
        rows.append(0)
        for px in range(size):
            sums = [0, 0, 0, 0]
            for sy in range(steps):
                for sx in range(steps):
                    x = (px + (sx + .5)/steps) * 256 / size
                    y = (py + (sy + .5)/steps) * 256 / size
                    color = (0, 0, 0, 0)
                    for shape in shapes:
                        if inside(shape, x, y):
                            h = shape[2].lstrip('#')
                            color = tuple(int(h[i:i+2], 16) for i in (0, 2, 4)) + (255,)
                    for i, value in enumerate(color):
                        sums[i] += value
            rows.extend((value + steps*steps//2)//(steps*steps) for value in sums)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 6, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(bytes(rows), 9)) + chunk(b'IEND', b''))


def svg(shapes):
    elements = []
    for kind, data, color in shapes:
        if kind == 'rect':
            x, y, w, h = data
            elements.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{color}"/>')
        elif kind == 'roundrect':
            x, y, w, h, r = data
            elements.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{color}"/>')
        else:
            (pts,) = data
            points = ' '.join(f'{x},{y}' for x,y in pts)
            elements.append(f'<polygon points="{points}" fill="{color}"/>')
    return '<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 256 256">\n' + '\n'.join(elements) + '\n</svg>\n'


shapes = scene()
DEST.mkdir(parents=True, exist_ok=True)
rendered = {size: png(size, shapes) for size in SIZES}
for size in SIZES:
    folder = DEST / str(size)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f'{APP_ID}.png').write_bytes(rendered[size])
vector = svg(shapes)
(DEST / f'{APP_ID}.svg').write_text(vector, encoding='utf-8')
# The icon container stores all standard sizes, each as a PNG-compressed ICO frame.
frames = [(s, rendered[s]) for s in (16, 24, 32, 48, 64, 128, 256)]
header = struct.pack('<HHH', 0, 1, len(frames))
offset = 6 + 16*len(frames)
entries = bytearray()
for size, data in frames:
    entries += struct.pack('<BBBBHHII', 0 if size == 256 else size, 0 if size == 256 else size, 0, 0, 1, 32, len(data), offset)
    offset += len(data)
(DEST / 'omaword.ico').write_bytes(header + entries + b''.join(data for _, data in frames))
