#!/usr/bin/env python3
"""Rekwizyt do struktury zajezdnia (AXON-Structure): opuszczona spalinowa lokomotywa manewrowa.

Zapisuje do build/: lokomotywa.json (model), lokomotywa.png (tekstura), lokomotywa_item.json (przedmiot).

Lokomotywa opisana jest w kratkach: lx w poprzek toru (-1.5..1.5, środek toru = 0), ly w górę od spodu
kratki, w której leżą szyny, lz wzdłuż toru (0..14, krótka maska na lz 0). 1 kratka = F jednostek modelu,
plugin rysuje model ze skalą 16 / F, a środek modelu (8 8 8) to punkt lx 0, ly 2.5, lz 7.

Kolizję w strukturze dają bariery (RailDepotStructure.locomotive w AXON-Structure):
  warstwa szyn+1 (ly 1-2): cała rama, 3 kolumny, lz 0-13,
  warstwy +2 i +3: maski 3 kolumny (lz 0-2 i 6-13), kabina tylko boczne ściany w lz 3 i 5,
  w lz 4 drzwi po obu stronach (stopień: bariera w warstwie szyn obok toru),
  warstwa +4: dach kabiny (lz 3-5).
Ściany kabiny leżą w kratkach barier, środek kabiny (kolumna 0, lz 3-5) jest pusty i da się do niego wejść.
"""
import json, os, random
from PIL import Image, ImageDraw

from gen_rekwizyty import noise, stains, FACES

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'build')

F = 3.0
SCALE = 16 / F

W = {  # obszary tekstury 128x128 w uv (1 uv = 8 px)
    'maska': (0, 0, 12, 3), 'kabina': (0, 3, 6, 6), 'czolo_kab': (6, 3, 10, 6), 'czolo': (10, 3, 14, 6),
    'pomar': (12, 0, 14, 2), 'krem': (14, 0, 16, 2), 'dach': (0, 6, 8, 8), 'rama': (8, 6, 12, 7),
    'zolty': (8, 7, 12, 8), 'kolo': (12, 6, 14, 8), 'metal': (14, 6, 16, 8), 'wnetrze': (0, 8, 4, 10),
    'pulpit': (4, 8, 6, 10), 'szyba': (6, 8, 8, 10), 'lampa': (8, 8, 9, 9), 'czarny': (9, 8, 10, 9),
    'krata': (10, 8, 14, 10), 'drzwi': (14, 2, 16, 6), 'stopien': (8, 9, 10, 10),
}

ORANGE = (196, 92, 38)
CREAM = (214, 200, 160)


def graffiti(d, box, rnd, n):
    x1, y1, x2, y2 = box
    for _ in range(n):
        c = rnd.choice([(40, 120, 200), (40, 40, 40), (200, 40, 160), (90, 180, 70), (230, 230, 230)])
        x, y = rnd.randint(x1, x2 - 14), rnd.randint(y1, y2 - 6)
        pts = [(x + i * 2, y + rnd.randint(0, 5)) for i in range(7)]
        d.line(pts, fill=c + (255,), width=2)


def rust(im, box, rnd, n):
    d = ImageDraw.Draw(im)
    x1, y1, x2, y2 = box
    for _ in range(n):
        x, y = rnd.randint(x1, x2 - 1), rnd.randint(y1, y2 - 1)
        ln = rnd.randint(2, 7)
        d.line([(x, y), (x, min(y2 - 1, y + ln))], fill=(120, 64, 30, 255))


