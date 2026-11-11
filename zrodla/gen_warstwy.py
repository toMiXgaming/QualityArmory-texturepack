#!/usr/bin/env python3
"""Generator płaskich warstw pancerza AXON (equipment layers) w układzie vanilla 64x32 (x4 = 256x128).

Dla każdego zestawu powstają dwie tekstury:
  humanoid/<zestaw>.png          - hełm (głowa), kamizelka (tułów + ramiona z naramiennikami i rękawicami), buty
  humanoid_leggings/<zestaw>.png - ochraniacze nóg (nogi + pas)
oraz equipment/<zestaw>.json. Materiały bierze z palet w QualityArmory-texturepack/zrodla/gen_pancerze.py.
Użycie: gen_warstwy.py [podgląd.png] - zapisuje podgląd; pliki do paczki daje pliki(), dopisuje je dodaj_warstwy.py,
a build_pack.py dokłada je przy pełnej przebudowie.
"""
import json, os, random, sys

S = 4  # skala względem tekstury vanilla 64x32

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_pancerze as G  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

# ---- układ UV pancerza (jednostki: teksele vanilla 64x32) ----
HEAD = dict(top=(8, 0, 16, 8), bottom=(16, 0, 24, 8), right=(0, 8, 8, 16), front=(8, 8, 16, 16),
            left=(16, 8, 24, 16), back=(24, 8, 32, 16))
BODY = dict(top=(20, 16, 28, 20), bottom=(28, 16, 36, 20), right=(16, 20, 20, 32), front=(20, 20, 28, 32),
            left=(28, 20, 32, 32), back=(32, 20, 40, 32))
ARM = dict(top=(44, 16, 48, 20), bottom=(48, 16, 52, 20), right=(40, 20, 44, 32), front=(44, 20, 48, 32),
           left=(48, 20, 52, 32), back=(52, 20, 56, 32))
LEG = dict(top=(4, 16, 8, 20), bottom=(8, 16, 12, 20), right=(0, 20, 4, 32), front=(4, 20, 8, 32),
           left=(8, 20, 12, 32), back=(12, 20, 16, 32))


def sub(rect, x0, y0, x1, y1):
    """Prostokąt względem lewego górnego rogu ściany (jednostki teksela)."""
    return (rect[0] + x0, rect[1] + y0, rect[0] + x1, rect[1] + y1)


