#!/usr/bin/env python3
"""Zamyka wnętrze modeli zwykłych bloków (piec, beczka), żeby przez szpary nie było widać nieba.

Modele piec/beczka/stół nie wypełniają całej kostki (korpus ma 1 piksel luzu, beczka 0,9). Gra uznaje
te bloki za pełne i nie rysuje ścian sąsiadów, które do nich przylegają, więc patrząc w szparę widać
pustkę, czyli jasnoniebieski kolor nieba (180, 207, 255): jasne obwódki wokół pieca i kamiennego bloku.
Skrypt dodaje do każdego z tych modeli sześć płaszczyzn na granicach kostki 0–16, zwróconych DO WEWNĄTRZ
(widać je tylko od środka, z zewnątrz są tylnymi ścianami i się nie rysują), z najciemniejszym pikselem
tekstury modelu. Zwykły podgląd bloku z zewnątrz się nie zmienia, szpary robią się ciemne zamiast niebieskich.
Użycie: python3 wnetrze_bloku.py [zip ...]  (build_pack.py i buduj_1_21_11.py wołają to same)."""
import io
import json
import os
import shutil
import sys
import zipfile
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEFAULT = ['QualityArmory-21-axon.zip', 'QualityArmory-21-axon-1.21.11.zip', 'QualityArmory-21-axon-1.21.11-shadery.zip']
MODELS = ['barrel', 'barrel_open', 'furnace', 'furnace_on']
# stół rzemieślniczy ma nogi i półkę, więc ma być przez niego widać na wylot: płaszczyzn nie dodajemy, a stare zdejmujemy
OTWARTE = ['crafting_table']
NAME = 'axon_wnetrze'
# (ściana zwrócona do środka, from, to): płaszczyzna na granicy kostki
PLANES = [
    ('south', [0, 0, 0], [16, 16, 0]),
    ('north', [0, 0, 16], [16, 16, 16]),
    ('east', [0, 0, 0], [0, 16, 16]),
    ('west', [16, 0, 0], [16, 16, 16]),
    ('up', [0, 0, 0], [16, 0, 16]),
    ('down', [0, 16, 0], [16, 16, 16]),
]


def dark_uv(png, tex):
    im = Image.open(io.BytesIO(png)).convert('RGBA')
    if im.height > im.width:      # animowana tekstura: tylko pierwsza klatka
        im = im.crop((0, 0, im.width, im.width))
    best = min(((p[0] + p[1] + p[2], x, y) for y in range(im.height) for x in range(im.width)
                for p in [im.getpixel((x, y))] if p[3] == 255))
    x, y = best[1], best[2]
    return [(x + .25) * 16 / im.width, (y + .25) * 16 / im.height, (x + .75) * 16 / im.width, (y + .75) * 16 / im.height]


def patch(path):
    with zipfile.ZipFile(path) as z:
        files = {n: z.read(n) for n in z.namelist()}
        infos = {i.filename: i for i in z.infolist()}
    changed = 0
    for m in OTWARTE:
        n = 'assets/minecraft/models/block/%s.json' % m
        if n not in files:
            continue
        d = json.loads(files[n])
        d['elements'] = [e for e in d['elements'] if e.get('name') != NAME]
        new = json.dumps(d, indent=2).encode()
        if new != files[n]:
            files[n] = new
            changed += 1
    for m in MODELS:
        n = 'assets/minecraft/models/block/%s.json' % m
        if n not in files:
            continue
        d = json.loads(files[n])
        d['elements'] = [e for e in d['elements'] if e.get('name') != NAME]
        tex = next(v for k, v in d['textures'].items() if k != 'particle')
        ns, p = tex.split(':', 1)
        uv = dark_uv(files['assets/%s/textures/%s.png' % (ns, p)], tex)
        key = next(k for k, v in d['textures'].items() if v == tex and k != 'particle')
        d['elements'] += [{'name': NAME, 'from': f, 'to': t, 'faces': {face: {'uv': uv, 'texture': '#' + key}}}
                          for face, f, t in PLANES]
        new = json.dumps(d, indent=2).encode()
        if new != files[n]:
            files[n] = new
            changed += 1
    if not changed:
        return 0
    tmp = path + '.tmp'
    with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
        for n, data in files.items():
            zout.writestr(infos.get(n) or n, data)
    shutil.move(tmp, path)
    return changed


if __name__ == '__main__':
    for p in sys.argv[1:] or [os.path.join(ROOT, n) for n in DEFAULT]:
        print(os.path.basename(p), patch(p), 'modeli')
