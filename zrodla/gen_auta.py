#!/usr/bin/env python3
"""Rekwizyty do blokowiska (AXON-Structure): dwa porzucone samochody i kineskopowy telewizor.

Zapisuje do build/: <nazwa>.json (model), <nazwa>.png (tekstura), <nazwa>_item.json (przedmiot).

- axon:auto_sedan i axon:auto_sedan_spalony (ten sam model, wypalona tekstura): srebrny sedan,
- axon:auto_kombi: zielone kombi z relingami,
- axon:telewizor: telewizor z kineskopem, mebel jednej kratki (przód na południe, blok loom w strukturze).

Auta opisane są w kratkach: lx w poprzek (-1..1, środek = 0), ly w górę od spodu kratki, na której stoją koła,
lz wzdłuż auta (0..4, przód na lz 0). 1 kratka = F jednostek modelu, plugin rysuje model ze skalą 16 / F,
a środek modelu (8 8 8) to punkt lx 0, ly 0.75, lz 2. Kolizję w strukturze dają bariery 2 × 4 kratki
w dwóch warstwach nad gruntem, a w pliku .axs środek modelu to (x0 + 1, y + 0.75, z0 + 2) przy obrocie 0
(auto wzdłuż osi z) albo (x0 + 2, y + 0.75, z0 + 1) przy obrocie 90.
"""
import json, os, random
from PIL import Image, ImageDraw

from gen_rekwizyty import noise, stains, FACES

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'build')

F = 8.0
SCALE = 16 / F
OFF = (0.0, 0.75, 2.0)

W = {  # obszary tekstury 128x128 w uv (1 uv = 8 px)
    'bok': (0, 0, 16, 3), 'okna': (0, 3, 16, 5), 'maska': (0, 5, 6, 8), 'dach': (6, 5, 12, 8),
    'przod': (12, 5, 16, 7), 'tyl': (12, 7, 16, 9), 'szyba': (0, 8, 4, 10), 'opona': (4, 8, 6, 10),
    'felga': (6, 8, 8, 10), 'czarny': (8, 8, 9, 9), 'lakier': (9, 8, 10, 9), 'rdza': (10, 8, 11, 9),
    'zderzak': (11, 8, 12, 9), 'wnetrze': (8, 9, 12, 10), 'lampa': (12, 9, 13, 10), 'czerwona': (13, 9, 14, 10),
    'pustak': (14, 9, 16, 11), 'drzwi': (0, 10, 6, 13), 'inna': (6, 10, 8, 13), 'metal': (8, 10, 10, 11),
}

AUTA = {
    # nazwa: (kolor lakieru, model, wypalony)
    'auto_sedan': ((150, 156, 162), 'sedan', False),
    'auto_sedan_spalony': ((150, 156, 162), 'sedan', True),
    'auto_kombi': ((46, 84, 62), 'kombi', False),
}


def px(box):
    return tuple(v * 8 for v in box)


def rust(d, box, rnd, n, col=(122, 66, 34, 255)):
    x1, y1, x2, y2 = box
    for _ in range(n):
        x, y = rnd.randint(x1, x2 - 1), rnd.randint(y1, y2 - 1)
        r = rnd.randint(1, 3)
        d.ellipse([x - r, y - r, x + r, y + r], fill=col)
        d.line([(x, y), (x, min(y2 - 1, y + rnd.randint(2, 6)))], fill=col)


def window(d, box, rnd, broken=False, burnt=False):
    x1, y1, x2, y2 = box
    if burnt:
        d.rectangle(box, fill=(18, 16, 15, 255))
        return
    d.rectangle(box, fill=(40, 52, 58, 255))
    for i in range(3):                                  # brud i odblask
        d.line([(x1 + 2 + i * 5, y1 + 1), (x1 + 6 + i * 5, y2 - 1)], fill=(70, 86, 92, 255))
    if broken:
        cx, cy = rnd.randint(x1 + 3, x2 - 3), rnd.randint(y1 + 2, y2 - 2)
        d.ellipse([cx - 4, cy - 3, cx + 4, cy + 3], fill=(10, 10, 12, 255))
        for _ in range(7):
            d.line([(cx, cy), (rnd.randint(x1, x2), rnd.randint(y1, y2))], fill=(150, 165, 170, 255))


