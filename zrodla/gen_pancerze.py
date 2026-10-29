#!/usr/bin/env python3
"""Zestawy pancerzy AXON (modele 3D, nie same tekstury) dla QualityArmory / AXON-Structure.

Każdy element zestawu to osobny model przedmiotu (axon:<zestaw>_<element>) w jednej,
wspólnej "ramie gracza": stopy na y=-4, nogi -4..8, tułów 8..20, głowa 20..28, środek na
x=8 i z=8, przód gracza to strona north (z mniejsze). Dzięki temu plugin stawia wszystkie
elementy w tym samym punkcie (wyświetlacz przedmiotu na graczu) i każdy ląduje na swoim
miejscu. Jednostka modelu = 1 piksel skóry gracza.

Zestawy: cien, lis, legion, bastion, ranger, ghillie oraz prowizoryczne: zlomiarz, lowca, tulacz (startowy) (strój liściasty dla snajperów).
Elementy: helm, kamizelka, spodnie, buty, rekawice.

Zapisuje build/<nazwa>.json, build/<nazwa>.png, build/<nazwa>_item.json.
"""
import json, math, os, random
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'build')
YSHIFT = 4.0
ELEMENTY = ['helm', 'kamizelka', 'bluza', 'spodnie', 'buty', 'rekawice']

# ------------------------------------------------------------------ tekstura
# 16 obszarów 16x16 px w siatce 4x4 (jednostka uv = 4 px, obszar = 4x4 uv).
REG = ['main', 'dark', 'accent', 'plate', 'strap', 'glow', 'metal', 'cloth2',
       'leafA', 'leafB', 'leafC', 'bark', 'lens', 'emblem', 'mesh', 'extra']
RI = {n: i for i, n in enumerate(REG)}

# Kamuflaże: lista kolorów od tła do plam
MULTICAM = [(150, 134, 104), (126, 130, 92), (104, 92, 66), (82, 92, 64), (172, 156, 124)]
WOODLAND = [(88, 98, 58), (54, 62, 38), (96, 72, 44), (26, 28, 20)]

# nazwa -> (kolor, wzór); wzór 'camo:<nazwa>' to kamuflaż z listy CAMO
CAMO = {'multicam': MULTICAM, 'woodland': WOODLAND}
PALETY = {
    # Cień: czerń i grafit, zero kolorów (lekka grupa specjalna)
    'cien': {'main': ((40, 42, 44), 'ripstop'), 'dark': ((24, 25, 27), 'ripstop'), 'accent': ((60, 62, 60), 'ripstop'),
             'plate': ((46, 48, 50), 'plate'), 'strap': ((28, 29, 30), 'strap'), 'glow': ((90, 90, 90), 'cloth'),
             'metal': ((84, 86, 88), 'plate'), 'cloth2': ((52, 54, 56), 'ripstop'), 'lens': ((40, 42, 46), 'lens'),
             'emblem': ((60, 60, 58), 'patch'), 'mesh': ((18, 18, 20), 'mesh'), 'extra': ((70, 72, 72), 'ripstop')},
    # Lis: zwiad w kamuflażu woodland
    'lis': {'main': ((0, 0, 0), 'camo:woodland'), 'dark': ((46, 52, 34), 'ripstop'), 'accent': ((120, 104, 70), 'cloth'),
            'plate': ((60, 64, 46), 'plate'), 'strap': ((46, 40, 30), 'strap'), 'glow': ((90, 90, 90), 'cloth'),
            'metal': ((96, 94, 86), 'plate'), 'cloth2': ((92, 80, 54), 'ripstop'), 'lens': ((70, 60, 40), 'lens'),
            'emblem': ((60, 64, 46), 'patch'), 'mesh': ((40, 40, 30), 'mesh'), 'extra': ((70, 62, 44), 'cloth')},
    # Legion: piechota w MultiCam
    'legion': {'main': ((0, 0, 0), 'camo:multicam'), 'dark': ((74, 70, 54), 'ripstop'), 'accent': ((150, 134, 104), 'cloth'),
               'plate': ((92, 86, 66), 'plate'), 'strap': ((52, 48, 38), 'strap'), 'glow': ((90, 90, 90), 'cloth'),
               'metal': ((70, 72, 72), 'plate'), 'cloth2': ((112, 106, 80), 'ripstop'), 'lens': ((30, 60, 46), 'lens'),
               'emblem': ((90, 86, 66), 'patch'), 'mesh': ((40, 38, 30), 'mesh'), 'extra': ((100, 96, 70), 'cloth')},
    # Bastion: ciężka ochrona, coyote i matowe płyty
    'bastion': {'main': ((116, 98, 70), 'ripstop'), 'dark': ((58, 52, 40), 'ripstop'), 'accent': ((140, 122, 90), 'cloth'),
                'plate': ((62, 64, 64), 'plate'), 'strap': ((38, 34, 28), 'strap'), 'glow': ((90, 90, 90), 'cloth'),
                'metal': ((90, 92, 92), 'plate'), 'cloth2': ((98, 84, 60), 'ripstop'), 'lens': ((40, 42, 42), 'lens'),
                'emblem': ((100, 86, 62), 'patch'), 'mesh': ((30, 28, 24), 'mesh'), 'extra': ((76, 68, 50), 'cloth')},
    # Ranger: służba mundurowa, granat
    'ranger': {'main': ((34, 44, 66), 'ripstop'), 'dark': ((22, 28, 42), 'ripstop'), 'accent': ((170, 174, 180), 'cloth'),
               'plate': ((44, 52, 70), 'plate'), 'strap': ((18, 20, 26), 'strap'), 'glow': ((90, 90, 90), 'cloth'),
               'metal': ((150, 150, 146), 'plate'), 'cloth2': ((46, 56, 78), 'ripstop'), 'lens': ((50, 70, 100), 'lens'),
               'emblem': ((172, 176, 182), 'patch'), 'mesh': ((16, 18, 26), 'mesh'), 'extra': ((60, 68, 88), 'cloth')},
    # --- prowizoryczne (dla biedniejszych graczy) ---
    # Złomiarz: dżins, skóra, blachy z karoserii i opony
    'zlomiarz': {'main': ((70, 84, 106), 'denim'), 'dark': ((76, 56, 38), 'leather'), 'accent': ((176, 142, 44), 'paint'),
                 'plate': ((132, 80, 48), 'rust'), 'strap': ((40, 34, 28), 'strap'), 'glow': ((90, 90, 90), 'cloth'),
                 'metal': ((112, 112, 110), 'rust'), 'cloth2': ((118, 108, 78), 'canvas'), 'lens': ((60, 60, 56), 'lens'),
                 'emblem': ((120, 110, 80), 'patch'), 'mesh': ((148, 150, 148), 'duct'), 'extra': ((30, 30, 32), 'rubber')},
    # Łowca: brezent, skóra i zszywane łaty
    'lowca': {'main': ((112, 100, 72), 'canvas'), 'dark': ((70, 50, 34), 'leather'), 'accent': ((142, 122, 90), 'canvas'),
              'plate': ((96, 66, 42), 'leather'), 'strap': ((44, 34, 26), 'leather'), 'glow': ((90, 90, 90), 'cloth'),
              'metal': ((100, 98, 92), 'rust'), 'cloth2': ((84, 90, 64), 'canvas'), 'lens': ((70, 60, 40), 'lens'),
              'emblem': ((90, 80, 56), 'patch'), 'mesh': ((120, 112, 90), 'duct'), 'extra': ((60, 46, 32), 'leather')},
    # Tułacz: najtańszy zestaw startowy; stara bluza, karton i taśma
    'tulacz': {'main': ((86, 90, 82), 'cloth'), 'dark': ((58, 54, 48), 'cloth'), 'accent': ((112, 54, 48), 'knit'),
               'plate': ((156, 122, 82), 'cardboard'), 'strap': ((140, 124, 92), 'rope'), 'glow': ((90, 90, 90), 'cloth'),
               'metal': ((112, 112, 110), 'rust'), 'cloth2': ((112, 112, 108), 'cloth'), 'lens': ((60, 60, 56), 'lens'),
               'emblem': ((100, 96, 86), 'patch'), 'mesh': ((150, 152, 150), 'duct'), 'extra': ((176, 172, 160), 'rubber')},
    'ghillie': {'main': ((70, 78, 44), 'cloth'), 'dark': ((40, 46, 28), 'cloth'), 'accent': ((120, 100, 60), 'cloth'),
                'plate': ((56, 60, 40), 'plate'), 'strap': ((50, 42, 30), 'strap'), 'glow': ((200, 200, 120), 'glow'),
                'metal': ((100, 100, 90), 'plate'), 'cloth2': ((96, 88, 54), 'cloth'), 'lens': ((60, 70, 40), 'lens'),
                'emblem': ((120, 100, 60), 'emblem'), 'mesh': ((40, 44, 28), 'mesh'), 'extra': ((82, 74, 46), 'cloth'),
                'leafA': ((72, 104, 36), 'leaf'), 'leafB': ((98, 124, 48), 'leaf'), 'leafC': ((126, 112, 54), 'leaf'),
                'bark': ((86, 66, 42), 'bark')},
}


def clamp(c):
    return tuple(max(0, min(255, int(v))) for v in c)


