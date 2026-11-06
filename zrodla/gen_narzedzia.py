#!/usr/bin/env python3
"""Narzędzia vanilla (drewniane i kamienne: siekiera, kilof, łopata, motyka), narzędzia Axon
(steel_*, hardened_*) i bronie białe AXON, w nowej, dużo bardziej szczegółowej wersji.

Każdy model to kilkadziesiąt do ponad stu prostopadłościanów z własną teksturą 256x256 malowaną
proceduralnie silnikiem z gen.py (jednolita gęstość pikseli na ścianach, AO w załamaniach,
wytarte krawędzie), z lekkim klimatem rdzy: rdzawe plamy i wżery na stali, wyschnięte, spękane
drewno, wytarta skóra, odprysnięta farba. Stare modele z axoncore/tools.py i gen_bronie_biale.py
rozciągały jeden kafelek 8x8 / 32x32 na całą ścianę, stąd „rozmyty” wygląd.

Narzędzia leżą w tym samym układzie co poprzednio (trzonek od (8, 0.5), głowica po x, obrót -45° wokół z),
więc pozycje w ręce, w ekwipunku i na ziemi się nie zmieniają. Bronie białe stoją pionowo jak dotąd.
Żadnych napisów z nazwami na modelach.

Uruchomienie:  python3 gen_narzedzia.py [nazwa ...]   ->  build/narz_<nazwa>.json|png (narzędzia),
build/<nazwa>.json|png (bronie białe, stare nazwy zostają).
"""
import json, math, os, sys
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen
from gen import Gun, build_model, fbm, white, vnoise, EXTRA_KINDS, MATS
from axoncore.model import HANDHELD

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'build')


# ------------------------------------------------------------------ materiały (painters)
def _c(x):
    return np.array(x, float)


def _lerp(a, b, t):
    a = a if a.ndim == 2 else a[None]
    b = b if b.ndim == 2 else b[None]
    return a * (1 - t[:, None]) + b * t[:, None]


def k_wood(m, G, side, el, seed):
    """Drewno: włókna wzdłuż osi (domyślnie v), słoje na przekroju, spękania, szare wyschnięcie."""
    L, D = _c(m['light']), _c(m['dark'])
    w, v, u = G[:, 0], G[:, 1], G[:, 2]
    ax = m.get('axis', 'v')
    if ax == 'v':
        S = np.array([6.0, 0.22, 6.0])
        end = side in 'TB'
        cc = (el.lo + el.hi) / 2
        r = np.hypot(w - cc[0], u - cc[2]) * m.get('rings', 2.2)
    else:
        S = np.array([6.0, 6.0, 0.22])
        end = side in 'FK'
        cc = (el.lo + el.hi) / 2
        r = np.hypot(w - cc[0], v - cc[1]) * m.get('rings', 2.2)
    warp = fbm(G * np.array([0.5, 0.18, 0.5]) if ax == 'v' else G * np.array([0.5, 0.5, 0.18]), 3, seed) * 1.6
    if end:
        ring = (0.5 + 0.5 * np.sin((r + warp) * 2 * math.pi)) ** 1.6
        t = 0.25 + 0.6 * ring
    else:
        fib = fbm(G * S, 3, seed + 5)
        band = (0.5 + 0.5 * np.sin((G[:, 0] * 1.9 + G[:, 2] * 1.7 + warp * 2.0) * 2 * math.pi * 0.55)) ** 2
        t = 0.2 + 0.45 * band + 0.5 * (fib - 0.5)
    t = np.clip(t, 0, 1)
    col = _lerp(L, D, t)
    # wyschnięcie: szary, matowy nalot w płatach
    age = m.get('age', 0.35)
    gray = fbm(G * np.array([0.7, 0.25, 0.7]), 3, seed + 9)
    gm = np.clip((gray - (0.75 - 0.4 * age)) * 5, 0, 1) * 0.6
    col = _lerp(col, _c(m.get('gray', (150, 138, 120))), gm)
    # spękania i ciemne pory
    crack = np.abs(fbm(G * (np.array([2.0, 0.35, 2.0]) if ax == 'v' else np.array([2.0, 2.0, 0.35])), 2, seed + 21) - 0.5) < 0.018
    col[crack] *= 0.45
    pores = white(G * (np.array([1, 0.3, 1]) if ax == 'v' else np.array([1, 1, 0.3])), seed + 3, 5.0) > 0.93
    col[pores] *= 0.8
    return col


def k_metal(m, G, side, el, seed):
    """Stal z lekką rdzą: rdzawe plamy, wżery, rysy; opcjonalnie farba z odpryskami (paint=kolor)."""
    base = _c(m['base'])
    var = m.get('var', 0.1)
    mott = fbm(G * np.array([0.9, 0.9, 0.9]), 3, seed) - 0.5
    fine = white(G, seed + 7, 4.0) - 0.5
    col = base[None] * (1 + var * 0.9 * mott[:, None] + var * 0.35 * fine[:, None])
    # rysy wzdłuż osi najdłuższego wymiaru
    ext = el.hi - el.lo
    la = int(np.argmax(ext))
    Q = G.copy() * 3.0
    Q[:, la] *= 0.12
    sc = fbm(Q, 2, seed + 4)
    col[sc > 0.72] *= 1.18
    col[(sc < 0.2)] *= 0.88
    if 'paint' in m:
        pc = _c(m['paint'])
        chip = fbm(G * 1.7, 3, seed + 12)
        wornmask = np.clip((chip - (0.66 - 0.3 * m.get('chip', 0.5))) * 8, 0, 1)
        wornmask = np.maximum(wornmask, (white(G, seed + 17, 3.0) > 0.975) * 0.9)
        pcol = pc[None] * (1 + 0.07 * (white(G, seed + 6, 4.0) - 0.5)[:, None])
        col = _lerp(pcol, col, wornmask)
        # pod odpryskiem często rdza
        rm = wornmask * np.clip((fbm(G * 2.1, 2, seed + 14) - 0.4) * 4, 0, 1) * 0.8
        col = _lerp(col, _c((120, 66, 36)), rm)
    rust = m.get('rust', 0.3)
    if rust > 0:
        n = fbm(G * np.array([1.2, 0.9, 1.2]), 3, seed + 31)
        low = 1 - np.clip((G[:, 1] - el.lo[1]) / max(1.0, ext[1]), 0, 1) * 0.0
        patch = np.clip((n - (0.66 - 0.4 * rust)) * 7, 0, 1) * low
        patch = np.clip(patch * (0.55 + 0.9 * white(G, seed + 3, 5.0)), 0, 1)
        n2 = fbm(G * 2.3, 2, seed + 41)
        rc = _lerp(_c((150, 84, 42)), _c((98, 54, 30)), np.clip(n2 * 1.5, 0, 1))
        rc = rc * (1 + 0.1 * (white(G, seed + 8, 6.0) - 0.5)[:, None])
        col = col * (1 - patch[:, None]) + rc * patch[:, None]
        # wżery i jasne punkciki wokół rdzy
        pits = (white(G, seed + 9, 5.0) > 0.955) & (patch > 0.15)
        col[pits] *= 0.55
        halo = (patch > 0.02) & (patch < 0.25)
        col[halo] = col[halo] * 0.88
    return col


