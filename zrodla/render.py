#!/usr/bin/env python3
"""Tiny software renderer for Minecraft Java block/item models (JSON + PNG).

- reads elements, element rotation, per-face uv (+face rotation), texture refs
- orthographic or perspective camera, z-buffer, back-face culling, nearest texel
  sampling (like Minecraft), perspective-correct uv
- helpers that reproduce Minecraft's display-transform chain for GUI,
  first person (right / left hand) and third person (with a stand-in player)
"""
import json, math, os
import numpy as np
from PIL import Image

FACE_N = {'north': (0, 0, -1), 'south': (0, 0, 1), 'east': (1, 0, 0),
          'west': (-1, 0, 0), 'up': (0, 1, 0), 'down': (0, -1, 0)}


def face_corners(f, t, face):
    """Corners TL, TR, BR, BL of a face as Minecraft maps uv (u1,v1)..(u2,v2)."""
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


def auto_uv(f, t, face):
    x1, y1, z1 = f
    x2, y2, z2 = t
    return {
        'north': [16 - x2, 16 - y2, 16 - x1, 16 - y1],
        'south': [x1, 16 - y2, x2, 16 - y1],
        'east':  [16 - z2, 16 - y2, 16 - z1, 16 - y1],
        'west':  [z1, 16 - y2, z2, 16 - y1],
        'up':    [x1, z1, x2, z2],
        'down':  [x1, 16 - z2, x2, 16 - z1],
    }[face]


