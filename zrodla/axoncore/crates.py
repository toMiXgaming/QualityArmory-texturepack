"""Skrzynie z łupem: własny model i tekstura 128×128 dla każdej (jak beczki w barrels.py).

Stara wersja składała się z kafelków atlasu rozciągniętych na całe ściany i z brył, które
na siebie nachodziły (narożniki, obwódki, dwie deski środkowe), więc wieka i ściany migały.
Tutaj każda skrzynia to korpus, osobne wieko położone na korpusie i kilka detali przyklejonych
z zewnątrz. Bryły tylko się stykają, a ściany zasłonięte przez sąsiada nie są w ogóle rysowane.
Obwódki, deski, opaski i napisy są namalowane na teksturze, 4 piksele na jednostkę modelu.

Każda skrzynia ma własny układ tekstury: słownik nazwa obszaru -> (x, y, szer., wys.) w pikselach.
"""
import math
import random
from PIL import Image

from .stations import BLOCKLIKE

S = 4  # pikseli na jednostkę modelu
DIRS = ('north', 'south', 'east', 'west', 'up', 'down')

STEEL = (96, 100, 106)
STEEL_DARK = (58, 61, 66)
RUST = (122, 64, 32)
BRASS = (176, 140, 62)


def _mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _mul(c, f):
    return tuple(max(0, min(255, int(v * f))) for v in c[:3])


# ---------------------------------------------------------------- malowanie


