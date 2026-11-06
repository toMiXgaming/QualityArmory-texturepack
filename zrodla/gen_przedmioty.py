#!/usr/bin/env python3
"""Przedmioty codzienne / wyposażenie QualityArmory z modelami `qualityarmory:misc/*`: granat, granat dymny,
zapalający i hukowy, koktajl Mołotowa, mina, apteczka, torba z amunicją i kanister paliwa.

Każdy model to kilkadziesiąt prostopadłościanów z własną teksturą 256x256 (silnik z gen_narzedzia.py:
jednolita gęstość pikseli, AO, wytarte krawędzie, lekka rdza). Układ display zostaje taki jak w oryginale
(czytany z zipa przy podmianie), więc pozycje w ręce, na ziemi i w ekwipunku się nie zmieniają.

python3 gen_przedmioty.py [nazwa ...]  ->  build/misc_<nazwa>.json|png"""
import json, math, os, sys
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_narzedzia as N
from gen_narzedzia import Tool, _c, _lerp, fbm, white, EXTRA_KINDS, MATS

OUT = N.OUT
NAMES = ['grenade', 'smokegrenade', 'incendarygrenade', 'flashbang', 'molotov', 'proxymine', 'medkit',
         'ammobag', 'fueltank']


def k_glass(m, G, side, el, seed):
    """Szkło butelki: ciemna zieleń, pionowy jasny refleks i delikatne bąbelki."""
    base = _c(m['base'])
    u = G[:, 0] + G[:, 2]
    streak = np.clip(1 - np.abs(((u * 1.7) % 4.0) - 1.1) * 3.5, 0, 1) * 0.45
    col = base[None] * (0.85 + 0.25 * fbm(G * np.array([1.6, 0.25, 1.6]), 2, seed)[:, None])
    return _lerp(col, _c(m.get('wear', (220, 245, 230))), streak)


EXTRA_KINDS['t_glass'] = k_glass
MATS.update({
    'glass': dict(kind='t_glass', base=(44, 104, 60), wear=(190, 235, 200), edge=0.2),
    'glass_b': dict(kind='t_glass', base=(120, 76, 30), wear=(240, 200, 130), edge=0.2),
    'paint_grey': dict(kind='t_metal', base=(112, 114, 116), wear=(190, 192, 192), edge=0.6, rust=0.06, paint=(150, 154, 152), chip=0.25),
    'paint_orange': dict(kind='t_metal', base=(112, 112, 116), wear=(190, 190, 190), edge=0.6, rust=0.2, paint=(196, 104, 38), chip=0.5),
    'paint_yellow': dict(kind='t_metal', base=(112, 112, 116), wear=(190, 190, 190), edge=0.6, rust=0.2, paint=(204, 170, 52), chip=0.5),
    'plastic': dict(kind='t_rubber', base=(206, 206, 198), wear=(236, 236, 230), edge=0.4),
    'plastic_g': dict(kind='t_rubber', base=(176, 176, 170), wear=(210, 210, 204), edge=0.4),
    'canvas': dict(kind='t_cloth', base=(84, 92, 62), wear=(120, 128, 92), edge=0.3, stain=(52, 56, 38)),
    'canvas_d': dict(kind='t_cloth', base=(60, 66, 46), wear=(96, 102, 74), edge=0.3, stain=(40, 44, 30)),
    'rag': dict(kind='t_cloth', base=(176, 164, 136), wear=(210, 200, 172), edge=0.3, stain=(110, 92, 60)),
    'redcross': dict(kind='t_rubber', base=(196, 40, 36), wear=(226, 80, 70), edge=0.3),
    'label': dict(kind='t_cloth', base=(196, 184, 150), wear=(226, 216, 182), edge=0.3, stain=(150, 130, 90)),
})


