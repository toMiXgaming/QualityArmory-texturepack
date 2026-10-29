#!/usr/bin/env python3
"""Amunicja QualityArmory w stylu AXON (modele 3D z teksturami 128x128).

Podmienia 10 modeli qualityarmory:ammo/<nazwa> (przedmiot phantom_membrane, custom_model_data 1-10),
więc numery modeli i definicje amunicji w pluginie zostają bez zmian. Tekstury leżą w
assets/qualityarmory/textures/axon/ammo_<nazwa>.png (katalog axon/ jest już w atlasie).

Każdy model stoi na y=0, środek na x=8 i z=8, mieści się w 16x16x16, żeby w ekwipunku wyglądał jak przedmiot.
Zapisuje build/ammo_<nazwa>.json i build/ammo_<nazwa>.png.
"""
import json, os, random
from PIL import Image, ImageDraw
import gen_bronie_biale as gb
from gen_bronie_biale import Bron, ALL

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'build')

# materiał -> (kolor, wzór); wzory z gen_bronie_biale plus własne: stripes, glow, cardboard
MAT = {
    'mosiadz': ((190, 150, 64), 'steel'), 'mosiadz_c': ((140, 106, 44), 'steel'),
    'miedz': ((176, 100, 62), 'steel'), 'olow': ((92, 96, 106), 'steel'), 'stal': gb.MAT['stal'],
    'stal_c': gb.MAT['stal_c'], 'czern': gb.MAT['czern'], 'stal_lak': ((92, 88, 76), 'steel'),
    'oliwka': gb.MAT['oliwka'], 'oliwka_c': ((58, 66, 42), 'paint'), 'czerwony': ((172, 40, 32), 'paint'),
    'czerwony_c': ((120, 28, 26), 'paint'), 'zolty': ((214, 176, 42), 'paint'), 'bialy': ((214, 210, 196), 'paint'),
    'karton': ((168, 132, 84), 'cardboard'), 'karton_c': ((124, 94, 58), 'cardboard'),
    'drewno': gb.MAT['drewno'], 'drewno_c': gb.MAT['drewno_c'], 'skora': gb.MAT['skora'],
    'skora_c': gb.MAT['skora_c'], 'guma': gb.MAT['guma'], 'paski': ((220, 180, 30), 'stripes'),
    'cyjan': ((60, 230, 235), 'glow'), 'pomarancz': ((255, 140, 40), 'glow'), 'szmata': gb.MAT['szmata'],
}


def tile(base, kind, rnd):
    if kind == 'cardboard':
        t = Image.new('RGBA', (32, 32), base + (255,))
        px = t.load()
        for y in range(32):
            for x in range(32):
                k = rnd.randint(-5, 5) + (6 if y % 4 == 0 else 0) - (rnd.random() < 0.02) * 18
                px[x, y] = tuple(max(0, min(255, v + k)) for v in base) + (255,)
        return t
    if kind == 'stripes':           # żółto-czarne pasy ostrzegawcze
        t = Image.new('RGBA', (32, 32), base + (255,))
        d = ImageDraw.Draw(t)
        for i in range(-32, 64, 16):
            d.polygon([(i, 32), (i + 8, 32), (i + 40, 0), (i + 32, 0)], fill=(24, 24, 26, 255))
        return t
    if kind == 'glow':              # rdzeń: jasny środek, ciemniejsze brzegi, drobne iskry
        t = Image.new('RGBA', (32, 32), base + (255,))
        px = t.load()
        for y in range(32):
            for x in range(32):
                e = 1 - min(abs(x - 15.5), abs(y - 15.5)) / 16
                k = int(-60 * e) + rnd.randint(-8, 8) + (60 if rnd.random() < 0.04 else 0)
                px[x, y] = tuple(max(0, min(255, v + k)) for v in base) + (255,)
        return t
    return gb.tile32(base, kind, rnd)


