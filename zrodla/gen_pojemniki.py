#!/usr/bin/env python3
"""Beczki i skrzynie AxonCore na silniku z gen_narzedzia.py: okrągłe beczki (stopniowany okrąg z pasów),
żebra, obręcze, wieko z korkami, rozbite wersje z łupem; skrzynie z deskami, okuciami i nitami.
Każdy model ma własną teksturę 256x256 (jednolita gęstość pikseli na ścianach, AO, wytarcie, rdza).

python3 gen_pojemniki.py [nazwa ...]  ->  build/poj_<nazwa>.json|png  (ścieżki w zipie: patrz pliki())"""
import json, math, os, sys
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_narzedzia as N
from gen_narzedzia import Tool, _c, _lerp, fbm, white, EXTRA_KINDS, MATS
from axoncore.stations import BLOCKLIKE
from gen_przedmioty import octo

OUT = N.OUT


def k_drum(m, G, side, el, seed):
    """Blacha beczki z farbą; na wieku koncentryczne tłoczenia, dwa korki i ślady po zaworze."""
    col = EXTRA_KINDS['t_metal'](m, G, side, el, seed)
    if side == 'T' and m.get('lid', True):
        r = np.hypot(G[:, 0], G[:, 2])
        ring = np.abs(((r - 4.6) % 1.9) - 0.95)
        col = col * (1 - 0.16 * (ring < 0.17)[:, None]) * (1 + 0.1 * ((ring > 0.17) & (ring < 0.34))[:, None])
        for cx, cz, rr in ((3.0, -2.2, 1.0), (-2.4, 2.8, 0.7)):         # korki
            d = np.hypot(G[:, 0] - cx, G[:, 2] - cz)
            col[d < rr] = _c((70, 72, 76)) * (0.9 + 0.2 * (d[d < rr] / rr))[:, None]
            col[(d >= rr) & (d < rr + 0.3)] *= 0.55
    return col


EXTRA_KINDS['t_drum'] = k_drum
_P = dict(kind='t_drum', base=(112, 112, 116), wear=(190, 190, 190), edge=0.55)
MATS.update({
    'drum_blue': dict(_P, rust=0.07, paint=(52, 92, 122), chip=0.3),
    'drum_red': dict(_P, rust=0.07, paint=(158, 46, 38), chip=0.3),
    'drum_rust': dict(_P, rust=0.3, paint=(150, 84, 44), chip=0.6),
    'drum_band': dict(_P, rust=0.05, paint=(206, 170, 52), chip=0.25, lid=False),
    'drum_hoop': dict(kind='t_metal', base=(100, 104, 110), wear=(184, 188, 194), edge=0.7, rust=0.12),
    'drum_in': dict(kind='t_metal', base=(40, 34, 30), wear=(90, 80, 70), edge=0.4, rust=0.4, var=0.15),
    'oil': dict(kind='t_rubber', base=(20, 16, 12), wear=(60, 50, 40), edge=0.2),
})


def disc(t, cx, cz, y0, y1, R, mat, tag='disc', bands=None, shift=0.0):
    """Walec o przekroju stopniowanego okręgu: pasy wzdłuż z o różnej szerokości (bez nakładania).

    shift (0..1 kroku) przesuwa podział na pasy: warstwy leżące jedna na drugiej (korpus, żebra, pas)
    dostają różny shift, żeby ich krawędzie nie wypadały w tej samej płaszczyźnie i nie migały (z-fighting)."""
    n = bands or max(6, int(R * 1.6))
    h = 2 * R / n
    cuts = [-R + (i + shift) * h for i in range(n)] if shift else [-R + i * h for i in range(n)]
    cuts = [-R] + [c for c in cuts if c > -R + 1e-6] + [R]
    for z0, z1 in zip(cuts, cuts[1:]):
        zm = (z0 + z1) / 2
        hw = math.sqrt(max(R * R - zm * zm, 0.04))
        t.box((cx - hw, y0, cz + z0), (cx + hw, y1, cz + z1), mat, tag)


