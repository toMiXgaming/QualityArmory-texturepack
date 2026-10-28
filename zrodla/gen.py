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

    def tube(self, name, u, vc, r, ri, mat, dw=0.0, k=0.68):
        """Hollow round-ish tube (scope body) with a see-through bore of half-size ri.
        Same cross-shaped outline as cyl(), split into non-overlapping walls."""
        a = max(r * k, ri + 0.04)
        self.b(name + '_t', u, (vc + ri, vc + r), (dw - a, dw + a), mat)
        self.b(name + '_bt', u, (vc - r, vc - ri), (dw - a, dw + a), mat)
        self.b(name + '_r', u, (vc - ri, vc + ri), (dw + ri, dw + r), mat)
        self.b(name + '_l', u, (vc - ri, vc + ri), (dw - r, dw - ri), mat)
        if a < r - 0.02:
            for sv in (-1, 1):
                for sw in (-1, 1):
                    vv = sorted((vc + sv * ri, vc + sv * a))
                    ww = sorted((dw + sw * a, dw + sw * r))
                    self.b('%s_c%d%d' % (name, sv + 1, sw + 1), u, vv, ww, mat)

    def stair(self, name, u, top, bot, n, w, mat):
        """Gently sloped part (e.g. a stock with less drop than 22.5deg) as n boxes whose top and
        bottom follow straight lines top=(v at u0, v at u1), bot=(...).  Steps are a fraction of a pixel."""
        d = (u[1] - u[0]) / n
        for i in range(n):
            f0, f1 = i / n, (i + 1) / n
            vt = top[0] + (top[1] - top[0]) * (f0 + f1) / 2
            vb = bot[0] + (bot[1] - bot[0]) * (f0 + f1) / 2
            self.b('%s_%d' % (name, i), (u[0] + i * d, u[0] + (i + 1) * d), (vb, vt), w, mat)

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

    # gun space -> QA model frame.  qa['ax'] is the MC axis the barrel lies along ('x' default:
    # muzzle at X=Xm, lateral centre Z=Zc; 'z': muzzle at Z=Zm, lateral centre X=Xc).
    # s = +1 when the stock is toward + along that axis.
    def frame(self):
        q = self.qa
        s, k, kw = q['s'], q['k'], q['kw']
        if q.get('ax', 'x') == 'x':
            O = np.array([q['Xm'], q['Yb'], q['Zc']], float)
            M = np.array([[0, 0, s * k], [0, k, 0], [-s * kw, 0, 0]], float)   # rows X,Y,Z; cols w,v,u
        else:
            O = np.array([q['Xc'], q['Yb'], q['Zm']], float)
            M = np.array([[s * kw, 0, 0], [0, k, 0], [0, 0, s * k]], float)
        return O, M

    def to_mc(self, P):
        O, M = self.frame()
        return O + np.atleast_2d(P) @ M.T

    def from_mc(self, P):
        O, M = self.frame()
        return (np.atleast_2d(P) - O) @ np.linalg.inv(M).T

    def mc_box(self, e):
        c = self.to_mc(np.array([e.lo, e.hi]))
        return c.min(0), c.max(0)

    def gun_dir(self, n_mc):
        """MC-frame direction -> gun-space direction (w, v, u)."""
        _, M = self.frame()
        d = np.linalg.inv(M) @ np.asarray(n_mc, float)
        return np.sign(d) * (np.abs(d) > 1e-9)

    def mc_rot(self, theta):
        """Element rotation about gun +w -> (MC axis, angle)."""
        q = self.qa
        if q.get('ax', 'x') == 'x':
            return 'z', -q['s'] * theta
        return 'x', q['s'] * theta

    def ads_yaw(self):
        q = self.qa
        if q.get('ax', 'x') == 'x':
            return 90 if q['s'] == 1 else -90
        return 0 if q['s'] == 1 else 180

    def right_mc(self):
        """MC-frame unit vector pointing to the gun's right side."""
        _, M = self.frame()
        r = M[:, 0]
        return r / np.linalg.norm(r)


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
    'green':    dict(kind='poly', base=(72, 104, 56), wear=(118, 150, 96), var=0.07, edge=0.5),
    'wood_sks': dict(kind='wood', light=(168, 92, 48), dark=(92, 40, 18), wear=(200, 132, 84), edge=0.45),
    'glass':    dict(kind='flat', base=(22, 30, 40), wear=(60, 80, 100), edge=0.0),
    'reticle':  dict(kind='flat', base=(8, 8, 8), wear=(8, 8, 8), edge=0.0),
    'stainless': dict(kind='metal', base=(146, 148, 153), wear=(206, 208, 212), var=0.08, edge=0.6),
    'sigmag':   dict(kind='poly', base=(176, 104, 46), wear=(214, 150, 92), var=0.06, edge=0.5),
}


def base_color(mat, G, side, el):
    m = MATS[mat]
    if 'sc' in m:            # skins on small guns: pattern size in AK-sized units
        G = G / m['sc']
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
    if k == 'damascus':
        # folded steel: wavy light/dark layers running along the gun, warped by noise
        L = np.array(m['light'], float)
        D = np.array(m['dark'], float)
        warp = fbm(G * np.array([0.5, 0.5, 0.18]), 3, seed) * 3.2
        ph = (v * 1.4 + w * 0.9 + 0.2 * u + warp) * 2 * math.pi * 0.55
        t = (0.5 + 0.5 * np.sin(ph)) ** 1.3
        return L[None] * (1 - t[:, None]) + D[None] * t[:, None]
    if k == 'lava':
        # cooled obsidian crust split by glowing cracks (thin iso-lines of warped noise)
        base = np.array(m['base'], float)
        crust = base[None] * (0.75 + 0.5 * fbm(G * 1.3, 2, seed + 2))[:, None]
        Q = G * np.array([0.3, 0.3, 0.2])
        n = fbm(Q + fbm(Q * 1.7, 2, seed + 4)[:, None] * 1.6, 3, seed)
        d = np.abs(np.sin(n * 2 * math.pi * 1.6))
        hot = np.clip(1 - d / 0.4, 0, 1) ** 0.8
        core = np.clip(1 - d / 0.16, 0, 1)
        glow = np.array(m['glow_col'], float)
        hotc = np.array(m['hot_col'], float)
        col = crust * (1 - hot[:, None]) + glow[None] * hot[:, None]
        return col * (1 - core[:, None]) + hotc[None] * core[:, None]
    if k == 'galaxy':
        # nebula clouds in several colours + scattered stars
        cs = [np.array(c, float) for c in m['cols']]
        a = fbm(G * 0.45, 3, seed)
        b = fbm(G * 0.6 + 7.3, 3, seed + 9)
        t1 = np.clip((a - 0.35) * 2.6, 0, 1)[:, None]
        t2 = np.clip((b - 0.5) * 3.0, 0, 1)[:, None]
        col = cs[0][None] * (1 - t1) + cs[1][None] * t1
        col = col * (1 - t2 * 0.8) + cs[2][None] * t2 * 0.8
        hl = np.clip((a + b - 1.15) * 3.0, 0, 1)[:, None]
        col = col * (1 - hl * 0.7) + cs[3][None] * hl * 0.7
        st = white(G, seed + 13, 4.0)
        col[st > 0.975] = (235, 235, 255)
        col[(st > 0.955) & (st <= 0.975)] = col[(st > 0.955) & (st <= 0.975)] * 0.4 + 150
        return col
    if k == 'holo':
        # holographic foil: hue sweeps along the gun, broken up by noise, with bright sheen bands
        n = fbm(G * 0.35, 3, seed)
        h = (u * 0.035 + v * 0.07 + w * 0.05 + n * 0.45) % 1.0
        sat, val = m.get('sat', 0.6), m.get('val', 0.95)
        rgb = np.clip(np.abs(((h[:, None] * 6 + np.array([0, 4, 2])) % 6) - 3) - 1, 0, 1)
        col = 255 * val * (1 - sat + sat * rgb)
        sheen = (0.5 + 0.5 * np.sin((u * 0.6 - v * 1.4 + n * 3) * math.pi)) ** 6
        return col * (1 - 0.5 * sheen[:, None]) + 255 * 0.5 * sheen[:, None]
    if k == 'carbon':
        # 2x2 twill weave
        L = np.array(m['light'], float)
        D = np.array(m['dark'], float)
        a = u if side not in 'FK' else w
        b = v if side not in 'TB' else w
        cell = (np.floor(a * 2.0) + np.floor(b * 2.0)) % 2
        f = np.where(cell == 0, (a * 2.0) % 1, (b * 2.0) % 1)
        t = cell * 0.55 + 0.45 * np.abs(f - 0.5) * 2
        return L[None] * (1 - t[:, None]) + D[None] * t[:, None]
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
    '9': ['111', '101', '111', '001', '110'], '3': ['110', '001', '010', '001', '110'],
}


def _snap_index(X, start, px, rising):
    """Index of each texel's row/column counted from the first texel past `start`.  Faces are
    packed with whole pixels, so their texel pitch is not exactly 1/density; counting the
    actual texel centres keeps every glyph row and column (no skipped or doubled lines)."""
    Xr = np.round(X, 5)
    u = np.unique(Xr)
    u = u[u >= start - 0.5 * px] if rising else u[u <= start + 0.5 * px][::-1]
    idx = np.full(len(X), -1)
    for i, val in enumerate(u):
        idx[Xr == val] = i
    return idx


def text(side, s, a0, btop, els=None, col=(150, 150, 150), px=None, snap=False):
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
        if snap:
            ci = _snap_index(A, a0, px, side == 'L')
            ri = _snap_index(B, btop, px, False)
        else:
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


def build_pm():
    L = 7.8
    g = Gun('makarov', dict(s=1, k=3.8125 / L, kw=3.8125 / L * 1.25, Xm=4.5625, Yb=5.4, Zc=4.5))
    g.density = 9.0        # small gun: finer texels so sights and markings stay readable
    B, C = g.b, g.cyl
    # --- slide (rounded top, tapered nose)
    B('slide', (0.1, 7.45), (-0.55, 0.55), 0.62, 'blued')
    B('slide_top', (0.15, 7.4), (0.55, 0.78), 0.47, 'blued')
    B('slide_nose', (0.0, 0.1), (-0.45, 0.68), 0.52, 'blued')
    B('fs_post', (0.3, 0.8), (0.78, 1.1), 0.08, 'blued')
    B('rs_base', (6.55, 7.25), (0.78, 0.92), 0.42, 'blued')
    B('rs_l', (6.85, 7.2), (0.92, 1.1), (-0.42, -0.11), 'blued')
    B('rs_r', (6.85, 7.2), (0.92, 1.1), (0.11, 0.42), 'blued')
    # slide-mounted safety / decocker (left side)
    B('safety', (6.25, 7.05), (0.08, 0.36), (-0.72, -0.62), 'parts')
    B('safety_tab', (6.05, 6.35), (0.0, 0.5), (-0.76, -0.62), 'parts')
    # --- hammer (round spur)
    B('hammer', (7.45, 7.7), (-0.4, 0.45), 0.2, 'steel')
    B('hammer_spur', (7.55, 7.8), (0.25, 0.74), 0.19, 'steel')
    # --- frame
    B('frame', (1.0, 7.45), (-1.3, -0.55), 0.56, 'blued')
    B('frame_nose', (0.82, 1.0), (-1.2, -0.65), 0.46, 'blued')
    B('slide_stop', (3.9, 5.3), (-0.9, -0.6), (-0.64, -0.56), 'parts')
    # --- trigger guard + trigger
    B('tg_front', (1.75, 2.05), (-2.3, -1.3), 0.2, 'blued')
    B('tg_corner', (1.9, 2.3), (-2.55, -2.2), 0.2, 'blued')
    B('tg_bottom', (2.2, 4.7), (-2.6, -2.32), 0.2, 'blued')
    B('trigger', (3.05, 3.3), (-2.1, -1.3), 0.11, 'parts', rot=(-22.5, (3.18, -1.3)))
    # --- grip: metal front strap + one-piece wraparound bakelite panel, slight rake
    for i, sh in enumerate((0.0, 0.07, 0.14, 0.21)):
        v0 = -1.3 - 0.95 * i
        B('fstrap_%d' % i, (4.6 + sh, 4.9 + sh), (v0 - 0.95, v0), 0.5, 'blued')
        B('grip_%d' % i, (4.88 + sh, 7.4 + sh), (max(v0 - 0.95, -5.08), min(v0, -1.42)), 0.68, 'bakelite')
    B('grip_core', (4.7, 7.3), (-5.0, -1.3), 0.5, 'blued')
    B('mag_floor', (4.85, 7.6), (-5.28, -5.0), 0.6, 'magsteel')
    B('mag_latch', (7.6, 7.8), (-5.22, -4.72), 0.3, 'parts')
    B('lanyard', (7.15, 7.55), (-5.0, -4.6), (-0.86, -0.68), 'parts')

    D = g.dec
    # muzzle: bore + recoil spring guide face
    D(oval('F', 0, 0.0, 0.2, 0.2, els=['slide_nose'], col=(8, 8, 9)))
    D(stripes('F', 'b', 99, 0.08, b=(-0.45, -0.3), els=['slide_nose'], mul=0.7))
    # rear slide serrations (both sides)
    D(stripes('RL', 'a', 0.22, 0.09, a=(5.7, 6.6), b=(-0.45, 0.5), els=['slide'], mul=0.5))
    # ejection port w/ barrel hood visible
    def barrel_inner(ctx, m, A, Bv):
        mm = m & (Bv < 0.4)
        ctx.col[mm] = np.array([92, 94, 98], float) * (0.9 + 0.2 * white(ctx.G[mm], 5, 4.0)[:, None])
    D(recess('R', (3.3, 4.9), (-0.1, 0.55), els=['slide', 'slide_top'], inner=barrel_inner))
    # sights: white dot-free blade, notch shading
    D(stripes('RL', 'b', 0.18, 0.06, els=['fs_post'], mul=0.75))
    D(stripes('K', 'a', 99, 0.2, a=(-0.12, 0.12), els=['rs_base'], mul=0.4))
    # safety markings (red dot = fire), markings on left of slide
    D(paint('L', (6.0, 6.2), (-0.35, -0.18), (200, 40, 30), els=['slide']))
    D(paint('L', (6.0, 6.2), (0.6, 0.72), (220, 220, 214), els=['slide_top']))
    D(text('L', 'AXON', 1.5, 0.3, els=['slide'], col=(170, 172, 176)))
    # hammer spur hole + serrations
    D(oval('RL', 7.68, 0.55, 0.08, 0.08, els=['hammer_spur']))
    D(stripes('K', 'b', 0.14, 0.06, els=['hammer_spur'], mul=0.6))
    # frame pins
    for (a, b) in ((2.6, -0.95), (4.2, -1.05), (6.8, -0.9)):
        D(rivet('RL', a, b, 0.11, els=['frame']))
    D(stripes('L', 'a', 0.2, 0.08, a=(3.95, 4.3), els=['slide_stop'], mul=0.6))
    # grip: checkering, star-in-circle medallion, screw
    D(hatch('RL', els=['grip_*'], period=0.3, mul=0.78, b=(-4.8, -2.6)))
    D(stripes('K', 'b', 0.3, 0.12, els=['grip_*'], mul=0.75))

    def medallion(ctx):
        if ctx.side not in 'RL' or ctx.el.name != 'grip_0':
            return
        A, Bv = ab(ctx)
        d = np.sqrt((A - 6.1) ** 2 + (Bv + 1.84) ** 2)
        disc = d < 0.3
        ctx.col[disc] = ctx.col[disc] * 0.75 + np.array([150, 74, 42], float) * 0.25
        ctx.col[(d > 0.22) & (d < 0.32)] *= 0.5
        ctx.col[d < 0.09] *= 0.55
    D(custom(medallion))
    D(rivet('RL', 6.1, -3.6, 0.1, els=['grip_*'], cols=((140, 140, 144), (30, 14, 8))))
    D(stripes('RL', 'a', 0.25, 0.1, els=['mag_floor'], mul=0.7))

    g.sight = dict(rear=(7.0, 1.1), front=(0.55, 1.1))
    # same idea as the AK: eye just behind the rear notch, 2.5deg cant, post on the crosshair
    g.ads = dict(cam=(13.0, 1.1), front=(0.55, 1.1), roll=2.5, sxyz=(1.0, 1.0, 1.1))
    g.grip = (6.0, -3.0)
    return g


# ------------------------------------------------------------------ skins
# Premium skins reuse a gun's geometry and display untouched; only the materials are swapped
# and extra decals painted.  Face packing depends on geometry alone, so the UVs match the base
# model and a skin is just the base model pointing at another texture.
AK_RECV = ['receiver', 'dust_cover', 'rear_trunnion']
AK_WOOD = ['hg_*', 'stock_*']