def texture(paint, burnt, seed):
    rnd = random.Random(seed)
    im = Image.new('RGBA', (128, 128), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if burnt:   # wypalony lakier: rdza, sadza, resztki farby
        base = (92, 54, 36)
        noise(im, (0, 0, 128, 104), base, 14, rnd)
        stains(im, (0, 0, 128, 104), (34, 30, 28, 255), 80, rnd, 6)
        stains(im, (0, 0, 128, 104), paint + (255,), 18, rnd, 3)
    else:
        noise(im, (0, 0, 128, 104), paint, 5, rnd)
    # bok: drzwi, klamki, listwa, nadkola, rdza, rysy
    b = px(W['bok'])
    for x in (34, 66, 96):
        d.line([(x, 1), (x, 21)], fill=(30, 30, 30, 255))
    for x in (54, 86):
        d.rectangle([x, 6, x + 4, 7], fill=(40, 40, 40, 255))
    d.rectangle([2, 13, 126, 15], fill=(44, 44, 46, 255))                       # listwa boczna
    for cx in (18, 110):
        d.ellipse([cx - 13, 12, cx + 13, 38], fill=(20, 20, 20, 255))           # nadkola
    rust(d, (0, 16, 128, 24), rnd, 7)
    if not burnt:
        for _ in range(5):
            x, y = rnd.randint(36, 120), rnd.randint(2, 12)
            d.line([(x, y), (x + rnd.randint(8, 20), y + rnd.randint(-2, 2))], fill=(210, 210, 210, 255))
        d.text((44, 1), 'XX', fill=(180, 40, 40, 255))                          # bazgroł sprayem
    # boczne szyby z słupkami
    o = px(W['okna'])
    d.rectangle([0, o[1], 127, o[3] - 1], fill=paint + (255,) if not burnt else (60, 40, 30, 255))
    window(d, (6, o[1] + 2, 60, o[3] - 2), rnd, broken=True, burnt=burnt)
    window(d, (66, o[1] + 2, 122, o[3] - 2), rnd, broken=rnd.random() < .5, burnt=burnt)
    # maska i dach: brud, liście, plamy po deszczu
    for k in ('maska', 'dach'):
        box = px(W[k])
        stains(im, box, (118, 112, 96, 255) if not burnt else (30, 28, 26, 255), 5, rnd, 2)
        rust(d, box, rnd, 2)
        for _ in range(6):
            x, y = rnd.randint(box[0], box[2] - 2), rnd.randint(box[1], box[3] - 2)
            d.rectangle([x, y, x + 1, y + 1], fill=(120, 96, 40, 255))
    # przód: atrapa, reflektory (jeden wybity), tablica
    p = px(W['przod'])
    d.rectangle(p, fill=(52, 52, 54, 255))
    d.rectangle([p[0] + 9, p[1] + 3, p[2] - 10, p[1] + 8], fill=(24, 24, 24, 255))
    for x in range(p[0] + 10, p[2] - 10, 2):
        d.line([(x, p[1] + 3), (x, p[1] + 8)], fill=(70, 70, 72, 255))
    d.rectangle([p[0] + 1, p[1] + 2, p[0] + 8, p[1] + 7], fill=(200, 200, 180, 255) if not burnt else (40, 36, 30, 255))
    d.rectangle([p[2] - 9, p[1] + 2, p[2] - 2, p[1] + 7], fill=(12, 12, 12, 255))
    d.rectangle([p[0] + 10, p[1] + 10, p[2] - 11, p[1] + 13], fill=(225, 225, 225, 255) if not burnt else (50, 46, 40, 255))
    # tył: lampy, tablica, klapa
    t = px(W['tyl'])
    d.rectangle(t, fill=paint + (255,) if not burnt else (70, 44, 32, 255))
    d.rectangle([t[0] + 1, t[1] + 2, t[0] + 8, t[1] + 7], fill=(170, 30, 26, 255) if not burnt else (30, 26, 24, 255))
    d.rectangle([t[2] - 9, t[1] + 2, t[2] - 2, t[1] + 7], fill=(14, 12, 12, 255))
    d.rectangle([t[0] + 10, t[1] + 9, t[2] - 11, t[1] + 12], fill=(225, 225, 225, 255) if not burnt else (50, 46, 40, 255))
    d.line([(t[0], t[1] + 1), (t[2], t[1] + 1)], fill=(30, 30, 30, 255))
    # przednia szyba z pajęczyną pęknięć
    s = px(W['szyba'])
    window(d, (s[0], s[1], s[2] - 1, s[3] - 1), rnd, broken=False, burnt=burnt)
    if not burnt:
        cx, cy = s[0] + 10, s[1] + 6
        for _ in range(10):
            d.line([(cx, cy), (rnd.randint(s[0], s[2]), rnd.randint(s[1], s[3]))], fill=(170, 185, 190, 255))
        d.ellipse([cx - 2, cy - 2, cx + 2, cy + 2], fill=(200, 210, 210, 255))
    # opona, felga i drobne kolory
    o = px(W['opona'])
    noise(im, o, (26, 26, 26), 4, rnd)
    for x in range(o[0], o[2], 3):
        d.line([(x, o[1]), (x, o[3] - 1)], fill=(14, 14, 14, 255))
    f = px(W['felga'])
    noise(im, f, (130, 130, 126) if not burnt else (70, 50, 40), 8, rnd)
    d.ellipse([f[0] + 3, f[1] + 3, f[2] - 4, f[3] - 4], fill=(70, 70, 70, 255))
    for k, c, a in (('czarny', (20, 20, 20), 3), ('lakier', paint, 4), ('rdza', (120, 64, 32), 10),
                    ('zderzak', (46, 46, 48), 5), ('lampa', (220, 210, 160), 6), ('czerwona', (170, 30, 26), 6),
                    ('metal', (150, 150, 146), 8)):
        noise(im, px(W[k]), c if not burnt or k in ('czarny', 'rdza') else (60, 46, 36), a, rnd)
    # wnętrze: szara tapicerka
    w = px(W['wnetrze'])
    noise(im, w, (70, 70, 74) if not burnt else (24, 22, 20), 8, rnd)
    # pustak pod autem bez koła
    pk = px(W['pustak'])
    noise(im, pk, (128, 126, 120), 12, rnd)
    d.rectangle([pk[0] + 2, pk[1] + 3, pk[0] + 6, pk[3] - 4], fill=(60, 60, 58, 255))
    d.rectangle([pk[0] + 9, pk[1] + 3, pk[0] + 13, pk[3] - 4], fill=(60, 60, 58, 255))
    # otwarte drzwi: zewnątrz i wnętrze tapicerki
    dr = px(W['drzwi'])
    noise(im, dr, paint if not burnt else (80, 50, 34), 5, rnd)
    window(d, (dr[0] + 2, dr[1] + 1, dr[2] - 3, dr[1] + 9), rnd, broken=True, burnt=burnt)
    rust(d, (dr[0], dr[1] + 12, dr[2], dr[3]), rnd, 5)
    # inna: drzwi z innego auta (czerwone, z demobilu)
    noise(im, px(W['inna']), (140, 40, 36) if not burnt else (70, 40, 30), 6, rnd)
    return im


def to_model(v, axis):
    return round(8 + (v - OFF[axis]) * F, 4)


def el(f, t, region, special=None, skip=(), rot=None):
    """Element w kratkach (lx, ly, lz); special = {kierunek: obszar} dla wybranych ścian."""
    special = special or {}
    e = {'from': [to_model(f[i], i) for i in range(3)], 'to': [to_model(t[i], i) for i in range(3)],
         'faces': {fc: {'uv': list(W[special.get(fc, region)]), 'texture': '#t'} for fc in FACES if fc not in skip}}
    if rot:
        axis, angle, origin = rot
        e['rotation'] = {'axis': axis, 'angle': angle, 'origin': [to_model(origin[i], i) for i in range(3)]}
    return e


def wheels(E, flat=(), missing=()):
    for i, (x0, z) in enumerate(((-0.92, 0.75), (0.72, 0.75), (-0.92, 3.25), (0.72, 3.25))):
        if i in missing:      # koło ukradzione, auto stoi na pustaku
            E.append(el([x0 + 0.02, 0.0, z - 0.3], [x0 + 0.22, 0.3, z + 0.3], 'pustak'))
            continue
        top = 0.45 if i in flat else 0.6
        E.append(el([x0, 0.0, z - 0.3], [x0 + 0.2, top, z + 0.3], 'opona',
                    {'east': 'felga', 'west': 'felga', 'up': 'czarny', 'down': 'czarny'}))


def sedan():
    E = []
    wheels(E, flat=(2,), missing=(1,))
    side = {'east': 'bok', 'west': 'bok', 'north': 'przod', 'south': 'tyl', 'up': 'maska', 'down': 'czarny'}
    E.append(el([-0.9, 0.25, 0.08], [0.9, 0.8, 3.92], 'bok', side))
    for z0, z1 in ((0.0, 0.08), (3.92, 4.0)):            # zderzaki
        E.append(el([-0.92, 0.25, z0], [0.92, 0.48, z1], 'zderzak'))
    # kabina z szybami, słupki w teksturze
    E.append(el([-0.82, 0.8, 1.85], [0.82, 1.42, 2.95], 'okna',
                {'north': 'wnetrze', 'south': 'wnetrze', 'up': 'dach', 'down': 'wnetrze'}))
    # przednia szyba pochylona do tyłu, tylna do przodu
    E.append(el([-0.8, 0.8, 1.6], [0.8, 1.48, 1.65], 'szyba', {'south': 'wnetrze'}, rot=('x', 22.5, (0, 0.8, 1.6))))
    E.append(el([-0.8, 0.8, 3.2], [0.8, 1.48, 3.25], 'szyba', {'north': 'wnetrze'}, rot=('x', -22.5, (0, 0.8, 3.25))))
    # maska uchylona (zamek puścił), pod nią pusta komora silnika
    E.append(el([-0.86, 0.8, 0.12], [0.86, 0.84, 1.55], 'maska', {'down': 'rdza'}, rot=('x', 22.5, (0, 0.8, 1.55))))
    E.append(el([-0.7, 0.8, 0.3], [0.7, 0.81, 1.4], 'rdza'))
    # lusterko zwisa na kablu, wycieraczki
    E.append(el([-1.02, 0.6, 1.7], [-0.92, 0.75, 1.82], 'czarny'))
    E.append(el([0.92, 0.95, 1.7], [1.02, 1.08, 1.82], 'czarny'))
    E.append(el([-0.6, 0.82, 1.5], [0.1, 0.85, 1.55], 'czarny'))
    # drzwi pasażera z innego auta
    E.append(el([0.9, 0.3, 1.9], [0.91, 0.78, 2.7], 'inna'))
    return E


def kombi():
    E = []
    wheels(E, flat=(0, 3))
    side = {'east': 'bok', 'west': 'bok', 'north': 'przod', 'south': 'tyl', 'up': 'maska', 'down': 'czarny'}
    E.append(el([-0.9, 0.25, 0.08], [0.9, 0.82, 3.92], 'bok', side))
    for z0, z1 in ((0.0, 0.08), (3.92, 4.0)):
        E.append(el([-0.92, 0.25, z0], [0.92, 0.48, z1], 'zderzak'))
    # długi dach do samego tyłu, tylna szyba pionowa
    E.append(el([-0.84, 0.82, 1.75], [0.84, 1.45, 3.9], 'okna',
                {'north': 'wnetrze', 'south': 'szyba', 'up': 'dach', 'down': 'wnetrze'}))
    E.append(el([-0.8, 0.82, 1.5], [0.8, 1.5, 1.55], 'szyba', {'south': 'wnetrze'}, rot=('x', 22.5, (0, 0.82, 1.5))))
    # relingi
    for x in (-0.7, 0.62):
        E.append(el([x, 1.45, 1.95], [x + 0.08, 1.52, 3.75], 'metal'))
    # otwarte przednie drzwi kierowcy (zawias z przodu)
    E.append(el([-0.95, 0.3, 1.75], [-0.9, 1.3, 2.75], 'drzwi', {'east': 'wnetrze'}, rot=('y', -45, (-0.9, 0.8, 1.75))))
    E.append(el([-0.9, 0.82, 1.75], [-0.89, 1.4, 2.75], 'wnetrze'))     # pusta rama okna
    # fotel widoczny przez drzwi
    E.append(el([-0.6, 0.6, 2.4], [-0.1, 0.95, 2.9], 'wnetrze'))
    E.append(el([-0.6, 0.95, 2.8], [-0.1, 1.35, 2.92], 'wnetrze'))
    # odpadnięty zderzak przedni z jednej strony
    E.append(el([0.5, 0.05, -0.05], [0.92, 0.25, 0.05], 'zderzak', rot=('z', -22.5, (0.92, 0.25, 0))))
    return E


# ---------------------------------------------------------------- telewizor

TW = {'obudowa': (0, 0, 8, 8), 'ekran': (8, 0, 16, 8), 'tyl': (0, 8, 8, 16), 'panel': (8, 8, 12, 12),
      'czarny': (12, 8, 14, 10), 'metal': (14, 8, 16, 10)}


def tv_texture():
    rnd = random.Random(77)
    im = Image.new('RGBA', (128, 128), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    noise(im, (0, 0, 64, 64), (58, 56, 54), 5, rnd)                  # ciemnoszary plastik
    stains(im, (0, 0, 64, 64), (90, 84, 70, 255), 10, rnd, 3)        # kurz
    noise(im, (0, 64, 64, 128), (48, 46, 44), 5, rnd)
    for y in range(70, 124, 6):                                       # kratka wentylacyjna z tyłu
        d.line([(10, y), (54, y)], fill=(24, 24, 24, 255), width=2)
    # ekran: wypukły kineskop, rozbity, w środku dziura do lampy
    noise(im, (64, 0, 128, 64), (34, 40, 40), 4, rnd)
    d.rectangle([64, 0, 127, 63], outline=(58, 56, 54, 255), width=4)
    d.ellipse([84, 18, 108, 42], fill=(6, 6, 8, 255))
    for _ in range(14):
        a, b = rnd.randint(68, 124), rnd.randint(4, 60)
        d.line([(96, 30), (a, b)], fill=(140, 156, 160, 255))
    d.line([(70, 8), (80, 14)], fill=(90, 110, 112, 255), width=2)   # odblask
    # panel z przyciskami i logo
    noise(im, (64, 64, 96, 96), (50, 48, 46), 4, rnd)
    for i in range(5):
        d.rectangle([68, 68 + i * 5, 74, 71 + i * 5], fill=(28, 28, 28, 255))
    d.ellipse([82, 70, 90, 78], fill=(30, 30, 30, 255), outline=(110, 110, 110, 255))
    d.rectangle([78, 86, 92, 89], fill=(150, 150, 150, 255))
    d.point((70, 92), fill=(200, 30, 30, 255))
    noise(im, (96, 64, 112, 80), (20, 20, 20), 3, rnd)
    noise(im, (112, 64, 128, 80), (160, 160, 156), 10, rnd)
    return im


def tel(f, t, region, special=None, rot=None):
    special = special or {}
    e = {'from': list(f), 'to': list(t),
         'faces': {fc: {'uv': list(TW[special.get(fc, region)]), 'texture': '#t'} for fc in FACES}}
    if rot:
        e['rotation'] = {'axis': rot[0], 'angle': rot[1], 'origin': list(rot[2])}
    return e


def telewizor():
    E = [tel([1.5, 0, 6], [14.5, 11, 15], 'obudowa', {'south': 'ekran'}),
         tel([3.5, 1, 1], [12.5, 10, 6], 'tyl', {'east': 'obudowa', 'west': 'obudowa'}),
         tel([5.5, 3, 0.5], [10.5, 8, 1], 'tyl'),
         tel([12, 1, 15], [14, 10, 15.3], 'panel'),                 # panel z przyciskami przy ekranie
         tel([2, 0, 6.5], [4, 0.6, 14.5], 'czarny'),                # nóżki
         tel([12, 0, 6.5], [14, 0.6, 14.5], 'czarny'),
         tel([7, 11, 9], [9, 11.6, 11], 'czarny'),                  # podstawka anteny
         tel([7.8, 11.4, 9.8], [8.3, 19, 10.3], 'metal', rot=('z', 22.5, (8, 11.4, 10))),
         tel([7.7, 11.4, 9.7], [8.2, 16, 10.2], 'metal', rot=('z', -45, (8, 11.4, 10)))]  # ucho zgięte
    return {'textures': {'t': 'axon:item/telewizor', 'particle': 'axon:item/telewizor'}, 'elements': E}


def save(name, model, tex):
    os.makedirs(OUT, exist_ok=True)
    tex.save(os.path.join(OUT, name + '.png'))
    for e in model['elements']:
        for v in e['from'] + e['to']:
            assert -16 <= v <= 32, ('poza zakresem modelu', name, e)
    json.dump(model, open(os.path.join(OUT, name + '.json'), 'w'), indent=1)
    json.dump({'model': {'type': 'minecraft:model', 'model': 'axon:block/' + name}},
              open(os.path.join(OUT, name + '_item.json'), 'w'), indent=1)


AUTA_I_TV = list(AUTA) + ['telewizor']


def write():
    for i, (name, (paint, kind, burnt)) in enumerate(AUTA.items()):
        E = sedan() if kind == 'sedan' else kombi()
        save(name, {'textures': {'t': 'axon:item/' + name, 'particle': 'axon:item/' + name}, 'elements': E},
             texture(paint, burnt, 10 + i))
        print('%s: %d elementów, skala %.1f' % (name, len(E), SCALE))
    save('telewizor', telewizor(), tv_texture())
    print('telewizor: mebel jednej kratki, przód na południe')


if __name__ == '__main__':
    write()
