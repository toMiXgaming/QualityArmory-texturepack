#!/usr/bin/env python3
"""AXON gun models for QualityArmory (Minecraft Java 1.21.4).

Builds three Blockbench-style item models (AK-47, M4A1-S, Remington 870) out of
many cuboids, auto-packs a per-gun 128x128 texture atlas and paints it
procedurally (wood grain, worn metal edges, ambient occlusion in creases,
rivets, ports, rail teeth, checkering, engraving ...).

Guns are authored in "gun space": u = metres-ish units from the muzzle
backwards, v = height above the bore axis, w = lateral (+ = gun's right side).
One gun unit ~ 21 mm.  Gun space is then mapped into the exact frame of
QualityArmory's own model of the same gun (muzzle end, bore height, length,
lateral centre), so QA's tuned display transforms keep working.

Run:  python3 gen.py  -> writes into ./build/<gun>.json + ./build/<gun>.png
"""
import json, math, os, zlib
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'build')
TEX = 128
CUR_DENS = 4.0
DENSITY = 4.0          # texels per gun unit (tries lower if the atlas is full)

# ------------------------------------------------------------------ helpers
FACES = ['north', 'south', 'east', 'west', 'up', 'down']
FACE_N = {'north': (0, 0, -1), 'south': (0, 0, 1), 'east': (1, 0, 0),
          'west': (-1, 0, 0), 'up': (0, 1, 0), 'down': (0, -1, 0)}


def face_corners(f, t, face):
    x1, y1, z1 = f
    x2, y2, z2 = t
    return {
        'north': [(x2, y2, z1), (x1, y2, z1), (x1, y1, z1), (x2, y1, z1)],
        'south': [(x1, y2, z2), (x2, y2, z2), (x2, y1, z2), (x1, y1, z2)],
        'east':  [(x2, y2, z2), (x2, y2, z1), (x2, y1, z1), (x2, y1, z2)],
        'west':  [(x1, y2, z1), (x1, y2, z2), (x1, y1, z2), (x1, y1, z1)],
        'up':    [(x1, y2, z1), (x2, y2, z1), (x2, y2, z2), (x1, y2, z2)],
        'down':  [(x1, y1, z2), (x2, y1, z2), (x2, y1, z1), (x1, y1, z1)],
    }[face]


def rot_w(theta):
    """Rotation about gun +w axis (gun space vectors are (w, v, u))."""
    a = math.radians(theta)
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


# ------------------------------------------------------------------ noise
def _hash(ix, iy, iz, seed):
    h = (ix * 73856093) ^ (iy * 19349663) ^ (iz * 83492791) ^ (seed * 974634347)
    h = h & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    h = h ^ (h >> 16)
    return (h & 0xFFFFFF) / float(0xFFFFFF)


def vnoise(P, seed=0):
    Pf = np.floor(P)
    f = P - Pf
    i = Pf.astype(np.int64)
    s = f * f * (3 - 2 * f)
    res = np.zeros(len(P))
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                h = _hash(i[:, 0] + dx, i[:, 1] + dy, i[:, 2] + dz, seed)
                wgt = ((s[:, 0] if dx else 1 - s[:, 0]) * (s[:, 1] if dy else 1 - s[:, 1]) *
                       (s[:, 2] if dz else 1 - s[:, 2]))
                res += h * wgt
    return res


def fbm(P, octaves=3, seed=0):
    tot, amp, norm = 0, 1.0, 0
    for o in range(octaves):
        tot = tot + amp * vnoise(P * (2 ** o), seed + 31 * o)
        norm += amp
        amp *= 0.5
    return tot / norm


def white(P, seed=0, q=8.0):
    i = np.floor(P * q).astype(np.int64)
    return _hash(i[:, 0], i[:, 1], i[:, 2], seed)


# ------------------------------------------------------------------ model
class El:
    def __init__(self, name, lo, hi, mat, rot=None, **params):
        self.name = name
        self.lo = np.array(lo, float)   # gun space (w, v, u)
        self.hi = np.array(hi, float)
        assert np.all(self.hi > self.lo), name
        self.mat = mat
        self.rot = rot                  # (theta, pivot (w,v,u)) or None
        self.p = params
        self.regions = {}
        if rot:
            self.R = rot_w(rot[0])
            self.o = np.array(rot[1], float)
        else:
            self.R = None

    def to_world(self, P):        # gun local -> gun (rotated)
        return P if self.R is None else (P - self.o) @ self.R.T + self.o

    def to_local(self, P):
        return P if self.R is None else (P - self.o) @ self.R + self.o

    def inside(self, P, eps=1e-3):
        L = self.to_local(P)
        return np.all((L > self.lo + eps) & (L < self.hi - eps), axis=1)


class Gun:
    def __init__(self, name, qa):
        self.name = name
        self.els = []
        self.decals = []
        self.qa = qa      # dict(s, k, kw, Xm, Yb, Zc)
        self.sight = None  # (u_rear, v_eye, u_front)
        self.grip = None

    # authoring helpers (gun units)
    def b(self, name, u, v, w, mat, rot=None, dw=0.0, **p):
        if isinstance(w, (int, float)):
            w = (dw - w, dw + w)
        lo = (w[0], v[0], u[0])
        hi = (w[1], v[1], u[1])
        r = None
        if rot:
            th, (pu, pv) = rot
            r = (th, (0.0, pv, pu))
        e = El(name, lo, hi, mat, r, **p)
        self.els.append(e)
        return e

    def cyl(self, name, u, vc, r, mat, dw=0.0, k=0.68, rot=None, **p):
        e1 = self.b(name + '_a', u, (vc - r * k, vc + r * k), r, mat, rot, dw, **p)
        e2 = self.b(name + '_b', (u[0] + 0.03, u[1] - 0.03), (vc - r, vc + r), r * k, mat, rot, dw, **p)
        return e1, e2

    def slope(self, name, pivot, theta, t, u_end, top_v, w, mat):
        """Sloped underside (stock): a 22.5deg slab plus hidden stair fillers above it.
        Returns the v of the slab's lowest back point (toe)."""
        up, vp = pivot
        ta, co, si = (math.tan(math.radians(theta)), math.cos(math.radians(theta)),
                      math.sin(math.radians(theta)))
        L = (u_end - up) / co
        self.b(name + '_slab', (up, up + L), (vp - t, vp), w, mat, rot=(theta, (up, vp)))
        vt = lambda u: vp - (u - up) * ta
        dmax = 0.8 * (t / co) / ta
        n = max(1, int(math.ceil((u_end - up) / dmax)))
        d = (u_end - up) / n
        top = top_v
        for i in range(n):
            ua = up + i * d
            bot = vt(ua + d) - 0.03
            if bot < top:
                self.b('%s_fill%d' % (name, i), (ua, u_end), (bot, top), w - 0.012, mat)
                top = bot
        ubb = u_end - t * si
        vb = vp - t * co - (u_end - up) * ta
        self.b(name + '_toe', (ubb - 0.04, u_end), (vb, vt(u_end) + 0.02), w - 0.012, mat)
        return vb

    def dec(self, fn):
        self.decals.append(fn)

    # gun space -> QA model frame
    def to_mc(self, P):
        q = self.qa
        P = np.atleast_2d(P)
        X = q['Xm'] + q['s'] * q['k'] * P[:, 2]
        Y = q['Yb'] + q['k'] * P[:, 1]
        Z = q['Zc'] - q['s'] * q['kw'] * P[:, 0]
        return np.stack([X, Y, Z], 1)

    def from_mc(self, P):
        q = self.qa
        P = np.atleast_2d(P)
        u = (P[:, 0] - q['Xm']) / (q['s'] * q['k'])
        v = (P[:, 1] - q['Yb']) / q['k']
        w = (q['Zc'] - P[:, 2]) / (q['s'] * q['kw'])
        return np.stack([w, v, u], 1)

    def mc_box(self, e):
        c = self.to_mc(np.array([e.lo, e.hi]))
        return c.min(0), c.max(0)

    def gun_dir(self, n_mc):
        """MC-frame direction -> gun-space direction (w, v, u)."""
        s = self.qa['s']
        return np.array([-s * n_mc[2], n_mc[1], s * n_mc[0]], float)


SIDE_OF = {(0, 1): 'T', (0, -1): 'B', (1, 1): 'K', (1, -1): 'F', (2, 1): 'R', (2, -1): 'L'}


