"""Beczki: własny model i tekstury 128×128 (niebieska, paliwowa, zardzewiała, wersje rozbite, beczka vanilla).

Model nie ma nakładających się ścian (stara wersja z dwóch skrzyżowanych prostopadłościanów
miała dwa wieka na tej samej wysokości i migała). Korpus to pięć brył, które tylko się stykają:
środek 2..14 × 2..14 i cztery płaty po bokach, razem dwunastokąt. Obręcze to ten sam układ
powiększony o 0,25. Tekstura ma stałą gęstość 4 piksele na jednostkę modelu (64 na blok).

Układ tekstury (piksele): bok 48×64 w (0,0), wieko 56×56 w (64,0) dla x, z 1..15,
dno 32×32 w (0,64), wnętrze 32×32 w (32,64), obręcz 64×8 w (0,104), korek 16×16 w (96,104).
"""
import math
import random
from PIL import Image

from .stations import BLOCKLIKE
from .atlas import uv as atlas_uv

S = 4  # pikseli na jednostkę modelu


def _uv(x0, y0, x1, y1):
    return [round(x0 / 8, 4), round(y0 / 8, 4), round(x1 / 8, 4), round(y1 / 8, 4)]


SIDE, TOP, BOTTOM, INNER, RING, BUNG = (0, 0), (64, 0), (0, 64), (32, 64), (0, 104), (96, 104)

# ---------------------------------------------------------------- malowanie

VARIANTS = {
    'beczka': {'paint': (58, 98, 126), 'chip': (118, 124, 128), 'rust': 0.25},
    'beczka_paliwa': {'paint': (150, 48, 38), 'chip': (112, 116, 120), 'rust': 0.35, 'band': (212, 172, 60)},
    'beczka_rdza': {'paint': (128, 70, 38), 'chip': (84, 46, 26), 'rust': 1.0},
}

STEEL = (96, 100, 106)
RUST = (122, 64, 32)
def _mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _mul(c, f):
    return tuple(max(0, min(255, int(v * f))) for v in c)


