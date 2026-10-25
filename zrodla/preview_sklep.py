#!/usr/bin/env python3
"""Podgląd mebli z gen_sklep.py: preview_sklep.py <plik.png> <obrót> (25 = przód, 205 = tył)."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from render import load_model, Canvas, draw, ortho_view, fit_ortho, light_preview
from PIL import Image, ImageDraw
import numpy as np
from gen_sklep import SKLEP
B = os.path.join(HERE, 'build')
W, H = 300, 380
yaw = float(sys.argv[2]); out = sys.argv[1]
sheet = Image.new('RGB', (W * 5, H * 2), (38, 42, 50))
for i, n in enumerate(SKLEP):
    m, q = load_model(os.path.join(B, n + '.json'), lambda r: os.path.join(B, r.split('/')[-1] + '.png'))
    cv = Canvas(W, H, grad=((70, 76, 90), (34, 38, 46)))
    R = ortho_view(yaw, 22)
    box = [dict(P=np.array([[0, 0, 0], [16, 32, 16], [0, 32, 16], [16, 0, 0], [16,0,16],[0,0,0]], float))]
    xf, pr, s = fit_ortho(box, R, W, H, margin=0.06)
    draw(cv, q, xf, pr, light_preview)
    im = cv.image(); ImageDraw.Draw(im).text((10, 8), n, fill=(235, 235, 235))
    sheet.paste(im, ((i % 5) * W, (i // 5) * H))
sheet.save(out)