def side_name(ng):
    # ng = (w, v, u)
    i = int(np.argmax(np.abs(ng)))
    sgn = 1 if ng[i] > 0 else -1
    return {0: {1: 'R', -1: 'L'}, 1: {1: 'T', -1: 'B'}, 2: {1: 'K', -1: 'F'}}[i][sgn]


# ------------------------------------------------------------------ materials
MATS = {
    'blued':    dict(kind='metal', base=(54, 56, 62), wear=(128, 132, 140), var=0.10, edge=0.75),
    'steel':    dict(kind='metal', base=(64, 65, 69), wear=(146, 148, 152), var=0.12, edge=0.8),
    'parts':    dict(kind='metal', base=(84, 86, 91), wear=(170, 172, 176), var=0.10, edge=0.7),
    'black':    dict(kind='metal', base=(60, 62, 67), wear=(134, 137, 143), var=0.07, edge=0.85),
    'rail':     dict(kind='metal', base=(72, 74, 79), wear=(150, 152, 158), var=0.07, edge=0.9),
    'magsteel': dict(kind='metal', base=(42, 43, 46), wear=(116, 118, 122), var=0.12, edge=0.8),
    'supp':     dict(kind='supp', base=(72, 72, 70), wear=(130, 130, 128), var=0.08, edge=0.6),
    'polymer':  dict(kind='poly', base=(50, 50, 50), wear=(92, 92, 94), var=0.07, edge=0.65),
    'tan':      dict(kind='poly', base=(150, 128, 92), wear=(190, 170, 130), var=0.06, edge=0.5),
    'rubber':   dict(kind='poly', base=(26, 26, 27), wear=(48, 48, 50), var=0.05, edge=0.4),
    'bakelite': dict(kind='bakelite', base=(126, 56, 30), dark=(74, 30, 15), wear=(160, 92, 58), edge=0.5),
    'wood_ak':  dict(kind='wood', light=(184, 98, 50), dark=(102, 44, 20), wear=(206, 136, 86), edge=0.45),
    'wood_870': dict(kind='wood', light=(150, 98, 52), dark=(70, 40, 19), wear=(186, 136, 88), edge=0.45),
    'brass':    dict(kind='metal', base=(204, 166, 76), wear=(244, 220, 146), var=0.06, edge=0.6),
    'spacer':   dict(kind='flat', base=(214, 210, 200), wear=(230, 228, 220), edge=0.0),
    'shell':    dict(kind='shell', base=(156, 30, 26), wear=(200, 70, 60), edge=0.3),
    'band':     dict(kind='poly', base=(30, 30, 31), wear=(55, 55, 57), var=0.05, edge=0.3),
}


def base_color(mat, G, side, el):
    m = MATS[mat]
    w, v, u = G[:, 0], G[:, 1], G[:, 2]
    k = m['kind']
    seed = zlib.crc32(el.name.encode()) & 0xFFFF
    if k in ('metal', 'supp', 'poly', 'flat'):
        base = np.array(m['base'], float)
        var = m.get('var', 0.05)
        mott = fbm(G * np.array([0.9, 0.9, 0.35]), 3, seed) - 0.5
        fine = white(G, seed + 7, 4.0) - 0.5
        col = base[None] * (1 + var * 0.9 * mott[:, None] + var * 0.35 * fine[:, None])
        if k == 'poly':
            st = white(G, seed + 3, 8.0)
            col *= (0.92 + 0.12 * st)[:, None]
        if k == 'supp':
            # heat tint toward the muzzle end + faint straw/blue band
            heat = np.clip(1 - (u - el.lo[2]) / max(0.1, el.hi[2] - el.lo[2]), 0, 1) ** 2
            tint = np.array([1.10, 0.98, 0.92])
            col = col * (1 + (tint - 1)[None] * heat[:, None])
        return col
    if k == 'bakelite':
        a = np.array(m['base'], float)
        d = np.array(m['dark'], float)
        sw = fbm(G * np.array([2.2, 1.4, 2.2]) + fbm(G * 0.8, 2, seed)[:, None] * 2.0, 3, seed + 1)
        t = np.clip((sw - 0.35) * 1.8, 0, 1)
        return a[None] * (1 - t[:, None]) + d[None] * t[:, None]
    if k == 'wood':
        L = np.array(m['light'], float)
        D = np.array(m['dark'], float)
        warp = fbm(G * np.array([0.35, 0.35, 0.12]), 3, seed) * 2.4
        r = np.sqrt(((w - 9.0) * 0.85) ** 2 + (v - 7.5) ** 2) + warp
        ring = 0.5 + 0.5 * np.sin(r * 2 * math.pi * 1.05)
        ring = ring ** 2.2
        fib = fbm(G * np.array([7.0, 7.0, 0.45]), 2, seed + 5)
        t = np.clip(0.18 + 0.55 * ring + 0.45 * (fib - 0.5), 0, 1)
        col = L[None] * (1 - t[:, None]) + D[None] * t[:, None]
        pores = white(G * np.array([1, 1, 0.25]), seed + 9, 4.0) > 0.93
        col[pores] *= 0.85
        return col
    if k == 'shell':
        red = np.array(m['base'], float)
        brass = np.array([206, 170, 82], float)
        head = el.p.get('head', 0.6)
        # shells stand upright; brass head at the bottom (low v)
        col = np.repeat(red[None], len(G), 0)
        hb = v < el.lo[1] + head
        col[hb] = brass
        rib = (np.floor((v - el.lo[1]) * 4) % 2 == 0) & ~hb
        col[rib] *= 0.9
        col[np.abs(v - (el.lo[1] + head)) < 0.12] *= 0.7
        return col * (1 + 0.06 * (white(G, 3, 4.0)[:, None] - 0.5))
    raise ValueError(mat)


# ------------------------------------------------------------------ decal helpers
def _sel(ctx, sides, els):
    if sides and ctx.side not in sides:
        return None
    if els is not None:
        nm = ctx.el.name
        if not any(nm == e or (e.endswith('*') and nm.startswith(e[:-1])) for e in els):
            return None
    return True


def ab(ctx):
    """2D face coordinates (a: along gun / lateral, b: up / lateral) in gun units."""
    w, v, u = ctx.G[:, 0], ctx.G[:, 1], ctx.G[:, 2]
    if ctx.side in 'RL':
        return u, v
    if ctx.side in 'TB':
        return u, w
    return w, v


def recess(sides, a, b, els=None, col=(17, 17, 19), inner=None, lip=True):
    def fn(ctx):
        if not _sel(ctx, sides, els):
            return
        A, B = ab(ctx)
        m = (A > a[0]) & (A < a[1]) & (B > b[0]) & (B < b[1])
        if not m.any():
            return
        c = np.array(col, float)
        ctx.col[m] = c
        if inner:
            inner(ctx, m, A, B)
        top = m & (B > b[1] - 0.28)
        ctx.col[top] *= 0.6
        if lip:
            # lighter lip just outside lower edge
            l2 = (A > a[0]) & (A < a[1]) & (B < b[0]) & (B > b[0] - 0.26)
            ctx.col[l2] = ctx.col[l2] * 1.35 + 8
            l3 = (A > a[0]) & (A < a[1]) & (B > b[1]) & (B < b[1] + 0.26)
            ctx.col[l3] *= 0.7
        ctx.flat[m] = True
    return fn


def paint(sides, a, b, col, els=None, alpha=1.0, mul=False):
    def fn(ctx):
        if not _sel(ctx, sides, els):
            return
        A, B = ab(ctx)
        m = (A > a[0]) & (A < a[1]) & (B > b[0]) & (B < b[1])
        if mul:
            ctx.col[m] *= np.array(col, float)[None]
        else:
            ctx.col[m] = ctx.col[m] * (1 - alpha) + np.array(col, float)[None] * alpha
    return fn


def oval(sides, a, b, ra, rb, els=None, col=(14, 14, 16)):
    def fn(ctx):
        if not _sel(ctx, sides, els):
            return
        A, B = ab(ctx)
        d = ((A - a) / ra) ** 2 + ((B - b) / rb) ** 2
        m = d < 1
        ctx.col[m] = np.array(col, float)
        sh = m & (B > b + rb * 0.25)
        ctx.col[sh] *= 0.55
        rim = (d >= 1) & (d < 1.9) & (B < b)
        ctx.col[rim] = ctx.col[rim] * 1.25 + 6
        ctx.flat[m] = True
    return fn


