"""Modele z teksturą liczoną proceduralnie na każdej ścianie (stanowiska, wraki, maszyny).

Stare modele brały kafelek 8×8 z atlasu i rozciągały go na ścianę, więc blat 16 jednostek i noga
2 jednostki miały ziarno drewna w różnej skali, a bryły nachodziły na siebie i migały. Tu:

* każda widoczna ściana dostaje własny prostokąt w teksturze modelu, 4 piksele na jednostkę
  (64 na blok) niezależnie od wielkości ściany, więc skala jest wszędzie ta sama;
* materiał (drewno, stal, emalia, rdza...) jest funkcją współrzędnych świata, więc słoje i rysy
  przechodzą przez krawędzie brył bez szwów;
* ściany zasłonięte przez sąsiednią bryłę i spody przy ziemi nie są w ogóle rysowane;
* dwie ściany leżące w jednej płaszczyźnie (powód migania) rozsuwane są o 0,03 jednostki;
* zacienienie przy stykach brył (ambient occlusion) jest wypalone w teksturze.

Układ ścian jak w Minecrafcie: patrząc na ścianę z zewnątrz, u rośnie w prawo, v w dół.
"""
import math

import numpy as np
from PIL import Image

from .model import Model, _point_90, _FACE_90

FACES = ('north', 'south', 'east', 'west', 'up', 'down')
NORMAL = {'north': (0, 0, -1), 'south': (0, 0, 1), 'east': (1, 0, 0), 'west': (-1, 0, 0),
          'up': (0, 1, 0), 'down': (0, -1, 0)}
AXIS = {'north': 2, 'south': 2, 'east': 0, 'west': 0, 'up': 1, 'down': 1}

DENSITY = 4          # pikseli tekstury na jednostkę modelu
GUTTER = 2           # powielone piksele wokół prostokąta ściany (bez przeciekania przy mipmapach)
PULL = 0.03          # o ile cofamy ścianę, która leży w jednej płaszczyźnie z inną


# ---------------------------------------------------------------- szum

def _hash(ix, iy, iz, seed):
    a = ix.astype(np.uint64) * np.uint64(374761393)
    b = iy.astype(np.uint64) * np.uint64(668265263)
    c = iz.astype(np.uint64) * np.uint64(2147483629)
    h = (a + b + c + np.uint64(seed * 1274126177 + 1013904223)) & np.uint64(0xFFFFFFFF)
    h = ((h ^ (h >> np.uint64(13))) * np.uint64(1274126177)) & np.uint64(0xFFFFFFFF)
    h = h ^ (h >> np.uint64(16))
    return (h & np.uint64(0xFFFF)).astype(np.float64) / 65535.0


def vnoise(x, y, z, seed=0):
    """Szum wartościowy 3D w zakresie 0..1."""
    x0, y0, z0 = np.floor(x), np.floor(y), np.floor(z)
    fx, fy, fz = x - x0, y - y0, z - z0
    sx, sy, sz = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy), fz * fz * (3 - 2 * fz)
    x0, y0, z0 = x0.astype(np.int64), y0.astype(np.int64), z0.astype(np.int64)
    out = 0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (sx if dx else 1 - sx) * (sy if dy else 1 - sy) * (sz if dz else 1 - sz)
                out = out + w * _hash(x0 + dx, y0 + dy, z0 + dz, seed)
    return out


def fbm(x, y, z, seed=0, octaves=3):
    total, amp, norm = 0, 1.0, 0
    for o in range(octaves):
        total = total + amp * vnoise(x, y, z, seed + o * 17)
        norm += amp
        x, y, z, amp = x * 2.03, y * 2.03, z * 2.03, amp * 0.5
    return total / norm


def smooth(lo, hi, x):
    t = np.clip((x - lo) / (hi - lo), 0, 1)
    return t * t * (3 - 2 * t)


# ---------------------------------------------------------------- kontekst ściany

