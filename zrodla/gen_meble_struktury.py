#!/usr/bin/env python3
"""Meble do struktur AXON-Structure, trzecia partia: wyposażenie zamiast bloków udających przedmioty.

Tak samo jak gen_meble.py i gen_sklep.py: jedna kratka (szafa i automat do gier dwie), przód modelu na
południe = +z, tekstura 64x64 z kafelków 16x16 px (w modelu uv 4x4). Plugin zamienia bloki-nośniki
(szkliwiona terakota, `meble.bloki` w configu AXON-Structure) na barierę i stawia na nich te modele.
Zapisuje build/<nazwa>.json, build/<nazwa>.png i build/<nazwa>_item.json.
"""
from gen_rekwizyty import noise, stains
from gen_meble import model, plain

RUST = (120, 72, 40, 255)
DIRT = (70, 62, 50, 255)


def rect(d, x0, y0, x1, y1, col):
    d.rectangle([x0, y0, x1, y1], fill=col + (255,) if len(col) == 3 else col)


# ---------------------------------------------------------------- kafelki


def wood(col, dark=26):
    """Deski z słojami i szczelinami co 4 px."""
    def p(im, d, b, rnd):
        x0, y0, x1, y1 = b
        noise(im, b, col, 6, rnd)
        for y in range(y0, y1, 4):
            d.line([(x0, y), (x1 - 1, y)], fill=tuple(max(0, c - dark) for c in col) + (255,))
        for _ in range(5):
            x, y = rnd.randint(x0, x1 - 3), rnd.randint(y0, y1 - 1)
            d.line([(x, y), (x + 2, y)], fill=tuple(max(0, c - dark // 2) for c in col) + (255,))
        stains(im, b, DIRT, 2, rnd, 1)
    return p


def fabric(col):
    def p(im, d, b, rnd):
        x0, y0, x1, y1 = b
        noise(im, b, col, 7, rnd)
        for y in range(y0, y1, 2):
            for x in range(x0 + (y // 2) % 2, x1, 2):
                c = im.getpixel((x, y))
                im.putpixel((x, y), tuple(max(0, v - 14) for v in c[:3]) + (255,))
        stains(im, b, (60, 40, 30, 255), 3, rnd, 2)
    return p


def wardrobe_door(im, d, b, rnd):
    x0, y0, x1, y1 = b
    wood((96, 64, 40))(im, d, b, rnd)
    d.rectangle([x0 + 1, y0 + 1, x1 - 2, y1 - 2], outline=(60, 40, 26, 255))
    d.rectangle([x0 + 3, y0 + 3, x1 - 4, y1 - 4], outline=(116, 80, 52, 255))


def cardboard(im, d, b, rnd):
    x0, y0, x1, y1 = b
    noise(im, b, (182, 140, 92), 6, rnd)
    rect(d, x0, y0 + 6, x1 - 1, y0 + 9, (198, 170, 120))          # taśma
    d.line([(x0, y0), (x1 - 1, y0)], fill=(140, 104, 66, 255))
    d.line([(x0, y1 - 1), (x1 - 1, y1 - 1)], fill=(140, 104, 66, 255))
    if rnd.random() < 0.7:                                       # strzałki "góra"
        d.line([(x0 + 3, y0 + 12), (x0 + 3, y0 + 14)], fill=(40, 34, 30, 255))
        d.point((x0 + 2, y0 + 12), fill=(40, 34, 30, 255))
        d.point((x0 + 4, y0 + 12), fill=(40, 34, 30, 255))
    stains(im, b, (150, 112, 70, 255), 3, rnd, 2)


def cardboard_top(im, d, b, rnd):
    x0, y0, x1, y1 = b
    noise(im, b, (190, 148, 98), 5, rnd)
    d.line([(x0, y0 + 7), (x1 - 1, y0 + 7)], fill=(150, 112, 70, 255))
    rect(d, x0 + 6, y0, x0 + 9, y1 - 1, (204, 178, 128))


def sack(im, d, b, rnd):
    x0, y0, x1, y1 = b
    noise(im, b, (196, 180, 138), 10, rnd)
    for y in range(y0, y1, 3):
        d.line([(x0, y), (x1 - 1, y)], fill=(176, 160, 118, 255))
    d.text((x0 + 3, y0 + 4), '', fill=(0, 0, 0, 255))
    rect(d, x0 + 4, y0 + 5, x0 + 11, y0 + 9, (150, 60, 50))      # nadruk
    stains(im, b, DIRT, 4, rnd, 2)


def produce(im, d, b, rnd):
    x0, y0, x1, y1 = b
    noise(im, b, (60, 44, 30), 4, rnd)
    for _ in range(26):
        col = rnd.choice(((196, 70, 40), (230, 140, 30), (110, 160, 60), (150, 92, 52), (210, 190, 80)))
        x, y = rnd.randint(x0, x1 - 3), rnd.randint(y0, y1 - 3)
        d.ellipse([x, y, x + 2, y + 2], fill=col + (255,))
        d.point((x, y), fill=tuple(min(255, c + 40) for c in col) + (255,))
    for _ in range(4):                                           # zgnilizna
        x, y = rnd.randint(x0, x1 - 2), rnd.randint(y0, y1 - 2)
        d.point((x, y), fill=(50, 60, 30, 255))


def crate_side(im, d, b, rnd):
    x0, y0, x1, y1 = b
    noise(im, b, (150, 110, 70), 6, rnd)
    for y in (y0 + 4, y0 + 10):
        rect(d, x0, y, x1 - 1, y + 1, (60, 40, 26))
    rect(d, x0 + 3, y0 + 12, x0 + 12, y0 + 14, (236, 230, 210))  # naklejka
    d.line([(x0 + 4, y0 + 13), (x0 + 10, y0 + 13)], fill=(70, 120, 60, 255))


def toys(im, d, b, rnd):
    x0, y0, x1, y1 = b
    noise(im, b, (40, 40, 44), 3, rnd)
    x = x0
    while x < x1 - 2:
        w = rnd.randint(2, 4)
        h = rnd.randint(4, 7)
        col = rnd.choice(((220, 60, 60), (60, 120, 220), (240, 200, 50), (90, 190, 90), (230, 120, 180), (240, 240, 240)))
        if rnd.random() < 0.8:
            rect(d, x, y0 + 7 - h, min(x + w - 1, x1 - 1), y0 + 7, col)
            rect(d, x, y0 + 15 - h + 1, min(x + w - 1, x1 - 1), y0 + 15, rnd.choice(((220, 60, 60), (60, 120, 220), (240, 200, 50))))
        x += w + 1
    d.line([(x0, y0 + 8), (x1 - 1, y0 + 8)], fill=(150, 152, 156, 255))


def shop_metal(im, d, b, rnd):
    noise(im, b, (200, 202, 204), 4, rnd)
    stains(im, b, RUST, 2, rnd, 1)


def arcade_side(im, d, b, rnd):
    x0, y0, x1, y1 = b
    noise(im, b, (66, 44, 108), 5, rnd)
    for i in range(4):                                           # błyskawica na boku
        d.line([(x0 + 4 + i * 2, y0 + 2 + i * 3), (x0 + 8 + i * 2, y0 + 3 + i * 3)], fill=(230, 190, 40, 255))
    stains(im, b, (30, 20, 40, 255), 3, rnd, 1)


def arcade_screen(im, d, b, rnd):
    x0, y0, x1, y1 = b
    noise(im, b, (14, 18, 22), 3, rnd)
    for _ in range(9):
        x, y = rnd.randint(x0 + 2, x1 - 3), rnd.randint(y0 + 2, y1 - 3)
        d.point((x, y), fill=rnd.choice(((60, 220, 120), (240, 80, 80), (80, 140, 250))) + (255,))
    d.line([(x0 + 2, y0 + 3), (x0 + 10, y0 + 12)], fill=(150, 160, 170, 255))   # pęknięcie
    d.line([(x0 + 10, y0 + 12), (x0 + 13, y0 + 9)], fill=(150, 160, 170, 255))


def arcade_marquee(im, d, b, rnd):
    x0, y0, x1, y1 = b
    noise(im, b, (214, 170, 40), 5, rnd)
    for x in range(x0 + 2, x1 - 2, 3):
        rect(d, x, y0 + 5, x + 1, y0 + 10, (180, 40, 40))


def buttons(im, d, b, rnd):
    x0, y0, x1, y1 = b
    noise(im, b, (40, 40, 44), 3, rnd)
    rect(d, x0 + 3, y0 + 5, x0 + 4, y0 + 9, (30, 30, 30))       # joystick
    rect(d, x0 + 2, y0 + 3, x0 + 5, y0 + 5, (200, 40, 40))
    for i, col in enumerate(((220, 60, 60), (60, 120, 220), (240, 200, 50))):
        rect(d, x0 + 8 + i * 3, y0 + 6, x0 + 9 + i * 3, y0 + 7, col)


def rubber(im, d, b, rnd):
    x0, y0, x1, y1 = b
    noise(im, b, (32, 32, 35), 4, rnd)
    for x in range(x0, x1, 3):                                   # bieżnik
        d.line([(x, y0), (x + 1, y1 - 1)], fill=(18, 18, 20, 255))
    stains(im, b, (80, 70, 56, 255), 3, rnd, 1)


def rubber_top(im, d, b, rnd):
    x0, y0, x1, y1 = b
    noise(im, b, (36, 36, 40), 4, rnd)
    d.ellipse([x0 + 1, y0 + 1, x1 - 2, y1 - 2], outline=(56, 56, 60, 255))


def enamel(dirty=0):
    def p(im, d, b, rnd):
        noise(im, b, (228, 228, 222), 4, rnd)
        stains(im, b, (200, 190, 160, 255), 2 + dirty, rnd, 2)
        if dirty:
            stains(im, b, RUST, dirty, rnd, 1)
    return p


def radiator_fins(im, d, b, rnd):
    x0, y0, x1, y1 = b
    enamel(2)(im, d, b, rnd)
    for x in range(x0 + 1, x1, 3):
        d.line([(x, y0), (x, y1 - 1)], fill=(170, 168, 160, 255))


def washer_front(im, d, b, rnd):
    x0, y0, x1, y1 = b
    enamel(1)(im, d, b, rnd)
    d.ellipse([x0 + 3, y0 + 3, x1 - 4, y1 - 4], fill=(150, 154, 160, 255))
    d.ellipse([x0 + 4, y0 + 4, x1 - 5, y1 - 5], fill=(46, 60, 74, 255))
    d.line([(x0 + 6, y0 + 6), (x0 + 8, y0 + 5)], fill=(140, 170, 200, 255))


def washer_panel(im, d, b, rnd):
    x0, y0, x1, y1 = b
    noise(im, b, (190, 192, 196), 3, rnd)
    rect(d, x0 + 10, y0 + 5, x0 + 13, y0 + 9, (60, 62, 66))     # pokrętło
    for i in range(3):
        rect(d, x0 + 2 + i * 2, y0 + 7, x0 + 2 + i * 2, y0 + 8, (40, 40, 44))


def pot(im, d, b, rnd):
    x0, y0, x1, y1 = b
    noise(im, b, (96, 96, 102), 6, rnd)
    rect(d, x0, y0, x1 - 1, y0 + 1, (60, 60, 64))
    stains(im, b, (30, 28, 26, 255), 5, rnd, 2)                  # sadza


def pot_top(im, d, b, rnd):
    x0, y0, x1, y1 = b
    noise(im, b, (80, 64, 40), 6, rnd)                           # resztki zupy
    d.rectangle([x0, y0, x1 - 1, y1 - 1], outline=(70, 70, 74, 255))


def machine(im, d, b, rnd):
    x0, y0, x1, y1 = b
    noise(im, b, (84, 104, 86), 5, rnd)
    d.rectangle([x0, y0, x1 - 1, y1 - 1], outline=(46, 52, 46, 255))
    for x, y in ((x0 + 1, y0 + 1), (x1 - 2, y0 + 1), (x0 + 1, y1 - 2), (x1 - 2, y1 - 2)):
        d.point((x, y), fill=(160, 160, 150, 255))               # śruby
    stains(im, b, RUST, 4, rnd, 2)
    stains(im, b, (30, 30, 28, 255), 2, rnd, 1)                  # olej


def machine_plate(im, d, b, rnd):
    x0, y0, x1, y1 = b
    noise(im, b, (214, 170, 40), 5, rnd)
    for k in range(0, 16, 4):
        d.line([(x0 + k, y1 - 1), (x0 + k + 3, y0)], fill=(30, 30, 30, 255))


def rubble(im, d, b, rnd):
    x0, y0, x1, y1 = b
    noise(im, b, (118, 114, 108), 8, rnd)
    for _ in range(14):
        x, y = rnd.randint(x0, x1 - 3), rnd.randint(y0, y1 - 3)
        col = rnd.choice(((150, 120, 100), (90, 86, 80), (160, 158, 150), (70, 66, 60)))
        rect(d, x, y, x + rnd.randint(1, 2), y + rnd.randint(1, 2), col)


def concrete_chunk(im, d, b, rnd):
    x0, y0, x1, y1 = b
    noise(im, b, (150, 150, 146), 8, rnd)
    d.line([(x0 + 2, y0), (x0 + 7, y1 - 1)], fill=(100, 100, 96, 255))
    stains(im, b, (110, 106, 100, 255), 3, rnd, 1)


def rebar(im, d, b, rnd):
    noise(im, b, (110, 70, 44), 6, rnd)
    stains(im, b, (70, 44, 30, 255), 3, rnd, 1)


# ---------------------------------------------------------------- meble


def legs(x0, z0, x1, z1, h, w, region):
    return [([x, 0, z], [x + w, h, z + w], region) for x in (x0, x1 - w) for z in (z0, z1 - w)]


def krzeslo():
    """Drewniane krzesło z tapicerowanym siedziskiem, oparcie z tyłu (z = 0)."""
    P = [('drewno', wood((132, 94, 58))), ('obicie', fabric((70, 96, 62)))]
    parts = legs(3, 3, 13, 13, 8, 1.6, 'drewno')
    parts += [([3, 8, 3], [13, 9.5, 13], 'drewno', {'up': 'obicie'}),
              ([3, 9.5, 3], [4.6, 21, 4.6], 'drewno'), ([11.4, 9.5, 3], [13, 21, 4.6], 'drewno'),
              ([4.6, 14, 3.4], [11.4, 20, 4.4], 'obicie'), ([3, 21, 3], [13, 22, 4.6], 'drewno')]
    model('krzeslo', parts, P, 101)


def stol():
    """Kwadratowy stół z ciemnymi nogami i porysowanym blatem."""
    P = [('blat', wood((140, 100, 62))), ('nogi', wood((90, 62, 40)))]
    parts = legs(1, 1, 15, 15, 14, 2, 'nogi')
    parts += [([0, 14, 0], [16, 16, 16], 'blat'), ([2, 12, 2], [14, 14, 2.6], 'nogi'), ([2, 12, 13.4], [14, 14, 14], 'nogi')]
    model('stol', parts, P, 102)


def szafa():
    """Dwudrzwiowa szafa z czasów PRL, dwie kratki wysokości, lekko uchylone prawe drzwi."""
    P = [('korpus', wood((92, 64, 40))), ('drzwi', wardrobe_door), ('metal', plain((170, 172, 176), 4, 1)),
         ('wnetrze', plain((40, 30, 22), 3))]
    parts = [([1, 0, 3], [15, 31, 15.5], 'korpus', {'south': 'wnetrze'}),
             ([1.4, 1, 15.5], [7.9, 30, 16], 'drzwi'),
             ([8.1, 1, 15.5], [14.6, 30, 16], 'drzwi'),
             ([7.2, 14, 16], [7.7, 18, 16.6], 'metal'), ([8.3, 14, 16], [8.8, 18, 16.6], 'metal'),
             ([0.5, 31, 2.5], [15.5, 32, 16], 'korpus'), ([1, 0, 15.5], [15, 1, 16], 'korpus')]
    model('szafa', parts, P, 103)


def lawka():
    """Ławka parkowa: żeliwne boki, trzy deski siedziska, dwie oparcia (tył przy z = 0)."""
    P = [('deski', wood((136, 98, 60))), ('zeliwo', plain((52, 54, 58), 4, 2))]
    parts = [([0.5, 0, 4], [2, 7, 14], 'zeliwo'), ([14, 0, 4], [15.5, 7, 14], 'zeliwo'),
             ([0.5, 7, 1], [2, 16, 2.5], 'zeliwo'), ([14, 7, 1], [15.5, 16, 2.5], 'zeliwo')]
    for z in (4, 7.6, 11.2):
        parts.append(([0, 7, z], [16, 8.4, z + 3], 'deski'))
    for y in (9.5, 13):
        parts.append(([0, y, 1.6], [16, y + 2.4, 2.8], 'deski'))
    model('lawka', parts, P, 104)


def kartony():
    """Sterta trzech kartonów oklejonych taśmą."""
    P = [('karton', cardboard), ('gora', cardboard_top)]
    parts = [([1, 0, 2], [10, 8, 12], 'karton', {'up': 'gora'}),
             ([9.5, 0, 6], [15, 6, 15], 'karton', {'up': 'gora'}),
             ([2, 8, 3], [9, 14, 10], 'karton', {'up': 'gora'})]
    model('kartony', parts, P, 105)


def worki():
    """Worki jutowe ułożone w stertę (piasek, mąka, gotówka w liczarni)."""
    P = [('worek', sack)]
    parts = [([1, 0, 1], [9, 6, 8], 'worek'), ([2, 6, 2], [8, 6.8, 7], 'worek'),
             ([8, 0, 7], [15, 6, 15], 'worek'), ([9, 6, 8], [14, 6.8, 14], 'worek'),
             ([3, 6, 7], [12, 11, 13], 'worek'), ([4, 11, 8], [11, 11.8, 12], 'worek')]
    model('worki', parts, P, 106)


def skrzynka_warzywa():
    """Drewniana skrzynka z warzywami ze straganu, część zgniła."""
    P = [('skrzynka', crate_side), ('warzywa', produce), ('dno', wood((120, 86, 54)))]
    parts = [([1, 0, 1], [15, 1.5, 15], 'dno'),
             ([1, 1.5, 1], [15, 8, 2], 'skrzynka'), ([1, 1.5, 14], [15, 8, 15], 'skrzynka'),
             ([1, 1.5, 2], [2, 8, 14], 'skrzynka'), ([14, 1.5, 2], [15, 8, 14], 'skrzynka'),
             ([2, 1.5, 2], [14, 9, 14], 'warzywa')]
    model('skrzynka_warzywa', parts, P, 107)


def zabawki():
    """Metalowy regał sklepowy z zabawkami: klocki, misie, auta w pudełkach."""
    P = [('metal', shop_metal), ('zabawki', toys), ('ciemny', plain((44, 44, 46), 3))]
    parts = [([0, 0, 0], [16, 16, 1], 'metal'), ([0, 0, 1], [1, 16, 15], 'metal'), ([15, 0, 1], [16, 16, 15], 'metal')]
    for y in (0, 7.5, 15):
        parts.append(([1, y, 1], [15, y + 1, 15], 'metal'))
    for y in (1, 8.5):
        parts.append(([1.5, y, 2], [14.5, y + 6, 13.5], 'ciemny', {'south': 'zabawki', 'up': 'ciemny'}))
    model('zabawki', parts, P, 108)


def automat_gier():
    """Automat do gier z rozbitym ekranem, dwie kratki wysokości."""
    P = [('bok', arcade_side), ('ekran', arcade_screen), ('szyld', arcade_marquee), ('pulpit', buttons),
         ('czarny', plain((30, 30, 34), 3))]
    parts = [([1, 0, 1], [15, 29, 13], 'bok', {'south': 'czarny', 'north': 'czarny'}),
             ([2, 15, 12.5], [14, 26, 13.2], 'ekran'),
             ([1, 10, 13], [15, 13, 16], 'czarny', {'up': 'pulpit'}),
             ([1, 26, 12], [15, 32, 14], 'szyld', {'up': 'czarny', 'down': 'czarny'})]
    model('automat_gier', parts, P, 109)


def sterta_opon():
    """Sterta trzech starych opon."""
    P = [('guma', rubber), ('bok', rubber_top)]
    parts = []
    for i, y in enumerate((0, 4.4, 8.8)):
        o = (0.6 if i % 2 else 0)
        parts += [([1 + o, y, 1], [15 + o, y + 4, 4], 'guma', {'up': 'bok', 'down': 'bok'}),
                  ([1 + o, y, 12], [15 + o, y + 4, 15], 'guma', {'up': 'bok', 'down': 'bok'}),
                  ([1 + o, y, 4], [4 + o, y + 4, 12], 'guma', {'up': 'bok', 'down': 'bok'}),
                  ([12 + o, y, 4], [15 + o, y + 4, 12], 'guma', {'up': 'bok', 'down': 'bok'})]
    model('sterta_opon', parts, P, 110)


def kaloryfer():
    """Żeliwny kaloryfer żeberkowy pod oknem, przy ścianie (z = 0), z zaworem."""
    P = [('zeberka', radiator_fins), ('emalia', enamel(2)), ('metal', plain((150, 152, 156), 4, 2))]
    parts = [([x, 2, 1], [x + 1.4, 13, 4], 'emalia', {'south': 'zeberka'}) for x in range(1, 15, 2)]
    parts += [([1, 3, 1.6], [15, 4, 3.4], 'emalia'), ([1, 11, 1.6], [15, 12, 3.4], 'emalia'),
              ([1.5, 0, 2], [2.5, 2, 3], 'metal'), ([13.5, 0, 2], [14.5, 2, 3], 'metal'),
              ([15, 10.5, 2], [16, 12.5, 3], 'metal')]
    model('kaloryfer', parts, P, 111)


def pralka():
    """Pralka „Polar” z okrągłymi drzwiczkami."""
    P = [('front', washer_front), ('panel', washer_panel), ('emalia', enamel(1))]
    parts = [([1, 0, 1], [15, 12, 15], 'emalia', {'south': 'front'}),
             ([1, 12, 1], [15, 15, 15], 'emalia', {'south': 'panel'})]
    model('pralka', parts, P, 112)


def kanapa():
    """Segment kanapy (boks w barze, wersalka w mieszkaniu), oparcie z tyłu (z = 0)."""
    P = [('obicie', fabric((142, 46, 40))), ('nogi', wood((70, 48, 30)))]
    parts = [([0, 1, 1], [16, 7, 15], 'obicie'), ([0, 7, 0], [16, 16, 4], 'obicie'), ([0, 7, 4], [16, 9, 15], 'obicie')]
    parts += [([x, 0, z], [x + 2, 1, z + 2], 'nogi') for x in (1, 13) for z in (2, 12)]
    model('kanapa', parts, P, 113)


def garnek():
    """Okopcony garnek na stojaku z prętów (obozowiska dzikich lokatorów)."""
    P = [('garnek', pot), ('zupa', pot_top), ('pret', plain((52, 52, 56), 3, 2))]
    parts = [([x, 0, z], [x + 1, 3, z + 1], 'pret') for x in (3, 12) for z in (3, 12)]
    parts += [([2, 3, 2], [14, 3.8, 14], 'pret'), ([4, 3.8, 4], [12, 10.5, 12], 'garnek', {'up': 'zupa'}),
              ([2.5, 9, 7], [4, 9.8, 9], 'pret'), ([12, 9, 7], [13.5, 9.8, 9], 'pret')]
    model('garnek', parts, P, 114)


def maszyna():
    """Silnik z pompą na ramie: rury, tabliczka ostrzegawcza, rdza i olej."""
    P = [('korpus', machine), ('rama', plain((60, 62, 66), 4, 2)), ('rura', rebar), ('tablica', machine_plate)]
    parts = [([0, 0, 0], [16, 2, 16], 'rama'),
             ([1, 2, 2], [11, 12, 14], 'korpus', {'south': 'korpus'}),
             ([11, 3, 4], [15, 9, 12], 'rura'),
             ([3, 12, 5], [5, 16, 7], 'rura'), ([7, 12, 9], [9, 15, 11], 'rura'),
             ([4, 5, 14], [8, 9, 14.4], 'tablica')]
    model('maszyna', parts, P, 115)


def gruz():
    """Kupka gruzu: pokruszony beton, cegły, deska i pręt zbrojeniowy."""
    P = [('gruz', rubble), ('beton', concrete_chunk), ('deska', wood((90, 62, 40))), ('pret', rebar)]
    parts = [([0, 0, 0], [16, 2, 16], 'gruz'),
             ([1, 2, 2], [9, 6, 10], 'gruz'), ([7, 2, 6], [14, 5, 14], 'beton'),
             ([3, 6, 4], [8, 9, 8], 'beton'), ([10, 5, 9], [13, 7, 12], 'gruz'),
             ([12, 2, 1], [15, 3, 7], 'deska'), ([2, 2, 12], [12, 2.8, 12.8], 'pret')]
    model('gruz', parts, P, 116)


MEBLE_STRUKTURY = ['krzeslo', 'stol', 'szafa', 'lawka', 'kartony', 'worki', 'skrzynka_warzywa', 'zabawki',
                   'automat_gier', 'sterta_opon', 'kaloryfer', 'pralka', 'kanapa', 'garnek', 'maszyna', 'gruz']

if __name__ == '__main__':
    for fn in (krzeslo, stol, szafa, lawka, kartony, worki, skrzynka_warzywa, zabawki, automat_gier, sterta_opon,
               kaloryfer, pralka, kanapa, garnek, maszyna, gruz):
        fn()
    print('ok', MEBLE_STRUKTURY)