def k_stone(m, G, side, el, seed):
    """Odłupany kamień/krzemień: fasety o różnej jasności, żyłki, drobny nalot."""
    base = _c(m['base'])
    dark = _c(m['dark'])
    cell = np.floor(G * m.get('facet', 1.1))
    h = np.array([vnoise(np.array([[c[0] * 1.37 + 0.31, c[1] * 1.11 + 0.17, c[2] * 1.23 + 0.59]]), seed)[0]
                  for c in cell[:: max(1, 1)]]) if len(G) < 600 else None
    if h is None:      # szybka ścieżka: skrót hashem komórek
        ii = cell.astype(np.int64)
        h = ((ii[:, 0] * 73856093) ^ (ii[:, 1] * 19349663) ^ (ii[:, 2] * 83492791) ^ (seed * 7919)) & 0xFFFF
        h = h / 65535.0
    n = fbm(G * 1.3, 3, seed + 2)
    t = np.clip(0.35 + 0.5 * (h - 0.5) + 0.7 * (n - 0.5), 0, 1)
    col = _lerp(base, dark, t)
    vein = np.abs(fbm(G * np.array([0.8, 0.8, 0.8]), 2, seed + 11) - 0.5) < 0.02
    col[vein] = col[vein] * 0.7 + 40
    sp = white(G, seed + 5, 5.0)
    col[sp > 0.95] *= 1.25
    col[sp < 0.04] *= 0.7
    dirt = np.clip((fbm(G * 0.9, 3, seed + 19) - 0.62) * 5, 0, 1) * m.get('dirt', 0.5)
    return _lerp(col, _c(m.get('dirt_col', (92, 84, 64))), dirt)


def k_rope(m, G, side, el, seed):
    """Skręcony sznur / owijka: pasy pod kątem + włókna."""
    L, D = _c(m['light']), _c(m['dark'])
    w, v, u = G[:, 0], G[:, 1], G[:, 2]
    per = m.get('period', 0.55)
    ph = (v / per + (w + u) * 0.9) * 2 * math.pi
    t = (0.5 + 0.5 * np.sin(ph)) ** 1.5
    t = np.clip(t + 0.35 * (fbm(G * np.array([4.0, 1.2, 4.0]), 2, seed) - 0.5), 0, 1)
    col = _lerp(L, D, t)
    soil = np.clip((fbm(G * 0.9, 3, seed + 7) - 0.58) * 4, 0, 1) * m.get('dirt', 0.5)
    return _lerp(col, _c(m.get('dirt_col', (64, 52, 38))), soil)


def k_leather(m, G, side, el, seed):
    """Skóra: przeszycia, spękania, wytarcie jasne w płatach."""
    L, D = _c(m['light']), _c(m['dark'])
    w, v, u = G[:, 0], G[:, 1], G[:, 2]
    n = fbm(G * 2.4, 3, seed)
    band = (0.5 + 0.5 * np.sin((v * 1.7 + (w + u) * 0.7) * 2 * math.pi * 0.5)) ** 2
    t = np.clip(0.35 + 0.45 * (n - 0.5) * 2 + 0.25 * band, 0, 1)
    col = _lerp(L, D, t)
    crk = np.abs(fbm(G * 5.0, 2, seed + 3) - 0.5) < 0.025
    col[crk] *= 0.6
    wear = np.clip((fbm(G * 0.8, 3, seed + 8) - 0.6) * 5, 0, 1) * 0.55
    return _lerp(col, _c(m.get('wear_col', (150, 112, 74))), wear)


def k_tape(m, G, side, el, seed):
    """Taśma izolacyjna / duct tape: fałdy, brud, strzępy."""
    base = _c(m['base'])
    v = G[:, 1]
    fold = (0.5 + 0.5 * np.sin(v * 2 * math.pi / 0.9 + fbm(G * 1.5, 2, seed) * 3)) * 0.12
    col = base[None] * (1 - fold[:, None] * 0.8 + 0.06 * (white(G, seed + 2, 5.0) - 0.5)[:, None])
    dirt = np.clip((fbm(G * 1.1, 3, seed + 5) - 0.55) * 4, 0, 1) * 0.6
    return _lerp(col, _c((52, 46, 38)), dirt)


def k_cloth(m, G, side, el, seed):
    base = _c(m['base'])
    w, v, u = G[:, 0], G[:, 1], G[:, 2]
    weave = ((np.floor(v * 5) + np.floor((w + u) * 5)) % 2) * 0.1
    col = base[None] * (0.92 + weave[:, None] + 0.08 * (white(G, seed, 6.0) - 0.5)[:, None])
    stain = np.clip((fbm(G * 1.0, 3, seed + 3) - 0.55) * 5, 0, 1) * 0.5
    return _lerp(col, _c(m.get('stain', (70, 58, 44))), stain)


def k_rubber(m, G, side, el, seed):
    base = _c(m['base'])
    return base[None] * (0.9 + 0.2 * (white(G, seed + 1, 6.0))[:, None])


for _k, _f in (('t_wood', k_wood), ('t_metal', k_metal), ('t_stone', k_stone), ('t_rope', k_rope),
               ('t_leather', k_leather), ('t_tape', k_tape), ('t_cloth', k_cloth), ('t_rubber', k_rubber)):
    EXTRA_KINDS[_k] = _f

MATS.update({
    # drewno: jasne (deska), ciemne (stare), popielate (hartowane)
    'w_light': dict(kind='t_wood', light=(196, 152, 98), dark=(132, 94, 56), wear=(214, 178, 128), edge=0.4, age=0.4),
    'w_dark': dict(kind='t_wood', light=(120, 86, 54), dark=(70, 48, 30), wear=(160, 124, 88), edge=0.4, age=0.3),
    'w_ash': dict(kind='t_wood', light=(214, 190, 152), dark=(150, 124, 90), wear=(232, 214, 180), edge=0.4, age=0.25),
    'w_old': dict(kind='t_wood', light=(150, 116, 78), dark=(86, 62, 40), wear=(180, 150, 112), edge=0.4, age=0.45, gray=(128, 112, 92)),
    'w_flat': dict(kind='t_wood', light=(120, 86, 54), dark=(70, 48, 30), wear=(160, 124, 88), edge=0.4, age=0.5, axis='u'),
    'cord': dict(kind='t_rope', light=(184, 160, 116), dark=(104, 84, 56), wear=(200, 178, 136), edge=0.3, period=0.5),
    'cord_d': dict(kind='t_rope', light=(130, 108, 76), dark=(70, 56, 38), wear=(160, 136, 100), edge=0.3, period=0.45),
    'leather': dict(kind='t_leather', light=(112, 74, 46), dark=(66, 42, 26), wear=(150, 110, 74), edge=0.4),
    'leather_d': dict(kind='t_leather', light=(78, 50, 32), dark=(44, 28, 18), wear=(120, 84, 56), edge=0.4),
    'tape': dict(kind='t_tape', base=(70, 72, 74), wear=(110, 112, 114), edge=0.3),
    'tape_g': dict(kind='t_tape', base=(150, 152, 148), wear=(190, 192, 188), edge=0.3),
    'cloth': dict(kind='t_cloth', base=(124, 106, 82), wear=(156, 138, 110), edge=0.3),
    'rubber': dict(kind='t_rubber', base=(28, 28, 30), wear=(60, 60, 64), edge=0.4),
    # kamień
    'stone': dict(kind='t_stone', base=(128, 126, 120), dark=(70, 68, 64), wear=(190, 188, 180), edge=0.55),
    'flint': dict(kind='t_stone', base=(104, 108, 114), dark=(48, 52, 58), wear=(160, 164, 170), edge=0.6, facet=1.7, dirt=0.25),
    # stal: ze zwiększającą się rdzą
    'steel': dict(kind='t_metal', base=(116, 118, 124), wear=(186, 188, 194), edge=0.7, rust=0.28),
    'steel_d': dict(kind='t_metal', base=(78, 80, 86), wear=(158, 160, 166), edge=0.7, rust=0.3),
    'steel_l': dict(kind='t_metal', base=(150, 152, 158), wear=(210, 212, 218), edge=0.6, rust=0.12),
    'edge': dict(kind='t_metal', base=(176, 178, 184), wear=(226, 228, 232), edge=0.5, rust=0.06),
    'black': dict(kind='t_metal', base=(38, 38, 42), wear=(108, 110, 116), edge=0.8, rust=0.12, var=0.07),
    'black_e': dict(kind='t_metal', base=(66, 68, 74), wear=(156, 158, 164), edge=0.7, rust=0.06),
    'forged': dict(kind='t_metal', base=(60, 62, 68), wear=(150, 152, 158), edge=0.8, rust=0.1),
    'rail': dict(kind='t_metal', base=(98, 74, 62), wear=(160, 130, 108), edge=0.7, rust=0.55),
    'leaf': dict(kind='t_metal', base=(52, 54, 58), wear=(130, 132, 138), edge=0.8, rust=0.32),
    'brass': dict(kind='t_metal', base=(196, 158, 74), wear=(240, 214, 140), edge=0.6, rust=0.0, var=0.07),
    'rust': dict(kind='t_metal', base=(128, 72, 40), wear=(170, 110, 66), edge=0.5, rust=0.9),
    'tempered': dict(kind='t_metal', base=(168, 140, 72), wear=(224, 200, 130), edge=0.6, rust=0.0, var=0.12),
    'gem': dict(kind='t_metal', base=(70, 200, 216), wear=(190, 250, 255), edge=0.5, rust=0.0, var=0.05),
    'paint_olive': dict(kind='t_metal', base=(82, 90, 60), wear=(150, 150, 140), edge=0.6, rust=0.2, paint=(84, 94, 58), chip=0.6),
    'paint_red': dict(kind='t_metal', base=(112, 112, 116), wear=(180, 180, 184), edge=0.5, rust=0.25, paint=(150, 44, 36), chip=0.6),
    'paint_blue': dict(kind='t_metal', base=(112, 112, 116), wear=(180, 180, 184), edge=0.5, rust=0.2, paint=(40, 76, 120), chip=0.5),
    'g10': dict(kind='t_metal', base=(46, 48, 46), wear=(96, 98, 94), edge=0.6, rust=0.0, var=0.06),
    'wire': dict(kind='t_metal', base=(104, 106, 112), wear=(180, 182, 188), edge=0.6, rust=0.5),
})