def beczka(mat='drum_blue', band=False, open_=False, stage=0):
    t = Tool('poj_beczka')
    x, z = 8.0, 8.0
    disc(t, x, z, 0.0, 0.7, 7.1, 'drum_hoop', 'chime')                   # dolny kołnierz
    disc(t, x, z, 0.7, 15.3, 6.6, mat, 'body')
    disc(t, x, z, 15.3, 15.9, 7.0, 'drum_hoop', 'chime')                  # górny kołnierz z wieczkiem
    if open_:
        disc(t, x, z, 15.9, 16.0, 6.2, 'drum_in', 'inner')
        disc(t, x, z, 15.0, 15.3, 6.2, 'oil', 'oil')
    else:
        disc(t, x, z, 15.9, 16.0, 6.3, mat, 'lid')
    for y in (4.2, 7.6, 11.0):                                           # żebra tłoczone w korpusie
        disc(t, x, z, y, y + 0.9, 6.95, 'drum_hoop', 'rib', shift=0.5)
    if band:
        disc(t, x, z, 5.6, 7.4, 6.88, 'drum_band', 'band', shift=0.4)
        disc(t, x, z, 7.4, 8.0, 6.64, 'black', 'bandline', shift=0.7)
    if stage:
        uszkodzenia(t, x, z, stage)
    return t


def uszkodzenia(t, x, z, stage):
    """Etapy zniszczenia beczki (1: <=66% HP, 2: <=33% HP): plamy rdzy i odprysków, wgniecenia i dziury z ciemnym wnętrzem,
    na etapie 2 jeszcze rozerwany szew, krzywe wieko i kałuża oleju. Elementy leżą tuż nad powierzchnią korpusu (r=6,6)."""
    # (kierunek, y0, y1, szerokość wzdłuż obwodu, materiał)
    plamy = [('E', 3.0, 5.2, 3.4, 'rust'), ('S', 9.0, 11.6, 3.0, 'rust'), ('W', 5.5, 7.0, 2.6, 'rust'), ('N', 1.6, 3.4, 3.2, 'rust')]
    dziury = [('E', 8.0, 9.4, 1.6), ('S', 4.4, 5.4, 1.2)]
    if stage >= 2:
        plamy += [('N', 8.4, 11.8, 3.8, 'rust'), ('W', 10.2, 13.0, 3.2, 'rust'), ('E', 11.2, 13.4, 2.8, 'rust'), ('S', 1.2, 3.0, 2.6, 'rust')]
        dziury += [('W', 8.0, 10.0, 2.2), ('N', 5.0, 7.2, 2.0), ('E', 2.0, 3.2, 1.4)]
    off = 6.62
    def na(d, y0, y1, w, mat, tag, depth):
        h = w / 2
        if d == 'E':
            t.box((x + off - depth, y0, z - h), (x + off + 0.12, y1, z + h), mat, tag)
        elif d == 'W':
            t.box((x - off - 0.12, y0, z - h), (x - off + depth, y1, z + h), mat, tag)
        elif d == 'S':
            t.box((x - h, y0, z + off - depth), (x + h, y1, z + off + 0.12), mat, tag)
        else:
            t.box((x - h, y0, z - off - 0.12), (x + h, y1, z - off + depth), mat, tag)
    for d, y0, y1, w, mat in plamy:
        na(d, y0, y1, w, mat, 'rustpatch', 0.0)
    for d, y0, y1, w in dziury:                                          # wgniecenie z dziurą po uderzeniu
        na(d, y0 - 0.4, y1 + 0.4, w + 0.8, 'drum_hoop', 'dent', 0.0)
        na(d, y0, y1, w, 'drum_in', 'hole', 0.0)
    if stage >= 2:
        t.box((x - 0.5, 0.7, z + 6.55), (x + 0.5, 15.3, z + 6.75), 'drum_in', 'seam')      # rozerwany szew
        t.box((x - 7.4, 0.0, z - 7.4), (x - 5.2, 0.1, z - 5.0), 'oil', 'puddle')            # wyciek oleju
        t.box((x + 4.2, 0.0, z - 6.2), (x + 6.6, 0.1, z - 4.4), 'oil', 'puddle')


