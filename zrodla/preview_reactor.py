#!/usr/bin/env python3
"""Podglądy reaktora (gen_reactor.py): wszystkie skiny w czterech stanach, porównanie z crying
obsidian, animacja GIF i miniatury do menu rdzenia w pluginie (out/miniatury/<skin>_<stan>.png)."""
import json, math, os, sys, tempfile
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render import *
from preview import label
from gen_reactor import SKINS

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'build', 'reactor')
MODELS = os.path.join(OUT, 'assets/axon/models/block/reactor')
TMP = tempfile.mkdtemp()
SKY = ((126, 168, 214), (196, 214, 226))
SCALE = 1.2     # tak samo jak w pluginie (ReactorSkins)
CRYSTAL_SCALE = 0.55
CRYSTAL_Y = 15.5   # środek kryształu nad środkiem bloku, w pikselach
NAMES = {'active': 'zasilony', 'low': 'mało paliwa', 'off': 'wygaszony', 'raid': 'atak'}


def resolver(frame):
    def resolve(ref):
        p = os.path.join(OUT, 'assets', ref.split(':')[0], 'textures', ref.split(':')[1] + '.png')
        if not os.path.exists(p):
            return None
        im = Image.open(p).convert('RGBA')
        w, h = im.size
        if h > w:   # animowana: wybrana klatka
            n = h // w
            im = im.crop((0, (frame % n) * w, w, (frame % n) * w + w))
        out = os.path.join(TMP, '%s_%d.png' % (ref.replace(':', '_').replace('/', '_'), frame))
        im.save(out)
        return out
    return resolve


def model_quads(skin, name, frame):
    m = json.load(open(os.path.join(MODELS, skin, name + '.json')))
    if 'parent' in m and m['parent'].startswith('axon:'):
        base = json.load(open(os.path.join(MODELS, skin, m['parent'].split('/')[-1] + '.json')))
        base['textures'] = dict(base['textures'], **m['textures'])
        m = base
    path = os.path.join(TMP, skin + '_' + name + '.json')
    json.dump(m, open(path, 'w'))
    return load_model(path, resolver(frame))[1]


def placed(quads, M, offset):
    """Model (0..16) -> świat w pikselach modelu: środek bloku w 0, macierz M, przesunięcie."""
    out = []
    for q in quads:
        P = (q['P'] - 8) @ M.T + offset
        n = M @ q['n']
        out.append(dict(q, P=P, n=n / (np.linalg.norm(n) + 1e-9)))
    return out


def crystal_matrix(spin):
    # Stoi na wierzchołku: przechył 45° wokół X i 35,26° wokół Z, potem obrót wokół pionu.
    tilt = rot_axis('z', 35.26) @ rot_axis('x', 45)
    return rot_axis('y', spin) @ tilt * CRYSTAL_SCALE


def scene(skin, state, frame=0, spin=20.0):
    shell = placed(model_quads(skin, state, frame), np.eye(3) * SCALE, np.zeros(3))
    crystal = []
    if state != 'off':
        bob = 0.6 * math.sin(spin / 180 * math.pi)
        crystal = placed(model_quads(skin, 'crystal_' + state, frame), crystal_matrix(spin),
                         np.array([0, CRYSTAL_Y + bob, 0]))
    return shell, crystal


def frame_ref():
    """Ten sam kadr dla wszystkich skinów (największy z nich), żeby miały tę samą skalę."""
    return (placed(model_quads('pustka', 'active', 0), np.eye(3) * SCALE, np.zeros(3)) +
            placed(model_quads('standard', 'active', 0), np.eye(3) * 0.42, np.array([0, 22, 0])))


def render_state(skin, state, W, H, frame=0, spin=20.0, yaw=-35, pitch=24, bg=None, margin=0.08, glow=1.05):
    shell, crystal = scene(skin, state, frame, spin)
    R = ortho_view(yaw, pitch)
    cv = Canvas(W, H, grad=None if bg else SKY, bg=bg or (0, 0, 0))
    xf, pr, _ = fit_ortho(frame_ref(), R, W, H, margin)
    draw(cv, shell, xf, pr, light_preview)
    if crystal:
        draw(cv, crystal, xf, pr, lambda n: glow)   # kryształ świeci (pełna jasność)
    return cv