def octo(t, x, z, y0, y1, r, mat, tag='oct'):
    """Pionowy walec o przekroju ośmiokąta (trzy prostopadłościany różnej szerokości)."""
    a = r * 0.45
    t.box((x - r, y0, z - a), (x + r, y1, z + a), mat, tag)
    t.box((x - a, y0, z - r), (x + a, y1, z + r), mat, tag)
    c = r * 0.86
    t.box((x - c, y0 + 0.02, z - c), (x + c, y1 - 0.02, z + c), mat, tag)


def pin_ring(t, x, y, z, side=1):
    """Zawleczka: oczko z mosiężnych klocków."""
    t.box((x - 0.55, y, z - 0.1), (x + 0.55, y + 0.18, z + 0.1), 'brass', 'ring')
    t.box((x - 0.55, y + 0.9, z - 0.1), (x + 0.55, y + 1.08, z + 0.1), 'brass', 'ring')
    t.box((x - 0.55, y, z - 0.1), (x - 0.37, y + 1.08, z + 0.1), 'brass', 'ring')
    t.box((x + 0.37, y, z - 0.1), (x + 0.55, y + 1.08, z + 0.1), 'brass', 'ring')


def grenade():
    t = Tool('misc_grenade')
    x, z = 8.0, 12.2
    layers = [(1.0, 1.9, 1.25), (1.9, 3.1, 1.8), (3.1, 4.5, 2.0), (4.5, 5.5, 1.75), (5.5, 6.1, 1.2)]
    for i, (y0, y1, r) in enumerate(layers):
        octo(t, x, z, y0, y1, r, 'paint_olive', 'body')
    for y in (2.4, 3.8):                                      # rowki segmentów
        octo(t, x, z, y, y + 0.16, 2.0 + 0.08, 'steel_d', 'groove')
    t.box((x - 0.9, 6.1, z - 0.9), (x + 0.9, 6.7, z + 0.9), 'steel_d', 'neck')
    t.box((x - 0.6, 6.7, z - 0.6), (x + 0.6, 7.0, z + 0.6), 'steel', 'fuse')
    t.box((x + 1.2, 3.0, z - 0.45), (x + 1.55, 6.9, z + 0.45), 'steel', 'spoon')       # łyżka zapalnika
    t.box((x + 0.6, 6.6, z - 0.45), (x + 1.55, 6.95, z + 0.45), 'steel', 'spoon')
    t.box((x - 0.35, 1.0, z + 1.5), (x + 0.35, 5.0, z + 1.9), 'steel_d', 'rib')
    pin_ring(t, x - 0.3, 7.0, z)
    t.box((x - 0.12, 6.6, z - 0.12), (x + 0.12, 7.2, z + 0.12), 'brass', 'pin')
    t.box((x - 0.9, 0.7, z - 0.9), (x + 0.9, 1.0, z + 0.9), 'steel_d', 'foot')
    return t


def _canister(name, body, band):
    t = Tool(name)
    x, z = 8.0, 8.5
    octo(t, x, z, 0.3, 11.4, 3.2, body, 'body')
    octo(t, x, z, 0.0, 0.6, 3.0, 'steel_d', 'base')
    octo(t, x, z, 11.4, 12.3, 3.0, 'steel_d', 'cap')
    octo(t, x, z, 12.3, 13.1, 1.5, 'steel', 'neck')
    octo(t, x, z, 4.6, 7.4, 3.34, band, 'band')               # kolorowy pas oznaczenia
    octo(t, x, z, 4.6, 4.8, 3.4, 'black', 'bandline')
    octo(t, x, z, 7.2, 7.4, 3.4, 'black', 'bandline')
    for yy in (1.3, 9.9):                                    # tłoczone obręcze
        octo(t, x, z, yy, yy + 0.3, 3.3, 'steel_d', 'hoop')
    for k in range(4):                                       # otwory wylotowe w pokrywie
        t.box((x - 2.4 + k * 1.3, 11.6, z + 3.0), (x - 1.9 + k * 1.3, 12.0, z + 3.3), 'black', 'vent')
        t.box((x - 2.4 + k * 1.3, 11.6, z - 3.3), (x - 1.9 + k * 1.3, 12.0, z - 3.0), 'black', 'vent')
    t.box((x + 1.5, 6.0, z - 0.5), (x + 1.9, 13.2, z + 0.5), 'steel', 'spoon')
    t.box((x + 0.4, 12.9, z - 0.5), (x + 1.9, 13.3, z + 0.5), 'steel', 'spoon')
    pin_ring(t, x - 0.5, 13.1, z + 0.2)
    t.box((x - 0.12, 12.6, z + 0.08), (x + 0.12, 13.3, z + 0.32), 'brass', 'pin')
    t.box((x - 1.4, 5.0, z + 3.3), (x + 1.4, 6.6, z + 3.38), 'label', 'label')
    t.box((x - 1.0, 5.4, z - 3.38), (x + 1.0, 6.4, z - 3.3), 'label', 'label')
    return t