def engraving(sides, els, a, b, col_mul=0.5):
    """Scrollwork: interleaved sine vines with a border line, cut into the surface."""
    def fn(ctx):
        if not _sel(ctx, sides, els):
            return
        A, Bv = ab(ctx)
        reg = (A > a[0]) & (A < a[1]) & (Bv > b[0]) & (Bv < b[1])
        vine = np.abs(np.sin(A * 1.9 + 1.4 * np.sin(Bv * 2.6 + A * 0.8))) < 0.2
        curl = np.abs(np.sin(A * 3.1 - 1.2 * np.cos(Bv * 3.3 - A * 0.5))) < 0.12
        border = ((np.abs(A - a[0] - 0.35) < 0.14) | (np.abs(A - a[1] + 0.35) < 0.14) |
                  (np.abs(Bv - b[0] - 0.3) < 0.13) | (np.abs(Bv - b[1] + 0.3) < 0.13))
        inside = (A > a[0] + 0.21) & (A < a[1] - 0.21) & (Bv > b[0] + 0.17) & (Bv < b[1] - 0.17)
        m = reg & inside & (vine | curl | border)
        ctx.col[m] *= col_mul
    return fn


def lines(sides, els, axis, at, width, col, a=(-99, 99), b=(-99, 99)):
    """Solid colour lines at given positions along one face axis (inlays, neon strips)."""
    def fn(ctx):
        if not _sel(ctx, sides, els):
            return
        A, Bv = ab(ctx)
        X = Bv if axis == 'b' else A
        reg = (A > a[0]) & (A < a[1]) & (Bv > b[0]) & (Bv < b[1])
        m = np.zeros(len(A), bool)
        for p in at:
            m |= np.abs(X - p) < width / 2
        ctx.col[reg & m] = np.array(col, float)
        ctx.flat[reg & m] = True
    return fn


def chevrons(sides, els, period, width, col, slope=0.8):
    def fn(ctx):
        if not _sel(ctx, sides, els):
            return
        A, Bv = ab(ctx)
        m = ((A + np.abs(Bv - (ctx.el.lo[1] + ctx.el.hi[1]) / 2) * slope) % period) < width
        ctx.col[m] = np.array(col, float)
        ctx.flat[m] = True
    return fn


def bands(sides, els, period, zones, k=0.55):
    """Graphic diagonal bands: zones = [(start, end, colour)] within one period of A + k*B."""
    def fn(ctx):
        if not _sel(ctx, sides, els):
            return
        A, Bv = ab(ctx)
        X = (A + k * Bv) % period
        for z0, z1, col in zones:
            m = (X >= z0) & (X < z1)
            ctx.col[m] = ctx.col[m] * 0.15 + np.array(col, float) * 0.85
    return fn


def skin_zloto(g):
    mats = {
        'blued':    dict(kind='metal', base=(200, 152, 50), wear=(255, 232, 150), var=0.08, edge=0.7),
        'steel':    dict(kind='metal', base=(36, 34, 33), wear=(110, 100, 80), var=0.10, edge=0.6),
        'parts':    dict(kind='metal', base=(222, 178, 70), wear=(255, 240, 170), var=0.06, edge=0.6),
        'magsteel': dict(kind='metal', base=(184, 136, 42), wear=(250, 220, 130), var=0.08, edge=0.7),
        'wood_ak':  dict(kind='wood', light=(78, 46, 32), dark=(24, 13, 9), wear=(120, 80, 54), edge=0.35),
        'bakelite': dict(kind='wood', light=(70, 40, 28), dark=(20, 11, 8), wear=(110, 74, 50), edge=0.35),
    }
    D = g.dec
    D(engraving('RL', ['receiver'], (19.8, 32.5), (-1.85, 1.15)))
    D(engraving('RL', ['dust_cover'], (23.0, 29.3), (1.2, 2.0)))
    D(engraving('RL', ['mag_*'], (19.0, 27.0), (-9.4, -1.9), col_mul=0.6))
    # gold inlay lines on the ebony furniture
    D(lines('RL', ['stock_comb'], 'b', (0.35, -0.95), 0.16, (226, 182, 74)))
    D(lines('RL', ['hg_lower', 'hg_upper'], 'b', (0.6, 1.95), 0.14, (226, 182, 74)))
    return mats


def skin_neon(g):
    cyan, mag = (40, 236, 255), (255, 50, 200)
    mats = {
        'blued':    dict(kind='metal', base=(30, 31, 36), wear=cyan, var=0.06, edge=0.95, glow=True),
        'steel':    dict(kind='metal', base=(24, 25, 29), wear=cyan, var=0.06, edge=0.8, glow=True),
        'parts':    dict(kind='metal', base=(40, 40, 46), wear=mag, var=0.05, edge=0.95, glow=True),
        'magsteel': dict(kind='metal', base=(26, 26, 30), wear=mag, var=0.06, edge=0.95, glow=True),
        'wood_ak':  dict(kind='carbon', light=(58, 60, 66), dark=(18, 18, 21), wear=cyan, edge=0.9, glow=True),
        'bakelite': dict(kind='carbon', light=(58, 60, 66), dark=(18, 18, 21), wear=mag, edge=0.9, glow=True),
    }
    D = g.dec
    # circuit traces on the receiver and stock, chevrons on the magazine
    D(lines('RL', ['receiver'], 'b', (-1.0,), 0.2, cyan, a=(20.5, 31.5)))
    D(lines('RL', ['receiver'], 'a', (20.5, 31.5), 0.2, cyan, b=(-1.1, -0.2)))
    D(lines('RL', ['stock_comb'], 'b', (-0.25,), 0.22, mag, a=(34.0, 41.2)))
    D(lines('RL', ['stock_comb'], 'a', (41.2,), 0.22, mag, b=(-0.35, 0.6)))
    D(lines('RL', ['hg_upper'], 'b', (1.95,), 0.2, cyan))
    D(chevrons('RL', ['mag_*'], 1.6, 0.3, cyan))
    return mats


def skin_polar(g):
    white_ = (232, 233, 236)
    orange, black = (240, 112, 28), (26, 26, 30)
    mats = {
        'blued':    dict(kind='poly', base=white_, wear=(150, 152, 158), var=0.03, edge=0.3),
        'steel':    dict(kind='metal', base=(34, 34, 38), wear=(110, 112, 118), var=0.08, edge=0.6),
        'parts':    dict(kind='metal', base=(36, 36, 40), wear=(130, 132, 138), var=0.06, edge=0.6),
        'magsteel': dict(kind='poly', base=orange, wear=(255, 190, 120), var=0.04, edge=0.5),
        'wood_ak':  dict(kind='poly', base=white_, wear=(150, 152, 158), var=0.03, edge=0.3),
        'bakelite': dict(kind='poly', base=black, wear=(80, 80, 86), var=0.05, edge=0.5),
    }
    D = g.dec
    zones = [(0.0, 0.35, black), (0.35, 2.6, orange), (2.6, 2.95, black)]
    D(bands('RL', AK_WOOD, 7.0, zones))
    D(bands('RL', ['receiver', 'dust_cover'], 9.0, [(0.0, 0.3, black), (5.2, 5.5, black)]))
    D(bands('T', ['dust_cover_top', 'hg_upper_top', 'stock_comb'], 7.0, zones, k=0.0))
    D(lines('RL', ['mag_*'], 'b', (-7.0,), 0.3, black))
    return mats


def skin_damast(g):
    mats = {
        'blued':    dict(kind='damascus', light=(158, 160, 166), dark=(66, 67, 73), wear=(205, 206, 210), edge=0.6),
        'steel':    dict(kind='damascus', light=(120, 122, 128), dark=(34, 35, 39), wear=(190, 190, 195), edge=0.6),
        'parts':    dict(kind='metal', base=(168, 112, 58), wear=(230, 180, 120), var=0.08, edge=0.6),
        'magsteel': dict(kind='damascus', light=(136, 138, 144), dark=(52, 53, 58), wear=(190, 190, 195), edge=0.6),
        'wood_ak':  dict(kind='wood', light=(172, 38, 30), dark=(66, 8, 10), wear=(212, 92, 76), edge=0.45),
        'bakelite': dict(kind='bakelite', base=(110, 18, 16), dark=(42, 6, 8), wear=(170, 70, 60), edge=0.5),
    }
    D = g.dec
    D(lines('RL', ['hg_lower', 'stock_comb'], 'b', (0.6,), 0.14, (186, 128, 66)))
    return mats


def skin_lawa(g):
    lava = dict(kind='lava', base=(30, 22, 24), glow_col=(232, 74, 12), hot_col=(255, 214, 70),
                wear=(255, 120, 30), edge=0.85, glow=True)
    mats = {
        'blued': lava, 'magsteel': lava, 'wood_ak': lava,
        'steel':    dict(kind='metal', base=(28, 24, 26), wear=(255, 120, 30), var=0.08, edge=0.85, glow=True),
        'parts':    dict(kind='metal', base=(255, 150, 40), wear=(255, 230, 120), var=0.08, edge=0.6),
        'bakelite': dict(lava, base=(22, 16, 18)),
    }
    return mats


def skin_galaktyka(g):
    gal = dict(kind='galaxy', cols=((14, 10, 44), (86, 30, 150), (30, 150, 220), (236, 80, 190)),
               wear=(200, 180, 255), edge=0.55)
    mats = {
        'blued': gal, 'magsteel': gal, 'wood_ak': gal, 'bakelite': gal,
        'steel':    dict(kind='metal', base=(176, 182, 198), wear=(240, 244, 255), var=0.06, edge=0.6),
        'parts':    dict(kind='metal', base=(196, 200, 214), wear=(250, 250, 255), var=0.05, edge=0.6),
    }
    D = g.dec
    D(lines('RL', ['receiver'], 'b', (1.05,), 0.14, (220, 225, 240)))
    return mats


# --- generic skins for the other AXON guns: materials grouped by role
METAL = ('blued', 'steel', 'black', 'rail', 'magsteel', 'supp', 'stainless')
ACCENT = ('parts', 'brass')
FURN = ('wood_ak', 'wood_870', 'polymer', 'tan', 'bakelite', 'rubber', 'band', 'sigmag')


def by_mat(mats, fn):
    """Run a decal only on elements made of the given (base gun) materials."""
    def w(ctx):
        if ctx.el.mat in mats:
            fn(ctx)
    return w


def free_engraving(sides, sc, col_mul=0.55):
    def fn(ctx):
        if ctx.side not in sides:
            return
        A, Bv = ab(ctx)
        A, Bv = A / sc, Bv / sc
        vine = np.abs(np.sin(A * 1.9 + 1.4 * np.sin(Bv * 2.6 + A * 0.8))) < 0.2
        curl = np.abs(np.sin(A * 3.1 - 1.2 * np.cos(Bv * 3.3 - A * 0.5))) < 0.12
        ctx.col[vine | curl] *= col_mul
    return fn


def generic_skin(theme, sc=1.0):
    def painter(g):
        M = {}

        def put(group, d):
            for k in group:
                M[k] = dict(d, sc=sc)
        D = g.dec
        if theme == 'zloto':
            put(METAL, dict(kind='metal', base=(200, 152, 50), wear=(255, 232, 150), var=0.08, edge=0.7))
            put(('steel',), dict(kind='metal', base=(36, 34, 33), wear=(110, 100, 80), var=0.10, edge=0.6))
            put(ACCENT, dict(kind='metal', base=(222, 178, 70), wear=(255, 240, 170), var=0.06, edge=0.6))
            put(FURN, dict(kind='wood', light=(78, 46, 32), dark=(24, 13, 9), wear=(120, 80, 54), edge=0.35))
            D(by_mat(('blued', 'black', 'magsteel', 'supp'), free_engraving('RL', sc)))
        elif theme == 'neon':
            cyan, mag = (40, 236, 255), (255, 50, 200)
            put(METAL, dict(kind='metal', base=(30, 31, 36), wear=cyan, var=0.06, edge=0.95, glow=True))
            put(ACCENT, dict(kind='metal', base=(40, 40, 46), wear=mag, var=0.05, edge=0.95, glow=True))
            put(FURN, dict(kind='carbon', light=(58, 60, 66), dark=(18, 18, 21), wear=mag, edge=0.9, glow=True))
        elif theme == 'lawa':
            lava = dict(kind='lava', base=(30, 22, 24), glow_col=(232, 74, 12), hot_col=(255, 214, 70),
                        wear=(255, 120, 30), edge=0.85, glow=True)
            put(METAL + FURN, lava)
            put(ACCENT, dict(kind='metal', base=(255, 150, 40), wear=(255, 230, 120), var=0.08, edge=0.6))
        elif theme == 'galaktyka':
            put(METAL + FURN, dict(kind='galaxy', cols=((14, 10, 44), (86, 30, 150), (30, 150, 220), (236, 80, 190)),
                                   wear=(200, 180, 255), edge=0.55))
            put(('steel', 'rail') + ACCENT, dict(kind='metal', base=(186, 190, 204), wear=(250, 250, 255), var=0.05, edge=0.6))
        elif theme == 'polar':
            white_, orange, black = (232, 233, 236), (240, 112, 28), (26, 26, 30)
            put(METAL, dict(kind='poly', base=white_, wear=(150, 152, 158), var=0.03, edge=0.3))
            put(('steel', 'rail') + ACCENT, dict(kind='metal', base=(36, 36, 40), wear=(130, 132, 138), var=0.06, edge=0.6))
            put(FURN, dict(kind='poly', base=orange, wear=(255, 190, 120), var=0.04, edge=0.5))
            put(('rubber', 'band'), dict(kind='poly', base=black, wear=(80, 80, 86), var=0.05, edge=0.5))
            zones = [(0.0, 0.35 * sc, black), (0.35 * sc, 2.6 * sc, orange), (2.6 * sc, 2.95 * sc, black)]
            D(by_mat(('blued', 'black', 'supp', 'magsteel'), bands('RL', None, 8.0 * sc, zones)))
        elif theme == 'holo':
            put(METAL + FURN, dict(kind='holo', wear=(255, 255, 255), edge=0.5))
            put(('steel',) + ACCENT, dict(kind='metal', base=(48, 50, 58), wear=(150, 156, 170), var=0.06, edge=0.7))
            put(('rubber', 'band'), dict(MATS['rubber']))
        elif theme == 'damast':
            put(METAL, dict(kind='damascus', light=(158, 160, 166), dark=(66, 67, 73), wear=(205, 206, 210), edge=0.6))
            put(ACCENT, dict(kind='metal', base=(168, 112, 58), wear=(230, 180, 120), var=0.08, edge=0.6))
            put(FURN, dict(kind='wood', light=(172, 38, 30), dark=(66, 8, 10), wear=(212, 92, 76), edge=0.45))
            put(('bakelite', 'polymer'), dict(kind='bakelite', base=(110, 18, 16), dark=(42, 6, 8), wear=(170, 70, 60), edge=0.5))
            put(('rubber', 'band'), dict(MATS['rubber']))
        return M
    return painter


def _gun_skins(base, first, sc, themes):
    names = {'zloto': 'Złoto', 'neon': 'Neon', 'lawa': 'Lawa', 'galaktyka': 'Galaktyka',
             'polar': 'Polar', 'damast': 'Damast', 'holo': 'Holo'}
    title = {'ak47': 'AK47', 'm4a1s': 'M4A1-S', 'remmington': 'Remington', 'makarov': 'Makarov',
             'awp': 'AWP', 'm16': 'M16', 'mac10': 'MAC-10', 'sks': 'SKS',
             'deagle': 'Desert Eagle', 'sw1911': 'SW1911', 'p30': 'P30', 'mp5': 'MP5', 'uzi': 'Uzi',
             'sg553': 'SG553', 'famas': 'FAMAS', 'dragunov': 'Dragunov', 'kar98k': 'Kar98k',
             'spas': 'SPAS-12'}[base]
    return {'%s_%s' % (base, t): (base, generic_skin(t, sc), first + i, '%s [%s]' % (title, names[t]))
            for i, t in enumerate(themes)}


