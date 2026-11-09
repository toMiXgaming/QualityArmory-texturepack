"""Surowa Siarka: ikona przedmiotu i ruda siarki w głazach.

Na serwerze nie ma miedzi: ruda miedzi w głazach AxonOre (i w kopalniach AXON-Structure) daje
wyłącznie Surową Siarkę. Dlatego paczka podmienia tekstury rudy miedzi (zwykłej i głębowej)
na kamień z żółtymi kryształami siarki, a Surowa Siarka (żółty barwnik z custom_model_data
10001, tak ją tworzą AxonOre i AxonPlot) dostaje własną ikonę żółtej grudki.

Pliki:
- assets/minecraft/textures/block/copper_ore.png, deepslate_copper_ore.png – ruda siarki (16×16),
- assets/axon/textures/item/surowa_siarka.png – ikona (16×16),
- assets/axon/models/block/surowa_siarka.json, assets/axon/items/surowa_siarka.json – model i przedmiot
  axon:surowa_siarka (jak inne ikony AxonCore; gdyby plugin kiedyś ustawiał item_model),
- assets/minecraft/items/yellow_dye.json – custom_model_data 10001 -> grudka siarki, reszta zwykły barwnik
  (na 1.21–1.21.3 to samo jako overrides z legacy_1_21_0/yellow_dye.json, robi build_pack.legacy_models)."""
import io
import json
import random
from PIL import Image

CMD = 10001
MODEL = 'axon:block/surowa_siarka'

# Cytrynowa, lekko zielonkawa żółć siarki (złoto w vanilli jest pomarańczowe, więc rud się nie pomyli):
# od cienia (oliwkowa ochra) do światła (prawie biała).
S0 = (98, 92, 22)
S1 = (150, 142, 30)
S2 = (198, 190, 42)
S3 = (228, 224, 66)
S4 = (244, 242, 128)
S5 = (252, 252, 206)
K = (52, 48, 14)
DUST = (206, 200, 120)   # żółty nalot na kamieniu wokół kryształów


def _stone(seed, base, spread, layers=False):
    rnd = random.Random(seed)
    img = Image.new('RGBA', (16, 16))
    for y in range(16):
        band = (rnd.random() - 0.5) * 6 if layers else 0
        for x in range(16):
            v = base + band + rnd.choice((-spread, -spread // 2, 0, 0, 0, spread // 2, spread))
            if layers and (y % 4 == 3) and rnd.random() < 0.7:
                v -= spread
            g = max(0, min(255, int(v)))
            tint = (0, 0, 4) if layers else (0, 0, 0)
            img.putpixel((x, y), (g + tint[0], g + tint[1], min(255, g + tint[2]), 255))
    return img


# Skupiska kryształów: (x, y) lewego górnego rogu i kształt; '3'..'5' jasność, '1'/'2' cień, 'k' kontur.
CLUSTERS = [
    (1, 1, ['.k3.', 'k453', '3442', '.21.']),
    (9, 2, ['.k4..', 'k5431', '34421', '.221.']),
    (4, 7, ['..k3.', '.k453', 'k3442', '.3321', '..21.']),
    (11, 9, ['.k4.', 'k541', '.32.']),
    (1, 12, ['.k3..', 'k4431', '.221.']),
    (8, 13, ['k43', '.21']),
]
CH = {'1': S1, '2': S2, '3': S3, '4': S4, '5': S5, 'k': S0}


DUST_PX = [(0, 4), (4, 2), (5, 5), (8, 1), (13, 6), (14, 1), (3, 10), (9, 6), (10, 11), (15, 13),
           (6, 14), (12, 15), (0, 9)]


def _ore(stone):
    img = stone.copy()
    for x, y in DUST_PX:   # nalot: jaśniejsze, zażółcone piksele kamienia
        r, g, b, a = img.getpixel((x, y))
        img.putpixel((x, y), ((r + DUST[0]) // 2, (g + DUST[1]) // 2, (b + DUST[2]) // 2, 255))
    for cx, cy, rows in CLUSTERS:
        for dy, row in enumerate(rows):
            for dx, ch in enumerate(row):
                x, y = cx + dx, cy + dy
                if ch != '.' and 0 <= x < 16 and 0 <= y < 16:
                    img.putpixel((x, y), CH[ch] + (255,))
    return img


COPPER_ORE = _ore(_stone(7, 124, 14))
DEEPSLATE_COPPER_ORE = _ore(_stone(11, 74, 10, layers=True))

# Ikona: nieregularna grudka siarki z kryształowymi ściankami, światło z lewej góry.
_ICON = '''
................
................
.......kk.......
.....kk54k......
....k5544kk.....
...k554433kk....
..k5544433322k..
..k4454333222k..
.k44434332221k..
.k3443332211k...
..k33322211k....
..k2232221kk....
...kk2211k......
.....kkkk.......
................
................
'''
_IC = {'1': S0, '2': S1, '3': S2, '4': S3, '5': S4, 'k': K}


def _icon():
    rows = [r.strip() for r in _ICON.strip('\n').split('\n')]
    img = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch != '.':
                img.putpixel((x, y), _IC[ch] + (255,))
    for x, y in ((6, 4), (5, 5), (8, 3)):   # odblaski
        img.putpixel((x, y), S5 + (255,))
    for x, y in ((7, 8), (10, 7)):          # krawędzie kryształów
        img.putpixel((x, y), S4 + (255,))
    return img


ICON = _icon()

ITEM_DEF = {
    'model': {
        'type': 'minecraft:range_dispatch',
        'property': 'minecraft:custom_model_data',
        'index': 0,
        'entries': [{'threshold': CMD, 'model': {'type': 'minecraft:model', 'model': MODEL}}],
        'fallback': {'type': 'minecraft:model', 'model': 'minecraft:item/yellow_dye'},
    }
}


def _png(img):
    buf = io.BytesIO()
    img.save(buf, 'PNG', optimize=True)
    return buf.getvalue()


def _json(data):
    return (json.dumps(data, indent=2, ensure_ascii=False) + '\n').encode()


def pliki():
    """Wszystkie pliki Surowej Siarki do paczki (gen_axoncore.pliki() i dodaj_siarke.py)."""
    return {
        'assets/minecraft/textures/block/copper_ore.png': _png(COPPER_ORE),
        'assets/minecraft/textures/block/deepslate_copper_ore.png': _png(DEEPSLATE_COPPER_ORE),
        'assets/axon/textures/item/surowa_siarka.png': _png(ICON),
        'assets/axon/models/block/surowa_siarka.json': _json(
            {'parent': 'minecraft:item/generated', 'textures': {'layer0': 'axon:item/surowa_siarka'}}),
        'assets/axon/items/surowa_siarka.json': _json({'model': {'type': 'minecraft:model', 'model': MODEL}}),
        'assets/minecraft/items/yellow_dye.json': _json(ITEM_DEF),
        # 1.21–1.21.3 nie czytają items/: to samo jako overrides (build_pack.legacy_models robi identyczne pliki)
        'axon_1_21_0/assets/minecraft/models/item/yellow_dye.json': _json({
            'parent': 'minecraft:item/generated', 'textures': {'layer0': 'minecraft:item/yellow_dye'},
            'overrides': [{'predicate': {'custom_model_data': CMD}, 'model': MODEL}]}),
        'axon_1_21_0/assets/axon/models/item/surowa_siarka.json': _json({'parent': MODEL}),
    }