def rivet(sides, a, b, r=0.2, els=None, cols=((150, 152, 158), (22, 22, 24))):
    def fn(ctx):
        if not _sel(ctx, sides, els):
            return
        A, B = ab(ctx)
        d = np.sqrt((A - a) ** 2 + (B - b) ** 2)
        m = d < r
        ctx.col[m] = ctx.col[m] * 0.6 + np.array(cols[0], float) * 0.4
        hl = m & (B > b) & (A < a + 0.05)
        ctx.col[hl] *= 1.2
        sh = (d >= r) & (d < r + 0.24) & (B < b)
        ctx.col[sh] *= 0.55
    return fn


def stripes(sides, axis, period, width, a=(-99, 99), b=(-99, 99), els=None, mul=0.55, add=0, offset=0.0):
    def fn(ctx):
        if not _sel(ctx, sides, els):
            return
        A, B = ab(ctx)
        X = A if axis == 'a' else B
        m = (A > a[0]) & (A < a[1]) & (B > b[0]) & (B < b[1])
        if period < 50:
            m &= ((X - offset) % period) < width
        ctx.col[m] = ctx.col[m] * mul + add
    return fn


def hatch(sides, els=None, period=0.5, mul=0.7, a=(-99, 99), b=(-99, 99)):
    def fn(ctx):
        if not _sel(ctx, sides, els):
            return
        A, B = ab(ctx)
        reg = (A > a[0]) & (A < a[1]) & (B > b[0]) & (B < b[1])
        g1 = ((A + B) % period) < period * 0.42
        g2 = ((A - B) % period) < period * 0.42
        ctx.col[reg & g1 & g2] *= mul
        ctx.col[reg & ~g1 & ~g2] *= 1.12
    return fn


FONT = {
    'A': ['010', '101', '111', '101', '101'], 'X': ['101', '101', '010', '101', '101'],
    'O': ['111', '101', '101', '101', '111'], 'N': ['1001', '1101', '1011', '1001', '1001'],
    '0': ['111', '101', '101', '101', '111'], '1': ['010', '110', '010', '010', '111'],
    '2': ['110', '001', '010', '100', '111'], '4': ['101', '101', '111', '001', '001'],
    '5': ['111', '100', '110', '001', '110'], '6': ['011', '100', '111', '101', '111'],
    '7': ['111', '001', '010', '010', '010'], '8': ['111', '101', '111', '101', '111'],
    'G': ['011', '100', '101', '101', '011'], 'M': ['10001', '11011', '10101', '10001', '10001'],
    'S': ['011', '100', '010', '001', '110'], 'K': ['101', '110', '100', '110', '101'],
    '.': ['000', '000', '000', '000', '010'], ' ': ['0', '0', '0', '0', '0'],
    '-': ['000', '000', '111', '000', '000'], 'C': ['011', '100', '100', '100', '011'],
    'L': ['100', '100', '100', '100', '111'], 'E': ['111', '100', '110', '100', '111'],
    'F': ['111', '100', '110', '100', '100'], 'U': ['101', '101', '101', '101', '111'],
    'T': ['111', '010', '010', '010', '010'], 'R': ['110', '101', '110', '101', '101'],
    'P': ['110', '101', '110', '100', '100'], 'I': ['111', '010', '010', '010', '111'],
}


def text(side, s, a0, btop, els=None, col=(150, 150, 150), px=None):
    cols = []
    for ch in s:
        g = FONT[ch]
        for c in range(len(g[0])):
            cols.append([g[r][c] == '1' for r in range(5)])
        cols.append([False] * 5)

    def fn(ctx):
        if not _sel(ctx, side, els):
            return
        px = 1.0 / CUR_DENS
        A, B = ab(ctx)
        d = (A - a0) / px if side == 'L' else (a0 - A) / px
        ci = np.floor(d).astype(int)
        ri = np.floor((btop - B) / px).astype(int)
        ok = (ci >= 0) & (ci < len(cols)) & (ri >= 0) & (ri < 5)
        idx = np.where(ok)[0]
        on = np.array([cols[ci[i]][ri[i]] for i in idx], bool) if len(idx) else np.array([], bool)
        hit = idx[on]
        ctx.col[hit] = ctx.col[hit] * 0.35 + np.array(col, float) * 0.65
    return fn


def elfrac_stripe(sides, els, frac, width, mul=1.35, add=6):
    """A raised rib running at a fixed fraction of each element's u-extent (follows stepped curves)."""
    def fn(ctx):
        if not _sel(ctx, sides, els):
            return
        u = ctx.G[:, 2]
        c = ctx.el.lo[2] + frac * (ctx.el.hi[2] - ctx.el.lo[2])
        m = np.abs(u - c) < width / 2
        ctx.col[m] = ctx.col[m] * mul + add
        sh = (u - c >= width / 2) & (u - c < width / 2 + 0.25)
        ctx.col[sh] *= 0.7
    return fn


def custom(fn):
    return fn


