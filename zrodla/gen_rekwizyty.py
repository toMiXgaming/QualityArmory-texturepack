#!/usr/bin/env python3
"""Rekwizyty do struktur AXON-Structure: wrak śmigłowca Mi-8 (jednostka wojskowa) i metalowe łóżko.

Zapisuje do build/: <nazwa>.json (model), <nazwa>.png (tekstura), <nazwa>_item.json (definicja przedmiotu).

Wrak opisany jest w kratkach struktury jednostka.axs (x, y, z jak w pliku), a skrypt przelicza je na
jednostki modelu: 1 kratka = F jednostek, plugin rysuje model ze skalą 16 / F. Ściany leżą dokładnie
w kratkach, które w pliku struktury są barierami, więc kolizja zgadza się z tym, co widać.
"""
import json, os, random
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'build')

# ---------------------------------------------------------------- wspólne


def noise(im, box, base, amp, rnd):
    x1, y1, x2, y2 = box
    for y in range(y1, y2):
        for x in range(x1, x2):
            k = rnd.randint(-amp, amp)
            im.putpixel((x, y), tuple(max(0, min(255, c + k)) for c in base) + (255,))


def stains(im, box, col, n, rnd, r=3):
    d = ImageDraw.Draw(im)
    x1, y1, x2, y2 = box
    for _ in range(n):
        cx, cy = rnd.randint(x1, x2 - 1), rnd.randint(y1, y2 - 1)
        rr = rnd.randint(1, r)
        d.ellipse([cx - rr, cy - rr // 2, cx + rr, cy + rr], fill=col)


def write(name, model, tex):
    os.makedirs(OUT, exist_ok=True)
    tex.save(os.path.join(OUT, name + '.png'))
    json.dump(model, open(os.path.join(OUT, name + '.json'), 'w'), indent=1)
    json.dump({'model': {'type': 'minecraft:model', 'model': 'axon:block/' + name}},
              open(os.path.join(OUT, name + '_item.json'), 'w'), indent=1)


# ---------------------------------------------------------------- wrak Mi-8

F = 2.0                       # jednostek modelu na kratkę
ORIGIN = (51, 22, 93)         # kratka struktury odpowiadająca ...
OFFSET = (-13.5, 0.0, 0.0)    # ... temu punktowi modelu
CENTER = tuple(ORIGIN[i] + (8 - OFFSET[i]) / F for i in range(3))   # środek modelu w strukturze
SCALE = 16 / F

W = {  # obszary tekstury 128x128 w uv (1 uv = 8 px)
    'bok': (0, 0, 12, 2), 'wnetrze': (0, 2, 12, 4), 'dach': (0, 4, 12, 7), 'podloga': (0, 7, 12, 9),
    'kadlub': (12, 0, 16, 4), 'szyba': (12, 4, 16, 7), 'czarny': (12, 7, 14, 9), 'metal': (14, 7, 16, 9),
    'opona': (0, 9, 2, 11), 'czerwony': (2, 9, 4, 11), 'ogon': (4, 9, 12, 10), 'drzwi': (12, 9, 14, 11),
}


def wrak_texture():
    rnd = random.Random(21)
    im = Image.new('RGBA', (128, 128), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    green = (78, 90, 52)
    # bok: kamuflaż, okrągłe okna, szachownica, sadza i rdza
    noise(im, (0, 0, 96, 16), green, 6, rnd)
    stains(im, (0, 0, 96, 16), (96, 88, 56, 255), 30, rnd, 4)
    stains(im, (0, 0, 96, 16), (58, 66, 40, 255), 25, rnd, 4)
    for x in range(22, 80, 11):
        d.ellipse([x, 3, x + 6, 9], fill=(40, 46, 50, 255), outline=(150, 156, 150, 255))
        d.point((x + 2, 4), fill=(120, 140, 150, 255))
    for i in range(4):          # biało-czerwona szachownica
        for j in range(2):
            c = (230, 230, 226, 255) if (i + j) % 2 == 0 else (190, 30, 40, 255)
            d.rectangle([84 + i * 2, 4 + j * 2, 85 + i * 2, 5 + j * 2], fill=c)
    d.line([(0, 15), (95, 15)], fill=(50, 56, 34, 255))
    stains(im, (0, 0, 40, 16), (34, 30, 28, 255), 10, rnd, 3)       # sadza przy silniku
    stains(im, (0, 8, 96, 16), (122, 70, 36, 255), 12, rnd, 2)      # rdza przy dole
    # wnętrze: szaro-zielona blacha z żebrami
    noise(im, (0, 16, 96, 32), (104, 112, 100), 5, rnd)
    for x in range(0, 96, 8):
        d.line([(x, 16), (x, 31)], fill=(80, 86, 76, 255))
    stains(im, (0, 16, 96, 32), (70, 64, 50, 255), 12, rnd, 2)
    # dach
    noise(im, (0, 32, 96, 56), (72, 84, 48), 6, rnd)
    stains(im, (0, 32, 96, 56), (52, 58, 36, 255), 20, rnd, 5)
    for x in range(0, 96, 16):
        d.line([(x, 32), (x, 55)], fill=(56, 64, 38, 255))
    stains(im, (30, 32, 70, 56), (36, 32, 30, 255), 8, rnd, 4)
    # podłoga: blacha ryflowana
    noise(im, (0, 56, 96, 72), (92, 94, 92), 6, rnd)
    for y in range(58, 72, 4):
        for x in range(1 + (y // 4) % 2 * 2, 96, 4):
            d.line([(x, y), (x + 1, y)], fill=(122, 124, 120, 255))
    stains(im, (0, 56, 96, 72), (90, 64, 40, 255), 10, rnd, 3)
    # kadłub ogólnie
    noise(im, (96, 0, 128, 32), green, 6, rnd)
    stains(im, (96, 0, 128, 32), (96, 88, 56, 255), 10, rnd, 4)
    d.rectangle([96, 0, 127, 31], outline=(54, 62, 36, 255))
    # szyba kokpitu: ramki i brudne szkło
    noise(im, (96, 32, 128, 56), (70, 92, 104), 6, rnd)
    for x in (96, 106, 117, 127):
        d.line([(x, 32), (x, 55)], fill=(60, 70, 46, 255), width=2)
    d.line([(96, 43), (127, 43)], fill=(60, 70, 46, 255), width=2)
    d.line([(100, 36), (104, 40)], fill=(170, 190, 200, 255))
    d.line([(110, 46), (115, 52)], fill=(30, 36, 40, 255))
    # czarny (wloty, wydechy), metal, opona
    noise(im, (96, 56, 112, 72), (34, 32, 30), 5, rnd)
    noise(im, (112, 56, 128, 72), (118, 120, 118), 7, rnd)
    d.line([(112, 63), (127, 64)], fill=(80, 82, 82, 255))
    noise(im, (0, 72, 16, 88), (28, 28, 28), 4, rnd)
    d.ellipse([4, 76, 11, 83], fill=(90, 92, 90, 255))
    # czerwono-białe paski statecznika
    for y in range(72, 88):
        c = (190, 30, 40) if (y // 4) % 2 == 0 else (226, 226, 220)
        for x in range(16, 32):
            im.putpixel((x, y), c + (255,))
    # belka ogonowa z napisem i szachownicą
    noise(im, (32, 72, 96, 80), green, 6, rnd)
    for i in range(3):
        for j in range(2):
            c = (230, 230, 226, 255) if (i + j) % 2 == 0 else (190, 30, 40, 255)
            d.rectangle([40 + i * 2, 74 + j * 2, 41 + i * 2, 75 + j * 2], fill=c)
    for k, x in enumerate((54, 58, 62, 66)):    # numer boczny
        d.rectangle([x, 74, x + 2, 77], outline=(220, 220, 210, 255))
    # drzwi przesuwne
    noise(im, (96, 72, 112, 88), (74, 86, 50), 5, rnd)
    d.rectangle([97, 73, 110, 86], outline=(48, 56, 32, 255))
    d.ellipse([101, 75, 106, 80], fill=(40, 46, 50, 255), outline=(150, 156, 150, 255))
    d.line([(98, 83), (102, 83)], fill=(150, 150, 140, 255))
    return im


FACES = ('north', 'south', 'east', 'west', 'up', 'down')


def to_model(b, axis):
    return round((b - ORIGIN[axis]) * F + OFFSET[axis], 4)


def el(f, t, region, special=None, skip=(), rot=None):
    """Element w kratkach struktury; special = {kierunek: obszar} dla wybranych ścian."""
    special = special or {}
    e = {'from': [to_model(f[i], i) for i in range(3)], 'to': [to_model(t[i], i) for i in range(3)],
         'faces': {fc: {'uv': list(W[special.get(fc, region)]), 'texture': '#t'} for fc in FACES if fc not in skip}}
    if rot:
        axis, angle, origin = rot
        e['rotation'] = {'axis': axis, 'angle': angle, 'origin': [to_model(origin[i], i) for i in range(3)]}
    return e


def wrak_model():
    E = []
    # podłoga i spód
    E.append(el([52, 22, 94], [63, 23, 98], 'kadlub', {'up': 'podloga'}))
    # ściany boczne: północna cała, południowa z otworem drzwi (x 55-57)
    E.append(el([52, 23, 94.1], [63, 25, 95], 'kadlub', {'north': 'bok', 'south': 'wnetrze'}))
    E.append(el([52, 23, 97], [55, 25, 97.9], 'kadlub', {'south': 'bok', 'north': 'wnetrze'}))
    E.append(el([57, 23, 97], [63, 25, 97.9], 'kadlub', {'south': 'bok', 'north': 'wnetrze'}))
    E.append(el([57.2, 23, 97.9], [59.2, 25, 98.1], 'drzwi'))                 # odsunięte drzwi
    # dach i zamknięte drzwi tylne
    E.append(el([52, 25, 94.1], [63.2, 26, 97.9], 'dach', {'down': 'wnetrze', 'north': 'kadlub', 'south': 'kadlub'}))
    E.append(el([62.9, 23, 94.1], [64, 25, 97.9], 'kadlub', {'west': 'wnetrze'}))
    # kokpit: przeszklony nos, pod nim osłona
    E.append(el([50.8, 23, 94.4], [53, 25, 97.6], 'szyba', {'east': 'szyba'}))
    E.append(el([50.2, 22.3, 94.7], [52, 23, 97.3], 'kadlub'))
    E.append(el([51.3, 25, 94.7], [53, 25.5, 97.3], 'kadlub'))
    # silniki i przekładnia na dachu
    E.append(el([54, 26, 94.8], [62, 27, 97.2], 'dach', {'east': 'kadlub', 'west': 'czarny'}))
    E.append(el([53.4, 26.1, 95.1], [54, 26.9, 95.9], 'czarny'))
    E.append(el([53.4, 26.1, 96.1], [54, 26.9, 96.9], 'czarny'))
    E.append(el([60.4, 26.2, 94.4], [62.3, 26.8, 94.8], 'czarny'))
    E.append(el([60.4, 26.2, 97.2], [62.3, 26.8, 97.6], 'czarny'))
    # wał i głowica wirnika
    E.append(el([57.6, 27, 95.6], [58.4, 27.6, 96.4], 'metal'))
    E.append(el([57.2, 27.6, 95.2], [58.8, 28, 96.8], 'metal'))
    # łopaty: jedna wygięta w górę, reszta połamana
    E.append(el([58.6, 27.7, 95.85], [68.6, 27.85, 96.15], 'metal', rot=('z', 22.5, (58, 27.8, 96))))
    E.append(el([52.6, 27.7, 95.85], [57.4, 27.85, 96.15], 'metal'))
    E.append(el([57.85, 27.7, 90.6], [58.15, 27.85, 95.4], 'metal', rot=('x', 22.5, (58, 27.8, 96))))
    E.append(el([57.85, 27.7, 96.6], [58.15, 27.85, 99.4], 'metal'))
    # belka ogonowa
    E.append(el([63.2, 24.7, 95.35], [67.5, 25.9, 96.65], 'kadlub', {'north': 'ogon', 'south': 'ogon'}))
    E.append(el([67.5, 24.95, 95.55], [72, 25.75, 96.45], 'kadlub'))
    E.append(el([68.6, 25.25, 94.6], [70.4, 25.45, 97.4], 'kadlub'))            # statecznik
    E.append(el([71, 25.75, 95.8], [72.4, 28.4, 96.2], 'kadlub', {'north': 'czerwony', 'south': 'czerwony'}))
    # śmigło ogonowe
    E.append(el([71.4, 26.9, 96.2], [71.8, 27.3, 96.45], 'metal'))
    E.append(el([71.5, 25.6, 96.45], [71.7, 28.6, 96.55], 'metal'))
    E.append(el([70.1, 27.0, 96.45], [73.1, 27.2, 96.55], 'metal'))
    # zewnętrzne zbiorniki paliwa i podwozie
    E.append(el([52, 22.3, 93.15], [60, 23.9, 94.1], 'kadlub', {'west': 'czarny'}))
    E.append(el([55, 22.3, 97.9], [62, 23.9, 98.85], 'kadlub', {'west': 'czarny'}))
    E.append(el([56, 22, 93.25], [57, 23, 93.95], 'opona'))
    E.append(el([56, 22, 98.05], [57, 23, 98.75], 'opona'))
    E.append(el([51.6, 22, 95.6], [52.4, 22.6, 96.4], 'opona'))
    return {'textures': {'t': 'axon:item/wrak_mi8', 'particle': 'axon:item/wrak_mi8'}, 'elements': E}


# ---------------------------------------------------------------- łóżko (2 kratki, wezgłowie na +z)

L = {'rura': (0, 0, 2, 2), 'materac': (2, 0, 8, 4), 'koc': (8, 0, 16, 4), 'poduszka': (0, 4, 4, 6),
     'koc_bok': (4, 4, 16, 5)}


def lozko_texture():
    rnd = random.Random(5)
    im = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    noise(im, (0, 0, 8, 8), (96, 102, 96), 6, rnd)                     # rura: łuszcząca się farba
    stains(im, (0, 0, 8, 8), (120, 72, 40, 255), 3, rnd, 1)
    noise(im, (8, 0, 32, 16), (196, 190, 170), 5, rnd)                 # materac w paski
    for x in range(9, 32, 4):
        d.line([(x, 0), (x, 15)], fill=(120, 130, 150, 255))
    stains(im, (8, 0, 32, 16), (150, 130, 90, 255), 4, rnd, 2)
    noise(im, (32, 0, 64, 16), (92, 98, 70), 5, rnd)                   # koc wojskowy
    for y in (3, 12):
        d.line([(32, y), (63, y)], fill=(70, 74, 52, 255))
    for x in range(36, 64, 9):
        d.line([(x, 0), (x + 2, 15)], fill=(80, 86, 60, 255))
    noise(im, (0, 16, 16, 24), (214, 210, 196), 5, rnd)                # poduszka
    stains(im, (0, 16, 16, 24), (180, 170, 140, 255), 2, rnd, 2)
    noise(im, (16, 16, 64, 20), (84, 90, 64), 4, rnd)                  # bok koca
    return im


def lozko_model():
    def e(f, t, region, skip=()):
        return {'from': f, 'to': t,
                'faces': {fc: {'uv': list(L[region]), 'texture': '#t'} for fc in FACES if fc not in skip}}
    E = []
    for x in (1, 14):
        E.append(e([x, 0, 22], [x + 1, 14, 23], 'rura'))      # słupki wezgłowia
        E.append(e([x, 0, -7], [x + 1, 9, -6], 'rura'))       # słupki w nogach
        E.append(e([x, 5, -6], [x + 1, 6, 22], 'rura'))       # boczne ramy
    E.append(e([2, 13, 22.2], [14, 14, 22.8], 'rura'))
    E.append(e([2, 9.5, 22.2], [14, 10.5, 22.8], 'rura'))
    for x in (4.5, 7.5, 10.5):
        E.append(e([x, 10.5, 22.3], [x + 1, 13, 22.7], 'rura'))
    E.append(e([2, 8, -6.8], [14, 9, -6.2], 'rura'))
    E.append(e([2, 6, -6], [14, 8.5, 22], 'materac', skip=('down',)))
    E.append(e([1.6, 7.6, -6.4], [14.4, 9.2, 14], 'koc'))
    E.append(e([3.5, 8.5, 15.5], [12.5, 10.5, 21.5], 'poduszka'))
    # zwisający brzeg koca
    E.append(e([1.4, 5.2, -6], [1.6, 9.2, 13.5], 'koc_bok'))
    E.append(e([14.4, 5.2, -6], [14.6, 9.2, 13.5], 'koc_bok'))
    return {'textures': {'t': 'axon:item/lozko', 'particle': 'axon:item/lozko'}, 'elements': E}


if __name__ == '__main__':
    write('wrak_mi8', wrak_model(), wrak_texture())
    write('lozko', lozko_model(), lozko_texture())
    print('wrak: środek modelu w strukturze', CENTER, 'skala', SCALE)