def rozbita(mat='drum_blue', band=False):
    t = Tool('poj_beczka_rozbita')
    x, z = 8.0, 8.0
    disc(t, x, z, 0.0, 0.7, 7.1, 'drum_hoop', 'chime')
    disc(t, x, z, 0.7, 7.0, 6.6, mat, 'body')
    disc(t, x, z, 4.2, 5.1, 6.95, 'drum_hoop', 'rib', shift=0.5)
    if band:
        disc(t, x, z, 2.2, 3.6, 6.88, 'drum_band', 'band', shift=0.4)
    disc(t, x, z, 6.4, 6.6, 6.0, 'drum_in', 'inner')
    # poszarpany górny brzeg: pionowe płaty blachy o różnej wysokości
    n = 14
    for i in range(n):
        a0 = 2 * math.pi * i / n
        a1 = 2 * math.pi * (i + 1) / n
        am = (a0 + a1) / 2
        hgt = [3.5, 1.2, 4.6, 2.2, 5.5, 1.0, 3.0, 4.2, 1.6, 5.0, 2.6, 0.8, 3.8, 2.0][i]
        if hgt < 1.0:
            continue
        cx, cz = x + math.cos(am) * 6.32, z + math.sin(am) * 6.32
        hw = 0.5 + 1.25 * abs(math.sin(am)) * 0.0
        sw, sd = (0.6, 1.5) if abs(math.cos(am)) > 0.7 else ((1.5, 0.6) if abs(math.sin(am)) > 0.7 else (1.1, 1.1))
        t.box((cx - sw / 2, 7.0, cz - sd / 2), (cx + sw / 2, 7.0 + hgt, cz + sd / 2), mat, 'tooth')
    # łup: złom, puszka, szmata
    t.box((5.0, 6.4, 5.0), (8.4, 8.6, 8.2), 'rust', 'loot')
    t.box((8.8, 6.4, 7.2), (11.2, 9.4, 9.6), 'steel_l', 'loot')
    t.box((9.0, 9.4, 7.4), (11.0, 9.7, 9.4), 'steel', 'loot')
    t.box((5.4, 6.4, 8.8), (9.0, 7.6, 11.4), 'cloth', 'loot')
    t.box((6.0, 7.6, 9.4), (8.0, 8.1, 10.8), 'cloth', 'loot')
    # wieko leżące obok
    disc(t, -5.6, 8.0, 0.0, 0.7, 5.4, mat, 'lid', bands=8)
    disc(t, -5.6, 8.0, 0.7, 0.85, 5.9, 'drum_hoop', 'lidrim', bands=8)
    return t


VAR = {'beczka': ('drum_blue', False), 'beczka_paliwa': ('drum_red', True), 'beczka_rdza': ('drum_rust', False)}
CONTAINERS = {}
for _n, (_m, _b) in VAR.items():
    CONTAINERS[_n] = (lambda m=_m, b=_b: beczka(m, b))
    CONTAINERS[_n + '_rozbita'.replace('beczka', '')] = None
CONTAINERS = {k: v for k, v in CONTAINERS.items() if v}
CONTAINERS['beczka_rozbita'] = lambda: rozbita('drum_blue', False)
CONTAINERS['beczka_paliwa_rozbita'] = lambda: rozbita('drum_red', True)
CONTAINERS['beczka_rdza_rozbita'] = lambda: rozbita('drum_rust', False)
for _n, (_m, _b) in VAR.items():                                         # etapy zniszczenia: plugin podmienia model wraz ze spadkiem HP
    for _st in (1, 2):
        CONTAINERS['%s_uszkodzona_%d' % (_n, _st)] = (lambda m=_m, b=_b, st=_st: beczka(m, b, False, st))
CONTAINERS['beczka_otwarta'] = lambda: beczka('drum_blue', False, True)



