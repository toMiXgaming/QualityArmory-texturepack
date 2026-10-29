#!/usr/bin/env python3
"""Zestawy pancerzy AXON (modele 3D, nie same tekstury) dla QualityArmory / AXON-Structure.

Każdy element zestawu to osobny model przedmiotu (axon:<zestaw>_<element>) w jednej,
wspólnej "ramie gracza": stopy na y=-4, nogi -4..8, tułów 8..20, głowa 20..28, środek na
x=8 i z=8, przód gracza to strona north (z mniejsze). Dzięki temu plugin stawia wszystkie
elementy w tym samym punkcie (wyświetlacz przedmiotu na graczu) i każdy ląduje na swoim
miejscu. Jednostka modelu = 1 piksel skóry gracza.

Zestawy: cien, lis, legion, bastion, widmo, ranger, ghillie (strój liściasty dla snajperów).
Elementy: helm, kamizelka, spodnie, buty, rekawice.

Zapisuje build/<nazwa>.json, build/<nazwa>.png, build/<nazwa>_item.json.
"""
import json, math, os, random
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'build')
YSHIFT = 4.0
ELEMENTY = ['helm', 'kamizelka', 'spodnie', 'buty', 'rekawice']

# ------------------------------------------------------------------ tekstura
# 16 obszarów 16x16 px w siatce 4x4 (jednostka uv = 4 px, obszar = 4x4 uv).
REG = ['main', 'dark', 'accent', 'plate', 'strap', 'glow', 'metal', 'cloth2',
       'leafA', 'leafB', 'leafC', 'bark', 'lens', 'emblem', 'mesh', 'extra']
RI = {n: i for i, n in enumerate(REG)}

# nazwa -> (kolor, wzór)
PALETY = {
    'cien': {'main': ((38, 40, 44), 'cloth'), 'dark': ((22, 23, 26), 'cloth'), 'accent': ((226, 112, 32), 'cloth'),
             'plate': ((58, 60, 66), 'plate'), 'strap': ((30, 31, 34), 'strap'), 'glow': ((255, 140, 40), 'glow'),
             'metal': ((92, 94, 100), 'plate'), 'cloth2': ((50, 52, 58), 'cloth'), 'lens': ((226, 112, 32), 'lens'),
             'emblem': ((226, 112, 32), 'emblem'), 'mesh': ((20, 20, 22), 'mesh'), 'extra': ((70, 72, 78), 'cloth')},
    'lis': {'main': ((92, 100, 62), 'camo'), 'dark': ((52, 58, 38), 'camo'), 'accent': ((196, 170, 110), 'cloth'),
            'plate': ((74, 78, 56), 'plate'), 'strap': ((60, 52, 38), 'strap'), 'glow': ((200, 200, 120), 'glow'),
            'metal': ((110, 108, 98), 'plate'), 'cloth2': ((130, 118, 84), 'camo'), 'lens': ((190, 150, 70), 'lens'),
            'emblem': ((196, 170, 110), 'emblem'), 'mesh': ((60, 56, 40), 'mesh'), 'extra': ((70, 62, 44), 'cloth')},
    'legion': {'main': ((84, 88, 60), 'cloth'), 'dark': ((48, 50, 36), 'cloth'), 'accent': ((196, 160, 70), 'cloth'),
               'plate': ((64, 68, 52), 'plate'), 'strap': ((40, 38, 30), 'strap'), 'glow': ((120, 255, 140), 'glow'),
               'metal': ((120, 122, 118), 'plate'), 'cloth2': ((150, 130, 90), 'cloth'), 'lens': ((60, 200, 120), 'lens'),
               'emblem': ((220, 190, 90), 'emblem'), 'mesh': ((30, 30, 24), 'mesh'), 'extra': ((100, 96, 70), 'cloth')},
    'bastion': {'main': ((92, 98, 106), 'plate'), 'dark': ((46, 50, 56), 'plate'), 'accent': ((214, 168, 40), 'plate'),
                'plate': ((120, 126, 134), 'plate'), 'strap': ((34, 36, 40), 'strap'), 'glow': ((255, 90, 40), 'glow'),
                'metal': ((150, 156, 164), 'plate'), 'cloth2': ((58, 62, 68), 'cloth'), 'lens': ((255, 90, 40), 'lens'),
                'emblem': ((214, 168, 40), 'emblem'), 'mesh': ((30, 32, 36), 'mesh'), 'extra': ((70, 74, 82), 'plate')},
    'widmo': {'main': ((20, 26, 48), 'carbon'), 'dark': ((10, 12, 24), 'carbon'), 'accent': ((40, 70, 130), 'carbon'),
              'plate': ((30, 38, 66), 'plate'), 'strap': ((14, 16, 28), 'strap'), 'glow': ((60, 230, 255), 'glow'),
              'metal': ((76, 88, 120), 'plate'), 'cloth2': ((26, 32, 58), 'carbon'), 'lens': ((60, 230, 255), 'lens'),
              'emblem': ((60, 230, 255), 'emblem'), 'mesh': ((8, 10, 20), 'mesh'), 'extra': ((40, 48, 80), 'carbon')},
    'ranger': {'main': ((38, 52, 84), 'cloth'), 'dark': ((24, 32, 54), 'cloth'), 'accent': ((190, 196, 204), 'cloth'),
               'plate': ((52, 62, 84), 'plate'), 'strap': ((20, 22, 28), 'strap'), 'glow': ((230, 230, 120), 'glow'),
               'metal': ((200, 180, 90), 'plate'), 'cloth2': ((110, 120, 140), 'cloth'), 'lens': ((60, 90, 150), 'lens'),
               'emblem': ((200, 180, 90), 'emblem'), 'mesh': ((16, 20, 30), 'mesh'), 'extra': ((70, 80, 100), 'cloth')},
    'ghillie': {'main': ((70, 78, 44), 'cloth'), 'dark': ((40, 46, 28), 'cloth'), 'accent': ((120, 100, 60), 'cloth'),
                'plate': ((56, 60, 40), 'plate'), 'strap': ((50, 42, 30), 'strap'), 'glow': ((200, 200, 120), 'glow'),
                'metal': ((100, 100, 90), 'plate'), 'cloth2': ((96, 88, 54), 'cloth'), 'lens': ((60, 70, 40), 'lens'),
                'emblem': ((120, 100, 60), 'emblem'), 'mesh': ((40, 44, 28), 'mesh'), 'extra': ((82, 74, 46), 'cloth'),
                'leafA': ((72, 104, 36), 'leaf'), 'leafB': ((98, 124, 48), 'leaf'), 'leafC': ((126, 112, 54), 'leaf'),
                'bark': ((86, 66, 42), 'bark')},
}