# ------------------------------------------------------------------ guns
def build_ak():
    g = Gun('ak47', dict(s=1, k=19.625 / 42.45, kw=19.625 / 42.45 * 1.25, Xm=0.0, Yb=11.75, Zc=4.28))
    B, C = g.b, g.cyl
    # --- muzzle: AKM slant brake
    C('brake', (0.35, 2.45), 0.0, 0.66, 'blued')
    B('brake_lip', (0.0, 0.4), (-0.66, -0.12), 0.6, 'blued')
    B('brake_ring', (2.25, 2.5), (-0.5, 0.5), 0.52, 'steel')
    # --- barrel
    C('barrel', (2.45, 13.0), 0.0, 0.43, 'steel')
    # --- front sight block
    B('fsb_collar', (4.0, 6.3), (-0.82, 0.62), 0.66, 'blued')
    B('fsb_tower', (4.35, 5.95), (0.62, 1.95), 0.5, 'blued')
    B('fsb_ear_l', (4.55, 5.75), (1.6, 3.15), (-0.55, -0.27), 'blued')
    B('fsb_ear_r', (4.55, 5.75), (1.6, 3.15), (0.27, 0.55), 'blued')
    B('fsb_post', (4.95, 5.3), (1.95, 2.95), 0.11, 'parts')
    B('bayonet_lug', (4.2, 6.3), (-1.45, -0.82), 0.32, 'blued')
    # --- cleaning rod
    B('rod', (5.0, 20.0), (-1.18, -0.86), 0.17, 'parts')
    B('rod_head', (6.3, 6.85), (-1.3, -0.72), 0.25, 'parts')
    # --- gas block + tube + front sling loop
    B('gas_block', (10.6, 12.2), (-0.62, 2.3), 0.62, 'blued')
    B('gas_block_nose', (10.15, 10.6), (1.0, 2.2), 0.55, 'blued')
    C('gas_tube', (12.2, 13.3), 1.65, 0.5, 'blued')
    B('swivel_f_top', (10.85, 11.95), (-0.2, 0.05), (-0.98, -0.62), 'parts')
    B('swivel_f_out', (10.85, 11.95), (-0.95, 0.05), (-1.0, -0.88), 'parts')
    B('swivel_f_bot', (10.85, 11.95), (-0.95, -0.7), (-0.98, -0.62), 'parts')
    # --- handguards
    B('hg_ferrule', (12.75, 13.3), (-1.85, 0.98), 1.24, 'blued')
    B('hg_lower', (13.3, 19.0), (-1.75, 0.95), 1.05, 'wood_ak')
    B('hg_swell_f', (13.75, 15.85), (-1.6, 0.55), 1.24, 'wood_ak')
    B('hg_swell_r', (16.45, 18.6), (-1.6, 0.55), 1.24, 'wood_ak')
    B('hg_upper', (13.0, 18.9), (0.95, 2.25), 0.86, 'wood_ak')
    B('hg_upper_top', (13.2, 18.7), (2.25, 2.55), 0.56, 'wood_ak')
    B('hg_retainer', (19.0, 19.65), (-1.95, 1.05), 1.24, 'blued')
    B('hg_lever', (19.1, 19.55), (-0.55, 0.55), (1.24, 1.5), 'parts')
    # --- rear sight
    B('rs_base', (19.65, 22.1), (0.62, 1.7), 0.86, 'blued')
    B('rs_block', (19.65, 21.2), (1.7, 2.3), 0.72, 'blued')
    B('rs_leaf', (20.6, 22.9), (2.2, 2.55), 0.6, 'blued')
    B('rs_slider', (21.05, 21.7), (2.15, 2.78), 0.7, 'parts')
    B('rs_notch_l', (22.45, 22.9), (2.55, 3.0), (-0.6, -0.12), 'blued')
    B('rs_notch_r', (22.45, 22.9), (2.55, 3.0), (0.12, 0.6), 'blued')
    # --- receiver
    # receiver runs forward to the handguard retainer (front trunnion under the rear sight)
    B('receiver', (19.65, 32.6), (-1.9, 1.2), 1.1, 'blued')
    B('rear_trunnion', (32.6, 33.4), (-1.0, 1.0), 1.0, 'blued')
    B('dust_cover', (22.9, 32.95), (1.2, 2.0), 1.0, 'blued')
    B('dust_cover_top', (22.9, 32.7), (2.0, 2.35), 0.66, 'blued')
    B('dc_button', (32.95, 33.4), (1.5, 2.05), 0.32, 'parts')
    B('side_rail', (26.2, 31.2), (-0.75, 0.45), (-1.26, -1.1), 'blued')
    # bolt carrier + charging handle (right side)
    B('carrier', (22.3, 25.2), (0.95, 1.45), (0.95, 1.2), 'parts')
    B('ch_shaft', (22.6, 23.25), (0.98, 1.42), (1.2, 2.0), 'parts')
    B('ch_knob', (22.35, 23.5), (0.82, 1.58), (1.9, 2.4), 'parts')
    # safety / selector lever (right side)
    B('sel_lever', (25.3, 31.4), (0.5, 0.95), (1.1, 1.25), 'parts')
    B('sel_tab', (24.9, 25.6), (0.12, 0.95), (1.1, 1.42), 'parts')
    B('sel_pivot', (30.9, 31.9), (0.15, 1.05), (1.1, 1.3), 'parts')
    # --- magazine (30 rd, curved: stepped cubes)
    steps = [(-1.9, -3.2, 0.0), (-3.2, -4.4, 0.22), (-4.4, -5.5, 0.55), (-5.5, -6.55, 0.98),
             (-6.55, -7.55, 1.5), (-7.55, -8.5, 2.1), (-8.5, -9.4, 2.76)]
    for i, (v0, v1, sh) in enumerate(steps):
        grow = 0.04 * i
        B('mag_%d' % i, (23.6 - sh, 26.6 - sh + grow), (v1, v0), 0.68, 'magsteel')
    B('mag_floor', (20.55, 24.1), (-9.95, -9.4), 0.78, 'magsteel')
    B('mag_catch', (26.6, 27.15), (-2.55, -1.9), 0.48, 'parts')
    B('mag_paddle', (26.75, 27.75), (-3.05, -2.55), 0.56, 'parts')
    # --- trigger group
    B('tg_front', (27.15, 27.5), (-3.05, -1.9), 0.3, 'blued')
    B('tg_bottom', (27.15, 30.4), (-3.35, -3.05), 0.32, 'blued')
    B('trigger', (28.5, 28.85), (-2.95, -1.9), 0.14, 'parts', rot=(-22.5, (28.6, -1.9)))
    # --- pistol grip (raked back)
    B('grip_tang', (29.7, 32.5), (-2.3, -1.9), 0.72, 'blued')
    B('grip', (29.9, 32.05), (-7.35, -2.3), 0.66, 'bakelite', rot=(-22.5, (29.9, -2.3)))
    B('grip_front', (29.7, 29.95), (-6.9, -2.6), 0.55, 'bakelite', rot=(-22.5, (29.9, -2.3)))
    B('grip_cap', (30.05, 31.9), (-7.55, -7.35), 0.6, 'blued', rot=(-22.5, (29.9, -2.3)))
    # --- stock
    B('stock_comb', (33.4, 42.0), (-1.45, 0.95), 0.86, 'wood_ak')
    B('stock_wrist', (33.0, 34.8), (-2.0, -1.45), 0.8, 'wood_ak')
    toe = g.slope('stock', (34.6, -1.45), 22.5, 1.3, 42.0, -1.45, 0.85, 'wood_ak')
    B('buttplate', (42.0, 42.45), (toe - 0.08, 1.0), 0.9, 'blued')
    B('stock_tang', (32.6, 35.2), (0.95, 1.18), 0.42, 'blued')
    B('swivel_r_plate', (39.0, 40.4), (-2.6, -1.9), (-0.98, -0.85), 'parts')
    B('swivel_r_loop', (39.15, 40.25), (-3.5, -2.6), (-1.02, -0.9), 'parts')

    D = g.dec
    # muzzle bore and slant face
    D(oval('F', 0, 0.0, 0.3, 0.3, els=['brake_a', 'brake_b'], col=(8, 8, 9)))
    D(recess('T', (0.6, 1.5), (-0.28, 0.28), els=['brake_*']))
    D(stripes('RL', 'a', 0.55, 0.12, a=(0.6, 2.2), els=['brake_*'], mul=0.6))
    # front sight hood holes / post
    D(oval('RL', 5.15, 2.45, 0.22, 0.3, els=['fsb_ear_*']))
    D(recess('RL', (4.55, 5.75), (1.0, 1.35), els=['fsb_tower'], col=(30, 30, 33)))
    # gas block port + vent holes on gas tube
    D(rivet('RL', 11.4, 0.6, 0.22, els=['gas_block']))
    D(oval('RL', 12.7, 1.65, 0.18, 0.18, els=['gas_tube_*']))
    # handguard vents + finger grooves
    for a0 in (13.9, 15.4, 16.9):
        D(oval('RL', a0 + 0.55, 1.62, 0.45, 0.22, els=['hg_upper']))
    D(stripes('RL', 'b', 0.9, 0.18, els=['hg_swell_*'], mul=0.8, offset=0.1))
    D(stripes('B', 'a', 1.2, 0.25, a=(13.5, 18.8), els=['hg_lower'], mul=0.8))
    # receiver rivets, pins, magwell dimple
    for (a, b) in ((20.2, -1.3), (20.2, 0.25), (22.55, -1.35), (22.55, 0.35), (23.35, -1.4), (31.95, -0.6), (31.95, 0.45),
                   (28.9, -1.15), (29.85, -0.5), (30.6, -1.25)):
        D(rivet('RL', a, b, 0.2, els=['receiver']))
    D(oval('RL', 25.1, -0.35, 0.75, 0.32, els=['receiver'], col=(36, 37, 41)))
    # ejection port w/ bolt carrier visible
    def bolt_inner(ctx, m, A, Bv):
        mm = m & (Bv > 0.4) & (Bv < 1.0) & (A < 27.6)
        ctx.col[mm] = np.array([120, 122, 126], float) * (0.9 + 0.2 * white(ctx.G[mm], 5, 4.0)[:, None])
        lug = mm & (A > 25.2) & (A < 25.75)
        ctx.col[lug] = (40, 40, 42)
    D(recess('R', (24.7, 28.3), (0.1, 1.2), els=['receiver'], inner=bolt_inner))
    # dust cover ribs + rear lug
    D(stripes('TRL', 'a', 0.7, 0.22, a=(29.4, 32.2), els=['dust_cover', 'dust_cover_top'], mul=1.3, add=8))
    D(stripes('TRL', 'a', 0.7, 0.12, a=(29.4, 32.2), els=['dust_cover', 'dust_cover_top'], mul=0.6, offset=0.3))
    # selector markings
    D(paint('R', (24.0, 24.5), (-0.25, -0.05), (190, 190, 186), els=['receiver']))
    D(paint('R', (23.8, 24.25), (-0.9, -0.7), (190, 190, 186), els=['receiver']))
    D(text('L', 'AXON', 22.75, -0.45, els=['receiver'], col=(170, 172, 176)))
    # magazine ribs + witness dimples
    D(elfrac_stripe('RL', ['mag_*'], 0.35, 0.3))
    D(stripes('K', 'b', 0.6, 0.2, els=['mag_*'], mul=1.3, add=6))
    D(rivet('RL', 22.3, -9.67, 0.18, els=['mag_floor']))
    # grip checkering, trigger guard
    D(hatch('RL', els=['grip'], period=0.42, mul=0.8, b=(-6.9, -2.9)))
    # stock: butt plate trap door + screws, wear
    D(recess('K', (-0.6, 0.6), (-3.2, -0.6), els=['buttplate'], col=(38, 38, 42), lip=False))
    D(rivet('K', 0.0, 0.5, 0.2, els=['buttplate']))
    D(rivet('K', 0.0, -4.9, 0.2, els=['buttplate']))
    D(rivet('RL', 37.5, -0.3, 0.17, els=['stock_comb'], cols=((120, 110, 100), (40, 20, 10))))

    g.sight = dict(rear=(22.6, 2.95), front=(5.1, 2.95))
    # classic rear-sight ADS: eye 8 units behind the notch, 2.5deg cant, vertical/lateral
    # display scale tweak (x1.7 / x0.72) so the receiver stays low and narrow on screen
    g.ads = dict(cam=(30.6, 2.95), front=(5.1, 2.95), roll=2.5, sxyz=(1.0, 1.7, 0.72))
    g.grip = (30.9, -4.0)
    return g