# ---------------------------------------------------------------- skrzynie
MATS.update({
    'w_plank': dict(kind='t_wood', light=(176, 134, 86), dark=(126, 90, 56), wear=(206, 168, 118), edge=0.35, axis='u'),
    'w_plank_z': dict(kind='t_wood', light=(176, 134, 86), dark=(126, 90, 56), wear=(206, 168, 118), edge=0.35, axis='w'),
    'w_post': dict(kind='t_wood', light=(120, 86, 54), dark=(78, 54, 34), wear=(160, 124, 88), edge=0.35),
    'w_gap': dict(kind='t_wood', light=(70, 50, 34), dark=(48, 34, 24), wear=(100, 76, 54), edge=0.2, axis='u'),
    'cardboard': dict(kind='t_cloth', base=(176, 140, 92), wear=(206, 172, 124), edge=0.3, stain=(120, 92, 58)),
    'cardboard_d': dict(kind='t_cloth', base=(150, 116, 74), wear=(190, 154, 108), edge=0.3, stain=(104, 78, 48)),
    'screen': dict(kind='t_rubber', base=(60, 210, 100), wear=(150, 255, 170), edge=0.2),
    'can_red': dict(kind='t_metal', base=(112, 112, 116), wear=(190, 190, 190), edge=0.5, rust=0.05, paint=(168, 44, 36), chip=0.3),
    'can_yel': dict(kind='t_metal', base=(112, 112, 116), wear=(190, 190, 190), edge=0.5, rust=0.05, paint=(212, 176, 56), chip=0.3),
    'enamel': dict(kind='t_metal', base=(150, 150, 146), wear=(200, 200, 196), edge=0.5, rust=0.03, paint=(226, 226, 220), chip=0.1),
    'paint_red_c': dict(kind='t_metal', base=(112, 112, 116), wear=(190, 190, 190), edge=0.5, rust=0.04, paint=(162, 42, 34), chip=0.2),
    'olive_c': dict(kind='t_metal', base=(82, 90, 60), wear=(150, 150, 140), edge=0.5, rust=0.03, paint=(78, 92, 54), chip=0.15),
    'black_c': dict(kind='t_metal', base=(30, 30, 34), wear=(110, 112, 118), edge=0.7, rust=0.02, paint=(34, 34, 38), chip=0.12),
})

FONT = {
    'P': ['###', '#.#', '###', '#..', '#..'], 'W': ['#.#', '#.#', '#.#', '###', '#.#'],
    '7': ['###', '..#', '.#.', '.#.', '.#.'], '6': ['###', '#..', '###', '#.#', '###'],
    '2': ['###', '..#', '###', '#..', '###'], '.': ['...', '...', '...', '...', '.#.'], ' ': ['...'] * 5,
}


def stencil(t, s, x, y, z, mat='paint_yellow', px=0.55, sign=1):
    """Napis z klocków na ścianie z (sign=1: przód +z). x, y: lewy górny róg."""
    cx = x
    for ch in s:
        g = FONT[ch]
        for j, row in enumerate(g):
            for i, c in enumerate(row):
                if c == '#':
                    t.box((cx + i * px, y - (j + 1) * px, z), (cx + (i + 1) * px, y - j * px, z + sign * 0.08), mat, 'txt')
        cx += 4 * px


def skrzynia_drewniana():
    t = Tool('poj_skrzynia_drewniana')
    t.box((1.2, 0.3, 1.2), (14.8, 12.0, 14.8), 'w_gap', 'core')
    for x, z in ((0.5, 0.5), (14.1, 0.5), (0.5, 14.1), (14.1, 14.1)):
        t.box((x, 0.0, z), (x + 1.4, 12.4, z + 1.4), 'w_post', 'post')
    for i in range(4):                                       # deski ścian (z lekkimi szparami)
        y0 = 0.4 + i * 2.95
        y1 = y0 + 2.75
        t.box((2.0, y0, 14.8), (14.0, y1, 15.4), 'w_plank', 'plankF')
        t.box((2.0, y0, 0.6), (14.0, y1, 1.2), 'w_plank', 'plankK')
        t.box((14.8, y0, 2.0), (15.4, y1, 14.0), 'w_plank_z', 'plankR')
        t.box((0.6, y0, 2.0), (1.2, y1, 14.0), 'w_plank_z', 'plankL')
    for k in range(3):                                       # wieko: trzy deski + dwie poprzeczki
        z0 = 0.25 + k * 5.2
        t.box((0.4, 12.4, z0), (15.6, 13.4, z0 + 5.05), 'w_plank', 'lid')
    for x in (1.6, 12.6):
        t.box((x, 13.4, 0.5), (x + 1.8, 13.9, 15.5), 'w_post', 'batten')
    for x, z in ((0.3, 0.3), (14.7, 0.3), (0.3, 14.7), (14.7, 14.7)):     # stalowe narożniki
        t.box((x, 11.0, z), (x + 1.0, 13.9, z + 1.0), 'steel_d', 'corner')
        t.box((x, 0.0, z), (x + 1.0, 1.4, z + 1.0), 'steel_d', 'corner')
    t.box((2.0, 10.8, 15.45), (14.0, 11.5, 15.7), 'steel_d', 'strapF')
    t.box((2.0, 0.9, 15.45), (14.0, 1.6, 15.7), 'steel_d', 'strapF')
    t.box((6.6, 8.4, 15.45), (9.4, 11.6, 15.9), 'brass', 'lock')
    t.box((7.7, 9.0, 15.9), (8.3, 10.2, 15.98), 'black', 'keyhole')
    for xx in (2.6, 13.0):
        for yy in (2.0, 5.0, 8.0):
            t.box((xx, yy, 15.4), (xx + 0.35, yy + 0.35, 15.55), 'steel_d', 'nail')
    return t