class Canvas:
    def __init__(self, seed, regions):
        self.img = Image.new('RGBA', (128, 128), (0, 0, 0, 0))
        self.px = self.img.load()
        self.rnd = random.Random(seed)
        self.R = regions

    def get(self, x, y):
        return self.px[x, y][:3]

    def set(self, x, y, c):
        if 0 <= x < 128 and 0 <= y < 128:
            self.px[x, y] = tuple(c[:3]) + (255,)

    def cells(self, name):
        x0, y0, w, h = self.R[name]
        for v in range(h):
            for u in range(w):
                yield x0 + u, y0 + v, u, v, w, h

    # --- podkłady
    def wood(self, name, base, plank=8, vertical=False, seam=(52, 36, 24)):
        """Deski z usłojeniem, fugami i gwoździami na końcach."""
        rnd = self.rnd
        x0, y0, w, h = self.R[name]
        n = (w if vertical else h) // plank + 1
        tones = [1 + rnd.uniform(-0.12, 0.1) for _ in range(n)]
        phase = [rnd.uniform(0, 6.28) for _ in range(n)]
        knots = [(rnd.uniform(0, w), rnd.uniform(0, h), rnd.uniform(1.2, 2.2)) for _ in range(max(1, w * h // 900))]
        for x, y, u, v, _, _ in self.cells(name):
            a, b = (u, v) if vertical else (v, u)   # a: w poprzek desek, b: wzdłuż
            i, k = a // plank, a % plank
            grain = math.sin(b * 0.35 + phase[i] + k * 1.7) * 0.5 + math.sin(b * 0.09 + phase[i] * 2) * 0.5
            f = tones[i] * (1 + 0.07 * grain) * (1 + rnd.uniform(-0.04, 0.04))
            if k == 0:
                f *= 1.12
            elif k == plank - 1:
                c = seam
                self.set(x, y, _mul(c, 1 + rnd.uniform(-0.08, 0.08)))
                continue
            c = _mul(base, f)
            for kx, ky, kr in knots:
                d = math.hypot(u - kx, (v - ky) * (0.6 if vertical else 1.6))
                if d < kr:
                    c = _mul(base, 0.62 if d > kr - 0.8 else 0.75)
            self.set(x, y, c)
        for i in range(n):   # gwoździe na końcach desek
            a = i * plank + plank // 2 - 1
            for b in (3, (h if vertical else w) - 4):
                px, py = (a, b) if vertical else (b, a)
                if px < w and py < h:
                    self.nail(x0 + px, y0 + py)

    def metal(self, name, base, chips=0, chip=STEEL, rust=0.0, noise=0.05):
        """Malowana blacha: szum, odpryski z cieniem krawędzi, plamki rdzy."""
        rnd = self.rnd
        x0, y0, w, h = self.R[name]
        for x, y, u, v, _, _ in self.cells(name):
            c = _mul(base, 1 + rnd.uniform(-noise, noise))
            if rnd.random() < 0.03 * rust:
                c = _mix(c, RUST, 0.6)
            self.set(x, y, c)
        for _ in range(chips):
            cx, cy = rnd.uniform(1, w - 1), rnd.uniform(1, h - 1)
            blobs = [(cx + rnd.uniform(-1.5, 1.5), cy + rnd.uniform(-1, 1), rnd.uniform(0.8, 2.0)) for _ in range(3)]
            inside = lambda a, b: any(math.hypot(a - bx, (b - by) * 1.3) < br for bx, by, br in blobs)
            for v in range(int(cy) - 5, int(cy) + 6):
                for u in range(int(cx) - 5, int(cx) + 6):
                    if not (0 <= u < w and 0 <= v < h):
                        continue
                    if inside(u, v):
                        self.set(x0 + u, y0 + v, _mix(_mul(chip, 1 + rnd.uniform(-0.06, 0.06)), RUST, rnd.random() * 0.4 * (1 + rust)))
                    elif inside(u - 1, v - 1):
                        self.set(x0 + u, y0 + v, _mul(self.get(x0 + u, y0 + v), 0.8))

    def cardboard(self, name, base=(164, 128, 84)):
        rnd = self.rnd
        for x, y, u, v, w, h in self.cells(name):
            f = 1 + 0.04 * math.sin(u * 1.6) + rnd.uniform(-0.05, 0.05)   # karbowanie tektury
            self.set(x, y, _mul(base, f))

    # --- detale
    def nail(self, x, y):
        self.set(x, y, (150, 152, 150))
        self.set(x + 1, y, (96, 98, 98))
        self.set(x, y + 1, (70, 72, 72))
        self.set(x + 1, y + 1, (50, 50, 52))

    def rivet(self, x, y, c=STEEL):
        for dx, dy, f in ((0, 0, 1.45), (1, 0, 1.1), (0, 1, 1.0), (1, 1, 0.6)):
            self.set(x + dx, y + dy, _mul(c, f))

    def frame(self, name, t, c, rivets=True):
        """Stalowy kątownik wokół ściany: jasna krawędź u góry, ciemna u dołu, nity w rogach."""
        x0, y0, w, h = self.R[name]
        rnd = self.rnd
        for x, y, u, v, _, _ in self.cells(name):
            if u < t or v < t or u >= w - t or v >= h - t:
                f = 1.0
                if v == 0 or u == 0:
                    f = 1.25
                elif v == h - 1 or u == w - 1:
                    f = 0.65
                elif (v == t - 1 and t <= u < w - t) or (u == t - 1 and t <= v < h - t):
                    f = 0.8
                cc = c if rnd.random() > 0.08 else _mix(c, RUST, 0.5)
                self.set(x, y, _mul(cc, f * (1 + rnd.uniform(-0.05, 0.05))))
        if rivets:
            for u, v in ((t // 2, t // 2), (w - t // 2 - 2, t // 2), (t // 2, h - t // 2 - 2), (w - t // 2 - 2, h - t // 2 - 2)):
                self.rivet(x0 + u, y0 + v, c)

    def band(self, name, v0, v1, c, highlight=True, axis='h'):
        """Poziomy (h) albo pionowy (v) pas w obszarze, w pikselach obszaru."""
        x0, y0, w, h = self.R[name]
        for x, y, u, v, _, _ in self.cells(name):
            a = v if axis == 'h' else u
            if v0 <= a < v1:
                f = 1.0
                if highlight and a == v0:
                    f = 1.2
                elif highlight and a == v1 - 1:
                    f = 0.7
                self.set(x, y, _mul(c, f * (1 + self.rnd.uniform(-0.05, 0.05))))

    def rect(self, name, u0, v0, u1, v1, c, noise=0.04, edge=True):
        x0, y0, _, _ = self.R[name]
        for v in range(v0, v1):
            for u in range(u0, u1):
                f = 1 + self.rnd.uniform(-noise, noise)
                if edge and (v == v0 or u == u0):
                    f *= 1.15
                elif edge and (v == v1 - 1 or u == u1 - 1):
                    f *= 0.75
                self.set(x0 + u, y0 + v, _mul(c, f))

    def hazard(self, name, v0, v1, step=6):
        x0, y0, w, _ = self.R[name]
        for v in range(v0, v1):
            for u in range(w):
                c = (210, 170, 52) if ((u + v) // step) % 2 == 0 else (34, 32, 30)
                self.set(x0 + u, y0 + v, _mul(c, 1 + self.rnd.uniform(-0.06, 0.06)))

    def ao(self, name, depth=3, f=0.82):
        """Lekkie przyciemnienie przy krawędziach, żeby ściana nie była płaska."""
        x0, y0, w, h = self.R[name]
        for x, y, u, v, _, _ in self.cells(name):
            d = min(u, v, w - 1 - u, h - 1 - v)
            if d < depth:
                self.set(x, y, _mul(self.get(x, y), f + (1 - f) * d / depth))

    def stencil(self, name, u0, v0, pattern, c, scale=2):
        """Napis szablonem z małej matrycy znaków ('#' = farba), symetryczny, więc odbicie nie szkodzi."""
        x0, y0, _, _ = self.R[name]
        for j, row in enumerate(pattern):
            for i, ch in enumerate(row):
                if ch == '#':
                    for dy in range(scale):
                        for dx in range(scale):
                            if self.rnd.random() > 0.12:   # wytarta farba
                                self.set(x0 + u0 + i * scale + dx, y0 + v0 + j * scale + dy,
                                         _mul(c, 1 + self.rnd.uniform(-0.08, 0.08)))


FONT = {
    'P': ['###', '#.#', '###', '#..', '#..'], 'U': ['#.#', '#.#', '#.#', '#.#', '###'],
    'S': ['###', '#..', '###', '..#', '###'], 'Z': ['###', '..#', '.#.', '#..', '###'],
    'K': ['#.#', '##.', '#..', '##.', '#.#'], 'I': ['###', '.#.', '.#.', '.#.', '###'],
    'W': ['#.#', '#.#', '#.#', '###', '#.#'], '7': ['###', '..#', '.#.', '.#.', '.#.'],
    '6': ['###', '#..', '###', '#.#', '###'], '2': ['###', '..#', '###', '#..', '###'],
    '.': ['...', '...', '...', '...', '.#.'], ' ': ['...'] * 5,
}


def text(s):
    """Napis jako matryca dla Canvas.stencil (znaki 3×5, odstęp 1)."""
    return ['.'.join(FONT[ch][r] for ch in s) for r in range(5)]


# ---------------------------------------------------------------- model


class Crate:
    """Model z jedną teksturą #b = axon:item/<nazwa>."""

    def __init__(self, name, regions):
        self.name = name
        self.R = regions
        self.elements = []
        self.display = BLOCKLIKE

    def uv(self, region, sub=None):
        x0, y0, w, h = self.R[region]
        if sub:   # wycinek obszaru w ułamkach (u0, v0, u1, v1)
            a, b, c, d = sub
            x0, y0, w, h = x0 + a * w, y0 + b * h, (c - a) * w, (d - b) * h
        return [round(x0 / 8, 4), round(y0 / 8, 4), round((x0 + w) / 8, 4), round((y0 + h) / 8, 4)]

    def box(self, frm, to, rot=None, **faces):
        """faces: kierunek -> nazwa obszaru albo (obszar, wycinek). Kierunki pominięte nie są rysowane."""
        out = {}
        for d in DIRS:
            f = faces.get(d)
            if f is None:
                continue
            region, sub = (f, None) if isinstance(f, str) else f
            out[d] = {'uv': self.uv(region, sub), 'texture': '#b'}
        el = {'from': [round(c, 4) for c in frm], 'to': [round(c, 4) for c in to], 'faces': out}
        if rot:
            el['rotation'] = rot
        self.elements.append(el)

    def json(self):
        ref = 'axon:item/' + self.name
        return {'textures': {'b': ref, 'particle': ref}, 'elements': self.elements,
                'display': self.display, 'gui_light': 'side'}


def all_sides(region, **over):
    d = {k: region for k in ('north', 'south', 'east', 'west', 'up', 'down')}
    d.update(over)
    return d


# ---------------------------------------------------------------- skrzynia drewniana z okuciami
# Korpus 15×11.5×15, wieko 15.5×2×15.5 na nim, okucia narożne i zamek przyklejone z zewnątrz.

def skrzynia_drewniana():
    R = {'front': (0, 0, 60, 46), 'side': (64, 0, 60, 46), 'top': (0, 48, 62, 62), 'lid': (64, 48, 62, 8),
         'bottom': (64, 58, 32, 32), 'steel': (98, 58, 30, 30), 'brass': (64, 92, 16, 16), 'inner': (82, 92, 16, 16)}
    c = Canvas('skrzynia_drewniana', R)
    wood = (150, 108, 66)
    for r in ('front', 'side'):
        c.wood(r, wood, plank=9)
        c.band(r, 20, 24, (78, 54, 34))           # deska środkowa (poprzeczka)
        c.ao(r)
    c.wood('top', _mul(wood, 1.05), plank=10, vertical=True)
    c.band('top', 4, 8, (78, 54, 34), axis='h')    # listwy wieka
    c.band('top', 54, 58, (78, 54, 34), axis='h')
    c.ao('top', 4)
    c.wood('lid', _mul(wood, 0.85), plank=8)
    c.band('lid', 6, 8, (60, 42, 28), highlight=False)
    c.wood('bottom', _mul(wood, 0.6), plank=8)
    c.metal('steel', STEEL_DARK, chips=4, chip=(120, 124, 128), rust=1.0)
    for u in (4, 24):
        for v in (4, 24):
            c.rivet(R['steel'][0] + u, R['steel'][1] + v, (130, 134, 138))
    c.metal('brass', BRASS, chips=1, chip=(210, 180, 100))
    x, y, _, _ = R['brass']
    for v in range(5, 11):                        # dziurka od klucza
        c.set(x + 7, y + v, (30, 26, 20))
        c.set(x + 8, y + v, (30, 26, 20))
    c.metal('inner', (60, 42, 28))

    m = Crate('skrzynia_drewniana', R)
    m.box((0.5, 0, 0.5), (15.5, 11.5, 15.5), north='front', south='side', east='side', west='side', down='bottom')
    m.box((0.25, 11.5, 0.25), (15.75, 13.5, 15.75), north='lid', south='lid', east='lid', west='lid', up='top', down='bottom')
    # okucia narożne: kątowniki na dwóch ścianach każdego narożnika, grubość 0,25, bez nakładania
    edge = ('steel', (0, 0, 0.1, 1))
    cap = ('steel', (0, 0, 1, 0.1))
    for x0, z0, sx, sz in ((0.5, 0.5, -1, -1), (15.5, 0.5, 1, -1), (0.5, 15.5, -1, 1), (15.5, 15.5, 1, 1)):
        fz, bz = ('north', 'south') if sz < 0 else ('south', 'north')
        fx, bx = ('west', 'east') if sx < 0 else ('east', 'west')
        for y0, y1 in ((0, 3), (8.5, 11.5)):
            xs = sorted((x0 + 0.25 * sx, x0 - 2.5 * sx))      # skrzydło na ścianie przedniej/tylnej
            zs = sorted((z0, z0 + 0.25 * sz))
            m.box((xs[0], y0, zs[0]), (xs[1], y1, zs[1]), **{fz: 'steel', fx: edge, bx: edge, 'up': cap, 'down': cap})
            xs = sorted((x0, x0 + 0.25 * sx))                  # skrzydło na ścianie bocznej
            zs = sorted((z0, z0 - 2.5 * sz))
            m.box((xs[0], y0, zs[0]), (xs[1], y1, zs[1]), **{fx: 'steel', bz: edge, 'up': cap, 'down': cap})
    # zamek: mosiężna płytka na przedzie korpusu i skobel na wieku
    m.box((6.5, 8, 0.2), (9.5, 11.5, 0.5), north='brass', east=('brass', (0, 0, 0.2, 1)), west=('brass', (0, 0, 0.2, 1)),
          down=('brass', (0, 0, 1, 0.2)))
    m.box((7, 11.5, 0), (9, 12.75, 0.25), north=('brass', (0.2, 0, 0.8, 0.5)), east=('brass', (0, 0, 0.2, 1)),
          west=('brass', (0, 0, 0.2, 1)), up=('brass', (0, 0, 1, 0.2)))
    return m, c.img


# ---------------------------------------------------------------- skrzynka narzędziowa (czerwona blacha)

def skrzynka_narzedziowa():
    R = {'front': (0, 0, 48, 24), 'side': (48, 0, 32, 24), 'top': (0, 24, 50, 34), 'lid_f': (0, 58, 50, 6),
         'lid_s': (50, 58, 34, 6), 'bottom': (80, 0, 48, 32), 'steel': (84, 32, 32, 32), 'grip': (50, 24, 16, 16)}
    c = Canvas('skrzynka_narzedziowa', R)
    red = (156, 46, 36)
    for r in ('front', 'side'):
        c.metal(r, red, chips=6, chip=(120, 124, 128), rust=1.0)
        c.band(r, 0, 2, _mul(red, 1.15))
        c.band(r, 21, 24, _mul(red, 0.7), highlight=False)
        c.ao(r, 2)
    c.metal('top', red, chips=8, chip=(120, 124, 128), rust=1.0)
    c.band('top', 15, 19, _mul(red, 0.8), axis='h')    # przetłoczenie na środku
    c.ao('top', 3)
    for r in ('lid_f', 'lid_s'):
        c.metal(r, _mul(red, 0.9), chips=1, rust=1.0)
        c.band(r, 5, 6, _mul(red, 0.55), highlight=False)
    c.metal('bottom', STEEL_DARK, rust=1.0)
    c.metal('steel', (150, 154, 158), chips=0, rust=0.5)
    c.metal('grip', (34, 32, 30), noise=0.08)
    m = Crate('skrzynka_narzedziowa', R)
    m.box((2, 0, 4), (14, 6, 12), north='front', south='front', east='side', west='side', down='bottom')
    m.box((1.75, 6, 3.75), (14.25, 7.5, 12.25), north='lid_f', south='lid_f', east='lid_s', west='lid_s', up='top',
          down='bottom')
    for x in (5, 10):   # słupki rączki
        m.box((x, 7.5, 7.5), (x + 1, 9.5, 8.5), **all_sides('steel', up=None, down=None))
    m.box((4.75, 9.5, 7.25), (11.25, 10.5, 8.75), **all_sides('grip'))
    for x in (3, 11.5):   # zatrzaski
        m.box((x, 4, 3.5), (x + 1.5, 6.5, 4), north='steel', east='steel', west='steel', up='steel', down='steel')
    return m, c.img


# ---------------------------------------------------------------- szafka medyczna (wisząca, biała emalia)

def szafka_medyczna():
    R = {'front': (0, 0, 56, 56), 'side': (56, 0, 24, 56), 'top': (0, 56, 56, 24), 'steel': (80, 0, 16, 16),
         'shelf': (0, 80, 64, 8), 'back': (80, 16, 48, 48)}
    c = Canvas('szafka_medyczna', R)
    white = (214, 212, 198)
    c.metal('front', white, chips=10, chip=(70, 74, 80), rust=1.0, noise=0.03)
    x0, y0, _, _ = R['front']
    for v in range(56):   # szczelina drzwiczek
        for u in range(56):
            if u in (2, 53) and 2 <= v <= 53 or v in (2, 53) and 2 <= u <= 53:
                c.set(x0 + u, y0 + v, (96, 96, 90))
    c.rect('front', 22, 12, 34, 44, (176, 44, 38), edge=False)    # krzyż
    c.rect('front', 12, 22, 44, 34, (176, 44, 38), edge=False)
    for v in range(56):   # zacieki rdzy spod zawiasów
        for hv in (8, 40):
            if hv + 3 <= v < hv + 3 + 10 and c.rnd.random() < 0.6:
                c.set(x0 + 4, y0 + v, _mix(c.get(x0 + 4, y0 + v), RUST, 0.5 * (1 - (v - hv - 3) / 10)))
    for hv in (8, 40):    # zawiasy
        c.rect('front', 3, hv, 6, hv + 4, (120, 124, 128))
    c.ao('front', 2, 0.85)
    c.metal('side', white, chips=4, chip=(70, 74, 80), rust=1.0, noise=0.03)
    c.ao('side', 2, 0.85)
    c.metal('top', _mul(white, 0.95), chips=3, chip=(70, 74, 80), rust=1.0, noise=0.03)
    c.metal('steel', (140, 144, 148))
    c.metal('shelf', STEEL, rust=1.0)
    c.metal('back', (150, 148, 138))
    m = Crate('szafka_medyczna', R)
    m.box((1, 2.5, 10), (15, 16, 16), north='front', south='back', east='side', west='side', up='top', down='top')
    m.box((0.5, 2, 9.5), (15.5, 2.5, 16), **all_sides('shelf', south=None))     # półka pod szafką
    m.box((12.75, 7.5, 9.5), (13.5, 10.5, 10), north='steel', east='steel', west='steel', up='steel', down='steel')
    return m, c.img


# ---------------------------------------------------------------- skrzynka z jedzeniem (karton z puszkami)

CANS = ((2.5, 3.5, 4, 'can_r'), (6, 3.5, 3.5, 'can_s'), (9.5, 4, 4.5, 'can_y'),
        (3, 8, 3.5, 'can_y'), (7, 8.5, 4, 'can_s'), (10.5, 8, 3, 'can_r'))

def skrzynka_jedzenie():
    R = {'front': (0, 0, 56, 36), 'side': (56, 0, 48, 36), 'flap': (0, 36, 56, 14), 'inner': (56, 36, 48, 40),
         'rim': (0, 50, 56, 4), 'can_r': (0, 56, 24, 16), 'can_s': (24, 56, 24, 16), 'can_y': (48, 56, 24, 16),
         'lid': (104, 0, 12, 12), 'bottom': (0, 80, 56, 48)}
    c = Canvas('skrzynka_jedzenie', R)
    card = (170, 132, 86)
    for r in ('front', 'side', 'flap', 'rim', 'bottom'):
        c.cardboard(r, card)
    c.cardboard('inner', (120, 92, 60))
    for r in ('front', 'side'):
        c.band(r, 16, 22, (196, 176, 130), highlight=False)    # taśma pakowa
        c.ao(r, 2, 0.85)
    c.stencil('front', 5, 3, text('PUSZKI'), (60, 46, 34))
    c.ao('flap', 2, 0.85)
    for r, col in (('can_r', (170, 44, 36)), ('can_s', (150, 154, 156)), ('can_y', (206, 168, 58))):
        c.metal(r, col, noise=0.04)
        c.band(r, 0, 2, (190, 192, 190))
        c.band(r, 14, 16, (120, 122, 122), highlight=False)
        c.rect(r, 4, 6, 20, 10, (232, 226, 206), edge=False)   # etykieta
        x0, y0, w, h = R[r]
        for v in range(h):   # walcowe cieniowanie
            for u in range(w):
                c.set(x0 + u, y0 + v, _mul(c.get(x0 + u, y0 + v), 0.8 + 0.3 * math.sin(math.pi * (u + 0.5) / w)))
    c.metal('lid', (176, 180, 182))
    x0, y0, _, _ = R['lid']
    for u in range(12):
        for v in range(12):
            if abs(math.hypot(u - 5.5, v - 5.5) - 4.5) < 0.6:
                c.set(x0 + u, y0 + v, (120, 124, 126))
    m = Crate('skrzynka_jedzenie', R)
    m.box((1, 0, 2), (15, 7, 14), north=('front', (0, 0.22, 1, 1)), south=('front', (0, 0.22, 1, 1)),
          east=('side', (0, 0.22, 1, 1)), west=('side', (0, 0.22, 1, 1)), up='inner', down='bottom')
    # ścianki nad dnem (puste wnętrze), każda osobno, bez nachodzenia
    m.box((1, 7, 2), (15, 9, 2.5), north=('front', (0, 0, 1, 0.22)), south='inner', up='rim')
    m.box((1, 7, 13.5), (15, 9, 14), south=('front', (0, 0, 1, 0.22)), north='inner', up='rim')
    m.box((1, 7, 2.5), (1.5, 9, 13.5), west=('side', (0, 0, 1, 0.22)), east='inner', up='rim')
    m.box((14.5, 7, 2.5), (15, 9, 13.5), east=('side', (0, 0, 1, 0.22)), west='inner', up='rim')
    # klapy odchylone na zewnątrz
    m.box((0.7, 9, 2), (1, 12.5, 14), rot={'angle': 22.5, 'axis': 'z', 'origin': [1, 9, 8]},
          west='flap', east='flap', up='rim', north='rim', south='rim')
    m.box((15, 9, 2), (15.3, 12.5, 14), rot={'angle': -22.5, 'axis': 'z', 'origin': [15, 9, 8]},
          west='flap', east='flap', up='rim', north='rim', south='rim')
    for x, z, h, tex in CANS:   # puszki stoją na dnie
        m.box((x, 7, z), (x + 3, 7 + h, z + 3), north=tex, south=tex, east=tex, west=tex, up='lid')
    return m, c.img


# ---------------------------------------------------------------- skrzynia wojskowa (oliwka, dwa bloki długości)

def skrzynia_wojskowa():
    R = {'front': (0, 0, 124, 32), 'lid_f': (0, 32, 128, 10), 'top': (0, 42, 128, 50), 'side': (0, 92, 48, 32),
         'lid_s': (48, 92, 50, 10), 'steel': (100, 92, 28, 28), 'bottom': (48, 102, 48, 24)}
    c = Canvas('skrzynia_wojskowa', R)
    olive = (82, 94, 56)
    c.metal('front', olive, chips=14, chip=(120, 112, 90), rust=0.6)
    for u0 in (8, 58, 108):          # czarne opaski
        c.band('front', u0, u0 + 8, (36, 36, 32), axis='v')
    c.stencil('front', 26, 6, text('WP'), (206, 170, 64), scale=4)
    c.stencil('front', 70, 11, text('7.62'), (206, 170, 64))
    c.ao('front', 3)
    c.metal('lid_f', _mul(olive, 0.9), chips=4, chip=(120, 112, 90), rust=0.6)
    for u0 in (8, 58, 110):
        c.band('lid_f', u0, u0 + 8, (36, 36, 32), axis='v')
    c.band('lid_f', 9, 10, _mul(olive, 0.5), highlight=False)
    c.metal('top', _mul(olive, 1.05), chips=16, chip=(120, 112, 90), rust=0.6)
    for u0 in (9, 60, 111):
        c.band('top', u0, u0 + 8, (36, 36, 32), axis='v')
    c.ao('top', 3)
    c.metal('side', olive, chips=4, chip=(120, 112, 90), rust=0.6)
    c.band('side', 20, 28, (36, 36, 32))
    c.ao('side', 3)
    c.metal('lid_s', _mul(olive, 0.9), chips=1, rust=0.6)
    c.metal('steel', (66, 68, 64), chips=2, chip=(140, 144, 146), rust=1.0)
    c.metal('bottom', (50, 56, 36), rust=1.0)
    m = Crate('skrzynia_wojskowa', R)
    m.box((-1, 0, 2), (31, 8, 14), north='front', south='front', east='side', west='side', down='bottom')
    m.box((-1.25, 8, 1.75), (31.25, 10.5, 14.25), north='lid_f', south='lid_f', east='lid_s', west='lid_s',
          up='top', down='bottom')
    for x in (7.5, 20.5):            # zatrzaski
        m.box((x, 5.5, 1.5), (x + 2, 8, 2), north='steel', east='steel', west='steel', down='steel', up='steel')
    m.box((-1.75, 3.5, 6), (-1, 4.5, 10), **all_sides('steel', east=None))     # uchwyty
    m.box((31, 3.5, 6), (31.75, 4.5, 10), **all_sides('steel', west=None))
    for z in (6, 9):
        m.box((-1.75, 4.5, z), (-1, 6, z + 1), **all_sides('steel', east=None, down=None))
        m.box((31, 4.5, z), (31.75, 6, z + 1), **all_sides('steel', west=None, down=None))
    return m, c.img


# ---------------------------------------------------------------- skrzynia elitarna (czarna, pasy ostrzegawcze, zamek szyfrowy)

def skrzynia_elitarna():
    R = {'front': (0, 0, 64, 36), 'side': (64, 0, 56, 36), 'top': (0, 36, 66, 58), 'lid_f': (0, 94, 66, 10),
         'lid_s': (66, 94, 58, 10), 'panel': (68, 40, 20, 16), 'led': (92, 40, 12, 8), 'steel': (68, 60, 24, 24),
         'bottom': (96, 56, 32, 32)}
    c = Canvas('skrzynia_elitarna', R)
    black = (40, 40, 42)
    for r in ('front', 'side'):
        c.metal(r, black, chips=4, chip=(110, 112, 116), noise=0.06)
        c.hazard(r, 28, 34)
        c.frame(r, 2, (78, 80, 86), rivets=True)
        c.ao(r, 3, 0.8)
    c.metal('top', (52, 54, 58), chips=6, chip=(110, 112, 116), noise=0.06)
    c.frame('top', 3, (78, 80, 86))
    x0, y0, w, h = R['top']
    for v in range(10, h - 10, 4):   # karbowanie (blacha ryflowana)
        for u in range(10, w - 10):
            if (u + v) % 8 < 2:
                c.set(x0 + u, y0 + v, _mul(c.get(x0 + u, y0 + v), 1.35))
    for r in ('lid_f', 'lid_s'):
        c.metal(r, (62, 64, 70), noise=0.05)
        c.band(r, 9, 10, (24, 24, 26), highlight=False)
    c.metal('panel', (150, 154, 160))
    c.rect('panel', 2, 2, 18, 6, (24, 30, 26), edge=False)        # wyświetlacz
    for u in (3, 8, 13):                                           # klawisze
        for v in (8, 12):
            c.rect('panel', u, v, u + 3, v + 2, (90, 94, 100))
    c.metal('led', (60, 210, 90), noise=0.1)
    c.metal('steel', (120, 124, 130), chips=0)
    c.metal('bottom', (30, 30, 32))
    m = Crate('skrzynia_elitarna', R)
    m.box((0, 0, 1), (16, 9, 15), north='front', south='front', east='side', west='side', down='bottom')
    m.box((-0.25, 9, 0.75), (16.25, 11.5, 15.25), north='lid_f', south='lid_f', east='lid_s', west='lid_s', up='top',
          down='bottom')
    m.box((5.5, 3.5, 0.5), (10.5, 7.5, 1), north='panel', east=('panel', (0, 0, 0.1, 1)), west=('panel', (0, 0, 0.1, 1)),
          up=('panel', (0, 0, 1, 0.1)), down=('panel', (0, 0, 1, 0.1)))
    m.box((7, 6.5, 0.25), (9, 7, 0.5), **all_sides('led', south=None))
    for x in (1, 13):                 # zawiasy zamków bocznych
        m.box((x, 5, 0.5), (x + 2, 9, 1), north='steel', east='steel', west='steel', down='steel', up='steel')
    return m, c.img


BUILD = {f.__name__: f for f in (skrzynia_drewniana, skrzynka_narzedziowa, szafka_medyczna, skrzynka_jedzenie,
                                 skrzynia_wojskowa, skrzynia_elitarna)}
MODELS, TEX = {}, {}
for _name, _f in BUILD.items():
    MODELS[_name], TEX[_name] = _f()