# ------------------------------------------------------------------ silnik modelu
class Tool:
    """Siatka prostopadłościanów w układzie Minecrafta (x, y, z w pikselach modelu) -> Gun z gen.py."""

    def __init__(self, name, dx=8.0, dz=8.0):
        self.name = name
        self.dx, self.dz = dx, dz
        self.g = Gun(name, dict(s=1, k=1.0, kw=1.0, Xm=dx, Yb=0.0, Zc=dz))
        self.n = 0

    def box(self, f, t, mat, tag=None):
        """Prostopadłościan od f do t (x, y, z), współrzędne absolutne (np. trzonek w 7.5..8.5)."""
        lo = [min(a, c) for a, c in zip(f, t)]
        hi = [max(a, c) for a, c in zip(f, t)]
        for a in range(3):
            if hi[a] - lo[a] < 0.02:
                hi[a] = lo[a] + 0.02
        nm = '%s%d' % (tag or mat, self.n)
        self.n += 1
        self.g.b(nm, (lo[0] - self.dx, hi[0] - self.dx), (lo[1], hi[1]), (self.dz - hi[2], self.dz - lo[2]), mat)

    def vcyl(self, x, z, y0, y1, r, mat, k=0.68, tag='cyl'):
        """Pionowy walec o przekroju krzyża (jak g.cyl, ale oś wzdłuż y)."""
        self.box((x - r, y0, z - r * k), (x + r, y1, z + r * k), mat, tag)
        self.box((x - r * k, y0 + 0.03, z - r), (x + r * k, y1 - 0.03, z + r), mat, tag)

    def ring(self, x, z, y0, y1, r, mat, pad=0.08, k=0.68, tag='ring'):
        self.vcyl(x, z, y0, y1, r + pad, mat, k, tag)

    def wrap(self, x, z, y0, y1, r, mat, step=0.5, alt=None, pad=0.1):
        """Owijka z pasów (każdy pas to cienki pierścień), co drugi inny kolor."""
        y, i = y0, 0
        while y < y1 - 1e-6:
            yy = min(y + step, y1)
            self.vcyl(x, z, y, yy, r + pad + (0.04 if i % 2 else 0), alt if (alt and i % 2) else mat, tag='wrap')
            y += step
            i += 1

    def save(self, texname, display, tool_rot=True, density=10.0):
        self.g.density = density
        self.g.sight = None
        model, img, dens, nf = build_model(self.g, texname, display)
        model['credit'] = 'AXON narzedzia - generated by gen_narzedzia.py (procedural, original)'
        if tool_rot:
            for e in model['elements']:
                e['rotation'] = {'angle': -45, 'axis': 'z', 'origin': [8, 8, 8]}
            model['gui_light'] = 'front'
        for e in model['elements']:
            for c in e['from'] + e['to']:
                assert -16 <= c <= 32, (self.name, e['name'], c)
        return model, img, dens, nf


# ------------------------------------------------------------------ szczegóły wspólne
def handle(t, top, wood, wrap=None, wrap_to=4.5, cap=None, x=8.0, z=8.0, taper=0.06):
    """Trzonek: lekko zwężający się walec, sęk, pęknięcie, gałka na dole."""
    n = max(2, int(top / 3.5))
    h = (top - 0.5) / n
    for i in range(n):
        r = 0.52 - taper * i / max(1, n - 1)
        t.vcyl(x, z, 0.5 + i * h, 0.5 + (i + 1) * h + 0.02, r, wood, tag='handle')
    t.box((x - 0.62, 0.0, z - 0.5), (x + 0.62, 0.6, z + 0.5), cap or wood, 'butt')
    t.box((x - 0.5, 0.3, z - 0.6), (x + 0.5, 0.7, z + 0.6), cap or wood, 'butt')
    if wrap:
        t.wrap(x, z, 1.0, wrap_to, 0.52, wrap[0], 0.4, wrap[1] if len(wrap) > 1 else None)
        t.box((x - 0.7, wrap_to, z - 0.3), (x + 0.7, wrap_to + 0.25, z + 0.3), wrap[0], 'wend')
    # sęk i zadziory
    t.box((x + 0.45, 6.2, z - 0.2), (x + 0.75, 6.9, z + 0.2), wood, 'knot')
    t.box((x - 0.78, 9.1, z - 0.18), (x - 0.5, 9.7, z + 0.18), wood, 'knot')


def lash(t, x, z, y0, y1, r=0.58, mat='cord', turns=None):
    n = turns or max(2, int((y1 - y0) / 0.35))
    h = (y1 - y0) / n
    for i in range(n):
        t.vcyl(x, z, y0 + i * h, y0 + (i + 1) * h - 0.04, r + (0.05 if i % 2 else 0), mat if i % 3 else 'cord_d', tag='lash')


def nail(t, x, y, z, side=1, mat='steel_d', ln=0.5):
    t.box((x - 0.12, y - 0.12, z + side * 0.4), (x + 0.12, y + 0.12, z + side * (0.4 + ln)), mat, 'nail')
    t.box((x - 0.2, y - 0.2, z + side * (0.4 + ln)), (x + 0.2, y + 0.2, z + side * (0.4 + ln + 0.1)), mat, 'nailh')