SKINS = {
    # name: (base gun, painter, custom_model_data on crossbow, display name)
    'ak47_zloto': ('ak47', skin_zloto, 101, 'AK47 [Złoto]'),
    'ak47_neon': ('ak47', skin_neon, 102, 'AK47 [Neon]'),
    'ak47_polar': ('ak47', skin_polar, 103, 'AK47 [Polar]'),
    'ak47_damast': ('ak47', skin_damast, 104, 'AK47 [Damast]'),
    'ak47_lawa': ('ak47', skin_lawa, 105, 'AK47 [Lawa]'),
    'ak47_galaktyka': ('ak47', skin_galaktyka, 106, 'AK47 [Galaktyka]'),
}
# custom_model_data blocks of ten per gun: AK 101-, M4 111-, Remington 121-, Makarov 131-,
# AWP 141-, M16 151-, MAC-10 161-, SKS 171-, Deagle 181-, SW1911 191-, P30 201-, MP5 211-,
# Uzi 221-, SG553 231-, FAMAS 241-, Dragunov 251-, Kar98k 261-, SPAS-12 271-
# every gun has the same seven themes
SKINS.update(_gun_skins('ak47', 107, 1.0, ('holo',)))
SKINS.update(_gun_skins('m4a1s', 111, 1.0, ('zloto', 'neon', 'lawa', 'galaktyka', 'polar', 'damast', 'holo')))
SKINS.update(_gun_skins('remmington', 121, 1.0, ('zloto', 'neon', 'lawa', 'galaktyka', 'damast', 'polar', 'holo')))
SKINS.update(_gun_skins('makarov', 131, 0.35, ('zloto', 'neon', 'lawa', 'galaktyka', 'damast', 'polar', 'holo')))
SKINS.update(_gun_skins('awp', 141, 1.0, ('zloto', 'neon', 'lawa', 'galaktyka', 'damast', 'polar', 'holo')))
SKINS.update(_gun_skins('m16', 151, 1.0, ('zloto', 'neon', 'lawa', 'galaktyka', 'damast', 'polar', 'holo')))
SKINS.update(_gun_skins('mac10', 161, 0.35, ('zloto', 'neon', 'lawa', 'galaktyka', 'damast', 'polar', 'holo')))
SKINS.update(_gun_skins('sks', 171, 1.0, ('zloto', 'neon', 'lawa', 'galaktyka', 'damast', 'polar', 'holo')))
SKINS.update(_gun_skins('deagle', 181, 0.35, ('zloto', 'neon', 'lawa', 'galaktyka', 'damast', 'polar', 'holo')))
SKINS.update(_gun_skins('sw1911', 191, 0.35, ('zloto', 'neon', 'lawa', 'galaktyka', 'damast', 'polar', 'holo')))
SKINS.update(_gun_skins('p30', 201, 0.35, ('zloto', 'neon', 'lawa', 'galaktyka', 'damast', 'polar', 'holo')))
SKINS.update(_gun_skins('mp5', 211, 1.0, ('zloto', 'neon', 'lawa', 'galaktyka', 'damast', 'polar', 'holo')))
SKINS.update(_gun_skins('uzi', 221, 0.35, ('zloto', 'neon', 'lawa', 'galaktyka', 'damast', 'polar', 'holo')))
SKINS.update(_gun_skins('sg553', 231, 1.0, ('zloto', 'neon', 'lawa', 'galaktyka', 'damast', 'polar', 'holo')))
SKINS.update(_gun_skins('famas', 241, 1.0, ('zloto', 'neon', 'lawa', 'galaktyka', 'damast', 'polar', 'holo')))
SKINS.update(_gun_skins('dragunov', 251, 1.0, ('zloto', 'neon', 'lawa', 'galaktyka', 'damast', 'polar', 'holo')))
SKINS.update(_gun_skins('kar98k', 261, 1.0, ('zloto', 'neon', 'lawa', 'galaktyka', 'damast', 'polar', 'holo')))
SKINS.update(_gun_skins('spas', 271, 1.0, ('zloto', 'neon', 'lawa', 'galaktyka', 'damast', 'polar', 'holo')))

def build_awp():
    L = 56.0
    k = 23.0 / L
    g = Gun('awp', dict(ax='z', s=1, k=k, kw=k * 1.25, Zm=-6.0, Yb=9.375, Xc=7.5))
    B, C, T = g.b, g.cyl, g.tube
    # --- muzzle brake + heavy barrel
    C('brake', (0.0, 2.6), 0.0, 0.74, 'black')
    C('barrel', (2.6, 24.0), 0.0, 0.5, 'black')
    C('barrel_rear', (24.0, 30.6), 0.0, 0.58, 'black')
    # --- green forend (free-float tube, sides rise around the barrel)
    B('forend', (13.4, 30.6), (-2.5, -0.3), 1.05, 'green')
    B('forend_nose', (12.9, 13.4), (-2.25, -0.55), 0.9, 'green')
    B('forend_lip_l', (13.8, 30.6), (-0.3, 0.3), (-1.05, -0.62), 'green')
    B('forend_lip_r', (13.8, 30.6), (-0.3, 0.3), (0.62, 1.05), 'green')
    # --- Harris bipod folded forward under the barrel
    B('bipod_mount', (14.0, 15.4), (-3.0, -2.5), 0.62, 'black')
    B('bipod_leg_l', (6.8, 14.4), (-3.0, -2.62), (-0.66, -0.24), 'black')
    B('bipod_leg_r', (6.8, 14.4), (-3.0, -2.62), (0.24, 0.66), 'black')
    B('bipod_foot_l', (6.2, 6.8), (-3.1, -2.52), (-0.7, -0.2), 'rubber')
    B('bipod_foot_r', (6.2, 6.8), (-3.1, -2.52), (0.2, 0.7), 'rubber')
    # --- receiver, rail, bolt
    C('receiver', (30.6, 41.2), 0.1, 0.95, 'black')
    B('rail', (28.8, 40.2), (1.0, 1.42), 0.44, 'rail')
    B('bolt_shroud', (41.2, 42.4), (-0.45, 0.7), 0.56, 'black')
    B('bolt_root', (39.4, 40.4), (0.1, 0.6), (0.95, 1.55), 'parts')
    B('bolt_arm', (39.6, 40.2), (-0.55, 0.3), (1.45, 1.95), 'parts')
    B('bolt_knob', (39.3, 40.5), (-1.15, -0.35), (1.7, 2.5), 'black')
    # --- action bed, magazine, trigger guard (green stock)
    B('bed', (30.6, 41.6), (-2.5, -0.85), 1.05, 'green')
    B('mag', (33.2, 36.2), (-3.85, -2.5), 0.72, 'magsteel')
    B('mag_release', (36.2, 36.75), (-3.0, -2.5), 0.36, 'parts')
    B('tg_front', (37.5, 37.9), (-3.75, -2.5), 0.34, 'green')
    B('tg_bottom', (37.5, 41.6), (-4.05, -3.75), 0.38, 'green')
    B('trigger', (39.0, 39.3), (-3.4, -2.5), 0.12, 'parts', rot=(-22.5, (39.1, -2.5)))
    # --- thumbhole stock
    B('grip', (41.6, 44.3), (-6.5, -0.85), 0.82, 'green')
    B('stock_top', (41.6, 47.6), (-0.85, 1.05), 0.95, 'green')
    B('stock_bottom', (44.3, 47.6), (-6.5, -5.1), 0.82, 'green')
    B('butt', (47.6, 55.4), (-6.5, 1.05), 0.95, 'green')
    B('cheek', (46.4, 54.6), (1.05, 1.95), 0.88, 'green')
    B('cheek_ramp', (45.4, 46.4), (1.05, 1.55), 0.88, 'green')
    B('buttpad', (55.4, 56.0), (-6.6, 2.0), 0.98, 'rubber')
    B('sling_stud', (52.6, 53.4), (-6.95, -6.5), 0.22, 'parts')
    # --- scope (hollow tube so it can be looked through, reticle at the front of the main tube)
    sv = 3.3
    T('obj', (22.6, 26.6), sv, 1.32, 1.1, 'black')
    T('obj_cone', (26.6, 27.8), sv, 1.02, 0.62, 'black')
    T('scope', (27.8, 36.4), sv, 0.74, 0.62, 'black')
    T('power', (36.4, 37.4), sv, 0.88, 0.62, 'black')
    T('ocular', (37.4, 41.6), sv, 1.02, 0.78, 'black')
    T('eyecup', (41.6, 42.4), sv, 0.98, 0.8, 'rubber')
    B('ret_v', (27.9, 28.0), (sv - 0.62, sv + 0.62), 0.03, 'reticle')
    B('ret_h_l', (27.9, 28.0), (sv - 0.03, sv + 0.03), (-0.62, -0.03), 'reticle')
    B('ret_h_r', (27.9, 28.0), (sv - 0.03, sv + 0.03), (0.03, 0.62), 'reticle')
    B('turret_el', (31.4, 32.8), (sv + 0.74, sv + 1.5), 0.6, 'black')
    B('turret_el_cap', (31.55, 32.65), (sv + 1.5, sv + 1.62), 0.5, 'parts')
    B('turret_wi', (31.4, 32.8), (sv - 0.6, sv + 0.6), (0.74, 1.5), 'black')
    B('turret_px', (31.6, 32.6), (sv - 0.5, sv + 0.5), (-1.25, -0.74), 'black')
    T('saddle', (31.0, 33.2), sv, 0.86, 0.74, 'black')
    for nm, u0 in (('ring_f', 29.2), ('ring_r', 34.8)):
        T(nm, (u0, u0 + 1.0), sv, 0.9, 0.74, 'black')
        B(nm + '_base', (u0, u0 + 1.0), (1.42, sv - 0.9), 0.55, 'black')
        B(nm + '_nut', (u0 + 0.2, u0 + 0.8), (1.6, 2.1), (0.55, 0.85), 'parts')

    D = g.dec
    D(oval('F', 0, 0, 0.3, 0.3, els=['brake_a', 'brake_b'], col=(6, 6, 7)))
    D(stripes('RL', 'a', 0.6, 0.28, a=(0.4, 2.3), b=(-0.35, 0.35), els=['brake_a'], mul=0.25))
    D(stripes('T', 'a', 0.6, 0.2, a=(0.4, 2.3), els=['brake_*'], mul=0.4))
    D(stripes('TBRL', 'a', 99, 0.12, a=(23.9, 24.1), els=['barrel_rear_*'], mul=0.6))
    # forend: vents + stipple panel
    for a0 in (16.0, 19.0, 22.0, 25.0):
        D(recess('RL', (a0, a0 + 1.8), (-1.6, -0.9), els=['forend'], col=(30, 44, 26)))
    D(stripes('B', 'a', 0.8, 0.3, a=(16.0, 29.0), els=['forend'], mul=0.82))
    D(stripes('RL', 'a', 0.35, 0.12, els=['bipod_leg_*'], mul=0.7))
    D(stripes('TRL', 'a', 0.5, 0.25, els=['rail'], mul=0.45, offset=0.1))
    D(text('L', 'AXON', 32.0, 0.6, els=['receiver_a'], col=(170, 172, 176)))
    def bolt_inner(ctx, m, A, Bv):
        ctx.col[m & (Bv < 0.4)] = np.array([118, 120, 124], float)
    D(recess('R', (34.4, 37.6), (-0.2, 0.75), els=['receiver_a'], inner=bolt_inner))
    D(stripes('RLK', 'b', 0.25, 0.1, els=['bolt_knob'], mul=0.7))
    D(stripes('RL', 'b', 0.55, 0.2, els=['mag'], mul=1.25, add=6))
    D(hatch('RL', els=['grip'], period=0.36, mul=0.8, b=(-6.0, -2.8)))
    D(stripes('F', 'b', 0.5, 0.18, els=['grip'], mul=0.75))
    D(recess('RL', (49.0, 53.0), (-2.4, -1.0), els=['butt'], col=(36, 52, 30)))
    D(rivet('RL', 48.4, 0.3, 0.18, els=['butt']))
    D(stripes('RLKB', 'a', 0.3, 0.12, els=['buttpad'], mul=0.55))
    D(stripes('K', 'b', 0.35, 0.12, els=['buttpad'], mul=0.55))
    # scope: knurled turrets, power ring, lens glints at the eyepiece rim
    D(stripes('RLFK', 'b', 0.18, 0.08, els=['turret_el'], mul=0.6))
    D(stripes('TBFK', 'b', 0.18, 0.08, els=['turret_wi', 'turret_px'], mul=0.6))
    D(stripes('TBRL', 'a', 0.25, 0.1, els=['power_*'], mul=0.6))
    D(stripes('TBRL', 'a', 0.3, 0.12, els=['eyecup_*'], mul=0.6))
    D(text('L', 'AXON', 35.6, sv + 0.3, els=['scope_l'], col=(190, 190, 190)))

    g.sight = dict(rear=(42.4, sv), front=(22.6, sv))
    # scope ADS: eye behind the eyecup, scope bore on the crosshair, gun length squashed (like QA)
    # so the view through the tube stays wide
    g.ads = dict(cam=(52.0, sv), front=(22.6, sv), roll=0.0, scale=(2.2, 2.2, 0.3))
    g.grip = (43.0, -4.0)
    return g


