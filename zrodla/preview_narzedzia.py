#!/usr/bin/env python3
"""Podglądy narzędzi i broni białych: ikona GUI (powiększona) i widok z boku, siatka kilku modeli.
python3 preview_narzedzia.py wyjscie.png model1 model2 ...   (nazwy plików z build/, np. narz_stone_axe kabar)"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render import *
from preview import font, label

HERE = os.path.dirname(os.path.abspath(__file__))
B = os.path.join(HERE, 'build')


def res(ref):
    p = os.path.join(B, ref.split('/')[-1] + '.png')
    return p if os.path.exists(p) else None


def gui(name, px=300):
    m, q = load_model(os.path.join(B, name + '.json'), res)
    cv = Canvas(px, px, bg=(139, 139, 139), ss=2)
    xf, pr = gui_view(m['display'], px)
    draw(cv, q, xf, pr, light_flat)
    return cv.image()


def side(name, px=300):
    m, q = load_model(os.path.join(B, name + '.json'), res)
    cv = Canvas(px, px, bg=(48, 52, 58), ss=2)
    R = ortho_view(0, 0)
    xf, pr, _ = fit_ortho(q, R, px, px, 0.06)
    draw(cv, q, xf, pr, light_preview)
    return cv.image()


def sheet(names, cols=4, px=300):
    rows = (len(names) + cols - 1) // cols
    out = Image.new('RGB', (cols * px, rows * (px + 22)), (30, 32, 36))
    for i, n in enumerate(names):
        x, y = (i % cols) * px, (i // cols) * (px + 22)
        im = gui(n, px) if not n.startswith('side:') else side(n[5:], px)
        out.paste(im, (x, y + 22))
        d = ImageDraw.Draw(out)
        d.text((x + 6, y + 5), n.replace('narz_', ''), font=font(13), fill=(235, 235, 235))
    return out


if __name__ == '__main__':
    sheet(sys.argv[2:]).save(sys.argv[1])
