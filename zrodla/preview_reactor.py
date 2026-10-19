#!/usr/bin/env python3
"""Podglądy reaktora (gen_reactor.py): cztery stany obok siebie, porównanie z crying obsidian
i animacja GIF zasilonego reaktora z obracającym się kryształem."""
import json, math, os, sys, tempfile
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render import *
from preview import label

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


def model_quads(name, frame):
    m = json.load(open(os.path.join(MODELS, name + '.json')))
    if 'parent' in m and m['parent'].startswith('axon:'):
        base = json.load(open(os.path.join(MODELS, m['parent'].split('/')[-1] + '.json')))
        base['textures'] = dict(base['textures'], **m['textures'])
        m = base
    path = os.path.join(TMP, name + '.json')
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


def scene(state, frame=0, spin=20.0):
    shell = placed(model_quads(state, frame), np.eye(3) * SCALE, np.zeros(3))
    crystal = []
    if state != 'off':
        bob = 0.6 * math.sin(spin / 180 * math.pi)
        crystal = placed(model_quads('crystal_' + state, frame), crystal_matrix(spin), np.array([0, CRYSTAL_Y + bob, 0]))
    return shell, crystal


def render_state(state, W, H, frame=0, spin=20.0, yaw=-35, pitch=24):
    shell, crystal = scene(state, frame, spin)
    R = ortho_view(yaw, pitch)
    cv = Canvas(W, H, grad=SKY)
    frame_pts = shell + placed(model_quads('active', 0), np.eye(3) * 0.42, np.array([0, 22, 0]))
    xf, pr, _ = fit_ortho(frame_pts, R, W, H, 0.08)
    draw(cv, shell, xf, pr, light_preview)
    if crystal:
        draw(cv, crystal, xf, pr, lambda n: 1.05)   # kryształ świeci (pełna jasność)
    return cv.image()


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
    ref = placed(model_quads('active', 0), np.eye(3) * SCALE, np.zeros(3)) + \
        placed(model_quads('active', 0), np.eye(3) * 0.42, np.array([0, 22, 0]))
    xf, pr, _ = fit_ortho(ref, R, W, H, 0.08)
    draw(cv, q, xf, pr, light_preview)
    return cv.image()


def main():
    os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
    W = 320
    sheet = Image.new('RGB', (W * 5 + 16, W + 4), (20, 22, 26))
    sheet.paste(label(crying_obsidian(W, W), 'dziś: crying obsidian', 16), (0, 2))
    for i, st in enumerate(('active', 'low', 'raid', 'off')):
        sheet.paste(label(render_state(st, W, W, frame=3), 'reaktor: ' + NAMES[st], 16), ((i + 1) * (W + 4), 2))
    sheet.save(os.path.join(HERE, 'out', 'reaktor-stany.png'))

    close = Image.new('RGB', (2 * 520 + 4, 520), (20, 22, 26))
    close.paste(label(render_state('active', 520, 520, frame=5, yaw=-28, pitch=14), 'zasilony z bliska', 18), (0, 0))
    close.paste(label(render_state('raid', 520, 520, frame=9, yaw=50, pitch=38), 'atak, widok z góry', 18), (524, 0))
    close.save(os.path.join(HERE, 'out', 'reaktor-z-bliska.png'))

    frames = [render_state('active', 360, 360, frame=f, spin=f * 360 / 32) for f in range(32)]
    frames[0].save(os.path.join(HERE, 'out', 'reaktor-animacja.gif'), save_all=True, append_images=frames[1:],
                   duration=100, loop=0)
    print('rendered')


if __name__ == '__main__':
    main()
