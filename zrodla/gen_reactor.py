#!/usr/bin/env python3
"""Reaktor działki (AxonPlot): model bloku rdzenia i tekstury jego stanów.

Plugin stawia na rdzeniu (crying obsidian) niewidzialny ItemDisplay z przedmiotem
crying_obsidian i custom_model_data jak niżej; ta paczka podmienia jego model na reaktor.
Bez paczki gracz widzi zwykły blok crying obsidian, więc nic się nie psuje.

  7101 obudowa, reaktor zasilony      7111 kryształ, zasilony
  7102 obudowa, mało paliwa           7112 kryształ, mało paliwa
  7103 obudowa, wygaszony             (wygaszony reaktor nie ma kryształu)
  7104 obudowa, działka atakowana     7114 kryształ, atakowana

Wynik: build/reactor/ (modele, tekstury, items/crying_obsidian.json).
"""
import json, math, os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'build', 'reactor')
T = 32          # tekstury 32x32 (2 teksele na piksel modelu)
FRAMES = 16     # klatki animowanych tekstur

STATES = {
    # nazwa: (kolor energii, jasność, szybkość animacji, migotanie)
    'active': ((255, 150, 40), 1.0, 1.0, 0.0),
    'low':    ((235, 190, 60), 0.55, 0.5, 0.35),
    'off':    ((70, 60, 60), 0.0, 0.0, 0.0),
    'raid':   ((255, 40, 30), 1.0, 2.0, 0.0),
}
CMD = {'active': 7101, 'low': 7102, 'off': 7103, 'raid': 7104}
CRYSTAL_CMD = {'active': 7111, 'low': 7112, 'raid': 7114}

METAL = (52, 54, 60)
METAL_LIGHT = (84, 88, 96)
METAL_DARK = (28, 29, 33)
ORANGE = (216, 127, 51)
BLACK = (20, 20, 22)


def clamp(c):
    return tuple(max(0, min(255, int(round(v)))) for v in c)


def mix(a, b, k):
    return clamp([a[i] * (1 - k) + b[i] * k for i in range(3)])


def noise(x, y, seed=0):
    h = (x * 374761393 + y * 668265263 + seed * 2147483647) & 0xFFFFFFFF
    h = (h ^ (h >> 13)) * 1274126177 & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFF) / 255.0


def metal_tex(seed, rivets=True):
    """Ciemna płyta z ukośnym połyskiem, fazą przy krawędziach i nitami w rogach."""
    im = Image.new('RGBA', (T, T))
    px = im.load()
    for y in range(T):
        for x in range(T):
            c = mix(METAL, METAL_LIGHT, 0.12 + 0.18 * noise(x, y, seed) + 0.15 * ((x + y) % 16 < 3))
            if x in (0, T - 1) or y in (0, T - 1):
                c = METAL_DARK
            elif x == 1 or y == 1:
                c = mix(c, METAL_LIGHT, 0.6)
            elif x == T - 2 or y == T - 2:
                c = mix(c, METAL_DARK, 0.5)
            px[x, y] = c + (255,)
    if rivets:
        for rx, ry in ((4, 4), (T - 5, 4), (4, T - 5), (T - 5, T - 5)):
            px[rx, ry] = METAL_LIGHT + (255,)
            px[rx + 1, ry + 1] = METAL_DARK + (255,)
            px[rx + 1, ry] = mix(METAL_LIGHT, METAL, 0.5) + (255,)
    return im