# ------------------------------------------------------------------ vanilla: drewniane i kamienne
def v_axe(name, head, lash_m, stick, head_dark, stone):
    t = Tool(name)
    handle(t, 13.8, stick, wrap=('leather', 'leather_d'), wrap_to=4.4)
    # głowica: klin (stone: odłupany, wood: ciosany), ułożona na trzonku z podkładką
    x0 = 8.5
    t.box((x0, 9.6, 7.55), (x0 + 3.6, 14.6, 8.45), head, 'head')
    t.box((x0 + 3.6, 10.1, 7.7), (x0 + 4.3, 14.1, 8.3), head, 'headb')
    t.box((x0 + 4.3, 10.5, 7.82), (x0 + 4.7, 13.7, 8.18), head_dark if not stone else 'flint', 'bit')
    t.box((x0 + 0.6, 14.6, 7.7), (x0 + 3.0, 15.0, 8.3), head, 'topnib')
    t.box((x0 + 0.8, 9.2, 7.7), (x0 + 2.8, 9.6, 8.3), head, 'beard')
    t.box((x0 + 3.0, 8.9, 7.8), (x0 + 3.8, 9.6, 8.2), head, 'beard')
    t.box((7.35, 9.4, 7.35), (8.65, 14.8, 8.65), stick, 'eye')       # oko: trzonek grubszy przy głowicy
    t.box((x0 + 1.0, 11.0, 7.45), (x0 + 1.3, 13.4, 7.55), head_dark, 'seam')
    t.box((x0 + 1.0, 11.0, 8.45), (x0 + 1.3, 13.4, 8.55), head_dark, 'seam')
    lash(t, 8, 8, 10.2, 11.4, 0.62, lash_m)
    lash(t, 8, 8, 12.9, 14.1, 0.62, lash_m)
    t.box((x0 - 0.1, 11.6, 7.4), (x0 + 1.5, 12.4, 7.55), lash_m, 'strap')
    t.box((x0 - 0.1, 11.6, 8.45), (x0 + 1.5, 12.4, 8.6), lash_m, 'strap')
    if not stone:
        nail(t, 10.6, 12.3, 8.0, 1)
        nail(t, 10.6, 12.3, 8.0, -1)
    else:
        for yy in (10.4, 13.4):
            t.box((x0 + 1.6, yy, 7.45), (x0 + 2.0, yy + 0.35, 7.55), 'flint', 'chip')
            t.box((x0 + 2.4, yy + 0.4, 8.45), (x0 + 2.8, yy + 0.75, 8.55), 'flint', 'chip')
    return t


def v_pickaxe(name, head, lash_m, stick, head_dark, stone):
    t = Tool(name)
    handle(t, 12.6, stick, wrap=('leather', 'leather_d'), wrap_to=4.4)
    t.box((3.0, 12.5, 7.5), (13.0, 14.0, 8.5), head, 'head')
    t.box((7.0, 12.0, 7.3), (9.0, 14.5, 8.7), head, 'eye')
    t.box((13.0, 12.7, 7.65), (13.5, 13.8, 8.35), head, 'armR')
    t.box((13.5, 12.9, 7.8), (13.8, 13.6, 8.2), head_dark if not stone else 'flint', 'tipR')
    t.box((2.5, 12.7, 7.65), (3.0, 13.8, 8.35), head, 'armL')
    t.box((2.2, 12.9, 7.8), (2.5, 13.6, 8.2), head_dark if not stone else 'flint', 'tipL')
    t.box((3.5, 14.0, 7.7), (12.5, 14.3, 8.3), head, 'crown')
    for x in (4.2, 5.8, 10.2, 11.8):                                         # rysy / fasety na głowicy
        t.box((x, 12.9, 7.4), (x + 0.5, 13.5, 7.5), head_dark, 'facet')
        t.box((x + 0.2, 13.1, 8.5), (x + 0.7, 13.7, 8.6), head_dark, 'facet')
    lash(t, 8, 8, 11.3, 12.4, 0.6, lash_m)
    t.box((6.4, 12.4, 7.35), (9.6, 12.8, 7.5), lash_m, 'strap')
    t.box((6.4, 12.4, 8.5), (9.6, 12.8, 8.65), lash_m, 'strap')
    if not stone:
        nail(t, 6.8, 13.2, 8.0, 1)
        nail(t, 9.2, 13.2, 8.0, -1)
    return t


def v_shovel(name, head, lash_m, stick, head_dark, stone):
    t = Tool(name)
    handle(t, 10.8, stick, wrap=('leather', 'leather_d'), wrap_to=4.0)
    t.box((6.0, 10.5, 7.6), (10.0, 14.2, 8.4), head, 'blade')
    t.box((6.6, 14.2, 7.65), (9.4, 15.2, 8.35), head, 'blade2')
    t.box((7.1, 15.2, 7.72), (8.9, 15.8, 8.28), head, 'blade3')
    t.box((7.5, 15.8, 7.85), (8.5, 16.1, 8.15), head_dark if not stone else 'flint', 'tip')
    t.box((5.7, 10.9, 7.7), (6.0, 13.6, 8.3), head_dark, 'edgeL')
    t.box((10.0, 10.9, 7.7), (10.3, 13.6, 8.3), head_dark, 'edgeR')
    t.box((7.2, 10.5, 7.4), (8.8, 13.4, 7.6), head_dark, 'spine')       # żebro wzmacniające
    t.box((7.2, 10.5, 8.4), (8.8, 13.4, 8.6), head_dark, 'spine')
    t.box((7.3, 9.6, 7.3), (8.7, 10.8, 8.7), stick, 'socket')
    lash(t, 8, 8, 9.2, 10.4, 0.6, lash_m)
    for yy in (11.8, 13.2):
        t.box((6.3, yy, 8.4), (6.7, yy + 0.4, 8.5), head_dark, 'chip')
        t.box((9.3, yy + 0.2, 7.5), (9.7, yy + 0.6, 7.6), head_dark, 'chip')
    if not stone:
        nail(t, 7.2, 11.0, 8.0, 1)
        nail(t, 8.8, 11.0, 8.0, -1)
    return t


def v_hoe(name, head, lash_m, stick, head_dark, stone):
    t = Tool(name)
    handle(t, 14.0, stick, wrap=('leather', 'leather_d'), wrap_to=4.4)
    t.box((8.5, 12.7, 7.6), (12.2, 14.4, 8.4), head, 'blade')
    t.box((12.2, 12.4, 7.7), (13.0, 14.0, 8.3), head, 'blade2')
    t.box((11.2, 11.3, 7.72), (12.2, 12.7, 8.28), head, 'hook')
    t.box((11.5, 10.7, 7.82), (12.1, 11.3, 8.18), head_dark if not stone else 'flint', 'hooktip')
    t.box((12.6, 12.6, 7.82), (13.3, 13.5, 8.18), head_dark if not stone else 'flint', 'bit')
    t.box((7.3, 12.4, 7.3), (8.7, 14.6, 8.7), stick, 'eye')
    t.box((8.8, 14.4, 7.7), (11.6, 14.8, 8.3), head, 'top')
    t.box((9.0, 13.5, 7.45), (11.8, 13.8, 7.55), head_dark, 'seam')
    lash(t, 8, 8, 12.5, 13.7, 0.62, lash_m)
    lash(t, 8, 8, 10.6, 11.4, 0.58, lash_m)
    t.box((8.7, 13.0, 7.4), (10.2, 13.5, 7.5), lash_m, 'strap')
    t.box((8.7, 13.0, 8.5), (10.2, 13.5, 8.6), lash_m, 'strap')
    if not stone:
        nail(t, 10.0, 13.6, 8.0, 1)
        nail(t, 10.0, 13.6, 8.0, -1)
    return t


VANILLA = {}
for _kind, _fn in (('axe', v_axe), ('pickaxe', v_pickaxe), ('shovel', v_shovel), ('hoe', v_hoe)):
    VANILLA['wooden_' + _kind] = (lambda f=_fn, k=_kind: f('narz_wooden_' + k, 'w_light', 'cord', 'w_old', 'w_dark', False))
    VANILLA['stone_' + _kind] = (lambda f=_fn, k=_kind: f('narz_stone_' + k, 'stone', 'cord_d', 'w_dark', 'stone', True))