def smokegrenade():
    return _canister('misc_smokegrenade', 'paint_grey', 'paint_yellow')


def incendarygrenade():
    return _canister('misc_incendarygrenade', 'paint_grey', 'paint_red')


def flashbang():
    t = Tool('misc_flashbang')
    x, z = 8.0, 8.0
    octo(t, x, z, 0.3, 10.6, 2.0, 'paint_grey', 'body')
    octo(t, x, z, 0.0, 0.5, 1.9, 'black', 'base')
    octo(t, x, z, 10.6, 11.2, 1.9, 'steel_d', 'cap')
    octo(t, x, z, 11.2, 12.0, 0.95, 'steel', 'neck')
    octo(t, x, z, 5.4, 7.0, 2.1, 'paint_orange', 'band')
    for yy in (1.5, 3.0, 8.4, 9.4):                          # rzędy otworów (pękający rdzeń)
        for k in range(3):
            xx = x - 1.0 + k * 0.9
            t.box((xx, yy, z + 1.98), (xx + 0.4, yy + 0.4, z + 2.1), 'black', 'hole')
            t.box((xx, yy, z - 2.1), (xx + 0.4, yy + 0.4, z - 1.98), 'black', 'hole')
        for k in range(3):
            zz = z - 1.0 + k * 0.9
            t.box((x + 1.98, yy, zz), (x + 2.1, yy + 0.4, zz + 0.4), 'black', 'hole')
            t.box((x - 2.1, yy, zz), (x - 1.98, yy + 0.4, zz + 0.4), 'black', 'hole')
    t.box((x + 0.95, 5.0, z - 0.4), (x + 1.3, 11.6, z + 0.4), 'steel', 'spoon')
    t.box((x + 0.3, 11.2, z - 0.4), (x + 1.3, 11.6, z + 0.4), 'steel', 'spoon')
    pin_ring(t, x - 0.4, 11.8, z)
    t.box((x - 0.1, 11.3, z - 0.1), (x + 0.1, 12.0, z + 0.1), 'brass', 'pin')
    return t


def molotov():
    t = Tool('misc_molotov')
    x, z = 8.0, 8.6
    octo(t, x, z, 0.0, 0.5, 3.0, 'glass', 'basering')         # grube dno
    octo(t, x, z, 0.5, 8.0, 3.5, 'glass', 'body')
    octo(t, x, z, 1.0, 5.6, 3.3, 'glass_b', 'liquid')          # płyn (bursztynowy, widoczny przez szkło)
    octo(t, x, z, 8.0, 9.4, 3.0, 'glass', 'shoulder')
    octo(t, x, z, 9.4, 10.6, 2.2, 'glass', 'shoulder')
    octo(t, x, z, 10.6, 15.6, 1.3, 'glass', 'neck')
    octo(t, x, z, 15.6, 16.3, 1.6, 'glass', 'lip')
    t.box((x - 3.6, 3.0, z + 3.52), (x + 3.6, 6.4, z + 3.6), 'label', 'label')
    t.box((x - 3.6, 4.2, z + 3.58), (x + 3.6, 4.7, z + 3.66), 'redcross', 'stripe')
    t.box((x - 3.6, 3.0, z - 3.6), (x + 3.6, 6.4, z - 3.52), 'label', 'label')
    # szmata zatkana w szyjce i zwisająca
    t.box((x - 0.55, 14.0, z - 0.55), (x + 0.55, 18.0, z + 0.55), 'rag', 'rag')
    t.box((x - 0.8, 17.0, z - 0.8), (x + 0.8, 20.0, z + 0.8), 'rag', 'rag')
    t.box((x + 0.5, 15.4, z - 0.3), (x + 1.3, 19.0, z + 0.3), 'rag', 'rag')
    t.box((x - 1.35, 15.0, z - 0.5), (x - 0.6, 18.6, z + 0.5), 'rag', 'rag')
    t.box((x - 0.4, 19.6, z - 0.4), (x + 0.4, 21.0, z + 0.4), 'rag', 'ragtip')
    octo(t, x, z, 16.0, 16.5, 1.7, 'cord', 'tie')
    return t


