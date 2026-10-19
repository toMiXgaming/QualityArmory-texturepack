#!/usr/bin/env python3
"""Reaktor działki (AxonPlot): modele bloku rdzenia w kilku skinach i tekstury ich stanów.

Plugin stawia na rdzeniu (crying obsidian) niewidzialny ItemDisplay z przedmiotem
crying_obsidian i custom_model_data jak niżej; ta paczka podmienia jego model na reaktor.
Bez paczki gracz widzi zwykły blok crying obsidian, więc nic się nie psuje.

Numer modelu: 7100 + 20 * numer skina + stan (1 zasilony, 2 mało paliwa, 3 wygaszony, 4 atak).
Kryształ nad reaktorem ma numer o 10 większy (wygaszony reaktor nie ma kryształu).

  skin 0 standard    7101..7104, kryształ 7111..7114
  skin 1 kwantowy    7121..7124, kryształ 7131..7134
  skin 2 pustka      7141..7144, kryształ 7151..7154
  skin 3 piekielny   7161..7164, kryształ 7171..7174
  skin 4 krolewski   7181..7184, kryształ 7191..7194

Stany są takie same we wszystkich skinach, żeby gracz od razu je rozpoznał: zasilony świeci
kolorem skina, mało paliwa przygasa i mruga na żółto, atak pulsuje na czerwono, wygaszony jest ciemny.

Wynik: build/reactor/ (modele, tekstury, items/crying_obsidian.json).
"""
import json, math, os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'build', 'reactor')
T = 32          # tekstury 32x32 (2 teksele na piksel modelu)
FRAMES = 16     # klatki animowanych tekstur

STATE_IDS = {'active': 1, 'low': 2, 'off': 3, 'raid': 4}
LOW = (255, 186, 20)
RAID = (255, 36, 26)
DEAD = (70, 60, 60)
BLACK = (20, 20, 22)


def clamp(c):
    return tuple(max(0, min(255, int(round(v)))) for v in c)


def mix(a, b, k):
    return clamp([a[i] * (1 - k) + b[i] * k for i in range(3)])


def noise(x, y, seed=0):
    h = (x * 374761393 + y * 668265263 + seed * 2147483647) & 0xFFFFFFFF
    h = (h ^ (h >> 13)) * 1274126177 & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFF) / 255.0


# ----------------------------------------------------------------------
#  Skiny
# ----------------------------------------------------------------------

class Skin:
    def __init__(self, index, name, accent, metal, light, dark, core, trim, pillar, elements, deco=None):
        self.index, self.name, self.accent = index, name, accent
        self.metal, self.light, self.dark = metal, light, dark
        self.core, self.trim, self.pillar, self.elements = core, trim, pillar, elements
        self.deco = deco or light

    def states(self):
        # nazwa: (kolor energii, jasność, szybkość animacji, migotanie)
        return {
            'active': (self.accent, 1.0, 1.0, 0.0),
            'low': (LOW, 0.5, 0.5, 0.45),
            'off': (DEAD, 0.0, 0.0, 0.0),
            'raid': (RAID, 1.0, 2.0, 0.0),
        }

    def cmd(self, state, crystal=False):
        return 7100 + 20 * self.index + STATE_IDS[state] + (10 if crystal else 0)


def metal_tex(s, seed, rivets=True, sheen=True):
    """Płyta w barwach skina z ukośnym połyskiem, fazą przy krawędziach i nitami w rogach."""
    im = Image.new('RGBA', (T, T))
    px = im.load()
    for y in range(T):
        for x in range(T):
            c = mix(s.metal, s.light, 0.12 + 0.18 * noise(x, y, seed) + (0.15 * ((x + y) % 16 < 3) if sheen else 0))
            if x in (0, T - 1) or y in (0, T - 1):
                c = s.dark
            elif x == 1 or y == 1:
                c = mix(c, s.light, 0.6)
            elif x == T - 2 or y == T - 2:
                c = mix(c, s.dark, 0.5)
            px[x, y] = c + (255,)
    if rivets:
        for rx, ry in ((4, 4), (T - 5, 4), (4, T - 5), (T - 5, T - 5)):
            px[rx, ry] = s.light + (255,)
            px[rx + 1, ry + 1] = s.dark + (255,)
            px[rx + 1, ry] = mix(s.light, s.metal, 0.5) + (255,)
    return im


