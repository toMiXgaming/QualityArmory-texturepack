#!/usr/bin/env python3
"""Podgląd amunicji z gen_ammo.py: preview_ammo.py <plik.png>
Górny rząd: modele z bliska, dolny rząd: ikony w ekwipunku (gui)."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from render import load_model, Canvas, draw, ortho_view, fit_ortho, gui_view, light_preview, light_flat
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from gen_ammo import NAZWY

OPIS = {'ammo9mm': '9 mm', 'ammo556': '5.56 mm', 'ammo762': '7.62 mm', 'ammoshotgun': 'Śrut',
        'ammorpg': 'Rakieta RPG', 'ammomusketball': 'Kula do muszkietu', 'ammo50cal': '.50 cal',
        'ammo40m': 'Granat 40 mm', 'ammomininuke': 'Mini-nuke', 'ammofusion': 'Ogniwo fuzyjne'}
B = os.path.join(HERE, 'build')
W, H, G = 280, 300, 120
try:
    F1 = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 17)
except OSError:
    F1 = ImageFont.load_default()
sheet = Image.new('RGB', (W * 5, H * 2 + G + 20), (38, 42, 50))
for i, n in enumerate(NAZWY):
    base = n.replace('ammo', 'ammo_', 1)
    m, q = load_model(os.path.join(B, base + '.json'), lambda ref: os.path.join(B, ref.split('/')[-1] + '.png'))
    cv = Canvas(W, H, grad=((70, 76, 90), (34, 38, 46)))
    R = ortho_view(30, 35)
    fit = [dict(P=np.array([[3, 0, 3], [13, 16, 13]], float))]
    xf, pr, s = fit_ortho(fit, R, W, H, margin=0.1)
    draw(cv, q, xf, pr, light_preview)
    im = cv.image()
    ImageDraw.Draw(im).text((12, 10), '%d. %s' % (i + 1, OPIS[n]), fill=(240, 240, 240), font=F1)
    sheet.paste(im, ((i % 5) * W, (i // 5) * H))
    cv = Canvas(G, G, bg=(139, 139, 139), ss=2)
    xf, pr = gui_view(m['display'], G)
    draw(cv, q, xf, pr, light_flat)
    sheet.paste(cv.image(), (10 + i * (G + 18), H * 2 + 10))
sheet.save(sys.argv[1])