class Ctx:
    """Współrzędne jednej ściany: tablice (h, w) wartości w jednostkach modelu."""

    def __init__(self, box, face, X, Y, Z, E, seed):
        self.box, self.face, self.X, self.Y, self.Z, self.E, self.seed = box, face, X, Y, Z, E, seed
        self.shape = X.shape
        dims = [box.to[i] - box.frm[i] for i in range(3)]
        n_axis = AXIS[face]
        # oś słojów: najdłuższy wymiar bryły; jeśli to normalna ściany, jest to czoło deski
        long_axis = max(range(3), key=lambda i: dims[i])
        in_dims = [dims[i] for i in range(3) if i != n_axis]
        self.end = long_axis == n_axis and max(in_dims) <= 3.5
        if long_axis == n_axis:
            in_plane = [i for i in range(3) if i != n_axis]
            long_axis = max(in_plane, key=lambda i: dims[i])
        self.grain_axis = long_axis
        across = [i for i in range(3) if i not in (long_axis, n_axis)]
        self.across_axis = across[0] if across else long_axis
        coords = (X, Y, Z)
        self.g = coords[long_axis]
        self.c = coords[self.across_axis]
        self.center = [(box.frm[i] + box.to[i]) / 2 for i in range(3)]
        self.dims = dims

    def noise(self, sx, sy, sz, seed=0, octaves=1):
        return fbm(self.X * sx, self.Y * sy, self.Z * sz, self.seed + seed, octaves) if octaves > 1 \
            else vnoise(self.X * sx, self.Y * sy, self.Z * sz, self.seed + seed)

    def streak(self, along, across, seed=0, octaves=2):
        """Szum rozciągnięty wzdłuż słojów: along/across to gęstość cech na jednostkę."""
        a = [0, 0, 0]
        a[self.grain_axis] = along
        a[self.across_axis] += across
        # trzecia oś (normalna) dostaje szum nisko-częstotliwościowy, żeby ściany różniły się
        for i in range(3):
            if a[i] == 0:
                a[i] = across
        return fbm(self.X * a[0], self.Y * a[1], self.Z * a[2], self.seed + seed, octaves)


def rgb(c):
    return np.array(c, dtype=np.float64)


def lerp(a, b, t):
    t = t[..., None] if hasattr(t, 'ndim') else t
    return a + (b - a) * t


# ---------------------------------------------------------------- materiały
# Każdy materiał: f(ctx) -> tablica (h, w, 3) kolorów 0..255.

def edge_wear(ctx, col, width=0.2, amount=0.10):
    """Jaśniejszy brzeg bryły: świeci tam, gdzie farba się ściera."""
    k = smooth(width, 0.0, ctx.E)[..., None]
    return col * (1 + amount * k)


