#!/usr/bin/env python3
"""Model zrzutu (skrzynia ze spadochronem) dla AXON-Structure.

Zapisuje build/zrzut.json, build/zrzut.png i build/zrzut_item.json.
Plugin stawia beczkę (prawdziwy pojemnik) i na niej wyświetlacz przedmiotu z tym modelem,
lekko większym od bloku, więc beczki nie widać, a kliknięcie dalej ją otwiera.
"""
import json, os, random
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'build')
TEX = 'axon:item/zrzut'

# Obszary tekstury 64x64 w jednostkach uv (1 uv = 4 px).
R = {
    'bok':    (0, 0, 8, 8),
    'wieko':  (8, 0, 16, 8),
    'metal':  (0, 8, 4, 12),
    'czasza': (4, 8, 8, 12),
    'pas':    (8, 8, 12, 12),
    'lampa':  (12, 8, 16, 12),
    'plozy':  (0, 12, 4, 16),
}


def texture():
    rnd = random.Random(7)
    im = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    def noise(box, base, amp):
        x1, y1, x2, y2 = box
        for y in range(y1, y2):
            for x in range(x1, x2):
                k = rnd.randint(-amp, amp)
                im.putpixel((x, y), tuple(max(0, min(255, c + k)) for c in base) + (255,))

    # bok: oliwkowa sklejka z ramą, żółto-czarny pas ostrzegawczy i biały znak spadochronu
    noise((0, 0, 32, 32), (86, 96, 52), 6)
    for y in (8, 16, 24):
        d.line([(1, y), (30, y)], fill=(70, 78, 42))
    d.rectangle([0, 0, 31, 31], outline=(52, 58, 32))
    d.rectangle([1, 1, 30, 30], outline=(104, 114, 64))
    for x in range(1, 31):
        for y in range(25, 30):
            im.putpixel((x, y), (222, 182, 40, 255) if ((x + y) // 3) % 2 == 0 else (30, 30, 30, 255))
    d.pieslice([10, 5, 22, 15], 180, 360, fill=(232, 232, 226))
    for x0 in (11, 16, 21):
        d.line([(x0, 10), (16, 19)], fill=(232, 232, 226))
    d.rectangle([15, 19, 17, 21], fill=(232, 232, 226))

    # wieko: ciemniejsze, z blachą antypoślizgową
    noise((32, 0, 64, 32), (66, 74, 40), 5)
    d.rectangle([32, 0, 63, 31], outline=(44, 50, 28))
    for y in range(3, 30, 4):
        for x in range(34 + (y // 4) % 2 * 2, 62, 4):
            d.line([(x, y), (x + 1, y)], fill=(90, 100, 56))

    # metal: okucia z nitami
    noise((0, 32, 16, 48), (118, 122, 126), 8)
    d.rectangle([0, 32, 15, 47], outline=(70, 72, 76))
    for p in ((3, 35), (12, 35), (3, 44), (12, 44), (7, 40)):
        d.point(p, fill=(190, 194, 198))

    # czasza: złożony pomarańczowy spadochron z fałdami
    noise((16, 32, 32, 48), (214, 98, 34), 7)
    for x in (19, 23, 27, 30):
        d.line([(x, 32), (x - 1, 47)], fill=(170, 70, 22))
    d.line([(16, 39), (31, 40)], fill=(240, 236, 228))

    # pas: czarna taśma z klamrą
    noise((32, 32, 48, 48), (34, 34, 36), 4)
    d.line([(33, 32), (33, 47)], fill=(56, 56, 60))
    d.line([(46, 32), (46, 47)], fill=(56, 56, 60))
    d.rectangle([35, 37, 44, 42], outline=(170, 170, 160))

    # lampa: czerwony sygnał
    noise((48, 32, 64, 48), (230, 40, 30), 10)
    d.ellipse([51, 35, 60, 44], fill=(255, 150, 120))

    # płozy: drewno
    noise((0, 48, 16, 64), (112, 80, 48), 8)
    for y in (52, 57, 61):
        d.line([(0, y), (15, y)], fill=(86, 60, 34))
    return im


def faces(region, skip=()):
    uv = list(R[region])
    return {f: {'uv': uv, 'texture': '#t'} for f in ('north', 'south', 'east', 'west', 'up', 'down') if f not in skip}


def box(f, t, region, skip=(), **kw):
    e = {'from': f, 'to': t, 'faces': faces(region, skip)}
    e.update(kw)
    return e


def model():
    el = []
    # skrzynia lekko większa od bloku, żeby zakryć beczkę
    body = box([-0.25, 1.5, -0.25], [16.25, 15.5, 16.25], 'bok', skip=('up', 'down'))
    el.append(body)
    el.append(box([-0.75, 15.5, -0.75], [16.75, 17, 16.75], 'wieko'))
    el.append(box([-0.5, 1, -0.5], [16.5, 1.5, 16.5], 'metal'))
    # narożniki z blachy
    for x in (-0.75, 14.75):
        for z in (-0.75, 14.75):
            el.append(box([x, 1, z], [x + 2, 15.5, z + 2], 'metal'))
    # płozy
    for z in (1.5, 12.5):
        el.append(box([-1, 0, z], [17, 1, z + 2], 'plozy'))
    # złożony spadochron na wieku
    el.append(box([3, 17, 3.5], [13, 20.5, 12.5], 'czasza', skip=('down',)))
    el.append(box([4, 20.5, 4.5], [12, 21.5, 11.5], 'czasza', skip=('down',)))
    # pasy mocujące spadochron
    el.append(box([7, 17, 2.75], [9, 21.75, 13.25], 'pas', skip=('down',)))
    el.append(box([2.25, 17, 7], [13.75, 20.75, 9], 'pas', skip=('down',)))
    # lampa sygnałowa w rogu wieka, świeci w ciemności
    el.append(box([13, 17, 13], [15, 19, 15], 'lampa', skip=('down',), light_emission=15))
    return {
        'textures': {'t': TEX, 'particle': TEX},
        'elements': el,
        'display': {
            'fixed': {'rotation': [0, 0, 0], 'translation': [0, 0, 0], 'scale': [1, 1, 1]},
            'gui': {'rotation': [30, 225, 0], 'translation': [0, -1.5, 0], 'scale': [0.5, 0.5, 0.5]},
            'ground': {'rotation': [0, 0, 0], 'translation': [0, 2, 0], 'scale': [0.3, 0.3, 0.3]},
            'head': {'rotation': [0, 0, 0], 'translation': [0, 0, 0], 'scale': [1, 1, 1]},
        },
    }


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    texture().save(os.path.join(OUT, 'zrzut.png'))
    json.dump(model(), open(os.path.join(OUT, 'zrzut.json'), 'w'), indent=1)
    json.dump({'model': {'type': 'minecraft:model', 'model': 'axon:block/zrzut'}},
              open(os.path.join(OUT, 'zrzut_item.json'), 'w'), indent=1)
    print('ok')