def build_m16():
    L = 47.6
    k = 18.6875 / L
    g = Gun('m16', dict(s=1, k=k, kw=k * 1.25, Xm=-3.4375, Yb=9.8125, Zc=2.28))
    B, C = g.b, g.cyl
    # --- A2 birdcage flash hider + barrel
    C('fh', (0.0, 2.6), 0.0, 0.54, 'black')
    C('barrel', (2.6, 10.0), 0.0, 0.38, 'black')
    # --- A2 front sight base (triangle)
    B('fsb_collar', (7.3, 9.0), (-0.72, 0.68), 0.62, 'black')
    B('fsb_tower_lo', (7.5, 8.9), (0.68, 1.4), 0.46, 'black')
    B('fsb_tower_hi', (7.75, 8.75), (1.4, 2.3), 0.42, 'black')
    B('fsb_ear_l', (7.8, 8.7), (2.3, 3.55), (-0.48, -0.2), 'black')
    B('fsb_ear_r', (7.8, 8.7), (2.3, 3.55), (0.2, 0.48), 'black')
    B('fsb_post', (8.1, 8.4), (2.3, 3.1), 0.11, 'parts')
    B('bayonet_lug', (7.4, 8.8), (-1.3, -0.72), 0.3, 'black')
    B('swivel_f', (7.7, 8.5), (-2.15, -1.3), 0.07, 'parts')
    # --- round A2 handguards (ribbed)
    C('hg_cap', (9.8, 10.4), 0.2, 1.18, 'black')
    C('hg', (10.4, 23.4), 0.2, 1.34, 'polymer')
    C('delta', (23.4, 24.2), 0.2, 1.46, 'black')
    # --- upper receiver + carry handle with A2 rear sight
    B('upper', (24.2, 33.8), (-0.65, 1.3), 1.02, 'black')
    B('upper_nose', (23.9, 24.2), (-0.55, 1.05), 0.82, 'black')
    B('ch_front', (24.8, 26.0), (1.3, 2.75), 0.62, 'black')
    B('ch_top', (24.8, 32.4), (2.25, 2.75), 0.62, 'black')
    B('ch_rear', (30.8, 32.4), (1.3, 2.25), 0.62, 'black')
    B('rs_body', (31.0, 32.4), (2.75, 2.82), 0.62, 'black')
    B('rs_l', (31.55, 31.85), (2.82, 3.62), (-0.56, -0.36), 'black')
    B('rs_r', (31.55, 31.85), (2.82, 3.62), (0.36, 0.56), 'black')
    B('rs_ap_top', (31.55, 31.85), (3.46, 3.62), (-0.36, 0.36), 'black')
    B('rs_drum', (31.1, 31.9), (2.35, 2.75), (0.62, 1.0), 'parts')
    B('rs_elev', (31.1, 31.9), (2.0, 2.4), (-0.95, -0.62), 'parts')
    B('ch_handle', (33.0, 34.4), (1.0, 1.5), 0.48, 'black')
    B('ch_latch', (33.95, 34.45), (1.02, 1.45), (-0.92, 0.48), 'black')
    B('fa_housing', (29.8, 31.9), (0.2, 1.05), (1.02, 1.48), 'black')
    B('fa_button', (29.4, 30.2), (0.3, 0.95), (1.18, 1.7), 'parts')
    B('port_cover', (25.0, 28.4), (-0.15, 0.95), (1.02, 1.1), 'black')
    B('deflector', (28.5, 29.8), (0.3, 1.2), (1.02, 1.42), 'black')
    # --- lower receiver
    B('lower', (24.6, 34.4), (-2.4, -0.65), 0.98, 'black')
    B('magwell', (24.6, 28.2), (-3.55, -2.4), 1.04, 'black')
    B('magwell_lip', (24.45, 28.35), (-3.82, -3.45), 1.1, 'black')
    B('pivot_lug', (24.2, 24.6), (-1.55, -0.65), 0.8, 'black')
    B('tg_front', (28.2, 28.55), (-3.4, -2.4), 0.34, 'black')
    B('tg_bottom', (28.2, 31.6), (-3.42, -3.12), 0.38, 'black')
    B('trigger', (29.5, 29.85), (-3.05, -2.4), 0.12, 'parts', rot=(-22.5, (29.6, -2.4)))
    B('selector', (31.9, 33.2), (-1.45, -1.12), (-1.13, -0.98), 'parts')
    B('bolt_catch', (27.4, 29.1), (-0.95, -0.42), (-1.13, -0.98), 'black')
    B('mag_release', (28.2, 28.85), (-1.45, -0.88), (0.98, 1.18), 'parts')
    # --- 30-rd magazine
    msteps = [(-3.55, -4.9, 0.0), (-4.9, -6.15, 0.12), (-6.15, -7.3, 0.38), (-7.3, -8.35, 0.75)]
    for i, (v0, v1, sh) in enumerate(msteps):
        B('mag_%d' % i, (24.8 - sh, 27.95 - sh), (v1, v0), 0.58, 'black')
    B('mag_floor', (23.8, 27.45), (-8.85, -8.35), 0.66, 'polymer')
    # --- A2 grip
    B('grip', (31.6, 33.85), (-7.1, -2.4), 0.6, 'polymer', rot=(-22.5, (31.6, -2.4)))
    B('grip_nub', (31.3, 31.65), (-4.85, -4.1), 0.56, 'polymer', rot=(-22.5, (31.6, -2.4)))
    B('grip_tang', (33.1, 34.4), (-2.65, -2.4), 0.6, 'black')
    # --- A2 fixed stock
    B('stock_front', (34.4, 35.6), (-1.6, 1.2), 0.86, 'polymer')
    B('stock_comb', (35.6, 46.9), (-0.9, 1.2), 0.9, 'polymer')
    toe = g.slope('stock', (35.2, -1.6), 22.5, 1.2, 46.9, -0.9, 0.9, 'polymer')
    B('buttplate', (46.9, 47.6), (toe - 0.08, 1.24), 0.94, 'black')
    sv = -1.6 - 1.2 * 0.924 - (44.0 - 35.2 + 0.46) * 0.414
    B('swivel_r', (43.6, 44.6), (sv - 0.8, sv + 0.3), 0.08, 'parts')

    D = g.dec
    # flash hider slots
    D(oval('F', 0, 0, 0.26, 0.26, els=['fh_a', 'fh_b'], col=(6, 6, 7)))
    D(stripes('TRL', 'b', 99, 1, a=(0.3, 1.9), b=(-0.16, 0.16), els=['fh_a', 'fh_b'], mul=0.18))
    D(stripes('T', 'a', 99, 1, a=(0.3, 1.9), b=(-0.12, 0.12), els=['fh_b'], mul=0.18))
    D(stripes('RL', 'b', 0.3, 0.1, els=['fsb_post'], mul=0.7))
    D(oval('RL', 8.25, 1.9, 0.18, 0.18, els=['fsb_tower_hi']))
    # handguard ribs + vents
    D(stripes('TBRL', 'a', 0.62, 0.24, a=(10.6, 23.2), els=['hg_*'], mul=0.62))
    for a0 in np.arange(11.0, 22.6, 1.24):
        D(oval('B', a0, 0.0, 0.22, 0.14, els=['hg_a', 'hg_b']))
    D(stripes('TBRL', 'a', 0.22, 0.11, els=['delta_*'], mul=0.75))
    # carry handle slot, rear sight aperture, drum marks
    D(recess('T', (25.2, 30.4), (-0.12, 0.12), els=['ch_top'], col=(18, 18, 20), lip=False))
    D(stripes('RL', 'a', 0.2, 0.08, els=['rs_drum', 'rs_elev'], mul=0.55))
    D(stripes('R', 'b', 99, 0.15, b=(-0.15, 0.0), els=['port_cover'], mul=0.5))
    D(rivet('R', 25.25, 0.4, 0.13, els=['port_cover']))
    D(stripes('R', 'a', 0.25, 0.1, els=['fa_button'], mul=0.6))
    D(stripes('TRL', 'a', 0.2, 0.08, els=['ch_latch'], mul=0.6))
    for (a, b) in ((24.9, -1.2), (33.7, -1.25), (30.0, -1.45), (31.1, -0.95)):
        D(rivet('RL', a, b, 0.17, els=['lower', 'pivot_lug']))
    D(paint('L', (33.3, 33.55), (-0.95, -0.75), (230, 230, 230), els=['lower']))
    D(paint('L', (33.35, 33.6), (-1.85, -1.65), (220, 40, 30), els=['lower']))
    D(text('L', 'AXON', 25.4, -1.0, els=['magwell', 'lower'], col=(165, 165, 168)))
    D(stripes('R', 'a', 0.18, 0.08, els=['mag_release'], mul=0.6))
    D(stripes('RL', 'b', 0.55, 0.18, b=(-8.3, -4.9), els=['mag_*'], mul=1.25, add=5))
    D(hatch('RL', els=['grip'], period=0.36, mul=0.75, b=(-6.7, -2.8)))
    D(stripes('F', 'b', 0.5, 0.18, els=['grip', 'grip_nub'], mul=0.7))
    # stock: trap door in buttplate, screws, parting line
    D(recess('K', (-0.5, 0.5), (-3.0, -0.7), els=['buttplate'], col=(28, 28, 30), lip=False))
    D(stripes('K', 'b', 0.3, 0.1, b=(-4.6, -3.2), els=['buttplate'], mul=0.6))
    D(rivet('RL', 36.2, 0.2, 0.17, els=['stock_comb', 'stock_front']))
    D(stripes('RL', 'b', 99, 0.08, b=(0.85, 0.93), els=['stock_comb'], mul=0.7))

    g.sight = dict(rear=(31.7, 3.1), front=(8.25, 3.1))
    g.ads = dict(cam=(36.0, 3.1), front=(8.25, 3.1), roll=2.5, sxyz=(1.0, 1.3, 0.72))
    g.grip = (32.6, -4.2)
    return g


def build_sks():
    L = 48.5
    k = 22.06 / L
    g = Gun('sks', dict(ax='z', s=1, k=k, kw=k * 1.25, Zm=-3.0, Yb=6.45, Xc=8.0))
    B, C = g.b, g.cyl
    sl = 2.05           # sight line height
    # --- barrel + front sight + folded bayonet
    C('barrel', (0.0, 21.0), 0.0, 0.4, 'blued')
    B('fs_base', (0.9, 2.6), (-0.6, 0.62), 0.5, 'blued')
    B('fs_tower', (1.15, 2.35), (0.62, 1.05), 0.36, 'blued')
    B('fs_ear_l', (1.2, 2.3), (1.05, 2.25), (-0.42, -0.24), 'blued')
    B('fs_ear_r', (1.2, 2.3), (1.05, 2.25), (0.24, 0.42), 'blued')
    B('fs_post', (1.55, 1.85), (1.05, sl), 0.1, 'parts')
    B('fs_hood', (1.2, 2.3), (2.25, 2.4), 0.42, 'blued')
    B('bay_hinge', (2.6, 3.6), (-1.05, -0.4), 0.38, 'blued')
    B('bay_blade', (3.6, 13.4), (-1.0, -0.55), 0.12, 'steel')
    B('bay_guard', (12.6, 13.0), (-1.2, -0.4), 0.32, 'blued')
    B('rod', (3.6, 12.6), (-0.48, -0.3), (0.25, 0.43), 'parts')
    # --- gas block + cylinder + upper handguard
    B('gas_block', (8.0, 9.2), (-0.5, 1.45), 0.5, 'blued')
    C('gas_tube', (9.2, 13.6), 0.98, 0.42, 'blued')
    B('hg_upper', (13.6, 20.6), (0.5, 1.5), 0.62, 'wood_sks')
    B('hg_upper_top', (13.8, 20.4), (1.5, 1.68), 0.42, 'wood_sks')
    B('hg_retainer', (20.6, 21.0), (0.4, 1.55), 0.66, 'blued')
    # --- one-piece stock: forend
    B('nose_cap', (11.6, 12.4), (-1.35, 0.5), 0.86, 'blued')
    B('forend', (12.4, 22.5), (-1.45, 0.5), 0.9, 'wood_sks')
    B('band', (13.8, 14.4), (-1.5, 1.72), (-0.95, 0.95), 'blued')
    B('swivel_f', (13.7, 14.5), (-0.6, 0.3), (-1.2, -0.95), 'parts')
    # --- rear tangent sight on the barrel shank
    B('rs_base', (20.6, 22.9), (0.5, 1.45), 0.62, 'blued')
    B('rs_block', (20.6, 21.6), (1.45, 1.75), 0.5, 'blued')
    B('rs_leaf', (21.1, 23.1), (1.65, 1.82), 0.48, 'blued')
    B('rs_slider', (21.6, 22.2), (1.6, 1.95), 0.56, 'parts')
    B('rs_notch_l', (22.75, 23.1), (1.82, 2.25), (-0.48, -0.22), 'blued')
    B('rs_notch_r', (22.75, 23.1), (1.82, 2.25), (0.22, 0.48), 'blued')
    # --- receiver, bolt carrier, receiver cover
    B('receiver', (22.5, 31.6), (-0.95, 0.75), 0.82, 'blued')
    B('cover', (23.1, 31.8), (0.75, 1.25), 0.72, 'blued')
    B('cover_top', (23.3, 31.6), (1.25, 1.42), 0.48, 'blued')
    B('carrier', (23.6, 28.4), (0.3, 0.75), (0.82, 0.9), 'parts')
    B('bolt_root', (27.4, 28.2), (0.25, 0.7), (0.82, 1.4), 'parts')
    B('bolt_knob', (27.3, 28.3), (0.15, 0.85), (1.35, 1.95), 'parts')
    B('cover_latch', (31.6, 32.2), (0.3, 1.0), 0.32, 'parts')
    # --- fixed 10-rd magazine, trigger guard, safety
    B('mag', (23.0, 27.2), (-2.75, -0.95), 0.66, 'blued')
    B('mag_hinge', (22.8, 23.3), (-2.35, -1.6), 0.5, 'parts')
    B('tg_front', (27.2, 27.6), (-2.75, -0.95), 0.3, 'blued')
    B('tg_bottom', (27.2, 31.4), (-3.0, -2.72), 0.34, 'blued')
    B('tg_rear', (31.0, 31.4), (-2.8, -0.95), 0.32, 'blued')
    B('trigger', (28.6, 28.9), (-2.4, -0.95), 0.12, 'parts', rot=(-22.5, (28.7, -0.95)))
    B('safety', (30.4, 30.9), (-1.65, -1.0), 0.18, 'parts')
    # --- wood stock: wrist and butt, drop toward the heel
    B('stock_inlet', (22.5, 31.6), (-1.6, -0.95), 0.88, 'wood_sks')
    B('wrist', (31.6, 33.6), (-2.1, 0.55), 0.76, 'wood_sks')
    g.stair('stock', (33.6, 47.9), (0.5, -0.15), (-2.15, -6.0), 14, 0.86, 'wood_sks')
    B('buttplate', (47.9, 48.5), (-6.1, -0.1), 0.92, 'blued')
    B('sling_slot', (43.2, 45.2), (-2.2, -1.4), (-0.92, -0.86), 'blued')

    D = g.dec
    D(oval('F', 0, 0, 0.22, 0.22, els=['barrel_a', 'barrel_b'], col=(6, 6, 7)))
    D(stripes('RL', 'b', 0.25, 0.08, els=['fs_post'], mul=0.7))
    D(oval('RL', 1.75, 1.75, 0.2, 0.26, els=['fs_ear_*']))
    D(stripes('RL', 'b', 99, 0.06, b=(-0.85, -0.7), els=['bay_blade'], mul=1.4, add=20))
    D(rivet('RL', 3.1, -0.72, 0.18, els=['bay_hinge']))
    D(oval('RL', 8.6, 0.95, 0.18, 0.18, els=['gas_block']))
    for a0 in (14.6, 16.4, 18.2):
        D(oval('RL', a0 + 0.5, 1.0, 0.4, 0.16, els=['hg_upper']))
    D(stripes('TRL', 'a', 0.5, 0.14, a=(21.15, 22.9), els=['rs_leaf'], mul=1.4, add=8))
    D(stripes('RL', 'a', 99, 0.4, a=(21.6, 22.2), els=['rs_slider'], mul=0.7))
    def bolt_inner(ctx, m, A, Bv):
        ctx.col[m & (Bv > 0.3)] = np.array([116, 118, 122], float)
    D(recess('R', (24.0, 27.2), (-0.35, 0.72), els=['receiver'], inner=bolt_inner))
    D(stripes('TRL', 'a', 0.3, 0.12, a=(29.8, 31.4), els=['cover', 'cover_top'], mul=0.6))
    D(rivet('RL', 30.2, -0.3, 0.17, els=['receiver']))
    D(rivet('RL', 23.4, -0.3, 0.17, els=['receiver']))
    D(text('L', 'AXON', 24.0, 0.45, els=['receiver'], col=(160, 162, 166)))
    D(stripes('RL', 'b', 0.45, 0.14, b=(-2.6, -1.1), els=['mag'], mul=1.25, add=6))
    D(stripes('RLK', 'b', 0.2, 0.08, els=['bolt_knob'], mul=0.7))
    D(rivet('RL', 36.5, -0.9, 0.17, els=['stock_*'], cols=((120, 110, 100), (40, 20, 10))))
    D(recess('K', (-0.35, 0.35), (-2.6, -1.0), els=['buttplate'], col=(30, 30, 32), lip=False))
    D(rivet('K', 0.0, -0.4, 0.17, els=['buttplate']))
    D(rivet('K', 0.0, -4.6, 0.17, els=['buttplate']))

    g.sight = dict(rear=(22.9, sl), front=(1.7, sl))
    g.ads = dict(cam=(32.5, sl), front=(1.7, sl), roll=2.5, scale=(0.72, 1.15, 1.0))
    g.grip = (33.0, -1.5)
    return g


def build_mac10():
    L = 14.0
    k = 9.51 / L
    g = Gun('mac10', dict(ax='z', s=1, k=k, kw=k * 1.25, Zm=2.74, Yb=5.75, Xc=8.05))
    g.density = 7.0
    B, C = g.b, g.cyl
    sl = 1.85
    # --- threaded barrel stub
    C('barrel', (0.0, 1.5), 0.0, 0.44, 'steel')
    C('barrel_nut', (1.2, 1.5), 0.0, 0.62, 'black')
    # --- upper receiver (stamped box)
    B('upper', (1.5, 13.4), (-0.95, 1.25), 1.1, 'black')
    B('lower', (1.5, 13.4), (-2.0, -0.95), 1.14, 'black')
    B('seam', (1.5, 13.4), (-1.02, -0.88), 1.17, 'black')
    # front sight with protective ears, rear peep sight
    B('fs_base', (1.6, 2.7), (1.25, 1.42), 0.62, 'black')
    B('fs_ear_l', (1.75, 2.55), (1.42, 2.25), (-0.62, -0.38), 'black')
    B('fs_ear_r', (1.75, 2.55), (1.42, 2.25), (0.38, 0.62), 'black')
    B('fs_post', (2.0, 2.3), (1.42, sl), 0.1, 'parts')
    B('rs_base', (12.0, 13.2), (1.25, 1.42), 0.62, 'black')
    B('rs_l', (12.5, 12.75), (1.42, 2.3), (-0.5, -0.32), 'black')
    B('rs_r', (12.5, 12.75), (1.42, 2.3), (0.32, 0.5), 'black')
    B('rs_top', (12.5, 12.75), (2.18, 2.3), (-0.32, 0.32), 'black')
    # cocking knob on top (slot runs along the receiver)
    # kept below the sight line (sl) so the handle never sits in the sight picture
    B('knob', (3.3, 4.2), (1.25, 1.5), 0.32, 'parts')
    B('knob_cap', (3.4, 4.1), (1.5, 1.62), 0.26, 'parts')
    # strap bracket under the front, ejection port right, safety
    B('strap_lug', (1.7, 2.9), (-2.7, -2.0), 0.36, 'black')
    B('strap', (1.55, 3.05), (-2.6, -2.35), (-0.5, 0.5), 'band')
    B('safety', (4.6, 5.8), (-1.75, -1.3), (1.14, 1.26), 'parts')
    B('bolt_stop', (9.2, 10.1), (-1.6, -1.2), (-1.26, -1.14), 'parts')
    # --- trigger guard + trigger
    B('tg_front', (4.3, 4.65), (-3.95, -2.0), 0.3, 'black')
    B('tg_bottom', (4.3, 7.2), (-4.25, -3.95), 0.34, 'black')
    B('trigger', (5.5, 5.8), (-3.5, -2.0), 0.12, 'parts', rot=(-22.5, (5.6, -2.0)))
    # --- grip / magwell, 30-rd magazine below
    B('grip', (7.0, 10.3), (-7.6, -2.0), 0.92, 'black')
    B('grip_front', (6.8, 7.0), (-7.4, -2.6), 0.8, 'black')
    B('mag', (7.25, 9.95), (-12.4, -7.6), 0.78, 'magsteel')
    B('mag_floor', (7.1, 10.1), (-12.75, -12.4), 0.86, 'magsteel')
    B('mag_release', (10.3, 10.8), (-7.55, -6.9), 0.4, 'parts')
    # --- retracted wire stock: side rods + folded butt plate at the back
    B('stock_rod_l', (2.6, 13.4), (-1.6, -1.25), (-1.38, -1.14), 'steel')
    B('stock_rod_r', (2.6, 13.4), (-1.6, -1.25), (1.14, 1.38), 'steel')
    B('stock_tip_l', (2.3, 2.6), (-1.75, -1.1), (-1.42, -1.14), 'steel')
    B('stock_tip_r', (2.3, 2.6), (-1.75, -1.1), (1.14, 1.42), 'steel')
    B('butt_hinge', (13.4, 13.7), (-1.75, -1.1), 1.42, 'steel')
    B('butt_plate', (13.7, 14.0), (-3.4, 0.6), 1.3, 'black')

    D = g.dec
    D(oval('F', 0, 0, 0.24, 0.24, els=['barrel_a', 'barrel_b'], col=(6, 6, 7)))
    D(stripes('TBRL', 'a', 0.16, 0.07, a=(0.05, 1.15), els=['barrel_*'], mul=0.6))
    D(recess('T', (3.0, 9.6), (-0.11, 0.11), els=['upper'], col=(14, 14, 16), lip=False))
    D(stripes('TRLF', 'b', 0.15, 0.06, els=['knob'], mul=0.7))
    def bolt_inner(ctx, m, A, Bv):
        ctx.col[m & (Bv > -0.3)] = np.array([110, 112, 116], float)
    D(recess('R', (4.0, 6.6), (-0.5, 0.6), els=['upper'], inner=bolt_inner))
    for (a, b) in ((2.2, -1.5), (6.2, -1.5), (11.0, -1.5), (12.6, 0.3), (2.2, 0.4)):
        D(rivet('RL', a, b, 0.14, els=['lower', 'upper']))
    D(text('L', 'AXON', 4.6, 0.6, els=['upper'], col=(150, 150, 152)))
    D(paint('R', (5.95, 6.15), (-1.7, -1.5), (220, 40, 30), els=['lower']))
    D(stripes('R', 'a', 0.18, 0.07, els=['safety'], mul=0.6))
    D(hatch('RL', els=['grip'], period=0.3, mul=0.78, b=(-7.2, -2.6)))
    D(stripes('F', 'b', 0.35, 0.14, els=['grip_front'], mul=0.7))
    D(stripes('RL', 'b', 0.6, 0.2, b=(-12.2, -8.0), els=['mag'], mul=1.25, add=6))
    D(oval('K', 0, -9.6, 0.12, 0.12, els=['mag']))
    D(stripes('RLK', 'b', 0.3, 0.1, els=['butt_plate'], mul=0.7))
    D(stripes('TB', 'a', 0.3, 0.12, els=['strap'], mul=0.75))

    g.sight = dict(rear=(12.65, sl), front=(2.15, sl))
    g.ads = dict(cam=(16.6, sl), front=(2.15, sl), roll=2.5, scale=(0.8, 1.2, 1.0))
    g.grip = (8.6, -5.0)
    return g


