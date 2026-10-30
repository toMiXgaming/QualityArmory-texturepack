"""Tekstury skrzyni (entity/chest): drewniana skrzynia z desek z okuciami, 128×128.

Układ jak w vanilla 64×64, tylko każdy piksel vanilla to 2×2 (Minecraft skaluje UV modelu
skrzyni do rozmiaru tekstury). Każda ściana ma deski z usłojeniem, stalowy kątownik
z nitami dookoła i jest symetryczna góra-dół, bo gra rysuje część ścian skrzyni odwróconych.
"""
from .crates import Canvas, BRASS, _mul

K = 2  # pikseli tekstury na piksel vanilla
WOOD = (150, 108, 66)
FRAME = (70, 74, 80)


def _box(c, u, v, w, h, d, lid):
    """Sześć ścian bryły w układzie Minecrafta (u, v, szer., wys., głęb. w pikselach vanilla)."""
    faces = {
        'top': (u + d, v, w, d), 'bottom': (u + d + w, v, w, d),
        'west': (u, v + d, d, h), 'north': (u + d, v + d, w, h),
        'east': (u + d + w, v + d, d, h), 'south': (u + 2 * d + w, v + d, w, h),
    }
    for name, (x, y, ww, hh) in faces.items():
        key = '%s_%d_%d' % (name, x, y)
        c.R[key] = (x * K, y * K, ww * K, hh * K)
        if name in ('top', 'bottom'):
            c.wood(key, _mul(WOOD, 1.05 if lid else 0.8), plank=10, vertical=True)
        else:
            c.wood(key, WOOD, plank=10 if lid else 8)
            if not lid:   # poprzeczka przez środek korpusu
                hy = hh * K // 2
                c.band(key, hy - 2, hy + 2, (78, 54, 34))
        c.frame(key, 3, FRAME, rivets=True)
        c.ao(key, 3, 0.85)


def _lock(c, u, v, w, h, d):
    c.R['lock'] = (u * K, v * K, 2 * (w + d) * K, (d + h) * K)
    c.metal('lock', BRASS, chips=1, chip=(214, 186, 110))
    x0, y0, ww, hh = c.R['lock']
    cx = x0 + (2 * d + w) * K // 2                         # środek przedniej ściany zamka
    for y in range(y0 + (d + 1) * K, y0 + (d + h - 1) * K):   # dziurka od klucza
        for x in ((cx - 1, cx) if w > 1 else (cx - 1,)):
            c.set(x, y, (30, 26, 20))


def chest(width):
    """width 14 = pojedyncza, 15 = połówka podwójnej."""
    c = Canvas('chest_%d' % width, {})
    _box(c, 0, 0, width, 5, 14, lid=True)       # wieko
    _box(c, 0, 19, width, 10, 14, lid=False)    # korpus
    if width == 14:
        _lock(c, 0, 0, 2, 4, 1)
    else:
        _lock(c, 0, 0, 1, 4, 1)
    return c.img


TEX = {
    'minecraft:entity/chest/normal': chest(14),
    'minecraft:entity/chest/normal_left': chest(15),
    'minecraft:entity/chest/normal_right': chest(15),
}