def trim_tex():
    """Pas u podstawy: ukośne pomarańczowo-czarne pasy ostrzegawcze między metalowymi listwami."""
    im = metal_tex(3, rivets=False)
    px = im.load()
    for y in range(T):
        for x in range(T):
            v = y % T  # u podstawy (2.5 px modelu) widać górę tekstury? auto uv: v = 16 - y
            if 26 <= v <= 30:
                stripe = ((x + v) // 3) % 2 == 0
                px[x, y] = (ORANGE if stripe else BLACK) + (255,)
            elif v == 25 or v == 31:
                px[x, y] = METAL_DARK + (255,)
    return im


def pillar_tex():
    """Słup: metal z pionowym rowkiem i lampką statusu (lampka bierze kolor stanu z rdzenia)."""
    im = metal_tex(5)
    px = im.load()
    for y in range(4, T - 4):
        px[15, y] = METAL_DARK + (255,)
        px[16, y] = mix(METAL_LIGHT, METAL, 0.3) + (255,)
    return im


def energy_frames(state):
    """Okno rdzenia: ciemne szkło z pionowymi prętami paliwowymi, po których płynie energia w górę."""
    color, bright, speed, flicker = STATES[state]
    frames = []
    for f in range(FRAMES):
        t = f / FRAMES
        im = Image.new('RGBA', (T, T))
        px = im.load()
        flick = 1.0 - flicker * (0.5 + 0.5 * math.sin(t * 2 * math.pi * 3)) * (f % 5 == 0)
        for y in range(T):
            for x in range(T):
                glass = mix((18, 20, 26), (30, 34, 44), 0.5 * noise(x, y, 11))
                rod = x % 8 in (3, 4)
                if rod and bright > 0:
                    wave = 0.5 + 0.5 * math.sin((y / T) * 2 * math.pi * 2 + t * 2 * math.pi * speed)
                    k = bright * flick * (0.55 + 0.45 * wave)
                    c = mix((60, 40, 30), color, k)
                    if x % 8 == 3:
                        c = mix(c, (255, 255, 230), 0.25 * k)
                elif x % 8 in (2, 5) and bright > 0:
                    glow = 0.5 + 0.5 * math.sin((y / T) * 2 * math.pi * 2 + t * 2 * math.pi * speed)
                    c = mix(glass, color, 0.28 * bright * flick * glow)
                elif rod:
                    c = (46, 42, 44)
                else:
                    c = glass
                # odblask na szybie
                if (x - y) % 32 in (0, 1) and x < 14:
                    c = mix(c, (200, 210, 230), 0.12)
                px[x, y] = c + (255,)
        frames.append(im)
    return frames


def top_frames(state):
    """Górna płyta z emiterem: pierścień w kolorze stanu, w środku przesłona."""
    color, bright, speed, _ = STATES[state]
    base = metal_tex(7)
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
                    px[x, y] = mix(METAL_DARK, (10, 10, 12), 0.5) + (255,)
                elif d < 6.2:
                    px[x, y] = (mix((60, 40, 30), color, bright * pulse) if bright else (40, 38, 40)) + (255,)
                elif d < 7.4:
                    px[x, y] = METAL_DARK + (255,)
                elif d < 8.4:
                    px[x, y] = METAL_LIGHT + (255,)
        # cztery kanały od emitera do rogów
        for i in range(8, 13):
            for (sx, sy) in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
                x, y = int(cx + sx * i * 0.72), int(cy + sy * i * 0.72)
                px[x, y] = (mix(METAL_DARK, color, 0.5 * bright * pulse) if bright else METAL_DARK) + (255,)
        frames.append(im)
    return frames


def crystal_frames(state):
    color, bright, speed, flicker = STATES[state]
    frames = []
    S = 16
    for f in range(FRAMES):
        t = f / FRAMES
        im = Image.new('RGBA', (S, S))
        px = im.load()
        pulse = 0.8 + 0.2 * math.sin(t * 2 * math.pi * max(speed, 0.5))
        if flicker and f % 5 == 0:
            pulse *= 0.6
        for y in range(S):
            for x in range(S):
                edge = min(x, y, S - 1 - x, S - 1 - y)
                k = 0.55 + 0.45 * (edge / 7.5)
                c = mix(mix(color, (120, 30, 10), 0.25 * (1 - k)), (255, 250, 220), 0.38 * k * k * pulse)
                if edge == 0:
                    c = mix(color, (90, 30, 10), 0.35)
                if x == y or x == S - 1 - y:
                    c = mix(c, (255, 255, 255), 0.2)
                px[x, y] = c + (255,)
        frames.append(im)
    return frames


def strip(frames, frametime):
    w, h = frames[0].size
    im = Image.new('RGBA', (w, h * len(frames)))
    for i, fr in enumerate(frames):
        im.paste(fr, (0, i * h))
    meta = {'animation': {'frametime': frametime, 'interpolate': True}}
    return im, meta


def faces(tex, which='nsewud', uv_from=None):
    names = {'n': 'north', 's': 'south', 'e': 'east', 'w': 'west', 'u': 'up', 'd': 'down'}
    return {names[c]: {'texture': tex} for c in which}


def box(name, f, t, tex, which='nsewud', per_face=None):
    fc = faces(tex, which)
    if per_face:
        for k, v in per_face.items():
            fc[k] = {'texture': v}
    return {'name': name, 'from': f, 'to': t, 'faces': fc}


def shell_elements():
    els = [
        box('podstawa', [0, 0, 0], [16, 2.5, 16], '#trim', per_face={'up': '#metal', 'down': '#metal'}),
        box('pokrywa', [0, 13.5, 0], [16, 16, 16], '#metal', per_face={'up': '#top'}),
        # Rdzeń ma ściany 1.25 px w głąb: przy skali 1.2 to wciąż przed ścianą prawdziwego bloku.
        box('rdzen', [1.25, 2.5, 1.25], [14.75, 13.5, 14.75], '#core', which='nsew'),
    ]
    for x in (0, 13):
        for z in (0, 13):
            els.append(box('slup', [x, 2.5, z], [x + 3, 13.5, z + 3], '#pillar', which='nsew'))
    for y in (4.75, 8, 11.25):
        els.append(box('krata', [3, y, 0.5], [13, y + 1, 1.25], '#metal', which='nud'))
        els.append(box('krata', [3, y, 14.75], [13, y + 1, 15.5], '#metal', which='sud'))
        els.append(box('krata', [0.5, y, 3], [1.25, y + 1, 13], '#metal', which='wud'))
        els.append(box('krata', [14.75, y, 3], [15.5, y + 1, 13], '#metal', which='eud'))
    return els


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if isinstance(data, Image.Image):
        data.save(path)
    else:
        with open(path, 'w') as fh:
            json.dump(data, fh, indent=1)


def main():
    tex = os.path.join(OUT, 'assets/axon/textures/block/reactor')
    models = os.path.join(OUT, 'assets/axon/models/block/reactor')
    write(os.path.join(tex, 'metal.png'), metal_tex(1))
    write(os.path.join(tex, 'trim.png'), trim_tex())
    write(os.path.join(tex, 'pillar.png'), pillar_tex())
    for st in STATES:
        frametime = 2 if STATES[st][2] >= 1 else 3
        for kind, frames in (('core', energy_frames(st)), ('top', top_frames(st))):
            im, meta = strip(frames, frametime)
            write(os.path.join(tex, '%s_%s.png' % (kind, st)), im)
            if st != 'off':
                write(os.path.join(tex, '%s_%s.png.mcmeta' % (kind, st)), meta)
            else:
                write(os.path.join(tex, '%s_%s.png' % (kind, st)), frames[0])
        if st in CRYSTAL_CMD:
            im, meta = strip(crystal_frames(st), frametime)
            write(os.path.join(tex, 'crystal_%s.png' % st), im)
            write(os.path.join(tex, 'crystal_%s.png.mcmeta' % st), meta)

    write(os.path.join(models, 'shell.json'), {
        'parent': 'minecraft:block/block',
        'textures': {'particle': 'axon:block/reactor/metal', 'metal': 'axon:block/reactor/metal',
                     'trim': 'axon:block/reactor/trim', 'pillar': 'axon:block/reactor/pillar'},
        'elements': shell_elements(),
    })
    entries = []
    for st, cmd in CMD.items():
        write(os.path.join(models, st + '.json'), {
            'parent': 'axon:block/reactor/shell',
            'textures': {'core': 'axon:block/reactor/core_' + st, 'top': 'axon:block/reactor/top_' + st},
        })
        entries.append({'threshold': cmd, 'model': {'type': 'minecraft:model', 'model': 'axon:block/reactor/' + st}})
    for st, cmd in CRYSTAL_CMD.items():
        write(os.path.join(models, 'crystal_' + st + '.json'), {
            'textures': {'particle': 'axon:block/reactor/crystal_' + st, 'c': 'axon:block/reactor/crystal_' + st},
            'elements': [box('krysztal', [4.5, 4.5, 4.5], [11.5, 11.5, 11.5], '#c')],
        })
        entries.append({'threshold': cmd, 'model': {'type': 'minecraft:model', 'model': 'axon:block/reactor/crystal_' + st}})
    entries.sort(key=lambda e: e['threshold'])
    # Bez custom_model_data (albo z mniejszym) crying obsidian wygląda jak zwykle.
    write(os.path.join(OUT, 'assets/minecraft/items/crying_obsidian.json'), {'model': {
        'type': 'minecraft:range_dispatch', 'property': 'minecraft:custom_model_data', 'index': 0,
        'entries': entries,
        'fallback': {'type': 'minecraft:model', 'model': 'minecraft:block/crying_obsidian'},
    }})
    print('ok', OUT)


if __name__ == '__main__':
    main()
