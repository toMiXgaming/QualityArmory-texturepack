#!/usr/bin/env python3
"""Podgląd broni białych z gen_bronie_biale.py: preview_bronie_biale.py <plik.png>
Górne dwa rzędy: modele z bliska, dolny rząd: ikony w ekwipunku (gui)."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from render import load_model, Canvas, draw, ortho_view, fit_ortho, gui_view, light_preview, light_flat
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from gen_bronie_biale import NAZWY

OPIS = {'rurka': ('Rurka z taśmą', 'startowa'), 'kij': ('Kij z gwoździami', 'startowa'),
        'maczeta': ('Maczeta z piły', 'startowa'), 'toporek': ('Toporek', 'średnia'),
        'noz': ('Nóż myśliwski', 'średnia'), 'lom': ('Łom', 'średnia'), 'kabar': ('Nóż bojowy KA-BAR', 'wojskowa'),
        'saperka': ('Saperka', 'wojskowa'), 'tomahawk': ('Tomahawk', 'wojskowa'), 'palka': ('Pałka teleskopowa', 'służbowa')}
B = os.path.join(HERE, 'build')
W, H, G = 280, 460, 120
try:
    F1 = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 17)
    F2 = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 14)
except OSError:
    F1 = F2 = ImageFont.load_default()
sheet = Image.new('RGB', (W * 5, H * 2 + G + 20), (38, 42, 50))
for i, n in enumerate(NAZWY):
    m, q = load_model(os.path.join(B, n + '.json'), lambda ref: os.path.join(B, ref.split('/')[-1] + '.png'))
    cv = Canvas(W, H, grad=((70, 76, 90), (34, 38, 46)))
    R = ortho_view(30, 12)
    fit = [dict(P=np.array([[3.5, -1, 5], [12.5, 29, 11]], float))]
    xf, pr, s = fit_ortho(fit, R, W, H, margin=0.12)
    draw(cv, q, xf, pr, light_preview)
    im = cv.image()
    d = ImageDraw.Draw(im)
    d.text((12, 10), '%d. %s' % (i + 1, OPIS[n][0]), fill=(240, 240, 240), font=F1)
    d.text((12, 32), OPIS[n][1], fill=(180, 186, 196), font=F2)
    sheet.paste(im, ((i % 5) * W, (i // 5) * H))
    cv = Canvas(G, G, bg=(139, 139, 139), ss=2)
    xf, pr = gui_view(m['display'], G)
    draw(cv, q, xf, pr, light_flat)
    sheet.paste(cv.image(), (10 + i * (G + 18), H * 2 + 10))
sheet.save(sys.argv[1])