def skrzynka_narzedziowa():
    t = Tool('poj_skrzynka_narzedziowa')
    t.box((1.75, 0.0, 3.75), (14.25, 6.8, 12.5), 'paint_red_c', 'body')
    t.box((1.55, 6.6, 3.55), (14.45, 8.4, 12.7), 'paint_red_c', 'lid')
    t.box((1.6, 6.5, 3.5), (14.4, 6.9, 12.75), 'steel_d', 'seam')
    t.box((1.5, 0.0, 3.5), (14.5, 0.5, 12.75), 'steel_d', 'foot')
    for x in (4.4, 11.0):                                  # uchwyt
        t.box((x, 8.4, 7.4), (x + 0.6, 10.4, 8.4), 'steel', 'post')
    t.box((4.4, 10.0, 7.2), (11.6, 10.5, 8.6), 'rubber', 'handle')
    for x in (4.0, 10.8):                                  # zatrzaski
        t.box((x, 5.6, 12.7), (x + 1.4, 8.0, 13.0), 'steel', 'latch')
        t.box((x + 0.45, 6.3, 13.0), (x + 0.95, 6.9, 13.1), 'steel_d', 'latchpin')
    for x in (2.2, 13.0):
        t.box((x, 0.5, 3.4), (x + 0.6, 6.5, 12.9), 'steel_d', 'rib')
    for x, y in ((2.3, 6.0), (13.0, 6.0), (2.3, 1.0), (13.0, 1.0)):
        t.box((x, y, 12.75), (x + 0.4, y + 0.4, 12.9), 'steel_l', 'rivet')
    t.box((5.5, 3.0, 12.75), (10.5, 4.6, 12.82), 'label', 'label')
    t.box((5.9, 3.3, 12.82), (10.1, 3.5, 12.88), 'black', 'labelline')
    return t


def szafka_medyczna():
    t = Tool('poj_szafka_medyczna')
    t.box((0.5, 2.0, 0.0), (15.5, 16.0, 1.0), 'enamel', 'back')
    t.box((1.0, 2.5, 1.0), (15.0, 15.5, 5.6), 'enamel', 'body')
    t.box((0.8, 2.3, 5.6), (15.2, 15.7, 6.5), 'enamel', 'door')
    t.box((0.7, 2.2, 5.5), (15.3, 2.6, 6.6), 'steel_l', 'frame')
    t.box((0.7, 15.4, 5.5), (15.3, 15.8, 6.6), 'steel_l', 'frame')
    t.box((7.7, 2.6, 6.45), (8.3, 15.4, 6.6), 'steel_d', 'door_seam')
    t.box((5.4, 7.4, 6.5), (10.6, 10.6, 6.6), 'redcross', 'cross')
    t.box((7.0, 6.0, 6.5), (9.0, 12.0, 6.6), 'redcross', 'cross')
    t.box((6.4, 7.4, 6.5), (9.6, 10.6, 6.6), 'redcross', 'cross')
    t.box((9.0, 4.4, 6.5), (9.4, 6.0, 7.0), 'steel', 'handle')     # klamka
    t.box((6.6, 4.4, 6.5), (7.0, 6.0, 7.0), 'steel', 'handle')
    t.box((6.6, 4.4, 7.0), (9.4, 4.8, 7.4), 'steel', 'handle')
    for y in (4.0, 13.0):                                         # zawiasy
        t.box((0.4, y, 6.0), (1.0, y + 1.6, 6.8), 'steel_d', 'hinge')
        t.box((15.0, y, 6.0), (15.6, y + 1.6, 6.8), 'steel_d', 'hinge')
    t.box((7.4, 13.2, 6.5), (8.6, 13.9, 6.7), 'steel_d', 'lock')
    for x in (3.0, 12.4):
        t.box((x, 14.2, 6.5), (x + 0.5, 14.7, 6.62), 'steel_l', 'rivet')
    return t


