#!/usr/bin/env python3
"""Meble do nowych struktur AXON-Structure: stacja Oilen, kiosk, fastfood, osiedle, zajezdnia, elektrownia, galeria.

Tak samo jak gen_meble.py: jedna kratka (lodówka i dystrybutor dwie), przód modelu na południe = +z,
tekstura 64x64 z kafelków 16x16 px (w modelu uv 4x4). Plugin zamienia bloki z `meble.bloki` na barierę
i stawia na nich te modele. Zapisuje build/<nazwa>.json, build/<nazwa>.png i build/<nazwa>_item.json.
"""
from PIL import ImageDraw
from gen_rekwizyty import noise, stains
from gen_meble import model, plain, wood_top

RUST = (120, 72, 40, 255)
DIRT = (70, 62, 50, 255)


def rect(d, x0, y0, x1, y1, col):
    d.rectangle([x0, y0, x1, y1], fill=col + (255,) if len(col) == 3 else col)


def digits(d, x, y, text, col):
    """Cyfry 3x5 px (wyświetlacze kasy i licznik dystrybutora)."""
    font = {'0': '111101101101111', '1': '010110010010111', '2': '111001111100111', '3': '111001111001111',
            '4': '101101111001001', '5': '111100111001111', '6': '111100111101111', '7': '111001001001001',
            '8': '111101111101111', '9': '111101111001111', '.': '000000000000010', ' ': '0' * 15}
    for ch in text:
        bits = font[ch]
        for i, b in enumerate(bits):
            if b == '1':
                d.point((x + i % 3, y + i // 3), fill=col + (255,))
        x += 2 if ch == '.' else 4


# ---------------------------------------------------------------- kafelki: kasa i lada


def kasa_front(im, d, b, rnd):
    x0, y0, x1, y1 = b
    noise(im, b, (196, 186, 160), 4, rnd)                       # beżowy plastik z lat 90
    rect(d, x0 + 1, y0 + 9, x1 - 2, y1 - 2, (172, 162, 138))    # szuflada na pieniądze
    d.line([(x0 + 1, y0 + 9), (x1 - 2, y0 + 9)], fill=(120, 112, 96, 255))
    rect(d, x0 + 6, y0 + 11, x0 + 9, y0 + 12, (60, 58, 54))     # zamek szuflady
    d.point((x0 + 7, y0 + 11), fill=(200, 196, 180, 255))
    rect(d, x0 + 4, y0 + 2, x1 - 5, y0 + 3, (40, 40, 40))       # szczelina na paragon
    stains(im, b, DIRT, 3, rnd, 1)


def keys(im, d, b, rnd):
    x0, y0, x1, y1 = b
    noise(im, b, (150, 142, 124), 3, rnd)
    for r in range(4):
        for c in range(5):
            col = (226, 222, 208)
            if c == 4:
                col = (200, 60, 50) if r == 3 else (90, 130, 190)
            rect(d, x0 + 1 + c * 3, y0 + 1 + r * 4, x0 + 2 + c * 3, y0 + 3 + r * 4, col)
    for _ in range(3):                                          # starte cyfry
        d.point((x0 + 1 + rnd.randint(0, 3) * 3, y0 + 1 + rnd.randint(0, 3) * 4), fill=(170, 164, 148, 255))


def led(im, d, b, rnd):
    x0, y0, x1, y1 = b
    noise(im, b, (60, 58, 54), 3, rnd)
    rect(d, x0 + 1, y0 + 4, x1 - 2, y1 - 5, (16, 24, 18))
    digits(d, x0 + 1, y0 + 5, '12.50', (110, 240, 120))


def paper(im, d, b, rnd):
    x0, y0, x1, y1 = b
    noise(im, b, (232, 228, 214), 4, rnd)
    for y in range(y0 + 2, y1, 3):
        d.line([(x0 + 3, y), (x0 + 3 + rnd.randint(3, 9), y)], fill=(150, 150, 160, 255))


def laminate(im, d, b, rnd):
    x0, y0, x1, y1 = b
    noise(im, b, (178, 150, 112), 4, rnd)                       # laminat „pod drewno”
    for x in range(x0 + 2, x1, 5):
        d.line([(x, y0), (x + rnd.randint(-1, 1), y1 - 1)], fill=(160, 132, 96, 255))
    stains(im, b, DIRT, 3, rnd, 1)


def lada_front(im, d, b, rnd):
    x0, y0, x1, y1 = b
    noise(im, b, (142, 30, 34), 4, rnd)                         # czerwony front z listwą
    rect(d, x0, y0, x1 - 1, y0 + 6, (60, 70, 74))               # szyba witryny
    for x, col in ((x0 + 1, (200, 170, 60)), (x0 + 4, (60, 120, 180)), (x0 + 8, (220, 220, 210)),
                   (x0 + 11, (170, 60, 50))):
        rect(d, x, y0 + 3, x + 2, y0 + 6, col)                   # towar za szybą
    d.line([(x0 + 2, y0 + 1), (x0 + 5, y0 + 1)], fill=(150, 170, 176, 255))
    d.line([(x0, y0 + 7), (x1 - 1, y0 + 7)], fill=(190, 190, 186, 255))
    rect(d, x0, y1 - 2, x1 - 1, y1 - 1, (40, 40, 42))           # cokół
    for _ in range(4):                                          # obtłuczenia do płyty wiórowej
        x, y = rnd.randint(x0, x1 - 3), rnd.randint(y0 + 8, y1 - 4)
        rect(d, x, y, x + 1, y + 1, (170, 140, 100))
    stains(im, b, DIRT, 2, rnd, 1)


def shelves_back(im, d, b, rnd):
    x0, y0, x1, y1 = b
    noise(im, b, (150, 124, 88), 4, rnd)
    for y in (y0 + 5, y0 + 10):
        d.line([(x0, y), (x1 - 1, y)], fill=(100, 80, 54, 255))
    for _ in range(5):
        x, y = rnd.randint(x0 + 1, x1 - 4), rnd.choice((y0 + 2, y0 + 7, y0 + 12))
        rect(d, x, y, x + 2, y + 2, rnd.choice(((220, 214, 196), (120, 90, 60), (70, 90, 140))))


def counter_top(im, d, b, rnd):
    x0, y0, x1, y1 = b
    noise(im, b, (196, 196, 190), 4, rnd)                       # szary blat z laminatu
    for _ in range(4):
        x, y = rnd.randint(x0, x1 - 6), rnd.randint(y0, y1 - 1)
        d.line([(x, y), (x + rnd.randint(2, 5), y + rnd.randint(-1, 1))], fill=(160, 160, 156, 255))
    stains(im, b, (150, 146, 136, 255), 3, rnd, 1)


# ---------------------------------------------------------------- kafelki: kibel


def porcelain(im, d, b, rnd):
    x0, y0, x1, y1 = b
    noise(im, b, (226, 226, 220), 4, rnd)
    stains(im, b, (190, 170, 120, 255), 3, rnd, 1)
    d.line([(x0 + 3, y1 - 1), (x0 + 6, y1 - 4)], fill=(170, 170, 164, 255))   # rysa


def bowl_top(im, d, b, rnd):
    x0, y0, x1, y1 = b
    noise(im, b, (226, 226, 220), 4, rnd)
    d.ellipse([x0 + 2, y0 + 1, x1 - 3, y1 - 2], fill=(150, 140, 110, 255))     # zaschnięta woda
    d.ellipse([x0 + 5, y0 + 6, x1 - 6, y1 - 4], fill=(70, 66, 50, 255))
    stains(im, (x0 + 3, y0 + 2, x1 - 3, y1 - 3), (110, 90, 50, 255), 3, rnd, 1)


def seat(im, d, b, rnd):
    x0, y0, x1, y1 = b
    noise(im, b, (84, 60, 40), 5, rnd)                          # deska „pod drewno”
    for y in range(y0 + 2, y1, 4):
        d.line([(x0, y), (x1 - 1, y)], fill=(68, 48, 30, 255))


def tank_front(im, d, b, rnd):
    x0, y0, x1, y1 = b
    noise(im, b, (222, 222, 216), 4, rnd)
    d.line([(x0, y1 - 1), (x1 - 1, y1 - 1)], fill=(180, 180, 176, 255))
    for _ in range(2):                                          # zacieki rdzy spod pokrywy
        x = rnd.randint(x0 + 2, x1 - 3)
        d.line([(x, y0), (x, y0 + rnd.randint(3, 8))], fill=(160, 110, 60, 255))


def chrome(im, d, b, rnd):
    noise(im, b, (180, 184, 188), 10, rnd)


# ---------------------------------------------------------------- kafelki: regał sklepowy


def goods(kind):
    def p(im, d, b, rnd):
        x0, y0, x1, y1 = b
        noise(im, b, (36, 36, 38), 2, rnd)                       # cień w głębi półki
        x = x0
        while x < x1:
            if rnd.random() < 0.22:                              # wyszabrowane miejsce
                x += 3
                continue
            if kind == 'puszki':
                col = rnd.choice(((180, 40, 40), (200, 180, 60), (60, 110, 60), (190, 190, 196)))
                rect(d, x, y0 + 7, min(x + 2, x1 - 1), y1 - 1, col)
                d.line([(x, y0 + 7), (min(x + 2, x1 - 1), y0 + 7)], fill=(210, 210, 214, 255))
                rect(d, x, y0 + 10, min(x + 2, x1 - 1), y0 + 12, (230, 226, 210))
                x += 3
            elif kind == 'sloiki':
                rect(d, x, y0 + 5, min(x + 3, x1 - 1), y1 - 1, rnd.choice(((180, 70, 40), (120, 30, 50), (200, 150, 40))))
                rect(d, x, y0 + 4, min(x + 3, x1 - 1), y0 + 5, (200, 196, 60))                # zakrętka
                rect(d, x, y0 + 9, min(x + 3, x1 - 1), y0 + 11, (236, 232, 216))             # etykieta
                x += 4
            elif kind == 'kartony':
                w = rnd.randint(4, 6)
                col = rnd.choice(((170, 136, 88), (210, 200, 170), (200, 70, 60), (70, 110, 170)))
                top = y0 + rnd.randint(1, 5)
                rect(d, x, top, min(x + w - 2, x1 - 1), y1 - 1, col)
                d.line([(x + 1, top + 3), (min(x + w - 3, x1 - 1), top + 3)], fill=(240, 236, 220, 255))
                x += w
            else:                                                # butelki
                col = rnd.choice(((60, 120, 60), (140, 80, 40), (200, 200, 210)))
                rect(d, x + 1, y0 + 2, x + 1, y0 + 6, col)
                rect(d, x, y0 + 6, min(x + 2, x1 - 1), y1 - 1, col)
                rect(d, x, y0 + 10, min(x + 2, x1 - 1), y0 + 12, (226, 214, 170))
                x += 3
    return p


def goods_top(im, d, b, rnd):
    x0, y0, x1, y1 = b
    noise(im, b, (60, 60, 62), 4, rnd)
    for _ in range(14):
        x, y = rnd.randint(x0, x1 - 3), rnd.randint(y0, y1 - 3)
        rect(d, x, y, x + 2, y + 2, rnd.choice(((180, 40, 40), (200, 180, 60), (170, 136, 88), (190, 190, 196))))


def shop_metal(im, d, b, rnd):
    noise(im, b, (196, 198, 194), 5, rnd)                       # biały lakier na blasze
    stains(im, b, RUST, 3, rnd, 1)


def price_rail(im, d, b, rnd):
    x0, y0, x1, y1 = b
    noise(im, b, (196, 198, 194), 4, rnd)
    for x in range(x0 + 1, x1 - 3, 6):
        rect(d, x, y0 + 4, x + 3, y0 + 9, (240, 236, 120))       # cenówki
        d.point((x + 1, y0 + 6), fill=(40, 40, 40, 255))
        d.point((x + 2, y0 + 6), fill=(40, 40, 40, 255))
    stains(im, b, RUST, 2, rnd, 1)


# ---------------------------------------------------------------- kafelki: lodówka


def fridge_glass(top):
    def p(im, d, b, rnd):
        x0, y0, x1, y1 = b
        noise(im, b, (196, 40, 40), 4, rnd)                      # czerwona rama
        rect(d, x0 + 1, y0 + (0 if top else 0), x1 - 2, y1 - (0 if top else 3), (40, 52, 56))
        for y in range(y0 + 4, y1 - 3, 5):                       # półki z butelkami za szybą
            d.line([(x0 + 1, y), (x1 - 2, y)], fill=(130, 140, 140, 255))
            x = x0 + 2
            while x < x1 - 3:
                if rnd.random() < 0.3:
                    x += 2
                    continue
                col = rnd.choice(((150, 50, 40), (60, 120, 70), (200, 140, 50), (90, 90, 160), (210, 210, 200)))
                rect(d, x, y - 3, x, y - 1, col)
                d.point((x, y - 4), fill=tuple(c // 2 for c in col) + (255,))
                x += 2
        for i in range(3):                                       # refleks i kurz na szybie
            d.point((x0 + 3 + i, y0 + 3 + i * 2), fill=(150, 170, 176, 255))
        stains(im, (x0 + 1, y0, x1 - 2, y1), (90, 92, 86, 255), 2, rnd, 1)
        if not top:
            rect(d, x0, y1 - 3, x1 - 1, y1 - 1, (60, 60, 62))     # kratka wentylacji
            for x in range(x0 + 1, x1 - 1, 2):
                d.point((x, y1 - 2), fill=(20, 20, 20, 255))
    return p


def fridge_sign(im, d, b, rnd):
    x0, y0, x1, y1 = b
    noise(im, b, (210, 40, 40), 4, rnd)
    d.arc([x0 - 4, y0 + 3, x1 + 3, y0 + 18], 200, 340, fill=(245, 245, 240, 255), width=2)   # biała fala
    rect(d, x0, y0, x1 - 1, y0, (160, 30, 30))
    stains(im, b, DIRT, 2, rnd, 1)


def red_paint(im, d, b, rnd):
    noise(im, b, (196, 40, 40), 4, rnd)
    stains(im, b, RUST, 3, rnd, 1)


# ---------------------------------------------------------------- kafelki: dystrybutor


def pump_counter(im, d, b, rnd):
    x0, y0, x1, y1 = b
    noise(im, b, (230, 228, 220), 4, rnd)                       # biała blacha
    rect(d, x0 + 1, y0 + 1, x1 - 2, y0 + 12, (40, 42, 44))
    rect(d, x0 + 2, y0 + 2, x1 - 3, y0 + 6, (236, 232, 210))    # mechaniczny licznik
    digits(d, x0 + 2, y0 + 2, '038', (30, 30, 30))
    rect(d, x0 + 4, y0 + 8, x1 - 5, y0 + 10, (236, 232, 210))
    d.point((x1 - 4, y0 + 2), fill=(150, 160, 160, 255))        # odprysk na szybce
    rect(d, x0 + 1, y1 - 3, x1 - 2, y1 - 2, (196, 40, 40))
    stains(im, b, RUST, 2, rnd, 1)


def pump_lower(im, d, b, rnd):
    x0, y0, x1, y1 = b
    noise(im, b, (196, 40, 40), 4, rnd)                         # czerwona obudowa CPN-owska
    rect(d, x0 + 2, y0 + 2, x1 - 3, y1 - 4, (180, 34, 34))
    d.rectangle([x0 + 2, y0 + 2, x1 - 3, y1 - 4], outline=(140, 26, 26, 255))
    rect(d, x0 + 5, y0 + 4, x0 + 10, y0 + 6, (230, 228, 220))   # tabliczka
    rect(d, x0, y1 - 2, x1 - 1, y1 - 1, (50, 50, 50))
    stains(im, b, RUST, 5, rnd, 1)


def pump_sign(im, d, b, rnd):
    x0, y0, x1, y1 = b
    noise(im, b, (240, 200, 40), 4, rnd)                        # żółty szyld z liczbą oktanową
    digits(d, x0 + 4, y0 + 5, '95', (30, 30, 30))
    rect(d, x0, y1 - 3, x1 - 1, y1 - 1, (196, 40, 40))
    stains(im, b, DIRT, 2, rnd, 1)


def hose(im, d, b, rnd):
    noise(im, b, (30, 30, 32), 3, rnd)


def concrete(im, d, b, rnd):
    x0, y0, x1, y1 = b
    noise(im, b, (150, 150, 146), 7, rnd)
    d.line([(x0 + 2, y0), (x0 + 5, y0 + 6), (x0 + 4, y1 - 1)], fill=(110, 110, 106, 255))
    stains(im, b, (60, 58, 50, 255), 3, rnd, 2)                 # plamy oleju


# ---------------------------------------------------------------- kafelki: rozdzielnia


def cabinet_front(im, d, b, rnd):
    x0, y0, x1, y1 = b
    noise(im, b, (150, 156, 150), 4, rnd)                       # szara blacha
    d.rectangle([x0, y0, x1 - 1, y1 - 1], outline=(110, 114, 110, 255))
    rect(d, x0 + 2, y0 + 2, x1 - 3, y0 + 5, (30, 34, 36))       # okienko z trzema licznikami
    for x in (x0 + 3, x0 + 6, x0 + 9):
        rect(d, x, y0 + 3, x + 1, y0 + 4, (226, 222, 210))
        d.point((x + 1, y0 + 4), fill=(200, 40, 30, 255))
    d.line([(x0 + 2, y0 + 6), (x1 - 3, y0 + 6)], fill=(110, 114, 110, 255))
    d.polygon([(x0 + 7, y0 + 8), (x0 + 4, y0 + 13), (x0 + 10, y0 + 13)], fill=(240, 200, 30, 255))   # trójkąt
    d.line([(x0 + 7, y0 + 9), (x0 + 6, y0 + 11), (x0 + 8, y0 + 11), (x0 + 7, y0 + 12)], fill=(30, 30, 30, 255))
    rect(d, x1 - 3, y0 + 8, x1 - 2, y0 + 10, (60, 60, 60))      # zamek
    stains(im, b, RUST, 4, rnd, 1)


def cabinet_side(im, d, b, rnd):
    x0, y0, x1, y1 = b
    noise(im, b, (150, 156, 150), 4, rnd)
    for y in range(y0 + 3, y0 + 8, 2):                          # wywietrznik
        d.line([(x0 + 4, y), (x1 - 5, y)], fill=(70, 74, 70, 255))
    stains(im, b, RUST, 5, rnd, 1)


def cable(im, d, b, rnd):
    noise(im, b, (36, 36, 38), 3, rnd)


# ---------------------------------------------------------------- kafelki: frytkownica


def steel(im, d, b, rnd):
    x0, y0, x1, y1 = b
    noise(im, b, (176, 178, 180), 6, rnd)
    for y in range(y0, y1, 2):                                  # szlif
        d.line([(x0, y), (x1 - 1, y)], fill=(168, 170, 172, 255))
    stains(im, b, (110, 90, 50, 255), 3, rnd, 1)                # tłuszcz


def fryer_front(im, d, b, rnd):
    x0, y0, x1, y1 = b
    steel(im, d, b, rnd)
    for x in (x0 + 3, x0 + 11):                                 # pokrętła termostatów
        rect(d, x - 1, y0 + 2, x, y0 + 3, (30, 30, 30))
        d.point((x, y0 + 2), fill=(220, 220, 220, 255))
    d.point((x0 + 7, y0 + 3), fill=(240, 120, 30, 255))         # lampka
    for y in range(y0 + 8, y1 - 2, 2):
        d.line([(x0 + 3, y), (x1 - 4, y)], fill=(80, 80, 82, 255))
    rect(d, x0, y1 - 2, x1 - 1, y1 - 1, (60, 60, 62))


def fryer_top(im, d, b, rnd):
    x0, y0, x1, y1 = b
    steel(im, d, b, rnd)
    for xa in (x0 + 1, x0 + 9):
        rect(d, xa, y0 + 3, xa + 5, y1 - 2, (60, 44, 20))       # stary olej
        d.point((xa + 2, y0 + 6), fill=(110, 84, 40, 255))
        d.point((xa + 4, y0 + 9), fill=(110, 84, 40, 255))


def basket(im, d, b, rnd):
    x0, y0, x1, y1 = b
    for y in range(y0, y1):
        for x in range(x0, x1):
            if (x - x0) % 3 == 0 or (y - y0) % 3 == 0:
                im.putpixel((x, y), (150, 150, 146, 255))


def black_plastic(im, d, b, rnd):
    noise(im, b, (34, 34, 36), 3, rnd)


# ---------------------------------------------------------------- kafelki: kanistry


def can_side(col):
    def p(im, d, b, rnd):
        x0, y0, x1, y1 = b
        noise(im, b, col, 5, rnd)
        dark = tuple(max(0, c - 40) for c in col) + (255,)
        d.line([(x0 + 2, y0 + 3), (x1 - 3, y1 - 3)], fill=dark)  # przetłoczenie X
        d.line([(x1 - 3, y0 + 3), (x0 + 2, y1 - 3)], fill=dark)
        d.rectangle([x0 + 1, y0 + 2, x1 - 2, y1 - 2], outline=dark)
        stains(im, b, RUST, 3, rnd, 1)
        for _ in range(4):                                       # obdrapany lakier
            d.point((rnd.randint(x0, x1 - 1), rnd.randint(y0, y1 - 1)), fill=(150, 150, 146, 255))
    return p


def can_end(col):
    def p(im, d, b, rnd):
        x0, y0, x1, y1 = b
        noise(im, b, col, 5, rnd)
        dark = tuple(max(0, c - 40) for c in col) + (255,)
        for x in range(x0 + 4, x1 - 3, 4):
            d.line([(x, y0 + 2), (x, y1 - 3)], fill=dark)
        stains(im, b, RUST, 2, rnd, 1)
    return p


def label_kanister(im, d, b, rnd):
    x0, y0, x1, y1 = b
    can_side((150, 30, 26))(im, d, b, rnd)
    rect(d, x0 + 3, y0 + 5, x1 - 4, y0 + 10, (232, 228, 214))   # naklejka „kto ukradł…” bez napisu
    for y in (y0 + 6, y0 + 8):
        d.line([(x0 + 4, y), (x1 - 5, y)], fill=(40, 40, 60, 255))


# ---------------------------------------------------------------- kafelki: wózek


def wire(im, d, b, rnd):
    x0, y0, x1, y1 = b
    for y in range(y0, y1):
        for x in range(x0, x1):
            if (x - x0) % 3 == 0 or (y - y0) % 3 == 0 or x == x1 - 1 or y == y1 - 1:
                k = rnd.randint(-10, 10)
                c = (178 + k, 182 + k, 186 + k, 255)
                if rnd.random() < 0.08:
                    c = (140, 96, 60, 255)                      # rdza na drutach
                im.putpixel((x, y), c)


def handle_red(im, d, b, rnd):
    noise(im, b, (200, 40, 36), 5, rnd)


# ---------------------------------------------------------------- meble


def kasa():
    """Kasa fiskalna z lat 90: szuflada, klawiatura, wyświetlacz na nóżce (stawiana na ladzie)."""
    P = [('obudowa', plain((196, 186, 160), 4)), ('front', kasa_front), ('klawisze', keys), ('led', led),
         ('papier', paper), ('ciemny', plain((60, 58, 54), 3))]
    parts = [([2, 0, 2], [14, 3, 14], 'obudowa', {'south': 'front'}),
             ([3, 3, 9], [13, 4.5, 14], 'obudowa', {'up': 'klawisze'}),
             ([3, 3, 3], [13, 7, 9], 'obudowa', {'south': 'front'}),
             ([7.2, 7, 4.5], [8.8, 9, 6], 'ciemny'),
             ([5, 9, 4], [11, 11.5, 6], 'ciemny', {'south': 'led', 'north': 'led'}),
             ([9.5, 7, 4], [12, 7.8, 8.5], 'papier')]
    model('kasa', parts, P, 31)


def lada():
    """Lada sklepowa: czerwony front z witryną, laminowane boki, półki po stronie sprzedawcy."""
    P = [('laminat', laminate), ('front', lada_front), ('polki', shelves_back), ('blat', counter_top),
         ('cokol', plain((40, 40, 42), 3))]
    parts = [([0, 0, 0], [16, 14, 15.5], 'laminat', {'south': 'front', 'north': 'polki'}),
             ([-0.2, 14, -0.2], [16.2, 15.2, 16], 'blat'),
             ([0, 0, 15.5], [16, 1, 16], 'cokol')]
    model('lada', parts, P, 32)


def kibel():
    """Kompakt WC ze spłuczką, podniesiona deska, zacieki (zbiornik z tyłu, sedes na południe)."""
    P = [('porcelana', porcelain), ('miska', bowl_top), ('deska', seat), ('zbiornik', tank_front),
         ('chrom', chrome)]
    parts = [([5.5, 0, 6], [10.5, 5, 12], 'porcelana'),
             ([4, 5, 4], [12, 8, 14], 'porcelana', {'up': 'miska'}),
             ([3.8, 8, 4], [12.2, 8.6, 14], 'deska'),
             ([4, 8.6, 4], [12, 15, 4.8], 'deska'),
             ([3.5, 8, 0.5], [12.5, 15, 4], 'porcelana', {'south': 'zbiornik', 'north': 'zbiornik'}),
             ([3, 15, 0], [13, 15.8, 4.5], 'porcelana'),
             ([7, 15.8, 1.6], [9, 16.2, 2.8], 'chrom'),
             ([7.4, 2, 0], [8.6, 3.2, 6], 'chrom')]
    model('kibel', parts, P, 33)


def regal_sklepowy():
    """Biały regał sklepowy z cenówkami: puszki, słoiki, kartony i butelki, część wyszabrowana."""
    P = [('metal', shop_metal), ('cenowki', price_rail), ('puszki', goods('puszki')), ('sloiki', goods('sloiki')),
         ('kartony', goods('kartony')), ('butelki', goods('butelki')), ('gora', goods_top),
         ('ciemny', plain((44, 44, 46), 3))]
    parts = []
    for x in (0, 15):
        for z in (0, 15):
            parts.append(([x, 0, z], [x + 1, 16, z + 1], 'metal'))
    parts.append(([0.2, 0, 0], [15.8, 16, 0.6], 'metal'))
    for y in (0, 4, 8, 12):
        parts.append(([0, y, 0], [16, y + 0.6, 16], 'metal'))
        parts.append(([0, y + 0.6, 15.4], [16, y + 1.4, 16], 'metal', {'south': 'cenowki'}))
    parts.append(([0, 15.4, 0], [16, 16, 16], 'metal'))
    for y, kind, z in ((0.6, 'kartony', 14.5), (4.6, 'sloiki', 14), (8.6, 'puszki', 14.8), (12.6, 'butelki', 13.5)):
        parts.append(([1, y, 1], [15, y + 3.2, z], 'ciemny', {'south': kind, 'up': 'gora'}))
    model('regal_sklepowy', parts, P, 34)


def lodowka():
    """Przeszklona lodówka na napoje z czerwonym szyldem, dwie kratki wysokości."""
    P = [('obudowa', red_paint), ('szyba_dol', fridge_glass(False)), ('szyba_gora', fridge_glass(True)),
         ('szyld', fridge_sign), ('chrom', chrome), ('ciemny', plain((40, 40, 42), 3))]
    parts = [([0.5, 0, 1], [15.5, 15, 15], 'obudowa', {'south': 'szyba_dol'}),
             ([0.5, 15, 1], [15.5, 27, 15], 'obudowa', {'south': 'szyba_gora'}),
             ([0.3, 27, 0.8], [15.7, 31, 15.6], 'obudowa', {'south': 'szyld', 'north': 'szyld'}),
             ([13, 8, 15], [14, 22, 16], 'chrom'),
             ([1, 0, 0], [15, 1, 15], 'ciemny')]
    model('lodowka', parts, P, 35)


def dystrybutor():
    """Dystrybutor paliwa w barwach CPN: licznik mechaniczny, szyld 95, pistolet z wężem."""
    P = [('podstawa', concrete), ('dol', pump_lower), ('licznik', pump_counter), ('szyld', pump_sign),
         ('blacha', red_paint), ('waz', hose), ('chrom', chrome), ('biala', plain((230, 228, 220), 4, 2))]
    parts = [([1, 0, 3], [15, 2, 13], 'podstawa'),
             ([2, 2, 4], [14, 13, 12], 'blacha', {'south': 'dol', 'north': 'dol'}),
             ([2, 13, 4], [14, 24, 12], 'biala', {'south': 'licznik', 'north': 'licznik'}),
             ([1.5, 24, 3.5], [14.5, 28, 12.5], 'blacha', {'south': 'szyld', 'north': 'szyld'}),
             ([14, 11, 6], [15.6, 15, 10], 'chrom'),
             ([14.4, 13, 7], [16, 14, 9], 'waz'),
             ([14.6, 3, 7.5], [15.4, 11, 8.5], 'waz'),
             ([13.6, 2, 7.4], [15.4, 3, 8.6], 'waz')]
    model('dystrybutor', parts, P, 36)


def rozdzielnia():
    """Szafa elektryczna (rozdzielnia) z okienkiem liczników, trójkątem ostrzegawczym i kablami."""
    P = [('front', cabinet_front), ('bok', cabinet_side), ('blacha', plain((150, 156, 150), 4, 3)),
         ('kabel', cable), ('beton', concrete)]
    parts = [([1, 0, 2], [15, 2, 15], 'beton'),
             ([1.5, 2, 3], [14.5, 16, 14.5], 'bok', {'south': 'front', 'up': 'blacha', 'down': 'blacha'}),
             ([1, 15.5, 2.5], [15, 16.5, 15], 'blacha'),
             ([4, 0, 1], [5.5, 3, 3], 'kabel'), ([7, 0, 0.5], [8.5, 3, 3], 'kabel'),
             ([10.5, 0, 1], [12, 3, 3], 'kabel')]
    model('rozdzielnia', parts, P, 37)


def frytkownica():
    """Dwukomorowa frytkownica gastronomiczna: jeden koszyk zawieszony, drugi w starym oleju."""
    P = [('stal', steel), ('front', fryer_front), ('gora', fryer_top), ('koszyk', basket),
         ('uchwyt', black_plastic)]
    parts = [([1, 0, 2], [15, 10, 15], 'stal', {'south': 'front', 'up': 'gora'}),
             ([1, 10, 2], [15, 14, 3], 'stal'),
             ([2, 10, 4], [7, 13, 10], 'koszyk'),
             ([3.8, 12, 10], [5.2, 12.8, 15.5], 'uchwyt'),
             ([9, 8.5, 4], [14, 10.6, 10], 'koszyk'),
             ([10.8, 10, 10], [12.2, 10.8, 15.5], 'uchwyt'),
             ([1.5, 0, 2.5], [3, 1, 4], 'uchwyt'), ([13, 0, 2.5], [14.5, 1, 4], 'uchwyt')]
    model('frytkownica', parts, P, 38)


def kanistry():
    """Sterta kanistrów: zielony i dwa czerwone stoją, jeden leży; na jednym naklejka z notką."""
    R, G = (176, 36, 30), (70, 96, 52)
    P = [('czerwony', can_side(R)), ('czerwony_bok', can_end(R)), ('zielony', can_side(G)),
         ('zielony_bok', can_end(G)), ('naklejka', label_kanister), ('uchwyt', plain((60, 60, 60), 4, 2)),
         ('korek', plain((200, 170, 60), 6))]
    parts = [([1, 0, 5.5], [10, 12, 9.5], 'czerwony_bok', {'south': 'naklejka', 'north': 'czerwony'}),
             ([1, 0, 1], [10, 12, 5], 'zielony_bok', {'south': 'zielony', 'north': 'zielony'}),
             ([10.5, 0, 1], [14.5, 12, 10], 'czerwony_bok', {'east': 'czerwony', 'west': 'czerwony'}),
             ([1.5, 0, 10.5], [13.5, 4, 15.5], 'czerwony_bok', {'up': 'czerwony'}),
             ([3, 12, 2.4], [7, 13.4, 3.6], 'uchwyt'), ([3, 12, 6.9], [7, 13.4, 8.1], 'uchwyt'),
             ([11.9, 12, 3], [13.1, 13.4, 7], 'uchwyt'),
             ([8, 12, 1.8], [9.4, 13.4, 3.2], 'korek'), ([8, 12, 6.3], [9.4, 13.4, 7.7], 'korek'),
             ([13.5, 1.3, 12.3], [15, 2.7, 13.7], 'korek')]
    model('kanistry', parts, P, 39)


def wozek():
    """Porzucony wózek sklepowy z drucianym koszem, czerwoną rączką i kółkami (lekko zardzewiały)."""
    P = [('siatka', wire), ('chrom', chrome), ('raczka', handle_red), ('kolko', plain((30, 30, 32), 3))]
    parts = [([2.5, 6, 1], [13.5, 14, 14], 'siatka'),
             ([3, 2.5, 2], [13, 3, 13], 'siatka'),
             ([2.5, 13.6, 1], [13.5, 14, 14], 'chrom', {'up': 'siatka', 'down': 'siatka'}),
             ([1.5, 13.5, 14.5], [14.5, 14.7, 15.7], 'raczka'),
             ([2.6, 6, 14], [3.4, 14, 15], 'chrom'), ([12.6, 6, 14], [13.4, 14, 15], 'chrom')]
    for x in (3, 12.2):
        for z in (2, 12.2):
            parts.append(([x, 1.5, z], [x + 0.8, 6, z + 0.8], 'chrom'))
            parts.append(([x - 0.2, 0, z - 0.4], [x + 1, 1.5, z + 1.2], 'kolko'))
    model('wozek', parts, P, 40)


SKLEP = ['kasa', 'lada', 'kibel', 'regal_sklepowy', 'lodowka', 'dystrybutor', 'rozdzielnia', 'frytkownica',
         'kanistry', 'wozek']

if __name__ == '__main__':
    for fn in (kasa, lada, kibel, regal_sklepowy, lodowka, dystrybutor, rozdzielnia, frytkownica, kanistry, wozek):
        fn()
    print('ok', SKLEP)