def proxymine():
    t = Tool('misc_proxymine')
    x, z = 8.0, 8.5
    octo(t, x, z, 1.0, 2.4, 4.7, 'paint_olive', 'body')
    octo(t, x, z, 2.4, 3.1, 4.0, 'paint_olive', 'dome')
    octo(t, x, z, 3.1, 3.5, 2.6, 'steel_d', 'plate')
    octo(t, x, z, 1.0, 1.4, 4.85, 'steel_d', 'rim')
    octo(t, x, z, 2.0, 2.15, 4.8, 'black', 'seam')
    for dx, dz in ((3.0, 0), (-3.0, 0), (0, 3.0), (0, -3.0)):    # czujniki zbliżeniowe
        t.box((x + dx - 0.4, 2.9, z + dz - 0.4), (x + dx + 0.4, 3.35, z + dz + 0.4), 'black', 'sensor')
    t.box((x - 0.7, 3.5, z - 0.7), (x + 0.7, 3.8, z + 0.7), 'brass', 'cap')
    t.box((x - 0.2, 3.8, z - 0.2), (x + 0.2, 4.0, z + 0.2), 'redcross', 'led')
    for sx in (1, -1):                                           # kolce do wbicia w ziemię
        t.box((x + sx * 4.4 - 0.15, 0.2, z - 0.15), (x + sx * 4.4 + 0.15, 1.1, z + 0.15), 'steel_d', 'spike')
    for sz in (1, -1):
        t.box((x - 0.15, 0.2, z + sz * 4.5 - 0.15), (x + 0.15, 1.1, z + sz * 4.5 + 0.15), 'steel_d', 'spike')
    t.box((x - 1.6, 1.5, z + 4.55), (x + 1.6, 2.0, z + 4.68), 'label', 'label')
    return t


def medkit():
    t = Tool('misc_medkit')
    z0, z1 = 4.74, 11.26
    zc = (z0 + z1) / 2
    t.box((2.0, 7.0, z0), (14.0, 11.6, z1), 'plastic', 'case')
    t.box((2.0, 11.7, z0 + 0.02), (14.0, 14.2, z1 - 0.02), 'plastic', 'lid')
    t.box((1.95, 11.55, z0 + 0.1), (14.05, 11.75, z1 - 0.1), 'black', 'seam')
    for xc in (2.0, 13.0):                                       # narożniki
        t.box((xc - 0.05, 7.0, z0 - 0.05), (xc + 1.05, 14.2, z0 + 0.55), 'plastic_g', 'corner')
        t.box((xc - 0.05, 7.0, z1 - 0.55), (xc + 1.05, 14.2, z1 + 0.05), 'plastic_g', 'corner')
    t.box((5.4, 14.2, zc - 0.5), (10.6, 14.5, zc + 0.5), 'rubber', 'handle')
    t.box((5.0, 14.2, zc - 0.6), (5.5, 14.5, zc + 0.6), 'rubber', 'handle')
    t.box((10.5, 14.2, zc - 0.6), (11.0, 14.5, zc + 0.6), 'rubber', 'handle')
    for xl in (4.0, 11.0):                                       # zatrzaski
        t.box((xl, 10.9, z0 - 0.08), (xl + 1.0, 12.3, z0 + 0.1), 'steel', 'latch')
        t.box((xl, 10.9, z1 - 0.1), (xl + 1.0, 12.3, z1 + 0.08), 'steel', 'latch')
        t.box((xl + 0.3, 11.3, z0 - 0.14), (xl + 0.7, 11.7, z0 - 0.08), 'steel_d', 'latch')
        t.box((xl + 0.3, 11.3, z1 + 0.08), (xl + 0.7, 11.7, z1 + 0.14), 'steel_d', 'latch')
    for zz, sg in ((z0, -1), (z1, 1)):                           # czerwony krzyż na obu stronach
        a = zz - 0.1 if sg < 0 else zz
        b = zz if sg < 0 else zz + 0.1
        t.box((6.6, 8.4, a), (9.4, 13.4, b), 'redcross', 'cross')
        t.box((5.1, 9.9, a), (10.9, 11.9, b), 'redcross', 'cross')
    rust_hint = [(3.0, 7.4), (12.6, 7.4)]
    for xr, yr in rust_hint:
        t.box((xr, yr, z0 - 0.04), (xr + 0.5, yr + 0.35, z0), 'rust', 'rustp')
    return t