def wood(ctx, base, plank=3.0, aged=0.0):
    """Deski wzdłuż najdłuższego wymiaru: szwy, słoje, styki czołowe, gwoździe."""
    g, c, box = ctx.g, ctx.c, ctx.box
    if ctx.end:
        # czoło deski: pierścienie roczne wokół środka przekroju
        ax = [i for i in range(3) if i != AXIS[ctx.face]]
        co = (ctx.X, ctx.Y, ctx.Z)
        da = co[ax[0]] - ctx.center[ax[0]]
        db = co[ax[1]] - ctx.center[ax[1]]
        r = np.hypot(da, db * 1.0)
        rings = np.sin(r * 4.2 + ctx.noise(0.5, 0.5, 0.5, 9) * 3) * 0.5 + 0.5
        col = rgb(base) * (0.78 + 0.16 * rings)[..., None]
        return edge_wear(ctx, col, 0.12, 0.04)
    off = ((int(box.frm[0] * 7 + box.frm[1] * 13 + box.frm[2] * 29) * 2654435761) % 1000) / 1000.0 * plank
    idx = np.floor((c + off) / plank).astype(np.int64)
    local = (c + off) - idx * plank
    z = np.zeros_like(idx)
    r1 = _hash(idx, z + ctx.grain_axis, z, ctx.seed + 3)
    r2 = _hash(idx, z + 1, z, ctx.seed + 5)
    # styki czołowe: każda deska ucięta w innym miejscu
    seg_len = 10.0 + 4.0 * r2
    gi = np.floor((g + r1 * 17.0) / seg_len).astype(np.int64)
    r3 = _hash(idx, gi, z + 2, ctx.seed + 7)
    tone = 1 + (r1 * 0.5 + r3 * 0.5 - 0.5) * 0.30
    col = rgb(base) * tone[..., None]
    col = col * np.stack([1 + (r3 - 0.5) * 0.08, np.ones_like(r3), 1 - (r3 - 0.5) * 0.10], axis=-1)
    # słoje: cienkie wydłużone linie wijące się wzdłuż deski
    warp = vnoise(g * 0.09, c * 0.6, idx * 1.0, ctx.seed + 11) * 2.2
    lines = np.sin((local * 2.9 + warp + r3 * 6.0) * 2.0)
    fib = ctx.streak(0.7, 9.0, 21, 2)
    shade = 0.075 * lines + 0.20 * (fib - 0.5)
    col = col * (1 + shade)[..., None]
    # drobne pory
    pores = ctx.streak(3.0, 16.0, 31, 1)
    col = col * (1 - 0.10 * smooth(0.70, 0.88, pores))[..., None]
    # sęki
    kn = vnoise(np.floor((g + r1 * 17.0) / seg_len) * 1.0 + idx * 5.0, idx * 3.0, z * 1.0, ctx.seed + 41)
    kx = (g + r1 * 17.0) % seg_len
    kd = np.hypot(kx - seg_len * (0.3 + 0.4 * r2), (local - plank * (0.3 + 0.4 * r1)) * 1.6)
    knot = (kn > 0.86) * smooth(1.1, 0.25, kd)
    col = col * (1 - 0.45 * knot)[..., None]
    # szwy między deskami i styki czołowe
    s = np.minimum(local, plank - local)
    crack = smooth(0.20, 0.05, s)
    lip = smooth(0.45, 0.22, s) * (local < plank / 2)
    sg = (g + r1 * 17.0) % seg_len
    ends = smooth(0.20, 0.04, np.minimum(sg, seg_len - sg)) * 0.7
    col = col * (1 - 0.50 * np.maximum(crack, ends))[..., None] * (1 + 0.06 * lip)[..., None]
    # gwoździe przy końcach bryły
    if min(ctx.dims) >= 1.0:
        for end_pos in (box.frm[ctx.grain_axis] + 1.0, box.to[ctx.grain_axis] - 1.0):
            dn = np.hypot(g - end_pos, local - plank / 2)
            col = col * (1 - 0.50 * smooth(0.28, 0.12, dn))[..., None]
            col = col + 22 * smooth(0.14, 0.05, np.hypot(g - end_pos + 0.10, local - plank / 2 + 0.10))[..., None]
    if aged:
        col = col * (1 - aged * 0.35 * smooth(0.4, 0.8, ctx.noise(1.3, 1.3, 1.3, 61, 3)))[..., None]
    return edge_wear(ctx, col, 0.14, 0.05)


def metal(ctx, base, brushed=0.07, band=0.06, rivets=False, rust=0.0, scratches=0.06):
    """Blacha szczotkowana: smugi wzdłuż długiego boku, szeroki połysk, rysy."""
    streak = ctx.streak(0.5, 22.0, 51, 2)
    wide = vnoise(ctx.c * 0.35, ctx.g * 0.05, ctx.Y * 0.0, ctx.seed + 53)
    col = rgb(base) * (1 + brushed * (streak - 0.5) * 2 + band * (wide - 0.5) * 2)[..., None]
    sc = ctx.streak(0.25, 40.0, 61, 1)
    col = col * (1 + scratches * (sc > 0.86) * 2.2 - scratches * (sc < 0.12) * 2.0)[..., None]
    if rust > 0:
        col = rust_over(ctx, col, rust)
    if rivets:
        col = rivet_row(ctx, col)
    return edge_wear(ctx, col, 0.14, 0.12)