class Layer:
    def __init__(self, name):
        self.name = name
        self.img = Image.new('RGBA', (64 * S, 32 * S), (0, 0, 0, 0))
        self.rnd = random.Random(sum(map(ord, name)) * 17)
        self.mat = {}
        pal = G.PALETY[name]
        for reg in G.REG:
            if reg not in pal:
                continue
            base, kind = pal[reg]
            canvas = Image.new('RGBA', (64 * S, 32 * S))
            for ty in range(0, 32 * S, 32):
                for tx in range(0, 64 * S, 32):
                    canvas.paste(G.tile(base, kind, self.rnd), (tx, ty))
            self.mat[reg] = canvas

    def px(self, r):
        x0, y0, x1, y1 = (int(round(v * S)) for v in r)
        return (max(0, min(64 * S, x0)), max(0, min(32 * S, y0)), max(0, min(64 * S, x1)), max(0, min(32 * S, y1)))

    def fill(self, r, reg):
        x0, y0, x1, y1 = self.px(r)
        if x1 <= x0 or y1 <= y0:
            return
        mat = self.mat.get(reg) or self.mat['main']
        self.img.paste(mat.crop((x0, y0, x1, y1)), (x0, y0))

    def color(self, r, col, outline=None):
        d = ImageDraw.Draw(self.img)
        x0, y0, x1, y1 = self.px(r)
        d.rectangle([x0, y0, x1 - 1, y1 - 1], fill=col + (255,) if len(col) == 3 else col,
                    outline=outline)

    def line(self, r, col, w=1):
        d = ImageDraw.Draw(self.img)
        x0, y0, x1, y1 = self.px(r)
        d.line([(x0, y0), (x1 - 1, y1 - 1)], fill=col + (255,), width=w)

    def clear(self, r):
        d = ImageDraw.Draw(self.img)
        x0, y0, x1, y1 = self.px(r)
        d.rectangle([x0, y0, x1 - 1, y1 - 1], fill=(0, 0, 0, 0))

    def shade(self, r, top=1.10, bottom=0.84, side=0.88):
        """Gradient pionowy i ciemniejsze krawędzie tylko na zakrytych pikselach."""
        x0, y0, x1, y1 = self.px(r)
        p = self.img.load()
        h = max(1, y1 - y0 - 1)
        for y in range(y0, y1):
            k = top + (bottom - top) * ((y - y0) / h)
            for x in range(x0, x1):
                if x - x0 < 2 or x1 - 1 - x < 2:
                    kk = k * side
                else:
                    kk = k
                rr, gg, bb, aa = p[x, y]
                if aa:
                    p[x, y] = (min(255, int(rr * kk)), min(255, int(gg * kk)), min(255, int(bb * kk)), aa)

    def bevel(self, r, light=1.25, dark=0.62, t=1):
        """Fazowana ramka płyty: jasna góra i lewo, ciemny dół i prawo."""
        x0, y0, x1, y1 = self.px(r)
        p = self.img.load()
        for i in range(t):
            for x in range(x0, x1):
                self._mul(p, x, y0 + i, light)
                self._mul(p, x, y1 - 1 - i, dark)
            for y in range(y0, y1):
                self._mul(p, x0 + i, y, light)
                self._mul(p, x1 - 1 - i, y, dark)

    @staticmethod
    def _mul(p, x, y, f):
        rr, gg, bb, aa = p[x, y]
        if aa:
            p[x, y] = (min(255, int(rr * f)), min(255, int(gg * f)), min(255, int(bb * f)), aa)

    def rivets(self, r, inset=0.5):
        x0, y0, x1, y1 = r
        col = (190, 190, 186)
        for x, y in ((x0 + inset, y0 + inset), (x1 - inset - 0.25, y0 + inset),
                     (x0 + inset, y1 - inset - 0.25), (x1 - inset - 0.25, y1 - inset - 0.25)):
            self.color((x, y, x + 0.25, y + 0.25), col)

    def noise_holes(self, r, edge, depth, chance=0.55):
        """Postrzępiona krawędź (przezroczyste ząbki), np. dla stroju liściastego."""
        x0, y0, x1, y1 = self.px(r)
        p = self.img.load()
        for x in range(x0, x1):
            n = self.rnd.randint(0, depth * S) if self.rnd.random() < chance else 0
            if edge == 'bottom':
                for y in range(y1 - n, y1):
                    p[x, y] = (0, 0, 0, 0)
            elif edge == 'top':
                for y in range(y0, y0 + n):
                    p[x, y] = (0, 0, 0, 0)

    def leaves(self, r, count, regs=('leafA', 'leafB', 'leafC'), size=1.0):
        d = ImageDraw.Draw(self.img)
        x0, y0, x1, y1 = self.px(r)
        for _ in range(count):
            reg = self.rnd.choice(regs)
            base = G.PALETY[self.name][reg][0]
            k = self.rnd.uniform(0.75, 1.2)
            col = tuple(min(255, int(c * k)) for c in base) + (255,)
            x = self.rnd.randint(x0, max(x0, x1 - 1))
            y = self.rnd.randint(y0, max(y0, y1 - 1))
            w = int(self.rnd.randint(3, 7) * size)
            h = int(self.rnd.randint(1, 3) * size) or 1
            d.ellipse([x, y, min(x1 - 1, x + w), min(y1 - 1, y + h + 1)], fill=col)
            if self.rnd.random() < 0.5:
                d.line([(x, y + h // 2), (min(x1 - 1, x + w), y + h // 2)], fill=tuple(int(c * 0.6) for c in col[:3]) + (255,))


# ---------------------------------------------------------------- elementy

def paint_helm(L, st):
    kind = st['helm']
    shell, trim = st.get('shell', 'main'), st.get('trim', 'dark')
    top = HEAD['top']
    L.fill(top, shell)
    L.fill(HEAD['bottom'], trim)
    cfg = {'cap': (3, 4, 5), 'helmet': (3.4, 6.5, 7.4), 'boonie': (3, 4, 4), 'hood': (3, 8, 8),
           'beanie': (3.4, 4.4, 5.4), 'hardhat': (3, 4.5, 5), 'visor': (3.6, 4.4, 5)}[kind]
    front_rows, side_rows, back_rows = cfg
    L.fill(sub(HEAD['front'], 0, 0, 8, front_rows), shell)
    for face in ('right', 'left'):
        L.fill(sub(HEAD[face], 0, 0, 8, side_rows), shell)
    L.fill(sub(HEAD['back'], 0, 0, 8, back_rows), shell)
    if kind == 'hood':      # kaptur: ramka wokół odkrytej twarzy
        for x0, x1 in ((0, 1.2), (6.8, 8)):
            L.fill(sub(HEAD['front'], x0, 0, x1, 7.5), shell)
    if kind == 'helmet':    # hełm: nauszniki z płyt po bokach
        ear = st.get('ear', 'plate')
        for face in ('right', 'left'):
            L.fill(sub(HEAD[face], 2.5, 3.5, 6.5, 7), ear)
            L.bevel(sub(HEAD[face], 2.5, 3.5, 6.5, 7), t=1)
    # krawędź / daszek
    if kind in ('cap', 'boonie', 'hardhat', 'visor', 'beanie'):
        brim = {'cap': 0.8, 'boonie': 1.0, 'hardhat': 0.8, 'visor': 1.0, 'beanie': 0.6}[kind]
        L.fill(sub(HEAD['front'], 0, front_rows - brim, 8, front_rows), trim)
        for face in ('right', 'left'):
            L.fill(sub(HEAD[face], 0, side_rows - brim, 8, side_rows), trim)
        L.fill(sub(HEAD['back'], 0, back_rows - brim, 8, back_rows), trim)
    if kind in ('helmet', 'hood'):
        L.fill(sub(HEAD['front'], 0, front_rows - 0.7, 8, front_rows), trim)
    if st.get('band'):      # opaska / pasek (np. gogle na czole, zestaw słuchawkowy)
        for face in ('right', 'left', 'back'):
            L.fill(sub(HEAD[face], 0, 2.2, 8, 3.0), st['band'])
        L.fill(sub(HEAD['front'], 0, 2.2, 8, 3.0), st['band'])
    if st.get('rails'):     # szyny na górze i mocowanie noktowizora
        for i in (2.5, 5.5):
            L.fill(sub(HEAD['top'], i, 0.3, i + 0.45, 7.7), 'metal')
        L.fill(sub(HEAD['front'], 3, 0.4, 5, 2.2), 'metal')
        L.bevel(sub(HEAD['front'], 3, 0.4, 5, 2.2))
    if st.get('badge'):     # odznaka na froncie czapki
        L.fill(sub(HEAD['front'], 3.2, 0.6, 4.8, 2.0), st['badge'])
        L.bevel(sub(HEAD['front'], 3.2, 0.6, 4.8, 2.0))
    if st.get('lamp'):      # latarka na kasku
        L.fill(sub(HEAD['front'], 3.2, 0.3, 4.8, 1.5), 'metal')
        L.color(sub(HEAD['front'], 3.5, 0.6, 4.5, 1.2), (236, 226, 160))
    if st.get('leaves'):
        for f in ('top', 'right', 'left', 'back', 'front'):
            L.leaves(HEAD[f], 16)
        L.noise_holes(HEAD['back'], 'bottom', 1)
    for f in ('top', 'right', 'left', 'front', 'back'):
        L.shade(HEAD[f], 1.08, 0.86)
    L.bevel(sub(HEAD['top'], 0, 0, 8, 8), 1.12, 0.8)


def paint_vest(L, st):
    kind = st['vest']
    main, trim = st.get('vmain', 'main'), st.get('vtrim', 'dark')
    plate = st.get('plate', 'plate')
    for f in ('top', 'bottom', 'right', 'left', 'front', 'back'):
        L.fill(BODY[f], main)
    # boki jak kamizelka z paskami (zamknięte, bez prześwitów)
    for f in ('right', 'left'):
        L.fill(sub(BODY[f], 0, 5.0, 4, 12), trim)
        L.fill(sub(BODY[f], 0, 6.2, 4, 6.8), 'strap')
        L.fill(sub(BODY[f], 0, 8.4, 4, 9.0), 'strap')
    if kind == 'leaf':
        for f in BODY:
            L.leaves(BODY[f], 26)
        L.noise_holes(BODY['front'], 'bottom', 1)
        L.noise_holes(BODY['back'], 'bottom', 1)
    elif kind == 'carrier':
        for face, big in (('front', False), ('back', True)):
            r = BODY[face]
            pr = sub(r, 1, 1.4, 7, 8.2 if not big else 8.8)
            L.fill(pr, plate)
            L.bevel(pr, t=1)
            L.rivets(pr)
            for y in (8.9, 9.7):    # taśmy MOLLE
                L.fill(sub(r, 0, y, 8, y + 0.45), 'strap')
        # ładownice z przodu
        r = BODY['front']
        for x0, x1 in ((0.3, 2.7), (2.9, 5.1), (5.3, 7.7)):
            pc = sub(r, x0, 8.6, x1, 11.7)
            L.fill(pc, trim)
            L.bevel(pc, 1.3, 0.55)
            L.fill(sub(r, x0, 8.6, x1, 9.4), 'strap')
            L.color(sub(r, (x0 + x1) / 2 - 0.2, 9.1, (x0 + x1) / 2 + 0.2, 9.7), (170, 170, 164))
        # pasy naramienne
        for x0 in (0.8, 5.7):
            L.fill(sub(r, x0, 0, x0 + 1.5, 1.6), 'strap')
            L.fill(sub(BODY['back'], x0, 0, x0 + 1.5, 1.6), 'strap')
        L.fill(sub(BODY['top'], 0.8, 0, 2.3, 4), 'strap')
        L.fill(sub(BODY['top'], 5.7, 0, 7.2, 4), 'strap')
        if st.get('patch'):
            L.fill(sub(r, 5.2, 2.2, 6.8, 3.4), st['patch'])
    elif kind == 'rig':
        r = BODY['front']
        for row, ys in enumerate((2.2, 5.2, 8.2)):
            for x0, x1 in ((0.5, 3.6), (4.4, 7.5)):
                pc = sub(r, x0, ys, x1, ys + 2.6)
                L.fill(pc, trim if row != 1 else 'cloth2')
                L.bevel(pc, 1.28, 0.55)
                L.fill(sub(r, x0, ys, x1, ys + 0.7), 'strap')
        L.fill(sub(r, 0, 0, 8, 0.8), 'strap')
        L.fill(sub(BODY['back'], 1, 1.5, 7, 7.5), 'cloth2')
        L.fill(sub(BODY['back'], 0.5, 8, 7.5, 11.5), trim)
        L.bevel(sub(BODY['back'], 0.5, 8, 7.5, 11.5))
    elif kind == 'heavy':
        for face in ('front', 'back'):
            r = BODY[face]
            for pr in (sub(r, 0.6, 0.8, 7.4, 5.6), sub(r, 0.8, 6.0, 7.2, 10.2)):
                L.fill(pr, plate)
                L.bevel(pr, 1.3, 0.55, t=1)
                L.rivets(pr)
            L.fill(sub(r, 0, 10.4, 8, 12), 'dark')
        for f in ('right', 'left'):
            pr = sub(BODY[f], 0.4, 1.2, 3.6, 5.0)
            L.fill(pr, plate)
            L.bevel(pr)
        L.fill(sub(BODY['top'], 0, 0, 8, 4), plate)
        L.bevel(sub(BODY['top'], 0, 0, 8, 4))
    elif kind == 'uniform':
        r = BODY['front']
        L.fill(sub(r, 3.8, 0, 4.2, 12), 'accent')              # rząd guzików/zamek
        for y in (2.5, 5, 7.5, 10):
            L.color(sub(r, 3.7, y, 4.3, y + 0.4), (200, 190, 120))
        L.fill(sub(r, 5.0, 2.0, 6.8, 3.8), 'emblem')           # odznaka
        L.bevel(sub(r, 5.0, 2.0, 6.8, 3.8))
        L.fill(sub(r, 0.8, 8.5, 3.0, 11.0), 'cloth2')          # kieszeń
        L.bevel(sub(r, 0.8, 8.5, 3.0, 11.0), 1.2, 0.6)
        L.fill(sub(r, 1, 3.5, 2.6, 5.5), 'metal')              # radio na ramieniu
        L.fill(sub(BODY['back'], 1, 1.5, 7, 9), 'cloth2')
        L.fill(sub(BODY['back'], 1.5, 3.6, 6.5, 4.4), 'accent')   # odblaskowy napis
        L.fill(sub(BODY['back'], 1.5, 5.4, 6.5, 6.2), 'accent')
    elif kind == 'scrap':
        r = BODY['front']
        for i, pr in enumerate((sub(r, 0.4, 0.8, 4.2, 5.4), sub(r, 4.0, 2.6, 7.8, 7.0), sub(r, 1.0, 6.0, 5.0, 10.8))):
            L.fill(pr, plate)
            L.bevel(pr, 1.25, 0.5)
            L.rivets(pr, 0.4)
        L.fill(sub(r, 0, 10.8, 8, 12), 'dark')
        L.fill(sub(BODY['back'], 0.8, 1.4, 7.2, 8.6), plate)
        L.bevel(sub(BODY['back'], 0.8, 1.4, 7.2, 8.6))
    elif kind == 'layers':
        r = BODY['front']
        for y, reg in ((0.5, 'dark'), (3.5, 'plate'), (6.5, 'dark'), (9.2, 'plate')):
            L.fill(sub(r, 0, y, 8, y + 3.0), reg)
            L.bevel(sub(r, 0, y, 8, y + 3.0), 1.15, 0.65)
        for x in (1.0, 2.6, 4.2, 5.8):  # ładunki na pasie
            L.fill(sub(r, x, 9.6, x + 1.1, 11.6), 'metal')
        L.fill(sub(BODY['back'], 0.8, 1.0, 7.2, 7.5), 'strap')
        L.fill(sub(BODY['back'], 1.5, 7.8, 6.5, 11.5), 'cloth2')
    elif kind == 'cardboard':
        r = BODY['front']
        for pr in (sub(r, 0.8, 1.2, 4.0, 6.2), sub(r, 4.2, 2.8, 7.4, 8.0), sub(r, 1.4, 6.6, 5.0, 10.6)):
            L.fill(pr, plate)
            L.bevel(pr, 1.15, 0.7)
            L.fill(sub(pr, 0, pr[3] - pr[1] - 0.5, pr[2] - pr[0], pr[3] - pr[1]), 'metal')
        L.fill(sub(r, 3.2, 8.4, 5.0, 10.0), 'metal')           # wieczko od puszki
        L.line(sub(r, 0, 0.5, 8, 11.5), (120, 112, 90), 1)     # sznurek na skos
    for f in BODY:
        L.shade(BODY[f], 1.08, 0.86)


def paint_arms(L, st):
    pad = st.get('pad', 'plate')
    glove = st.get('glove', 'dark')
    kind = st.get('vest')
    for f in ARM:
        if kind == 'leaf':
            L.fill(ARM[f], st.get('vmain', 'main'))
            L.leaves(ARM[f], 14)
            continue
        # naramiennik (góra ramienia)
        h = 3.6
        L.fill(sub(ARM[f], 0, 0, 4, h) if f not in ('top', 'bottom') else ARM[f] if f == 'top' else (0, 0, 0, 0), pad)
        L.fill(sub(ARM[f], 0, h, 4, h + 0.6) if f not in ('top', 'bottom') else (0, 0, 0, 0), 'strap')
        # rękawica (dół ramienia)
        if f not in ('top',):
            gr = sub(ARM[f], 0, 9.0, 4, 12) if f != 'bottom' else ARM[f]
            L.fill(gr, glove)
            if f != 'bottom':
                L.fill(sub(ARM[f], 0, 9.0, 4, 9.6), 'strap')   # opaska nadgarstka
    if kind != 'leaf':
        L.bevel(sub(ARM['right'], 0.2, 0.2, 3.8, 3.4), 1.2, 0.6)
        L.fill(sub(ARM['back'], 0.6, 9.8, 3.4, 11.0), st.get('knuckle', 'plate')) if st.get('knuckle', 'plate') else None
        if st.get('apatch'):
            L.fill(sub(ARM['right'], 0.8, 1.0, 3.2, 2.6), st['apatch'])
    else:
        L.noise_holes(ARM['front'], 'bottom', 1)
    for f in ARM:
        L.shade(ARM[f], 1.08, 0.86)


def paint_boots(L, st):
    dark = st.get('bmain', 'dark')
    top_row = st.get('bhigh', 7.0)
    for f in LEG:
        if f == 'top':
            continue
        r = LEG[f]
        if f == 'bottom':
            L.fill(r, 'extra' if 'extra' in L.mat else 'dark')
            continue
        L.fill(sub(r, 0, top_row, 4, 12), dark)
        L.fill(sub(r, 0, top_row, 4, top_row + 0.7), st.get('bcuff', 'strap'))
        L.fill(sub(r, 0, 11.0, 4, 12), 'extra' if 'extra' in L.mat else 'dark')   # podeszwa
    fr = LEG['front']
    for y in (top_row + 1.2, top_row + 2.4, top_row + 3.6):   # sznurowanie
        if y < 10.6:
            L.color(sub(fr, 1.2, y, 2.8, y + 0.3), (200, 200, 190))
    if st.get('btoe'):
        L.fill(sub(fr, 0.3, 9.6, 3.7, 11.0), st['btoe'])
        L.bevel(sub(fr, 0.3, 9.6, 3.7, 11.0))
    if st.get('leaves'):
        for f in ('front', 'back', 'right', 'left'):
            L.leaves(sub(LEG[f], 0, top_row, 4, 11), 8)
        L.noise_holes(sub(LEG['front'], 0, top_row, 4, top_row + 1), 'top', 1)
    for f in LEG:
        L.shade(LEG[f], 1.06, 0.84)


def paint_pants(L, st):
    main = st.get('pmain', 'main')
    dark = st.get('pdark', 'dark')
    kind = st.get('pants', 'cargo')
    for f in LEG:
        L.fill(LEG[f], main)
    # pas i biodra
    for f in ('front', 'back', 'right', 'left'):
        L.fill(sub(BODY[f], 0, 8.0, BODY[f][2] - BODY[f][0], 12), main)
        L.fill(sub(BODY[f], 0, 8.0, BODY[f][2] - BODY[f][0], 8.9), st.get('belt', 'strap'))
    L.fill(BODY['bottom'], main)
    L.color(sub(BODY['front'], 3.2, 8.0, 4.8, 8.9), (178, 176, 168))       # klamra
    if kind == 'leaf':
        for f in LEG:
            L.fill(LEG[f], main)
            L.leaves(LEG[f], 18)
        for f in ('front', 'back', 'right', 'left'):
            L.leaves(sub(BODY[f], 0, 8.0, BODY[f][2] - BODY[f][0], 12), 12)
        L.noise_holes(LEG['front'], 'bottom', 1)
        L.noise_holes(LEG['back'], 'bottom', 1)
    else:
        for f in ('front', 'right', 'left', 'back'):
            r = LEG[f]
            L.fill(sub(r, 0, 4.4, 4, 4.9), dark)            # szew nad kolanem
        if kind in ('cargo', 'holster'):
            for f in ('right',):
                pc = sub(LEG[f], 0.4, 1.6, 3.6, 4.0)
                L.fill(pc, dark)
                L.bevel(pc, 1.2, 0.6)
                L.fill(sub(LEG[f], 0.4, 1.6, 3.6, 2.2), 'strap')
            pc = sub(LEG['front'], 0.5, 1.8, 3.5, 4.0)
            L.fill(pc, dark)
            L.bevel(pc, 1.2, 0.6)
        if kind == 'holster':
            L.fill(sub(LEG['left'], 0.3, 0.5, 3.7, 5.0), 'strap')
            L.bevel(sub(LEG['left'], 0.3, 0.5, 3.7, 5.0))
        if st.get('knee', 'plate'):
            for f in ('front', 'right', 'left'):
                kp = sub(LEG[f], 0.2, 5.2, 3.8, 8.2) if f == 'front' else sub(LEG[f], 0.4, 5.4, 3.6, 8.0)
                L.fill(kp, st['knee'] if st.get('knee') else 'plate')
                L.bevel(kp, 1.28, 0.55)
        if st.get('stripe'):
            for f in ('right', 'left'):
                L.fill(sub(LEG[f], 1.6, 0, 2.4, 12), st['stripe'])
        for y in (9.6,):                                   # mankiety
            for f in ('front', 'right', 'left', 'back'):
                L.fill(sub(LEG[f], 0, y, 4, 12), dark)
    for f in LEG:
        L.shade(LEG[f], 1.06, 0.84)
    for f in ('front', 'back', 'right', 'left'):
        L.shade(sub(BODY[f], 0, 8.0, BODY[f][2] - BODY[f][0], 12), 1.04, 0.88)


# ---------------------------------------------------------------- style zestawów
STYLES = {
    'cien': dict(helm='cap', shell='dark', trim='main', band='strap', vest='carrier', vmain='dark', vtrim='dark',
                 plate='plate', pad='dark', glove='main', pants='holster', pmain='dark', pdark='main', knee='plate',
                 bmain='dark', bhigh=6.0),
    'lis': dict(helm='boonie', shell='main', trim='cloth2', band='strap', vest='rig', vmain='main', vtrim='dark',
                pad='cloth2', glove='cloth2', pants='cargo', pmain='main', pdark='dark', knee=None, bmain='cloth2',
                bhigh=6.4),
    'legion': dict(helm='helmet', shell='main', trim='dark', rails=True, ear='plate', vest='carrier', vmain='main',
                   vtrim='dark', plate='plate', pad='main', glove='cloth2', pants='holster', pmain='main',
                   pdark='dark', knee='plate', bmain='cloth2', bhigh=5.8, patch='emblem'),
    'bastion': dict(helm='helmet', shell='plate', trim='dark', rails=True, ear='plate', vest='heavy', vmain='main',
                    plate='plate', pad='plate', glove='dark', pants='holster', pmain='main', pdark='dark',
                    knee='plate', bmain='dark', bhigh=5.4, btoe='plate'),
    'ranger': dict(helm='visor', shell='main', trim='dark', badge='emblem', vest='uniform', vmain='main',
                   vtrim='dark', pad='main', glove='strap', pants='cargo', pmain='main', pdark='dark',
                   knee=None, stripe='accent', bmain='strap', bhigh=6.6, apatch='emblem'),
    'zlomiarz': dict(helm='hardhat', shell='accent', trim='extra', lamp=True, vest='scrap', vmain='dark',
                     plate='plate', pad='extra', glove='dark', knuckle=None, pants='cargo', pmain='main',
                     pdark='cloth2', knee='extra', bmain='dark', bhigh=6.8),
    'lowca': dict(helm='hood', shell='main', trim='dark', band='accent', vest='layers', vmain='dark',
                  pad='plate', glove='dark', knuckle=None, pants='cargo', pmain='main', pdark='dark', knee='plate',
                  bmain='dark', bhigh=5.6),
    'tulacz': dict(helm='beanie', shell='accent', trim='dark', vest='cardboard', vmain='main', plate='plate',
                   pad='plate', glove='accent', knuckle=None, pants='cargo', pmain='cloth2', pdark='dark',
                   knee='plate', bmain='cloth2', bhigh=8.0, btoe='mesh'),
    'ghillie': dict(helm='hood', shell='main', trim='dark', leaves=True, vest='leaf', vmain='main', pants='leaf',
                    pmain='main', bmain='dark', bhigh=6.0, leaves_boots=True),
}


def build(name):
    st = STYLES[name]
    # warstwa 1: głowa, tułów, ramiona, buty (nogi)
    L1 = Layer(name)
    paint_boots(L1, dict(st, leaves=st.get('leaves_boots')))
    paint_vest(L1, st)
    paint_arms(L1, st)
    paint_helm(L1, st)
    # warstwa 2: nogi i pas
    L2 = Layer(name)
    paint_pants(L2, st)
    return L1.img, L2.img


# ---------------------------------------------------------------- podgląd
def preview(layers, out, names=None, zoom=3):
    """Podgląd z przodu, z tyłu i z boku na szarym manekinie (pełna rozdzielczość tekstur)."""
    names = names or list(layers)
    cw, ch = 16 * S, 32 * S
    pad = 8
    im = Image.new('RGBA', (3 * (cw + pad) * zoom + pad, len(names) * (ch + pad) * zoom + pad), (58, 62, 70, 255))
    skin = (156, 156, 160, 255)

    def crop(layer, rect, mirror=False):
        c = layer.crop(tuple(int(v * S) for v in rect))
        return c.transpose(Image.FLIP_LEFT_RIGHT) if mirror else c

    def put(canvas, img, x, y):
        canvas.alpha_composite(img, (int(x * S), int(y * S)))

    def box(canvas, x, y, w, h):
        canvas.paste(skin, (int(x * S), int(y * S), int((x + w) * S), int((y + h) * S)))

    for row, name in enumerate(names):
        l1, l2 = layers[name]
        for col, view in enumerate(('front', 'back', 'right')):
            canvas = Image.new('RGBA', (cw, ch), (0, 0, 0, 0))
            if view == 'right':
                box(canvas, 4, 0, 8, 8)
                box(canvas, 6, 8, 4, 12)
                box(canvas, 6, 20, 4, 12)
                put(canvas, crop(l2, LEG['right']), 6, 20)
                put(canvas, crop(l2, sub(BODY['right'], 0, 8, 4, 12)), 6, 16)
                put(canvas, crop(l1, LEG['right']), 6, 20)
                put(canvas, crop(l1, BODY['right']), 6, 8)
                put(canvas, crop(l1, ARM['right']), 6, 8)
                put(canvas, crop(l1, HEAD['right']), 4, 0)
            else:
                f = view
                for x, y, w, h in ((4, 0, 8, 8), (4, 8, 8, 12), (0, 8, 4, 12), (12, 8, 4, 12), (4, 20, 4, 12), (8, 20, 4, 12)):
                    box(canvas, x, y, w, h)
                legs = [(4, False), (8, True)] if f == 'front' else [(4, True), (8, False)]
                for x, mir in legs:
                    put(canvas, crop(l2, LEG[f], mir), x, 20)
                put(canvas, crop(l2, sub(BODY[f], 0, 8, 8, 12)), 4, 16)
                for x, mir in legs:
                    put(canvas, crop(l1, LEG[f], mir), x, 20)
                put(canvas, crop(l1, BODY[f]), 4, 8)
                arms = [(0, False), (12, True)] if f == 'front' else [(0, True), (12, False)]
                for x, mir in arms:
                    put(canvas, crop(l1, ARM[f], mir), x, 8)
                put(canvas, crop(l1, HEAD[f]), 4, 0)
            big = canvas.resize((cw * zoom, ch * zoom), Image.NEAREST)
            im.alpha_composite(big, (pad + col * (cw + pad) * zoom, pad + row * (ch + pad) * zoom))
    im.save(out)


def pliki():
    """Pliki warstw dla paczki: {ścieżka w zipie: bajty}."""
    import io
    files = {}
    for name in STYLES:
        l1, l2 = build(name)
        for sub_dir, img in (('humanoid', l1), ('humanoid_leggings', l2)):
            buf = io.BytesIO()
            img.save(buf, 'PNG', optimize=True)
            files['assets/axon/textures/entity/equipment/%s/%s.png' % (sub_dir, name)] = buf.getvalue()
        files['assets/axon/equipment/%s.json' % name] = json.dumps(
            {'layers': {'humanoid': [{'texture': 'axon:' + name}],
                        'humanoid_leggings': [{'texture': 'axon:' + name}]}}, indent=2).encode()
    return files


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'build', 'warstwy-podglad.png')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    layers = {name: build(name) for name in STYLES}
    preview(layers, out)
    print('podgląd:', out, '(%d zestawów)' % len(layers))


if __name__ == '__main__':
    main()