def build_deagle():
    L = 13.0
    k = 3.75 / L
    g = Gun('deagle', dict(s=1, k=k, kw=k * 1.25, Xm=5.25, Yb=5.45, Zc=4.5))
    g.density = 7.0
    B, C = g.b, g.cyl
    sl = 1.5            # sight line: front post top level with the rear sight ears
    # --- fixed barrel with integral rib and rail, frame nose below it
    B('barrel', (0.0, 6.7), (-0.62, 0.62), 0.58, 'stainless')
    B('barrel_rib', (0.05, 6.65), (0.62, 0.8), 0.44, 'stainless')
    B('rail', (0.4, 6.3), (0.8, 1.0), 0.34, 'stainless')
    B('frame_nose', (1.7, 6.7), (-1.32, -0.62), 0.52, 'black')
    B('fs_base', (0.35, 1.05), (1.0, 1.12), 0.2, 'stainless')
    B('fs_post', (0.5, 0.86), (1.12, sl), 0.09, 'black')
    # --- slide (rear), rear sight with a wide notch
    B('slide', (6.7, 12.55), (-0.62, 0.82), 0.62, 'stainless')
    B('slide_top', (6.75, 12.5), (0.82, 1.0), 0.42, 'stainless')
    B('rs_base', (11.55, 12.3), (1.0, 1.2), 0.46, 'black')
    B('rs_l', (11.95, 12.3), (1.2, sl), (-0.46, -0.14), 'black')
    B('rs_r', (11.95, 12.3), (1.2, sl), (0.14, 0.46), 'black')
    B('safety_l', (11.7, 12.4), (0.05, 0.42), (-0.74, -0.62), 'black')
    B('safety_r', (11.7, 12.4), (0.05, 0.42), (0.62, 0.74), 'black')
    # --- hammer (skeletonised spur)
    B('hammer', (12.55, 12.85), (-0.35, 0.55), 0.2, 'steel')
    B('hammer_spur', (12.7, 13.0), (0.35, 0.85), 0.19, 'steel')
    # --- frame, controls
    B('frame', (6.7, 12.5), (-1.38, -0.62), 0.58, 'black')
    B('tang', (12.5, 13.0), (-1.62, -1.1), 0.5, 'black')
    B('slide_stop', (7.3, 8.9), (-0.95, -0.7), (-0.66, -0.58), 'parts')
    B('takedown', (6.75, 7.25), (-1.25, -0.85), (-0.66, -0.58), 'parts')
    B('mag_release', (9.05, 9.4), (-1.9, -1.55), (-0.66, -0.5), 'parts')
    # --- squared trigger guard with a hook, trigger
    B('tg_front', (6.05, 6.4), (-2.95, -1.38), 0.22, 'black')
    B('tg_hook', (5.85, 6.05), (-3.0, -2.6), 0.2, 'black')
    B('tg_bottom', (6.2, 9.4), (-3.22, -2.92), 0.24, 'black')
    B('trigger', (7.75, 8.05), (-2.6, -1.38), 0.12, 'parts', rot=(-22.5, (7.9, -1.38)))
    # --- raked grip: metal front strap + wraparound rubber panel, 9-rd magazine base
    for i in range(5):
        sh = 0.16 * i
        v0 = -1.38 - 0.97 * i
        B('fstrap_%d' % i, (9.15 + sh, 9.45 + sh), (max(v0 - 0.97, -6.1), v0), 0.5, 'black')
        B('grip_%d' % i, (9.42 + sh, 12.35 + sh), (max(v0 - 0.97, -6.1), min(v0, -1.45)), 0.74, 'rubber')
    B('grip_core', (9.3, 12.3), (-6.0, -1.38), 0.55, 'black')
    B('mag_floor', (9.95, 13.15), (-6.4, -6.1), 0.62, 'magsteel')

    D = g.dec
    # .50 bore and the frame/barrel seam
    D(oval('F', 0, 0, 0.36, 0.36, els=['barrel'], col=(6, 6, 7)))
    D(stripes('RL', 'b', 99, 0.05, b=(-0.67, -0.6), els=['barrel', 'slide'], mul=0.6))
    # cross slots in the top rail
    D(stripes('T', 'a', 0.4, 0.16, a=(0.5, 6.2), els=['rail'], mul=0.55))
    D(stripes('RL', 'a', 0.4, 0.16, a=(0.5, 6.2), els=['rail'], mul=0.6))
    # rear slide serrations (both sides)
    D(stripes('RL', 'a', 0.24, 0.1, a=(10.4, 11.5), b=(-0.4, 0.7), els=['slide'], mul=0.5))

    def case_inner(ctx, m, A, Bv):
        mm = m & (Bv < 0.5) & (A > 7.7) & (A < 9.1)
        ctx.col[mm] = np.array([186, 146, 64], float) * (0.85 + 0.25 * white(ctx.G[mm], 9, 4.0)[:, None])
    D(recess('R', (7.4, 9.4), (0.0, 0.7), els=['slide'], inner=case_inner))
    # three white dots for a readable sight picture
    D(paint('K', (-0.05, 0.05), (1.3, 1.42), (236, 236, 232), els=['fs_post']))
    D(paint('K', (-0.36, -0.24), (1.3, 1.42), (236, 236, 232), els=['rs_l']))
    D(paint('K', (0.24, 0.36), (1.3, 1.42), (236, 236, 232), els=['rs_r']))
    D(stripes('K', 'a', 99, 0.2, a=(-0.14, 0.14), els=['rs_base'], mul=0.4))
    # markings
    D(text('L', 'AXON', 1.2, 0.35, els=['barrel'], col=(40, 40, 44), snap=True))
    D(text('L', '.50 AE', 7.0, 0.55, els=['slide'], col=(40, 40, 44), snap=True))
    D(oval('RL', 12.85, 0.62, 0.08, 0.08, els=['hammer_spur']))
    D(stripes('K', 'b', 0.14, 0.06, els=['hammer_spur'], mul=0.6))
    for (a, b) in ((7.6, -1.05), (10.0, -0.95), (11.8, -1.0)):
        D(rivet('RL', a, b, 0.11, els=['frame']))
    D(stripes('L', 'a', 0.2, 0.08, a=(7.35, 7.8), els=['slide_stop'], mul=0.6))
    D(stripes('RL', 'b', 0.12, 0.05, els=['safety_*'], mul=0.6))
    # grip: stippled rubber, front strap grooves, magazine base
    D(hatch('RL', els=['grip_*'], period=0.28, mul=0.72, b=(-5.9, -1.6)))
    D(stripes('K', 'b', 0.3, 0.12, els=['grip_*'], mul=0.75))
    D(stripes('F', 'b', 0.35, 0.14, els=['fstrap_*'], mul=0.7))
    D(stripes('RL', 'a', 0.3, 0.12, els=['mag_floor'], mul=0.7))

    g.sight = dict(rear=(12.1, sl), front=(0.68, sl))
    # same as the Makarov: eye behind the rear notch, 2.5deg cant, post on the crosshair
    g.ads = dict(cam=(19.5, sl), front=(0.68, sl), roll=2.5)
    g.grip = (11.0, -3.5)
    return g


def build_sw1911():
    L = 10.4
    k = 4.25 / L
    g = Gun('sw1911', dict(s=1, k=k, kw=k * 1.25, Xm=3.812, Yb=5.4, Zc=4.5))
    g.density = 8.0
    B, C = g.b, g.cyl
    sl = 1.18
    # --- slide with barrel bushing and recoil spring plug at the muzzle
    C('bushing', (0.0, 0.25), 0.0, 0.32, 'steel')
    C('plug', (0.0, 0.25), -0.62, 0.24, 'steel')
    B('slide', (0.15, 10.0), (-0.95, 0.62), 0.5, 'blued')
    B('slide_top', (0.2, 9.95), (0.62, 0.78), 0.34, 'blued')
    B('fs_post', (0.45, 0.85), (0.78, sl), 0.08, 'blued')
    # low rear sight with a wide notch
    B('rs_base', (8.9, 9.7), (0.78, 0.95), 0.42, 'blued')
    B('rs_l', (9.3, 9.7), (0.95, sl), (-0.42, -0.14), 'blued')
    B('rs_r', (9.3, 9.7), (0.95, sl), (0.14, 0.42), 'blued')
    # --- frame, beavertail, hammer
    B('dust_cover', (2.0, 4.7), (-1.45, -0.95), 0.46, 'blued')
    B('frame', (4.7, 9.9), (-1.45, -0.95), 0.46, 'blued')
    B('beavertail', (9.6, 10.4), (-1.6, -1.15), 0.42, 'blued')
    B('grip_safety', (9.3, 9.7), (-2.7, -1.45), 0.4, 'blued')
    B('hammer', (9.95, 10.22), (-0.6, 0.45), 0.18, 'steel')
    B('hammer_spur', (10.05, 10.35), (0.25, 0.62), 0.17, 'steel')
    # left side controls: thumb safety, slide stop, magazine release
    B('thumb_safety', (8.6, 9.5), (-1.22, -0.88), (-0.62, -0.46), 'blued')
    B('safety_shelf', (8.45, 8.9), (-0.98, -0.88), (-0.78, -0.46), 'blued')
    B('slide_stop', (4.8, 6.3), (-1.25, -0.97), (-0.58, -0.46), 'blued')
    B('mag_release', (6.95, 7.25), (-1.95, -1.6), (-0.68, -0.55), 'parts')
    # --- trigger guard + long flat trigger
    B('tg_front', (4.0, 4.3), (-2.6, -1.45), 0.2, 'blued')
    B('tg_corner', (4.15, 4.55), (-2.85, -2.5), 0.2, 'blued')
    B('tg_bottom', (4.45, 6.75), (-2.88, -2.6), 0.22, 'blued')
    B('trigger', (5.2, 5.45), (-2.25, -1.45), 0.12, 'parts')
    # --- grip: metal front and back straps, checkered wood panels with screws
    for i in range(5):
        sh = 0.26 * i       # ~17deg grip angle
        v0 = -1.45 - 0.9 * i
        vb = max(v0 - 0.9, -5.95)
        B('fstrap_%d' % i, (6.6 + sh, 6.9 + sh), (vb, v0), 0.42, 'blued')
        B('grip_%d' % i, (6.9 + sh, 9.3 + sh), (vb, min(v0, -1.5)), 0.6, 'wood_870')
        B('core_%d' % i, (6.85 + sh, 9.55 + sh), (vb, v0), 0.4, 'blued')
        if i:
            B('bstrap_%d' % i, (9.3 + sh, 9.6 + sh), (vb, v0), 0.42, 'blued')
    B('mag_base', (7.7, 10.6), (-6.2, -5.95), 0.45, 'magsteel')

    D = g.dec
    D(oval('F', 0, 0, 0.27, 0.27, els=['bushing_a', 'bushing_b'], col=(6, 6, 7)))
    D(oval('F', 0, -0.62, 0.1, 0.1, els=['plug_a', 'plug_b'], col=(30, 30, 32)))
    # front and rear slide serrations
    D(stripes('RL', 'a', 0.22, 0.09, a=(0.8, 2.0), b=(-0.75, 0.5), els=['slide'], mul=0.5))
    D(stripes('RL', 'a', 0.22, 0.09, a=(7.6, 8.9), b=(-0.75, 0.5), els=['slide'], mul=0.5))

    def barrel_inner(ctx, m, A, Bv):
        mm = m & (Bv < 0.42)
        ctx.col[mm] = np.array([96, 98, 102], float) * (0.9 + 0.2 * white(ctx.G[mm], 5, 4.0)[:, None])
    D(recess('R', (4.3, 6.2), (-0.1, 0.56), els=['slide'], inner=barrel_inner))
    # three white dots
    D(paint('K', (-0.05, 0.05), (1.0, 1.1), (236, 236, 232), els=['fs_post']))
    D(paint('K', (-0.34, -0.22), (1.0, 1.1), (236, 236, 232), els=['rs_l']))
    D(paint('K', (0.22, 0.34), (1.0, 1.1), (236, 236, 232), els=['rs_r']))
    D(stripes('K', 'a', 99, 0.2, a=(-0.14, 0.14), els=['rs_base'], mul=0.4))
    D(text('L', 'AXON 1911', 2.4, 0.3, els=['slide'], col=(170, 172, 176), snap=True))
    # hammer, safety, slide stop
    D(oval('RL', 10.2, 0.45, 0.07, 0.07, els=['hammer_spur']))
    D(stripes('K', 'b', 0.12, 0.05, els=['hammer_spur'], mul=0.6))
    D(stripes('T', 'a', 0.12, 0.05, els=['safety_shelf'], mul=0.6))
    D(stripes('L', 'a', 0.2, 0.08, a=(4.85, 5.3), els=['slide_stop'], mul=0.6))
    for (a, b) in ((5.3, -1.2), (8.3, -1.2)):
        D(rivet('RL', a, b, 0.1, els=['frame']))
    # grip: diamond checkering around two screws, grooved front strap, checkered back strap
    D(hatch('RL', els=['grip_*'], period=0.3, mul=0.72, b=(-5.8, -1.7)))
    for (a, b) in ((7.75, -2.0), (8.75, -5.2)):
        D(rivet('RL', a, b, 0.15, els=['grip_*'], cols=((150, 150, 154), (40, 22, 12))))
    D(stripes('F', 'b', 0.25, 0.1, els=['fstrap_*'], mul=0.7))
    D(hatch('K', els=['bstrap_*', 'grip_safety'], period=0.25, mul=0.7))
    D(stripes('RL', 'a', 0.3, 0.12, els=['mag_base'], mul=0.7))

    g.sight = dict(rear=(9.5, sl), front=(0.65, sl))
    g.ads = dict(cam=(15.2, sl), front=(0.65, sl), roll=2.5)
    g.grip = (8.6, -3.5)
    return g