def build_m4():
    L = 44.0
    g = Gun('m4a1s', dict(s=1, k=21.69 / L, kw=21.69 / L * 1.2, Xm=-6.44, Yb=9.91, Zc=2.28))
    B, C = g.b, g.cyl
    # --- suppressor
    C('supp_cap', (0.0, 0.55), 0.0, 0.88, 'supp')
    C('supp_body', (0.55, 8.7), 0.0, 1.02, 'supp')
    C('supp_collar', (8.7, 9.6), 0.0, 0.9, 'black')
    B('supp_cone', (9.6, 10.25), (-0.58, 0.58), 0.58, 'black')
    # --- barrel
    C('barrel', (10.25, 13.2), 0.0, 0.42, 'black')
    # --- A2 front sight base
    B('fsb_collar', (11.4, 12.95), (-0.72, 0.72), 0.62, 'black')
    B('fsb_tower', (11.65, 12.75), (0.72, 1.6), 0.42, 'black')
    B('fsb_ear_l', (11.55, 12.85), (1.6, 3.3), (-0.5, -0.2), 'black')
    B('fsb_ear_r', (11.55, 12.85), (1.6, 3.3), (0.2, 0.5), 'black')
    B('fsb_post', (12.05, 12.35), (1.6, 3.0), 0.12, 'parts')
    B('fsb_lug', (11.55, 12.9), (-1.32, -0.72), 0.3, 'black')
    B('fsb_swivel', (11.85, 12.55), (-2.15, -1.32), 0.07, 'parts')
    # --- RIS handguard
    B('hg_body_a', (13.0, 22.4), (-1.32, 1.32), 1.0, 'black')
    B('hg_body_b', (13.03, 22.37), (-1.0, 1.0), 1.32, 'black')
    B('rail_t', (13.0, 22.4), (1.32, 1.52), 0.42, 'rail')
    B('rail_t_crown', (13.0, 22.4), (1.52, 1.78), 0.56, 'rail')
    B('rail_b', (13.0, 22.4), (-1.52, -1.32), 0.42, 'rail')
    B('rail_b_crown', (13.0, 22.4), (-1.78, -1.52), 0.56, 'rail')
    B('rail_r', (13.0, 22.4), (-0.42, 0.42), (1.32, 1.52), 'rail')
    B('rail_r_crown', (13.0, 22.4), (-0.56, 0.56), (1.52, 1.78), 'rail')
    B('rail_l', (13.0, 22.4), (-0.42, 0.42), (-1.52, -1.32), 'rail')
    B('rail_l_crown', (13.0, 22.4), (-0.56, 0.56), (-1.78, -1.52), 'rail')
    B('hg_cap', (12.85, 13.05), (-1.25, 1.25), 1.2, 'black')
    C('delta_ring', (22.4, 23.05), 0.0, 1.48, 'black')
    # --- upper receiver
    B('upper', (23.05, 33.6), (-0.65, 1.32), 1.05, 'black')
    B('up_rail', (23.05, 33.2), (1.32, 1.52), 0.42, 'rail')
    B('up_rail_crown', (23.05, 33.2), (1.52, 1.78), 0.56, 'rail')
    B('ch_body', (33.2, 34.25), (1.0, 1.5), 0.5, 'black')
    B('ch_latch', (33.85, 34.35), (1.02, 1.45), (-0.95, 0.5), 'black')
    B('fa_housing', (29.9, 31.9), (0.15, 1.05), (1.05, 1.5), 'black')
    B('fa_button', (29.45, 30.2), (0.3, 0.9), (1.2, 1.72), 'parts')
    B('port_cover', (25.0, 28.4), (-0.15, 0.95), (1.05, 1.13), 'black')
    B('deflector', (28.55, 29.85), (0.3, 1.2), (1.05, 1.45), 'black')
    # rear flip-up sight (BUIS) with real aperture
    # low flip-up rear sight: thin open ring with a big aperture centred on the sight line (v 3.0)
    B('buis_base', (31.0, 32.9), (1.78, 2.15), 0.58, 'black')
    B('buis_l', (32.25, 32.5), (2.15, 3.5), (-0.58, -0.4), 'black')
    B('buis_r', (32.25, 32.5), (2.15, 3.5), (0.4, 0.58), 'black')
    B('buis_top', (32.25, 32.5), (3.36, 3.5), (-0.4, 0.4), 'black')
    B('buis_bot', (32.25, 32.5), (2.15, 2.64), (-0.4, 0.4), 'black')
    # --- lower receiver
    B('lower', (24.0, 33.9), (-2.4, -0.65), 1.0, 'black')
    B('magwell', (24.0, 27.65), (-3.55, -2.4), 1.05, 'black')
    B('magwell_lip', (23.85, 27.8), (-3.82, -3.45), 1.12, 'black')
    B('pivot_lug', (23.6, 24.0), (-1.55, -0.65), 0.82, 'black')
    B('tg_front', (27.65, 28.0), (-3.4, -2.4), 0.34, 'black')
    B('tg_bottom', (27.65, 31.1), (-3.42, -3.12), 0.38, 'black')
    B('trigger', (29.0, 29.35), (-3.05, -2.4), 0.12, 'parts', rot=(-22.5, (29.1, -2.4)))
    B('selector', (31.4, 32.7), (-1.45, -1.12), (-1.15, -1.0), 'parts')
    B('bolt_catch', (26.9, 28.6), (-0.95, -0.42), (-1.15, -1.0), 'black')
    B('mag_release', (27.7, 28.35), (-1.45, -0.88), (1.0, 1.2), 'parts')
    B('ext_housing', (33.9, 34.5), (-1.95, -0.5), 0.8, 'black')
    # --- magazine (STANAG, slight curve)
    msteps = [(-3.55, -4.9, 0.0), (-4.9, -6.15, 0.12), (-6.15, -7.3, 0.38), (-7.3, -8.35, 0.75)]
    for i, (v0, v1, sh) in enumerate(msteps):
        B('mag_%d' % i, (24.2 - sh, 27.35 - sh), (v1, v0), 0.58, 'black')
    B('mag_floor', (23.2, 26.85), (-8.85, -8.35), 0.66, 'polymer')
    # --- grip (A2)
    B('grip', (31.1, 33.35), (-7.1, -2.4), 0.6, 'polymer', rot=(-22.5, (31.1, -2.4)))
    B('grip_nub', (30.8, 31.15), (-4.85, -4.1), 0.56, 'polymer', rot=(-22.5, (31.1, -2.4)))
    B('grip_tang', (32.6, 34.2), (-2.65, -2.4), 0.6, 'black')
    # --- buffer tube + stock
    C('buffer', (34.5, 42.3), 0.0, 0.72, 'black')
    B('castle_nut', (34.5, 35.05), (-0.86, 0.86), 0.86, 'black')
    B('endplate_loop', (34.55, 35.0), (-1.75, -0.86), (-0.95, -0.6), 'parts')
    B('stock_house', (37.0, 43.2), (-0.95, 1.05), 0.9, 'polymer')
    B('stock_ridge', (37.9, 43.2), (1.05, 1.5), 0.72, 'polymer')
    toe = g.slope('stock_web', (37.6, -0.95), 22.5, 1.0, 42.6, -0.95, 0.66, 'polymer')
    B('butt', (42.6, 43.25), (toe - 0.05, 1.5), 0.94, 'polymer')
    B('buttpad', (43.25, 43.75), (toe + 0.05, 1.42), 0.9, 'rubber')
    B('stock_lever', (37.4, 39.0), (-1.38, -0.95), 0.32, 'polymer')

    D = g.dec
    # suppressor: bore + gas ports on cap, engraved bands, knurl
    D(oval('F', 0, 0, 0.32, 0.32, els=['supp_cap_*'], col=(6, 6, 7)))
    for (a, b) in ((0.55, 0.45), (-0.55, 0.45), (0.55, -0.45), (-0.55, -0.45)):
        D(oval('F', a, b, 0.12, 0.12, els=['supp_cap_*'], col=(20, 20, 22)))
    D(stripes('TBRL', 'a', 99, 0.18, a=(1.0, 1.25), els=['supp_body_*'], mul=0.55))
    D(stripes('TBRL', 'a', 99, 0.18, a=(7.6, 7.85), els=['supp_body_*'], mul=0.55))
    D(stripes('TBRL', 'a', 99, 0.25, a=(3.6, 3.9), els=['supp_body_*'], mul=1.25, add=6))
    D(hatch('TBRL', els=['supp_collar_*'], period=0.35, mul=0.6))
    D(text('L', 'AXON', 2.6, 0.62, els=['supp_body_*'], col=(170, 170, 166)))
    # front sight
    D(stripes('RL', 'b', 0.3, 0.1, els=['fsb_post'], mul=0.7))
    # rails: teeth + T-markings
    D(stripes('TBRL', 'a', 0.5, 0.25, els=['rail_*_crown', 'up_rail_crown'], mul=0.45, offset=0.1))
    # handguard vents (visible strips between rails)
    for a0 in np.arange(13.6, 22.0, 0.95):
        D(oval('RL', a0 + 0.3, 0.75, 0.22, 0.14, els=['hg_body_a']))
        D(oval('RL', a0 + 0.3, -0.75, 0.22, 0.14, els=['hg_body_a']))
        D(oval('TB', a0 + 0.3, 0.75, 0.22, 0.14, els=['hg_body_b']))
        D(oval('TB', a0 + 0.3, -0.75, 0.22, 0.14, els=['hg_body_b']))
    D(stripes('TBRL', 'a', 0.22, 0.11, els=['delta_ring_*'], mul=0.75))
    # upper: port cover hinge lines, forward assist serrations, charging handle grip
    D(stripes('R', 'b', 99, 0.15, b=(-0.15, 0.0), els=['port_cover'], mul=0.5))
    D(rivet('R', 25.25, 0.4, 0.13, els=['port_cover']))
    D(stripes('R', 'a', 0.25, 0.1, els=['fa_button'], mul=0.6))
    D(stripes('TRL', 'a', 0.2, 0.08, els=['ch_latch'], mul=0.6))
    D(rivet('RL', 23.55, 0.3, 0.17, els=['upper']))
    # lower: pins, markings
    for (a, b) in ((24.3, -1.2), (33.2, -1.25), (29.5, -1.45), (30.6, -0.95)):
        D(rivet('RL', a, b, 0.17, els=['lower', 'pivot_lug']))
    D(paint('L', (32.8, 33.05), (-0.95, -0.75), (230, 230, 230), els=['lower']))
    D(paint('L', (32.85, 33.1), (-1.85, -1.65), (220, 40, 30), els=['lower']))
    D(stripes('R', 'a', 0.18, 0.08, els=['mag_release'], mul=0.6))
    # magazine ribs + witness holes
    D(stripes('RL', 'b', 0.55, 0.18, b=(-8.3, -4.9), els=['mag_*'], mul=1.25, add=5))
    D(oval('K', 0, -5.6, 0.12, 0.12, els=['mag_*']))
    D(oval('K', 0, -7.6, 0.12, 0.12, els=['mag_*']))
    # grip texture
    D(hatch('RL', els=['grip'], period=0.36, mul=0.75, b=(-6.7, -2.8)))
    D(stripes('F', 'b', 0.5, 0.18, els=['grip', 'grip_nub'], mul=0.7))
    # buffer & stock
    D(stripes('TBRL', 'a', 99, 0.15, a=(34.75, 34.85), els=['castle_nut'], mul=0.5))
    for a0 in (36.3, 37.3, 38.3, 39.3, 40.3):
        D(oval('B', a0, 0.0, 0.16, 0.16, els=['buffer_a', 'buffer_b']))
    D(recess('RL', (39.6, 42.2), (-0.55, 0.55), els=['stock_house'], col=(22, 22, 24)))
    D(recess('RL', (42.7, 43.15), (-3.0, -2.1), els=['butt'], col=(14, 14, 15)))
    D(stripes('RLK', 'b', 0.35, 0.14, els=['buttpad'], mul=0.55))

    g.sight = dict(rear=(32.35, 3.0), front=(12.2, 3.0))
    # classic ADS like the AK: eye just behind the aperture, 2.5deg cant
    g.ads = dict(cam=(37.0, 3.0), front=(12.2, 3.0), roll=2.5, sxyz=(1.0, 1.3, 0.72))
    g.grip = (32.2, -4.2)
    return g