# ------------------------------------------------------------------ narzędzia Axon
def rust_patch(t, x0, x1, y0, y1, z, side=1, tag='rustp'):
    """Cienka rdzawa łata przyklejona do płaskiej ściany (z = położenie ściany)."""
    if side > 0:
        t.box((x0, y0, z), (x1, y1, z + 0.05), 'rust', tag)
    else:
        t.box((x0, y0, z - 0.05), (x1, y1, z), 'rust', tag)


def a_steel_axe():
    t = Tool('narz_steel_axe')
    handle(t, 13.0, 'steel_d', wrap=('tape', 'tape_g'), wrap_to=4.6, cap='steel', taper=0.0)
    t.box((7.3, 8.8, 7.3), (8.7, 9.6, 8.7), 'tape', 'tape')
    # resor: kilka warstw o różnej długości (jak w prawdziwym resorze piórowym)
    t.box((8.5, 9.5, 7.7), (13.0, 14.5, 7.9), 'leaf', 'leaf1')
    t.box((8.5, 9.7, 7.9), (12.4, 14.3, 8.1), 'leaf', 'leaf2')
    t.box((8.5, 9.9, 8.1), (11.8, 14.1, 8.3), 'leaf', 'leaf3')
    t.box((13.0, 9.0, 7.8), (13.6, 15.0, 8.2), 'edge', 'edge')
    t.box((13.6, 9.6, 7.88), (13.9, 14.4, 8.12), 'edge', 'edge')
    t.box((12.6, 9.0, 7.95), (13.0, 9.5, 8.05), 'edge', 'nick')
    t.box((6.6, 10.5, 7.4), (8.5, 13.5, 8.6), 'steel', 'poll')
    t.box((6.3, 11.0, 7.55), (6.6, 13.0, 8.45), 'steel_d', 'poll')
    t.box((7.1, 12.9, 7.3), (8.7, 13.8, 8.7), 'steel_d', 'clamp')
    t.box((7.1, 9.6, 7.3), (8.7, 10.5, 8.7), 'steel_d', 'clamp')
    for y in (11.0, 12.9):
        t.box((9.2, y, 7.5), (9.8, y + 0.6, 8.5), 'brass', 'rivet')
        t.box((9.3, y + 0.1, 8.5), (9.7, y + 0.5, 8.62), 'brass', 'rivet')
        t.box((9.3, y + 0.1, 7.38), (9.7, y + 0.5, 7.5), 'brass', 'rivet')
    for x in (10.6, 11.6, 12.4):                                    # żebrowanie / ślady kucia na resorze
        t.box((x, 10.4, 7.62), (x + 0.3, 13.6, 7.7), 'steel_d', 'dent')
    rust_patch(t, 9.4, 11.2, 13.0, 14.1, 8.3, 1)
    rust_patch(t, 10.2, 12.2, 9.8, 10.8, 7.7, -1)
    rust_patch(t, 7.5, 8.6, 5.5, 6.5, 8.52, 1, 'rustw')
    return t


def a_steel_pickaxe():
    t = Tool('narz_steel_pickaxe')
    handle(t, 12.0, 'w_old', wrap=('leather', 'leather_d'), wrap_to=4.4)
    # fragment szyny: stopka, środnik, łeb
    t.box((4.0, 11.6, 7.1), (12.0, 12.2, 8.9), 'rail', 'foot')
    t.box((3.0, 12.2, 7.6), (13.0, 13.4, 8.4), 'rail', 'web')
    t.box((2.5, 13.4, 7.2), (13.5, 14.6, 8.8), 'rail', 'headr')
    t.box((3.2, 13.45, 7.0), (12.8, 13.8, 7.2), 'rail', 'lip')
    t.box((3.2, 13.45, 8.8), (12.8, 13.8, 9.0), 'rail', 'lip')
    t.box((1.9, 12.9, 7.6), (2.5, 14.1, 8.4), 'steel', 'tipL')
    t.box((1.6, 13.2, 7.78), (1.9, 13.8, 8.22), 'edge', 'tipL')
    t.box((13.5, 12.9, 7.6), (14.1, 14.1, 8.4), 'steel', 'tipR')
    t.box((14.1, 13.2, 7.78), (14.4, 13.8, 8.22), 'edge', 'tipR')
    t.box((7.2, 12.4, 7.0), (8.8, 13.0, 9.0), 'brass', 'collar')
    t.box((6.8, 11.4, 7.3), (9.2, 11.7, 8.7), 'steel_d', 'strap')
    for x in (4.2, 5.6, 10.4, 11.8):                                # otwory po śrubach podkładek
        t.box((x, 12.5, 7.55), (x + 0.5, 13.1, 7.6), 'black', 'hole')
        t.box((x, 12.5, 8.4), (x + 0.5, 13.1, 8.45), 'black', 'hole')
    for x in (4.0, 9.0, 11.2):
        rust_patch(t, x, x + 1.2, 12.3, 13.3, 8.4, 1)
    rust_patch(t, 5.0, 7.0, 12.4, 13.2, 7.6, -1)
    t.box((3.0, 13.4, 7.5), (13.0, 13.6, 8.5), 'rail', 'seam')
    return t


def a_steel_shovel():
    t = Tool('narz_steel_shovel')
    handle(t, 9.5, 'w_old', wrap=('leather', 'leather_d'), wrap_to=3.5)
    t.box((7.3, 9.0, 7.3), (8.7, 10.5, 8.7), 'paint_olive', 'socket')
    t.box((5.0, 10.5, 7.75), (11.0, 15.0, 8.25), 'paint_olive', 'plate')
    t.box((6.0, 15.0, 7.75), (10.0, 16.0, 8.25), 'paint_olive', 'plate')
    t.box((5.0, 10.5, 8.25), (11.0, 10.9, 8.5), 'paint_olive', 'rim')
    t.box((4.75, 10.9, 7.78), (5.0, 14.6, 8.22), 'steel_l', 'edgeL')
    t.box((11.0, 10.9, 7.78), (11.25, 14.6, 8.22), 'steel_l', 'edgeR')
    t.box((5.5, 15.0, 7.7), (6.0, 15.8, 8.3), 'steel_l', 'edgeTL')
    t.box((10.0, 15.0, 7.7), (10.5, 15.8, 8.3), 'steel_l', 'edgeTR')
    t.box((6.4, 16.0, 7.8), (9.6, 16.3, 8.2), 'edge', 'tip')
    t.box((7.55, 11.0, 7.5), (8.45, 15.2, 7.75), 'paint_olive', 'rib')       # żebro tłoczenia
    t.box((7.55, 11.0, 8.25), (8.45, 15.2, 8.5), 'paint_olive', 'rib')
    t.box((7.6, 10.8, 7.45), (8.4, 11.6, 8.55), 'steel', 'rivbase')
    for x, y in ((6.0, 11.6), (10.0, 11.6), (6.2, 13.6), (9.8, 13.6)):
        t.box((x - 0.2, y - 0.2, 8.5), (x + 0.2, y + 0.2, 8.62), 'steel_l', 'rivet')
        t.box((x - 0.2, y - 0.2, 7.38), (x + 0.2, y + 0.2, 7.5), 'steel_l', 'rivet')
    rust_patch(t, 5.2, 7.0, 10.6, 11.6, 8.5, 1)
    rust_patch(t, 8.6, 10.6, 13.8, 15.2, 7.75, -1)
    rust_patch(t, 9.4, 10.8, 11.0, 12.4, 8.5, 1)
    t.box((7.55, 9.9, 8.7), (8.45, 10.5, 9.0), 'steel_d', 'bolt')
    t.box((7.55, 9.9, 7.0), (8.45, 10.5, 7.3), 'steel_d', 'bolt')
    return t