def skrzynka_jedzenie():
    t = Tool('poj_skrzynka_jedzenie')
    t.box((0.7, 0.0, 2.0), (15.3, 8.2, 14.0), 'cardboard', 'box')
    t.box((0.6, 3.6, 1.9), (15.4, 5.2, 14.1), 'tape_g', 'tape')
    t.box((0.9, 0.0, 2.2), (15.1, 0.4, 13.8), 'cardboard_d', 'bottom')
    t.box((0.7, 8.0, 2.0), (15.3, 8.2, 14.0), 'cardboard_d', 'rim')
    t.box((0.7, 8.2, 2.0), (2.0, 11.6, 2.4), 'cardboard', 'flapK')        # otwarte klapy
    t.box((14.0, 8.2, 2.0), (15.3, 11.6, 2.4), 'cardboard', 'flapK')
    t.box((0.7, 8.2, 13.6), (15.3, 12.5, 14.0), 'cardboard', 'flapF')
    t.box((0.7, 8.2, 2.4), (1.1, 12.0, 13.6), 'cardboard', 'flapL')
    t.box((14.9, 8.2, 2.4), (15.3, 11.0, 13.6), 'cardboard', 'flapR')
    mats = ('can_red', 'can_yel', 'steel_l', 'can_yel', 'can_red', 'steel_l')
    k = 0
    for ix in range(3):
        for iz in range(2):
            cx, cz = 3.8 + ix * 4.2, 5.4 + iz * 4.4
            octo(t, cx, cz, 8.2, 11.4, 1.7, mats[k % 6], 'can')
            octo(t, cx, cz, 11.4, 11.6, 1.5, 'steel', 'lid')
            octo(t, cx, cz, 9.0, 10.2, 1.78, 'label', 'canlabel')
            k += 1
    stencil(t, 'WP 62', 3.2, 3.2, 14.0, 'black', px=0.55)
    t.box((12.0, 5.8, 14.0), (14.6, 7.6, 14.06), 'label', 'sticker')
    return t


def skrzynia_wojskowa():
    t = Tool('poj_skrzynia_wojskowa')
    x0, x1 = -15.4, 17.4
    t.box((x0, 0.0, 1.75), (x1, 8.4, 14.5), 'olive_c', 'body')
    t.box((x0 - 0.15, 8.4, 1.6), (x1 + 0.15, 10.5, 14.65), 'olive_c', 'lid')
    t.box((x0 - 0.2, 8.2, 1.55), (x1 + 0.2, 8.6, 14.7), 'black', 'seam')
    for x in (-8.5, 9.9):                                          # czarne pasy
        t.box((x, 0.0, 1.6), (x + 1.8, 10.6, 14.7), 'black_c', 'strap')
    for x in (x0 - 0.2, x1 - 0.5):                                  # okucia końcowe
        t.box((x, 0.0, 1.6), (x + 0.7, 10.6, 14.7), 'steel_d', 'endcap')
    for x in (-3.0, 4.2):                                           # zatrzaski
        t.box((x, 6.8, 14.55), (x + 1.8, 9.2, 14.85), 'steel', 'latch')
        t.box((x + 0.6, 7.6, 14.85), (x + 1.2, 8.2, 14.95), 'steel_d', 'latchpin')
    for x in (x0, x1):                                              # uchwyty-pętle po bokach
        t.box((x - 0.4, 4.0, 6.0), (x + 0.4, 6.5, 10.2), 'cord_d', 'loop')
    stencil(t, 'WP', -13.4, 6.6, 14.5, 'paint_yellow', px=0.6)
    stencil(t, '7.62', 8.6 + 0.6, 6.6, 14.5, 'paint_yellow', px=0.55)
    t.box((-6.4, 1.8, 14.5), (6.8, 2.4, 14.56), 'paint_yellow', 'stripe')
    for x in (x0 + 1.0, x1 - 2.0):
        t.box((x, 8.8, 14.6), (x + 0.5, 9.3, 14.72), 'steel_l', 'rivet')
    return t