def build_870():
    L = 46.2
    g = Gun('remmington', dict(s=-1, k=22.25 / L, kw=22.25 / L * 1.25, Xm=16.5, Yb=10.75, Zc=4.25))
    B, C = g.b, g.cyl
    # --- barrel + vent rib + bead
    C('barrel', (0.0, 25.3), 0.0, 0.64, 'blued')
    B('vent_rib', (0.3, 24.4), (0.6, 0.95), 0.2, 'blued')
    B('bead', (0.45, 0.8), (0.95, 1.2), 0.13, 'brass')
    B('barrel_shank', (23.9, 25.3), (-0.72, 0.72), 0.72, 'blued')
    # --- magazine tube, cap, barrel ring, swivel
    C('magtube', (6.6, 25.3), -1.32, 0.54, 'blued')
    C('magcap', (4.55, 5.9), -1.32, 0.64, 'blued')
    B('barrel_ring', (5.9, 6.65), (-1.95, 0.72), 0.7, 'blued')
    B('swivel_f_stud', (4.95, 5.45), (-2.2, -1.9), 0.18, 'parts')
    B('swivel_f_loop', (4.75, 5.65), (-2.85, -2.2), 0.07, 'parts')
    # --- pump forend (ribbed)
    B('forend', (12.9, 21.6), (-2.55, -0.32), 0.98, 'wood_870')
    B('forend_nose', (12.5, 12.9), (-2.25, -0.55), 0.84, 'wood_870')
    for i in range(6):
        a0 = 13.45 + i * 1.3
        B('forend_rib%d' % i, (a0, a0 + 0.75), (-2.72, -0.5), 1.13, 'wood_870')
    B('action_bar_r', (21.6, 25.3), (-1.85, -1.5), (0.7, 0.86), 'parts')
    B('action_bar_l', (21.6, 25.3), (-1.85, -1.5), (-0.86, -0.7), 'parts')
    # --- receiver
    B('receiver', (25.3, 33.5), (-2.15, 0.78), 1.1, 'blued')
    B('receiver_top', (25.3, 33.3), (0.78, 1.15), 0.78, 'blued')
    B('bolt', (26.4, 29.4), (-0.5, 0.55), (0.98, 1.14), 'parts')
    B('trigger_plate', (27.3, 33.65), (-2.65, -2.15), 0.95, 'black')
    B('carrier', (25.6, 27.3), (-2.3, -2.15), 0.7, 'parts')
    B('tg_front', (28.4, 28.78), (-3.7, -2.65), 0.3, 'black')
    B('tg_bottom', (28.4, 31.7), (-3.98, -3.68), 0.32, 'black')
    B('tg_rear', (31.3, 31.7), (-3.7, -2.65), 0.3, 'black')
    B('trigger', (29.8, 30.15), (-3.45, -2.65), 0.13, 'parts', rot=(-22.5, (29.9, -2.65)))
    B('safety', (31.95, 32.45), (-2.58, -2.2), 1.2, 'parts')
    B('slide_release', (27.4, 28.45), (-2.58, -2.3), (-1.18, -0.95), 'parts')
    # side-saddle with 6 shells (left side)
    B('saddle_plate', (25.7, 31.9), (-1.9, 0.95), (-1.28, -1.1), 'polymer')
    for i in range(6):
        a0 = 25.85 + i * 1.0
        B('shell%d' % i, (a0, a0 + 0.9), (-2.3, 1.0), (-2.12, -1.28), 'shell', head=0.62)
    B('saddle_band', (25.75, 31.85), (-0.55, 0.15), (-2.2, -1.95), 'band')
    # --- stock (walnut, semi-pistol grip)
    B('stock_wrist', (33.5, 37.2), (-2.2, 0.88), 0.74, 'wood_870')
    B('stock_grip', (33.75, 36.8), (-3.35, -2.2), 0.72, 'wood_870')
    B('stock_body', (37.2, 45.4), (-2.6, 0.88), 0.86, 'wood_870')
    B('stock_belly', (36.8, 39.0), (-3.35, -2.6), 0.85, 'wood_870')
    toe = g.slope('stock', (39.0, -2.45), 22.5, 1.0, 45.4, -2.6, 0.86, 'wood_870')
    B('grip_cap', (34.05, 36.5), (-3.5, -3.35), 0.68, 'black')
    B('spacer', (45.4, 45.55), (toe - 0.05, 0.92), 0.88, 'spacer')
    B('recoil_pad', (45.55, 46.2), (toe - 0.05, 0.92), 0.9, 'rubber')
    sv = -2.45 - 1.0 * 0.924 - (42.3 - 39.0 + 0.383) * 0.414
    B('swivel_r_stud', (42.0, 42.5), (sv - 0.35, sv + 0.3), 0.18, 'parts')
    B('swivel_r_loop', (41.8, 42.7), (sv - 1.0, sv - 0.35), 0.07, 'parts')

    D = g.dec
    D(oval('F', 0, 0, 0.42, 0.42, els=['barrel_a', 'barrel_b'], col=(6, 6, 7)))
    D(stripes('RL', 'a', 0.9, 0.5, els=['vent_rib'], mul=0.25, offset=0.2))
    D(hatch('TBRL', els=['magcap_*'], period=0.3, mul=0.6))
    D(stripes('TBRL', 'a', 99, 0.12, a=(5.75, 5.9), els=['magcap_*'], mul=0.5))
    # forend grooves (darker under the ribs)
    D(stripes('RLB', 'a', 1.3, 0.55, a=(13.2, 21.4), els=['forend'], mul=0.7, offset=13.45 + 0.75 - 13.0))
    # receiver: ejection port, loading port, pins, engraving
    D(recess('R', (26.15, 29.65), (-0.75, 0.75), els=['receiver'], col=(14, 14, 16)))
    D(recess('B', (25.4, 28.6), (-0.62, 0.62), els=['receiver'], col=(16, 16, 18)))
    D(stripes('R', 'a', 99, 0.5, a=(26.4, 26.9), els=['bolt'], mul=0.5))
    for (a, b) in ((28.6, -1.6), (31.6, -1.6)):
        D(rivet('RL', a, b, 0.2, els=['receiver']))
    D(text('R', 'AXON', 43.0, -0.15, els=['stock_body'], col=(52, 26, 12)))
    D(text('L', 'AXON', 38.4, -0.15, els=['stock_body'], col=(52, 26, 12)))
    D(stripes('RL', 'b', 99, 0.15, b=(0.62, 0.78), els=['receiver'], mul=1.3, add=8))
    D(stripes('RL', 'a', 0.6, 0.25, els=['saddle_plate'], mul=0.7))
    D(stripes('RLKB', 'a', 0.3, 0.12, els=['recoil_pad'], mul=0.55))
    D(stripes('K', 'b', 0.35, 0.12, els=['recoil_pad'], mul=0.55))
    D(stripes('RL', 'a', 0.32, 0.12, els=['safety'], mul=0.6))

    g.sight = dict(rear=(28.0, 1.2), front=(0.62, 1.2))
    g.ads = dict(cam=(56.5, 2.0), front=(0.62, 1.2))
    g.grip = (35.0, -2.4)
    return g