def rust_over(ctx, col, amount):
    """Rdza: plamy z szumu, ciemniejsze przy krawędziach."""
    n = ctx.noise(0.45, 0.95, 0.45, 71, 3)
    drip = vnoise(ctx.X * 1.6 + ctx.Z * 1.6, ctx.Y * 0.12, ctx.Y * 0, ctx.seed + 73)
    m = smooth(0.62 - amount * 0.45, 0.78 - amount * 0.30, n * 0.7 + drip * 0.5 + (1 - smooth(0, 6, ctx.Y)) * 0.1)
    m = np.clip(m + smooth(0.5, 0.0, ctx.E) * amount * 0.35, 0, 1)
    tone = ctx.noise(2.2, 2.2, 2.2, 77, 2)
    r = lerp(rgb((120, 63, 31)), rgb((156, 88, 44)), tone)
    return lerp(col, r, m * min(1.0, amount * 1.3))


def rivet_row(ctx, col, spacing=3.0):
    """Nity wzdłuż krawędzi ściany: kopułka z jasnym odbiciem."""
    inset = 0.55
    k = (ctx.g / spacing) % 1.0 * spacing
    dk = np.minimum(k, spacing - k)
    dist = np.hypot(dk, ctx.E - inset)
    dome = smooth(0.3, 0.05, dist)
    light = smooth(0.14, 0.0, np.hypot(dk - 0.07, ctx.E - inset + 0.07))
    out = col * (1 - 0.35 * smooth(0.36, 0.28, dist) * (1 - dome))[..., None]
    return out * (1 + 0.2 * dome)[..., None] + 55 * light[..., None]


def paint(ctx, color, chip=(150, 154, 158), chips=0.25, worn=0.0, grime=0.0, panel=None, rivets=False):
    """Emalia na blasze: fakturka, odpryski przy krawędziach, brud."""
    fine = ctx.noise(5.0, 5.0, 5.0, 81, 2)
    low = ctx.noise(0.35, 0.35, 0.35, 83, 2)
    col = rgb(color) * (1 + 0.035 * (fine - 0.5) * 2 + 0.06 * (low - 0.5) * 2)[..., None]
    if panel:
        s = (ctx.g / panel) % 1.0 * panel
        line = smooth(0.14, 0.04, np.minimum(s, panel - s))
        col = col * (1 - 0.35 * line)[..., None]
    edge_zone = smooth(0.8, 0.05, ctx.E)
    cn = ctx.noise(3.2, 3.2, 3.2, 87, 3)
    val = cn * 0.55 + edge_zone * (0.22 + chips * 0.6 + worn * 0.5) + worn * 0.22
    chipped = smooth(0.66, 0.70, val)
    metal_c = rgb(chip) * (1 + 0.10 * (ctx.noise(8, 8, 8, 89) - 0.5))[..., None]
    col = lerp(col, metal_c, chipped)
    if worn > 0.5:
        col = rust_over(ctx, col, min(1.0, (worn - 0.3) * 1.2))
    if grime > 0:
        down = 1 - smooth(0, 7, ctx.Y)
        dirt = ctx.noise(1.4, 0.4, 1.4, 91, 3)
        col = col * (1 - grime * (0.15 + 0.5 * down) * smooth(0.35, 0.8, dirt))[..., None]
    if rivets:
        col = rivet_row(ctx, col)
    return edge_wear(ctx, col, 0.10, 0.10)


def concrete(ctx, base=(130, 128, 120)):
    n = ctx.noise(2.5, 2.5, 2.5, 101, 3)
    fine = ctx.noise(9, 9, 9, 103)
    col = rgb(base) * (1 + 0.20 * (n - 0.5) * 2 + 0.08 * (fine - 0.5) * 2)[..., None]
    col = col * (1 - 0.18 * (ctx.noise(6, 6, 6, 107) > 0.88))[..., None]
    return edge_wear(ctx, col, 0.1, 0.05)