def thumbnail(skin, state, size):
    """Miniatura z przezroczystym tłem (alfa z bufora głębokości)."""
    # Kryształ ciemniejszy niż w grze: jasne pastele paleta map zamienia na błękit.
    cv = render_state(skin, state, size, size, frame=4, bg=(0, 0, 0), margin=0.02, glow=0.75)
    im = cv.image().convert('RGBA')
    mask = Image.fromarray(((cv.z > -1e8) * 255).astype(np.uint8)).resize((size, size), Image.BILINEAR)
    im.putalpha(mask.point(lambda a: 255 if a >= 110 else 0))
    return im


def crying_obsidian(W, H, yaw=-35, pitch=24):
    path = '/tmp/qa/pack/assets/minecraft/textures/block/crying_obsidian.png'
    cv = Canvas(W, H, grad=SKY)
    q = []
    for face in FACE_N:
        P = np.array(face_corners((0, 0, 0), (16, 16, 16), face), float) - 8
        if os.path.exists(path):
            tex = np.asarray(Image.open(path).convert('RGBA'), dtype=np.float32)[:16]
            q.append(dict(P=P, UV=np.array([(0, 0), (16, 0), (16, 16), (0, 16)], float), tex=tex,
                          n=np.array(FACE_N[face], float), box=(0, 0, 16, 16)))
        else:
            q.append(dict(P=P, color=np.array((40, 20, 70), float), n=np.array(FACE_N[face], float)))
    R = ortho_view(yaw, pitch)
    xf, pr, _ = fit_ortho(frame_ref(), R, W, H, 0.08)
    draw(cv, q, xf, pr, light_preview)
    return cv.image()


def main():
    out = os.path.join(HERE, 'out')
    os.makedirs(os.path.join(out, 'miniatury'), exist_ok=True)
    W = 260
    states = ('active', 'low', 'raid', 'off')
    sheet = Image.new('RGB', (W * 4 + 12, (W + 4) * len(SKINS)), (20, 22, 26))
    for r, (sid, s) in enumerate(SKINS.items()):
        for i, st in enumerate(states):
            im = render_state(sid, st, W, W, frame=3).image()
            sheet.paste(label(im, '%s: %s' % (s.name, NAMES[st]), 15), (i * (W + 4), r * (W + 4)))
    sheet.save(os.path.join(out, 'reaktor-stany.png'))

    big = 300
    skins = Image.new('RGB', ((big + 4) * len(SKINS) - 4, big), (20, 22, 26))
    for i, (sid, s) in enumerate(SKINS.items()):
        tag = s.name if s.index == 0 else s.name + ' (premium)'
        skins.paste(label(render_state(sid, 'active', big, big, frame=5, yaw=-28, pitch=16).image(), tag, 17),
                    (i * (big + 4), 0))
    skins.save(os.path.join(out, 'reaktor-skiny.png'))

    cmp = Image.new('RGB', (2 * W + 4, W), (20, 22, 26))
    cmp.paste(label(crying_obsidian(W, W), 'bez paczki: crying obsidian', 15), (0, 0))
    cmp.paste(label(render_state('standard', 'active', W, W, frame=3).image(), 'z paczką: reaktor', 15), (W + 4, 0))
    cmp.save(os.path.join(out, 'reaktor-porownanie.png'))

    fw = 200
    frames = []
    for f in range(32):
        im = Image.new('RGB', (fw * len(SKINS), fw))
        for i, sid in enumerate(SKINS):
            im.paste(render_state(sid, 'active', fw, fw, frame=f, spin=f * 360 / 32).image(), (i * fw, 0))
        frames.append(im)
    frames[0].save(os.path.join(out, 'reaktor-animacja.gif'), save_all=True, append_images=frames[1:],
                   duration=100, loop=0)

    for sid in SKINS:
        for st in states:
            thumbnail(sid, st, 72).save(os.path.join(out, 'miniatury', '%s_%s.png' % (sid, st)))
        thumbnail(sid, 'active', 52).save(os.path.join(out, 'miniatury', '%s_card.png' % sid))
    print('rendered')


if __name__ == '__main__':
    main()
