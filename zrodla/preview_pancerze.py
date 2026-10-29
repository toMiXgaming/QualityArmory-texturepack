#!/usr/bin/env python3
"""Podgląd zestawów z gen_pancerze.py na manekinie: preview_pancerze.py <plik.png> [zestaw ...]
Każdy zestaw: przód, tył i zbliżenie głowy. Obrót 205 = przód, 25 = tył."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from render import load_model, box_quads, Canvas, draw, ortho_view, fit_ortho, light_preview
from PIL import Image, ImageDraw
import numpy as np
from gen_pancerze import ZESTAWY, ELEMENTY, YSHIFT

B = os.path.join(HERE, 'build')
out = sys.argv[1]
sets = sys.argv[2:] or list(ZESTAWY)
W, H = 300, 420
SKIN = (176, 138, 108)
MAN = [([4, 20, 4], [12, 28, 12], SKIN), ([4, 8, 6], [12, 20, 10], (70, 74, 82)),
       ([0, 8, 6], [4, 20, 10], (70, 74, 82)), ([12, 8, 6], [16, 20, 10], (70, 74, 82)),
       ([4, -4, 6], [8, 8, 10], (60, 64, 72)), ([8, -4, 6], [12, 8, 10], (60, 64, 72))]
mannequin = []
for f, t, c in MAN:
    f = [f[0], f[1] - 0.0, f[2]]; t = [t[0], t[1], t[2]]
    mannequin += box_quads(f, t, c)
sheet = Image.new('RGB', (W * 3, H * len(sets)), (38, 42, 50))
for r, z in enumerate(sets):
    quads = []
    for e in [x for x in ELEMENTY if x in ZESTAWY[z]]:
        n = '%s_%s' % (z, e)
        m, q = load_model(os.path.join(B, n + '.json'), lambda ref: os.path.join(B, ref.split('/')[-1] + '.png'))
        quads += q
    for c, (yaw, zoom) in enumerate(((205, False), (25, False), (205, True))):
        cv = Canvas(W, H, grad=((70, 76, 90), (34, 38, 46)))
        R = ortho_view(yaw, 14 if zoom else 10)
        fit = [dict(P=np.array([[0, 19, 2], [16, 29.5, 14]] if zoom else [[0, -4, 2], [16, 29, 14]], float))]
        xf, pr, s = fit_ortho(fit, R, W, H, margin=0.08)
        draw(cv, mannequin + quads, xf, pr, light_preview)
        im = cv.image()
        ImageDraw.Draw(im).text((10, 8), z + (' zblizenie' if zoom else ' przod' if yaw == 205 else ' tyl'), fill=(235, 235, 235))
        sheet.paste(im, (c * W, r * H))
sheet.save(out)
