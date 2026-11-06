#!/usr/bin/env python3
"""Podgląd przedmiotów (granaty, mina, apteczka...) w widoku izometrycznym: preview_przedmioty.py wyjscie.png [nazwa ...]"""
import os, sys
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render import *
from preview import font
import preview_narzedzia as P
from gen_przedmioty import NAMES


def iso(name, px=300, rot=(28, 215, 0)):
    m, q = load_model(os.path.join(P.B, name + '.json'), P.res)
    cv = Canvas(px, px, bg=(139, 139, 139), ss=2)
    d = {'gui': {'rotation': list(rot), 'translation': [0, 0, 0], 'scale': [1, 1, 1]}}
    xf, pr = gui_view(d, px)
    draw(cv, q, xf, pr, light_flat)
    return cv.image()


def main(out, names):
    names = names or NAMES
    cols = 3
    rows = (len(names) + cols - 1) // cols
    px = 300
    sh = Image.new('RGB', (cols * px, rows * (px + 22)), (30, 32, 36))
    for i, n in enumerate(names):
        x, y = (i % cols) * px, (i // cols) * (px + 22)
        sh.paste(iso('misc_' + n, px), (x, y + 22))
        ImageDraw.Draw(sh).text((x + 6, y + 5), n, font=font(13), fill=(235, 235, 235))
    sh.save(out)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2:])
