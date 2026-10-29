#!/usr/bin/env python3
"""Bronie białe AXON (modele 3D z teksturami 128x128) dla QualityArmory / AXON.

Każda broń to model przedmiotu axon:<nazwa> (komponent item_model). Broń stoi pionowo:
rękojeść na dole (chwyt około y=3), ostrze/głowica u góry, środek na x=8 i z=8, płaska
strona ostrza widoczna od south/north. Pozycje w ręce (1. i 3. osoba), w ekwipunku i na
ziemi są w "display".

Poziomy: startowe (rurka, kij, maczeta), średnie (toporek, nóż myśliwski, łom),
wojskowe (KA-BAR, saperka, tomahawk) i służbowa (pałka teleskopowa).

Zapisuje build/<nazwa>.json, build/<nazwa>.png, build/<nazwa>_item.json.
"""
import json, os, random
from PIL import Image, ImageDraw
from gen_pancerze import tile as pancerz_tile, refine

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'build')
ALL = ('north', 'south', 'east', 'west', 'up', 'down')

# materiał -> (kolor, wzór); wzory 'steel', 'wood', 'blued' są tutaj, reszta z gen_pancerze
MAT = {
    'stal': ((150, 152, 158), 'steel'), 'stal_j': ((200, 202, 208), 'edge'), 'stal_c': ((96, 98, 104), 'steel'),
    'czern': ((34, 34, 38), 'blued'), 'czern_j': ((70, 72, 78), 'edge'),
    'tasma': ((150, 152, 150), 'duct'), 'drewno': ((128, 90, 54), 'wood'), 'drewno_c': ((88, 60, 36), 'wood'),
    'skora': ((96, 64, 40), 'leather'), 'skora_c': ((70, 46, 30), 'leather'), 'rdza': ((132, 80, 48), 'rust'),
    'szmata': ((112, 96, 74), 'cloth'), 'mosiadz': ((180, 146, 70), 'steel'), 'farba_r': ((150, 42, 34), 'paint'),
    'oliwka': ((84, 92, 58), 'paint'), 'g10': ((44, 46, 44), 'ripstop'), 'guma': ((30, 30, 32), 'rubber'),
    'drut': ((110, 112, 116), 'steel'),
}


def tile32(base, kind, rnd):
    if kind in ('steel', 'edge', 'blued', 'wood'):
        t = Image.new('RGBA', (32, 32), base + (255,))
        px = t.load()
        for y in range(32):
            for x in range(32):
                k = rnd.randint(-4, 4)
                if kind in ('steel', 'blued'):
                    k += 5 if y % 3 == 0 else 0                   # szlif wzdłuż
                    k += -12 if rnd.random() < 0.01 else 0        # ślady użycia
                if kind == 'edge':
                    k += 14 if x > 26 else 0                      # wyostrzona krawędź
                if kind == 'wood':                                # słoje
                    k += int(9 * __import__('math').sin(x * 0.9 + 1.7 * __import__('math').sin(y * 0.21)))
                c = [max(0, min(255, v + k)) for v in base]
                px[x, y] = tuple(c) + (255,)
        d = ImageDraw.Draw(t)
        if kind in ('steel', 'blued'):
            for _ in range(5):                                    # rysy
                x0, y0 = rnd.randint(0, 28), rnd.randint(0, 30)
                d.line([(x0, y0), (x0 + rnd.randint(2, 6), y0 + rnd.randint(-1, 1))],
                       fill=tuple(min(255, v + 40) for v in base) + (255,))
        if kind == 'wood':
            for _ in range(2):                                    # sęk
                cx, cy = rnd.randint(4, 27), rnd.randint(4, 27)
                d.ellipse([cx - 2, cy - 1, cx + 2, cy + 1], fill=tuple(int(v * 0.6) for v in base) + (255,))
        return refine(t, 'plate' if kind != 'wood' else 'cloth', rnd, base)
    return pancerz_tile(base, kind, rnd)