def skrzynia_elitarna():
    t = Tool('poj_skrzynia_elitarna')
    t.box((0.0, 0.0, 1.0), (16.0, 8.8, 15.5), 'black_c', 'body')
    t.box((-0.25, 8.8, 0.75), (16.25, 11.2, 15.75), 'black_c', 'lid')
    t.box((-0.3, 8.6, 0.7), (16.3, 9.0, 15.8), 'steel_d', 'seam')
    t.box((-0.1, 0.0, 0.9), (0.9, 8.8, 15.6), 'steel_d', 'rail')
    t.box((15.1, 0.0, 0.9), (16.1, 8.8, 15.6), 'steel_d', 'rail')
    for k in range(5):                                              # kratka wentylacyjna na wieku
        t.box((3.0, 11.2, 3.0 + k * 2.2), (13.0, 11.4, 4.0 + k * 2.2), 'steel_d', 'vent')
    for x in (2.0, 12.4):                                           # zatrzaski
        t.box((x, 5.6, 15.5), (x + 1.6, 9.4, 15.85), 'steel', 'latch')
    t.box((5.6, 3.0, 15.5), (10.4, 7.6, 15.95), 'steel_d', 'panel')
    t.box((6.0, 5.8, 15.95), (10.0, 7.2, 16.05), 'screen', 'screen')
    for r in range(3):                                              # klawiatura 3x2
        for c in range(3):
            t.box((6.4 + c * 1.2, 3.5 + r * 0.7, 15.95), (7.0 + c * 1.2, 3.95 + r * 0.7, 16.05), 'steel_l', 'key')
    for k in range(7):                                              # pasy ostrzegawcze
        t.box((0.8 + k * 2.2, 0.4, 15.5), (1.9 + k * 2.2, 2.0, 15.6), 'paint_yellow' if k % 2 == 0 else 'black', 'hazard')
    for x, y in ((0.6, 10.6), (14.8, 10.6), (0.6, 0.6), (14.8, 0.6)):
        t.box((x, y, 15.6), (x + 0.6, y + 0.6, 15.75), 'steel_l', 'bolt')
    return t


CONTAINERS.update({n: globals()[n] for n in ('skrzynia_drewniana', 'skrzynka_narzedziowa', 'szafka_medyczna',
                                              'skrzynka_jedzenie', 'skrzynia_wojskowa', 'skrzynia_elitarna')})


VANILLA_BLOCKS = {'barrel': 'beczka', 'barrel_open': 'beczka_otwarta'}


def render(n):
    t = CONTAINERS[n]()
    model, img, dens, nf = t.save('axon:item/poj_' + n, BLOCKLIKE, tool_rot=False)
    model['gui_light'] = 'side'
    json.dump(model, open(os.path.join(OUT, 'poj_%s.json' % n), 'w'), indent=1)
    Image.fromarray(img, 'RGBA').save(os.path.join(OUT, 'poj_%s.png' % n))
    print(n, 'elements', len(model['elements']), 'faces', nf, 'density', dens, flush=True)


def pliki(src=None):
    """Ścieżka w zipie -> bajty (modele beczek i skrzyń axon:<nazwa>, beczka z Minecrafta, tekstury poj_*)."""
    src = src or OUT
    f = {}
    for n in CONTAINERS:
        mj = open(os.path.join(src, 'poj_%s.json' % n), 'rb').read()
        f['assets/axon/models/block/%s.json' % n] = mj
        f['assets/axon/textures/item/poj_%s.png' % n] = open(os.path.join(src, 'poj_%s.png' % n), 'rb').read()
    for vanilla, n in VANILLA_BLOCKS.items():
        m = json.loads(f['assets/axon/models/block/%s.json' % n])
        m.pop('display', None)
        m.pop('gui_light', None)
        vt = 'axon:block/vanilla/poj_' + n               # od 1.21.9 model bloku może używać tylko atlasu block/
        m['textures'] = {'0': vt, 'particle': vt}
        f['assets/axon/textures/block/vanilla/poj_%s.png' % n] = f['assets/axon/textures/item/poj_%s.png' % n]
        f['assets/minecraft/models/block/%s.json' % vanilla] = (json.dumps({'parent': 'minecraft:block/block', **m}, indent=1) + '\n').encode()
    return f


def main(want=()):
    os.makedirs(OUT, exist_ok=True)
    for n in CONTAINERS:
        if not want or n in want:
            render(n)


if __name__ == '__main__':
    main(sys.argv[1:])