def paint(name):
    v = VARIANTS[name]
    rnd = random.Random(name)
    img = Image.new('RGBA', (128, 128), (0, 0, 0, 0))
    px = img.load()
    paint_c = v['paint']

    # bok: walcowe cieniowanie, rąbki, przetłoczenia, odpryski, zacieki
    W, H = 48, 64
    side = [[paint_c for _ in range(W)] for _ in range(H)]
    hoops = (20, 42)
    for y in range(H):
        for x in range(W):
            c = paint_c
            if 'band' in v and 27 <= y <= 36:
                c = v['band']
            if v['rust'] >= 1.0:
                c = _mix(c, RUST, rnd.random() * 0.5)
            side[y][x] = _mul(c, 1 + rnd.uniform(-0.05, 0.05))
    if 'band' in v:   # czarne obrzeża żółtego pasa
        for x in range(W):
            side[27][x] = side[36][x] = (40, 36, 30)
    for _ in range(14 if v['rust'] < 1 else 9):   # odpryski farby: nieregularne plamy z kilku kół
        cx, cy = rnd.uniform(2, W - 2), rnd.uniform(6, H - 8)
        blobs = [(cx + rnd.uniform(-2, 2), cy + rnd.uniform(-1.5, 1.5), rnd.uniform(1.3, 2.8)) for _ in range(3)]
        inside = lambda x, y: any(math.hypot(x - bx, (y - by) * 1.3) < br for bx, by, br in blobs)
        for y in range(int(cy) - 6, int(cy) + 7):
            for x in range(int(cx) - 6, int(cx) + 7):
                if not (0 <= x < W and 0 <= y < H):
                    continue
                if inside(x, y):
                    side[y][x] = _mix(_mul(v['chip'], 1 + rnd.uniform(-0.06, 0.06)), RUST, rnd.random() * 0.35)
                elif inside(x - 1, y - 1):   # cień krawędzi farby od dołu i z prawej
                    side[y][x] = _mul(side[y][x], 0.78)
    for _ in range(int(16 * v['rust']) + 4):   # zacieki rdzy spod obręczy i rąbka
        x = rnd.randrange(W)
        y0 = rnd.choice((4,) + tuple(h + 3 for h in hoops))
        for y in range(y0, min(H - 4, y0 + rnd.randint(4, 14))):
            t = 0.55 * (1 - (y - y0) / 16)
            side[y][x] = _mix(side[y][x], RUST, t)
    for y in range(H - 12, H):   # błoto przy dnie
        for x in range(W):
            side[y][x] = _mix(side[y][x], (70, 58, 44), (y - (H - 12)) / 12 * 0.45)
    for y in range(H):
        for x in range(W):
            c = side[y][x]
            if y < 3 or y >= H - 3:   # rąbki
                c = _mul(STEEL, 1.25 if y in (0, H - 3) else 0.85)
            for h in hoops:   # przetłoczenia
                if y == h - 1:
                    c = _mul(c, 1.25)
                elif y == h + 1:
                    c = _mul(c, 0.6)
            f = 0.78 + 0.3 * math.sin(math.pi * (x + 0.5) / W)   # walec
            px[SIDE[0] + x, SIDE[1] + y] = _mul(c, f) + (255,)

    # wieko: zwinięty brzeg, przetłoczony pierścień, dwa korki, starta farba
    N = 56
    c0 = (N - 1) / 2
    big, small = (40, 16, 4.2), (15, 39, 3.0)
    for y in range(N):
        for x in range(N):
            d = math.hypot(x - c0, y - c0)
            if d >= 23:
                c = _mul(STEEL, 1.2 if 24 <= d < 25.5 else (0.75 if d >= 26.5 else 1.0))
            else:
                c = paint_c if v['rust'] < 1 else _mix(paint_c, RUST, rnd.random() * 0.6)
                if 15 <= d < 16:
                    c = _mul(c, 0.7)
                elif 16 <= d < 17:
                    c = _mul(c, 1.2)
                if d < 12 and rnd.random() < 0.10:   # wytarta farba na środku
                    c = _mix(c, v['chip'], 0.4)
            for bx, by, br in (big, small):
                db = math.hypot(x - bx, y - by)
                if db < br:
                    c = _mul(STEEL, 1.15 if db < br - 1.2 else 0.7)
                    if db < 1.3:
                        c = _mul(STEEL, 0.5)
            if rnd.random() < 0.04 * (1 + v['rust']):
                c = _mix(c, RUST, 0.6)
            px[TOP[0] + x, TOP[1] + y] = _mul(c, 1 + rnd.uniform(-0.05, 0.05)) + (255,)

    for y in range(32):   # dno i wnętrze
        for x in range(32):
            px[BOTTOM[0] + x, BOTTOM[1] + y] = _mul(STEEL, 0.7 + rnd.uniform(-0.06, 0.06)) + (255,)
            ic = (34, 30, 28) if rnd.random() > 0.15 else (80, 44, 26)
            px[INNER[0] + x, INNER[1] + y] = _mul(ic, 1 + rnd.uniform(-0.1, 0.1)) + (255,)
    for y in range(8):   # obręcz
        for x in range(64):
            f = (1.3, 1.1, 1.0, 1.0, 0.95, 0.9, 0.75, 0.6)[y]
            c = STEEL if rnd.random() > 0.12 * (1 + v['rust']) else RUST
            px[RING[0] + x, RING[1] + y] = _mul(c, f + rnd.uniform(-0.05, 0.05)) + (255,)
    for y in range(16):   # korek
        for x in range(16):
            d = math.hypot(x - 7.5, y - 7.5)
            f = 1.2 if d < 5 else 0.9
            px[BUNG[0] + x, BUNG[1] + y] = _mul(STEEL, f + rnd.uniform(-0.05, 0.05)) + (255,)
    return img


