#!/usr/bin/env python3
"""Podgląd przedmiotów (granaty, mina, apteczka...) w widoku izometrycznym: preview_przedmioty.py wyjscie.png [nazwa ...]"""
import os, sys
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render import *
from preview import font
import preview_narzedzia as P
from gen_przedmioty import NAMES


SC = 1
ROT = (30, 225, 0)


def iso(name, px=300, rot=None):
    rot = rot or ROT
    m, q = load_model(os.path.join(P.B, name + '.json'), P.res)
    cv = Canvas(px, px, bg=(139, 139, 139), ss=2)
    d = {'gui': {'rotation': list(rot), 'translation': [0, 0, 0], 'scale': [SC, SC, SC]}}
    xf, pr = gui_view(d, px)
    draw(cv, q, xf, pr, light_flat)
    return cv.image()


def main(out, names, prefix='misc_'):
    names = names or NAMES
    cols = 3
    rows = (len(names) + cols - 1) // cols
    px = 300
    sh = Image.new('RGB', (cols * px, rows * (px + 22)), (30, 32, 36))
    for i, n in enumerate(names):
        x, y = (i % cols) * px, (i // cols) * (px + 22)
        sh.paste(iso(prefix + n, px), (x, y + 22))
        ImageDraw.Draw(sh).text((x + 6, y + 5), n, font=font(13), fill=(235, 235, 235))
    sh.save(out)


if __name__ == '__main__':
    a = sys.argv[2:]
    pre = 'misc_'
    if a and a[0].startswith('prefix='):
        pre = a.pop(0)[7:]
    if a and a[0].startswith('rot='):
        ROT = tuple(float(v) for v in a.pop(0)[4:].split(','))
    if a and a[0].startswith('scale='):
        SC = float(a.pop(0)[6:])
    main(sys.argv[1], a, pre)