# ------------------------------------------------------------------ pipeline
class Ctx:
    pass


def face_list(g):
    """Non-culled faces with corners in gun space + pixel size."""
    faces = []
    for e in g.els:
        lo_mc, hi_mc = g.mc_box(e)
        others = [o for o in g.els if o is not e]
        for f in FACES:
            Cmc = np.array(face_corners(lo_mc, hi_mc, f), float)
            Cg = g.from_mc(Cmc)                  # local gun space (unrotated)
            ng = g.gun_dir(np.array(FACE_N[f], float))
            Wg = np.linalg.norm(Cg[1] - Cg[0])
            Hg = np.linalg.norm(Cg[3] - Cg[0])
            # cull if fully covered by other elements
            ss = np.linspace(0.02, 0.98, max(3, int(Wg * 4) + 2))
            ts = np.linspace(0.02, 0.98, max(3, int(Hg * 4) + 2))
            S, T = np.meshgrid(ss, ts)
            P = Cg[0] + S.ravel()[:, None] * (Cg[1] - Cg[0]) + T.ravel()[:, None] * (Cg[3] - Cg[0]) + ng * 0.03
            Pw = e.to_world(P)
            cov = np.zeros(len(P), bool)
            for o in others:
                cov |= o.inside(Pw, eps=0.0)
            if cov.all():
                continue
            faces.append(dict(el=e, face=f, Cg=Cg, ng=ng, W=Wg, H=Hg))
    return faces


SIDE_MULT = {'R': 1.0, 'L': 1.0, 'T': 1.0, 'B': 0.6, 'F': 0.6, 'K': 0.6}
PAD = 0


def pack(faces, density):
    for fd in faces:
        dd = density * SIDE_MULT[side_name(fd['ng'])]
        fd['wpx'] = max(1, int(round(fd['W'] * dd)))
        fd['hpx'] = max(1, int(round(fd['H'] * dd)))
    order = sorted(faces, key=lambda f: (-f['hpx'], -f['wpx']))
    x = y = 0
    shelf = 0
    for fd in order:
        if x + fd['wpx'] > TEX:
            x = 0
            y += shelf + PAD
            shelf = 0
        if fd['wpx'] > TEX or y + fd['hpx'] > TEX:
            return False
        fd['px'] = (x, y)
        x += fd['wpx'] + PAD
        shelf = max(shelf, fd['hpx'])
    return True


def paint_face(g, fd, img, filled):
    e, Cg, ng = fd['el'], fd['Cg'], fd['ng']
    wpx, hpx = fd['wpx'], fd['hpx']
    x0, y0 = fd['px']
    ii, jj = np.meshgrid(np.arange(wpx), np.arange(hpx))
    s = ((ii + 0.5) / wpx).ravel()
    t = ((jj + 0.5) / hpx).ravel()
    eu = Cg[1] - Cg[0]
    ev = Cg[3] - Cg[0]
    P = Cg[0] + s[:, None] * eu + t[:, None] * ev
    side = side_name(ng)
    ctx = Ctx()
    ctx.G, ctx.side, ctx.el = P, side, e
    ctx.col = base_color(e.mat, P, side, e).astype(float)
    ctx.flat = np.zeros(len(P), bool)
    # subtle vertical gradient on side faces (top lighter)
    if side in 'RLFK':
        vv = (P[:, 1] - e.lo[1]) / max(0.2, e.hi[1] - e.lo[1])
        ctx.col *= (0.94 + 0.1 * vv)[:, None]
    for d in g.decals:
        d(ctx)
    others = [o for o in g.els if o is not e]

    def occ(Q):
        Qw = e.to_world(Q)
        r = np.zeros(len(Q), bool)
        for o in others:
            r |= o.inside(Qw)
        return r
    # ambient occlusion
    du = eu / (np.linalg.norm(eu) + 1e-9)
    dv = ev / (np.linalg.norm(ev) + 1e-9)
    ao = np.zeros(len(P))
    samples = [ng * 0.3, ng * 0.3 + du * 0.35, ng * 0.3 - du * 0.35, ng * 0.3 + dv * 0.35,
               ng * 0.3 - dv * 0.35, ng * 0.65]
    for sv in samples:
        ao += occ(P + sv)
    ao /= len(samples)
    ctx.col *= (1 - 0.5 * ao)[:, None]
    # convex-edge highlight (worn edges)
    m = MATS[e.mat]
    W, H = fd['W'], fd['H']
    edges = [(-du, s * W), (du, (1 - s) * W), (-dv, t * H), (dv, (1 - t) * H)]
    ef = np.zeros(len(P))
    ew = 0.42
    for tdir, dist in edges:
        near = dist < ew
        if not near.any():
            continue
        idx = np.where(near)[0]
        pe = P[idx] + tdir[None] * (dist[idx, None] + 0.1)
        q1 = pe + ng * 0.06
        q2 = pe - ng * 0.12
        conv = ~(occ(q1) | occ(q2))
        val = np.clip(1 - dist[idx] / ew, 0, 1) * conv
        ef[idx] = np.maximum(ef[idx], val)
    ef[ctx.flat] = 0
    wear = np.array(m.get('wear', m.get('base', (128, 128, 128))), float)
    rnd = fbm(P * 2.2, 2, 11)
    amt = (ef * m.get('edge', 0.5) * (0.25 + 0.6 * rnd))[:, None]
    ctx.col = ctx.col * (1 - amt) + wear[None] * amt
    # dither
    ctx.col += (white(P, 99, 4.0)[:, None] - 0.5) * 4
    img[y0:y0 + hpx, x0:x0 + wpx, :3] = np.clip(ctx.col, 0, 255).reshape(hpx, wpx, 3)
    img[y0:y0 + hpx, x0:x0 + wpx, 3] = 255
    filled[y0:y0 + hpx, x0:x0 + wpx] = True