def clamp(c):
    return tuple(max(0, min(255, int(v))) for v in c)


def tile(base, kind, rnd, accent=None):
    """Obszar 16x16 z wzorem."""
    t = Image.new('RGBA', (16, 16), base + (255,))
    px = t.load()
    d = ImageDraw.Draw(t)

    def shade(x, y, k):
        px[x, y] = clamp([base[0] + k, base[1] + k, base[2] + k]) + (255,)

    for y in range(16):
        for x in range(16):
            n = rnd.randint(-5, 5)
            if kind in ('cloth', 'strap'):
                n += 4 if (x + y) % 4 == 0 else 0     # splot tkaniny
                n -= 3 if (x % 2 == 0 and y % 2 == 0) else 0
            elif kind == 'camo':
                n = rnd.randint(-4, 4)
            elif kind == 'carbon':
                n += 6 if ((x // 2 + y // 2) % 2 == 0) else -4
            elif kind == 'plate':
                n = rnd.randint(-4, 4) + (3 if y % 5 == 0 else 0)  # szczotkowany metal
            shade(x, y, n)
    if kind == 'camo':
        for _ in range(7):
            cx, cy, r = rnd.randint(0, 15), rnd.randint(0, 15), rnd.randint(2, 4)
            k = rnd.choice((-26, -18, 20, 28))
            for y in range(16):
                for x in range(16):
                    if (x - cx) ** 2 + (y - cy) ** 2 <= r * r + rnd.randint(-1, 2):
                        shade(x, y, k + rnd.randint(-3, 3))
    if kind == 'plate':
        d.rectangle([0, 0, 15, 15], outline=clamp([base[0] * 0.6, base[1] * 0.6, base[2] * 0.6]) + (255,))
        d.line([(1, 1), (14, 1)], fill=clamp([base[0] * 1.3 + 12, base[1] * 1.3 + 12, base[2] * 1.3 + 12]) + (255,))
        for p in ((2, 2), (13, 2), (2, 13), (13, 13)):
            px[p] = clamp([base[0] * 1.5 + 30, base[1] * 1.5 + 30, base[2] * 1.5 + 30]) + (255,)
    if kind == 'strap':
        d.line([(0, 7), (15, 7)], fill=clamp([base[0] * 0.6, base[1] * 0.6, base[2] * 0.6]) + (255,))
        d.line([(0, 9), (15, 9)], fill=clamp([base[0] * 0.6, base[1] * 0.6, base[2] * 0.6]) + (255,))
    if kind == 'mesh':
        for y in range(16):
            for x in range(16):
                if (x % 3 == 1) and (y % 3 == 1):
                    px[x, y] = clamp([base[0] * 2.2 + 30, base[1] * 2.2 + 30, base[2] * 2.2 + 30]) + (255,)
    if kind == 'glow':
        for y in range(16):
            k = 1.0 - abs(y - 8) / 12.0
            for x in range(16):
                px[x, y] = clamp([base[0] * (0.6 + 0.5 * k) + 20, base[1] * (0.6 + 0.5 * k) + 20,
                                  base[2] * (0.6 + 0.5 * k) + 20]) + (255,)
    if kind == 'lens':
        for y in range(16):
            for x in range(16):
                k = 0.45 + 0.7 * (y / 15.0)
                px[x, y] = clamp([base[0] * k, base[1] * k, base[2] * k]) + (255,)
        d.line([(2, 2), (7, 2)], fill=(255, 255, 255, 255))
        d.line([(2, 3), (4, 3)], fill=(255, 255, 255, 255))
        d.rectangle([0, 0, 15, 15], outline=(10, 10, 12, 255))
    if kind == 'emblem':
        d.rectangle([0, 0, 15, 15], fill=(18, 18, 20, 255))
        d.polygon([(8, 2), (14, 13), (10, 13), (8, 8), (6, 13), (2, 13)], fill=base + (255,))  # litera A
        d.line([(5, 11), (11, 11)], fill=base + (255,))
    if kind == 'leaf':
        for y in range(16):
            for x in range(16):
                shade(x, y, rnd.randint(-10, 10))
        d.line([(0, 8), (15, 8)], fill=clamp([base[0] * 0.65, base[1] * 0.65, base[2] * 0.65]) + (255,))
        for x in range(2, 15, 3):
            d.line([(x, 8), (x + 2, 3)], fill=clamp([base[0] * 0.75, base[1] * 0.75, base[2] * 0.75]) + (255,))
            d.line([(x, 8), (x + 2, 13)], fill=clamp([base[0] * 0.75, base[1] * 0.75, base[2] * 0.75]) + (255,))
    if kind == 'bark':
        for x in range(0, 16, 3):
            d.line([(x, 0), (x + rnd.randint(-1, 1), 15)], fill=clamp([base[0] * 0.6, base[1] * 0.6, base[2] * 0.6]) + (255,))
    return t


def texture(name):
    rnd = random.Random(hash(name) & 0xFFFF)
    rnd.seed(sum(map(ord, name)) * 31)
    pal = PALETY[name]
    im = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    for i, rn in enumerate(REG):
        if rn not in pal:
            base, kind = (120, 120, 120), 'cloth'
        else:
            base, kind = pal[rn]
        im.paste(tile(base, kind, rnd), ((i % 4) * 16, (i // 4) * 16))
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


def pants_base(pal_main, pal_dark, pocket=True, knee='plate', kneesize=1.0, belt='strap', stripe=None):
    el = []
    # prawa noga (x 4..8) + lustro
    leg = [box([3.75, 0.6, 5.75], [8.0, 12.4, 10.25], pal_main)]
    el.append(box([3.6, 11.0, 5.6], [8.1, 12.6, 10.4], belt))          # pas przy biodrach
    if pocket:
        leg.append(box([3.35, 6.0, 6.4], [3.75, 9.4, 9.6], pal_dark))  # kieszeń cargo z boku
        leg.append(box([3.3, 9.0, 6.3], [3.8, 9.5, 9.7], 'strap'))     # klapka
    leg.append(box([4.2, 3.4, 5.4], [7.6, 5.6, 5.75], knee, skip=('south',)))  # nakolannik
    leg.append(box([4.4, 3.7, 5.2], [7.4, 5.3, 5.4], 'metal', skip=('south',)))
    leg.append(box([3.7, 0.6, 5.7], [8.05, 1.6, 10.3], pal_dark))      # mankiet
    if stripe:
        leg.append(box([5.0, 1.8, 5.65], [6.8, 11.0, 5.78], stripe, skip=('south', 'up', 'down')))
    return both(leg) + [box([3.6, 11.0, 5.6], [12.4, 12.6, 10.4], belt)]


def boots_base(main, dark, high=5.0, plate=None, sole='dark'):
    b = [box([3.7, 0.0, 4.2], [8.0, 0.9, 10.3], sole),                 # podeszwa z bieżnikiem
         box([3.8, 0.9, 4.4], [7.95, high, 10.2], main),               # cholewka
         box([4.0, 0.9, 3.9], [7.8, 3.0, 4.5], dark),                  # nosek
         box([3.7, high - 0.8, 5.6], [8.1, high + 0.3, 10.4], dark),   # kołnierz
         box([4.3, 1.0, 4.4], [7.5, 2.0, 4.6], 'strap', skip=('south',))]
    for z in (5.4, 6.8, 8.2):                                          # sznurowanie
        b.append(box([5.4, 3.0 + (z - 5.4) * 0.3, 4.3], [6.6, 3.3 + (z - 5.4) * 0.3, 4.6], 'strap'))
    if plate:
        b.append(box([3.6, 1.0, 8.4], [8.1, 3.4, 10.5], plate))        # ochrona pięty
    return both(b)


def gloves_base(main, dark, plate=None, cuff=3.0):
    # dłonie na dole rąk (x 0..4 prawa), dłoń y ok. 11..14, mankiet wyżej
    g = [box([0.0, 12.0, 6.0], [4.0, 15.0, 10.0], main),                # dłoń
         box([-0.15, 14.4, 5.85], [4.15, 14.4 + cuff * 0.5, 10.15], dark),  # mankiet
         box([0.2, 11.4, 6.3], [3.8, 12.0, 9.7], dark)]                # kłykcie od dołu
    for i in range(4):                                                  # palce
        g.append(box([0.2 + i * 0.9, 11.0, 5.7], [0.9 + i * 0.9, 12.2, 6.2], main))
    if plate:
        g.append(box([0.4, 12.3, 5.5], [3.6, 14.2, 6.0], plate, skip=('south',)))  # osłona kłykci
    g.append(box([3.6, 12.0, 6.3], [4.15, 14.0, 9.7], dark))
    return both(g)


# ----------------------------------------------------------- CIEŃ (lekki)
def cien_helm():
    e = [box([3.5, 24.0, 3.5], [12.5, 32.6, 12.5], 'main'),             # kaptur
         box([3.6, 24.0, 3.3], [12.4, 28.0, 4.6], 'dark', skip=('south',)),  # chusta na twarz
         box([3.5, 28.0, 3.3], [12.5, 29.6, 4.0], 'strap'),              # opaska pod gogle
         box([4.0, 28.3, 3.0], [7.6, 30.9, 3.7], 'lens'),                # szkło gogli
         box([8.4, 28.3, 3.0], [12.0, 30.9, 3.7], 'lens'),
         box([3.8, 28.0, 2.9], [12.2, 28.5, 3.8], 'metal'),              # oprawa dolna
         box([3.8, 30.7, 2.9], [12.2, 31.2, 3.8], 'metal'),
         box([7.6, 28.2, 2.9], [8.4, 31.0, 3.8], 'metal'),               # mostek
         box([3.1, 28.0, 4.0], [3.5, 31.0, 11.8], 'strap'),              # pasek gogli z boku
         box([12.5, 28.0, 4.0], [12.9, 31.0, 11.8], 'strap'),
         box([3.4, 24.3, 11.0], [12.6, 29.0, 13.0], 'dark'),             # płat kaptura na karku
         box([5.0, 32.4, 5.0], [11.0, 32.9, 11.0], 'cloth2'),            # szew
         box([7.4, 30.9, 3.0], [8.6, 32.7, 3.5], 'accent'),              # pomarańczowy znacznik
         box([3.8, 25.0, 3.0], [12.2, 25.6, 3.4], 'mesh', skip=('south',))]  # siatka wentylacyjna
    return e


def cien_kamizelka():
    e = [box([3.6, 12.6, 5.6], [12.4, 24.0, 10.4], 'main'),
         box([3.5, 12.2, 5.5], [12.5, 13.4, 10.5], 'dark'),              # dolny pas
         box([4.0, 22.8, 5.4], [6.2, 24.8, 10.6], 'strap'),              # szelki na ramionach
         box([9.8, 22.8, 5.4], [12.0, 24.8, 10.6], 'strap'),
         box([7.0, 15.0, 5.0], [9.0, 22.5, 5.6], 'dark', skip=('south',)),  # zamek
         box([3.4, 20.5, 6.3], [4.0, 23.5, 9.7], 'plate'),               # ochraniacze barków
         box([12.0, 20.5, 6.3], [12.6, 23.5, 9.7], 'plate')]
    for x0 in (4.0, 6.9, 9.8):                                           # magazynki z przodu
        e.append(box([x0, 14.0, 4.7], [x0 + 2.2, 17.4, 5.6], 'dark', skip=('south',)))
        e.append(box([x0 + 0.1, 17.0, 4.6], [x0 + 2.1, 17.6, 5.7], 'strap', skip=('south',)))
        e.append(box([x0 + 0.9, 16.3, 4.4], [x0 + 1.3, 17.0, 4.7], 'accent', skip=('south',)))
    e += [box([4.4, 19.2, 4.8], [7.0, 21.6, 5.6], 'dark', skip=('south',)),   # kieszeń piersiowa
          box([9.0, 19.2, 4.8], [11.6, 21.6, 5.6], 'dark', skip=('south',)),
          box([4.8, 20.8, 4.6], [6.6, 21.4, 4.9], 'accent', skip=('south',)),
          box([4.6, 12.0, 10.4], [11.4, 21.0, 11.2], 'dark'),            # panel pleców
          box([6.5, 16.0, 11.1], [9.5, 18.0, 11.5], 'emblem', skip=('south',))]
    return e


# ------------------------------------------------------------ LIS (zwiad)
def lis_helm():
    return [box([3.6, 24.4, 3.6], [12.4, 31.4, 12.4], 'main'),           # czapka
            box([3.5, 30.6, 3.5], [12.5, 32.4, 12.5], 'dark'),
            box([4.0, 29.8, 0.6], [12.0, 30.5, 3.7], 'dark'),            # daszek
            box([4.4, 29.6, 0.4], [11.6, 29.9, 3.7], 'strap'),
            box([5.0, 27.0, 3.2], [7.7, 28.6, 3.8], 'lens'),             # gogle opuszczone na oczy
            box([8.3, 27.0, 3.2], [11.0, 28.6, 3.8], 'lens'),
            box([4.8, 26.8, 3.0], [11.2, 27.3, 3.9], 'metal'),
            box([3.4, 24.0, 4.2], [4.2, 28.0, 11.8], 'cloth2'),          # klapki na uszy
            box([11.8, 24.0, 4.2], [12.6, 28.0, 11.8], 'cloth2'),
            box([3.8, 24.2, 11.6], [12.2, 28.0, 12.8], 'cloth2'),        # osłona karku
            box([7.2, 31.4, 2.8], [8.8, 32.0, 3.6], 'emblem', skip=('south',)),
            box([6.0, 32.3, 5.0], [10.0, 32.8, 11.0], 'extra')]          # siatka kamuflażowa


def lis_kamizelka():
    e = [box([3.6, 12.6, 5.6], [12.4, 24.0, 10.4], 'main'),
         box([3.5, 20.6, 5.4], [12.5, 24.6, 10.6], 'cloth2'),
         box([4.5, 12.0, 10.4], [11.5, 23.0, 14.6], 'dark'),             # plecak
         box([5.0, 12.4, 14.6], [11.0, 19.0, 15.4], 'strap'),
         box([4.8, 22.6, 11.5], [11.2, 25.4, 14.4], 'dark'),             # zwinięty koc na plecaku
         box([5.2, 18.0, 15.2], [10.8, 22.0, 15.8], 'accent'),
         box([3.0, 21.4, 6.0], [4.0, 23.6, 10.0], 'plate'),              # naramienniki
         box([12.0, 21.4, 6.0], [13.0, 23.6, 10.0], 'plate'),
         box([4.2, 13.4, 4.8], [7.6, 16.6, 5.6], 'dark', skip=('south',)),
         box([8.4, 13.4, 4.8], [11.8, 16.6, 5.6], 'dark', skip=('south',)),
         box([4.4, 19.0, 4.9], [7.4, 21.8, 5.6], 'cloth2', skip=('south',)),
         box([8.6, 19.0, 4.9], [11.6, 21.8, 5.6], 'cloth2', skip=('south',)),
         box([4.0, 16.4, 4.5], [12.0, 16.9, 5.7], 'strap', skip=('south',)),   # pas z karabinkami
         box([5.0, 17.2, 4.4], [5.8, 18.4, 5.0], 'metal', skip=('south',)),
         box([10.2, 17.2, 4.4], [11.0, 18.4, 5.0], 'metal', skip=('south',))]
    for dz in (0.0, 1.6, 3.2, 4.8):                                      # kieszonki na plecaku
        e.append(box([4.9 + dz * 0.2, 14.0 + dz * 0.4, 15.4], [6.0 + dz * 0.2, 17.0 + dz * 0.4, 15.9], 'extra'))
    return e


# ---------------------------------------------------------- LEGION (średni)
def legion_helm():
    return [box([3.5, 24.2, 3.5], [12.5, 31.8, 12.5], 'main'),           # hełm balistyczny
            box([3.2, 24.6, 3.2], [12.8, 28.6, 12.8], 'plate'),          # krawędź
            box([4.5, 31.6, 4.5], [11.5, 32.8, 11.5], 'main'),           # czasza
            box([3.4, 28.2, 3.0], [12.6, 29.0, 4.0], 'dark'),            # opaska
            box([3.3, 27.0, 5.0], [3.8, 30.6, 9.0], 'metal'),            # szyny boczne
            box([12.2, 27.0, 5.0], [12.7, 30.6, 9.0], 'metal'),
            box([6.6, 30.8, 2.4], [9.4, 32.2, 3.8], 'metal'),            # mocowanie noktowizora
            box([7.0, 31.2, 1.2], [9.0, 32.0, 2.6], 'dark'),
            box([4.2, 30.0, 0.8], [7.4, 31.8, 2.2], 'lens', skip=('south',)),   # noktowizor podniesiony
            box([8.6, 30.0, 0.8], [11.8, 31.8, 2.2], 'lens', skip=('south',)),
            box([4.0, 29.8, 0.7], [12.0, 30.2, 2.4], 'dark'),
            box([3.8, 24.0, 11.4], [12.2, 28.0, 13.0], 'dark'),          # tylny płat
            box([3.9, 24.4, 4.0], [4.6, 28.2, 9.0], 'cloth2'),           # nauszniki
            box([11.4, 24.4, 4.0], [12.1, 28.2, 9.0], 'cloth2'),
            box([6.6, 29.2, 2.9], [9.4, 30.2, 3.5], 'emblem', skip=('south',))]


def legion_kamizelka():
    e = [box([3.4, 12.6, 5.4], [12.6, 24.0, 10.6], 'main'),
         box([3.9, 14.0, 4.6], [12.1, 22.6, 5.5], 'plate', skip=('south',)),   # płyta przednia
         box([4.4, 14.6, 4.3], [11.6, 21.8, 4.7], 'metal', skip=('south',)),
         box([4.0, 14.0, 10.5], [12.0, 22.6, 11.4], 'plate'),            # płyta tylna
         box([2.6, 20.8, 5.8], [4.2, 24.4, 10.2], 'plate'),              # naramienniki
         box([11.8, 20.8, 5.8], [13.4, 24.4, 10.2], 'plate'),
         box([2.2, 19.0, 6.2], [3.4, 21.6, 9.8], 'dark'),
         box([12.6, 19.0, 6.2], [13.8, 21.6, 9.8], 'dark'),
         box([3.0, 12.8, 5.2], [4.0, 14.6, 10.8], 'cloth2'),             # boczne osłony brzucha
         box([12.0, 12.8, 5.2], [13.0, 14.6, 10.8], 'cloth2'),
         box([5.8, 23.6, 4.4], [10.2, 24.9, 11.0], 'dark'),              # kołnierz
         box([4.4, 12.6, 4.6], [11.6, 14.2, 5.6], 'strap', skip=('south',))]
    for x0 in (4.2, 6.2, 8.2, 10.2):                                     # molle: ładownice
        e.append(box([x0, 14.4 - 0.6, 3.9], [x0 + 1.5, 16.8, 4.5], 'cloth2', skip=('south',)))
        e.append(box([x0 + 0.2, 16.3, 3.8], [x0 + 1.3, 16.7, 4.6], 'accent', skip=('south',)))
    e.append(box([5.5, 18.2, 3.9], [10.5, 20.8, 4.4], 'emblem', skip=('south',)))   # naszywka
    return e


# ------------------------------------------------------- BASTION (ciężki)
def bastion_helm():
    return [box([3.0, 24.0, 3.0], [13.0, 32.2, 13.0], 'main'),           # masywny hełm
            box([2.7, 24.4, 2.7], [13.3, 27.6, 13.3], 'plate'),
            box([5.0, 32.0, 4.0], [11.0, 33.4, 12.0], 'dark'),           # grzebień
            box([7.4, 33.0, 3.5], [8.6, 34.2, 12.5], 'accent'),
            box([3.2, 27.0, 1.8], [12.8, 31.4, 3.0], 'dark'),            # przyłbica
            box([3.9, 28.2, 1.4], [12.1, 30.6, 2.0], 'lens'),            # wąska szyba
            box([3.0, 27.0, 1.2], [13.0, 27.6, 3.2], 'metal'),
            box([3.0, 30.8, 1.2], [13.0, 31.6, 3.2], 'metal'),
            box([3.2, 24.0, 1.6], [12.8, 27.0, 3.0], 'plate'),           # szczęka z kratką
            box([5.0, 24.6, 1.2], [11.0, 26.6, 1.7], 'mesh', skip=('south',)),
            box([2.4, 25.0, 5.0], [3.2, 30.0, 11.0], 'metal'),           # nity boczne
            box([12.8, 25.0, 5.0], [13.6, 30.0, 11.0], 'metal'),
            box([3.4, 24.0, 12.6], [12.6, 28.4, 14.0], 'plate')]         # osłona karku


def bastion_kamizelka():
    e = [box([2.8, 12.2, 5.0], [13.2, 24.0, 11.0], 'main'),
         box([3.4, 13.0, 4.0], [12.6, 23.0, 5.0], 'plate', skip=('south',)),
         box([4.0, 14.0, 3.6], [12.0, 17.0, 4.1], 'metal', skip=('south',)),    # żebra
         box([4.0, 18.0, 3.6], [12.0, 21.0, 4.1], 'metal', skip=('south',)),
         box([6.4, 17.0, 3.4], [9.6, 18.0, 4.2], 'accent'),
         box([3.4, 13.0, 11.0], [12.6, 23.0, 12.0], 'plate'),
         box([1.6, 21.0, 5.0], [4.6, 25.2, 11.0], 'plate'),              # duże naramienniki
         box([11.4, 21.0, 5.0], [14.4, 25.2, 11.0], 'plate'),
         box([1.2, 19.4, 5.4], [3.6, 21.6, 10.6], 'metal'),
         box([12.4, 19.4, 5.4], [14.8, 21.6, 10.6], 'metal'),
         box([1.2, 22.4, 5.2], [3.0, 23.0, 10.8], 'accent'),
         box([13.0, 22.4, 5.2], [14.8, 23.0, 10.8], 'accent'),
         box([5.0, 23.4, 4.4], [11.0, 25.6, 11.6], 'dark'),              # kołnierz
         box([3.6, 12.2, 4.4], [12.4, 14.2, 5.2], 'dark'),               # tasset
         box([4.0, 10.8, 4.6], [7.6, 12.2, 5.4], 'plate', skip=('south',)),
         box([8.4, 10.8, 4.6], [12.0, 12.2, 5.4], 'plate', skip=('south',))]
    for x in (4.2, 11.4):
        for y in (14.0, 18.5, 22.0):
            e.append(box([x, y, 3.4], [x + 0.5, y + 0.5, 3.7], 'metal', skip=('south',)))
    e.append(box([6.6, 19.4, 3.5], [9.4, 22.2, 4.0], 'emblem', skip=('south',)))
    return e


# ---------------------------------------------------------- WIDMO (elitarny)
def widmo_helm():
    return [box([3.4, 24.0, 3.4], [12.6, 32.4, 12.6], 'main'),
            box([3.0, 24.0, 2.6], [13.0, 29.2, 4.0], 'dark'),            # pełna maska
            box([3.6, 27.4, 1.9], [12.4, 30.2, 2.7], 'lens'),            # wizjer pasmowy
            box([7.6, 24.2, 1.6], [8.4, 27.2, 3.0], 'glow'),             # filtr świecący
            box([4.0, 24.6, 1.8], [7.0, 26.4, 2.8], 'mesh', skip=('south',)),
            box([9.0, 24.6, 1.8], [12.0, 26.4, 2.8], 'mesh', skip=('south',)),
            box([7.4, 32.2, 4.0], [8.6, 33.4, 12.6], 'accent'),          # grzbiet
            box([3.0, 29.8, 4.0], [3.5, 31.6, 11.0], 'glow'),            # świecące linie
            box([12.5, 29.8, 4.0], [13.0, 31.6, 11.0], 'glow'),
            box([2.8, 25.0, 9.0], [3.8, 28.0, 12.6], 'metal'),           # moduł komunikacji
            box([12.2, 25.0, 9.0], [13.2, 28.0, 12.6], 'metal'),
            box([3.8, 24.0, 12.4], [12.2, 28.6, 13.6], 'plate'),
            box([2.6, 28.4, 8.6], [3.0, 31.0, 9.0], 'glow')]


def widmo_kamizelka():
    e = [box([3.8, 12.6, 5.8], [12.2, 24.0, 10.2], 'main'),
         box([4.4, 14.0, 5.0], [11.6, 22.6, 5.9], 'plate', skip=('south',)),
         box([7.5, 14.4, 4.7], [8.5, 22.2, 5.0], 'glow', skip=('south',)),     # linia świetlna
         box([5.0, 21.4, 4.7], [11.0, 21.8, 5.0], 'glow', skip=('south',)),
         box([5.0, 15.6, 4.7], [7.2, 16.0, 5.0], 'glow', skip=('south',)),
         box([8.8, 15.6, 4.7], [11.0, 16.0, 5.0], 'glow', skip=('south',)),
         box([4.2, 22.6, 5.4], [11.8, 24.6, 10.6], 'dark'),
         box([2.8, 21.0, 5.6], [4.6, 24.0, 10.4], 'plate'),
         box([11.4, 21.0, 5.6], [13.2, 24.0, 10.4], 'plate'),
         box([2.4, 20.0, 6.0], [3.2, 22.6, 10.0], 'glow'),
         box([12.8, 20.0, 6.0], [13.6, 22.6, 10.0], 'glow'),
         box([5.4, 13.0, 10.2], [10.6, 22.0, 11.6], 'metal'),            # rdzeń zasilania z tyłu
         box([7.2, 14.0, 11.5], [8.8, 21.0, 11.9], 'glow'),
         box([3.6, 12.2, 5.6], [12.4, 13.8, 10.4], 'dark'),
         box([4.8, 15.2, 4.8], [5.8, 19.6, 5.4], 'accent', skip=('south',)),
         box([10.2, 15.2, 4.8], [11.2, 19.6, 5.4], 'accent', skip=('south',))]
    return e


# --------------------------------------------------------- RANGER (służbowy)
def ranger_helm():
    return [box([3.6, 24.4, 3.6], [12.4, 30.6, 12.4], 'main'),           # czapka garnizonowa
            box([3.4, 29.8, 3.4], [12.6, 31.8, 12.6], 'dark'),
            box([4.4, 31.6, 4.4], [11.6, 32.4, 11.6], 'main'),
            box([4.0, 28.4, 0.8], [12.0, 29.4, 3.8], 'dark'),            # daszek
            box([3.5, 29.0, 3.0], [12.5, 30.0, 4.0], 'accent'),          # otok
            box([6.8, 29.4, 2.6], [9.2, 31.8, 3.6], 'metal'),            # odznaka
            box([7.4, 30.0, 2.4], [8.6, 31.2, 2.8], 'emblem', skip=('south',)),
            box([3.2, 27.0, 3.8], [3.8, 28.4, 5.0], 'metal'),            # guziki
            box([12.2, 27.0, 3.8], [12.8, 28.4, 5.0], 'metal'),
            box([3.8, 24.2, 11.6], [12.2, 28.6, 12.6], 'dark')]


def ranger_kamizelka():
    e = [box([3.6, 12.6, 5.6], [12.4, 24.0, 10.4], 'main'),
         box([2.8, 12.6, 5.6], [13.2, 24.4, 10.4], 'cloth2', skip=('up', 'down')),  # jasna koszula
         box([3.9, 13.0, 5.2], [12.1, 23.0, 5.7], 'dark'),               # kamizelka odblaskowa
         box([4.0, 15.2, 4.9], [12.0, 16.6, 5.3], 'accent', skip=('south',)),    # odblaski
         box([4.0, 19.2, 4.9], [12.0, 20.6, 5.3], 'accent', skip=('south',)),
         box([3.6, 12.0, 5.4], [12.4, 13.6, 10.6], 'strap'),             # pas z kaburą
         box([3.1, 12.2, 6.0], [3.6, 17.0, 9.0], 'dark'),                # kabura (prawy bok)
         box([2.9, 15.8, 6.2], [3.3, 17.2, 8.8], 'strap'),
         box([5.0, 12.0, 4.8], [7.0, 14.0, 5.6], 'dark', skip=('south',)),
         box([9.0, 12.0, 4.8], [11.0, 14.0, 5.6], 'dark', skip=('south',)),
         box([8.8, 20.6, 4.8], [11.2, 22.6, 5.5], 'metal', skip=('south',)),     # odznaka
         box([9.4, 21.0, 4.6], [10.6, 22.2, 5.0], 'emblem', skip=('south',)),
         box([4.4, 21.0, 4.8], [7.2, 22.0, 5.5], 'dark', skip=('south',)),       # krótkofalówka
         box([5.4, 22.0, 4.6], [5.9, 24.4, 5.2], 'strap'),
         box([5.4, 18.0, 10.4], [10.6, 22.0, 10.6], 'emblem', skip=('north',)),  # napis z tyłu
         box([5.6, 14.0, 10.4], [10.4, 17.0, 10.6], 'accent', skip=('north',))]
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
    e = [box([3.4, 24.0, 3.4], [12.6, 32.4, 12.6], 'dark'),              # kaptur
         box([4.2, 25.0, 2.8], [11.8, 28.6, 3.6], 'extra'),              # siatka na twarz
         box([4.4, 28.8, 2.8], [11.6, 29.8, 3.6], 'dark')]
    e += leaves(rnd, [3.0, 24.0, 3.0], [13.0, 33.0, 13.0], 112, size=1.0, hang=0.45)
    e += leaves(rnd, [3.0, 29.0, 2.4], [13.0, 31.5, 3.0], 19, faces=('north',), size=0.9, hang=0.8)  # frędzle na czole
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
def _spodnie(main, dark, **kw):
    return lambda rnd=None: pants_base(main, dark, **kw)


ZESTAWY = {
    'cien': {
        'helm': cien_helm, 'kamizelka': cien_kamizelka,
        'spodnie': lambda: pants_base('main', 'dark', pocket=True, knee='plate', stripe='accent'),
        'buty': lambda: boots_base('dark', 'main', high=5.0, plate='plate'),
        'rekawice': lambda: gloves_base('dark', 'main', plate='plate', cuff=2.5)},
    'lis': {
        'helm': lis_helm, 'kamizelka': lis_kamizelka,
        'spodnie': lambda: pants_base('main', 'dark', pocket=True, knee='cloth2'),
        'buty': lambda: boots_base('cloth2', 'dark', high=5.4),
        'rekawice': lambda: gloves_base('cloth2', 'dark', cuff=3.0)},
    'legion': {
        'helm': legion_helm, 'kamizelka': legion_kamizelka,
        'spodnie': lambda: pants_base('main', 'dark', pocket=True, knee='plate', kneesize=1.3),
        'buty': lambda: boots_base('cloth2', 'dark', high=6.0, plate='plate'),
        'rekawice': lambda: gloves_base('main', 'dark', plate='plate', cuff=3.0)},
    'bastion': {
        'helm': bastion_helm, 'kamizelka': bastion_kamizelka,
        'spodnie': lambda: pants_base('dark', 'main', pocket=False, knee='plate', belt='metal')
        + both([box([3.5, 6.2, 5.0], [8.2, 10.8, 5.7], 'plate', skip=('south',)),     # płyty na udach
                box([3.5, 1.0, 5.0], [8.2, 3.2, 5.7], 'plate', skip=('south',)),      # golenie
                box([3.4, 8.0, 5.8], [3.9, 10.5, 10.2], 'metal')]),
        'buty': lambda: boots_base('main', 'dark', high=6.4, plate='plate'),
        'rekawice': lambda: gloves_base('dark', 'main', plate='plate', cuff=4.0)},
    'widmo': {
        'helm': widmo_helm, 'kamizelka': widmo_kamizelka,
        'spodnie': lambda: pants_base('main', 'dark', pocket=False, knee='plate', stripe='glow'),
        'buty': lambda: boots_base('main', 'dark', high=5.4, plate='plate', sole='glow'),
        'rekawice': lambda: gloves_base('main', 'dark', plate='plate', cuff=3.0)},
    'ranger': {
        'helm': ranger_helm, 'kamizelka': ranger_kamizelka,
        'spodnie': lambda: pants_base('main', 'dark', pocket=True, knee='main', stripe='accent'),
        'buty': lambda: boots_base('strap', 'dark', high=4.6),
        'rekawice': lambda: gloves_base('strap', 'dark', cuff=2.0)},
    'ghillie': {'helm': ghillie_helm, 'kamizelka': ghillie_kamizelka, 'spodnie': ghillie_spodnie,
                'buty': ghillie_buty, 'rekawice': ghillie_rekawice},
}
PANCERZE = ['%s_%s' % (z, e) for z in ZESTAWY for e in ELEMENTY]


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
        'texture_size': [64, 64],
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
        for e in ELEMENTY:
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