TEX = {name: paint(name) for name in VARIANTS}

# ---------------------------------------------------------------- model


class Barrel:
    """Model z jedną teksturą #b (tekstura beczki) i opcjonalnie #a (atlas, łup w rozbitej)."""

    def __init__(self, tex):
        self.tex = tex
        self.elements = []
        self.display = BLOCKLIKE

    def raw(self, frm, to, faces, rot=None):
        el = {'from': [round(c, 4) for c in frm], 'to': [round(c, 4) for c in to], 'faces': faces}
        if rot:
            el['rotation'] = rot
        self.elements.append(el)

    def atlas(self, frm, to, tile, **over):
        faces = {f: {'uv': atlas_uv(over.get(f, tile)), 'texture': '#a'} for f in
                 ('north', 'south', 'east', 'west', 'up', 'down')}
        self.raw(frm, to, faces, over.get('rot'))

    def json(self):
        textures = {'b': 'axon:item/' + self.tex, 'particle': 'axon:item/' + self.tex}
        if any(f['texture'] == '#a' for e in self.elements for f in e['faces'].values()):
            textures['a'] = 'axon:block/axoncore_atlas'
        out = {'textures': textures, 'elements': self.elements}
        if self.display:
            out['display'] = self.display
            out['gui_light'] = 'side'
        return out


def _side_uv(width, y0, y1):
    """Kawałek pasa bocznego: wyśrodkowany w poziomie, w pionie jak wysokość w modelu."""
    u0 = (12 - width) / 2 * S
    return _uv(SIDE[0] + u0, SIDE[1] + (16 - y1) * S, SIDE[0] + u0 + width * S, SIDE[1] + (16 - y0) * S)


def _top_uv(x0, z0, x1, z1):
    return _uv(TOP[0] + (x0 - 1) * S, TOP[1] + (z0 - 1) * S, TOP[0] + (x1 - 1) * S, TOP[1] + (z1 - 1) * S)


PIECES = ((2, 2, 14, 14), (1, 3, 2, 13), (14, 3, 15, 13), (3, 1, 13, 2), (3, 14, 13, 15))


def _body(m, y0, y1, up='top'):
    """Pięć stykających się brył od y0 do y1; up = 'top' (wieko) albo 'inner' (otwarte wnętrze)."""
    for x0, z0, x1, z1 in PIECES:
        faces = {}
        for f, w in (('north', x1 - x0), ('south', x1 - x0), ('east', z1 - z0), ('west', z1 - z0)):
            faces[f] = {'uv': _side_uv(w, y0, y1), 'texture': '#b'}
        if up == 'top':
            faces['up'] = {'uv': _top_uv(max(1, x0), max(1, z0), min(15, x1), min(15, z1)), 'texture': '#b'}
        elif up == 'inner':
            faces['up'] = {'uv': _uv(INNER[0], INNER[1], INNER[0] + 32, INNER[1] + 32), 'texture': '#b'}
        faces['down'] = {'uv': _uv(BOTTOM[0], BOTTOM[1], BOTTOM[0] + 32, BOTTOM[1] + 32), 'texture': '#b'}
        m.raw((x0, y0, z0), (x1, y1, z1), faces)


def _ring_uv(w):
    return _uv(RING[0], RING[1], RING[0] + min(64, w * S), RING[1] + 8)


def _hoop(m, y):
    """Obręcz: ten sam układ co korpus, powiększony o 0,25 i wysoki na 1."""
    for x0, z0, x1, z1 in PIECES:
        faces = {f: {'uv': _ring_uv(12), 'texture': '#b'} for f in ('north', 'south', 'east', 'west')}
        faces['up'] = faces['down'] = {'uv': _uv(RING[0], RING[1], RING[0] + 64, RING[1] + 2), 'texture': '#b'}
        m.raw((x0 - 0.25, y, z0 - 0.25), (x1 + 0.25, y + 1, z1 + 0.25), faces)