class Bron:
    def __init__(self, name):
        self.name, self.el, self.mats = name, [], []

    def reg(self, m):
        if m not in self.mats:
            self.mats.append(m)
        i = self.mats.index(m)
        return [(i % 4) * 4, (i // 4) * 4, (i % 4) * 4 + 4, (i // 4) * 4 + 4]

    def b(self, f, t, m, skip=(), rot=None):
        """Prostopadłościan w układzie broni (x, z wokół 0, y od dołu rękojeści)."""
        uv = self.reg(m)
        F = [f[0] + 8, f[1], f[2] + 8]
        T = [t[0] + 8, t[1], t[2] + 8]
        e = {'from': [round(v, 3) for v in F], 'to': [round(v, 3) for v in T],
             'faces': {fc: {'uv': uv, 'texture': '#t'} for fc in ALL if fc not in skip}}
        if rot:
            ax, ang = rot
            e['rotation'] = {'origin': [(F[i] + T[i]) / 2 for i in range(3)], 'axis': ax, 'angle': ang}
        self.el.append(e)

    def texture(self):
        rnd = random.Random(sum(map(ord, self.name)))
        im = Image.new('RGBA', (128, 128), (0, 0, 0, 0))
        assert len(self.mats) <= 16, self.name
        for i, m in enumerate(self.mats):
            base, kind = MAT[m]
            im.paste(tile32(base, kind, rnd), ((i % 4) * 32, (i // 4) * 32))
        return im


# ------------------------------------------------------------------ startowe
def rurka(w):
    w.b([-0.6, 0.4, -0.6], [0.6, 27.6, 0.6], 'stal')                           # rura
    w.b([-0.75, 27.4, -0.75], [0.75, 28.4, 0.75], 'stal_c')                    # kolanko na końcu
    w.b([-0.5, 28.4, -0.5], [0.5, 28.8, 0.5], 'czern')
    w.b([-0.7, 0.0, -0.7], [0.7, 0.5, 0.7], 'stal_c')                          # zaślepka
    for i, y in enumerate(range(0, 8)):                                         # taśma na chwycie, nierówno
        o = 0.08 * (i % 3)
        w.b([-0.78 - o, y + 0.4, -0.78], [0.78, y + 1.25, 0.78 + o], 'tasma')
    w.b([-0.8, 7.8, -0.8], [0.8, 8.4, 0.3], 'tasma', rot=('x', 22.5))            # odstający koniec taśmy
    for y in (13, 18.5, 23):                                                    # gwint i rdza
        w.b([-0.66, y, -0.66], [0.66, y + 0.8, 0.66], 'rdza')
    w.b([-0.68, 26.0, -0.68], [0.68, 26.4, 0.68], 'stal_c')


def kij(w):
    for i in range(14):                                                        # pałka zwęża się do rękojeści
        r = 0.55 + i * 0.055
        w.b([-r, 1 + i * 1.95, -r], [r, 2.95 + i * 1.95, r], 'drewno' if i % 4 else 'drewno_c')
    w.b([-0.7, 0, -0.7], [0.7, 1.2, 0.7], 'drewno_c')                           # gałka
    w.b([-0.8, 1.2, -0.8], [0.8, 5.6, 0.8], 'tasma')                            # taśma na chwycie
    rnd = random.Random(5)
    for y in (17.5, 19.5, 21.5, 23.5, 25.5, 27.0):                              # gwoździe w czterech kierunkach
        s = rnd.choice((-1, 1))
        r = 0.55 + (y - 1) / 1.95 * 0.055
        w.b([r - 0.1 if s > 0 else -r - 1.6, y, -0.1], [r + 1.6 if s > 0 else -r + 0.1, y + 0.22, 0.1], 'stal_j')
        w.b([-0.1, y + 1, r - 0.1 if s < 0 else -r - 1.6], [0.1, y + 1.22, r + 1.6 if s < 0 else -r + 0.1], 'stal_j')
        w.b([s * (r + 1.4) - 0.2, y - 0.1, -0.2], [s * (r + 1.4) + 0.2, y + 0.32, 0.2], 'stal_c')   # łebek
    for y in (16.6, 24.6):                                                      # drut owinięty wokół
        w.b([-1.45, y, -1.45], [1.45, y + 0.35, 1.45], 'drut')
        w.b([-1.47, y + 0.5, -1.47], [1.47, y + 0.8, 1.47], 'drut')


def maczeta(w):
    w.b([-0.7, 0.0, -0.5], [0.7, 7.0, 0.5], 'szmata')                          # rękojeść ze szmaty
    for y in (0.6, 2.6, 4.6):
        w.b([-0.78, y, -0.58], [0.78, y + 0.9, 0.58], 'tasma')
    w.b([-1.1, 7.0, -0.65], [1.1, 7.7, 0.65], 'czern')                          # prowizoryczny jelec
    w.b([-1.4, 7.7, -0.14], [1.4, 25.4, 0.14], 'stal')                          # brzeszczot
    w.b([-1.0, 25.4, -0.14], [1.4, 26.6, 0.14], 'stal')
    w.b([-0.2, 26.6, -0.14], [1.4, 27.4, 0.14], 'stal')
    w.b([-1.42, 7.7, -0.16], [-0.9, 25.4, 0.16], 'stal_c')                      # grzbiet
    w.b([0.9, 7.7, -0.15], [1.4, 26.6, 0.15], 'stal_j')                         # zaostrzona krawędź
    y = 8.2
    while y < 25.4:                                                             # zęby piły na grzbiecie
        w.b([-1.85, y, -0.13], [-1.4, y + 0.45, 0.13], 'stal_c')
        y += 0.9
    for y in (9.2, 16.0, 22.4):                                                 # nity i rdza
        w.b([-0.2, y, -0.2], [0.25, y + 0.45, 0.2], 'rdza')
    w.b([-1.2, 12.0, -0.15], [0.3, 13.6, 0.15], 'rdza')


# ------------------------------------------------------------------ średnie
def toporek(w):
    w.b([-0.55, 0.6, -0.45], [0.55, 23.6, 0.45], 'drewno')                     # trzonek
    w.b([-0.7, 0.0, -0.55], [0.7, 1.2, 0.55], 'drewno_c')                       # zgrubienie
    w.b([-0.62, 2.0, -0.5], [0.62, 6.8, 0.5], 'skora')                          # owijka
    for y in (2.4, 4.0, 5.6):
        w.b([-0.66, y, -0.54], [0.66, y + 0.4, 0.54], 'skora_c')
    w.b([-1.2, 20.2, -0.7], [1.2, 24.2, 0.7], 'stal_c')                         # oko głowicy
    w.b([1.2, 20.0, -0.45], [2.6, 24.0, 0.45], 'stal')                          # klin
    w.b([2.6, 19.4, -0.3], [3.8, 24.6, 0.3], 'stal')
    w.b([3.8, 18.8, -0.18], [4.6, 25.2, 0.18], 'stal_j')                        # ostrze
    w.b([-2.2, 20.8, -0.65], [-1.2, 23.4, 0.65], 'stal_c')                      # obuch
    w.b([-0.5, 24.2, -0.4], [0.5, 24.6, 0.4], 'drewno_c')                       # koniec trzonka z klinem


def noz(w):
    y = 1.0
    while y < 6.4:                                                              # pierścienie skóry
        w.b([-0.6, y, -0.45], [0.6, y + 0.7, 0.45], 'skora' if int(y * 10) % 14 < 7 else 'skora_c')
        y += 0.7
    w.b([-0.72, 0.0, -0.55], [0.72, 1.0, 0.55], 'mosiadz')                      # głowica
    w.b([-1.6, 6.4, -0.5], [1.6, 7.0, 0.5], 'mosiadz')                          # jelec
    w.b([-0.9, 7.0, -0.15], [0.9, 15.0, 0.15], 'stal')                          # głownia
    w.b([-0.9, 15.0, -0.15], [0.6, 16.4, 0.15], 'stal')
    w.b([-0.9, 16.4, -0.15], [0.0, 17.4, 0.15], 'stal')                         # sztych
    w.b([0.6, 7.0, -0.16], [0.9, 15.0, 0.16], 'stal_j')
    w.b([-0.5, 8.4, -0.17], [-0.25, 14.0, 0.17], 'stal_c')                      # zbrocze
    w.b([-0.95, 7.2, -0.16], [-0.6, 9.0, 0.16], 'stal_c')                       # wycięcie na kciuk


def lom(w):
    w.b([-0.45, 1.0, -0.45], [0.45, 21.4, 0.45], 'farba_r')                    # pręt
    w.b([-0.75, 0.0, -0.28], [0.75, 1.2, 0.28], 'stal')                         # płaska końcówka
    w.b([-0.9, -0.3, -0.18], [0.9, 0.2, 0.18], 'stal_j')
    w.b([-0.45, 21.0, -0.45], [2.3, 21.9, 0.45], 'farba_r')                     # kolanko
    w.b([1.6, 21.9, -0.45], [2.5, 23.6, 0.45], 'farba_r')
    w.b([-0.2, 23.4, -0.45], [2.5, 24.3, 0.45], 'farba_r')
    w.b([-0.8, 23.5, -0.35], [-0.2, 24.2, 0.35], 'stal')                         # pazur
    w.b([-1.2, 23.6, -0.06], [-0.8, 24.1, 0.06], 'stal_j')
    for y in (6.0, 11.5, 17.0):                                                 # odpryski farby
        w.b([-0.47, y, -0.47], [0.47, y + 0.9, 0.47], 'stal_c')
    w.b([-0.5, 2.4, -0.5], [0.5, 6.0, 0.5], 'guma')                             # gumowa nakładka


# ------------------------------------------------------------------ wojskowe
def kabar(w):
    y = 1.0
    while y < 6.4:                                                              # skórzane pierścienie
        w.b([-0.6, y, -0.45], [0.6, y + 0.55, 0.45], 'skora' if int(y * 20) % 22 < 11 else 'skora_c')
        y += 0.55
    w.b([-0.75, 0.0, -0.55], [0.75, 1.0, 0.55], 'czern')                        # głowica
    w.b([-1.5, 6.4, -0.55], [1.5, 7.0, 0.55], 'stal_c')                         # jelec
    w.b([-0.85, 7.0, -0.15], [0.85, 15.8, 0.15], 'czern')                       # oksydowana głownia
    w.b([-0.85, 15.8, -0.15], [0.35, 17.4, 0.15], 'czern')
    w.b([0.35, 15.4, -0.15], [0.85, 16.4, 0.15], 'czern')                       # clip point
    w.b([0.55, 7.0, -0.16], [0.85, 15.6, 0.16], 'czern_j')                      # krawędź
    w.b([-0.4, 8.0, -0.17], [-0.15, 14.2, 0.17], 'stal_c')                      # zbrocze
    w.b([-0.86, 7.0, -0.16], [-0.55, 8.4, 0.16], 'stal_c')


def saperka(w):
    w.b([-0.5, 0.0, -0.5], [0.5, 15.0, 0.5], 'drewno_c')                        # stylisko
    w.b([-1.7, 0.0, -0.5], [1.7, 0.8, 0.5], 'czern')                            # uchwyt T
    w.b([-1.7, 0.0, -0.5], [-1.0, 2.6, 0.5], 'czern')
    w.b([1.0, 0.0, -0.5], [1.7, 2.6, 0.5], 'czern')
    w.b([-0.8, 15.0, -0.7], [0.8, 16.6, 0.7], 'czern')                          # zawias
    w.b([-1.0, 15.4, -0.8], [1.0, 16.2, 0.8], 'stal')                           # nakrętka blokady
    w.b([-0.55, 16.2, -0.9], [0.55, 16.8, 0.9], 'stal_c')
    w.b([-2.6, 16.6, -0.2], [2.6, 21.6, 0.2], 'oliwka')                         # pióro łopatki
    w.b([-2.0, 21.6, -0.2], [2.0, 22.6, 0.2], 'oliwka')
    w.b([-1.2, 22.6, -0.21], [1.2, 23.2, 0.21], 'stal_j')                       # naostrzone krawędzie
    w.b([-2.65, 17.0, -0.21], [-2.4, 21.4, 0.21], 'stal_j')
    w.b([2.4, 17.0, -0.21], [2.65, 21.4, 0.21], 'stal_j')
    w.b([-0.4, 16.8, -0.3], [0.4, 21.0, 0.3], 'oliwka')                         # przetłoczenie
    for y in (3.0, 6.0, 9.0):
        w.b([-0.54, y, -0.54], [0.54, y + 0.4, 0.54], 'czern')


def tomahawk(w):
    w.b([-0.6, 0.0, -0.45], [0.6, 22.0, 0.45], 'czern')                         # trzonek
    w.b([-0.66, 1.4, -0.52], [0.66, 9.0, 0.52], 'g10')                          # okładzina chwytu
    w.b([-0.7, 0.0, -0.55], [0.7, 0.8, 0.55], 'stal_c')
    w.b([-0.65, 9.0, -0.5], [0.65, 9.4, 0.5], 'stal_c')
    w.b([-1.0, 18.4, -0.6], [1.0, 22.6, 0.6], 'czern')                          # głowica
    w.b([1.0, 18.8, -0.3], [3.0, 22.4, 0.3], 'czern')
    w.b([3.0, 18.0, -0.22], [3.6, 23.0, 0.22], 'czern')
    w.b([3.6, 17.4, -0.15], [4.2, 23.6, 0.15], 'czern_j')                       # ostrze
    w.b([-2.0, 19.8, -0.4], [-1.0, 21.4, 0.4], 'czern')                         # kolec
    w.b([-3.0, 20.2, -0.26], [-2.0, 21.0, 0.26], 'czern')
    w.b([-3.6, 20.4, -0.12], [-3.0, 20.8, 0.12], 'czern_j')
    w.b([1.6, 19.6, -0.32], [2.4, 21.6, 0.32], 'stal_c')                        # otwór odciążający (obwódka)


def palka(w):
    w.b([-0.7, 0.0, -0.7], [0.7, 8.0, 0.7], 'guma')                             # piankowa rękojeść
    w.b([-0.76, 0.0, -0.76], [0.76, 0.8, 0.76], 'stal_c')
    y = 1.2
    while y < 7.6:
        w.b([-0.73, y, -0.73], [0.73, y + 0.22, 0.73], 'czern')                 # rowki
        y += 0.8
    w.b([-0.5, 8.0, -0.5], [0.5, 15.0, 0.5], 'stal')                            # segmenty
    w.b([-0.55, 14.6, -0.55], [0.55, 15.0, 0.55], 'stal_c')
    w.b([-0.4, 15.0, -0.4], [0.4, 21.0, 0.4], 'stal')
    w.b([-0.45, 20.6, -0.45], [0.45, 21.0, 0.45], 'stal_c')
    w.b([-0.3, 21.0, -0.3], [0.3, 26.0, 0.3], 'stal')
    w.b([-0.55, 26.0, -0.55], [0.55, 27.2, 0.55], 'stal_c')                     # końcówka
    w.b([-0.4, 27.2, -0.4], [0.4, 27.5, 0.4], 'stal_c')
    w.b([-0.4, -0.5, -0.4], [0.4, 0.0, 0.4], 'stal_c')                          # zatyczka z otworem na smycz


BRONIE = [('rurka', rurka), ('kij', kij), ('maczeta', maczeta), ('toporek', toporek), ('noz', noz),
          ('lom', lom), ('kabar', kabar), ('saperka', saperka), ('tomahawk', tomahawk), ('palka', palka)]
NAZWY = [n for n, _ in BRONIE]

# Pozycje: chwyt (y ok. 3) w dłoni, broń skierowana w przód i lekko w górę jak miecz.
DISPLAY = {
    'thirdperson_righthand': {'rotation': [0, -90, 10], 'translation': [0, 1.0, 0.5], 'scale': [0.85, 0.85, 0.85]},
    'thirdperson_lefthand': {'rotation': [0, 90, -10], 'translation': [0, 1.0, 0.5], 'scale': [0.85, 0.85, 0.85]},
    'firstperson_righthand': {'rotation': [0, -90, -20], 'translation': [1.13, 0.8, 1.13], 'scale': [0.68, 0.68, 0.68]},
    'firstperson_lefthand': {'rotation': [0, 90, 20], 'translation': [1.13, 0.8, 1.13], 'scale': [0.68, 0.68, 0.68]},
    'gui': {'rotation': [0, 0, -45], 'translation': [-2.5, -2.5, 0], 'scale': [0.6, 0.6, 0.6]},
    'ground': {'rotation': [0, 0, 0], 'translation': [0, -1, 0], 'scale': [0.4, 0.4, 0.4]},
    'fixed': {'rotation': [0, 0, -45], 'translation': [-2.5, -2.5, 0], 'scale': [0.6, 0.6, 0.6]},
    'head': {'rotation': [0, 0, 0], 'translation': [0, 0, 0], 'scale': [1, 1, 1]},
}


def build(name, fn):
    w = Bron(name)
    fn(w)
    tex = 'axon:item/' + name
    m = {'credit': 'AXON bronie biale - generated by gen_bronie_biale.py (procedural, original)',
         'texture_size': [128, 128], 'textures': {'t': tex, 'particle': tex},
         'elements': w.el, 'display': DISPLAY}
    for el in m['elements']:
        for a in range(3):
            assert -16 <= el['from'][a] <= el['to'][a] <= 32, (name, el)
    return m, w.texture()


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, fn in BRONIE:
        m, tex = build(name, fn)
        tex.save(os.path.join(OUT, name + '.png'))
        json.dump(m, open(os.path.join(OUT, name + '.json'), 'w'), indent=1)
        json.dump({'model': {'type': 'minecraft:model', 'model': 'axon:block/' + name}},
                  open(os.path.join(OUT, name + '_item.json'), 'w'), indent=1)
        print(name, len(m['elements']))


if __name__ == '__main__':
    main()
