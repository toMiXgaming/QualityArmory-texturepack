#!/usr/bin/env python3
"""Szkice koncepcyjne broni białych (płaskie kolory), arkusz 5x2: koncepty_bronie_biale.py <plik.png>"""
import sys, random
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from render import box_quads, Canvas, draw, ortho_view, fit_ortho, light_preview
from PIL import Image, ImageDraw, ImageFont
F1 = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 17)
F2 = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 14)
import numpy as np

STAL = (150, 152, 158); STAL_J = (196, 198, 204); CIEMNA = (40, 40, 44)
TASMA = (162, 164, 160); DREWNO = (128, 90, 54); DREWNO_C = (92, 62, 36)
SKORA = (96, 64, 40); CZARNY = (30, 30, 32); RDZA = (130, 74, 42)


def B(f, t, c):
    return (f, t, c)


def rurka():
    e = [B([-0.6, 0, -0.6], [0.6, 28, 0.6], STAL), B([-0.75, 27, -0.75], [0.75, 28.4, 0.75], CIEMNA)]
    for y in range(0, 8):
        e.append(B([-0.75, y, -0.75], [0.75, y + 0.85, 0.75], TASMA if y % 2 == 0 else (140, 142, 140)))
    for y in (14, 19, 23):
        e.append(B([-0.62, y, -0.62], [0.62, y + 0.8, 0.62], RDZA))
    return e


def kij():
    e = []
    for i in range(14):
        w = 0.55 + i * 0.05
        e.append(B([-w, i * 2, -w], [w, i * 2 + 2, w], DREWNO if i % 3 else DREWNO_C))
    rnd = random.Random(3)
    for y in (18, 20, 22, 24, 26):
        s = rnd.choice((-1, 1))
        e.append(B([s * 1.2 if s > 0 else -2.6, y, -0.12], [2.6 if s > 0 else -1.2, y + 0.25, 0.12], STAL_J))
        e.append(B([-0.12, y + 1, s * 1.2 if s > 0 else -2.6], [0.12, y + 1.25, 2.6 if s > 0 else -1.2], STAL_J))
    for y in (17, 25.5):
        e.append(B([-1.3, y, -1.3], [1.3, y + 0.4, 1.3], (90, 92, 96)))
    e.append(B([-0.8, 0, -0.8], [0.8, 4, 0.8], TASMA))
    return e


def maczeta():
    e = [B([-0.7, 0, -0.5], [0.7, 7, 0.5], (110, 92, 70)), B([-0.75, 1, -0.55], [0.75, 2, 0.55], TASMA),
         B([-0.75, 4, -0.55], [0.75, 5, 0.55], TASMA), B([-1.0, 7, -0.6], [1.0, 7.6, 0.6], CIEMNA),
         B([-1.4, 7.6, -0.15], [1.6, 26, 0.15], STAL), B([-1.0, 26, -0.15], [1.6, 27.6, 0.15], STAL),
         B([-1.4, 7.6, -0.16], [-0.8, 26, 0.16], (120, 122, 128))]
    for y in np.arange(8, 26, 0.9):
        e.append(B([1.6, y, -0.15], [1.95, y + 0.45, 0.15], STAL_J))
    for y in (9, 16, 23):
        e.append(B([0.0, y, -0.2], [0.4, y + 0.4, 0.2], (100, 62, 34)))
    return e


def toporek():
    return [B([-0.6, 0, -0.5], [0.6, 24, 0.5], DREWNO), B([-0.7, 0, -0.6], [0.7, 1.2, 0.6], DREWNO_C),
            B([-1.2, 20, -0.7], [1.2, 24.4, 0.7], STAL), B([1.2, 19.4, -0.35], [4.2, 25.0, 0.35], STAL),
            B([4.2, 18.8, -0.2], [4.8, 25.6, 0.2], STAL_J), B([-2.2, 21, -0.7], [-1.2, 23.4, 0.7], STAL)]


def noz():
    e = [B([-0.6, y, -0.45], [0.6, y + 0.8, 0.45], SKORA if (y * 10) % 16 < 8 else DREWNO_C) for y in np.arange(1, 6.6, 0.8)]
    e += [B([-0.7, 0, -0.55], [0.7, 1, 0.55], (176, 140, 60)), B([-1.6, 6.4, -0.5], [1.6, 7.0, 0.5], (176, 140, 60)),
          B([-0.9, 7.0, -0.15], [0.9, 15, 0.15], STAL), B([-0.9, 15, -0.15], [0.5, 16.6, 0.15], STAL),
          B([-0.9, 16.6, -0.15], [0.0, 17.6, 0.15], STAL), B([0.6, 7.0, -0.16], [0.9, 15, 0.16], STAL_J),
          B([-0.5, 9, -0.17], [-0.2, 14.5, 0.17], (110, 112, 118))]
    return e


def lom():
    r = (150, 40, 32)
    return [B([-0.5, 1, -0.5], [0.5, 22, 0.5], r), B([-0.7, 0, -0.3], [0.7, 1.2, 0.3], STAL),
            B([-0.5, 21, -0.5], [2.5, 22, 0.5], r), B([2.0, 22, -0.5], [3.0, 23.5, 0.5], r),
            B([2.0, 23.5, -0.5], [0.0, 24.5, 0.5], r) if False else B([0.0, 23.5, -0.5], [3.0, 24.5, 0.5], r),
            B([-0.6, 23.8, -0.3], [0.0, 24.4, 0.3], STAL), B([-0.52, 8, -0.52], [0.52, 9.5, 0.52], STAL),
            B([-0.52, 15, -0.52], [0.52, 15.8, 0.52], STAL)]