def _bung(m, x, z, r):
    """Korek wystający 0,4 nad wieko, w miejscu narysowanym na teksturze wieka."""
    full = _uv(BUNG[0], BUNG[1], BUNG[0] + 16, BUNG[1] + 16)
    edge = _uv(BUNG[0], BUNG[1], BUNG[0] + 16, BUNG[1] + 2)
    m.raw((x - r, 16, z - r), (x + r, 16.4, z + r),
          {'up': {'uv': full, 'texture': '#b'}, 'north': {'uv': edge, 'texture': '#b'},
           'south': {'uv': edge, 'texture': '#b'}, 'east': {'uv': edge, 'texture': '#b'},
           'west': {'uv': edge, 'texture': '#b'}})


def barrel(tex, open_=False):
    m = Barrel(tex)
    _body(m, 0, 16, up='inner' if open_ else 'top')
    for y in (4.5, 10.5):
        _hoop(m, y)
    if not open_:
        _bung(m, 1 + 40 / S, 1 + 16 / S, 0.9)
        _bung(m, 1 + 15 / S, 1 + 39 / S, 0.6)
    return m


def broken(tex):
    """Po rozbiciu: dolna połowa z poszarpanym brzegiem, wieko oparte o beczkę, łup w środku."""
    m = Barrel(tex)
    _body(m, 0, 7, up='inner')
    _hoop(m, 3.5)
    # poszarpany brzeg: cienkie kawałki blachy na krawędzi (bez nakładania na korpus)
    teeth = (((3, 1, 6, 2), 10.5), ((6, 1, 9, 2), 8.5), ((9, 1, 13, 2), 11.5),
             ((3, 14, 7, 15), 9), ((7, 14, 11, 15), 11), ((11, 14, 13, 15), 8),
             ((1, 3, 2, 8), 9.5), ((1, 8, 2, 13), 8), ((14, 3, 15, 7), 8.5), ((14, 7, 15, 13), 10.5))
    for (x0, z0, x1, z1), h in teeth:
        faces = {f: {'uv': _side_uv(min(12, max(x1 - x0, z1 - z0)), 7, h), 'texture': '#b'}
                 for f in ('north', 'south', 'east', 'west')}
        faces['up'] = {'uv': _uv(RING[0], RING[1], RING[0] + 16, RING[1] + 2), 'texture': '#b'}
        m.raw((x0, 7, z0), (x1, h, z1), faces)
    # wieko na ziemi, oparte o bok
    lid_top = _top_uv(3, 3, 13, 13)
    edge = _uv(RING[0], RING[1], RING[0] + 40, RING[1] + 3)
    m.raw((-6, 0, 3), (4, 0.75, 13), {'up': {'uv': lid_top, 'texture': '#b'},
                                       'down': {'uv': _uv(BOTTOM[0], BOTTOM[1], BOTTOM[0] + 32, BOTTOM[1] + 32), 'texture': '#b'},
                                       'north': {'uv': edge, 'texture': '#b'}, 'south': {'uv': edge, 'texture': '#b'},
                                       'east': {'uv': edge, 'texture': '#b'}, 'west': {'uv': edge, 'texture': '#b'}},
          rot={'angle': -22.5, 'axis': 'z', 'origin': [4, 0, 8]})
    # łup w środku: złom, puszka, szmata
    m.atlas((4, 7, 5), (8, 9, 8), 'rust')
    m.atlas((8.5, 7, 7), (11, 10, 9.5), 'steel', up='steel_light')
    m.atlas((5, 7, 9.5), (9, 7.8, 12), 'cloth')
    return m


MODELS = {
    'beczka': barrel('beczka'),
    'beczka_paliwa': barrel('beczka_paliwa'),
    'beczka_rdza': barrel('beczka_rdza'),
    'beczka_rozbita': broken('beczka'),
    'beczka_paliwa_rozbita': broken('beczka_paliwa'),
    'beczka_rdza_rozbita': broken('beczka_rdza'),
}