def build_p30():
    L = 8.5
    k = 3.25 / L
    g = Gun('p30', dict(s=1, k=k, kw=k * 1.25, Xm=5.75, Yb=5.3, Zc=4.5))
    g.density = 9.0
    B, C = g.b, g.cyl
    sl = 1.12
    # --- slide with a tapered nose
    B('slide_nose', (0.0, 0.5), (-0.42, 0.52), 0.48, 'black')
    B('slide', (0.5, 8.1), (-0.5, 0.6), 0.56, 'black')
    B('slide_top', (0.55, 8.05), (0.6, 0.76), 0.4, 'black')
    B('fs_post', (0.55, 0.9), (0.76, sl), 0.08, 'black')
    B('rs_base', (7.2, 7.9), (0.76, 0.92), 0.44, 'black')
    B('rs_l', (7.55, 7.9), (0.92, sl), (-0.44, -0.14), 'black')
    B('rs_r', (7.55, 7.9), (0.92, sl), (0.14, 0.44), 'black')
    B('hammer', (8.05, 8.3), (-0.3, 0.42), 0.18, 'steel')
    # --- polymer frame with accessory rail, ambidextrous slide release, decocker
    B('frame_nose', (0.9, 4.0), (-1.2, -0.5), 0.5, 'polymer')
    B('frame', (4.0, 8.0), (-1.2, -0.5), 0.52, 'polymer')
    B('tang', (7.95, 8.55), (-1.45, -1.1), 0.46, 'polymer')
    B('release_l', (4.4, 5.4), (-0.85, -0.62), (-0.62, -0.52), 'black')
    B('release_r', (4.4, 5.4), (-0.85, -0.62), (0.52, 0.62), 'black')
    B('decocker', (7.7, 8.0), (-1.0, -0.7), (-0.6, -0.52), 'parts')
    # --- trigger guard with HK paddle magazine release, trigger
    B('tg_front', (3.6, 3.95), (-2.45, -1.2), 0.22, 'polymer')
    B('tg_bottom', (3.8, 6.0), (-2.7, -2.42), 0.24, 'polymer')
    B('mag_paddle', (5.75, 6.0), (-2.6, -2.1), 0.2, 'parts')
    B('trigger', (4.75, 5.0), (-2.05, -1.2), 0.12, 'parts', rot=(-22.5, (4.88, -1.2)))
    # --- grip: finger-grooved front strap, stippled sides, separate backstrap insert
    for i in range(5):
        sh = 0.14 * i
        v0 = -1.2 - 0.9 * i
        vb = max(v0 - 0.9, -5.7)
        B('fstrap_%d' % i, (5.75 + sh, 6.0 + sh), (vb, v0), 0.5, 'polymer')
        B('grip_%d' % i, (5.98 + sh, 8.25 + sh), (vb, min(v0, -1.3)), 0.62, 'polymer')
        B('bstrap_%d' % i, (8.25 + sh, 8.45 + sh), (vb, min(v0, -1.45)), 0.45, 'rubber')
    B('mag_base', (6.1, 8.9), (-5.95, -5.7), 0.52, 'polymer')

    D = g.dec
    D(oval('F', 0, 0, 0.25, 0.25, els=['slide_nose'], col=(6, 6, 7)))
    D(stripes('RL', 'a', 0.2, 0.08, a=(0.7, 1.6), b=(-0.35, 0.5), els=['slide'], mul=0.5))
    D(stripes('RL', 'a', 0.2, 0.08, a=(6.2, 7.4), b=(-0.35, 0.5), els=['slide'], mul=0.5))

    def barrel_inner(ctx, m, A, Bv):
        mm = m & (Bv < 0.42)
        ctx.col[mm] = np.array([96, 98, 102], float) * (0.9 + 0.2 * white(ctx.G[mm], 5, 4.0)[:, None])
    D(recess('R', (3.2, 4.6), (0.05, 0.55), els=['slide'], inner=barrel_inner))
    D(paint('K', (-0.05, 0.05), (0.95, 1.05), (236, 236, 232), els=['fs_post']))
    D(paint('K', (-0.32, -0.22), (0.95, 1.05), (236, 236, 232), els=['rs_l']))
    D(paint('K', (0.22, 0.32), (0.95, 1.05), (236, 236, 232), els=['rs_r']))
    D(stripes('K', 'a', 99, 0.2, a=(-0.14, 0.14), els=['rs_base'], mul=0.4))
    D(text('L', 'AXON P30', 2.0, 0.3, els=['slide'], col=(150, 152, 156), snap=True))
    # rail slots under the dust cover, frame pins
    D(stripes('B', 'a', 0.45, 0.18, a=(1.1, 3.8), els=['frame_nose'], mul=0.5))
    D(stripes('RL', 'a', 0.45, 0.18, a=(1.1, 3.8), b=(-1.2, -1.0), els=['frame_nose'], mul=0.6))
    for (a, b) in ((4.3, -1.0), (7.3, -0.95)):
        D(rivet('RL', a, b, 0.09, els=['frame']))
    D(stripes('RL', 'a', 0.15, 0.06, els=['release_*'], mul=0.6))
    # grip texture, finger grooves, magazine base
    D(hatch('RL', els=['grip_*'], period=0.22, mul=0.7, b=(-5.5, -1.5)))
    D(stripes('F', 'b', 0.9, 0.18, els=['fstrap_*'], mul=0.55, offset=0.35))
    D(hatch('K', els=['bstrap_*'], period=0.22, mul=0.7))
    D(stripes('RL', 'a', 0.3, 0.12, els=['mag_base'], mul=0.7))

    g.sight = dict(rear=(7.7, sl), front=(0.72, sl))
    g.ads = dict(cam=(12.7, sl), front=(0.72, sl), roll=2.5)
    g.grip = (7.0, -3.3)
    return g


def build_mp5():
    L = 32.6
    k = 15.75 / L
    g = Gun('mp5', dict(s=1, k=k, kw=k * 1.25, Xm=-0.25, Yb=8.75, Zc=4.25))
    B, C = g.b, g.cyl
    sl = 2.6            # sight line through the front ring and the rear drum aperture
    # --- barrel with the three-lug muzzle, cocking tube above it
    C('muzzle', (0.0, 0.8), 0.0, 0.42, 'blued')
    C('barrel', (0.8, 3.6), 0.0, 0.3, 'blued')
    C('ctube', (1.3, 10.6), 1.25, 0.48, 'black')
    # hooded front sight: open ring around a post
    B('fs_base', (1.6, 2.6), (1.6, 2.0), 0.42, 'black')
    B('fs_ring_l', (1.85, 2.35), (2.0, 3.0), (-0.44, -0.3), 'black')
    B('fs_ring_r', (1.85, 2.35), (2.0, 3.0), (0.3, 0.44), 'black')
    B('fs_ring_top', (1.85, 2.35), (2.88, 3.0), (-0.3, 0.3), 'black')
    B('fs_post', (2.0, 2.2), (2.0, sl), 0.07, 'parts')
    # cocking handle on the left of the tube
    B('ch_arm', (4.8, 5.3), (1.0, 1.45), (-1.15, -0.45), 'parts')
    B('ch_knob', (4.7, 5.4), (0.9, 1.55), (-1.4, -1.1), 'parts')
    # --- slimline handguard with finger grooves
    B('handguard', (3.4, 10.4), (-1.6, 0.85), 0.72, 'polymer')
    # --- receiver, rear drum sight with an open aperture on the sight line
    B('receiver', (10.4, 21.0), (-0.6, 1.75), 0.62, 'black')
    B('rs_base', (19.0, 20.8), (1.75, 2.0), 0.5, 'black')
    B('rs_l', (19.8, 20.2), (2.0, 3.2), (-0.56, -0.22), 'black')
    B('rs_r', (19.8, 20.2), (2.0, 3.2), (0.22, 0.56), 'black')
    B('rs_top', (19.8, 20.2), (3.0, 3.2), (-0.22, 0.22), 'black')
    B('rs_bot', (19.8, 20.2), (2.0, 2.25), (-0.22, 0.22), 'black')
    B('rs_drum_l', (19.65, 20.35), (2.2, 3.0), (-0.72, -0.56), 'parts')
    B('rs_drum_r', (19.65, 20.35), (2.2, 3.0), (0.56, 0.72), 'parts')
    # --- magwell + curved 30-rd magazine (curves forward)
    B('magwell', (10.6, 12.6), (-1.7, -0.6), 0.6, 'black')
    for i in range(6):
        du = -0.3 * i
        v0 = -1.7 - 1.15 * i
        B('mag_%d' % i, (10.8 + du, 12.4 + du), (v0 - 1.15, v0), 0.45, 'magsteel')
    B('mag_floor', (9.15, 10.95), (-8.9, -8.6), 0.5, 'magsteel')
    B('mag_release', (12.6, 12.95), (-2.0, -1.6), 0.3, 'parts')
    # --- polymer trigger group, trigger guard, raked pistol grip, selector
    B('lower', (12.6, 19.2), (-1.6, -0.6), 0.6, 'polymer')
    B('tg_front', (13.1, 13.4), (-3.1, -1.6), 0.22, 'polymer')
    B('tg_bottom', (13.2, 15.7), (-3.35, -3.05), 0.24, 'polymer')
    B('trigger', (14.1, 14.35), (-2.6, -1.6), 0.12, 'parts', rot=(-22.5, (14.2, -1.6)))
    for i in range(4):
        sh = 0.32 * i
        v0 = -1.6 - 1.0 * i
        B('grip_%d' % i, (15.6 + sh, 17.3 + sh), (v0 - 1.0, v0), 0.62, 'polymer')
    B('selector', (16.6, 17.6), (-1.3, -0.95), (-0.76, -0.6), 'parts')
    B('selector_hub', (17.3, 17.75), (-1.4, -0.85), (-0.7, -0.6), 'parts')
    # --- fixed A2 stock and rubber butt pad
    g.stair('stock', (21.0, 32.0), (1.55, 1.1), (-0.9, -3.4), 12, 0.62, 'polymer')
    B('buttpad', (32.0, 32.6), (-3.5, 1.2), 0.66, 'rubber')

    D = g.dec
    D(oval('F', 0, 0, 0.2, 0.2, els=['muzzle_a', 'muzzle_b'], col=(6, 6, 7)))
    D(stripes('TBRL', 'a', 0.27, 0.09, a=(0.05, 0.75), els=['muzzle_*'], mul=0.6))
    D(recess('L', (3.6, 9.8), (1.12, 1.38), els=['ctube_a', 'ctube_b'], lip=False))
    # claw-mount dimples on top, welds, ejection port, markings
    D(stripes('T', 'a', 1.6, 0.3, a=(11.0, 18.5), els=['receiver'], mul=0.6, offset=0.4))
    D(stripes('RL', 'b', 99, 0.08, b=(-0.15, -0.05), a=(10.6, 20.8), els=['receiver'], mul=0.65))
    D(recess('R', (11.0, 13.2), (0.0, 1.2), els=['receiver']))
    D(text('L', 'AXON MP5', 11.2, 1.35, els=['receiver'], col=(150, 152, 156), snap=True))
    D(paint('L', (17.0, 17.25), (-0.5, -0.3), (220, 220, 214), els=['receiver']))
    D(paint('L', (17.55, 17.8), (-0.5, -0.3), (200, 40, 30), els=['receiver']))
    D(stripes('RL', 'a', 0.8, 0.25, a=(3.7, 10.0), b=(-1.4, 0.5), els=['handguard'], mul=0.6))
    D(stripes('B', 'a', 0.8, 0.25, a=(3.7, 10.0), els=['handguard'], mul=0.6))
    D(paint('K', (-0.07, 0.07), (2.45, 2.6), (236, 236, 232), els=['fs_post']))
    D(stripes('RL', 'b', 0.2, 0.08, els=['rs_drum_*'], mul=0.6))
    for (a, b) in ((13.2, -1.1), (18.6, -1.1)):
        D(rivet('RL', a, b, 0.12, els=['lower']))
    D(hatch('RL', els=['grip_*'], period=0.3, mul=0.75, b=(-5.4, -1.8)))
    D(stripes('F', 'b', 0.35, 0.14, els=['grip_*'], mul=0.7))
    D(stripes('RL', 'b', 0.45, 0.12, els=['mag_*'], mul=1.2, add=6))
    D(stripes('K', 'b', 0.3, 0.12, els=['buttpad'], mul=0.7))
    D(rivet('RL', 22.0, 0.4, 0.14, els=['stock_*']))

    g.sight = dict(rear=(20.0, sl), front=(2.1, sl))
    # like the M16: eye just behind the rear aperture, 2.5deg cant
    g.ads = dict(cam=(24.3, sl), front=(2.1, sl), roll=2.5, sxyz=(1.0, 1.3, 0.72))
    g.grip = (16.6, -3.0)
    return g


def build_uzi():
    L = 21.8
    k = 17.5 / L
    g = Gun('uzi', dict(ax='z', s=1, k=k, kw=k * 1.25, Zm=-3.76, Yb=5.75, Xc=8.05))
    B, C = g.b, g.cyl
    sl = 2.35
    # --- barrel and nut
    C('barrel', (0.0, 3.4), 0.0, 0.36, 'blued')
    C('barrel_nut', (3.0, 3.7), 0.0, 0.66, 'black')
    # --- stamped receiver with top cover and cocking knob
    B('receiver', (3.6, 21.2), (-0.95, 1.05), 0.82, 'black')
    B('cover', (4.0, 20.9), (1.05, 1.3), 0.7, 'black')
    B('ch_knob', (9.0, 9.8), (1.3, 1.85), 0.32, 'parts')
    # protected front post and rear aperture between ears
    B('fs_base', (4.2, 5.2), (1.3, 1.5), 0.55, 'black')
    B('fs_ear_l', (4.4, 5.0), (1.5, 2.6), (-0.55, -0.36), 'black')
    B('fs_ear_r', (4.4, 5.0), (1.5, 2.6), (0.36, 0.55), 'black')
    B('fs_post', (4.6, 4.8), (1.5, sl), 0.08, 'parts')
    B('rs_base', (19.4, 20.6), (1.3, 1.5), 0.55, 'black')
    B('rs_ear_l', (19.8, 20.3), (1.5, 2.75), (-0.55, -0.36), 'black')
    B('rs_ear_r', (19.8, 20.3), (1.5, 2.75), (0.36, 0.55), 'black')
    B('rs_ap', (19.95, 20.15), (1.5, 2.05), (-0.36, 0.36), 'black')
    # --- ribbed forend, lower frame, big trigger guard
    B('forend', (4.6, 10.8), (-1.9, -0.95), 0.9, 'polymer')
    B('lower', (10.8, 18.6), (-1.6, -0.95), 0.7, 'black')
    B('tg_front', (11.0, 11.35), (-3.4, -1.6), 0.24, 'black')
    B('tg_bottom', (11.1, 13.45), (-3.65, -3.35), 0.26, 'black')
    B('trigger', (11.9, 12.15), (-2.9, -1.6), 0.12, 'parts', rot=(-22.5, (12.0, -1.6)))
    # --- pistol grip holding the magazine, grip safety, selector
    for i in range(3):
        sh = 0.12 * i
        v0 = -1.6 - 1.67 * i
        B('grip_%d' % i, (13.4 + sh, 15.8 + sh), (v0 - 1.67, v0), 0.78, 'polymer')
    B('grip_safety', (16.05, 16.4), (-4.4, -1.8), 0.5, 'parts')
    B('selector', (14.2, 15.2), (-1.45, -1.15), (-0.8, -0.7), 'parts')
    B('mag', (13.75, 15.25), (-9.4, -6.6), 0.48, 'magsteel')
    B('mag_floor', (13.65, 15.35), (-9.65, -9.4), 0.55, 'magsteel')
    B('mag_release', (15.55, 16.0), (-6.95, -6.55), 0.35, 'parts')
    # --- metal stock folded under the receiver: hinge, side arms, butt plate
    B('hinge', (21.2, 21.8), (-1.5, 0.9), 0.75, 'black')
    B('stock_arm_l', (16.9, 21.4), (-1.9, -1.55), (-0.86, -0.72), 'steel')
    B('stock_arm_r', (16.9, 21.4), (-1.9, -1.55), (0.72, 0.86), 'steel')
    B('butt_plate', (16.75, 17.1), (-2.9, -1.4), 0.86, 'black')
    B('butt_pad', (16.5, 16.75), (-2.8, -1.5), 0.8, 'rubber')

    D = g.dec
    D(oval('F', 0, 0, 0.22, 0.22, els=['barrel_a', 'barrel_b'], col=(6, 6, 7)))
    D(stripes('TBRL', 'a', 0.18, 0.07, els=['barrel_nut_*'], mul=0.6))
    # pressed flutes along the receiver sides, ejection port, cocking slot
    D(stripes('RL', 'b', 99, 0.14, b=(0.62, 0.9), a=(4.2, 20.6), els=['receiver'], mul=0.6))
    D(recess('R', (12.6, 15.0), (-0.2, 0.75), els=['receiver']))
    D(recess('T', (6.0, 15.0), (-0.1, 0.1), els=['cover'], lip=False))
    D(stripes('TRLF', 'b', 0.15, 0.06, els=['ch_knob'], mul=0.7))
    D(text('L', 'AXON 9MM', 5.0, 0.45, els=['receiver'], col=(150, 152, 156), snap=True))
    D(stripes('RL', 'a', 0.5, 0.18, a=(4.8, 10.6), els=['forend'], mul=0.6))
    D(stripes('B', 'a', 0.5, 0.18, a=(4.8, 10.6), els=['forend'], mul=0.6))
    D(paint('K', (-0.08, 0.08), (2.2, 2.35), (236, 236, 232), els=['fs_post']))
    D(paint('L', (14.25, 14.45), (-1.4, -1.2), (220, 220, 214), els=['lower']))
    for (a, b) in ((11.2, -1.3), (18.0, -1.3)):
        D(rivet('RL', a, b, 0.12, els=['lower']))
    D(hatch('RL', els=['grip_*'], period=0.3, mul=0.75, b=(-6.4, -1.8)))
    D(stripes('RL', 'b', 0.3, 0.1, els=['grip_safety'], mul=0.7))
    D(stripes('RL', 'b', 0.5, 0.14, els=['mag'], mul=1.2, add=6))
    D(stripes('F', 'b', 0.3, 0.12, els=['butt_pad'], mul=0.7))

    g.sight = dict(rear=(20.05, sl), front=(4.7, sl))
    g.ads = dict(cam=(24.0, sl), front=(4.7, sl), roll=2.5, scale=(0.8, 1.2, 1.0))
    g.grip = (14.6, -3.5)
    return g