def brick(ctx, base=(150, 62, 44), mortar=(168, 160, 148)):
    """Cegły w wiązaniu: 3×1 jednostki z fugą."""
    h, w = 1.0, 3.0
    if AXIS[ctx.face] == 1:
        along, vert = ctx.X, ctx.Z
    elif AXIS[ctx.face] == 2:
        along, vert = ctx.X, ctx.Y
    else:
        along, vert = ctx.Z, ctx.Y
    row = np.floor(vert / h)
    shifted = along + (row % 2) * (w / 2)
    ci = np.floor(shifted / w)
    lx = shifted - ci * w
    ly = vert - row * h
    gap = np.minimum(np.minimum(lx, w - lx) * 0.8, np.minimum(ly, h - ly)) < 0.12
    rnd = _hash(ci.astype(np.int64), row.astype(np.int64), np.zeros_like(row, dtype=np.int64), ctx.seed + 113)
    col = rgb(base) * (1 + (rnd[..., None] - 0.5) * 0.35)
    col = col * (1 + 0.10 * (ctx.noise(6, 6, 6, 117) - 0.5) * 2)[..., None]
    mort = rgb(mortar) * (1 + 0.1 * (ctx.noise(8, 8, 8, 119) - 0.5))[..., None]
    return lerp(col, mort, gap.astype(float))


def plain(ctx, base, noise=0.05, edge=0.06):
    col = rgb(base) * (1 + noise * (ctx.noise(6, 6, 6, 131) - 0.5) * 2)[..., None]
    return edge_wear(ctx, col, 0.1, edge)


def emissive(ctx, inner, outer):
    t = smooth(0.0, 1.8, ctx.E)
    col = lerp(rgb(outer), rgb(inner), t)
    return col * (0.92 + 0.16 * ctx.noise(2.0, 2.0, 2.0, 141, 2))[..., None]


def screen(ctx):
    """Zielony monitor CRT z liniami skanowania i poświatą."""
    scan = 0.82 + 0.18 * (np.floor(ctx.Y * 4) % 2)
    t = smooth(0.0, 1.5, ctx.E)
    col = lerp(rgb((24, 70, 40)), rgb((70, 214, 110)), t * 0.8)
    txt = (vnoise(ctx.X * 2.2 + ctx.Z * 2.2, np.floor(ctx.Y * 2.4), ctx.Y * 0, ctx.seed + 143) > 0.62) * (ctx.E > 1.2)
    return lerp(col, rgb((190, 255, 200)), txt * 0.9) * scan[..., None]


def fabric(ctx, base=(168, 160, 140)):
    weave = 1 + 0.07 * (np.sin(ctx.X * 12.0) * np.sin(ctx.Z * 12.0 + ctx.Y * 12.0))
    return rgb(base) * (weave * (1 + 0.15 * (ctx.noise(3, 3, 3, 151, 2) - 0.5)))[..., None]


def cardboard(ctx, base=(168, 134, 90)):
    flute = 1 + 0.05 * np.sin((ctx.X + ctx.Z) * 14.0)
    return rgb(base) * (flute * (1 + 0.12 * (ctx.noise(3, 3, 3, 153) - 0.5)))[..., None]


def rubber(ctx, base=(34, 34, 36)):
    return rgb(base) * (1 + 0.20 * (ctx.noise(10, 10, 10, 155) - 0.5))[..., None]


def brass(ctx):
    n = ctx.streak(0.4, 18.0, 157, 2)
    col = rgb((188, 146, 62)) * (1 + 0.16 * (n - 0.5) * 2)[..., None]
    return edge_wear(ctx, col, 0.14, 0.2)


