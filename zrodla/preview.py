#!/usr/bin/env python3
"""Preview renders: side, 3/4, first person (hip), ADS (off-hand), GUI slot, third person,
plus a comparison sheet against QualityArmory's original model."""
import json, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render import *

HERE = os.path.dirname(os.path.abspath(__file__))
QA = '/tmp/qa/pack'
S_OF = {'ak47': 1, 'm4a1s': 1, 'remmington': -1, 'makarov': 1}
TITLE = {'ak47': 'AK-47', 'm4a1s': 'M4A1-S', 'remmington': 'Remington 870', 'makarov': 'Makarov PM'}
SKY = ((126, 168, 214), (196, 214, 226))


def font(sz):
    for p in ('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
              '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'):
        if os.path.exists(p):
            return ImageFont.truetype(p, sz)
    return ImageFont.load_default()


def label(im, txt, sz=18, xy=(10, 8), col=(235, 235, 235)):
    d = ImageDraw.Draw(im)
    d.text((xy[0] + 1, xy[1] + 1), txt, font=font(sz), fill=(0, 0, 0))
    d.text(xy, txt, font=font(sz), fill=col)
    return im


def load(name, which):
    if which == 'axon':
        res = lambda ref: (os.path.join(HERE, 'build', ref.split('/')[-1] + '.png')
                           if ref.startswith('qualityarmory:axon/') else resolver_for(QA)(ref))
        return load_model(os.path.join(HERE, 'build', name + '.json'), res)
    return load_model(os.path.join(QA, 'assets/qualityarmory/models/gun', name + '.json'), resolver_for(QA))


def side_view(q, name, W, H, left=False, yaw_off=0, pitch=0, bg=(38, 42, 50), margin=0.05):
    s = S_OF[name]
    base = 180 if s == 1 else 0           # camera on the gun's right side
    if left:
        base += 180
    R = ortho_view(base + yaw_off, pitch)
    cv = Canvas(W, H, bg=bg, grad=((52, 58, 68), (28, 31, 37)))
    xf, pr, _ = fit_ortho(q, R, W, H, margin)
    draw(cv, q, xf, pr, light_preview)
    return cv.image()


def fp_view(m, q, W, H, left=False, cross=True):
    cv = Canvas(W, H, grad=SKY)
    # ground band
    cv.col[int(cv.col.shape[0] * 0.62):] = (98, 128, 74)
    xf, pr = first_person(m['display'], W, H, left=left, charged=True)
    draw(cv, q, xf, pr, light_mc3d, near=0.05)
    im = cv.image()
    if cross:
        d = ImageDraw.Draw(im)
        c = (W // 2, H // 2)
        d.line([(c[0] - 7, c[1]), (c[0] + 7, c[1])], fill=(255, 255, 255), width=1)
        d.line([(c[0], c[1] - 7), (c[0], c[1] + 7)], fill=(255, 255, 255), width=1)
    return im


def gui_view_img(m, q, px=160):
    cv = Canvas(px, px, bg=(139, 139, 139), ss=1)
    xf, pr = gui_view(m['display'], px)
    draw(cv, q, xf, pr, light_flat)
    big = cv.image()
    # actual-size slot at GUI scale 2 (32 px) upscaled nearest for inspection
    cv2 = Canvas(32, 32, bg=(139, 139, 139), ss=1)
    xf, pr = gui_view(m['display'], 32)
    draw(cv2, q, xf, pr, light_flat)
    small = cv2.image().resize((96, 96), Image.NEAREST)
    return big, small


def third_view(m, q, W, H):
    xf_item, pivot, Ra, B = third_person_world(m['display'])
    gun = [dict(qq, P=xf_item(qq['P']), n=None) for qq in q]
    for g0, g1 in zip(gun, q):
        P = g1['P']
        n = xf_item(P[:1] + g1['n'][None]) - xf_item(P[:1])
        g0['n'] = n[0] / (np.linalg.norm(n[0]) + 1e-9)
    pl = player_quads()
    allq = gun + pl
    R = ortho_view(-125, 12)   # player faces +Z; view from front-right
    cv = Canvas(W, H, grad=SKY)
    xf, pr, _ = fit_ortho(allq, R, W, H, 0.06)
    draw(cv, allq, xf, pr, light_preview)
    return cv.image()


def sheet(name):
    m, q = load(name, 'axon')
    W = 1000
    a = label(side_view(q, name, W, 400), TITLE[name] + '  -  prawa strona / right side', 22)
    b = label(side_view(q, name, W, 400, left=True, yaw_off=-32, pitch=18), 'widok 3/4 (lewa strona)', 18)
    fp = label(fp_view(m, q, 496, 279), 'first person (biodro)', 15)
    ads = label(fp_view(m, q, 496, 279, left=True), 'celowanie / ADS (off-hand)', 15)
    tp = label(third_view(m, q, 330, 330), '3rd person', 15)
    gb, gs = gui_view_img(m, q, 160)
    gui = Image.new('RGB', (330, 330), (60, 60, 64))
    gui.paste(gb, (10, 40)); gui.paste(gs, (200, 72))
    label(gui, 'GUI slot (x10 / 32px)', 15)
    out = Image.new('RGB', (W, 400 + 400 + 279 + 330 + 8), (20, 22, 26))
    out.paste(a, (0, 0)); out.paste(b, (0, 402))
    out.paste(fp, (0, 804)); out.paste(ads, (504, 804))
    out.paste(tp, (0, 1085)); out.paste(gui, (335, 1085))
    # texture atlas
    tex = Image.open(os.path.join(HERE, 'build', name + '.png')).convert('RGB').resize((256, 256), Image.NEAREST)
    out.paste(tex, (680, 1085 + 37))
    label(out, 'tekstura 128x128', 15, (680, 1090))
    return out


def compare(name):
    rows = []
    for which, lab in (('qa', 'QualityArmory (oryginal)'), ('axon', 'AXON (nowy)')):
        m, q = load(name, which)
        sv = label(side_view(q, name, 620, 250), lab, 17)
        fp = fp_view(m, q, 444, 250)
        ads = fp_view(m, q, 444, 250, left=True)
        tp = third_view(m, q, 250, 250)
        r = Image.new('RGB', (620 + 444 * 2 + 250 + 12, 250), (20, 22, 26))
        r.paste(sv, (0, 0)); r.paste(fp, (624, 0)); r.paste(ads, (624 + 448, 0)); r.paste(tp, (624 + 896, 0))
        rows.append(r)
    out = Image.new('RGB', (rows[0].width, 254 * 2), (20, 22, 26))
    for i, r in enumerate(rows):
        out.paste(r, (0, i * 254))
    return out


if __name__ == '__main__':
    names = sys.argv[1:] or ['ak47', 'm4a1s', 'remmington', 'makarov']
    os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
    for n in names:
        sheet(n).save(os.path.join(HERE, 'out', n + '-podglad.png'))
        compare(n).save(os.path.join(HERE, 'out', n + '-porownanie.png'))
        print('rendered', n)