def dilate(img, filled, iters=3):
    for _ in range(iters):
        acc = np.zeros(img.shape[:2] + (3,), float)
        cnt = np.zeros(img.shape[:2], float)
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            sh = np.roll(np.roll(filled, dy, 0), dx, 1)
            sc = np.roll(np.roll(img[..., :3].astype(float), dy, 0), dx, 1)
            acc += sc * sh[..., None]
            cnt += sh
        grow = (~filled) & (cnt > 0)
        img[grow, :3] = (acc[grow] / cnt[grow, None]).astype(np.uint8)
        img[grow, 3] = 255
        filled = filled | grow
    img[~filled] = (30, 30, 32, 255)
    return img


def r4(x):
    return float(round(x * 10000) / 10000)


def build_model(g, tex_ref, display):
    faces = face_list(g)
    global CUR_DENS
    dens = DENSITY
    while not pack(faces, dens):
        dens -= 0.125
    CUR_DENS = dens
    img = np.zeros((TEX, TEX, 4), np.uint8)
    filled = np.zeros((TEX, TEX), bool)
    for fd in faces:
        paint_face(g, fd, img, filled)
    img = dilate(img, filled)
    by_el = {}
    for fd in faces:
        by_el.setdefault(id(fd['el']), {})[fd['face']] = fd
    els = []
    for e in g.els:
        lo, hi = g.mc_box(e)
        fdict = {}
        for f in FACES:
            fd = by_el.get(id(e), {}).get(f)
            if not fd:
                continue
            x, y = fd['px']
            fdict[f] = {'uv': [r4(x * 16 / TEX), r4(y * 16 / TEX), r4((x + fd['wpx']) * 16 / TEX),
                               r4((y + fd['hpx']) * 16 / TEX)], 'texture': '#0'}
        if not fdict:
            continue
        j = {'name': e.name, 'from': [r4(c) for c in lo], 'to': [r4(c) for c in hi]}
        if e.rot:
            org = g.to_mc(np.array([e.rot[1]]))[0]
            ang = -g.qa['s'] * e.rot[0]
            j['rotation'] = {'angle': ang, 'axis': 'z', 'origin': [r4(c) for c in org]}
        j['faces'] = fdict
        els.append(j)
    model = {
        'credit': 'AXON guns - generated by gen.py (procedural, original)',
        'texture_size': [TEX, TEX],
        'textures': {'0': tex_ref, 'particle': tex_ref},
        'elements': els,
        'display': display,
    }
    return model, img, dens, len(faces)


ADS_YAW = {'ak47': 90, 'm4a1s': 90, 'remmington': -90}


def _R(ax, deg):
    t = math.radians(deg)
    c, s_ = math.cos(t), math.sin(t)
    return {'x': np.array([[1, 0, 0], [0, c, -s_], [0, s_, c]]),
            'y': np.array([[c, 0, s_], [0, 1, 0], [-s_, 0, c]]),
            'z': np.array([[c, -s_, 0], [s_, c, 0], [0, 0, 1]])}[ax]


def ads_display(g, disp):
    """QualityArmory aims by moving the gun to the off hand, so firstperson_lefthand is the
    ADS pose.  Keep QA's scale, then solve rotation (yaw +-90 plus a small pitch) and
    translation so the eye sits exactly at g.ads['cam'] and the front sight lands on the
    crosshair.  Minecraft mirrors left-hand transforms (negates rot y/z and translation x)."""
    d = json.loads(json.dumps(disp))
    lh = d.get('firstperson_lefthand', {})
    S = np.array(lh.get('scale', d.get('firstperson_righthand', {}).get('scale', [1, 1, 1])), float)
    S = S * g.ads.get('sf', 1.0) * np.array(g.ads.get('sxyz', (1.0, 1.0, 1.0)), float)
    yaw_json = ADS_YAW[g.name]
    to = lambda uv: g.to_mc(np.array([[0, uv[1], uv[0]]]))[0]
    C, F = to(g.ads['cam']), to(g.ads['front'])
    R0 = _R('y', -yaw_json)
    dvec = R0 @ ((F - C) * S)
    alpha = math.degrees(math.atan(dvec[1] / dvec[2]))
    Reff = _R('z', g.ads.get('roll', 0.0)) @ _R('x', alpha) @ R0
    arm = np.array([-0.56, -0.52, -0.72])
    teff = -(arm + Reff @ ((C / 16.0 - 0.5) * S)) * 16.0
    assert np.all(np.abs(teff) <= 80), teff
    eb = math.asin(max(-1.0, min(1.0, Reff[0, 2])))
    ec = math.atan2(-Reff[0, 1], Reff[0, 0])
    ea = math.atan2(-Reff[1, 2], Reff[2, 2])
    e_eff = [math.degrees(ea), math.degrees(eb), math.degrees(ec)]
    assert np.allclose(_R('x', e_eff[0]) @ _R('y', e_eff[1]) @ _R('z', e_eff[2]), Reff, atol=1e-6)
    lh = {'rotation': [round(e_eff[0], 3) + 0.0, round(-e_eff[1], 3) + 0.0, round(-e_eff[2], 3) + 0.0],
          'translation': [round(float(-teff[0]), 3), round(float(teff[1]), 3), round(float(teff[2]), 3)],
          'scale': [float(x) for x in S]}
    d['firstperson_lefthand'] = lh
    # check: where does the front sight land?
    pf = arm + teff / 16 + Reff @ ((F / 16.0 - 0.5) * S)
    return d, pf


BUILDERS = {'ak47': build_ak, 'm4a1s': build_m4, 'remmington': build_870}

if __name__ == '__main__':
    import sys
    os.makedirs(OUT, exist_ok=True)
    disp = json.load(open(os.path.join(HERE, 'display_qa.json')))
    for name, fn in BUILDERS.items():
        if len(sys.argv) > 1 and name not in sys.argv[1:]:
            continue
        g = fn()
        dsp, pf = ads_display(g, disp[name])
        print(name, 'ADS lefthand', dsp['firstperson_lefthand'], 'front sight cam pos', pf.round(4))
        model, img, dens, nf = build_model(g, 'qualityarmory:axon/' + name, dsp)
        json.dump(model, open(os.path.join(OUT, name + '.json'), 'w'), indent=1)
        Image.fromarray(img, 'RGBA').save(os.path.join(OUT, name + '.png'))
        meta = dict(sight=g.sight, grip=g.grip, sight_mc=dict(
            rear=g.to_mc(np.array([[0, g.sight['rear'][1], g.sight['rear'][0]]]))[0].tolist(),
            front=g.to_mc(np.array([[0, g.sight['front'][1], g.sight['front'][0]]]))[0].tolist()),
            grip_mc=g.to_mc(np.array([[0, g.grip[1], g.grip[0]]]))[0].tolist())
        json.dump(meta, open(os.path.join(OUT, name + '.meta.json'), 'w'), indent=1)
        print(name, 'elements', len(model['elements']), 'faces', nf, 'density', dens)