MATS = {
    'plank': lambda c: wood(c, (186, 148, 96)),
    'plank_dark': lambda c: wood(c, (128, 94, 60), aged=0.4),
    'wood': lambda c: wood(c, (156, 112, 68), plank=2.2),
    'wood_dark': lambda c: wood(c, (98, 68, 42), plank=2.2, aged=0.6),
    'steel_light': lambda c: metal(c, (150, 156, 162)),
    'steel': lambda c: metal(c, (130, 136, 142)),
    'steel_dark': lambda c: metal(c, (78, 82, 88), brushed=0.05),
    'rail': lambda c: metal(c, (104, 100, 98), rust=0.35),
    'olive': lambda c: paint(c, (86, 102, 62), panel=8.0, rivets=True),
    'olive_chipped': lambda c: paint(c, (80, 96, 58), worn=0.45, panel=8.0, grime=0.4),
    'blue_enamel': lambda c: paint(c, (48, 92, 150), chips=0.1),
    'blue_chipped': lambda c: paint(c, (46, 86, 140), worn=0.5, grime=0.3),
    'red_paint': lambda c: paint(c, (156, 46, 36), chips=0.2),
    'yellow_paint': lambda c: paint(c, (216, 172, 32), chips=0.3, grime=0.3, panel=8.0),
    'white_enamel': lambda c: paint(c, (216, 214, 202), chips=0.12, grime=0.2),
    'black': lambda c: paint(c, (30, 30, 33), chip=(70, 70, 74), chips=0.15),
    'rubber': rubber,
    'brass': brass,
    'rust': lambda c: metal(c, (112, 78, 58), rust=1.0),
    'rust_heavy': lambda c: metal(c, (96, 62, 44), rust=1.5, brushed=0.1),
    'concrete': concrete,
    'stone_dark': lambda c: concrete(c, (84, 86, 88)),
    'brick': brick,
    'cardboard': cardboard,
    'cord': lambda c: fabric(c, (150, 120, 80)),
    'cloth': fabric,
    'screen': screen,
    'green_led': lambda c: emissive(c, (150, 255, 160), (40, 150, 70)),
    'glow': lambda c: emissive(c, (255, 224, 140), (232, 120, 30)),
}


# ---------------------------------------------------------------- bryły i pakowanie

class Box:
    def __init__(self, frm, to, faces, rot=None):
        self.frm, self.to, self.faces, self.rot = list(frm), list(to), dict(faces), rot


def _inside(boxes, X, Y, Z, eps=1e-4):
    hit = np.zeros(X.shape, dtype=bool)
    for b in boxes:
        hit |= ((X >= b.frm[0] - eps) & (X <= b.to[0] + eps) & (Y >= b.frm[1] - eps) & (Y <= b.to[1] + eps)
                & (Z >= b.frm[2] - eps) & (Z <= b.to[2] + eps))
    return hit


def _plane(b, f):
    ax = AXIS[f]
    return b.to[ax] if NORMAL[f][ax] > 0 else b.frm[ax]


def _overlap(a, b, ax):
    for i in range(3):
        if i != ax and min(a.to[i], b.to[i]) - max(a.frm[i], b.frm[i]) <= 1e-6:
            return False
    return True


def _axes(f):
    """(oś u, znak u, oś v, znak v): kierunek wzrostu współrzędnej świata przy rosnących u, v."""
    return {'north': (0, -1, 1, -1), 'south': (0, 1, 1, -1), 'east': (2, -1, 1, -1), 'west': (2, 1, 1, -1),
            'up': (0, 1, 2, 1), 'down': (0, 1, 2, -1)}[f]