class Amo(Bron):
    def texture(self):
        rnd = random.Random(sum(map(ord, self.name)))
        im = Image.new('RGBA', (128, 128), (0, 0, 0, 0))
        assert len(self.mats) <= 16, self.name
        for i, m in enumerate(self.mats):
            base, kind = MAT[m]
            im.paste(tile(base, kind, rnd), ((i % 4) * 32, (i // 4) * 32))
        return im

    def cyl(self, x, z, y0, y1, r, m, tip=None):
        """Walec jako ośmiokąt: prostopadłościan plus drugi obrócony o 45 stopni."""
        a, c = r * 0.96, r * 0.74       # kwadrat i obrócony kwadrat: unia daje przybliżony walec
        self.b([x - a, y0, z - a], [x + a, y1, z + a], m)
        self.b([x - c, y0, z - c], [x + c, y1, z + c], m, skip=('up', 'down'), rot=('y', 45))

    def bullet(self, x, z, y0, h, r, case, head, tip=None):
        """Nabój: łuska, rowek, pocisk zwężony ku górze."""
        hc = h * 0.62
        self.cyl(x, z, y0, y0 + hc, r, case)
        self.b([x - r - 0.05, y0, z - r - 0.05], [x + r + 0.05, y0 + 0.5, z + r + 0.05], case)   # kołnierz
        self.cyl(x, z, y0 + hc, y0 + hc + (h - hc) * 0.55, r * 0.82, head)
        self.cyl(x, z, y0 + hc + (h - hc) * 0.55, y0 + h, r * 0.55, tip or head)







# Jeden przedmiot = jedna sztuka (liczbę pokazuje licznik w slocie), dlatego bez pudełek i skrzynek.
def a9mm(w):
    w.bullet(0, 0, 0, 13, 2.3, 'mosiadz', 'miedz')


def a556(w):
    w.bullet(0, 0, 0, 16, 2.0, 'mosiadz', 'miedz', 'czerwony_c')


def a762(w):
    w.bullet(0, 0, 0, 16, 2.4, 'stal_lak', 'stal_c', 'czerwony')


def ashotgun(w):
    w.cyl(0, 0, 0, 3.4, 3.6, 'mosiadz')
    w.cyl(0, 0, 3.2, 14.5, 3.3, 'czerwony')
    w.cyl(0, 0, 13.0, 14.5, 3.4, 'czerwony_c')
    w.b([-1.4, 14.5, -1.4], [1.4, 15.0, 1.4], 'czerwony_c')                     # zawinięcie
    w.cyl(0, 0, 3.2, 4.0, 3.7, 'mosiadz_c')


def amusket(w):
    w.b([-2.5, 2, -2.5], [2.5, 7, 2.5], 'olow')                                  # kula ołowiana
    w.b([-2, 0.8, -2], [2, 2, 2], 'olow')
    w.b([-2, 7, -2], [2, 8.2, 2], 'olow')
    w.b([-3, 3, -2], [3, 6, 2], 'olow')
    w.b([-2, 3, -3], [2, 6, 3], 'olow')
    w.b([-3.2, 0, -3.2], [3.2, 0.5, 3.2], 'szmata')                              # podkładka ze szmaty
    w.b([-1, 8.2, -1], [1, 10.5, 1], 'szmata')                                   # skręcony papier


def a50cal(w):
    w.bullet(0, 0, 0, 20, 2.8, 'mosiadz', 'miedz', 'czern')


def a40m(w):
    w.cyl(0, 0, 0, 7, 3.2, 'mosiadz')
    w.b([-3.4, 6.6, -3.4], [3.4, 7.3, 3.4], 'stal_c')                            # pierścień
    w.cyl(0, 0, 7.3, 13, 3.0, 'oliwka')
    w.cyl(0, 0, 13, 15.5, 2.2, 'oliwka_c')
    w.cyl(0, 0, 15.5, 16, 1.0, 'stal_c')
    w.b([-3.2, 10, -3.2], [3.2, 11, 3.2], 'zolty')                               # żółty pas


def arpg(w):
    w.cyl(0, 0, 0.0, 6.0, 1.5, 'oliwka')                                        # silnik / tuba
    w.cyl(0, 0, 6.0, 8.0, 2.0, 'oliwka_c')
    w.cyl(0, 0, 8.0, 12.5, 3.0, 'oliwka')                                       # głowica
    w.cyl(0, 0, 12.5, 14.5, 2.2, 'oliwka')
    w.cyl(0, 0, 14.5, 15.8, 1.0, 'stal_c')                                      # zapalnik
    w.b([-3.1, 10.0, -3.1], [3.1, 10.9, 3.1], 'paski')                          # pas ostrzegawczy
    w.b([-3.1, 10.0, -3.1], [3.1, 10.9, 3.1], 'paski', skip=('up', 'down'), rot=('y', 45))
    # statecznik: dwie skrzyżowane płytki
    w.b([-4.8, 0.0, -0.15], [4.8, 4.5, 0.15], 'stal_c')
    w.b([-0.15, 0.0, -4.8], [0.15, 4.5, 4.8], 'stal_c')
    w.cyl(0, 0, -0.0, 0.8, 1.9, 'czern')





def amininuke(w):
    w.cyl(0, 0, 3.0, 11.0, 3.6, 'oliwka')                                       # korpus
    w.cyl(0, 0, 11.0, 14.0, 2.7, 'oliwka')
    w.cyl(0, 0, 14.0, 15.6, 1.4, 'oliwka_c')
    w.cyl(0, 0, 15.6, 16.0, 0.6, 'czerwony')
    w.b([-3.7, 6.0, -3.7], [3.7, 8.0, 3.7], 'paski')                            # znak zagrożenia
    w.b([-3.7, 6.0, -3.7], [3.7, 8.0, 3.7], 'paski', skip=('up', 'down'), rot=('y', 45))
    w.b([-3.9, 3.0, -3.9], [3.9, 3.8, 3.9], 'stal_c')
    w.b([-3.9, 10.4, -3.9], [3.9, 11.0, 3.9], 'stal_c')
    w.b([-6.4, 0.0, -0.25], [6.4, 5.0, 0.25], 'czerwony_c')                     # statecznik
    w.b([-0.25, 0.0, -6.4], [0.25, 5.0, 6.4], 'czerwony_c')
    w.cyl(0, 0, 0.0, 3.0, 1.8, 'stal_c')                                        # dysza


def afusion(w):
    w.cyl(0, 0, 0.0, 2.0, 4.0, 'stal_c')                                        # podstawa
    w.cyl(0, 0, 14.0, 16.0, 4.0, 'stal_c')                                      # głowica
    w.cyl(0, 0, 2.0, 14.0, 3.0, 'cyjan')                                        # rdzeń energii
    w.b([-1.2, 2.0, -1.2], [1.2, 14.0, 1.2], 'pomarancz')                       # żarzący się środek
    for y in (4.0, 8.0, 12.0):
        w.b([-3.7, y, -3.7], [3.7, y + 0.8, 3.7], 'czern')                       # obręcze
    for x, z in ((-4.0, -4.0), (4.0, -4.0), (-4.0, 4.0), (4.0, 4.0)):             # pręty osłony
        w.b([x - 0.45, 2.0, z - 0.45], [x + 0.45, 14.0, z + 0.45], 'stal')


AMMO = [('ammo9mm', a9mm), ('ammo556', a556), ('ammo762', a762), ('ammoshotgun', ashotgun), ('ammorpg', arpg),
        ('ammomusketball', amusket), ('ammo50cal', a50cal), ('ammo40m', a40m), ('ammomininuke', amininuke),
        ('ammofusion', afusion)]
NAZWY = [n for n, _ in AMMO]

# jak w oryginalnych modelach QA, tylko spójne: przedmiot do trzymania w dłoni, w ekwipunku i na ziemi
DISPLAY = {
    'thirdperson_righthand': {'rotation': [0, 45, 0], 'translation': [0, 3, 1], 'scale': [0.3, 0.3, 0.3]},
    'thirdperson_lefthand': {'rotation': [0, 45, 0], 'translation': [0, 3, 1], 'scale': [0.3, 0.3, 0.3]},
    'firstperson_righthand': {'rotation': [0, 45, 0], 'translation': [1, 3, 1], 'scale': [0.45, 0.45, 0.45]},
    'firstperson_lefthand': {'rotation': [0, 45, 0], 'translation': [1, 3, 1], 'scale': [0.45, 0.45, 0.45]},
    'gui': {'rotation': [30, 225, 0], 'translation': [0, -0.5, 0], 'scale': [0.85, 0.85, 0.85]},
    'ground': {'rotation': [0, 0, 0], 'translation': [0, 2, 0], 'scale': [0.35, 0.35, 0.35]},
    'fixed': {'rotation': [30, 225, 0], 'translation': [0, -0.5, 0], 'scale': [0.85, 0.85, 0.85]},
}


def build(name, fn):
    w = Amo(name)
    fn(w)
    tex = 'qualityarmory:axon/' + name.replace('ammo', 'ammo_', 1)
    m = {'credit': 'AXON ammo - generated by gen_ammo.py (procedural, original)',
         'texture_size': [128, 128], 'textures': {'t': tex, 'particle': tex},
         'elements': w.el, 'display': DISPLAY}
    for i, el in enumerate(m['elements']):
        el['name'] = 'e%d' % i
        for a in range(3):
            assert -16 <= el['from'][a] <= el['to'][a] <= 32, (name, el)
    return m, w.texture()


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, fn in AMMO:
        m, tex = build(name, fn)
        base = name.replace('ammo', 'ammo_', 1)
        tex.save(os.path.join(OUT, base + '.png'))
        json.dump(m, open(os.path.join(OUT, base + '.json'), 'w'), indent=1)
        print(name, len(m['elements']))


if __name__ == '__main__':
    main()