def build_sg553():
    L = 35.0
    k = 21.69 / L
    g = Gun('sg553', dict(s=1, k=k, kw=k * 1.2, Xm=-6.438, Yb=9.81, Zc=2.28))
    B, C = g.b, g.cyl
    sl = 2.1
    # --- slotted flash hider, barrel, gas block with hooded front post, gas tube
    C('fh', (0.0, 1.6), 0.0, 0.42, 'black')
    C('barrel', (1.6, 7.4), 0.0, 0.3, 'black')
    B('fsb', (5.6, 7.2), (-0.55, 1.1), 0.45, 'black')
    B('fs_hood_l', (6.0, 6.6), (1.1, 2.5), (-0.46, -0.32), 'black')
    B('fs_hood_r', (6.0, 6.6), (1.1, 2.5), (0.32, 0.46), 'black')
    B('fs_hood_top', (6.0, 6.6), (2.38, 2.5), (-0.32, 0.32), 'black')
    B('fs_post', (6.2, 6.4), (1.1, sl), 0.07, 'parts')
    C('gas_tube', (7.2, 12.0), 0.85, 0.32, 'black')
    # --- ribbed polymer handguard
    B('handguard', (7.4, 14.5), (-1.35, 1.35), 0.85, 'polymer')
    # --- receiver with a short top rail and the rear diopter
    B('receiver', (14.5, 24.0), (-1.1, 1.45), 0.78, 'black')
    B('rail', (15.0, 22.0), (1.45, 1.75), 0.5, 'rail')
    B('rs_base', (22.2, 23.6), (1.45, 1.7), 0.55, 'black')
    B('rs_l', (22.6, 23.0), (1.7, 2.6), (-0.55, -0.2), 'black')
    B('rs_r', (22.6, 23.0), (1.7, 2.6), (0.2, 0.55), 'black')
    B('rs_top', (22.6, 23.0), (2.4, 2.6), (-0.2, 0.2), 'black')
    B('rs_bot', (22.6, 23.0), (1.7, 1.85), (-0.2, 0.2), 'black')
    # AK-style charging handle on the right
    B('ch_arm', (18.0, 18.5), (0.35, 0.75), (0.78, 1.25), 'parts')
    B('ch_knob', (17.9, 18.6), (0.25, 0.85), (1.2, 1.5), 'parts')
    # --- magwell and the translucent polymer magazine (slight curve)
    B('magwell', (15.0, 17.6), (-2.0, -1.1), 0.7, 'black')
    for i in range(4):
        du = -0.22 * i
        v0 = -2.0 - 1.4 * i
        B('mag_%d' % i, (15.2 + du, 17.3 + du), (v0 - 1.4, v0), 0.5, 'sigmag')
    B('mag_floor', (14.45, 16.75), (-7.85, -7.6), 0.55, 'polymer')
    # --- lower, trigger guard, raked grip, selector
    B('lower', (17.6, 24.0), (-1.6, -1.1), 0.7, 'black')
    B('tg_front', (18.3, 18.6), (-3.0, -1.6), 0.22, 'black')
    B('tg_bottom', (18.4, 20.9), (-3.25, -2.95), 0.24, 'black')
    B('trigger', (19.2, 19.45), (-2.5, -1.6), 0.12, 'parts', rot=(-22.5, (19.3, -1.6)))
    for i in range(4):
        sh = 0.35 * i
        v0 = -1.6 - 1.0 * i
        B('grip_%d' % i, (20.8 + sh, 22.4 + sh), (v0 - 1.0, v0), 0.62, 'polymer')
    B('selector', (21.6, 22.6), (-1.0, -0.65), (-0.9, -0.78), 'parts')
    # --- side-folding skeleton stock (extended): top bar, sloped lower bar, butt
    B('stock_hinge', (24.0, 24.6), (-1.2, 1.3), 0.7, 'black')
    B('stock_top', (24.6, 34.4), (0.6, 1.2), 0.55, 'polymer')
    g.stair('stock_bot', (24.6, 33.6), (-0.3, -1.6), (-0.9, -2.4), 10, 0.5, 'polymer')
    B('stock_post', (33.6, 34.4), (-2.4, 0.6), 0.52, 'polymer')
    B('buttpad', (34.4, 35.0), (-2.6, 1.3), 0.6, 'rubber')

    D = g.dec
    D(oval('F', 0, 0, 0.2, 0.2, els=['fh_a', 'fh_b'], col=(6, 6, 7)))
    D(stripes('TBRL', 'a', 99, 0.12, a=(0.25, 1.2), els=['fh_*'], mul=0.35))
    D(oval('RL', 6.4, 0.2, 0.15, 0.15, els=['fsb']))
    D(stripes('RL', 'a', 0.6, 0.2, a=(7.8, 14.2), b=(-1.0, 1.0), els=['handguard'], mul=0.6))
    D(stripes('T', 'a', 0.6, 0.2, a=(7.8, 14.2), els=['handguard'], mul=0.6))
    D(stripes('T', 'a', 0.4, 0.16, a=(15.1, 21.9), els=['rail'], mul=0.55))
    D(stripes('RL', 'a', 0.4, 0.16, a=(15.1, 21.9), els=['rail'], mul=0.6))
    D(recess('R', (18.8, 21.2), (-0.1, 0.9), els=['receiver']))
    D(text('L', 'AXON', 15.4, 1.15, els=['receiver'], col=(150, 152, 156), snap=True))
    for (a, b) in ((15.3, -0.6), (19.0, -0.6), (23.4, -0.6), (23.4, 0.9)):
        D(rivet('RL', a, b, 0.13, els=['receiver']))
    D(paint('K', (-0.07, 0.07), (1.95, 2.1), (236, 236, 232), els=['fs_post']))
    D(paint('L', (21.7, 21.95), (-1.5, -1.3), (220, 220, 214), els=['lower']))
    D(paint('L', (22.3, 22.55), (-1.5, -1.3), (200, 40, 30), els=['lower']))
    D(stripes('RL', 'b', 0.45, 0.12, els=['mag_*'], mul=0.8))
    D(oval('RL', 16.0, -2.6, 0.12, 0.12, els=['mag_0'], col=(120, 70, 30)))
    D(hatch('RL', els=['grip_*'], period=0.3, mul=0.75, b=(-5.4, -1.8)))
    D(stripes('F', 'b', 0.35, 0.14, els=['grip_*'], mul=0.7))
    D(stripes('K', 'b', 0.3, 0.12, els=['buttpad'], mul=0.7))
    D(stripes('T', 'a', 0.5, 0.2, a=(25.0, 33.8), els=['stock_top'], mul=0.8))

    g.sight = dict(rear=(22.8, sl), front=(6.3, sl))
    g.ads = dict(cam=(27.1, sl), front=(6.3, sl), roll=2.5, sxyz=(1.0, 1.3, 0.72))
    g.grip = (21.8, -3.0)
    return g


def build_famas():
    L = 36.0
    k = 21.25 / L
    g = Gun('famas', dict(ax='z', s=1, k=k, kw=k * 1.25, Zm=-3.0, Yb=6.45, Xc=8.0))
    B, C = g.b, g.cyl
    sl = 4.25           # sights sit on top of the long carry handle
    # --- barrel with flash hider and grenade rings, folded bipod along the handguard
    C('fh', (0.0, 1.2), 0.0, 0.45, 'black')
    C('barrel', (1.2, 4.2), 0.0, 0.3, 'black')
    C('gl_ring1', (1.5, 1.75), 0.0, 0.42, 'black')
    C('gl_ring2', (2.1, 2.35), 0.0, 0.42, 'black')
    B('bipod_hinge', (4.0, 4.8), (-0.6, 0.4), 1.1, 'black')
    B('bipod_l', (4.8, 12.5), (-0.3, 0.15), (-1.12, -0.92), 'black')
    B('bipod_r', (4.8, 12.5), (-0.3, 0.15), (0.92, 1.12), 'black')
    B('bipod_foot_l', (12.3, 12.8), (-0.45, 0.3), (-1.18, -0.9), 'black')
    B('bipod_foot_r', (12.3, 12.8), (-0.45, 0.3), (0.9, 1.18), 'black')
    # --- polymer body: handguard, receiver/stock, cheek rest, butt
    B('hg', (4.2, 13.0), (-1.6, 1.0), 0.9, 'polymer')
    B('body', (13.0, 34.5), (-2.2, 1.0), 0.95, 'polymer')
    B('body_low', (17.5, 34.5), (-3.2, -2.2), 0.9, 'polymer')
    B('cheek', (24.0, 32.5), (1.0, 1.6), 0.7, 'polymer')
    B('buttpad', (34.5, 36.0), (-3.4, 1.4), 0.95, 'rubber')
    # --- carry handle with the sights on top, charging lever underneath
    B('ch_front', (5.0, 6.2), (1.0, 3.6), 0.42, 'black')
    B('ch_rear', (21.0, 22.5), (1.0, 3.6), 0.42, 'black')
    B('ch_bar', (5.0, 22.5), (3.3, 3.75), 0.5, 'black')
    B('fs_ear_l', (5.0, 5.9), (3.75, 4.5), (-0.5, -0.32), 'black')
    B('fs_ear_r', (5.0, 5.9), (3.75, 4.5), (0.32, 0.5), 'black')
    B('fs_post', (5.35, 5.55), (3.75, sl), 0.07, 'parts')
    B('rs_l', (21.5, 22.0), (3.75, 4.75), (-0.5, -0.2), 'black')
    B('rs_r', (21.5, 22.0), (3.75, 4.75), (0.2, 0.5), 'black')
    B('rs_top', (21.5, 22.0), (4.55, 4.75), (-0.2, 0.2), 'black')
    B('rs_bot', (21.5, 22.0), (3.75, 3.95), (-0.2, 0.2), 'black')
    B('cock_lever', (13.5, 15.0), (1.0, 2.0), 0.2, 'parts')
    # --- full-hand trigger guard, grip, trigger
    B('trigger', (13.4, 13.65), (-3.0, -2.2), 0.12, 'parts', rot=(-22.5, (13.5, -2.2)))
    B('tg_front', (12.3, 12.7), (-5.6, -1.6), 0.25, 'polymer')
    B('tg_bottom', (12.4, 15.6), (-5.9, -5.6), 0.28, 'polymer')
    for i in range(4):
        sh = 0.25 * i
        v0 = -2.2 - 0.9 * i
        B('grip_%d' % i, (14.6 + sh, 16.2 + sh), (v0 - 0.9, v0), 0.62, 'polymer')
    # --- magazine behind the grip
    B('magwell', (18.2, 21.0), (-3.6, -3.2), 0.8, 'polymer')
    B('mag', (18.5, 20.7), (-6.6, -3.6), 0.5, 'magsteel')
    B('mag_floor', (18.4, 20.8), (-6.85, -6.6), 0.55, 'magsteel')

    D = g.dec
    D(oval('F', 0, 0, 0.22, 0.22, els=['fh_a', 'fh_b'], col=(6, 6, 7)))
    D(stripes('TBRL', 'a', 99, 0.12, a=(0.2, 1.0), els=['fh_*'], mul=0.4))
    D(stripes('RL', 'a', 0.7, 0.25, a=(5.0, 12.5), b=(-1.3, 0.7), els=['hg'], mul=0.6))
    D(recess('R', (23.0, 26.0), (-0.6, 0.6), els=['body']))
    D(recess('L', (23.0, 26.0), (-0.6, 0.6), els=['body'], col=(36, 36, 38)))
    D(text('L', 'AXON F1', 26.6, 0.4, els=['body'], col=(140, 142, 146), snap=True))
    D(recess('B', (6.5, 20.5), (-0.12, 0.12), els=['ch_bar'], lip=False))
    D(paint('K', (-0.07, 0.07), (4.1, 4.25), (236, 236, 232), els=['fs_post']))
    D(stripes('RL', 'b', 0.2, 0.08, els=['cock_lever'], mul=0.7))
    D(hatch('RL', els=['grip_*'], period=0.3, mul=0.75, b=(-5.6, -2.4)))
    D(stripes('RL', 'b', 0.45, 0.12, els=['mag'], mul=1.2, add=6))
    D(stripes('K', 'b', 0.3, 0.12, els=['buttpad'], mul=0.7))
    D(stripes('T', 'a', 0.5, 0.2, a=(24.5, 32.0), els=['cheek'], mul=0.8))
    for (a, b) in ((14.0, -1.2), (28.0, -1.4), (33.0, -1.4)):
        D(rivet('RL', a, b, 0.13, els=['body']))

    g.sight = dict(rear=(21.75, sl), front=(5.45, sl))
    g.ads = dict(cam=(25.2, sl), front=(5.45, sl), roll=2.5, scale=(0.8, 1.2, 1.0))
    g.grip = (15.6, -3.8)
    return g