# Boki podstawy pokazują dół tekstury (auto UV: v = 16 - y), więc wzór rysujemy od dołu.

def trim_hazard(s):
    im = metal_tex(s, 3, rivets=False)
    px = im.load()
    for y in range(T):
        for x in range(T):
            if 26 <= y <= 30:
                px[x, y] = ((216, 127, 51) if ((x + y) // 3) % 2 == 0 else BLACK) + (255,)
            elif y in (25, 31):
                px[x, y] = s.dark + (255,)
    return im


def trim_seam(s):
    """Gładki biały panel z cienką szarą fugą i diodami."""
    im = metal_tex(s, 3, rivets=False, sheen=False)
    px = im.load()
    for x in range(T):
        px[x, 27] = s.dark + (255,)
        px[x, 28] = mix(s.dark, s.metal, 0.5) + (255,)
    for x in range(3, T, 8):
        px[x, 30] = (90, 100, 115, 255)
        px[x + 1, 30] = (90, 100, 115, 255)
    return im


def trim_endstone(s):
    """Ciemny obsydian, u dołu jasna skorupa kamienia Endu z kraterkami."""
    im = metal_tex(s, 3, rivets=False, sheen=False)
    px = im.load()
    for y in range(T):
        for x in range(T):
            edge = 25 + int(2 * noise(x, 0, 9))
            if y >= edge:
                c = mix((219, 222, 158), (190, 190, 130), noise(x, y, 4))
                if noise(x, y, 6) > 0.85:
                    c = (170, 165, 110)
                px[x, y] = c + (255,)
            elif y == edge - 1:
                px[x, y] = mix(s.dark, (120, 80, 160), 0.4) + (255,)
    return im


def trim_gold_band(s):
    """Czarny kamień z pasem złota."""
    im = metal_tex(s, 3, rivets=False, sheen=False)
    px = im.load()
    for y in range(T):
        for x in range(T):
            n = noise(x, y, 13)
            c = mix(s.metal, s.dark, 0.5 * n)
            if 27 <= y <= 29:
                c = mix((230, 180, 40), (255, 230, 110), 0.5 if (x + y) % 6 == 0 else 0.1 * n)
            elif y in (26, 30):
                c = (120, 85, 20)
            px[x, y] = c + (255,)
    return im


def trim_engraved(s):
    """Złoto z grawerem w romby."""
    im = metal_tex(s, 3, rivets=False)
    px = im.load()
    for y in range(22, T):
        for x in range(T):
            if (x + y) % 6 == 0 or (x - y) % 6 == 0:
                px[x, y] = s.dark + (255,)
    return im


def pillar_groove(s):
    im = metal_tex(s, 5)
    px = im.load()
    for y in range(4, T - 4):
        px[15, y] = s.dark + (255,)
        px[16, y] = mix(s.light, s.metal, 0.3) + (255,)
    return im


def pillar_obsidian(s):
    """Obsydian z fioletowymi błyskami."""
    im = Image.new('RGBA', (T, T))
    px = im.load()
    for y in range(T):
        for x in range(T):
            n = noise(x, y, 21)
            c = mix(s.metal, s.dark, 0.6 * n)
            if n > 0.92:
                c = (150, 90, 220)
            elif n > 0.85:
                c = mix(s.metal, (110, 60, 170), 0.6)
            if x in (0, T - 1):
                c = mix(c, (140, 100, 200), 0.6)
            elif x in (1, T - 2):
                c = mix(c, (90, 60, 140), 0.4)
            px[x, y] = c + (255,)
    return im


def pillar_banded(s):
    """Czarny kamień z trzema złotymi obręczami."""
    im = trim_gold_band(s).copy()
    px = im.load()
    for y in range(T):
        for x in range(T):
            n = noise(x, y, 31)
            c = mix(s.light, s.metal, 0.3 + 0.4 * n)
            if x in (0, T - 1):
                c = s.dark
            if y % 11 in (4, 5):
                c = mix((230, 180, 40), (255, 230, 110), 0.3 * n)
            elif y % 11 in (3, 6):
                c = (120, 85, 20)
            px[x, y] = c + (255,)
    return im


def pillar_fluted(s):
    """Złota kolumna z pionowymi żłobieniami."""
    im = Image.new('RGBA', (T, T))
    px = im.load()
    for y in range(T):
        for x in range(T):
            k = 0.5 + 0.5 * math.cos(x / T * 2 * math.pi * 4)
            c = mix(s.dark, s.light, 0.25 + 0.6 * k)
            if y < 3 or y > T - 4:
                c = mix(s.light, s.metal, 0.3)
            px[x, y] = c + (255,)
    return im


# Okno rdzenia: każda funkcja dostaje (x, y, t, stan) i zwraca kolor teksela.

def core_rods(color, bright, speed, flick, x, y, t):
    glass = mix((18, 20, 26), (30, 34, 44), 0.5 * noise(x, y, 11))
    wave = 0.5 + 0.5 * math.sin((y / T) * 2 * math.pi * 2 + t * 2 * math.pi * speed)
    if x % 8 in (3, 4) and bright > 0:
        k = bright * flick * (0.55 + 0.45 * wave)
        c = mix((40, 50, 40), color, k)
        if x % 8 == 3:
            c = mix(c, (255, 255, 230), 0.25 * k)
    elif x % 8 in (2, 5) and bright > 0:
        c = mix(glass, color, 0.28 * bright * flick * wave)
    elif x % 8 in (3, 4):
        c = (46, 42, 44)
    else:
        c = glass
    if (x - y) % 32 in (0, 1) and x < 14:
        c = mix(c, (200, 210, 230), 0.12)
    return c


def core_grid(color, bright, speed, flick, x, y, t):
    """Jasne szkło z siatką kwantową; po liniach siatki przesuwa się fala energii."""
    glass = mix((26, 34, 48), (40, 52, 70), 0.5 * noise(x, y, 12))
    line = x % 8 == 0 or y % 8 == 0
    node = x % 8 == 0 and y % 8 == 0
    wave = 0.5 + 0.5 * math.sin(((x + y) / T) * 2 * math.pi + t * 2 * math.pi * speed)
    if bright <= 0:
        return (60, 64, 72) if line else glass
    k = bright * flick
    if node:
        return mix(color, (255, 255, 255), 0.6 * k)
    if line:
        return mix((50, 60, 75), color, k * (0.45 + 0.55 * wave))
    # poświata w środku oczek
    d = min(x % 8, 8 - x % 8, y % 8, 8 - y % 8)
    return mix(glass, color, k * 0.18 * wave * (1 if d <= 1 else 0.4))


def core_stars(color, bright, speed, flick, x, y, t):
    """Pustka: czarne niebo z mgławicą, która wiruje, i migoczącymi gwiazdami."""
    cx, cy = x - 15.5, y - 15.5
    r = math.hypot(cx, cy)
    a = math.atan2(cy, cx)
    swirl = 0.5 + 0.5 * math.sin(a * 2 + r * 0.35 - t * 2 * math.pi * speed)
    c = mix((8, 4, 16), (22, 10, 38), noise(x, y, 14))
    if bright > 0:
        c = mix(c, color, bright * flick * (0.25 + 0.6 * swirl) * max(0.0, 1 - r / 24))
    n = noise(x, y, 15)
    if n > 0.93:
        tw = 0.5 + 0.5 * math.sin(t * 2 * math.pi * 2 + n * 40)
        c = mix(c, (255, 255, 255) if bright > 0 else (90, 90, 110), 0.5 + 0.5 * tw)
    return c


def _cracks():
    """Sieć pęknięć: krawędzie komórek Woronoja na kafelku 32x32 (zawija się)."""
    pts = [(noise(i, 0, 40) * T, noise(i, 1, 40) * T) for i in range(16)]
    out = {}
    for y in range(T):
        for x in range(T):
            ds = sorted(min(math.hypot(x - px_ + dx, y - py_ + dy) for dx in (-T, 0, T) for dy in (-T, 0, T))
                        for px_, py_ in pts)
            out[x, y] = ds[1] - ds[0]
    return out


CRACKS = _cracks()


def core_cracks(color, bright, speed, flick, x, y, t):
    """Czarny kamień popękany; w szczelinach płynie ogień w kolorze stanu."""
    n = noise(x, y, 16)
    c = mix((40, 34, 38), (22, 18, 20), 0.6 * n)
    e = CRACKS[x, y]
    if e < 1.1:
        flow = 0.5 + 0.5 * math.sin(y / T * 2 * math.pi * 2 + t * 2 * math.pi * speed + x * 0.2)
        k = bright * flick * (0.6 + 0.4 * flow) * (1 if e < 0.6 else 0.5)
        c = mix((60, 30, 26) if bright <= 0 else (50, 20, 16), color, k)
        if e < 0.4 and bright > 0:
            c = mix(c, (255, 255, 230), 0.3 * k)
    return c


def core_facets(color, bright, speed, flick, x, y, t):
    """Klejnot: złota krata w romby, w każdym rombie szlif z błyskiem przesuwającym się po skosie."""
    u, v = (x + y) % 16, (x - y) % 16
    if u in (0, 15) or v in (0, 15):
        return (200, 150, 40) if (x + y) % 4 else (255, 225, 110)
    shade = 0.45 + 0.35 * (u / 15) + 0.2 * (1 - v / 15)
    gem = mix((30, 18, 34), color, (0.35 + 0.5 * shade) * bright * flick) if bright > 0 else mix((40, 34, 44), (70, 64, 74), shade)
    glint = ((x + y) / 2 - t * 2 * T * speed) % T
    if bright > 0 and glint < 2.5:
        gem = mix(gem, (255, 255, 255), 0.55 * bright)
    return gem


def energy_frames(s, state, core):
    color, bright, speed, flicker = s.states()[state]
    frames = []
    for f in range(FRAMES):
        t = f / FRAMES
        im = Image.new('RGBA', (T, T))
        px = im.load()
        flick = 1.0 - flicker * (0.5 + 0.5 * math.sin(t * 2 * math.pi * 3)) * (f % 5 == 0)
        for y in range(T):
            for x in range(T):
                px[x, y] = core(color, bright, speed, flick, x, y, t) + (255,)
        frames.append(im)
    return frames


def top_frames(s, state):
    """Górna płyta z emiterem: pierścień w kolorze stanu, w środku przesłona."""
    color, bright, speed, _ = s.states()[state]
    base = metal_tex(s, 7)
    frames = []
    cx = cy = (T - 1) / 2
    for f in range(FRAMES):
        t = f / FRAMES
        im = base.copy()
        px = im.load()
        pulse = 0.75 + 0.25 * math.sin(t * 2 * math.pi * max(speed, 0.5))
        for y in range(T):
            for x in range(T):
                d = math.hypot(x - cx, y - cy)
                if d < 4:
                    px[x, y] = mix(s.dark, (10, 10, 12), 0.5) + (255,)
                elif d < 6.2:
                    px[x, y] = (mix((50, 40, 30), color, bright * pulse) if bright else (40, 38, 40)) + (255,)
                elif d < 7.4:
                    px[x, y] = s.dark + (255,)
                elif d < 8.4:
                    px[x, y] = s.light + (255,)
        for i in range(8, 13):
            for (sx, sy) in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
                x, y = int(cx + sx * i * 0.72), int(cy + sy * i * 0.72)
                px[x, y] = (mix(s.dark, color, 0.5 * bright * pulse) if bright else s.dark) + (255,)
        frames.append(im)
    return frames


def glow_frames(s, state):
    """Świecące elementy ozdobne (pierścień, kamienie, żyły): czysty kolor stanu, pulsuje."""
    color, bright, speed, flicker = s.states()[state]
    frames = []
    for f in range(FRAMES):
        t = f / FRAMES
        im = Image.new('RGBA', (16, 16))
        px = im.load()
        pulse = 0.8 + 0.2 * math.sin(t * 2 * math.pi * max(speed, 0.5))
        if flicker and f % 5 == 0:
            pulse *= 0.5
        for y in range(16):
            for x in range(16):
                if bright <= 0:
                    c = mix((44, 40, 44), (60, 56, 60), noise(x, y, 3))
                else:
                    band = 0.5 + 0.5 * math.sin((x + y) / 16 * 2 * math.pi - t * 2 * math.pi * speed)
                    c = mix(mix(color, (40, 30, 30), 0.35), mix(color, (255, 255, 240), 0.35), pulse * (0.4 + 0.6 * band))
                px[x, y] = c + (255,)
        frames.append(im)
    return frames


def crystal_frames(s, state):
    color, bright, speed, flicker = s.states()[state]
    frames = []
    S = 16
    for f in range(FRAMES):
        t = f / FRAMES
        im = Image.new('RGBA', (S, S))
        px = im.load()
        pulse = 0.8 + 0.2 * math.sin(t * 2 * math.pi * max(speed, 0.5))
        if flicker and f % 5 == 0:
            pulse *= 0.6
        dark = mix(color, (20, 10, 20), 0.6)
        for y in range(S):
            for x in range(S):
                edge = min(x, y, S - 1 - x, S - 1 - y)
                k = 0.55 + 0.45 * (edge / 7.5)
                c = mix(mix(color, dark, 0.3 * (1 - k)), (255, 252, 235), 0.38 * k * k * pulse)
                if edge == 0:
                    c = mix(color, dark, 0.45)
                if x == y or x == S - 1 - y:
                    c = mix(c, (255, 255, 255), 0.2)
                px[x, y] = c + (255,)
        frames.append(im)
    return frames


# ----------------------------------------------------------------------
#  Bryły
# ----------------------------------------------------------------------

def face_uv(f, t, face):
    """UV jak automatyczne w grze, ale przesunięte do 0..16: elementy wystające poza blok
    (korony, obeliski) dostałyby inaczej UV spoza tekstury i próbkowały sąsiednie w atlasie."""
    x1, y1, z1 = f
    x2, y2, z2 = t
    uv = {
        'north': [16 - x2, 16 - y2, 16 - x1, 16 - y1],
        'south': [x1, 16 - y2, x2, 16 - y1],
        'east': [16 - z2, 16 - y2, 16 - z1, 16 - y1],
        'west': [z1, 16 - y2, z2, 16 - y1],
        'up': [x1, z1, x2, z2],
        'down': [x1, 16 - z2, x2, 16 - z1],
    }[face]
    for i in (0, 1):
        lo, hi = uv[i], uv[i + 2]
        shift = -lo if lo < 0 else 16 - hi if hi > 16 else 0
        uv[i], uv[i + 2] = round(lo + shift, 4), round(hi + shift, 4)
    return uv


def box(name, f, t, tex, which='nsewud', per_face=None):
    names = {'n': 'north', 's': 'south', 'e': 'east', 'w': 'west', 'u': 'up', 'd': 'down'}
    fc = {names[c]: {'texture': tex} for c in which}
    if per_face:
        for k, v in per_face.items():
            fc[k] = {'texture': v}
    for face, d in fc.items():
        d['uv'] = face_uv(f, t, face)
    return {'name': name, 'from': f, 'to': t, 'faces': fc}


def grille(els, ys, tex='#metal'):
    for y in ys:
        els.append(box('krata', [3, y, 0.5], [13, y + 1, 1.25], tex, which='nud'))
        els.append(box('krata', [3, y, 14.75], [13, y + 1, 15.5], tex, which='sud'))
        els.append(box('krata', [0.5, y, 3], [1.25, y + 1, 13], tex, which='wud'))
        els.append(box('krata', [14.75, y, 3], [15.5, y + 1, 13], tex, which='eud'))


def corners(size):
    return [(0, 0), (16 - size, 0), (0, 16 - size), (16 - size, 16 - size)]


# Rdzeń zawsze ma ściany 1.25 px w głąb: przy skali 1.2 to wciąż przed ścianą prawdziwego bloku,
# więc crying obsidian spod spodu nigdzie nie prześwituje.

def els_standard():
    els = [
        box('podstawa', [0, 0, 0], [16, 2.5, 16], '#trim', per_face={'up': '#metal', 'down': '#metal'}),
        box('pokrywa', [0, 13.5, 0], [16, 16, 16], '#metal', per_face={'up': '#top'}),
        box('rdzen', [1.25, 2.5, 1.25], [14.75, 13.5, 14.75], '#core', which='nsew'),
    ]
    for x, z in corners(3):
        els.append(box('slup', [x, 2.5, z], [x + 3, 13.5, z + 3], '#pillar', which='nsew'))
    grille(els, (4.75, 8, 11.25))
    return els


def els_kwantowy():
    """Biała, gładka kapsuła: cienkie szyny w rogach, świecący pierścień w pasie, kopułka na górze."""
    els = [
        box('podstawa', [0, 0, 0], [16, 2, 16], '#trim', per_face={'up': '#metal', 'down': '#metal'}),
        box('pokrywa', [0, 14, 0], [16, 16, 16], '#metal', per_face={'up': '#top'}),
        box('rdzen', [1.25, 2, 1.25], [14.75, 14, 14.75], '#core', which='nsew'),
        box('pierscien', [0.5, 7.5, 0.5], [15.5, 8.5, 15.5], '#glow', which='nsewud'),
        box('kopula', [5, 16, 5], [11, 16.75, 11], '#metal', which='nsewu', per_face={'up': '#glow'}),
    ]
    for x, z in corners(2):
        els.append(box('szyna', [x, 2, z], [x + 2, 14, z + 2], '#pillar', which='nsew'))
    for y in (2.5, 13):
        els.append(box('listwa', [0.25, y, 0.25], [15.75, y + 0.5, 15.75], '#metal', which='nsewud'))
    return els


def els_pustka():
    """Obsydianowy ołtarz Endu: kamienna podstawa, cztery obeliski wyrastające ponad pokrywę."""
    els = [
        box('podstawa', [0, 0, 0], [16, 3, 16], '#trim', per_face={'up': '#metal', 'down': '#trim'}),
        box('pokrywa', [0, 13, 0], [16, 15.5, 16], '#metal', per_face={'up': '#top'}),
        box('rdzen', [1.25, 3, 1.25], [14.75, 13, 14.75], '#core', which='nsew'),
    ]
    for x, z in corners(2.5):
        els.append(box('obelisk', [x, 3, z], [x + 2.5, 19, z + 2.5], '#pillar', which='nsewu'))
        els.append(box('szczyt', [x + 0.5, 19, z + 0.5], [x + 2, 21, z + 2], '#pillar', which='nsewu'))
        els.append(box('runa', [x - 0.15, 16.25, z - 0.15], [x + 2.65, 17, z + 2.65], '#glow', which='nsew'))
    return els


def els_piekielny():
    """Piekielny piec z czarnego kamienia: grube słupy ze złotymi obręczami, misa na górze,
    nad którą unosi się kryształ jak płomień."""
    els = [
        box('podstawa', [0, 0, 0], [16, 3, 16], '#trim', per_face={'up': '#metal', 'down': '#metal'}),
        box('pokrywa', [0, 13, 0], [16, 15, 16], '#metal', per_face={'up': '#top'}),
        box('rdzen', [1.25, 3, 1.25], [14.75, 13, 14.75], '#core', which='nsew'),
    ]
    for x, z in corners(3.5):
        els.append(box('slup', [x, 3, z], [x + 3.5, 13, z + 3.5], '#pillar', which='nsew'))
    # misa: niskie ścianki wokół pokrywy
    els += [
        box('misa', [0, 15, 0], [16, 17, 1.5], '#trim', which='nsewu'),
        box('misa', [0, 15, 14.5], [16, 17, 16], '#trim', which='nsewu'),
        box('misa', [0, 15, 1.5], [1.5, 17, 14.5], '#trim', which='ewu'),
        box('misa', [14.5, 15, 1.5], [16, 17, 14.5], '#trim', which='ewu'),
        box('zar', [1.5, 15, 1.5], [14.5, 15.5, 14.5], '#core', which='u'),
    ]
    # żyły na środku każdej ściany
    els += [
        box('zyla', [7.5, 3, 0.75], [8.5, 13, 1.25], '#glow', which='nwe'),
        box('zyla', [7.5, 3, 14.75], [8.5, 13, 15.25], '#glow', which='swe'),
        box('zyla', [0.75, 3, 7.5], [1.25, 13, 8.5], '#glow', which='wns'),
        box('zyla', [14.75, 3, 7.5], [15.25, 13, 8.5], '#glow', which='ens'),
    ]
    return els


def els_krolewski():
    """Złoty relikwiarz: dwustopniowa podstawa, żłobione kolumny, korona z kamieniami na górze."""
    els = [
        box('podstawa', [0, 0, 0], [16, 1.5, 16], '#trim', per_face={'up': '#metal', 'down': '#metal'}),
        box('stopien', [0.75, 1.5, 0.75], [15.25, 3, 15.25], '#trim', per_face={'up': '#metal'}, which='nsewu'),
        box('pokrywa', [0, 13, 0], [16, 15, 16], '#metal', per_face={'up': '#top'}),
        box('rdzen', [1.25, 3, 1.25], [14.75, 13, 14.75], '#core', which='nsew'),
    ]
    for x, z in corners(2.5):
        els.append(box('kolumna', [x, 3, z], [x + 2.5, 12, z + 2.5], '#pillar', which='nsew'))
        els.append(box('kapitel', [x - 0.25 if x == 0 else x, 12, z - 0.25 if z == 0 else z],
                       [x + 2.75 if x == 0 else x + 2.5, 13, z + 2.75 if z == 0 else z + 2.5], '#metal'))
        # zęby korony w rogach z kamieniem
        els.append(box('zab', [x, 15, z], [x + 2.5, 18, z + 2.5], '#metal', which='nsewu'))
        els.append(box('kamien', [x + 0.75, 18, z + 0.75], [x + 1.75, 19, z + 1.75], '#glow'))
    for a, b in (([7, 15, 0], [9, 17, 1]), ([7, 15, 15], [9, 17, 16]), ([0, 15, 7], [1, 17, 9]), ([15, 15, 7], [16, 17, 9])):
        els.append(box('zab', a, b, '#metal', which='nsewu'))
    for a, b in (([7.5, 17, 0.25], [8.5, 17.75, 0.75]), ([7.5, 17, 15.25], [8.5, 17.75, 15.75]),
                 ([0.25, 17, 7.5], [0.75, 17.75, 8.5]), ([15.25, 17, 7.5], [15.75, 17.75, 8.5])):
        els.append(box('kamien', a, b, '#glow'))
    return els


SKINS = {
    'standard': Skin(0, 'Standard', (60, 240, 90), (52, 54, 60), (84, 88, 96), (28, 29, 33),
                     core_rods, trim_hazard, pillar_groove, els_standard),
    'kwantowy': Skin(1, 'Kwantowy', (40, 215, 255), (196, 202, 212), (236, 240, 246), (120, 128, 142),
                     core_grid, trim_seam, pillar_groove, els_kwantowy),
    'pustka': Skin(2, 'Pustka', (186, 84, 255), (34, 22, 50), (74, 52, 104), (12, 8, 20),
                   core_stars, trim_endstone, pillar_obsidian, els_pustka),
    'piekielny': Skin(3, 'Piekielny', (70, 225, 215), (44, 38, 42), (96, 84, 90), (20, 16, 18),
                      core_cracks, trim_gold_band, pillar_banded, els_piekielny),
    'krolewski': Skin(4, 'Królewski', (255, 70, 200), (214, 166, 46), (255, 230, 120), (130, 88, 20),
                      core_facets, trim_engraved, pillar_fluted, els_krolewski),
}


def strip(frames, frametime):
    w, h = frames[0].size
    im = Image.new('RGBA', (w, h * len(frames)))
    for i, fr in enumerate(frames):
        im.paste(fr, (0, i * h))
    return im, {'animation': {'frametime': frametime, 'interpolate': True}}


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if isinstance(data, Image.Image):
        data.save(path)
    else:
        with open(path, 'w') as fh:
            json.dump(data, fh, indent=1)


def write_anim(tex, name, frames, frametime, animated):
    if animated:
        im, meta = strip(frames, frametime)
        write(os.path.join(tex, name + '.png'), im)
        write(os.path.join(tex, name + '.png.mcmeta'), meta)
    else:
        write(os.path.join(tex, name + '.png'), frames[0])


def main():
    entries = []
    for sid, s in SKINS.items():
        ns = 'axon:block/reactor/' + sid + '/'
        tex = os.path.join(OUT, 'assets/axon/textures/block/reactor', sid)
        models = os.path.join(OUT, 'assets/axon/models/block/reactor', sid)
        write(os.path.join(tex, 'metal.png'), metal_tex(s, 1))
        write(os.path.join(tex, 'trim.png'), s.trim(s))
        write(os.path.join(tex, 'pillar.png'), s.pillar(s))
        for st, (_, _, speed, _) in s.states().items():
            frametime = 2 if speed >= 1 else 3
            animated = st != 'off'
            write_anim(tex, 'core_' + st, energy_frames(s, st, s.core), frametime, animated)
            write_anim(tex, 'top_' + st, top_frames(s, st), frametime, animated)
            write_anim(tex, 'glow_' + st, glow_frames(s, st), frametime, animated)
            if st != 'off':
                write_anim(tex, 'crystal_' + st, crystal_frames(s, st), frametime, True)

        write(os.path.join(models, 'shell.json'), {
            'parent': 'minecraft:block/block',
            'textures': {'particle': ns + 'metal', 'metal': ns + 'metal', 'trim': ns + 'trim', 'pillar': ns + 'pillar'},
            'elements': s.elements(),
        })
        for st in STATE_IDS:
            write(os.path.join(models, st + '.json'), {
                'parent': ns + 'shell',
                'textures': {'core': ns + 'core_' + st, 'top': ns + 'top_' + st, 'glow': ns + 'glow_' + st},
            })
            entries.append({'threshold': s.cmd(st), 'model': {'type': 'minecraft:model', 'model': ns + st}})
            if st == 'off':
                continue
            write(os.path.join(models, 'crystal_' + st + '.json'), {
                'textures': {'particle': ns + 'crystal_' + st, 'c': ns + 'crystal_' + st},
                'elements': [box('krysztal', [4.5, 4.5, 4.5], [11.5, 11.5, 11.5], '#c')],
            })
            entries.append({'threshold': s.cmd(st, True),
                            'model': {'type': 'minecraft:model', 'model': ns + 'crystal_' + st}})
    entries.sort(key=lambda e: e['threshold'])
    # Bez custom_model_data (albo z mniejszym) crying obsidian wygląda jak zwykle.
    write(os.path.join(OUT, 'assets/minecraft/items/crying_obsidian.json'), {'model': {
        'type': 'minecraft:range_dispatch', 'property': 'minecraft:custom_model_data', 'index': 0,
        'entries': entries,
        'fallback': {'type': 'minecraft:model', 'model': 'minecraft:block/crying_obsidian'},
    }})
    print('ok', OUT, len(entries), 'modeli')


if __name__ == '__main__':
    main()
