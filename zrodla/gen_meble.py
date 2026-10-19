#!/usr/bin/env python3
"""Meble do struktur AXON-Structure (jedna kratka, przód modelu na południe = +z).

Plugin zamienia bloki z pliku struktury na barierę i stawia na nich te modele (config `meble.bloki`).
Każdy mebel ma własną teksturę 64x64 złożoną z kafelków 16x16 px (w modelu uv 4x4).
Zapisuje build/<nazwa>.json, build/<nazwa>.png i build/<nazwa>_item.json.
"""
import json, os, random
from PIL import Image, ImageDraw
from gen_rekwizyty import noise, stains, write, FACES


def tiles_texture(painters, seed):
    rnd = random.Random(seed)
    im = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    uv = {}
    for i, (name, paint) in enumerate(painters):
        x, y = (i % 4) * 16, (i // 4) * 16
        paint(im, d, (x, y, x + 16, y + 16), rnd)
        uv[name] = [x / 4, y / 4, x / 4 + 4, y / 4 + 4]
    return im, uv


def plain(col, amp=5, rust=0):
    def p(im, d, b, rnd):
        noise(im, b, col, amp, rnd)
        if rust:
            stains(im, b, (120, 72, 40, 255), rust, rnd, 1)
    return p


def model(name, parts, painters, seed):
    tex, uv = tiles_texture(painters, seed)
    els = []
    for part in parts:
        f, t, region = part[:3]
        special = part[3] if len(part) > 3 else {}
        els.append({'from': f, 'to': t, 'faces': {fc: {'uv': uv[special.get(fc, region)], 'texture': '#t'}
                                                  for fc in FACES}})
    for e in els:
        for c in e['from'] + e['to']:
            assert -16 <= c <= 32, (name, e)
    write(name, {'textures': {'t': 'axon:item/' + name, 'particle': 'axon:item/' + name}, 'elements': els}, tex)


# ---------------------------------------------------------------- kafelki


def binders(im, d, b, rnd):
    x0, y0, x1, y1 = b
    noise(im, b, (60, 62, 64), 3, rnd)
    for row in (y0, y0 + 8):
        x = x0
        while x < x1:
            w = rnd.choice((2, 2, 3))
            col = rnd.choice(((150, 40, 40), (40, 70, 130), (60, 100, 60), (190, 170, 120), (110, 110, 110)))
            if rnd.random() < 0.15:
                x += w
                continue
            h = rnd.randint(5, 7)
            d.rectangle([x, row + 7 - h, min(x + w - 1, x1 - 1), row + 6], fill=col + (255,))
            d.point((x, row + 7 - h + 1), fill=(220, 220, 210, 255))
            x += w
        d.line([(x0, row + 7), (x1 - 1, row + 7)], fill=(130, 132, 134, 255))


def drawers(im, d, b, rnd):
    x0, y0, x1, y1 = b
    noise(im, b, (104, 112, 100), 4, rnd)
    for k in range(4):
        y = y0 + k * 4
        d.rectangle([x0, y, x1 - 1, y + 3], outline=(70, 76, 66, 255))
        d.rectangle([x0 + 6, y + 1, x0 + 9, y + 1], fill=(190, 190, 180, 255))
        d.point((x0 + 7, y + 2), fill=(230, 230, 220, 255))
    stains(im, b, (120, 72, 40, 255), 3, rnd, 1)


def ceramic_bowl(im, d, b, rnd):
    x0, y0, x1, y1 = b
    noise(im, b, (222, 222, 214), 4, rnd)
    d.rectangle([x0 + 2, y0 + 2, x1 - 3, y1 - 3], fill=(176, 178, 172, 255))
    d.ellipse([x0 + 7, y0 + 7, x0 + 8, y0 + 8], fill=(40, 40, 40, 255))
    stains(im, (x0 + 2, y0 + 2, x1 - 3, y1 - 3), (150, 120, 70, 255), 3, rnd, 1)


def wood_top(im, d, b, rnd):
    x0, y0, x1, y1 = b
    noise(im, b, (120, 88, 56), 6, rnd)
    for y in range(y0 + 3, y1, 4):
        d.line([(x0, y), (x1 - 1, y)], fill=(92, 66, 40, 255))
    stains(im, b, (60, 50, 44, 255), 4, rnd, 1)


def tools(im, d, b, rnd):
    x0, y0, x1, y1 = b
    noise(im, b, (150, 120, 84), 5, rnd)                         # płyta z otworami
    for y in range(y0 + 1, y1, 3):
        for x in range(x0 + 1, x1, 3):
            im.putpixel((x, y), (90, 70, 50, 255))
    d.line([(x0 + 3, y0 + 3), (x0 + 3, y0 + 11)], fill=(180, 40, 30, 255), width=2)      # śrubokręt
    d.line([(x0 + 7, y0 + 2), (x0 + 7, y0 + 10)], fill=(140, 140, 140, 255), width=1)   # klucz
    d.rectangle([x0 + 6, y0 + 2, x0 + 8, y0 + 3], fill=(140, 140, 140, 255))
    d.line([(x0 + 11, y0 + 4), (x0 + 11, y0 + 12)], fill=(110, 80, 50, 255), width=2)   # młotek
    d.rectangle([x0 + 9, y0 + 3, x0 + 13, y0 + 4], fill=(70, 70, 74, 255))


def enamel_front(im, d, b, rnd):
    x0, y0, x1, y1 = b
    noise(im, b, (214, 210, 196), 4, rnd)
    d.rectangle([x0 + 2, y0 + 4, x1 - 3, y1 - 2], fill=(40, 40, 42, 255), outline=(150, 150, 146, 255))
    d.line([(x0 + 4, y0 + 5), (x1 - 5, y0 + 5)], fill=(170, 170, 166, 255))
    for x in (x0 + 3, x0 + 6, x0 + 9, x0 + 12):
        d.point((x, y0 + 2), fill=(30, 30, 30, 255))
    stains(im, b, (120, 72, 40, 255), 4, rnd, 1)


def burners(im, d, b, rnd):
    x0, y0, x1, y1 = b
    noise(im, b, (210, 206, 194), 4, rnd)
    for cx, cy in ((4, 4), (11, 4), (4, 11), (11, 11)):
        d.ellipse([x0 + cx - 3, y0 + cy - 3, x0 + cx + 2, y0 + cy + 2], fill=(34, 34, 36, 255))
        d.ellipse([x0 + cx - 1, y0 + cy - 1, x0 + cx, y0 + cy], fill=(90, 90, 96, 255))


def cast_iron_door(im, d, b, rnd):
    x0, y0, x1, y1 = b
    noise(im, b, (44, 42, 42), 4, rnd)
    d.rectangle([x0 + 3, y0 + 4, x1 - 4, y1 - 4], outline=(80, 76, 72, 255))
    for x in range(x0 + 5, x1 - 5, 2):
        d.line([(x, y0 + 6), (x, y1 - 6)], fill=(220, 110, 30, 255))
    d.rectangle([x1 - 5, y0 + 7, x1 - 4, y0 + 8], fill=(150, 140, 120, 255))


def radio_panel(im, d, b, rnd):
    x0, y0, x1, y1 = b
    noise(im, b, (78, 90, 58), 4, rnd)
    d.rectangle([x0 + 1, y0 + 1, x0 + 8, y0 + 6], fill=(20, 26, 20, 255), outline=(40, 44, 36, 255))
    d.line([(x0 + 2, y0 + 4), (x0 + 4, y0 + 3), (x0 + 6, y0 + 5), (x0 + 7, y0 + 3)], fill=(90, 230, 110, 255))
    for x in (x0 + 10, x0 + 13):
        d.ellipse([x - 1, y0 + 2, x + 1, y0 + 4], fill=(30, 30, 30, 255), outline=(170, 170, 160, 255))
    for x in range(x0 + 2, x0 + 14, 3):
        d.rectangle([x, y0 + 9, x + 1, y0 + 10], fill=(30, 30, 30, 255))
    d.point((x0 + 13, y0 + 12), fill=(230, 40, 30, 255))
    d.rectangle([x0 + 2, y0 + 12, x0 + 9, y0 + 14], fill=(60, 66, 44, 255))


def tap(im, d, b, rnd):
    noise(im, b, (176, 178, 180), 8, rnd)


def label_box(im, d, b, rnd):
    x0, y0, x1, y1 = b
    noise(im, b, (170, 136, 88), 6, rnd)
    d.line([(x0, y0 + 7), (x1 - 1, y0 + 7)], fill=(196, 170, 120, 255))
    d.rectangle([x0 + 4, y0 + 9, x0 + 11, y0 + 12], fill=(226, 222, 206, 255))


# ---------------------------------------------------------------- meble


def regal():
    """Metalowy regał z segregatorami i kartonem (zamiast biblioteczki)."""
    P = [('metal', plain((112, 116, 118), 6, 3)), ('segregatory', binders), ('karton', label_box),
         ('ciemny', plain((52, 54, 56), 3))]
    parts = []
    for x in (0, 15):
        for z in (0, 15):
            parts.append(([x, 0, z], [x + 1, 16, z + 1], 'metal'))
    for y in (0, 7.5, 15):
        parts.append(([0, y, 0], [16, y + 1, 16], 'metal'))
    parts.append(([1, 1, 1], [15, 7.5, 14.5], 'ciemny', {'south': 'segregatory'}))
    parts.append(([1, 8.5, 4], [9, 15, 14.5], 'ciemny', {'south': 'segregatory'}))
    parts.append(([9.5, 8.5, 5], [15, 13.5, 14.8], 'karton'))
    parts.append(([0.2, 1, 0], [15.8, 15, 0.4], 'ciemny'))
    model('regal', parts, P, 11)


def kartoteka():
    """Szafa kartotekowa z czterema szufladami, jedna wysunięta."""
    P = [('szuflady', drawers), ('blacha', plain((104, 112, 100), 4, 2)), ('papiery', plain((214, 210, 192), 6))]
    parts = [([1, 0, 1], [15, 16, 14], 'blacha', {'south': 'szuflady'}),
             ([2, 8.2, 8], [14, 11.6, 18], 'blacha', {'up': 'papiery'}),
             ([3, 11.6, 9], [13, 12.2, 17], 'papiery')]
    model('kartoteka', parts, P, 12)


def umywalka():
    """Ceramiczna umywalka na nodze z kranem (zamiast kotła)."""
    P = [('ceramika', plain((222, 222, 214), 4)), ('misa', ceramic_bowl), ('kran', tap),
         ('rura', plain((150, 152, 150), 6, 2))]
    parts = [([2, 9, 3], [14, 13, 15], 'ceramika', {'up': 'misa'}),
             ([6, 0, 7], [10, 9, 11], 'ceramika'),
             ([7.3, 13, 3.5], [8.7, 16, 5], 'kran'),
             ([7.3, 14.6, 5], [8.7, 15.6, 8], 'kran'),
             ([7, 6, 0], [9, 7, 7], 'rura')]
    model('umywalka', parts, P, 13)


def warsztat():
    """Stół warsztatowy z imadłem i tablicą narzędzi (zamiast stołu rzemieślniczego)."""
    P = [('blat', wood_top), ('noga', plain((70, 72, 74), 4, 3)), ('narzedzia', tools),
         ('imadlo', plain((60, 90, 140), 6, 2)), ('szuflada', plain((96, 74, 50), 5))]
    parts = [([0, 10, 0], [16, 12, 16], 'blat'),
             ([1, 0, 1], [3, 10, 3], 'noga'), ([13, 0, 1], [15, 10, 3], 'noga'),
             ([1, 0, 13], [3, 10, 15], 'noga'), ([13, 0, 13], [15, 10, 15], 'noga'),
             ([1, 2, 2], [15, 3, 14], 'szuflada'),
             ([0.5, 12, 0], [15.5, 16, 1], 'szuflada', {'south': 'narzedzia'}),
             ([10, 12, 10], [14, 14.5, 15], 'imadlo'),
             ([11.5, 12.5, 15], [12.5, 13.5, 16.5], 'noga'),
             ([3, 12, 6], [8, 12.6, 9], 'noga')]
    model('warsztat', parts, P, 14)


def kuchenka():
    """Stara kuchenka gazowa z piekarnikiem (zamiast wędzarni)."""
    P = [('emalia', plain((214, 210, 196), 4, 3)), ('przod', enamel_front), ('palniki', burners),
         ('ruszt', plain((40, 40, 42), 3))]
    parts = [([1, 0, 1], [15, 13, 15], 'emalia', {'south': 'przod', 'up': 'palniki'}),
             ([1, 13, 1], [15, 16, 2], 'emalia'),
             ([2, 13, 3], [7, 13.5, 8], 'ruszt'), ([9, 13, 3], [14, 13.5, 8], 'ruszt'),
             ([2, 13, 9], [7, 13.5, 14], 'ruszt'), ([9, 13, 9], [14, 13.5, 14], 'ruszt')]
    model('kuchenka', parts, P, 15)


def piecyk():
    """Żeliwny piecyk koza z rurą (zamiast pieca)."""
    P = [('zeliwo', plain((52, 50, 50), 5, 4)), ('drzwiczki', cast_iron_door), ('rura', plain((66, 64, 62), 5, 3))]
    parts = [([3, 2, 3], [13, 11, 14], 'zeliwo', {'south': 'drzwiczki'}),
             ([2, 11, 2], [14, 12, 15], 'zeliwo'),
             ([3, 0, 3], [4, 2, 4], 'zeliwo'), ([12, 0, 3], [13, 2, 4], 'zeliwo'),
             ([3, 0, 13], [4, 2, 14], 'zeliwo'), ([12, 0, 13], [13, 2, 14], 'zeliwo'),
             ([6.5, 12, 5.5], [9.5, 16, 8.5], 'rura')]
    model('piecyk', parts, P, 16)


def radiostacja():
    """Wojskowa radiostacja na skrzynce ze słuchawką i anteną (zamiast obserwatora)."""
    P = [('panel', radio_panel), ('oliwka', plain((78, 90, 58), 5, 2)), ('czarny', plain((32, 32, 34), 3)),
         ('skrzynka', plain((96, 84, 58), 5))]
    parts = [([1, 0, 2], [15, 6, 14], 'skrzynka'),
             ([2, 6, 3], [14, 14, 13], 'oliwka', {'south': 'panel'}),
             ([12, 14, 6], [12.6, 16, 6.6], 'czarny'),
             ([3, 14, 5], [9, 15, 8], 'czarny'),
             ([2.5, 14, 9], [7.5, 15.5, 11], 'czarny')]
    model('radiostacja', parts, P, 17)


MEBLE = ['regal', 'kartoteka', 'umywalka', 'warsztat', 'kuchenka', 'piecyk', 'radiostacja']

if __name__ == '__main__':
    for fn in (regal, kartoteka, umywalka, warsztat, kuchenka, piecyk, radiostacja):
        fn()
    print('ok', MEBLE)