def ammobag():
    t = Tool('misc_ammobag')
    z0, z1 = 4.74, 11.26
    zc = (z0 + z1) / 2
    t.box((2.2, 7.0, z0 + 0.2), (13.8, 12.4, z1 - 0.2), 'canvas', 'bag')
    t.box((2.0, 7.2, z0 + 0.4), (14.0, 12.0, z1 - 0.4), 'canvas', 'bagside')
    t.box((2.3, 11.6, z0 + 0.1), (13.7, 14.2, z1 - 0.1), 'canvas_d', 'flap')
    t.box((2.5, 11.6, z0 + 0.02), (13.5, 11.8, z1 - 0.02), 'black', 'flapline')
    t.box((5.4, 14.2, zc - 0.5), (10.6, 14.5, zc + 0.5), 'canvas_d', 'handle')
    t.box((5.0, 13.6, zc - 0.5), (5.5, 14.5, zc + 0.5), 'canvas_d', 'handle')
    t.box((10.5, 13.6, zc - 0.5), (11.0, 14.5, zc + 0.5), 'canvas_d', 'handle')
    for xs in (4.2, 10.8):                                      # pasy zapinane na sprzączki
        t.box((xs, 7.0, z0 + 0.0), (xs + 1.0, 13.6, z0 + 0.2), 'leather', 'strap')
        t.box((xs, 7.0, z1 - 0.2), (xs + 1.0, 13.6, z1), 'leather', 'strap')
        t.box((xs - 0.05, 10.8, z0 - 0.08), (xs + 1.05, 11.8, z0 + 0.04), 'brass', 'buckle')
        t.box((xs - 0.05, 10.8, z1 - 0.04), (xs + 1.05, 11.8, z1 + 0.08), 'brass', 'buckle')
    t.box((4.8, 7.4, z0 - 0.05), (11.2, 9.8, z0 + 0.15), 'canvas_d', 'pocket')           # kieszeń z przodu
    t.box((4.8, 9.6, z0 - 0.08), (11.2, 9.9, z0 + 0.15), 'canvas', 'pocketflap')
    t.box((7.6, 9.0, z0 - 0.1), (8.4, 9.9, z0 - 0.04), 'brass', 'snap')
    t.box((5.4, 8.2, z1 - 0.1), (10.6, 11.2, z1 + 0.06), 'tape', 'patch')               # naszywka z tyłu
    t.box((2.0, 7.2, z0 + 0.3), (2.3, 11.8, z1 - 0.3), 'leather_d', 'edge')
    t.box((13.7, 7.2, z0 + 0.3), (14.0, 11.8, z1 - 0.3), 'leather_d', 'edge')
    return t