def _smooth_noise(rnd, n=16, cell=4):
    """Gładki szum 0..1 na siatce n x n (dwuliniowa interpolacja losowych węzłów)."""
    g = [[rnd.random() for _ in range(n // cell + 2)] for _ in range(n // cell + 2)]
    out = [[0.0] * n for _ in range(n)]
    for y in range(n):
        for x in range(n):
            gx, gy = x / cell, y / cell
            x0, y0 = int(gx), int(gy)
            fx, fy = gx - x0, gy - y0
            a = g[y0][x0] * (1 - fx) + g[y0][x0 + 1] * fx
            b = g[y0 + 1][x0] * (1 - fx) + g[y0 + 1][x0 + 1] * fx
            out[y][x] = a * (1 - fy) + b * fy
    return out


def camo_tile(cols, rnd):
    t = Image.new('RGBA', (32, 32), cols[0] + (255,))
    px = t.load()
    layers = [_smooth_noise(rnd, 32, 9) for _ in range(len(cols) - 1)]
    for y in range(32):
        for x in range(32):
            c = cols[0]
            for i, lay in enumerate(layers):
                if lay[y][x] > 0.58 + 0.04 * i:
                    c = cols[i + 1]
            k = rnd.randint(-5, 5)
            px[x, y] = clamp((c[0] + k, c[1] + k, c[2] + k)) + (255,)
    return t


def refine(t, kind, rnd, base):
    """Drobne szczegóły na obszarze 32x32: szum włókien, fazy krawędzi, ściegi, rysy i odblaski."""
    px = t.load()
    src = t.copy().load()
    S = 32

    def mul(x, y, f):
        r, g, b, a = px[x, y]
        px[x, y] = (max(0, min(255, int(r * f))), max(0, min(255, int(g * f))), max(0, min(255, int(b * f))), a)

    for y in range(S):
        for x in range(S):
            mul(x, y, 1 + rnd.uniform(-0.05, 0.05))
            if kind in ('cloth', 'ripstop', 'strap', 'denim', 'canvas', 'leather', 'knit') or kind.startswith('camo'):
                mul(x, y, 1.06 if (x + y) % 2 == 0 else 0.95)           # splot
                if kind == 'ripstop' and (x % 8 == 0 or y % 8 == 0):
                    mul(x, y, 1.12)
            if kind.startswith('camo'):                                  # kontury plam kamuflażu
                c = src[x, y]
                for dx, dy in ((1, 0), (0, 1)):
                    if x + dx < S and y + dy < S and sum(abs(c[i] - src[x + dx, y + dy][i]) for i in range(3)) > 40:
                        mul(x, y, 0.88)
    for i in range(S):                                                    # faza krawędzi: jasna góra/lewo, ciemny dół/prawo
        mul(i, 0, 1.18); mul(0, i, 1.12); mul(i, S - 1, 0.7); mul(S - 1, i, 0.75)
        mul(i, 1, 1.07); mul(1, i, 1.05); mul(i, S - 2, 0.85); mul(S - 2, i, 0.88)
    if kind in ('cloth', 'ripstop', 'strap', 'denim', 'canvas', 'leather') or kind.startswith('camo'):  # ścieg: przerywana linia
        for i in range(3, S - 3):
            if i % 4 < 2:
                mul(i, 3, 0.8); mul(i, S - 4, 0.8); mul(3, i, 0.82); mul(S - 4, i, 0.82)
    if kind in ('plate', 'rust'):                                         # rysy i otarcia na płycie, nity z odblaskiem
        for _ in range(7):
            x, y = rnd.randint(3, 26), rnd.randint(3, 28)
            for k in range(rnd.randint(3, 7)):
                if x + k < S - 2:
                    mul(x + k, y, 1.35)
        for _ in range(30):
            mul(rnd.randint(2, 29), rnd.randint(2, 29), 0.7)
        for (x, y) in ((4, 4), (27, 4), (4, 27), (27, 27)):
            for dx in (0, 1):
                for dy in (0, 1):
                    mul(x + dx, y + dy, 1.5 if (dx, dy) == (0, 0) else 0.75)
    if kind in ('cloth', 'ripstop', 'denim', 'canvas') and base[0] + base[1] + base[2] < 450:   # wyblakłe zagniecenia na tkaninie
        for _ in range(5):
            x, y = rnd.randint(2, 28), rnd.randint(2, 28)
            for k in range(rnd.randint(4, 9)):
                if x + k < S - 2:
                    mul(x + k, y + k // 3, 1.14)
    return t


def tile(base, kind, rnd, accent=None):
    """Obszar 32x32: wzór 16x16 powiększony i dopracowany refine()."""
    if kind.startswith('camo:'):
        return refine(camo_tile(CAMO[kind[5:]], rnd), kind, rnd, (150, 140, 100))
    return refine(tile16(base, kind, rnd).resize((32, 32), Image.NEAREST), kind, rnd, base)


def tile16(base, kind, rnd, accent=None):
    """Obszar 16x16 z wzorem."""
    t = Image.new('RGBA', (16, 16), base + (255,))
    px = t.load()
    d = ImageDraw.Draw(t)

    def dk(f):
        return clamp([base[0] * f, base[1] * f, base[2] * f]) + (255,)

    def shade(x, y, k):
        px[x, y] = clamp([base[0] + k, base[1] + k, base[2] + k]) + (255,)

    for y in range(16):
        for x in range(16):
            n = rnd.randint(-4, 4)
            if kind in ('cloth', 'strap'):
                n += 4 if (x + y) % 4 == 0 else 0     # splot tkaniny
                n -= 3 if (x % 2 == 0 and y % 2 == 0) else 0
            elif kind == 'ripstop':                    # siatka rip-stop co 4 piksele + splot
                n += 7 if (x % 4 == 0 or y % 4 == 0) else 0
                n += 2 if (x + y) % 2 == 0 else -2
            elif kind == 'plate':
                n = rnd.randint(-4, 4) + (3 if y % 5 == 0 else 0)
            elif kind == 'denim':                      # skośny splot jeansu
                n += 7 if (x + y) % 3 == 0 else -2
            elif kind == 'canvas':                     # gruby brezent
                n += 6 if ((x // 2 + y // 2) % 2 == 0) else -4
            elif kind == 'leather':                    # skóra: plamy
                n = rnd.randint(-3, 3) + (-6 if rnd.random() < 0.08 else 0)
            elif kind == 'rubber':                     # opona: bieżnik
                n += -9 if x % 4 == 0 else (5 if y % 6 == 0 else 0)
            elif kind == 'duct':                       # taśma: srebrne żeberka
                n += 8 if y % 3 == 0 else -3
            elif kind == 'paint':
                n += rnd.randint(-3, 3)
            elif kind == 'cardboard':                  # tektura falista
                n += 6 if x % 3 == 0 else -2
            elif kind == 'knit':                       # dzianina: rządki oczek
                n += 8 if (x + (y // 2) * 2) % 4 in (0, 1) and y % 2 == 0 else -4
            elif kind == 'rope':                       # sznurek skręcany
                n += 9 if (x + y) % 4 == 0 else -3
            elif kind == 'rust':
                n = rnd.randint(-5, 5)
            shade(x, y, n)
    if kind == 'rust':                                   # blacha: rdza, resztki lakieru, nity
        for _ in range(9):
            cx, cy, r = rnd.randint(0, 15), rnd.randint(0, 15), rnd.randint(1, 3)
            col = rnd.choice(((150, 72, 28), (110, 54, 24), (84, 42, 22), (170, 100, 50)))
            for y in range(16):
                for x in range(16):
                    if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                        px[x, y] = col + (255,)
        d.rectangle([0, 0, 15, 15], outline=dk(0.55))
        for p in ((2, 2), (13, 2), (2, 13), (13, 13)):
            px[p] = (170, 168, 160, 255)
    if kind == 'cardboard':                              # nadruk i przetarcia na kartonie
        d.line([(3, 4), (9, 4)], fill=dk(0.6))
        d.line([(3, 6), (7, 6)], fill=dk(0.6))
        for _ in range(6):
            px[rnd.randint(1, 14), rnd.randint(1, 14)] = dk(0.75)
    if kind == 'paint':                                  # odpryski lakieru
        for _ in range(10):
            px[rnd.randint(1, 14), rnd.randint(1, 14)] = (70, 60, 40, 255)
    if kind == 'leather':
        for _ in range(4):                               # zagniecenia
            y0 = rnd.randint(2, 13)
            d.line([(0, y0), (15, y0 + rnd.randint(-1, 1))], fill=dk(0.7))
    if kind in ('plate',):
        d.rectangle([0, 0, 15, 15], outline=dk(0.6))
        d.line([(1, 1), (14, 1)], fill=dk(1.3))
        for p in ((2, 2), (13, 2), (2, 13), (13, 13)):
            px[p] = dk(1.5)
    if kind == 'strap':
        d.line([(0, 7), (15, 7)], fill=dk(0.6))
        d.line([(0, 9), (15, 9)], fill=dk(0.6))
    if kind in ('ripstop', 'cloth'):
        d.line([(0, 15), (15, 15)], fill=dk(0.8))      # szew
        d.line([(15, 0), (15, 15)], fill=dk(0.8))
    if kind == 'mesh':
        for y in range(16):
            for x in range(16):
                if (x % 3 == 1) and (y % 3 == 1):
                    px[x, y] = clamp([base[0] * 2.2 + 30, base[1] * 2.2 + 30, base[2] * 2.2 + 30]) + (255,)
    if kind == 'glow':
        for y in range(16):
            k = 1.0 - abs(y - 8) / 12.0
            for x in range(16):
                px[x, y] = clamp([base[0] * (0.6 + 0.5 * k) + 20] * 3) + (255,)
    if kind == 'lens':                                 # przydymione szkło z delikatnym odbiciem
        for y in range(16):
            for x in range(16):
                k = 0.55 + 0.5 * (y / 15.0)
                px[x, y] = clamp([base[0] * k, base[1] * k, base[2] * k]) + (255,)
        d.line([(2, 2), (6, 2)], fill=clamp([base[0] + 70, base[1] + 70, base[2] + 70]) + (255,))
        d.rectangle([0, 0, 15, 15], outline=(10, 10, 12, 255))
    if kind == 'patch':                                # naszywka na rzep: ciemne tło, ramka, napis jako kreski
        d.rectangle([0, 0, 15, 15], fill=(26, 26, 24, 255))
        d.rectangle([1, 1, 14, 14], outline=dk(0.9))
        for y in (5, 8, 11):
            d.line([(3, y), (12, y)], fill=dk(0.75))
    if kind == 'emblem':
        d.rectangle([0, 0, 15, 15], fill=(18, 18, 20, 255))
        d.polygon([(8, 2), (14, 13), (10, 13), (8, 8), (6, 13), (2, 13)], fill=base + (255,))
        d.line([(5, 11), (11, 11)], fill=base + (255,))
    if kind == 'leaf':
        for y in range(16):
            for x in range(16):
                shade(x, y, rnd.randint(-10, 10))
        d.line([(0, 8), (15, 8)], fill=dk(0.65))
        for x in range(2, 15, 3):
            d.line([(x, 8), (x + 2, 3)], fill=dk(0.75))
            d.line([(x, 8), (x + 2, 13)], fill=dk(0.75))
    if kind == 'bark':
        for x in range(0, 16, 3):
            d.line([(x, 0), (x + rnd.randint(-1, 1), 15)], fill=dk(0.6))
    return t


def texture(name):
    rnd = random.Random(sum(map(ord, name)) * 31)
    pal = PALETY[name]
    im = Image.new('RGBA', (128, 128), (0, 0, 0, 0))
    for i, rn in enumerate(REG):
        base, kind = pal.get(rn, ((120, 120, 120), 'cloth'))
        im.paste(tile(base, kind, rnd), ((i % 4) * 32, (i // 4) * 32))
    return im


# ------------------------------------------------------------------ geometria
ALL = ('north', 'south', 'east', 'west', 'up', 'down')


def box(f, t, reg, skip=(), **kw):
    i = RI[reg]
    uv = [(i % 4) * 4, (i // 4) * 4, (i % 4) * 4 + 4, (i // 4) * 4 + 4]
    e = {'from': [round(v, 3) for v in f], 'to': [round(v, 3) for v in t],
         'faces': {fc: {'uv': uv, 'texture': '#t'} for fc in ALL if fc not in skip}}
    e.update(kw)
    return e


def mirror(els):
    """Odbicie lustrzane względem x=8 (lewa strona)."""
    out = []
    for e in els:
        f, t = e['from'], e['to']
        m = {'from': [16 - t[0], f[1], f[2]], 'to': [16 - f[0], t[1], t[2]], 'faces': e['faces']}
        for k in e:
            if k not in m and k != 'rotation':
                m[k] = e[k]
        if 'rotation' in e:
            r = dict(e['rotation'])
            r['origin'] = [16 - r['origin'][0], r['origin'][1], r['origin'][2]]
            if r['axis'] in ('y', 'z'):
                r['angle'] = -r['angle']
            m['rotation'] = r
        out.append(m)
    return out


def both(els):
    return els + mirror(els)


def rotated(f, t, reg, axis, angle, **kw):
    o = [(f[0] + t[0]) / 2, (f[1] + t[1]) / 2, (f[2] + t[2]) / 2]
    return box(f, t, reg, rotation={'origin': o, 'axis': axis, 'angle': angle}, **kw)


# Elementy gracza w ramie gracza (przód = north = z mniejsze)
HX = (4, 12)         # głowa x
TZ = (6, 10)         # tułów z


# Elementy gracza w ramie gracza (przód = north = z mniejsze)
# głowa x 4..12, y 24..32, z 4..12; tułów x 4..12, y 12..24, z 6..10 (wartości przed przesunięciem YSHIFT)


def molle(x0, x1, y0, y1, z, back=False, reg='strap'):
    """Pasy PALS (rzędy taśm) na przodzie albo na tyle plecaka/kamizelki."""
    out = []
    y = y0
    while y + 0.35 <= y1:
        if back:
            out.append(box([x0, y, z], [x1, y + 0.35, z + 0.18], reg, skip=('north',)))
        else:
            out.append(box([x0, y, z - 0.18], [x1, y + 0.35, z], reg, skip=('south',)))
        y += 0.9
    return out


def pouch(x, y, w, h, zf=4.7, depth=0.8, reg='dark', flap=True, buckle=True):
    """Ładownica przednia na kamizelce: korpus, klapa i klamra."""
    out = [box([x, y, zf - depth], [x + w, y + h, zf], reg, skip=('south',))]
    if flap:
        out.append(box([x - 0.05, y + h * 0.62, zf - depth - 0.2], [x + w + 0.05, y + h + 0.05, zf - depth + 0.02], reg, skip=('south',)))
        if buckle:
            out.append(box([x + w / 2 - 0.3, y + h * 0.55, zf - depth - 0.3], [x + w / 2 + 0.3, y + h * 0.78, zf - depth - 0.15], 'metal', skip=('south',)))
    return out


def plate_carrier(main='main', trim='dark', plates=True, side_plates=False, cummer=True, drag=True):
    """Nosidło płyt: worek na płytę przód i tył, ramiona, kołnierz i pas boczny z taśmami PALS."""
    e = [box([3.7, 12.6, 5.2], [12.3, 23.0, 10.8], trim),                       # korpus pod spodem
         box([4.2, 14.0, 4.6], [11.8, 22.4, 5.3], main, skip=('south',)),       # worek na płytę (przód)
         box([4.2, 14.0, 10.7], [11.8, 22.4, 11.4], main, skip=('north',)),     # worek na płytę (tył)
         box([4.0, 22.2, 5.1], [6.6, 24.6, 10.9], main),                        # ramiona
         box([9.4, 22.2, 5.1], [12.0, 24.6, 10.9], main),
         box([4.0, 24.2, 5.2], [6.6, 24.9, 10.8], trim),                        # wyściółka na barkach
         box([9.4, 24.2, 5.2], [12.0, 24.9, 10.8], trim),
         box([5.6, 23.6, 5.8], [10.4, 24.9, 10.4], trim, skip=('up',)),         # miękki kołnierz
         box([3.7, 12.2, 5.2], [12.3, 14.0, 10.8], trim)]                       # dolna krawędź
    if cummer:
        e += [box([3.5, 14.0, 5.0], [4.4, 18.6, 11.0], trim),                    # pas boczny (cummerbund)
              box([11.6, 14.0, 5.0], [12.5, 18.6, 11.0], trim),
              box([3.4, 14.4, 6.0], [3.7, 18.0, 10.0], 'strap'),                 # rzep pasa
              box([12.3, 14.4, 6.0], [12.6, 18.0, 10.0], 'strap')]
    if plates:
        e += [box([4.8, 14.6, 4.45], [11.2, 21.8, 4.62], 'plate', skip=('south',)),   # zarys płyty pod tkaniną
              box([4.8, 14.6, 11.38], [11.2, 21.8, 11.5], 'plate', skip=('north',))]
    if side_plates:
        e += [box([3.0, 14.6, 6.4], [3.5, 19.8, 9.6], 'plate'),
              box([12.5, 14.6, 6.4], [13.0, 19.8, 9.6], 'plate')]
    e += molle(4.4, 11.6, 14.4, 22.0, 4.62)
    e += molle(4.4, 11.6, 14.4, 22.0, 11.38, back=True)
    if drag:
        e += [box([6.8, 22.0, 11.38], [9.2, 22.4, 11.7], 'strap', skip=('north',)),   # uchwyt do ewakuacji
              box([6.8, 22.0, 11.6], [9.2, 23.6, 11.8], 'strap', skip=('north',))]
    for x in (4.9, 10.7):                                                        # klamry ramion
        e.append(box([x, 22.0, 4.5], [x + 0.6, 22.8, 4.7], 'metal', skip=('south',)))
    return e


def shoulder_pads(reg='main', trim='dark', size=1.0):
    pad = [box([2.4, 22.4, 5.4], [4.2, 24.4, 10.6], reg), box([2.2, 21.4, 5.6], [3.2, 23.4, 10.4], trim)]
    return both([p for p in pad]) if size else []


def pants(main, dark, kneepad='plate', belt='strap', holster=False, cargo=True, stripe=None):
    """Spodnie bojowe: kieszenie cargo z klapkami, szwy, nakolanniki z paskami, pas z klamrą, blouse do butów."""
    leg = [box([3.75, 0.9, 5.75], [8.0, 12.4, 10.25], main),
           box([3.7, 0.4, 5.7], [8.05, 1.9, 10.3], dark),                       # ściągacz nad butem
           box([7.7, 1.9, 5.8], [8.1, 11.6, 10.2], dark, skip=('west',)),       # szew wewnętrzny
           box([5.4, 2.4, 5.6], [6.6, 11.2, 5.75], dark, skip=('south',)),      # szew centralny przód
           box([4.1, 3.2, 5.3], [7.7, 5.9, 5.8], kneepad, skip=('south',)),     # nakolannik
           box([4.4, 3.5, 5.15], [7.4, 5.6, 5.3], 'plate', skip=('south',)),
           box([3.8, 3.9, 5.3], [8.0, 4.3, 10.3], 'strap'),                     # pasek nakolannika
           box([3.8, 5.2, 5.3], [8.0, 5.6, 10.3], 'strap')]
    if cargo:
        leg += [box([3.3, 6.4, 6.4], [3.75, 9.6, 9.6], dark),                   # kieszeń cargo
                box([3.25, 8.8, 6.3], [3.8, 9.8, 9.7], dark),                   # klapka
                box([3.2, 8.9, 7.7], [3.35, 9.3, 8.3], 'metal'),                # guzik
                box([3.35, 6.6, 6.6], [3.5, 7.0, 9.4], 'strap')]                # ściągacz kieszeni
    if holster:
        leg += [box([3.2, 5.6, 6.2], [3.7, 9.6, 9.6], 'strap'),
                box([3.0, 8.8, 6.2], [3.4, 9.8, 9.6], 'dark')]
    if stripe:
        leg.append(box([5.0, 2.0, 5.65], [6.8, 11.0, 5.78], stripe, skip=('south', 'up', 'down')))
    out = both(leg)
    out += [box([3.6, 11.2, 5.6], [12.4, 12.7, 10.4], belt),                    # pas
            box([7.4, 11.4, 5.4], [8.6, 12.5, 5.6], 'metal', skip=('south',)),  # klamra
            box([3.6, 12.5, 5.6], [12.4, 12.9, 10.4], dark)]                    # pasek na szlufki
    for x in (4.2, 5.8, 10.2, 11.8):
        out.append(box([x, 11.2, 5.5], [x + 0.5, 12.7, 5.7], dark, skip=('south',)))   # szlufki
    return out


def boots_base(main, dark, high=5.0, plate=None, sole='dark'):
    b = [box([3.7, 0.0, 4.2], [8.0, 0.9, 10.3], sole),                          # podeszwa z bieżnikiem
         box([3.8, 0.9, 4.4], [7.95, high, 10.2], main),                        # cholewka
         box([4.0, 0.9, 3.9], [7.8, 3.0, 4.5], dark),                           # nosek
         box([3.7, high - 0.8, 5.6], [8.1, high + 0.3, 10.4], dark),            # kołnierz
         box([3.7, 0.9, 5.0], [8.0, 1.5, 10.3], dark),                          # rant
         box([4.3, 1.0, 4.4], [7.5, 2.0, 4.6], 'strap', skip=('south',))]
    b += [box([3.6, 0.0, 3.8], [8.1, 0.5, 4.2], sole),                           # nosek podeszwy
          box([3.7, 0.9, 3.7], [7.9, 2.0, 4.0], dark),                           # wzmocniony czubek
          box([4.0, 2.0, 3.9], [7.7, 2.6, 4.3], dark),
          box([3.7, 0.0, 9.4], [8.0, 1.6, 10.6], sole)]                          # obcas
    for i in range(5):                                                          # bieżnik: klocki pod podeszwą
        b.append(box([3.7, -0.3, 4.4 + i * 1.2], [8.0, 0.0, 5.2 + i * 1.2], 'strap'))
    for z in (5.4, 6.8, 8.2):                                                   # sznurowanie
        b.append(box([5.4, 3.0 + (z - 5.4) * 0.3, 4.3], [6.6, 3.3 + (z - 5.4) * 0.3, 4.6], 'strap'))
    for i in range(4):                                                          # haczyki
        b.append(box([4.6, 2.2 + i * 0.9, 4.2], [4.9, 2.5 + i * 0.9, 4.45], 'metal'))
        b.append(box([7.1, 2.2 + i * 0.9, 4.2], [7.4, 2.5 + i * 0.9, 4.45], 'metal'))
    if plate:
        b.append(box([3.6, 1.0, 8.4], [8.1, 3.4, 10.5], plate))
    return both(b)


def gloves_base(main, dark, plate=None, cuff=3.0):
    g = [box([0.0, 12.0, 6.0], [4.0, 15.0, 10.0], main),                        # dłoń
         box([-0.15, 14.4, 5.85], [4.15, 14.4 + cuff * 0.5, 10.15], dark),      # mankiet
         box([0.2, 11.4, 6.3], [3.8, 12.0, 9.7], dark)]                          # kłykcie od dołu
    for i in range(4):                                                          # palce
        g.append(box([0.2 + i * 0.9, 11.0, 5.7], [0.9 + i * 0.9, 12.2, 6.2], main))
    for i in range(4):                                                          # zgięcia palców
        g.append(box([0.2 + i * 0.9, 11.2, 5.6], [0.9 + i * 0.9, 11.9, 5.7], dark))
    g.append(box([3.9, 11.6, 5.4], [4.5, 13.6, 6.6], main))                      # kciuk
    g.append(box([4.0, 11.4, 5.5], [4.4, 12.0, 6.2], dark))
    g.append(box([0.4, 13.8, 9.8], [3.6, 14.6, 10.3], dark))                     # rzep z tyłu dłoni
    if plate:
        g.append(box([0.4, 12.3, 5.5], [3.6, 14.2, 6.0], plate, skip=('south',)))
        g.append(box([0.6, 14.0, 5.3], [3.4, 14.5, 5.9], plate))
    g.append(box([3.6, 12.0, 6.3], [4.15, 14.0, 9.7], dark))
    return both(g)


def sleeves(main, dark, pad='plate', patch='emblem', cuff='dark'):
    """Rękawy bluzy bojowej: szew barkowy, łokcie z wkładkami, naszywka na ramieniu, ściągacz."""
    a = [box([-0.4, 12.6, 5.6], [4.2, 24.2, 10.4], main),
         box([-0.5, 22.6, 5.5], [4.3, 24.3, 10.5], dark),                        # szew/wzmocnienie barku
         box([-0.5, 12.2, 5.5], [4.3, 13.6, 10.5], cuff),                        # mankiet
         box([-0.3, 16.0, 10.3], [4.1, 19.0, 11.0], pad),                        # wkładka łokciowa
         box([0.2, 16.4, 10.9], [3.5, 18.6, 11.2], 'plate'),
         box([-0.7, 19.8, 6.4], [-0.4, 22.8, 9.6], patch, skip=('east',)),       # naszywka na ramieniu (rzep)
         box([-0.5, 14.0, 5.3], [4.2, 14.4, 5.65], 'strap'),                     # pasek mankietu
         box([4.2, 14.4, 6.4], [4.4, 17.6, 9.6], dark)]                          # kieszeń po wewnętrznej stronie
    return both(a)


def head_open(reg, hi, lo=24.4, thick=0.0):
    """Czasza i boki/tył hełmu bez zakrywania twarzy (przód poniżej czoła odsłonięty)."""
    return [box([3.5 - thick, 29.2, 3.5 - thick], [12.5 + thick, hi, 12.5 + thick], reg),
            box([3.5 - thick, lo, 6.0], [12.5 + thick, 29.4, 12.5 + thick], reg)]


def combat_helmet(shell='main', cover=True, rails=True, nvg=True, ear='plate', strap='strap'):
    """Hełm balistyczny typu FAST/ACH: czasza, pokrowiec, szyny, mocowanie NVG, nauszniki i podbródek."""
    e = [box([3.2, 28.4, 3.2], [12.8, 29.6, 12.8], shell),                       # czasza schodkowa (kopuła z warstw)
         box([3.5, 29.6, 3.5], [12.5, 30.6, 12.5], shell),
         box([3.9, 30.6, 3.9], [12.1, 31.5, 12.1], shell),
         box([4.6, 31.5, 4.6], [11.4, 32.3, 11.4], shell),
         box([5.6, 32.3, 5.6], [10.4, 32.7, 10.4], shell),
         box([3.2, 27.6, 6.0], [12.8, 29.0, 12.8], shell),                       # tył/boki w dół
         box([3.0, 26.0, 8.0], [3.4, 28.0, 12.6], shell),                        # wywinięty tył czaszy
         box([12.6, 26.0, 8.0], [13.0, 28.0, 12.6], shell),
         box([3.6, 24.6, 10.4], [12.4, 27.8, 12.6], shell),                      # osłona karku
         box([3.0, 28.4, 3.0], [13.0, 29.0, 13.0], 'dark', skip=()),             # krawędź / opaska
         box([3.6, 29.0, 2.9], [12.4, 29.5, 3.5], strap)]                        # pas przedni nad czołem
    if cover:
        e += [box([3.6, 29.6, 3.6], [12.4, 31.8, 5.0], 'dark'),                  # kamuflażowa siatka na czole
              box([4.4, 32.2, 4.4], [11.6, 32.7, 11.6], 'cloth2')]
    if rails:
        e += [box([3.0, 28.4, 6.0], [3.4, 30.4, 9.0], 'metal'),                  # szyny boczne
              box([12.6, 28.4, 6.0], [13.0, 30.4, 9.0], 'metal'),
              box([2.8, 29.0, 6.6], [3.1, 29.6, 8.4], 'dark'),
              box([12.9, 29.0, 6.6], [13.2, 29.6, 8.4], 'dark')]
    if nvg:
        e += [box([6.6, 30.4, 2.4], [9.4, 32.0, 3.6], 'metal'),                  # mocowanie NVG (shroud)
              box([7.2, 30.8, 1.4], [8.8, 31.8, 2.5], 'dark'),
              box([7.5, 31.0, 1.1], [8.5, 31.6, 1.5], 'lens')]
    e += [box([3.0, 25.2, 6.2], [3.6, 28.6, 9.8], ear),                          # nauszniki komunikacyjne
          box([12.4, 25.2, 6.2], [13.0, 28.6, 9.8], ear),
          box([3.2, 25.6, 4.0], [3.5, 29.0, 4.4], strap),                        # pasek podbródkowy
          box([12.5, 25.6, 4.0], [12.8, 29.0, 4.4], strap),
          box([3.9, 24.0, 4.0], [12.1, 24.3, 4.4], strap),
          box([7.2, 23.9, 3.8], [8.8, 24.4, 4.4], 'metal')]                      # klamra pod brodą
    return e


# ------------------------------------------------------------- CIEŃ (lekka grupa specjalna)
def cien_helm():
    """Czapka patrolowa, zestaw słuchawkowy z mikrofonem i chusta na szyi (twarz odkryta)."""
    e = [box([3.6, 29.4, 3.6], [12.4, 31.6, 12.4], 'main'),                      # denko czapki
         box([4.2, 31.5, 4.2], [11.8, 32.1, 11.8], 'main'),
         box([3.5, 28.4, 3.5], [12.5, 29.6, 12.5], 'dark'),                      # otok
         box([3.5, 24.6, 10.8], [12.5, 28.6, 12.7], 'dark'),                     # kaptur z tyłu
         box([4.0, 29.4, 0.9], [12.0, 30.0, 3.6], 'dark'),                       # daszek
         box([4.4, 29.2, 0.7], [11.6, 29.5, 3.6], 'strap'),
         box([6.6, 29.8, 3.2], [9.4, 31.0, 3.7], 'emblem', skip=('south',)),     # naszywka rzep
         box([2.6, 25.6, 6.0], [3.5, 29.0, 10.0], 'metal'),                      # nauszniki słuchawek
         box([12.5, 25.6, 6.0], [13.4, 29.0, 10.0], 'metal'),
         box([2.3, 26.2, 6.6], [2.7, 28.4, 9.4], 'dark'),
         box([13.3, 26.2, 6.6], [13.7, 28.4, 9.4], 'dark'),
         box([3.2, 31.4, 5.5], [12.8, 32.0, 6.3], 'strap'),                      # pałąk
         box([3.6, 24.4, 4.0], [3.9, 26.4, 5.6], 'strap'),                       # mikrofon na wysięgniku
         box([3.9, 24.4, 3.1], [5.2, 24.9, 4.0], 'strap'),
         box([4.8, 24.0, 2.6], [5.8, 25.1, 3.2], 'dark'),
         box([3.6, 21.6, 4.6], [12.4, 24.2, 11.4], 'cloth2', skip=('up',))]      # chusta na szyi
    return e


def cien_kamizelka():
    e = plate_carrier('main', 'dark', plates=True, drag=True)
    e += pouch(4.6, 14.6, 1.6, 3.0) + pouch(6.4, 14.6, 1.6, 3.0)                 # dwie ładownice na magazynki
    e += pouch(8.2, 14.6, 1.6, 3.0) + pouch(10.0, 14.6, 1.6, 3.0)
    e += pouch(4.8, 18.4, 2.4, 2.8, depth=0.6, reg='dark') + pouch(8.8, 18.4, 2.4, 2.8, depth=0.6, reg='dark')   # kieszenie na wyposażenie
    e += [box([7.2, 18.6, 4.1], [8.8, 20.2, 4.5], 'emblem', skip=('south',))]
    e += [box([2.6, 20.8, 5.6], [4.2, 24.0, 10.4], 'main'), box([11.8, 20.8, 5.6], [13.4, 24.0, 10.4], 'main')]
    return e


# ------------------------------------------------------------ LIS (zwiad terenowy)
def lis_helm():
    """Kapelusz polowy (boonie) w kamuflażu woodland, twarz odkryta."""
    return [box([3.5, 29.4, 3.5], [12.5, 31.8, 12.5], 'main'),                   # głowa kapelusza
            box([4.2, 31.7, 4.2], [11.8, 32.3, 11.8], 'main'),
            box([1.8, 29.0, 1.8], [14.2, 29.6, 14.2], 'main'),                   # rondo
            box([1.2, 28.7, 1.2], [14.8, 29.2, 14.8], 'main', skip=('up', 'down')),   # opadające krawędzie ronda
            box([3.4, 29.4, 3.4], [12.6, 30.2, 12.6], 'strap'),                  # taśma
            box([6.6, 30.0, 3.3], [9.4, 31.2, 3.7], 'emblem', skip=('south',)),  # mała naszywka
            box([3.6, 24.6, 11.2], [12.4, 29.0, 12.6], 'main'),                  # osłona karku (flap)
            box([3.5, 24.6, 4.2], [4.0, 28.8, 4.6], 'strap'),                    # sznurek pod brodę
            box([12.0, 24.6, 4.2], [12.5, 28.8, 4.6], 'strap'),
            box([3.8, 24.2, 4.2], [12.2, 24.5, 4.6], 'strap')]


def lis_kamizelka():
    """Lekka kamizelka zwiadowcy (chest rig) i plecak patrolowy z zrolowaną karimatą."""
    e = [box([3.8, 13.0, 5.4], [12.2, 23.4, 10.6], 'dark'),                      # kamizelka bazowa
         box([4.1, 22.0, 5.2], [6.4, 24.6, 10.8], 'main'),                       # szelki
         box([9.6, 22.0, 5.2], [11.9, 24.6, 10.8], 'main'),
         box([4.2, 15.2, 4.7], [11.8, 21.6, 5.5], 'main', skip=('south',)),      # panel przedni
         box([3.6, 13.0, 5.2], [12.4, 15.2, 10.8], 'dark')]                      # pas
    e += molle(4.4, 11.6, 15.6, 21.2, 4.7)
    e += pouch(4.4, 15.2, 1.7, 3.2, zf=4.7) + pouch(6.3, 15.2, 1.7, 3.2, zf=4.7)
    e += pouch(8.2, 15.2, 1.7, 3.2, zf=4.7) + pouch(10.1, 15.2, 1.7, 3.2, zf=4.7)
    e += pouch(4.8, 18.8, 2.6, 2.6, depth=0.6, zf=4.7) + pouch(8.6, 18.8, 2.6, 2.6, depth=0.6, zf=4.7)
    e += [box([7.8, 21.0, 4.3], [8.2, 22.6, 4.6], 'strap', skip=('south',)),     # mikrofon radiowy
          box([4.6, 12.4, 3.9], [7.0, 14.0, 5.5], 'dark', skip=('south',)),
          box([4.6, 11.6, 10.4], [11.4, 22.8, 14.4], 'main'),                    # plecak
          box([4.9, 12.4, 14.4], [11.1, 20.0, 15.1], 'dark'),                    # kieszeń główna
          box([4.4, 21.8, 10.6], [11.6, 24.2, 14.2], 'cloth2'),                  # karimata zrolowana
          box([4.4, 22.2, 14.0], [11.6, 23.8, 14.6], 'cloth2'),
          box([5.2, 12.6, 14.3], [5.8, 21.8, 14.9], 'strap'),                    # pasy kompresyjne
          box([10.2, 12.6, 14.3], [10.8, 21.8, 14.9], 'strap'),
          box([6.8, 14.4, 15.0], [9.2, 16.2, 15.6], 'extra'),                    # kieszeń zewnętrzna
          box([2.6, 14.0, 8.2], [3.8, 17.6, 10.6], 'dark'),                      # bidon z boku
          box([2.8, 17.4, 8.6], [3.6, 18.2, 10.2], 'metal')]
    return e


# ---------------------------------------------------------- LEGION (piechota)
def legion_helm():
    e = combat_helmet('main', cover=True, rails=True, nvg=True, ear='plate')
    e += [box([4.0, 28.8, 2.6], [12.0, 29.4, 3.0], 'strap')]
    return e


def legion_kamizelka():
    e = plate_carrier('main', 'dark', plates=True, side_plates=False, drag=True)
    e += shoulder_pads('main', 'dark')
    for i, x in enumerate((4.5, 6.3, 8.1, 9.9)):                                  # cztery ładownice na magazynki M4
        e += pouch(x, 14.6, 1.6, 3.4)
    e += pouch(4.6, 18.4, 3.0, 3.0, depth=0.5, reg='dark') + pouch(8.4, 18.4, 3.0, 3.0, depth=0.5, reg='dark')   # panel administracyjny, kieszeń rzutowa
    e += [box([5.2, 21.2, 4.2], [6.8, 22.4, 4.6], 'emblem', skip=('south',)),    # naszywki imienne i flagi
          box([9.2, 21.2, 4.2], [10.8, 22.4, 4.6], 'emblem', skip=('south',)),
          box([3.0, 15.4, 6.6], [3.5, 18.4, 9.4], 'dark'),                        # radiostacja przy boku
          box([2.8, 18.2, 7.6], [3.1, 21.8, 7.8], 'strap')]                       # antena
    e += both([box([3.0, 18.4, 7.0], [3.6, 20.0, 9.0], 'dark')])
    return e


# ------------------------------------------------------- BASTION (ciężka ochrona)
def bastion_helm():
    e = combat_helmet('plate', cover=False, rails=True, nvg=True, ear='dark')
    e += [box([2.6, 25.2, 5.6], [3.2, 29.0, 10.6], 'plate'),                      # pełne osłony uszu
          box([12.8, 25.2, 5.6], [13.4, 29.0, 10.6], 'plate'),
          box([3.2, 24.0, 12.0], [12.8, 28.4, 13.6], 'plate'),                    # rozszerzona osłona karku
          box([3.4, 28.8, 3.0], [12.6, 29.4, 3.6], 'dark')]
    return e


def bastion_kamizelka():
    e = plate_carrier('main', 'dark', plates=True, side_plates=True, drag=True)
    e += shoulder_pads('main', 'dark')
    e += [box([5.0, 23.8, 3.8], [11.0, 25.6, 5.0], 'plate', skip=('south',)),     # osłona gardła
          box([4.4, 10.4, 4.4], [11.6, 12.8, 5.4], 'main', skip=('south',)),      # osłona krocza
          box([5.4, 9.6, 4.2], [10.6, 10.6, 5.2], 'dark', skip=('south',)),
          box([2.4, 20.8, 5.0], [4.2, 24.8, 11.0], 'plate'),                      # ciężkie naramienniki
          box([11.8, 20.8, 5.0], [13.6, 24.8, 11.0], 'plate')]
    e += pouch(4.6, 14.6, 1.7, 3.4) + pouch(6.5, 14.6, 1.7, 3.4)
    e += pouch(8.4, 14.6, 1.7, 3.4) + pouch(10.3, 14.6, 1.7, 3.4)
    e += pouch(5.0, 18.4, 2.4, 2.8, depth=0.5) + pouch(8.6, 18.4, 2.4, 2.8, depth=0.5)
    e += [box([5.4, 21.0, 4.2], [10.6, 21.9, 4.6], 'emblem', skip=('south',))]
    return e


# --------------------------------------------------------- RANGER (służby mundurowe)
def ranger_helm():
    """Czapka służbowa (baseballówka patrolowa), twarz odkryta."""
    return [box([3.6, 29.4, 3.6], [12.4, 31.6, 12.4], 'main'),
            box([4.2, 31.5, 4.2], [11.8, 32.1, 11.8], 'main'),
            box([3.5, 28.6, 3.5], [12.5, 29.6, 12.5], 'main'),
            box([3.6, 25.0, 11.4], [12.4, 29.0, 12.6], 'dark'),                  # tył czapki
            box([4.0, 29.4, 0.9], [12.0, 30.0, 3.6], 'dark'),                    # daszek
            box([4.4, 29.2, 0.7], [11.6, 29.5, 3.6], 'strap'),
            box([6.2, 29.8, 3.2], [9.8, 31.4, 3.7], 'emblem', skip=('south',)),  # tarcza na czole
            box([7.2, 31.6, 3.6], [8.8, 31.9, 4.0], 'metal'),                    # guzik
            box([3.6, 28.6, 12.2], [12.4, 29.4, 12.8], 'strap')]                 # regulacja z tyłu


def ranger_kamizelka():
    e = plate_carrier('main', 'dark', plates=False, drag=False)
    e += [box([4.6, 15.0, 4.2], [11.4, 19.4, 4.65], 'cloth2', skip=('south',)),   # panel z napisem
          box([5.0, 16.4, 4.1], [11.0, 18.0, 4.3], 'accent', skip=('south',)),    # pasek odblaskowy
          box([4.8, 20.4, 4.1], [7.0, 21.9, 4.6], 'emblem', skip=('south',)),     # numer służbowy
          box([9.0, 20.4, 4.1], [11.2, 21.9, 4.6], 'metal', skip=('south',)),     # odznaka
          box([3.4, 11.6, 5.1], [12.6, 12.9, 10.9], 'strap'),                     # pas służbowy
          box([3.0, 11.6, 6.0], [3.6, 15.4, 9.4], 'dark'),                        # kabura
          box([2.8, 14.6, 6.2], [3.4, 15.8, 9.2], 'strap'),
          box([10.0, 11.0, 4.5], [12.2, 13.0, 5.4], 'dark', skip=('south',)),     # kajdanki
          box([4.2, 10.8, 4.6], [6.4, 12.8, 5.4], 'dark', skip=('south',)),       # latarka
          box([7.0, 20.6, 4.2], [7.5, 23.4, 4.6], 'strap', skip=('south',)),      # kabel krótkofalówki
          box([6.2, 22.0, 4.0], [8.2, 24.0, 4.6], 'dark', skip=('south',)),       # krótkofalówka na ramieniu
          box([5.4, 18.6, 11.6], [10.6, 21.0, 11.8], 'cloth2', skip=('north',)),  # napis z tyłu
          box([5.4, 16.0, 11.6], [10.6, 18.0, 11.8], 'accent', skip=('north',))]
    e += pouch(4.6, 12.8, 1.8, 2.2, depth=0.5) + pouch(9.6, 12.8, 1.8, 2.2, depth=0.5)
    return e


# ------------------------------------------------------------- PROWIZORYCZNE
def patch_strip(x0, x1, y, z, reg='mesh', skip=('south',)):
    """Pas taśmy naprawczej (duct tape) przez element."""
    return box([x0, y, z - 0.12], [x1, y + 0.8, z], reg, skip=skip)


def zlomiarz_helm():
    """Kask budowlany z latarką czołową i taśmą; twarz odkryta."""
    return [box([3.3, 28.4, 3.3], [12.7, 29.6, 12.7], 'accent'),
            box([3.7, 29.6, 3.7], [12.3, 30.8, 12.3], 'accent'),
            box([4.3, 30.8, 4.3], [11.7, 31.8, 11.7], 'accent'),
            box([5.4, 31.8, 5.4], [10.6, 32.4, 10.6], 'accent'),
            box([7.4, 31.4, 4.0], [8.6, 32.6, 12.0], 'accent'),                   # żeberko kasku
            box([3.0, 28.0, 1.4], [13.0, 28.8, 3.4], 'accent'),                   # daszek
            box([3.4, 27.0, 7.0], [12.6, 28.6, 13.0], 'accent'),                  # tył
            box([3.9, 29.2, 2.8], [12.1, 29.9, 3.4], 'strap'),                    # opaska
            box([6.8, 30.0, 2.2], [9.2, 31.4, 3.3], 'metal'),                     # latarka czołowa
            box([7.2, 30.4, 1.7], [8.8, 31.0, 2.3], 'lens'),
            box([9.6, 29.2, 2.6], [12.2, 32.6, 3.0], 'mesh'),                     # taśma przez kask
            box([3.6, 24.6, 11.4], [12.4, 27.4, 12.8], 'cloth2'),                 # szmata na kark
            box([3.4, 25.2, 4.2], [3.8, 28.4, 4.6], 'strap'),
            box([12.2, 25.2, 4.2], [12.6, 28.4, 4.6], 'strap')]


def zlomiarz_kamizelka():
    """Skórzana kamizelka z przynitowanymi blachami z karoserii i barkami z opon."""
    e = [box([3.8, 12.8, 5.3], [12.2, 23.4, 10.7], 'dark'),
         box([4.0, 22.4, 5.2], [6.4, 24.4, 10.8], 'dark'),
         box([9.6, 22.4, 5.2], [12.0, 24.4, 10.8], 'dark'),
         box([4.4, 17.2, 4.6], [8.0, 22.4, 5.3], 'plate', skip=('south',)),       # blacha na piersi, lewa
         box([8.2, 15.0, 4.55], [11.8, 21.6, 5.3], 'plate', skip=('south',)),     # prawa, większa
         box([4.6, 13.6, 4.6], [9.4, 17.0, 5.2], 'metal', skip=('south',)),       # dolna, inny kawałek
         rotated([9.4, 13.0, 4.5], [11.8, 15.4, 5.1], 'plate', 'z', 22.5, skip=('south',)),
         box([4.4, 14.4, 10.7], [11.6, 22.0, 11.3], 'plate', skip=('north',)),    # blacha na plecach
         box([4.6, 12.8, 11.2], [11.4, 14.8, 11.8], 'metal', skip=('north',)),
         patch_strip(4.2, 11.8, 17.0, 4.62), patch_strip(4.2, 11.8, 21.2, 4.62),  # taśma łącząca blachy
         box([2.0, 21.2, 5.0], [4.4, 25.4, 11.0], 'extra'),                       # opona na ramieniu (lewa)
         box([2.4, 25.0, 5.6], [4.4, 25.8, 10.4], 'extra'),
         box([11.6, 21.4, 5.0], [14.0, 25.0, 11.0], 'extra'),                     # prawa, węższa
         box([2.2, 22.4, 4.8], [2.6, 24.4, 11.2], 'mesh'),                        # taśma na oponie
         box([3.6, 12.2, 5.1], [12.4, 13.0, 10.9], 'strap'),                      # pas z klamrą
         box([7.4, 12.2, 4.9], [8.6, 13.0, 5.2], 'metal', skip=('south',)),
         box([5.6, 23.6, 5.8], [10.4, 24.8, 10.2], 'cloth2', skip=('up',))]       # szmata na szyi
    for (x, y) in ((4.8, 21.6), (7.4, 21.6), (8.6, 20.6), (11.2, 20.6), (5.0, 14.2), (8.8, 14.2)):   # nity
        e.append(box([x, y, 4.3], [x + 0.5, y + 0.5, 4.6], 'metal', skip=('south',)))
    e += pouch(10.0, 12.9, 1.8, 2.0, zf=4.6, depth=0.5, reg='dark')
    return e


def lowca_helm():
    """Kaptur z brezentu z szalikiem i goglami na czole; twarz odkryta."""
    return [box([3.4, 29.0, 3.4], [12.6, 31.4, 12.6], 'main'),
            box([4.0, 31.4, 4.0], [12.0, 32.2, 12.0], 'main'),
            box([5.4, 32.0, 5.4], [10.6, 32.6, 10.6], 'accent'),
            box([3.2, 24.2, 6.0], [12.8, 29.2, 12.8], 'main'),                    # kaptur po bokach i z tyłu
            box([3.0, 25.0, 11.2], [13.0, 28.0, 13.4], 'accent'),                 # luźny tył
            box([3.6, 24.8, 4.6], [4.4, 29.0, 6.2], 'main'),                      # brzegi kaptura przy twarzy
            box([11.6, 24.8, 4.6], [12.4, 29.0, 6.2], 'main'),
            box([4.0, 28.6, 3.0], [12.0, 29.6, 4.0], 'strap'),                    # opaska
            box([4.6, 29.4, 2.4], [7.4, 30.8, 3.2], 'lens'),                      # gogle spawalnicze na czole
            box([8.6, 29.4, 2.4], [11.4, 30.8, 3.2], 'lens'),
            box([4.4, 29.2, 2.2], [11.6, 29.6, 3.1], 'metal'),
            box([4.4, 21.8, 4.4], [11.6, 24.6, 11.4], 'accent', skip=('up',)),    # gruby szalik
            box([4.0, 22.4, 3.8], [6.4, 24.0, 4.6], 'accent'),
            box([3.0, 29.6, 6.0], [3.4, 31.4, 10.0], 'mesh')]                     # łata z taśmy


def lowca_kamizelka():
    """Skórzana kamizelka warstwowa z pasami na naboje, plecak ze zwiniętym kocem i toporkiem."""
    e = [box([3.8, 12.8, 5.3], [12.2, 23.4, 10.7], 'dark'),
         box([4.0, 22.4, 5.2], [6.6, 24.4, 10.8], 'dark'),
         box([9.4, 22.4, 5.2], [12.0, 24.4, 10.8], 'dark'),
         box([3.8, 18.6, 4.6], [12.2, 22.0, 5.3], 'plate', skip=('south',)),      # warstwy skóry (zakładki)
         box([3.8, 15.2, 4.5], [12.2, 18.8, 5.3], 'extra', skip=('south',)),
         box([3.8, 12.6, 4.4], [12.2, 15.4, 5.3], 'plate', skip=('south',)),
         box([5.0, 23.0, 4.4], [11.0, 25.0, 11.4], 'accent', skip=('up',)),        # futrzany kołnierz
         rotated([4.2, 15.6, 4.25], [5.0, 23.0, 4.55], 'strap', 'z', -22.5, skip=('south',)),    # pas na naboje na skos
         rotated([11.0, 15.6, 4.25], [11.8, 23.0, 4.55], 'strap', 'z', 22.5, skip=('south',)),
         box([2.4, 21.4, 5.0], [4.4, 24.8, 11.0], 'plate'),                        # naramienniki ze skóry
         box([11.6, 21.4, 5.0], [13.6, 24.8, 11.0], 'plate'),
         box([2.2, 24.4, 5.4], [4.2, 25.0, 10.6], 'strap'),
         box([11.8, 24.4, 5.4], [13.8, 25.0, 10.6], 'strap'),
         box([3.6, 12.2, 5.1], [12.4, 13.2, 10.9], 'strap'),                      # pas
         box([7.4, 12.2, 4.8], [8.6, 13.2, 5.2], 'metal', skip=('south',)),
         box([4.8, 11.0, 4.4], [6.4, 13.0, 5.4], 'dark', skip=('south',)),        # nóż w pochwie
         box([4.9, 9.8, 4.6], [5.5, 11.2, 5.0], 'strap', skip=('south',)),
         box([4.8, 11.6, 10.6], [11.2, 23.0, 14.2], 'accent'),                    # plecak/koc
         box([4.4, 21.8, 10.8], [11.6, 24.4, 13.8], 'cloth2'),                    # zrolowany koc
         box([4.4, 21.4, 13.6], [11.6, 24.0, 14.4], 'cloth2'),
         box([5.6, 12.4, 14.0], [6.4, 22.0, 14.6], 'strap'),
         box([9.6, 12.4, 14.0], [10.4, 22.0, 14.6], 'strap'),
         box([7.4, 13.0, 14.2], [8.6, 21.0, 15.2], 'dark'),                       # trzon toporka
         box([6.8, 19.6, 14.4], [9.2, 21.6, 15.4], 'metal')]                      # głowica
    for x in (4.4, 5.4, 6.4, 8.6, 9.6, 10.6):                                      # naboje w pasach
        e.append(box([x, 17.0 + (x - 4.4) * 0.25, 4.0], [x + 0.5, 18.4 + (x - 4.4) * 0.25, 4.3], 'accent', skip=('south',)))
    e += pouch(4.6, 13.2, 1.8, 2.2, zf=4.5, depth=0.5, reg='extra') + pouch(9.2, 13.2, 1.8, 2.2, zf=4.5, depth=0.5, reg='extra')
    return e


def tulacz_helm():
    """Wełniana czapka z wywiniętym brzegiem i cerą; twarz odkryta."""
    return [box([3.4, 29.6, 3.4], [12.6, 31.0, 12.6], 'accent'),
            box([3.8, 31.0, 3.8], [12.2, 32.0, 12.2], 'accent'),
            box([4.6, 32.0, 4.6], [11.4, 32.6, 11.4], 'accent'),
            box([3.2, 28.4, 3.2], [12.8, 29.8, 12.8], 'accent'),                  # wywinięty brzeg
            box([3.4, 25.2, 7.0], [12.6, 28.6, 12.6], 'accent'),                  # tył naciągnięty na uszy
            box([9.0, 30.2, 3.2], [10.6, 31.4, 3.5], 'cloth2', skip=('south',)),  # łata na dziurze
            box([3.1, 30.0, 8.0], [3.3, 31.2, 9.6], 'dark', skip=('east',))]


def tulacz_kamizelka():
    """Stara bluza z kapturem, kawałki kartonu przyklejone taśmą i przewiązane sznurkiem."""
    e = [box([3.7, 12.4, 5.5], [12.3, 23.6, 10.5], 'main'),                       # bluza
         box([4.2, 20.8, 10.4], [11.8, 24.4, 12.2], 'main'),                      # opuszczony kaptur
         box([5.0, 21.4, 12.1], [11.0, 23.8, 12.5], 'dark', skip=('north',)),
         box([5.0, 13.0, 5.2], [11.0, 16.2, 5.55], 'dark', skip=('south',)),      # kieszeń kangurka
         box([6.6, 20.6, 5.2], [6.9, 23.0, 5.5], 'strap', skip=('south',)),       # sznurki kaptura
         box([9.1, 20.0, 5.2], [9.4, 23.0, 5.5], 'strap', skip=('south',)),
         box([4.4, 16.0, 4.9], [11.2, 21.8, 5.5], 'plate', skip=('south',)),      # karton na piersi
         rotated([8.6, 18.4, 4.75], [11.6, 22.2, 5.15], 'plate', 'z', -22.5, skip=('south',)),  # drugi kawałek krzywo
         box([4.4, 14.6, 10.5], [11.6, 21.8, 11.1], 'plate', skip=('north',)),    # karton na plecach
         box([3.6, 16.8, 4.75], [12.4, 17.6, 11.25], 'mesh'),                     # taśma dookoła
         box([3.6, 20.4, 4.75], [12.4, 21.2, 11.25], 'mesh'),
         rotated([5.0, 15.0, 4.3], [5.5, 24.6, 4.6], 'strap', 'z', 22.5),          # sznurek przez ramię
         box([4.6, 23.6, 4.8], [6.0, 24.3, 11.2], 'strap'),
         box([9.6, 14.2, 4.6], [11.0, 15.6, 5.0], 'metal', skip=('south',)),      # wieczko od puszki
         box([3.6, 12.0, 5.3], [12.4, 12.8, 10.7], 'strap')]                       # sznurek zamiast paska
    return e


# ------------------------------------------------------- GHILLIE (snajper)
def sample_surface(rnd, f, t, faces=('north', 'south', 'east', 'west', 'up')):
    dx, dy, dz = t[0] - f[0], t[1] - f[1], t[2] - f[2]
    area = {'north': dx * dy, 'south': dx * dy, 'east': dy * dz, 'west': dy * dz, 'up': dx * dz}
    fs = [x for x in faces if x in area]
    face = rnd.choices(fs, weights=[area[x] for x in fs])[0]
    u, v = rnd.random(), rnd.random()
    if face == 'north':
        return (f[0] + dx * u, f[1] + dy * v, f[2]), face
    if face == 'south':
        return (f[0] + dx * u, f[1] + dy * v, t[2]), face
    if face == 'east':
        return (t[0], f[1] + dy * v, f[2] + dz * u), face
    if face == 'west':
        return (f[0], f[1] + dy * v, f[2] + dz * u), face
    return (f[0] + dx * u, t[1], f[2] + dz * v), face


NRM = {'north': (0, 0, -1), 'south': (0, 0, 1), 'east': (1, 0, 0), 'west': (-1, 0, 0), 'up': (0, 1, 0)}


def leaves(rnd, f, t, count, faces=('north', 'south', 'east', 'west', 'up'), size=1.0, hang=0.5):
    """Liście i strzępy materiału rozsiane po powierzchni pudełka f..t."""
    out = []
    for _ in range(count):
        p, face = sample_surface(rnd, f, t, faces)
        n = NRM[face]
        s = size * rnd.uniform(0.7, 1.35)
        reg = rnd.choice(('leafA', 'leafA', 'leafB', 'leafB', 'leafC', 'bark', 'dark'))
        if rnd.random() < hang:                       # zwisający strzęp
            w, h = 0.7 * s, 1.9 * s
            c = [p[0] + n[0] * 0.5, p[1] + n[1] * 0.5 - (h * 0.35 if face != 'up' else 0), p[2] + n[2] * 0.5]
            f2 = [c[0] - w / 2, c[1] - h / 2, c[2] - 0.12]
            t2 = [c[0] + w / 2, c[1] + h / 2, c[2] + 0.12]
            ax = rnd.choice(('x', 'z'))
        else:                                         # płaski liść
            w, d = 1.6 * s, 1.0 * s
            c = [p[0] + n[0] * 0.45, p[1] + n[1] * 0.45, p[2] + n[2] * 0.45]
            f2 = [c[0] - w / 2, c[1] - 0.1, c[2] - d / 2]
            t2 = [c[0] + w / 2, c[1] + 0.1, c[2] + d / 2]
            ax = rnd.choice(('x', 'z'))
        out.append(rotated(f2, t2, reg, ax, rnd.choice((-22.5, 22.5, -45, 22.5, -22.5))))
    return out


def ghillie_helm(rnd):
    e = head_open('dark', 31.8, thick=0.3) + [
        box([3.3, 24.4, 3.3], [12.7, 29.6, 6.0], 'dark', skip=('south', 'north', 'down'))]  # boki kaptura przy twarzy
    e = e[:-1]
    e += leaves(rnd, [3.0, 28.6, 3.0], [13.0, 32.4, 13.0], 90, size=1.0, hang=0.45)
    e += leaves(rnd, [3.0, 24.4, 6.0], [13.0, 29.0, 13.0], 40, faces=('east', 'west', 'south'), size=1.0, hang=0.5)
    e += leaves(rnd, [3.0, 29.0, 2.4], [13.0, 30.6, 3.0], 12, faces=('north',), size=0.8, hang=0.8)   # frędzle na czole
    return e


def ghillie_kamizelka(rnd):
    e = [box([3.5, 12.4, 5.5], [12.5, 24.2, 10.5], 'main'),
         box([3.5, 24.0, 5.3], [12.5, 24.8, 10.7], 'cloth2'),
         box([0.0, 12.0, 6.0], [4.0, 24.2, 10.0], 'main'),               # rękawy
         box([12.0, 12.0, 6.0], [16.0, 24.2, 10.0], 'main'),
         box([0.0, 14.0, 5.8], [4.0, 15.0, 10.2], 'strap'),
         box([12.0, 14.0, 5.8], [16.0, 15.0, 10.2], 'strap'),
         box([4.0, 12.6, 4.6], [12.0, 14.2, 5.5], 'strap', skip=('south',))]
    e += leaves(rnd, [3.2, 12.0, 5.2], [12.8, 24.6, 10.8], 136, size=1.1, hang=0.5)
    for fx, tx in (([-0.3, 12.0, 5.7], [4.3, 24.6, 10.3]), ([11.7, 12.0, 5.7], [16.3, 24.6, 10.3])):
        e += leaves(rnd, fx, tx, 38, size=1.0, hang=0.55)
    e += leaves(rnd, [3.0, 24.0, 5.0], [13.0, 25.5, 11.0], 35, faces=('up',), size=1.2, hang=0.2)  # naramienniki z liści
    return e


def ghillie_spodnie(rnd):
    e = both([box([3.75, 0.8, 5.75], [8.0, 12.4, 10.25], 'main'),
              box([3.6, 5.0, 5.6], [8.1, 5.7, 10.4], 'strap')]) + [box([3.6, 11.0, 5.6], [12.4, 12.6, 10.4], 'strap')]
    e += leaves(rnd, [3.5, 1.0, 5.5], [8.3, 12.4, 10.5], 64, faces=('north', 'east', 'west', 'south'), size=1.0, hang=0.6)
    e += leaves(rnd, [7.7, 1.0, 5.5], [12.5, 12.4, 10.5], 64, faces=('north', 'east', 'west', 'south'), size=1.0, hang=0.6)
    return e


def ghillie_buty(rnd):
    e = boots_base('dark', 'main', high=4.6)
    e += leaves(rnd, [3.5, 0.5, 4.0], [8.0, 5.0, 10.3], 22, faces=('east', 'west', 'north', 'up'), size=0.8, hang=0.6)
    e += leaves(rnd, [8.0, 0.5, 4.0], [12.5, 5.0, 10.3], 22, faces=('east', 'west', 'north', 'up'), size=0.8, hang=0.6)
    return e


def ghillie_rekawice(rnd):
    e = gloves_base('dark', 'main', cuff=3.0)
    e += leaves(rnd, [-0.2, 11.5, 5.8], [4.2, 15.5, 10.2], 16, faces=('north', 'up', 'east', 'west'), size=0.7, hang=0.6)
    e += leaves(rnd, [11.8, 11.5, 5.8], [16.2, 15.5, 10.2], 16, faces=('north', 'up', 'east', 'west'), size=0.7, hang=0.6)
    return e


# --------------------------------------------------------------- zestawy
ZESTAWY = {
    'cien': {
        'bluza': lambda: sleeves('main', 'dark', pad='dark'),
        'helm': cien_helm, 'kamizelka': cien_kamizelka,
        'spodnie': lambda: pants('main', 'dark', kneepad='dark', holster=True),
        'buty': lambda: boots_base('dark', 'main', high=5.6, plate=None),
        'rekawice': lambda: gloves_base('dark', 'main', plate='plate', cuff=2.5)},
    'lis': {
        'bluza': lambda: sleeves('main', 'dark', pad='dark'),
        'helm': lis_helm, 'kamizelka': lis_kamizelka,
        'spodnie': lambda: pants('main', 'dark', kneepad='dark'),
        'buty': lambda: boots_base('cloth2', 'dark', high=5.4),
        'rekawice': lambda: gloves_base('cloth2', 'dark', cuff=3.0)},
    'legion': {
        'bluza': lambda: sleeves('main', 'dark', pad='plate'),
        'helm': legion_helm, 'kamizelka': legion_kamizelka,
        'spodnie': lambda: pants('main', 'dark', kneepad='plate'),
        'buty': lambda: boots_base('cloth2', 'dark', high=6.0, plate='plate'),
        'rekawice': lambda: gloves_base('cloth2', 'dark', plate='plate', cuff=3.0)},
    'bastion': {
        'bluza': lambda: sleeves('main', 'dark', pad='plate'),
        'helm': bastion_helm, 'kamizelka': bastion_kamizelka,
        'spodnie': lambda: pants('main', 'dark', kneepad='plate', holster=False)
        + both([box([3.5, 6.2, 5.0], [8.2, 10.8, 5.7], 'plate', skip=('south',)),
                box([3.5, 1.2, 5.0], [8.2, 3.2, 5.7], 'plate', skip=('south',))]),
        'buty': lambda: boots_base('dark', 'main', high=6.4, plate='plate'),
        'rekawice': lambda: gloves_base('dark', 'main', plate='plate', cuff=4.0)},
    'ranger': {
        'bluza': lambda: sleeves('main', 'dark', pad='plate', patch='emblem'),
        'helm': ranger_helm, 'kamizelka': ranger_kamizelka,
        'spodnie': lambda: pants('main', 'dark', kneepad='main', holster=False),
        'buty': lambda: boots_base('strap', 'dark', high=4.6),
        'rekawice': lambda: gloves_base('strap', 'dark', cuff=2.0)},
    'zlomiarz': {
        'helm': zlomiarz_helm, 'kamizelka': zlomiarz_kamizelka,
        'bluza': lambda: sleeves('main', 'dark', pad='extra', patch='cloth2'),
        'spodnie': lambda: pants('main', 'dark', kneepad='extra', holster=False),
        'buty': lambda: boots_base('dark', 'extra', high=5.2),
        'rekawice': lambda: gloves_base('dark', 'main', cuff=2.5)},
    'lowca': {
        'helm': lowca_helm, 'kamizelka': lowca_kamizelka,
        'bluza': lambda: sleeves('main', 'dark', pad='plate', patch='cloth2', cuff='strap'),
        'spodnie': lambda: pants('main', 'dark', kneepad='plate', holster=True),
        'buty': lambda: boots_base('dark', 'strap', high=6.2),
        'rekawice': lambda: gloves_base('dark', 'main', cuff=3.0)},
    'tulacz': {
        'helm': tulacz_helm, 'kamizelka': tulacz_kamizelka,
        'bluza': lambda: sleeves('main', 'dark', pad='plate', patch='cloth2', cuff='main'),
        'spodnie': lambda: pants('cloth2', 'dark', kneepad='plate', belt='strap', cargo=False)
        + both([box([3.6, 3.8, 5.1], [8.1, 4.4, 10.4], 'mesh'), box([3.6, 5.2, 5.1], [8.1, 5.8, 10.4], 'mesh')]),
        'buty': lambda: boots_base('cloth2', 'dark', high=3.0, sole='extra')
        + both([box([3.6, 1.2, 4.1], [8.1, 1.9, 10.4], 'mesh')]),
        'rekawice': lambda: gloves_base('accent', 'accent', cuff=2.0)},
    'ghillie': {'helm': ghillie_helm, 'kamizelka': ghillie_kamizelka, 'spodnie': ghillie_spodnie,
                'buty': ghillie_buty, 'rekawice': ghillie_rekawice},
}

PANCERZE = ['%s_%s' % (z, e) for z in ZESTAWY for e in ELEMENTY if e in ZESTAWY[z]]


def build(zestaw, elem):
    fn = ZESTAWY[zestaw][elem]
    rnd = random.Random(sum(map(ord, zestaw + elem)))
    try:
        els = fn(rnd) if zestaw == 'ghillie' else fn()
    except TypeError:
        els = fn()
    tex = 'axon:item/%s_%s' % (zestaw, elem)
    for el in els:               # przesunięcie o -4 w pionie: grzebień hełmu mieści się w limicie 32 modelu
        el['from'][1] = round(el['from'][1] - YSHIFT, 3)
        el['to'][1] = round(el['to'][1] - YSHIFT, 3)
        if 'rotation' in el:
            el['rotation']['origin'][1] = round(el['rotation']['origin'][1] - YSHIFT, 3)
    # tułów i głowa są symetryczne: prawa połowa jest już w modelu, więc lustra nie dodajemy
    return {
        'credit': 'AXON pancerze - generated by gen_pancerze.py (procedural, original)',
        'texture_size': [128, 128],
        'textures': {'t': tex, 'particle': tex},
        'elements': els,
        'display': {
            'fixed': {'rotation': [0, 0, 0], 'translation': [0, 0, 0], 'scale': [1, 1, 1]},
            'gui': {'rotation': [25, 205, 0], 'translation': [0, 0, 0], 'scale': [0.42, 0.42, 0.42]},
            'ground': {'rotation': [0, 0, 0], 'translation': [0, 2, 0], 'scale': [0.3, 0.3, 0.3]},
            'head': {'rotation': [0, 0, 0], 'translation': [0, 0, 0], 'scale': [1, 1, 1]},
        },
    }


def main():
    os.makedirs(OUT, exist_ok=True)
    total = 0
    for z in ZESTAWY:
        tex = texture(z)
        for e in [x for x in ELEMENTY if x in ZESTAWY[z]]:
            name = '%s_%s' % (z, e)
            m = build(z, e)
            for el in m['elements']:
                for a in range(3):
                    assert -16 <= el['from'][a] <= 32 and -16 <= el['to'][a] <= 32, (name, el)
                    assert el['from'][a] <= el['to'][a], (name, el)
            tex.save(os.path.join(OUT, name + '.png'))
            json.dump(m, open(os.path.join(OUT, name + '.json'), 'w'), indent=1)
            json.dump({'model': {'type': 'minecraft:model', 'model': 'axon:block/' + name}},
                      open(os.path.join(OUT, name + '_item.json'), 'w'), indent=1)
            total += len(m['elements'])
            print(name, len(m['elements']))
    print('ok', total, 'elementow')


if __name__ == '__main__':
    main()