def texture():
    rnd = random.Random(42)
    im = Image.new('RGBA', (128, 128), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # bok maski: pomarańcz, kremowy pas, żaluzje, rdza i graffiti
    noise(im, (0, 0, 96, 24), ORANGE, 7, rnd)
    noise(im, (0, 15, 96, 19), CREAM, 5, rnd)
    for x in range(6, 90, 14):
        d.rectangle([x, 3, x + 9, 11], fill=(150, 70, 30, 255))
        for y in range(4, 11, 2):
            d.line([(x + 1, y), (x + 8, y)], fill=(70, 40, 24, 255))
    for x in range(0, 96, 24):
        d.line([(x, 0), (x, 23)], fill=(150, 66, 28, 255))
    rust(im, (0, 0, 96, 24), rnd, 40)
    stains(im, (0, 18, 96, 24), (90, 70, 50, 255), 14, rnd, 2)
    graffiti(d, (20, 10, 90, 22), rnd, 4)
    # bok kabiny: kremowa góra z oknem, pomarańczowy dół
    noise(im, (0, 24, 48, 48), CREAM, 5, rnd)
    noise(im, (0, 38, 48, 48), ORANGE, 6, rnd)
    d.rectangle([6, 27, 41, 35], fill=(46, 58, 62, 255), outline=(60, 56, 50, 255))
    d.line([(23, 27), (23, 35)], fill=(60, 56, 50, 255), width=2)
    d.line([(9, 28), (14, 33)], fill=(150, 170, 176, 255))
    rust(im, (0, 36, 48, 48), rnd, 12)
    # czoło kabiny: dwie szyby
    noise(im, (48, 24, 80, 48), CREAM, 5, rnd)
    noise(im, (48, 40, 80, 48), ORANGE, 6, rnd)
    d.rectangle([51, 27, 63, 36], fill=(46, 58, 62, 255), outline=(60, 56, 50, 255))
    d.rectangle([66, 27, 77, 36], fill=(46, 58, 62, 255), outline=(60, 56, 50, 255))
    d.line([(68, 29), (75, 35)], fill=(20, 24, 26, 255))               # pęknięta szyba
    d.line([(73, 28), (69, 34)], fill=(20, 24, 26, 255))
    # czoło maski: krata, reflektory, tabliczka z numerem
    noise(im, (80, 24, 112, 48), ORANGE, 6, rnd)
    noise(im, (80, 42, 112, 48), CREAM, 5, rnd)
    d.rectangle([86, 27, 105, 37], fill=(70, 40, 24, 255))
    for y in range(28, 37, 2):
        d.line([(87, y), (104, y)], fill=(110, 60, 30, 255))
    d.ellipse([82, 40, 86, 44], fill=(230, 220, 150, 255))
    d.ellipse([105, 40, 109, 44], fill=(90, 90, 80, 255))               # wybity reflektor
    d.rectangle([91, 39, 100, 41], fill=(40, 40, 40, 255))
    for x in (92, 95, 98):
        d.point((x, 40), fill=(220, 220, 200, 255))
    # jednolite kolory
    noise(im, (96, 0, 112, 16), ORANGE, 6, rnd)
    rust(im, (96, 0, 112, 16), rnd, 6)
    noise(im, (112, 0, 128, 16), CREAM, 5, rnd)
    # drzwi kabiny: kremowe z okienkiem i klamką
    noise(im, (112, 16, 128, 48), CREAM, 5, rnd)
    noise(im, (112, 38, 128, 48), ORANGE, 6, rnd)
    d.rectangle([114, 19, 125, 28], fill=(46, 58, 62, 255))
    d.line([(123, 33), (125, 33)], fill=(40, 40, 40, 255))
    # dach: szara blacha, sadza przy wydechu
    noise(im, (0, 48, 64, 64), (104, 104, 100), 6, rnd)
    stains(im, (20, 48, 50, 64), (40, 38, 36, 255), 12, rnd, 4)
    for x in range(0, 64, 8):
        d.line([(x, 48), (x, 63)], fill=(86, 86, 84, 255))
    # rama, żółto-czarne pasy, koło, metal
    noise(im, (64, 48, 96, 56), (36, 34, 32), 4, rnd)
    rust(im, (64, 48, 96, 56), rnd, 8)
    for x in range(64, 96):
        for y in range(56, 64):
            c = (210, 170, 30) if ((x + y) // 4) % 2 == 0 else (30, 30, 30)
            im.putpixel((x, y), c + (255,))
    noise(im, (96, 48, 112, 64), (40, 38, 36), 4, rnd)
    d.ellipse([97, 49, 110, 62], outline=(120, 110, 100, 255), width=2)
    d.ellipse([102, 54, 105, 57], fill=(130, 120, 110, 255))
    noise(im, (112, 48, 128, 64), (120, 118, 112), 7, rnd)
    rust(im, (112, 48, 128, 64), rnd, 6)
    # wnętrze kabiny, pulpit, szyba, lampa, czarny, krata
    noise(im, (0, 64, 32, 80), (176, 168, 140), 5, rnd)
    stains(im, (0, 64, 32, 80), (120, 110, 90, 255), 6, rnd, 2)
    noise(im, (32, 64, 48, 80), (70, 84, 80), 4, rnd)
    for x, y, c in ((35, 67, (200, 40, 30)), (40, 67, (40, 160, 60)), (44, 70, (220, 200, 60))):
        d.rectangle([x, y, x + 2, y + 2], fill=c + (255,))
    d.ellipse([36, 72, 42, 78], fill=(220, 220, 210, 255), outline=(20, 20, 20, 255))
    noise(im, (48, 64, 64, 80), (52, 66, 70), 5, rnd)
    im.paste((236, 228, 170, 255), (64, 64, 72, 72))
    noise(im, (72, 64, 80, 72), (24, 24, 24), 3, rnd)
    noise(im, (80, 64, 112, 80), (60, 40, 28), 4, rnd)
    for y in range(65, 80, 3):
        d.line([(80, y), (111, y)], fill=(100, 56, 28, 255))
    noise(im, (64, 72, 80, 80), (70, 70, 66), 5, rnd)                  # stopień: blacha ryflowana
    for x in range(65, 80, 3):
        d.line([(x, 73), (x + 1, 78)], fill=(110, 110, 104, 255))
    return im


def to_model(v, axis):
    off = (0.0, 2.5, 7.0)[axis]
    return round(8 + (v - off) * F, 4)


def el(f, t, region, special=None, skip=(), rot=None):
    """Element w kratkach (lx, ly, lz); special = {kierunek: obszar} dla wybranych ścian."""
    special = special or {}
    e = {'from': [to_model(f[i], i) for i in range(3)], 'to': [to_model(t[i], i) for i in range(3)],
         'faces': {fc: {'uv': list(W[special.get(fc, region)]), 'texture': '#t'} for fc in FACES if fc not in skip}}
    if rot:
        axis, angle, origin = rot
        e['rotation'] = {'axis': axis, 'angle': angle, 'origin': [to_model(origin[i], i) for i in range(3)]}
    return e


def model():
    E = []
    side = {'east': 'maska', 'west': 'maska'}
    # wózki: dwa po dwie osie, koła po obu stronach, rama wózka
    for c in (2.6, 11.4):
        for a in (c - 0.9, c + 0.9):
            for x in (-0.95, 0.75):
                E.append(el([x, 0.1, a - 0.45], [x + 0.2, 1.0, a + 0.45], 'kolo', {'up': 'czarny', 'down': 'czarny'}))
        for x in (-1.2, 0.95):
            E.append(el([x, 0.7, c - 1.6], [x + 0.25, 1.3, c + 1.6], 'rama'))
            for a in (c - 0.9, c + 0.9):          # maźnice
                E.append(el([x - 0.02, 0.4, a - 0.2], [x + 0.27, 0.7, a + 0.2], 'metal'))
        E.append(el([-0.95, 0.9, c - 0.4], [0.95, 1.3, c + 0.4], 'czarny'))
    # zbiornik paliwa między wózkami
    E.append(el([-1.1, 0.5, 5.0], [1.1, 1.3, 9.0], 'rama', {'east': 'czarny', 'west': 'czarny'}))
    # rama główna z pomostem i belki zderzakowe w pasy
    E.append(el([-1.5, 1.3, 0.3], [1.5, 2.0, 13.7], 'rama', {'up': 'metal'}))
    E.append(el([-1.55, 1.15, 0.0], [1.55, 1.95, 0.3], 'zolty'))
    E.append(el([-1.55, 1.15, 13.7], [1.55, 1.95, 14.0], 'zolty'))
    # zderzaki, sprzęg
    for z0, z1 in ((-0.5, 0.0), (14.0, 14.5)):
        for x in (-1.1, 0.7):
            E.append(el([x, 1.35, z0], [x + 0.4, 1.75, z1], 'metal'))
        E.append(el([-0.15, 1.3, min(z0, z1) + (0.15 if z0 < 0 else 0)], [0.15, 1.5, max(z0, z1) - (0 if z0 < 0 else 0.15)], 'czarny'))
    # krótka maska (lz 0.5-3.0)
    E.append(el([-0.95, 2.0, 0.5], [0.95, 3.6, 3.0], 'maska', {'north': 'czolo', 'up': 'dach', 'south': 'pomar'}))
    E.append(el([-0.9, 3.6, 0.6], [0.9, 3.8, 2.9], 'dach'))
    # kabina (lz 3.0-6.0): ściany boczne z drzwiami w lz 4.0-5.0, ściany czołowe, dach
    for x0, x1, fin in ((-1.5, -1.4, 'east'), (1.4, 1.5, 'west')):
        out = 'west' if fin == 'east' else 'east'
        E.append(el([x0, 2.0, 3.0], [x1, 4.0, 4.0], 'kabina', {fin: 'wnetrze', 'up': 'krem', 'down': 'krem'}))
        E.append(el([x0, 2.0, 5.0], [x1, 4.0, 6.0], 'kabina', {fin: 'wnetrze', 'up': 'krem', 'down': 'krem'}))
        E.append(el([x0, 3.75, 4.0], [x1, 4.0, 5.0], 'krem', {fin: 'wnetrze'}))
        # drzwi odchylone na zawiasie przy lz 5.0 (jedne otwarte szeroko, drugie uchylone)
        ang = -45 if out == 'west' else 22.5
        xo = x0 - 0.1 if out == 'west' else x1
        E.append(el([xo, 2.05, 4.05], [xo + 0.1, 3.7, 4.95], 'drzwi', rot=('y', ang, (xo, 3.0, 4.95))))
        # stopnie pod drzwiami (bariera w warstwie szyn obok toru)
        sx = -1.5 if out == 'west' else 1.1
        E.append(el([sx + (0 if out == 'west' else 0), 0.85, 4.1], [sx + 0.4, 1.0, 4.9], 'stopien'))
        E.append(el([sx, 0.2, 4.1], [sx + 0.4, 0.3, 4.9], 'stopien'))
        hx = -1.65 if out == 'west' else 1.55
        E.append(el([hx, 2.1, 3.95], [hx + 0.1, 3.6, 4.05], 'metal'))       # poręcze przy drzwiach
        E.append(el([hx, 2.1, 4.95], [hx + 0.1, 3.6, 5.05], 'metal'))
    E.append(el([-1.4, 2.0, 3.0], [1.4, 4.0, 3.1], 'czolo_kab', {'south': 'wnetrze'}))
    E.append(el([-1.4, 2.0, 5.9], [1.4, 4.0, 6.0], 'czolo_kab', {'north': 'wnetrze'}))
    E.append(el([-1.6, 4.0, 2.9], [1.6, 4.35, 6.1], 'dach', {'down': 'wnetrze'}))
    E.append(el([-0.4, 4.35, 4.1], [0.4, 4.55, 4.9], 'lampa', {'up': 'metal'}))  # syrena / kogut
    # wnętrze: podłoga i pulpit pod przednią szybą, fotel
    E.append(el([-1.4, 2.0, 3.1], [1.4, 2.05, 5.9], 'wnetrze'))
    E.append(el([-1.3, 2.9, 3.1], [1.3, 3.1, 3.7], 'pulpit', {'up': 'pulpit'}))
    E.append(el([0.3, 2.05, 4.9], [0.9, 2.5, 5.5], 'czarny'))
    E.append(el([0.3, 2.5, 5.4], [0.9, 3.2, 5.55], 'czarny'))
    # długa maska (lz 6.0-13.5)
    E.append(el([-0.95, 2.0, 6.0], [0.95, 3.6, 13.5], 'maska', {'south': 'czolo', 'up': 'dach', 'north': 'pomar'}))
    E.append(el([-0.9, 3.6, 6.2], [0.9, 3.8, 13.3], 'dach'))
    E.append(el([-0.6, 3.8, 7.2], [0.6, 3.95, 12.0], 'krata', {'up': 'krata'}))  # wentylator chłodnicy
    E.append(el([-0.2, 3.8, 6.6], [0.2, 4.6, 7.0], 'czarny'))                    # wydech
    # reflektory na obu czołach
    for z0, z1 in ((0.42, 0.5), (13.5, 13.58)):
        E.append(el([-0.25, 3.2, z0], [0.25, 3.5, z1], 'lampa'))
        for x in (-1.3, 1.0):
            E.append(el([x, 1.95, z0 - 0.3], [x + 0.3, 2.2, z1 + 0.3 if z0 > 1 else z1], 'lampa'))
    # poręcze wzdłuż masek
    for x in (-1.4, 1.35):
        E.append(el([x, 2.85, 6.2], [x + 0.05, 2.95, 13.4], 'metal'))
        E.append(el([x, 2.85, 0.6], [x + 0.05, 2.95, 2.9], 'metal'))
    return {'textures': {'t': 'axon:item/lokomotywa', 'particle': 'axon:item/lokomotywa'}, 'elements': E}


def write():
    os.makedirs(OUT, exist_ok=True)
    texture().save(os.path.join(OUT, 'lokomotywa.png'))
    m = model()
    for e in m['elements']:
        for v in e['from'] + e['to']:
            assert -16 <= v <= 32, ('poza zakresem modelu', e)
    json.dump(m, open(os.path.join(OUT, 'lokomotywa.json'), 'w'), indent=1)
    json.dump({'model': {'type': 'minecraft:model', 'model': 'axon:block/lokomotywa'}},
              open(os.path.join(OUT, 'lokomotywa_item.json'), 'w'), indent=1)
    return m


if __name__ == '__main__':
    m = write()
    print('lokomotywa: %d elementów, skala %.4f, środek modelu = lx 0, ly 2.5, lz 7' % (len(m['elements']), SCALE))