def a_hardened_axe():
    t = Tool('narz_hardened_axe')
    handle(t, 13.5, 'w_ash', wrap=('leather', 'leather_d'), wrap_to=4.4)
    t.box((8.5, 9.5, 7.65), (12.0, 14.5, 8.35), 'forged', 'head')
    t.box((12.0, 9.0, 7.7), (13.5, 15.0, 8.3), 'tempered', 'band')
    t.box((13.5, 8.5, 7.78), (14.0, 15.5, 8.22), 'edge', 'edge')
    t.box((14.0, 9.0, 7.88), (14.2, 15.0, 8.12), 'edge', 'edge')
    t.box((5.5, 11.0, 7.4), (8.5, 13.5, 8.6), 'forged', 'poll')
    t.box((5.1, 11.4, 7.55), (5.5, 13.1, 8.45), 'steel_d', 'poll')
    t.box((7.6, 13.5, 7.6), (8.4, 14.0, 8.4), 'brass', 'cap')
    t.box((7.3, 9.0, 7.3), (8.7, 9.6, 8.7), 'brass', 'collar')
    t.box((8.5, 14.5, 7.7), (11.5, 14.9, 8.3), 'forged', 'top')
    t.box((8.5, 9.1, 7.7), (11.5, 9.5, 8.3), 'forged', 'bottom')
    t.box((9.0, 10.5, 7.55), (11.6, 13.5, 7.65), 'steel_d', 'fuller')         # wgłębienie (fuller)
    t.box((9.0, 10.5, 8.35), (11.6, 13.5, 8.45), 'steel_d', 'fuller')
    for y in (10.2, 13.0):
        t.box((9.2, y, 7.45), (9.8, y + 0.5, 7.55), 'brass', 'rivet')
        t.box((9.2, y, 8.45), (9.8, y + 0.5, 8.55), 'brass', 'rivet')
    for y in (10.0, 11.4, 12.8, 14.2):                                       # ślady kucia na obuchu
        t.box((5.4, y, 7.35), (7.6, y + 0.35, 7.42), 'steel_d', 'hammer')
    rust_patch(t, 8.8, 10.0, 13.2, 14.4, 8.35, 1)
    rust_patch(t, 6.0, 7.4, 11.0, 12.2, 7.4, -1)
    t.box((13.0, 8.8, 7.95), (13.4, 9.3, 8.05), 'black', 'nick')
    return t


def a_hardened_pickaxe():
    t = Tool('narz_hardened_pickaxe')
    handle(t, 12.0, 'w_ash', wrap=('leather', 'leather_d'), wrap_to=4.4)
    t.box((3.0, 12.0, 7.3), (13.0, 14.0, 8.7), 'forged', 'head')
    t.box((6.5, 11.5, 7.1), (9.5, 14.5, 8.9), 'steel', 'boss')
    t.box((2.2, 12.4, 7.5), (3.0, 13.6, 8.5), 'tempered', 'tipL')
    t.box((13.0, 12.4, 7.5), (13.8, 13.6, 8.5), 'tempered', 'tipR')
    t.box((1.9, 12.7, 7.7), (2.2, 13.3, 8.3), 'gem', 'gemL')
    t.box((13.8, 12.7, 7.7), (14.1, 13.3, 8.3), 'gem', 'gemR')
    t.box((3.4, 14.0, 7.5), (12.6, 14.25, 8.5), 'forged', 'crown')
    t.box((3.4, 11.8, 7.5), (12.6, 12.0, 8.5), 'forged', 'under')
    for x in (4.2, 5.2, 10.8, 11.8):
        t.box((x, 12.5, 8.7), (x + 0.4, 13.5, 8.78), 'steel_d', 'groove')
        t.box((x, 12.5, 7.22), (x + 0.4, 13.5, 7.3), 'steel_d', 'groove')
    for x, y in ((7.0, 12.0), (9.0, 12.0), (7.0, 14.0), (9.0, 14.0)):
        t.box((x - 0.2, y - 0.2, 8.9), (x + 0.2, y + 0.2, 9.02), 'brass', 'rivet')
        t.box((x - 0.2, y - 0.2, 6.98), (x + 0.2, y + 0.2, 7.1), 'brass', 'rivet')
    t.box((7.2, 11.2, 7.3), (8.8, 11.6, 8.7), 'brass', 'collar')
    rust_patch(t, 3.5, 5.6, 12.2, 13.2, 8.7, 1)
    rust_patch(t, 10.4, 12.4, 12.4, 13.6, 7.3, -1)
    return t


AXON = {'steel_axe': a_steel_axe, 'steel_pickaxe': a_steel_pickaxe, 'steel_shovel': a_steel_shovel,
        'hardened_axe': a_hardened_axe, 'hardened_pickaxe': a_hardened_pickaxe}



# ------------------------------------------------------------------ bronie białe
import gen_bronie_biale as GB

MAT_B = {'stal': 'steel', 'stal_j': 'edge', 'stal_c': 'steel_d', 'czern': 'black', 'czern_j': 'black_e',
         'tasma': 'tape_g', 'drewno': 'w_old', 'drewno_c': 'w_dark', 'skora': 'leather', 'skora_c': 'leather_d',
         'rdza': 'rust', 'szmata': 'cloth', 'mosiadz': 'brass', 'farba_r': 'paint_red', 'oliwka': 'paint_olive',
         'g10': 'g10', 'guma': 'rubber', 'drut': 'wire'}


class Bron(Tool):
    """Adapter: stare funkcje z gen_bronie_biale.py (b(f, t, materiał), x i z wokół 0) na nowy silnik."""

    def __init__(self, name):
        super().__init__(name)

    def b(self, f, t, m, skip=(), rot=None):
        if rot:         # pojedyncze obroty wokół x (końcówka taśmy) pomijamy: nowy silnik ma obrót tylko wokół w
            return
        self.box((f[0] + 8, f[1], f[2] + 8), (t[0] + 8, t[1], t[2] + 8), MAT_B.get(m, m), m)

    def r(self, f, t, m, tag=None):                     # prostopadłościan w nowych nazwach materiałów, x i z wokół 0
        self.box((f[0] + 8, f[1], f[2] + 8), (t[0] + 8, t[1], t[2] + 8), m, tag)

    def pins(self, ys, x, half_z, mat='brass', r=0.2):
        for y in ys:
            for s in (-1, 1):
                self.r((x - r, y - r, s * half_z - (0 if s < 0 else 0) - (0.1 if s < 0 else 0)),
                       (x + r, y + r, s * half_z + (0.1 if s > 0 else 0)), mat, 'pin')

    def patch(self, x0, x1, y0, y1, half_z, side=1):
        if side >= 0:
            self.r((x0, y0, half_z), (x1, y1, half_z + 0.05), 'rust', 'rustp')
        else:
            self.r((x0, y0, -half_z - 0.05), (x1, y1, -half_z), 'rust', 'rustp')

    def nicks(self, x, ys, half_z, mat='black'):
        for y in ys:
            self.r((x, y, -half_z - 0.01), (x + 0.22, y + 0.35, half_z + 0.01), mat, 'nick')


def x_rurka(w):
    GB.rurka(w)
    w.r((0.52, 1.0, -0.12), (0.7, 27.4, 0.12), 'steel_d', 'weld')           # szew spawalniczy
    for y in (3.0, 7.5):                                                    # łatki rdzy
        w.patch(-0.55, 0.1, y, y + 1.6, 0.6, 1)
        w.patch(0.0, 0.55, y + 4.0, y + 5.4, 0.6, -1)
    for y in (13.0, 19.0, 24.5):
        w.patch(-0.62, 0.62, y + 1.0, y + 1.6, 0.62, 1)
    w.r((-0.82, 9.0, -0.82), (0.82, 9.5, 0.82), 'steel_l', 'clamp')         # opaska zaciskowa
    w.r((0.8, 9.05, -0.2), (1.1, 9.45, 0.2), 'steel_d', 'screw')
    for sx in (-1, 1):                                                      # śruby na zaślepce
        for sz in (-1, 1):
            w.r((sx * 0.45 - 0.12, -0.12, sz * 0.45 - 0.12), (sx * 0.45 + 0.12, 0.0, sz * 0.45 + 0.12), 'steel_d', 'bolt')
    for y in (21.0, 25.0):
        w.r((-0.8, y, -0.8), (0.8, y + 0.28, 0.8), 'steel_d', 'band')
    w.r((-0.22, 28.8, -0.22), (0.22, 29.2, 0.22), 'black', 'plug')