class SolidModel(Model):
    """Model, w którym każda widoczna ściana ma własny prostokąt w jednej teksturze modelu.

    `unit` przelicza jednostki modelu na „jednostki materiału” (1/16 m), gdy model jest zmniejszony
    (wraki: unit = 1.6 / f), żeby rysy, odpryski i nity miały tę samą wielkość co na stanowiskach.
    `density` to piksele tekstury na jednostkę modelu (przy braku miejsca w 512×512 maleje)."""
    name = None
    unit = 1.0
    density = DENSITY

    def __init__(self, display=None, gui_light='side'):
        super().__init__(display=display, rotation=None, gui_light=gui_light)
        self.boxes = []
        self._built = None

    def solid(self, frm, to, tex, **face_tex):
        rot = face_tex.pop('rot', None)
        faces = {f: face_tex.get(f, tex) for f in FACES}
        self.boxes.append(Box(frm, to, faces, rot))
        self._built = None
        return self

    def rotate(self, quarters):
        for _ in range(quarters % 4):
            for b in self.boxes:
                p, q = _point_90(b.frm), _point_90(b.to)
                b.frm = [min(p[i], q[i]) for i in range(3)]
                b.to = [max(p[i], q[i]) for i in range(3)]
                b.faces = {_FACE_90[k]: v for k, v in b.faces.items()}
                r = b.rot
                if r:
                    r = dict(r, origin=_point_90(r['origin']))
                    if r['axis'] == 'x':
                        r['axis'] = 'z'
                    elif r['axis'] == 'z':
                        r['axis'], r['angle'] = 'x', -r['angle']
                    b.rot = r
        self._built = None
        return self

    # ---- budowa
    def _geometry(self):
        boxes = [Box(b.frm, b.to, b.faces, b.rot) for b in self.boxes]
        # 1. ściany w jednej płaszczyźnie (migają): wcześniejsza wchodzi w głąb
        for i, a in enumerate(boxes):
            for f, mat in a.faces.items():
                if mat is None:
                    continue
                ax = AXIS[f]
                for j in range(i + 1, len(boxes)):
                    b = boxes[j]
                    if b.faces.get(f) is None or abs(_plane(a, f) - _plane(b, f)) > 1e-6 or not _overlap(a, b, ax):
                        continue
                    if NORMAL[f][ax] > 0:
                        a.to[ax] -= PULL
                    else:
                        a.frm[ax] += PULL
                    break
        # 2. ściany zasłonięte
        visible = []
        for i, a in enumerate(boxes):
            others = [b for j, b in enumerate(boxes) if j != i]
            for f, mat in a.faces.items():
                if mat is None:
                    continue
                if f == 'down' and a.frm[1] <= 0.001:
                    continue
                X, Y, Z = self._grid(a, f, 3, 3)
                n = NORMAL[f]
                if _inside(others, X + n[0] * 0.02, Y + n[1] * 0.02, Z + n[2] * 0.02).all():
                    continue
                visible.append((i, f))
        return boxes, visible

    @staticmethod
    def _grid(b, f, w, h, inset=0.0):
        ua, us, va, vs = _axes(f)
        ud, vd = b.to[ua] - b.frm[ua], b.to[va] - b.frm[va]
        uu = (np.arange(w) + 0.5) / w
        vv = (np.arange(h) + 0.5) / h
        U, V = np.meshgrid(uu, vv)
        pos = [None] * 3
        pos[AXIS[f]] = np.full(U.shape, _plane(b, f))
        pos[ua] = (b.frm[ua] + U * ud) if us > 0 else (b.to[ua] - U * ud)
        pos[va] = (b.frm[va] + V * vd) if vs > 0 else (b.to[va] - V * vd)
        return pos

    def build(self):
        if self._built:
            return self._built
        boxes, visible = self._geometry()
        for density in (self.density, self.density * 0.75, self.density * 0.5, self.density * 0.35):
            rects = []
            for i, f in visible:
                b = boxes[i]
                ua, _, va, _ = _axes(f)
                w = max(2, int(round((b.to[ua] - b.frm[ua]) * density)))
                h = max(2, int(round((b.to[va] - b.frm[va]) * density)))
                rects.append((i, f, w, h))
            placed, size = self._pack(rects)
            if placed:
                break
        else:
            raise ValueError('model %s nie mieści się w teksturze 512' % self.name)
        sw, sh = size
        sheet = np.zeros((sh, sw, 4), dtype=np.uint8)
        elements = []
        for i, b in enumerate(boxes):
            elements.append({'from': [round(v, 4) for v in b.frm], 'to': [round(v, 4) for v in b.to], 'faces': {}})
            if b.rot:
                elements[-1]['rotation'] = b.rot
        for (i, f, w, h), (x, y) in placed.items():
            b = boxes[i]
            patch = self._paint(boxes, i, f, w, h)
            patch = np.pad(patch, ((GUTTER, GUTTER), (GUTTER, GUTTER), (0, 0)), mode='edge')
            sheet[y - GUTTER:y + h + GUTTER, x - GUTTER:x + w + GUTTER] = patch
            elements[i]['faces'][f] = {'uv': [round(x / sw * 16, 4), round(y / sh * 16, 4),
                                              round((x + w) / sw * 16, 4), round((y + h) / sh * 16, 4)],
                                       'texture': '#b'}
        elements = [e for e in elements if e['faces']]
        self._built = (elements, Image.fromarray(sheet, 'RGBA'))
        return self._built

    @staticmethod
    def _pack(rects):
        """Półkowe upakowanie; wybiera szerokość 64..512 dającą najmniejszą powierzchnię."""
        best = None
        for width in (64, 128, 256, 512):
            x = y = row_h = 0
            placed = {}
            ok = True
            for r in sorted(rects, key=lambda r: (-r[3], -r[2])):
                sw, sh = r[2] + 2 * GUTTER, r[3] + 2 * GUTTER
                if sw > width:
                    ok = False
                    break
                if x + sw > width:
                    x, y, row_h = 0, y + row_h, 0
                placed[r] = (x + GUTTER, y + GUTTER)
                x += sw
                row_h = max(row_h, sh)
            if not ok:
                continue
            height = -(-(y + row_h) // 8) * 8
            if height <= 512 and (best is None or width * height < best[0]):
                best = (width * height, placed, (width, height))
        return (best[1], best[2]) if best else (None, None)

    def _paint(self, boxes, i, f, w, h):
        b = boxes[i]
        X, Y, Z = self._grid(b, f, w, h)
        ua, _, va, _ = _axes(f)
        lu, lv = b.to[ua] - b.frm[ua], b.to[va] - b.frm[va]
        uu = (np.arange(w) + 0.5) / w
        vv = (np.arange(h) + 0.5) / h
        U, V = np.meshgrid(uu, vv)
        E = np.minimum(np.minimum(U * lu, (1 - U) * lu), np.minimum(V * lv, (1 - V) * lv))
        seed = (i * 31 + FACES.index(f) * 7) % 997
        u = self.unit
        if u != 1.0:
            sb = Box([v * u for v in b.frm], [v * u for v in b.to], b.faces, b.rot)
            ctx = Ctx(sb, f, X * u, Y * u, Z * u, E * u, seed)
        else:
            ctx = Ctx(b, f, X, Y, Z, E, seed)
        col = MATS[b.faces[f]](ctx)
        # zacienienie przy stykach z innymi bryłami
        others = [o for j, o in enumerate(boxes) if j != i]
        n = NORMAL[f]
        ax = (X, Y, Z)
        shade = np.zeros(X.shape)
        for t_axis in (ua, va):
            for sgn in (-1, 1):
                p = [ax[0] + n[0] * 0.15, ax[1] + n[1] * 0.15, ax[2] + n[2] * 0.15]
                p[t_axis] = p[t_axis] + sgn * 0.6
                shade += 0.09 * _inside(others, *p)
        shade += 0.14 * _inside(others, X + n[0] * 0.5, Y + n[1] * 0.5, Z + n[2] * 0.5)
        col = col * (1 - np.clip(shade, 0, 0.45))[..., None]
        # lekka kierunkowość światła, żeby kształt było widać (góra jasna, dół ciemny)
        col = col * {'up': 1.08, 'down': 0.72, 'north': 0.92, 'south': 0.96, 'east': 0.84, 'west': 0.84}[f]
        col = np.clip(np.round(col / 4.0) * 4.0, 0, 255)
        out = np.dstack([col, np.full(X.shape, 255.0)]).astype(np.uint8)
        return out

    # ---- zgodność z Model
    @property
    def elements(self):
        return self.build()[0]

    @elements.setter
    def elements(self, value):
        pass

    @property
    def texture(self):
        return self.build()[1]

    def json(self):
        tex = 'axon:item/%s' % self.name
        out = {'textures': {'b': tex, 'particle': tex}, 'elements': self.elements}
        if self.gui_light:
            out['gui_light'] = self.gui_light
        if self.display:
            out['display'] = self.display
        return out
