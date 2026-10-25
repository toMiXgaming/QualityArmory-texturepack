#!/usr/bin/env python3
"""Podgląd aut i telewizora z gen_auta.py: preview_auta.py <plik.png> [obrót] (domyślnie 35)."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from render import load_model, Canvas, draw, ortho_view, fit_ortho, light_preview
from PIL import Image, ImageDraw
import numpy as np
from gen_auta import AUTA_I_TV
B = os.path.join(HERE, 'build')
W, H = 380, 300
out = sys.argv[1]
yaws = [float(sys.argv[2])] if len(sys.argv) > 2 else [35, 215]
sheet = Image.new('RGB', (W * len(AUTA_I_TV), H * len(yaws)), (38, 42, 50))
for j, yaw in enumerate(yaws):
    for i, n in enumerate(AUTA_I_TV):
        m, q = load_model(os.path.join(B, n + '.json'), lambda r: os.path.join(B, r.split('/')[-1] + '.png'))
        cv = Canvas(W, H, grad=((70, 76, 90), (34, 38, 46)))
        R = ortho_view(yaw, 24)
        lo, hi = ([-1, 2, -9], [17, 14, 25]) if n != 'telewizor' else ([0, 0, 0], [16, 19, 16])
        box = [dict(P=np.array([lo, hi, [lo[0], hi[1], hi[2]], [hi[0], lo[1], lo[2]], [hi[0], lo[1], hi[2]], [lo[0], hi[1], lo[2]]], float))]
        xf, pr, s = fit_ortho(box, R, W, H, margin=0.08)
        draw(cv, q, xf, pr, light_preview)
        im = cv.image(); ImageDraw.Draw(im).text((10, 8), n, fill=(235, 235, 235))
        sheet.paste(im, (i * W, j * H))
sheet.save(out)
