"""Mały zestaw do rysowania pixel artu 16x16 w palecie PRL."""
import random
from PIL import Image

PAL = {
    '.': None,
    'k': (30, 27, 24),
    # stal
    '1': (52, 55, 60), '2': (84, 90, 97), '3': (128, 135, 142), '4': (176, 182, 186), '5': (222, 225, 222),
    # rdza
    'r': (95, 50, 30), 'R': (138, 76, 40), 'o': (176, 104, 56), 'O': (210, 140, 80),
    # drewno
    'w': (70, 48, 32), 'W': (104, 72, 46), 'd': (138, 100, 64), 'D': (170, 130, 88),
    # oliwka (PRL)
    'g': (58, 68, 42), 'G': (84, 97, 58), 'h': (110, 124, 76), 'H': (140, 154, 98),
    # błękit emalii
    'b': (44, 70, 92), 'B': (62, 102, 128), 'c': (92, 140, 168), 'C': (140, 182, 204),
    # czerwień
    'e': (118, 36, 30), 'E': (163, 57, 46), 'f': (200, 86, 64),
    # żółć ostrzegawcza
    'y': (160, 128, 44), 'Y': (212, 175, 69), 'Z': (236, 208, 112),
    # beż / papier
    's': (176, 164, 132), 'S': (214, 202, 168), 'z': (236, 230, 214),
    # czerń
    'n': (40, 40, 40), 'N': (62, 62, 62),
    # kamień
    't': (90, 86, 80), 'T': (125, 120, 112), 'u': (157, 151, 140),
    # stal wojskowa
    'm': (40, 42, 50), 'M': (66, 70, 80), 'l': (104, 110, 122),
    # proch
    'p': (72, 70, 66), 'P': (108, 104, 98), 'q': (146, 140, 130),
    # mosiądz
    'a': (130, 100, 44), 'A': (180, 142, 62), 'x': (220, 184, 102),
    # ogień / żar
    'F': (240, 150, 50), 'v': (250, 210, 90),
}


def parse(rows):
    rows = [r for r in rows.strip('\n').split('\n')]
    assert len(rows) == 16, len(rows)
    img = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
    for y, row in enumerate(rows):
        row = row.strip()
        assert len(row) == 16, (y, row, len(row))
        for x, ch in enumerate(row):
            col = PAL[ch]
            if col:
                img.putpixel((x, y), col + (255,))
    return img


def _scale(c, f):
    return tuple(max(0, min(255, int(v * f))) for v in c[:3]) + (c[3],)


def shade(img, seed=0, noise=0.05, dark=0.72, light=1.14):
    """Ciemniejsza krawędź z prawej i z dołu, jaśniejsza z lewej i z góry, lekki szum."""
    rnd = random.Random(seed)
    w, h = img.size
    src = img.copy()
    out = img.copy()
    def opaque(x, y):
        return 0 <= x < w and 0 <= y < h and src.getpixel((x, y))[3] > 0
    for y in range(h):
        for x in range(w):
            c = src.getpixel((x, y))
            if c[3] == 0:
                continue
            f = 1 + rnd.uniform(-noise, noise)
            if not opaque(x + 1, y) or not opaque(x, y + 1):
                f *= dark
            elif not opaque(x - 1, y) or not opaque(x, y - 1):
                f *= light
            out.putpixel((x, y), _scale(c, f))
    return out


def texture(rows, seed=0, noise=0.06):
    """Tekstura bloku: bez cieniowania krawędzi, tylko szum."""
    img = parse(rows)
    rnd = random.Random(seed)
    for y in range(16):
        for x in range(16):
            c = img.getpixel((x, y))
            if c[3]:
                img.putpixel((x, y), _scale(c, 1 + rnd.uniform(-noise, noise)))
    return img


def sheet(images, scale=8, cols=8, bg=(54, 58, 52)):
    names = list(images)
    rows = (len(names) + cols - 1) // cols
    cell = 16 * scale + 8
    out = Image.new('RGBA', (cols * cell, rows * cell), bg + (255,))
    for i, n in enumerate(names):
        im = images[n].resize((16 * scale, 16 * scale), Image.NEAREST)
        out.alpha_composite(im, ((i % cols) * cell + 4, (i // cols) * cell + 4))
    return out