def build_dragunov():
    L = 58.3
    k = 25.6 / L
    g = Gun('dragunov', dict(ax='z', s=1, k=k, kw=k * 1.25, Zm=-4.6, Yb=3.05, Xc=8.0))
    B, C, T = g.b, g.cyl, g.tube
    sl = 1.35
    # --- slotted flash hider, barrel, front sight with ears, bayonet lug, gas block
    C('fh', (0.0, 3.4), 0.0, 0.42, 'black')
    C('barrel', (3.4, 12.6), 0.0, 0.33, 'black')
    B('fs_base', (4.0, 5.0), (0.3, 0.75), 0.36, 'black')
    B('fs_ear_l', (4.1, 4.9), (0.75, 1.6), (-0.38, -0.24), 'black')
    B('fs_ear_r', (4.1, 4.9), (0.75, 1.6), (0.24, 0.38), 'black')
    B('fs_post', (4.4, 4.6), (0.75, sl), 0.06, 'parts')
    B('bay_lug', (5.2, 6.2), (-0.8, -0.3), 0.25, 'black')
    B('gas_block', (11.0, 12.6), (-0.5, 1.2), 0.45, 'black')
    # --- vented handguard halves, retainer
    B('hg_upper', (12.6, 24.6), (0.4, 1.25), 0.7, 'wood_ak')
    B('hg_lower', (12.6, 24.6), (-1.05, 0.4), 0.82, 'wood_ak')
    B('hg_retainer', (24.6, 25.2), (-1.1, 1.3), 0.85, 'black')
    # --- receiver with dust cover, rear leaf, charging handle and safety lever on the right
    B('rs_block', (25.2, 27.0), (0.6, 1.5), 0.55, 'black')
    B('rs_leaf', (25.4, 27.2), (1.5, 1.65), 0.45, 'black')
    B('receiver', (25.2, 39.0), (-1.2, 0.9), 0.8, 'black')
    B('cover', (27.0, 38.8), (0.9, 1.35), 0.66, 'black')
    B('ch_knob', (30.6, 31.4), (0.1, 0.65), (0.8, 1.3), 'parts')
    B('safety', (31.0, 36.0), (-0.2, 0.25), (0.8, 0.9), 'black')
    # --- PSO-style scope on a left side mount (hollow tube with a chevron reticle)
    sv = 3.4
    B('mount_base', (28.0, 33.0), (-0.2, 1.6), (-0.98, -0.8), 'black')
    B('mount_arm', (28.5, 32.5), (1.6, sv - 0.55), (-0.85, -0.45), 'black')
    T('shade', (24.6, 26.4), sv, 1.0, 0.82, 'black')
    T('obj', (26.4, 27.4), sv, 1.05, 0.82, 'black')
    T('scope', (27.4, 34.0), sv, 0.72, 0.6, 'black')
    T('ocular', (34.0, 35.6), sv, 0.9, 0.72, 'black')
    T('eyecup', (35.6, 37.6), sv, 0.95, 0.78, 'rubber')
    B('ret_v', (27.5, 27.6), (sv - 0.6, sv - 0.1), 0.03, 'reticle')
    B('ret_c', (27.5, 27.6), (sv - 0.04, sv + 0.06), 0.06, 'reticle')
    B('ret_h_l', (27.5, 27.6), (sv - 0.03, sv + 0.03), (-0.6, -0.18), 'reticle')
    B('ret_h_r', (27.5, 27.6), (sv - 0.03, sv + 0.03), (0.18, 0.6), 'reticle')
    B('turret_el', (30.0, 31.2), (sv + 0.72, sv + 1.35), 0.5, 'black')
    B('turret_wi', (30.0, 31.2), (sv - 0.5, sv + 0.5), (0.72, 1.3), 'black')
    B('turret_bat', (31.6, 32.3), (sv - 0.3, sv + 0.3), (-1.1, -0.72), 'black')
    # --- 10-rd magazine (slight curve), trigger guard, trigger
    for i in range(3):
        du = -0.25 * i
        v0 = -1.2 - 1.2 * i
        B('mag_%d' % i, (27.6 + du, 30.4 + du), (v0 - 1.2, v0), 0.5, 'magsteel')
    B('mag_floor', (27.0, 29.9), (-5.0, -4.8), 0.55, 'magsteel')
    B('tg_front', (31.4, 31.7), (-2.9, -1.2), 0.22, 'black')
    B('tg_bottom', (31.5, 34.6), (-3.15, -2.85), 0.24, 'black')
    B('trigger', (32.6, 32.85), (-2.5, -1.2), 0.12, 'parts', rot=(-22.5, (32.7, -1.2)))
    # --- thumbhole skeleton stock with cheek rest and steel butt plate
    B('stock_neck', (39.0, 41.0), (-1.6, 1.1), 0.72, 'wood_ak')
    B('stock_top', (41.0, 56.2), (0.2, 1.0), 0.66, 'wood_ak')
    B('cheek', (43.5, 50.5), (1.0, 1.7), 0.6, 'wood_ak')
    for i in range(4):
        sh = 0.35 * i
        v0 = -1.6 - 0.85 * i
        B('grip_%d' % i, (39.6 + sh, 41.4 + sh), (v0 - 0.85, v0), 0.66, 'wood_ak')
    g.stair('stock_low', (42.6, 56.2), (-3.9, -2.6), (-5.0, -6.2), 10, 0.62, 'wood_ak')
    B('butt', (56.2, 57.6), (-6.2, 1.0), 0.7, 'wood_ak')
    B('buttplate', (57.6, 58.3), (-6.3, 1.05), 0.74, 'black')

    D = g.dec
    D(oval('F', 0, 0, 0.2, 0.2, els=['fh_a', 'fh_b'], col=(6, 6, 7)))
    D(stripes('TBRL', 'a', 0.7, 0.25, a=(0.4, 3.0), els=['fh_*'], mul=0.35))
    for a0 in (14.0, 16.2, 18.4, 20.6, 22.8):
        D(oval('RL', a0 + 0.6, 0.85, 0.5, 0.16, els=['hg_upper']))
        D(oval('RL', a0 + 0.6, -0.35, 0.5, 0.16, els=['hg_lower']))
    D(stripes('TRL', 'a', 0.5, 0.14, a=(25.6, 27.0), els=['rs_leaf'], mul=1.4, add=8))
    D(recess('R', (32.0, 35.6), (-0.3, 0.75), els=['receiver']))
    D(stripes('TRL', 'a', 0.4, 0.14, a=(36.2, 38.6), els=['cover'], mul=0.6))
    D(text('L', 'AXON', 34.4, 0.55, els=['receiver'], col=(150, 152, 156), snap=True))
    for (a, b) in ((26.0, -0.6), (37.8, -0.6)):
        D(rivet('RL', a, b, 0.14, els=['receiver']))
    D(stripes('TBRL', 'a', 0.25, 0.1, els=['turret_*'], mul=0.6))
    D(stripes('TBRL', 'a', 0.3, 0.12, els=['eyecup_*'], mul=0.6))
    D(paint('K', (-0.06, 0.06), (1.2, 1.35), (236, 236, 232), els=['fs_post']))
    D(stripes('RL', 'b', 0.5, 0.14, els=['mag_*'], mul=1.2, add=6))
    D(hatch('RL', els=['grip_*'], period=0.3, mul=0.78))
    D(stripes('K', 'b', 0.3, 0.12, els=['buttplate'], mul=0.7))

    g.sight = dict(rear=(37.6, sv), front=(24.6, sv))
    # scope ADS like the AWP: eye behind the eyecup, gun squashed lengthwise so the tube view stays wide
    g.ads = dict(cam=(47.2, sv), front=(24.6, sv), roll=0.0, scale=(2.2, 2.2, 0.3))
    g.grip = (40.8, -2.8)
    return g


def build_kar98k():
    L = 52.9
    k = 21.8 / L
    g = Gun('kar98k', dict(ax='z', s=1, k=k, kw=k * 1.25, Zm=-3.0, Yb=6.52, Xc=8.0))
    B, C = g.b, g.cyl
    sl = 1.25
    # --- barrel, hooded front post, nose cap, cleaning rod, bayonet lug
    C('barrel', (0.0, 22.6), 0.0, 0.33, 'blued')
    B('fs_base', (0.6, 1.6), (0.3, 0.7), 0.3, 'blued')
    B('fs_hood_l', (0.7, 1.5), (0.7, 1.55), (-0.36, -0.24), 'blued')
    B('fs_hood_r', (0.7, 1.5), (0.7, 1.55), (0.24, 0.36), 'blued')
    B('fs_hood_top', (0.7, 1.5), (1.45, 1.55), (-0.24, 0.24), 'blued')
    B('fs_post', (1.0, 1.2), (0.7, sl), 0.06, 'parts')
    B('rod', (1.8, 2.6), (-0.7, -0.5), 0.08, 'steel')
    B('nose_cap', (2.6, 3.4), (-0.9, 0.5), 0.55, 'blued')
    B('bay_lug', (3.4, 4.6), (-0.98, -0.62), 0.25, 'blued')
    # --- full-length wood: forend, upper handguard, bands
    B('forend', (3.4, 22.6), (-1.05, 0.25), 0.62, 'wood_870')
    B('hg_top', (9.5, 20.6), (0.25, 0.62), 0.42, 'wood_870')
    B('band_front', (6.2, 6.8), (-1.12, 0.5), 0.66, 'blued')
    B('band_rear', (12.6, 13.1), (-1.12, 0.7), 0.66, 'blued')
    B('swivel', (12.7, 13.0), (-1.7, -1.12), 0.12, 'blued')
    # --- tangent rear sight, receiver, bolt with the turned-down handle, flag safety
    B('rs_base', (20.8, 22.6), (0.35, 0.75), 0.42, 'blued')
    B('rs_leaf', (21.0, 22.8), (0.75, 0.95), 0.38, 'blued')
    B('rs_l', (22.45, 22.8), (0.95, sl), (-0.38, -0.12), 'blued')
    B('rs_r', (22.45, 22.8), (0.95, sl), (0.12, 0.38), 'blued')
    B('receiver', (22.6, 30.0), (-0.75, 0.62), 0.5, 'blued')
    B('receiver_top', (23.0, 29.6), (0.62, 0.8), 0.3, 'blued')
    C('bolt', (28.0, 32.2), 0.35, 0.32, 'steel')
    B('bolt_arm', (30.2, 30.6), (-0.6, 0.3), (0.5, 1.2), 'steel')
    B('bolt_ball', (29.9, 30.9), (-1.25, -0.5), (1.0, 1.5), 'steel')
    B('shroud', (32.2, 33.0), (-0.1, 0.65), 0.28, 'blued')
    B('safety_flag', (32.4, 32.8), (0.65, 1.05), 0.12, 'blued')
    # --- stock under the action, floor plate, trigger guard
    B('stock_mid', (22.6, 33.0), (-1.6, -0.75), 0.66, 'wood_870')
    B('floorplate', (24.2, 28.6), (-1.75, -1.6), 0.42, 'blued')
    B('tg_front', (28.8, 29.1), (-2.6, -1.6), 0.2, 'blued')
    B('tg_bottom', (28.9, 31.4), (-2.85, -2.6), 0.22, 'blued')
    B('tg_rear', (31.2, 31.5), (-2.7, -1.6), 0.2, 'blued')
    B('trigger', (29.8, 30.05), (-2.3, -1.6), 0.12, 'parts', rot=(-22.5, (29.9, -1.6)))
    # --- wrist and butt with drop, steel butt plate
    B('wrist', (33.0, 35.4), (-2.4, 0.1), 0.6, 'wood_870')
    g.stair('stock', (35.4, 52.2), (0.1, -0.35), (-2.6, -4.6), 14, 0.68, 'wood_870')
    B('buttplate', (52.2, 52.9), (-4.7, -0.3), 0.7, 'blued')

    D = g.dec
    D(oval('F', 0, 0, 0.17, 0.17, els=['barrel_a', 'barrel_b'], col=(6, 6, 7)))
    D(stripes('TRL', 'a', 0.5, 0.14, a=(21.2, 22.6), els=['rs_leaf'], mul=1.4, add=8))
    D(paint('K', (-0.06, 0.06), (1.1, 1.25), (236, 236, 232), els=['fs_post']))
    D(recess('R', (26.8, 29.4), (0.05, 0.62), els=['receiver']))
    D(text('L', 'AXON', 23.2, 0.4, els=['receiver'], col=(170, 172, 176), snap=True))
    D(stripes('TBRL', 'a', 0.2, 0.08, els=['shroud'], mul=0.7))
    # stock disc, sling slot, finger grooves along the forend
    D(rivet('RL', 37.0, -1.2, 0.3, els=['stock_*'], cols=((150, 150, 154), (40, 22, 12))))
    D(recess('RL', (41.5, 43.3), (-2.2, -1.8), els=['stock_*'], col=(30, 18, 10)))
    D(stripes('RL', 'b', 99, 0.12, b=(-0.3, -0.15), a=(8.0, 19.0), els=['forend'], mul=0.65))

    g.sight = dict(rear=(22.6, sl), front=(1.1, sl))
    # like the SKS: eye behind the rear notch, 2.5deg cant
    g.ads = dict(cam=(31.6, sl), front=(1.1, sl), roll=2.5, scale=(0.72, 1.15, 1.0))
    g.grip = (34.0, -1.2)
    return g


def build_spas():
    L = 38.6
    k = 16.8 / L
    g = Gun('spas', dict(s=-1, k=k, kw=k * 1.25, Xm=16.0, Yb=10.75, Zc=4.25))
    B, C = g.b, g.cyl
    # --- barrel with a perforated heat shield, magazine tube, clamp
    C('barrel', (0.0, 26.2), 0.0, 0.36, 'black')
    B('shield', (0.8, 21.0), (-0.05, 0.6), 0.48, 'black')
    B('fs_post', (0.8, 1.2), (0.6, 1.0), 0.08, 'parts')
    C('magcap', (0.0, 0.6), -0.95, 0.48, 'black')
    C('magtube', (0.6, 31.0), -0.95, 0.42, 'black')
    B('clamp', (1.4, 2.0), (-1.5, 0.45), 0.5, 'black')
    # --- ribbed pump forend
    B('forend', (12.0, 24.0), (-1.75, 0.3), 0.82, 'polymer')
    # --- receiver, trigger group, raked pistol grip
    B('receiver', (26.0, 35.2), (-1.6, 1.1), 0.72, 'black')
    B('receiver_tail', (35.2, 38.6), (-1.4, 0.9), 0.6, 'black')
    B('mode_button', (24.6, 25.4), (-1.5, -1.1), 0.5, 'parts')
    B('tg_front', (29.4, 29.7), (-3.3, -1.6), 0.22, 'black')
    B('tg_bottom', (29.5, 32.0), (-3.55, -3.25), 0.24, 'black')
    B('trigger', (30.4, 30.65), (-2.8, -1.6), 0.12, 'parts', rot=(-22.5, (30.5, -1.6)))
    for i in range(4):
        sh = 0.35 * i
        v0 = -1.6 - 0.95 * i
        B('grip_%d' % i, (31.8 + sh, 33.5 + sh), (v0 - 0.95, v0), 0.62, 'polymer')
    B('safety', (32.0, 32.6), (-1.5, -1.2), (-0.8, -0.72), 'parts')
    # --- stock folded over the top, with the arm hook
    B('stock_hinge', (36.8, 38.0), (0.9, 1.8), 0.45, 'black')
    B('stock_bar', (23.6, 37.4), (1.25, 1.65), 0.3, 'black')
    B('butt', (22.9, 23.6), (0.8, 2.4), 0.6, 'black')
    B('hook', (21.9, 22.9), (2.0, 2.4), 0.3, 'black')
    B('hook_tip', (21.9, 22.3), (1.4, 2.0), 0.3, 'black')

    D = g.dec
    D(oval('F', 0, 0, 0.3, 0.3, els=['barrel_a', 'barrel_b'], col=(6, 6, 7)))
    D(oval('F', 0, -0.95, 0.2, 0.2, els=['magcap_a', 'magcap_b'], col=(40, 40, 42)))

    def shield_holes(ctx):
        if ctx.el.name != 'shield' or ctx.side not in 'RLT':
            return
        A, Bv = ab(ctx)
        bc = 0.0 if ctx.side == 'T' else 0.28
        da = (A - 1.6) % 0.9 - 0.45
        hole = (A > 1.4) & (A < 20.6) & (da ** 2 / 0.05 + (Bv - bc) ** 2 / 0.03 < 1)
        ctx.col[hole] = np.array([10, 10, 11], float)
        ctx.flat[hole] = True
    D(custom(shield_holes))
    D(stripes('RL', 'a', 0.7, 0.25, a=(12.5, 23.5), b=(-1.5, 0.1), els=['forend'], mul=0.55))
    D(stripes('B', 'a', 0.7, 0.25, a=(12.5, 23.5), els=['forend'], mul=0.55))

    def shell_inner(ctx, m, A, Bv):
        mm = m & (Bv < 0.6)
        ctx.col[mm] = np.array([156, 30, 26], float)
        ctx.col[mm & (A > 30.4)] = np.array([186, 146, 64], float)
    D(recess('R', (27.4, 31.0), (-0.6, 0.85), els=['receiver'], inner=shell_inner))
    D(recess('B', (27.0, 31.5), (-0.4, 0.4), els=['receiver']))
    D(text('L', 'AXON', 27.2, 0.6, els=['receiver'], col=(150, 152, 156), snap=True))
    for (a, b) in ((26.6, -1.2), (34.6, -1.2)):
        D(rivet('RL', a, b, 0.14, els=['receiver']))
    D(hatch('RL', els=['grip_*'], period=0.3, mul=0.75, b=(-5.2, -1.8)))
    D(stripes('F', 'b', 0.35, 0.14, els=['grip_*'], mul=0.7))
    D(stripes('RL', 'a', 0.6, 0.2, a=(24.2, 37.0), els=['stock_bar'], mul=0.7))

    g.sight = dict(rear=(36.5, 1.65), front=(1.0, 1.0))
    # like the Remington: no true sights, the eye looks along the top of the gun
    g.ads = dict(cam=(56.0, 2.8), front=(1.0, 1.0))
    g.grip = (33.0, -3.0)
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
    if m.get('glow'):     # skins: crisp, even outline on every convex edge instead of wear
        amt = ((ef > 0.45) * m.get('edge', 0.5))[:, None]
    else:
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
    dens = getattr(g, 'density', DENSITY)
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
            ax, ang = g.mc_rot(e.rot[0])
            j['rotation'] = {'angle': ang + 0.0, 'axis': ax, 'origin': [r4(c) for c in org]}
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
    if 'scale' in g.ads:          # absolute ADS scale (new guns; QA's off-hand scales are often squashed)
        S = np.array(g.ads['scale'], float)
    S = S * g.ads.get('sf', 1.0) * np.array(g.ads.get('sxyz', (1.0, 1.0, 1.0)), float)
    yaw_json = g.ads_yaw()
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


BUILDERS = {'ak47': build_ak, 'm4a1s': build_m4, 'remmington': build_870, 'makarov': build_pm,
            'awp': build_awp, 'mac10': build_mac10, 'm16': build_m16, 'sks': build_sks,
            'deagle': build_deagle, 'sw1911': build_sw1911, 'p30': build_p30,
            'mp5': build_mp5, 'uzi': build_uzi, 'sg553': build_sg553, 'famas': build_famas,
            'dragunov': build_dragunov, 'kar98k': build_kar98k, 'spas': build_spas}

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
    for name, (base, painter, cmd, _) in SKINS.items():
        if len(sys.argv) > 1 and name not in sys.argv[1:] and base not in sys.argv[1:]:
            continue
        g = BUILDERS[base]()
        dsp, _ = ads_display(g, disp[base])
        saved = dict(MATS)
        MATS.update(painter(g))
        try:
            model, img, dens, nf = build_model(g, 'qualityarmory:axon/' + name, dsp)
        finally:
            MATS.clear()
            MATS.update(saved)
        model['credit'] = 'AXON guns - %s skin, generated by gen.py' % name
        json.dump(model, open(os.path.join(OUT, name + '.json'), 'w'), indent=1)
        Image.fromarray(img, 'RGBA').save(os.path.join(OUT, name + '.png'))
        print(name, 'skin of', base, 'custom_model_data', cmd, 'density', dens)