def fueltank():
    t = Tool('misc_fueltank')
    z0, z1 = 4.5, 11.5
    zc = 8.0
    t.box((1.5, 0.0, z0), (14.5, 14.0, z1), 'paint_olive', 'can')
    t.box((1.3, 0.4, z0 + 0.3), (14.7, 13.6, z1 - 0.3), 'paint_olive', 'canside')
    t.box((1.3, 0.0, z0 + 0.3), (14.7, 0.4, z1 - 0.3), 'steel_d', 'foot')
    for zz, sg in ((z0, -1), (z1, 1)):                           # tłoczone przekątne (X) na ściankach
        a = zz - 0.08 if sg < 0 else zz
        b = zz if sg < 0 else zz + 0.08
        for k in range(8):
            t.box((3.2 + k * 1.25, 3.0 + k * 1.1, a), (4.2 + k * 1.25, 4.0 + k * 1.1, b), 'steel_d', 'emb')
            t.box((3.2 + k * 1.25, 11.8 - k * 1.1, a), (4.2 + k * 1.25, 12.8 - k * 1.1, b), 'steel_d', 'emb')
        t.box((2.3, 1.2, a), (13.7, 1.5, b), 'steel_d', 'emb')
        t.box((2.3, 12.4, a), (13.7, 12.7, b), 'steel_d', 'emb')
    t.box((2.4, 14.0, z0 + 0.6), (7.0, 14.3, z1 - 0.6), 'paint_olive', 'top')
    t.box((7.0, 14.0, z0 + 0.6), (14.0, 14.2, z1 - 0.6), 'paint_olive', 'top')
    t.box((2.4, 14.3, 5.6), (7.4, 15.1, 6.1), 'paint_olive', 'handle')                   # rączka
    t.box((2.4, 14.3, 9.9), (7.4, 15.1, 10.4), 'paint_olive', 'handle')
    t.box((2.4, 15.0, 5.6), (7.4, 15.6, 10.4), 'paint_olive', 'handle')
    t.box((9.6, 14.2, zc - 1.1), (12.0, 15.1, zc + 1.1), 'steel', 'spout')               # wlew z korkiem
    t.box((9.9, 15.1, zc - 0.9), (11.7, 15.9, zc + 0.9), 'black', 'cap')
    t.box((9.6, 15.0, zc - 0.2), (12.0, 15.4, zc + 0.2), 'steel_d', 'chain')
    t.box((12.2, 14.2, zc - 0.5), (13.2, 14.9, zc + 0.5), 'steel', 'lug')
    t.box((5.6, 6.0, z0 - 0.06), (10.4, 8.4, z0), 'paint_yellow', 'label')
    t.box((6.0, 6.5, z0 - 0.1), (10.0, 6.8, z0 - 0.06), 'black', 'labelline')
    t.box((6.0, 7.5, z0 - 0.1), (10.0, 7.8, z0 - 0.06), 'black', 'labelline')
    for xr, yr, zr in ((3.0, 1.6, z1), (11.0, 11.0, z0), (2.4, 9.0, z0)):
        sg = 1 if zr == z1 else -1
        t.box((xr, yr, zr if sg > 0 else zr - 0.05), (xr + 1.2, yr + 1.0, zr + 0.05 if sg > 0 else zr), 'rust', 'rustp')
    return t


DISPLAY = json.load(open(os.path.join(N.HERE, 'display_misc.json')))
BUILD = {n: globals()[n] for n in NAMES}


def render(n):
    t = BUILD[n]()
    model, img, dens, nf = t.save('qualityarmory:axon/misc_' + n, DISPLAY[n], tool_rot=False)
    json.dump(model, open(os.path.join(OUT, 'misc_%s.json' % n), 'w'), indent=1)
    Image.fromarray(img, 'RGBA').save(os.path.join(OUT, 'misc_%s.png' % n))
    print(n, 'elements', len(model['elements']), 'faces', nf, 'density', dens, flush=True)


def main(want=()):
    os.makedirs(OUT, exist_ok=True)
    for n in NAMES:
        if not want or n in want:
            render(n)


if __name__ == '__main__':
    main(sys.argv[1:])