def rot_axis(axis, deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    if axis == 'x':
        return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    if axis == 'y':
        return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def rot_xyz(r):
    return rot_axis('x', r[0]) @ rot_axis('y', r[1]) @ rot_axis('z', r[2])


def euler_xyz(R):
    b = math.asin(max(-1, min(1, R[0, 2])))
    c = math.atan2(-R[0, 1], R[0, 0])
    a = math.atan2(-R[1, 2], R[2, 2])
    return [math.degrees(a), math.degrees(b), math.degrees(c)]


def load_model(path, resolve):
    """resolve('ns:path') -> png file path."""
    m = json.load(open(path))
    texs = m.get('textures', {})

    def tex_of(ref):
        seen = 0
        while ref.startswith('#') and seen < 10:
            ref = texs.get(ref[1:], '')
            seen += 1
        return ref
    cache = {}
    quads = []
    for el in m['elements']:
        f, t = el['from'], el['to']
        rot = el.get('rotation')
        if rot and rot.get('angle', 0):
            R = rot_axis(rot['axis'], rot['angle'])
            o = np.array(rot['origin'], float)
        else:
            R, o = None, None
        for face, fd in el.get('faces', {}).items():
            ref = tex_of(fd.get('texture', ''))
            if ref not in cache:
                p = resolve(ref)
                cache[ref] = np.asarray(Image.open(p).convert('RGBA'), dtype=np.float32) if p else None
            tex = cache[ref]
            if tex is None:
                continue
            uv = fd.get('uv') or auto_uv(f, t, face)
            P = np.array(face_corners(f, t, face), float)
            n = np.array(FACE_N[face], float)
            if R is not None:
                P = (P - o) @ R.T + o
                n = R @ n
            th, tw = tex.shape[:2]
            u1, v1, u2, v2 = [c / 16.0 for c in uv]
            UV = [(u1 * tw, v1 * th), (u2 * tw, v1 * th), (u2 * tw, v2 * th), (u1 * tw, v2 * th)]
            r = int(fd.get('rotation', 0)) // 90
            UV = UV[-r:] + UV[:-r] if r else UV
            quads.append(dict(P=P, UV=np.array(UV), tex=tex, n=n,
                              box=(min(uv[0], uv[2]) / 16 * tw, min(uv[1], uv[3]) / 16 * th,
                                   max(uv[0], uv[2]) / 16 * tw, max(uv[1], uv[3]) / 16 * th)))
    return m, quads


def box_quads(f, t, color, xf=None):
    """Untextured box (for stand-in player limbs). xf: fn(N,3)->(N,3) affine."""
    out = []
    for face in FACE_N:
        P = np.array(face_corners(f, t, face), float)
        n = np.array(FACE_N[face], float)
        if xf is not None:
            P2 = xf(P)
            n = xf(np.array([n]) + P[:1])[0] - xf(P[:1])[0]
            n /= np.linalg.norm(n) + 1e-9
            P = P2
        out.append(dict(P=P, color=np.array(color, float), n=n))
    return out


class Canvas:
    def __init__(self, W, H, bg=(40, 44, 52), ss=2, grad=None):
        self.W, self.H, self.ss = W, H, ss
        w, h = W * ss, H * ss
        self.col = np.zeros((h, w, 3), np.float32)
        if grad:
            top, bot = np.array(grad[0], float), np.array(grad[1], float)
            k = np.linspace(0, 1, h)[:, None, None]
            self.col[:] = top * (1 - k) + bot * k
        else:
            self.col[:] = bg
        self.z = np.full((h, w), -1e9, np.float32)

    def image(self):
        im = Image.fromarray(np.clip(self.col, 0, 255).astype(np.uint8))
        if self.ss > 1:
            im = im.resize((self.W, self.H), Image.LANCZOS)
        return im


def _clip_near(Pc, UV, near):
    """Sutherland-Hodgman clip of a polygon against plane z = -near (keep z <= -near)."""
    out_p, out_u = [], []
    n = len(Pc)
    for i in range(n):
        a, b = Pc[i], Pc[(i + 1) % n]
        ua, ub = UV[i], UV[(i + 1) % n]
        ina, inb = a[2] <= -near, b[2] <= -near
        if ina:
            out_p.append(a); out_u.append(ua)
        if ina != inb:
            t = (-near - a[2]) / (b[2] - a[2])
            out_p.append(a + t * (b - a)); out_u.append(ua + t * (ub - ua))
    return np.array(out_p), np.array(out_u)


def draw(cv, quads, xform, project, light, cull=True, near=None):
    """xform: model pts -> camera space (x right, y up, z toward viewer).
    project: camera pts -> (sx, sy, depth, w); w = perspective divisor (1 for ortho).
    near: if set, polygons are clipped at z = -near (perspective views)."""
    ss = cv.ss
    h, w = cv.z.shape
    for q in quads:
        Pc = xform(q['P'])
        nc = xform(q['P'][:1] + q['n'][None]) - xform(q['P'][:1])
        nc = nc[0] / (np.linalg.norm(nc[0]) + 1e-9)
        UV = q['UV'] if 'UV' in q else np.zeros((4, 2))
        if near is not None:
            if np.all(Pc[:, 2] > -near):
                continue
            if np.any(Pc[:, 2] > -near):
                Pc, UV = _clip_near(Pc, UV, near)
                if len(Pc) < 3:
                    continue
        sx, sy, dep, iw = project(Pc)
        sx = sx * ss
        sy = sy * ss
        # front faces wind clockwise on screen (TL,TR,BR,...; y down)
        area = 0.0
        for i in range(len(sx)):
            j = (i + 1) % len(sx)
            area += sx[i] * sy[j] - sx[j] * sy[i]
        if cull and area <= 0:
            continue
        if not np.all(np.isfinite(sx)):
            continue
        shade = light(nc)
        qq = dict(q, UV=UV)
        for k in range(1, len(sx) - 1):
            _tri(cv, qq, (0, k, k + 1), sx, sy, dep, iw, shade, h, w)


def _tri(cv, q, tri, sx, sy, dep, iw, shade, h, w):
    i0, i1, i2 = tri
    xs = np.array([sx[i0], sx[i1], sx[i2]])
    ys = np.array([sy[i0], sy[i1], sy[i2]])
    x0, x1 = int(max(0, math.floor(xs.min()))), int(min(w - 1, math.ceil(xs.max())))
    y0, y1 = int(max(0, math.floor(ys.min()))), int(min(h - 1, math.ceil(ys.max())))
    if x1 < x0 or y1 < y0:
        return
    X, Y = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
    d = (ys[1] - ys[2]) * (xs[0] - xs[2]) + (xs[2] - xs[1]) * (ys[0] - ys[2])
    if abs(d) < 1e-9:
        return
    a = ((ys[1] - ys[2]) * (X - xs[2]) + (xs[2] - xs[1]) * (Y - ys[2])) / d
    b = ((ys[2] - ys[0]) * (X - xs[2]) + (xs[0] - xs[2]) * (Y - ys[2])) / d
    c = 1 - a - b
    m = (a >= -1e-6) & (b >= -1e-6) & (c >= -1e-6)
    if not m.any():
        return
    wv = np.array([iw[i0], iw[i1], iw[i2]])
    ww = a * wv[0] + b * wv[1] + c * wv[2]
    z = (a * dep[i0] * wv[0] + b * dep[i1] * wv[1] + c * dep[i2] * wv[2]) / ww
    zb = cv.z[y0:y1 + 1, x0:x1 + 1]
    m &= z > zb
    if not m.any():
        return
    if 'tex' in q:
        UV = q['UV']
        u = (a * UV[i0, 0] * wv[0] + b * UV[i1, 0] * wv[1] + c * UV[i2, 0] * wv[2]) / ww
        v = (a * UV[i0, 1] * wv[0] + b * UV[i1, 1] * wv[1] + c * UV[i2, 1] * wv[2]) / ww
        bx = q['box']
        u = np.clip(u, bx[0], max(bx[0], bx[2] - 1e-3))
        v = np.clip(v, bx[1], max(bx[1], bx[3] - 1e-3))
        tex = q['tex']
        ui = np.clip(u.astype(int), 0, tex.shape[1] - 1)
        vi = np.clip(v.astype(int), 0, tex.shape[0] - 1)
        texel = tex[vi, ui]
        m &= texel[..., 3] > 25
        rgb = texel[..., :3]
    else:
        rgb = np.broadcast_to(q['color'], X.shape + (3,))
    cb = cv.col[y0:y1 + 1, x0:x1 + 1]
    cb[m] = rgb[m] * shade
    zb[m] = z[m]


# ---------------------------------------------------------------- lights
def light_preview(n):
    L0 = np.array([-0.45, 0.75, 0.55]); L0 /= np.linalg.norm(L0)
    L1 = np.array([0.6, 0.2, 0.4]); L1 /= np.linalg.norm(L1)
    return min(1.25, 0.42 + 0.62 * max(0, n @ L0) + 0.25 * max(0, n @ L1))


def light_mc3d(n):
    L0 = np.array([0.2, 1.0, -0.7]); L0 /= np.linalg.norm(L0)
    L1 = np.array([-0.2, 1.0, 0.7]); L1 /= np.linalg.norm(L1)
    return min(1.0, 0.4 + 0.6 * (max(0, n @ L0) + max(0, n @ L1)))


def light_flat(n):
    return min(1.0, 0.62 + 0.38 * max(0.0, n[2]) + 0.12 * n[1])


# ---------------------------------------------------------------- cameras
def ortho_view(yaw, pitch):
    """Rotation turning model space into camera space; yaw about Y, then pitch about X."""
    return rot_axis('x', pitch) @ rot_axis('y', yaw)


def fit_ortho(quads_list, R, W, H, margin=0.06, center=None):
    pts = np.concatenate([q['P'] for q in quads_list]) @ R.T
    mn, mx = pts.min(0), pts.max(0)
    s = min(W * (1 - 2 * margin) / (mx[0] - mn[0]), H * (1 - 2 * margin) / (mx[1] - mn[1]))
    c = (mn + mx) / 2

    def xform(P):
        return P @ R.T

    def project(Pc):
        return (W / 2 + (Pc[:, 0] - c[0]) * s, H / 2 - (Pc[:, 1] - c[1]) * s, Pc[:, 2], np.ones(len(Pc)))
    return xform, project, s


def display_matrix(d):
    R = rot_xyz(d.get('rotation', [0, 0, 0]))
    S = np.array(d.get('scale', [1, 1, 1]), float)
    T = np.array(d.get('translation', [0, 0, 0]), float) / 16.0
    return R, S, T


def apply_display(P, d, left=False):
    """Model units -> item space (blocks), Minecraft ItemTransform.apply semantics."""
    r = list(d.get('rotation', [0, 0, 0]))
    t = list(d.get('translation', [0, 0, 0]))
    if left:
        r = [r[0], -r[1], -r[2]]
        t = [-t[0], t[1], t[2]]
    R = rot_xyz(r)
    S = np.array(d.get('scale', [1, 1, 1]), float)
    return np.array(t) / 16.0 + ((P / 16.0 - 0.5) * S) @ R.T


def first_person(display, W, H, left=False, fov=70.0, charged=False):
    """charged=True adds vanilla's extra main-hand transform for a *charged crossbow*
    (translate x -0.641864, rotate Y 10deg), which applies when QA guns are charged crossbows."""
    key = 'firstperson_lefthand' if left else 'firstperson_righthand'
    d = display.get(key) or display.get('firstperson_righthand', {})
    arm = np.array([-0.56 if left else 0.56, -0.52, -0.72])
    f = (H / 2) / math.tan(math.radians(fov / 2))
    Rc = rot_axis('y', 10.0)

    def xform(P):
        p = apply_display(P, d, left)
        if charged and not left:
            return arm + np.array([-0.641864, 0, 0]) + p @ Rc.T
        return p + arm

    def project(Pc):
        zz = -Pc[:, 2]
        zz = np.where(zz < 0.05, 1e-4, zz)
        return (W / 2 + Pc[:, 0] / zz * f, H / 2 - Pc[:, 1] / zz * f, Pc[:, 2], 1.0 / zz)
    return xform, project


def gui_view(display, px):
    d = display.get('gui', {})

    def xform(P):
        return apply_display(P, d)

    def project(Pc):
        return (px / 2 + Pc[:, 0] * px, px / 2 - Pc[:, 1] * px, Pc[:, 2], np.ones(len(Pc)))
    return xform, project


def arm_pose_world(xrot, yrot, zrot=0.0):
    """ModelPart rotation (radians, ZYX like vanilla) converted to player/world space."""
    F = np.diag([1.0, -1.0, -1.0])
    Rm = rot_axis('z', math.degrees(zrot)) @ rot_axis('y', math.degrees(yrot)) @ rot_axis('x', math.degrees(xrot))
    return F @ Rm @ F


CROSSBOW_R = (-math.pi / 2 + 0.1, -0.3)
CROSSBOW_L = (-1.5, 0.6)


def third_person_world(display, left=False, arm_pitch=-18.0, crossbow=True):
    """Model -> player space (feet at origin, player faces +Z, player's right is -X)."""
    key = 'thirdperson_lefthand' if left else 'thirdperson_righthand'
    d = display.get(key) or display.get('thirdperson_righthand', {})
    side = 1 if left else -1
    pivot = np.array([side * 5 / 16.0, 1.375, 0.0])
    B = np.array([[-1, 0, 0], [0, 0, 1], [0, 1, 0]], float).T  # columns: item X,Y,Z in player space
    if left:
        B = np.array([[-1, 0, 0], [0, 0, 1], [0, 1, 0]], float).T
    Ra = arm_pose_world(*CROSSBOW_R) if crossbow else rot_axis('x', arm_pitch)
    off = np.array([(-1 if left else 1) / 16.0, 0.125, -0.625])

    def xf(P):
        it = apply_display(P, d, left) + off
        return pivot + (it @ B.T) @ Ra.T
    return xf, pivot, Ra, B


def player_quads(arm_pitch=-18.0, gun_hand='right', crossbow=True):
    skin = (196, 150, 118); shirt = (40, 160, 170); pants = (60, 60, 150); hair = (70, 45, 25)
    q = []
    q += box_quads((-4 / 16, 1.5, -4 / 16), (4 / 16, 2.0, 4 / 16), skin)
    q += box_quads((-4.2 / 16, 1.92, -4.2 / 16), (4.2 / 16, 2.03, 4.2 / 16), hair)
    q += box_quads((-4 / 16, 0.75, -2 / 16), (4 / 16, 1.5, 2 / 16), shirt)
    q += box_quads((-4 / 16, 0, -2 / 16), (0, 0.75, 2 / 16), pants)
    q += box_quads((0, 0, -2 / 16), (4 / 16, 0.75, 2 / 16), pants)
    # arms: right arm at -X (player's right), pivot at shoulder
    Ra = arm_pose_world(*CROSSBOW_R) if crossbow else rot_axis('x', arm_pitch)
    La = arm_pose_world(*CROSSBOW_L) if crossbow else np.eye(3)
    pr = np.array([-5 / 16, 1.375, 0])
    pl = np.array([5 / 16, 1.375, 0])

    def xr(P):
        return pr + (P - pr) @ Ra.T

    def xl(P):
        return pl + (P - pl) @ La.T
    q += box_quads((-8 / 16, 0.75, -2 / 16), (-4 / 16, 1.5, 2 / 16), shirt, xr)
    q += box_quads((-8.05 / 16, 0.745, -2.05 / 16), (-3.95 / 16, 0.9, 2.05 / 16), skin, xr)
    q += box_quads((4 / 16, 0.75, -2 / 16), (8 / 16, 1.5, 2 / 16), shirt, xl)
    q += box_quads((3.95 / 16, 0.745, -2.05 / 16), (8.05 / 16, 0.9, 2.05 / 16), skin, xl)
    return q


def resolver_for(pack_root):
    def resolve(ref):
        if not ref:
            return None
        ns, p = ref.split(':', 1) if ':' in ref else ('minecraft', ref)
        f = os.path.join(pack_root, 'assets', ns, 'textures', p + '.png')
        return f if os.path.exists(f) else None
    return resolve