def x_kij(w):
    GB.kij(w)
    for i, y in enumerate((3.0, 9.0, 12.5, 14.5, 19.0, 22.5, 26.0)):         # odpryski kory i drzazgi
        s = 1 if i % 2 else -1
        r = 0.55 + (y - 1) / 1.95 * 0.055
        w.r((s * r - (0.0 if s > 0 else 0.35), y, -0.2), (s * r + (0.35 if s > 0 else 0.0), y + 0.9, 0.2), 'w_light', 'splinter')
    for y in (10.0, 20.5):                                                  # pęknięcia
        w.r((-0.1, y, 0.5), (0.1, y + 3.2, 0.9), 'black', 'crack')
    for y in (7.4, 7.9, 8.4, 8.9, 9.4):                                     # sznur pod nasadą kolców
        w.r((-1.0, y, -1.0), (1.0, y + 0.3, 1.0), 'cord' if int(y * 10) % 2 else 'cord_d', 'cord')
    w.r((-0.18, 0.6, 0.55), (0.18, 1.0, 0.95), 'steel_d', 'staple')
    w.patch(0.3, 1.2, 16.5, 18.0, 1.0, 1)


def x_maczeta(w):
    GB.maczeta(w)
    w.r((-0.55, 9.0, -0.18), (0.55, 24.0, 0.18), 'steel_d', 'fuller')       # zbrocze po obu stronach
    for y in (1.2, 3.2, 5.2):                                               # nity rękojeści
        w.r((-0.15, y, -0.62), (0.15, y + 0.3, 0.62), 'brass', 'rivet')
        w.r((-0.3, y - 0.05, 0.62), (0.3, y + 0.35, 0.72), 'brass', 'rivet')
        w.r((-0.3, y - 0.05, -0.72), (0.3, y + 0.35, -0.62), 'brass', 'rivet')
    w.r((-0.85, 0.0, -0.6), (0.85, 0.5, 0.6), 'black', 'pommel')
    w.nicks(1.18, (12.0, 15.5, 19.0, 22.5), 0.15)
    w.patch(-1.1, 0.4, 14.0, 16.5, 0.15, 1)
    w.patch(-0.4, 1.0, 9.0, 10.4, 0.15, -1)
    w.patch(-1.0, 0.6, 19.5, 21.8, 0.15, -1)
    w.r((-1.3, 25.4, -0.2), (-0.7, 26.2, 0.2), 'steel_d', 'tipspine')
    w.r((-1.2, 7.2, -0.4), (1.2, 7.5, 0.4), 'tape', 'guardtape')


def x_toporek(w):
    GB.toporek(w)
    w.r((2.6, 17.4, -0.25), (4.2, 19.4, 0.25), 'steel', 'beard')            # broda
    w.r((4.2, 17.8, -0.15), (4.8, 19.0, 0.15), 'edge', 'beardedge')
    w.r((4.6, 18.8, -0.12), (4.95, 25.2, 0.12), 'edge', 'bevel')
    w.r((-0.3, 24.3, -0.5), (0.3, 24.9, 0.5), 'w_dark', 'wedge')            # klin w trzonku
    w.r((-0.78, 8.0, -0.68), (0.78, 8.7, 0.68), 'steel_d', 'ferrule')       # tulejka
    for y in (21.2, 22.8):
        w.r((-0.3, y, -0.72), (0.3, y + 0.35, 0.72), 'steel_l', 'rivet')
    w.r((-2.2, 21.1, -0.7), (-1.9, 23.2, 0.7), 'steel_d', 'poll')
    w.nicks(4.5, (20.5, 22.4, 24.2), 0.2)
    w.patch(1.4, 3.4, 20.6, 23.0, 0.3, 1)
    w.patch(-1.1, 0.8, 21.0, 23.6, 0.7, -1)
    w.r((-0.66, 12.0, -0.52), (0.66, 12.35, 0.52), 'cord_d', 'grip')
    w.r((-0.66, 14.0, -0.52), (0.66, 14.35, 0.52), 'cord_d', 'grip')


def x_noz(w):
    GB.noz(w)
    for y in (1.8, 3.4, 5.0):
        w.r((-0.1, y, -0.62), (0.1, y + 0.35, 0.62), 'steel_l', 'pin')
    w.r((-0.55, 8.0, -0.2), (0.45, 14.8, 0.2), 'steel_d', 'fuller')
    for y in (9.2, 10.2, 11.2, 12.2, 13.2):                                 # ząbki na grzbiecie
        w.r((-1.05, y, -0.12), (-0.9, y + 0.4, 0.12), 'steel_d', 'tooth')
    w.r((-0.3, 0.1, -0.5), (0.3, 0.5, -0.4), 'black', 'lanyard')
    w.r((-1.85, 6.3, -0.4), (-1.6, 7.1, 0.4), 'brass', 'quillon')
    w.r((1.6, 6.3, -0.4), (1.85, 7.1, 0.4), 'brass', 'quillon')
    w.nicks(0.78, (10.0, 12.6), 0.17)
    w.patch(-0.7, 0.3, 9.0, 11.5, 0.2, 1)
    w.patch(-0.5, 0.5, 13.0, 14.6, 0.2, -1)


def x_lom(w):
    GB.lom(w)
    for y in (3.0, 4.2, 5.4):
        w.r((-0.52, y, -0.52), (0.52, y + 0.35, 0.52), 'rubber', 'knurl')
    for y in (8.0, 14.5):
        w.r((-0.48, y, -0.48), (0.48, y + 1.0, 0.48), 'steel_d', 'chip')
    w.r((-0.9, 23.65, -0.15), (-0.6, 24.0, 0.15), 'black', 'clawgap')
    w.r((-0.14, 24.3, -0.5), (0.14, 24.6, 0.5), 'steel_d', 'weld')
    w.r((-0.2, 22.2, -0.5), (0.5, 22.8, 0.5), 'paint_red', 'bump')
    w.patch(-0.4, 0.4, 9.0, 12.0, 0.46, 1)
    w.patch(-0.4, 0.4, 15.0, 17.5, 0.46, -1)
    w.patch(0.0, 2.4, 21.2, 21.9, 0.46, 1)
    w.r((-0.82, 1.2, -0.3), (0.82, 1.5, 0.3), 'steel_d', 'neck')


def x_kabar(w):
    GB.kabar(w)
    w.r((-0.5, 8.6, -0.18), (0.4, 15.0, 0.18), 'steel_d', 'fuller')
    w.r((-0.55, 16.4, -0.17), (0.0, 17.2, 0.17), 'black_e', 'tipbevel')
    w.r((-0.3, -0.35, -0.3), (0.3, 0.0, 0.3), 'steel_d', 'pommelnut')        # nakrętka głowicy
    for z in (-0.52, 0.52):
        w.r((-1.5, 6.5, z - (0.1 if z > 0 else 0)), (-1.0, 6.9, z + (0.0 if z > 0 else 0.1)), 'steel', 'guard')
    w.r((-1.6, 6.5, -0.6), (-1.5, 7.0, 0.6), 'steel_d', 'guardend')
    w.r((1.5, 6.5, -0.6), (1.6, 7.0, 0.6), 'steel_d', 'guardend')
    w.nicks(0.8, (9.5, 13.0), 0.17, 'steel_d')
    w.patch(-0.7, 0.4, 10.0, 11.4, 0.17, 1)
    w.patch(0.0, 0.7, 13.5, 14.8, 0.17, -1)
    w.r((-0.66, 2.0, -0.5), (0.66, 2.2, 0.5), 'black', 'washer')
    w.r((-0.66, 4.0, -0.5), (0.66, 4.2, 0.5), 'black', 'washer')