def kabar():
    e = [B([-0.6, y, -0.45], [0.6, y + 0.6, 0.45], SKORA if int(y * 10) % 12 < 6 else (78, 52, 32)) for y in np.arange(1, 6.4, 0.6)]
    e += [B([-0.75, 0, -0.55], [0.75, 1, 0.55], CZARNY), B([-1.5, 6.4, -0.55], [1.5, 7.0, 0.55], STAL),
          B([-0.85, 7.0, -0.15], [0.85, 16, 0.15], CZARNY), B([-0.85, 16, -0.15], [0.3, 17.6, 0.15], CZARNY),
          B([0.3, 15.4, -0.15], [0.85, 16.4, 0.15], CZARNY), B([0.55, 7.0, -0.16], [0.85, 16, 0.16], (90, 92, 96)),
          B([-0.4, 8, -0.17], [-0.15, 14, 0.17], (54, 54, 58))]
    return e


def saperka():
    o = (84, 92, 58)
    return [B([-0.5, 0, -0.5], [0.5, 15, 0.5], DREWNO_C), B([-1.6, 0, -0.5], [1.6, 0.8, 0.5], CIEMNA),
            B([-1.6, 0, -0.5], [-1.0, 2.6, 0.5], CIEMNA), B([1.0, 0, -0.5], [1.6, 2.6, 0.5], CIEMNA),
            B([-0.8, 15, -0.7], [0.8, 16.6, 0.7], CIEMNA), B([-0.9, 15.4, -0.8], [0.9, 16.2, 0.8], STAL),
            B([-2.6, 16.6, -0.2], [2.6, 21.6, 0.2], o), B([-2.0, 21.6, -0.2], [2.0, 22.6, 0.2], o),
            B([-1.2, 22.6, -0.21], [1.2, 23.2, 0.21], STAL_J), B([-2.65, 17, -0.21], [-2.4, 21.4, 0.21], STAL_J),
            B([2.4, 17, -0.21], [2.65, 21.4, 0.21], STAL_J)]


def tomahawk():
    return [B([-0.6, 0, -0.45], [0.6, 22, 0.45], CZARNY), B([-0.65, 2, -0.5], [0.65, 8, 0.5], (52, 52, 56)),
            B([-1.0, 18.4, -0.6], [1.0, 22.6, 0.6], CZARNY), B([1.0, 18.8, -0.3], [3.6, 22.4, 0.3], CZARNY),
            B([3.6, 17.6, -0.2], [4.2, 23.4, 0.2], (110, 112, 118)), B([-2.0, 20.0, -0.4], [-1.0, 21.2, 0.4], CZARNY),
            B([-3.2, 20.3, -0.25], [-2.0, 20.9, 0.25], CZARNY), B([-0.7, 0, -0.55], [0.7, 0.8, 0.55], STAL)]


def palka():
    e = [B([-0.7, 0, -0.7], [0.7, 8, 0.7], CZARNY), B([-0.75, 0, -0.75], [0.75, 0.8, 0.75], STAL),
         B([-0.5, 8, -0.5], [0.5, 15, 0.5], STAL_J), B([-0.4, 15, -0.4], [0.4, 21, 0.4], STAL_J),
         B([-0.3, 21, -0.3], [0.3, 26, 0.3], STAL_J), B([-0.55, 26, -0.55], [0.55, 27.2, 0.55], STAL)]
    for y in np.arange(1, 7.6, 0.8):
        e.append(B([-0.72, y, -0.72], [0.72, y + 0.25, 0.72], (46, 46, 50)))
    return e


BRONIE = [('Rurka z taśmą', 'startowa', rurka), ('Kij z gwoździami', 'startowa', kij), ('Maczeta z piły', 'startowa', maczeta),
          ('Toporek', 'średnia', toporek), ('Nóż myśliwski', 'średnia', noz), ('Łom', 'średnia', lom),
          ('Nóż bojowy KA-BAR', 'wojskowa', kabar), ('Saperka', 'wojskowa', saperka), ('Tomahawk', 'wojskowa', tomahawk),
          ('Pałka teleskopowa', 'służbowa', palka)]
W, H = 280, 420
sheet = Image.new('RGB', (W * 5, H * 2), (38, 42, 50))
for i, (n, tier, fn) in enumerate(BRONIE):
    quads = []
    for f, t, c in fn():
        quads += box_quads(f, t, c)
    cv = Canvas(W, H, grad=((70, 76, 90), (34, 38, 46)))
    R = ortho_view(30, 12)
    fit = [dict(P=np.array([[-4, -1, -3], [4, 28, 3]], float))]
    xf, pr, s = fit_ortho(fit, R, W, H, margin=0.1)
    draw(cv, quads, xf, pr, light_preview)
    im = cv.image()
    dr = ImageDraw.Draw(im)
    dr.text((12, 10), '%d. %s' % (i + 1, n), fill=(240, 240, 240), font=F1)
    dr.text((12, 32), tier, fill=(180, 186, 196), font=F2)
    sheet.paste(im, ((i % 5) * W, (i // 5) * H))
sheet.save(sys.argv[1])
