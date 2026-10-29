"""Tekstury skrzyni (entity/chest): drewniana skrzynia z desek z okuciami."""
import random
from PIL import Image
from .px import PAL

def col(ch, f=1.0):
    r, g, b = PAL[ch]
    return (max(0, min(255, int(r * f))), max(0, min(255, int(g * f))), max(0, min(255, int(b * f))), 255)

def face(img, x0, y0, w, h, rnd, kind='side'):
    """Deski poziome, ciemne fugi co 5 px, stalowy kątownik na brzegu, nity w rogach."""
    for y in range(h):
        for x in range(w):
            edge = x in (0, w - 1) or y in (0, h - 1)
            if edge:
                ch, f = ('2', rnd.uniform(0.9, 1.1))
                if (x in (0, w - 1)) and (y in (0, h - 1)):
                    ch = '4'
            else:
                row = (y - 1) if kind == 'side' else (x - 1)
                seam = row % 5 == 4
                if seam:
                    ch = 'w'
                else:
                    plank = row // 5
                    ch = ('d', 'D', 'd')[plank % 3] if rnd.random() > 0.12 else 'W'
                f = rnd.uniform(0.92, 1.06)
            img.putpixel((x0 + x, y0 + y), col(ch, f))

def box(img, u, v, w, h, d, rnd, top_kind='top'):
    face(img, u + d, v, w, d, rnd, top_kind)            # góra
    face(img, u + d + w, v, w, d, rnd, top_kind)        # dół
    face(img, u, v + d, d, h, rnd)                      # bok
    face(img, u + d, v + d, w, h, rnd)                  # przód
    face(img, u + d + w, v + d, d, h, rnd)              # bok
    face(img, u + 2 * d + w, v + d, w, h, rnd)          # tył

def lock(img, u, v, w, h, d):
    for x in range(u, u + 2 * (w + d)):
        for y in range(v, v + d + h):
            img.putpixel((x, y), col('A' if (x + y) % 3 else 'a'))

def chest(width):
    """width 14 = pojedyncza, 15 = połówka podwójnej."""
    img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    rnd = random.Random(width)
    box(img, 0, 0, width, 5, 14, rnd)       # wieko
    box(img, 0, 19, width, 10, 14, rnd)     # skrzynia
    if width == 14:
        lock(img, 0, 0, 2, 4, 1)
    else:
        lock(img, 0, 0, 1, 4, 1)
    return img

TEX = {
    'minecraft:entity/chest/normal': chest(14),
    'minecraft:entity/chest/normal_left': chest(15),
    'minecraft:entity/chest/normal_right': chest(15),
}