def x_saperka(w):
    GB.saperka(w)
    y = 17.2
    while y < 21.3:                                                         # ząbki piły z jednej strony
        w.r((2.65, y, -0.2), (3.0, y + 0.45, 0.2), 'steel_l', 'tooth')
        y += 0.9
    w.r((-0.3, 16.9, -0.38), (0.3, 21.2, 0.38), 'paint_olive', 'rib')
    w.r((-1.6, 16.6, -0.26), (-1.1, 21.4, 0.26), 'paint_olive', 'fold')      # zagięcie krawędzi
    w.r((1.1, 16.6, -0.26), (1.6, 21.4, 0.26), 'paint_olive', 'fold')
    w.r((-0.55, 15.6, -1.1), (0.55, 16.4, -0.7), 'steel_l', 'wing')          # nakrętka motylkowa
    w.r((-1.0, 15.7, -1.5), (1.0, 16.2, -1.1), 'steel_l', 'wing')
    for x, yy in ((-2.0, 18.0), (2.0, 18.0), (-1.6, 20.6), (1.6, 20.6)):
        w.r((x - 0.2, yy - 0.2, 0.2), (x + 0.2, yy + 0.2, 0.32), 'steel_d', 'rivet')
    for y in (4.0, 5.2):
        w.r((-0.55, y, -0.55), (0.55, y + 0.3, 0.55), 'steel_d', 'ring')
    w.patch(-2.2, -0.6, 17.0, 19.0, 0.2, 1)
    w.patch(0.8, 2.4, 19.6, 21.6, 0.2, -1)
    w.patch(-0.5, 0.5, 9.0, 10.2, 0.52, 1)


def x_tomahawk(w):
    GB.tomahawk(w)
    for y in (2.0, 4.2, 6.4, 8.2):                                          # śruby okładziny
        w.r((-0.2, y, -0.56), (0.2, y + 0.4, 0.56), 'steel_l', 'screw')
        w.r((-0.3, y - 0.05, 0.56), (0.3, y + 0.45, 0.66), 'steel_l', 'screw')
        w.r((-0.3, y - 0.05, -0.66), (0.3, y + 0.45, -0.56), 'steel_l', 'screw')
    w.r((-0.5, 0.1, -0.5), (0.5, 0.4, -0.3), 'black', 'lanyard')
    w.r((3.0, 18.6, -0.12), (4.5, 23.4, 0.12), 'black_e', 'bevel')
    w.r((-3.4, 20.2, -0.1), (-2.8, 21.0, 0.1), 'black_e', 'spikebev')
    w.r((-1.0, 19.5, -0.62), (-0.7, 21.7, 0.62), 'steel_d', 'collar')
    w.nicks(4.0, (19.6, 21.4, 22.6), 0.17, 'steel_d')
    w.patch(-0.8, 0.8, 20.0, 21.5, 0.62, 1)
    w.patch(1.2, 2.8, 19.0, 21.4, 0.31, -1)
    w.r((-0.66, 12.0, -0.52), (0.66, 12.3, 0.52), 'steel_d', 'ring')


def x_palka(w):
    GB.palka(w)
    for y in (9.0, 15.6, 21.6):                                             # gwintowane złącza
        w.r((-0.62, y, -0.62), (0.62, y + 0.4, 0.62), 'steel_d', 'joint')
    w.r((-0.55, 27.5, -0.55), (0.55, 28.4, 0.55), 'steel_l', 'ball')
    for y in (10.0, 12.0, 17.0, 19.0, 23.0):
        w.r((-0.05, y, -0.62), (0.1, y + 1.0, 0.62), 'steel_l', 'glint')
    for y in (2.4, 3.6, 4.8, 6.0):
        w.r((-0.78, y, -0.78), (0.78, y + 0.22, 0.78), 'black', 'knurl')
    w.r((0.5, 0.2, -0.3), (1.0, 0.9, 0.3), 'leather_d', 'strap')           # pętla na nadgarstek
    w.r((0.9, -0.8, -0.3), (1.3, 0.9, 0.3), 'leather_d', 'strap')
    w.patch(-0.4, 0.4, 10.0, 11.4, 0.52, 1)
    w.patch(-0.3, 0.3, 17.5, 18.6, 0.42, -1)
    w.patch(-0.3, 0.3, 23.0, 24.0, 0.32, 1)


BRONIE = {'rurka': (GB.rurka, x_rurka), 'kij': (GB.kij, x_kij), 'maczeta': (GB.maczeta, x_maczeta),
          'toporek': (GB.toporek, x_toporek), 'noz': (GB.noz, x_noz), 'lom': (GB.lom, x_lom),
          'kabar': (GB.kabar, x_kabar), 'saperka': (GB.saperka, x_saperka), 'tomahawk': (GB.tomahawk, x_tomahawk),
          'palka': (GB.palka, x_palka)}


def render_bron(name, out=OUT):
    w = Bron(name)
    BRONIE[name][1](w)          # x_<nazwa> woła też oryginalną funkcję z gen_bronie_biale.py
    model, img, dens, nf = w.save('axon:item/' + name, GB.DISPLAY, tool_rot=False, density=10.0)
    model['credit'] = 'AXON bronie biale - generated by gen_narzedzia.py (procedural, original)'
    json.dump(model, open(os.path.join(out, name + '.json'), 'w'), indent=1)
    Image.fromarray(img, 'RGBA').save(os.path.join(out, name + '.png'))
    json.dump({'model': {'type': 'minecraft:model', 'model': 'axon:block/' + name}},
              open(os.path.join(out, name + '_item.json'), 'w'), indent=1)
    print(name, 'elements', len(model['elements']), 'faces', nf, 'density', dens, flush=True)


def render_tool(name, fn, out=OUT):
    t = fn()
    model, img, dens, nf = t.save('axon:item/' + name, HANDHELD)
    json.dump(model, open(os.path.join(out, name + '.json'), 'w'), indent=1)
    Image.fromarray(img, 'RGBA').save(os.path.join(out, name + '.png'))
    print(name, 'elements', len(model['elements']), 'faces', nf, 'density', dens, flush=True)



def wszystkie():
    """Nazwy wszystkich modeli z tego pliku: (nazwa pliku w build/, ścieżka modelu w zipie, ścieżka tekstury)."""
    out = []
    for k in VANILLA:
        out.append(('narz_' + k, 'assets/minecraft/models/item/%s.json' % k, 'assets/axon/textures/item/narz_%s.png' % k))
    for k in AXON:
        out.append(('narz_' + k, 'assets/axon/models/block/%s.json' % k, 'assets/axon/textures/item/narz_%s.png' % k))
    for k in BRONIE:
        out.append((k, 'assets/axon/models/block/%s.json' % k, 'assets/axon/textures/item/%s.png' % k))
    return out


def pliki(src=None):
    """Ścieżka w zipie -> bajty, z build/ (wynik tego skryptu) albo z podanego katalogu."""
    src = src or OUT
    files = {}
    for name, mpath, tpath in wszystkie():
        files[mpath] = open(os.path.join(src, name + '.json'), 'rb').read()
        files[tpath] = open(os.path.join(src, name + '.png'), 'rb').read()
    return files


def main(want=()):
    os.makedirs(OUT, exist_ok=True)
    for key, fn in VANILLA.items():
        if not want or key in want:
            render_tool('narz_' + key, fn)
    for key, fn in AXON.items():
        if not want or key in want:
            render_tool('narz_' + key, fn)
    for key in BRONIE:
        if not want or key in want:
            render_bron(key)


if __name__ == '__main__':
    main(sys.argv[1:])
