"""Atlas materiałów 64x64 dla modeli 3D: kafelki 8x8 px (w modelu 2x2 jednostki UV)."""
import random
import zlib
from PIL import Image
from .px import PAL

T = 8
TILES = {}   # nazwa -> (kol, rząd)
_img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))

def c(ch, f=1.0):
    r, g, b = PAL[ch]
    return (max(0, min(255, int(r * f))), max(0, min(255, int(g * f))), max(0, min(255, int(b * f))), 255)

def tile(name, col, row, fn, seed=0):
    rnd = random.Random(zlib.crc32(name.encode()) ^ seed)
    for y in range(T):
        for x in range(T):
            _img.putpixel((col * T + x, row * T + y), fn(x, y, rnd))
    TILES[name] = (col, row)

def noise(chars, amp=0.07):
    def f(x, y, rnd):
        return c(rnd.choice(chars), 1 + rnd.uniform(-amp, amp))
    return f

def grain(a, b, dark):
    def f(x, y, rnd):
        ch = dark if (x * 3 + (y // 3)) % 7 == 0 else (a if (x + rnd.randint(0, 1)) % 3 else b)
        return c(ch, 1 + rnd.uniform(-0.05, 0.05))
    return f

def stripes(a, b, period=3):
    def f(x, y, rnd):
        return c(a if (x + y) % period else b, 1 + rnd.uniform(-0.05, 0.05))
    return f

def specks(base, speck, p=0.15):
    def f(x, y, rnd):
        return c(speck if rnd.random() < p else base, 1 + rnd.uniform(-0.06, 0.06))
    return f

def gradient(chars):
    def f(x, y, rnd):
        return c(chars[min(len(chars) - 1, y * len(chars) // T)], 1 + rnd.uniform(-0.04, 0.04))
    return f

# rząd 0: drewno, owijki
tile('wood_light', 0, 0, grain('D', 'd', 'W'))
tile('wood', 1, 0, grain('d', 'W', 'w'))
tile('wood_dark', 2, 0, grain('W', 'w', 'k'))
tile('ash', 3, 0, grain('S', 'D', 'd'))
tile('leather', 4, 0, stripes('r', 'w', 2))
tile('cord', 5, 0, stripes('s', 'd', 3))
tile('tape', 6, 0, stripes('n', 'N', 4))
tile('cloth', 7, 0, specks('S', 's', 0.3))
# rząd 1: stal
tile('steel_light', 0, 1, noise('445'))
tile('steel', 1, 1, noise('334'))
tile('steel_dark', 2, 1, noise('223'))
tile('edge', 3, 1, noise('55z', 0.03))
tile('leafspring', 4, 1, specks('1', 'b', 0.25))
tile('rail', 5, 1, specks('2', 'r', 0.35))
tile('rust', 6, 1, specks('R', 'o', 0.3))
tile('brass', 7, 1, noise('Aax'))
# rząd 2: farby, hartowanie, kamień
tile('olive', 0, 2, noise('Gh'))
tile('olive_chipped', 1, 2, specks('G', '3', 0.12))
tile('tempered', 2, 2, specks('A', 'x', 0.3))
tile('forged', 3, 2, specks('1', '3', 0.15))
tile('diamond', 4, 2, noise('cCz', 0.03))
tile('stone', 5, 2, noise('tTu'))
tile('stone_dark', 6, 2, noise('ttn'))
tile('flint', 7, 2, noise('nN2'))
# rząd 3: kolory pomocnicze dla stanowisk i pojemników
tile('blue_enamel', 0, 3, specks('B', 'c', 0.1))
tile('blue_chipped', 1, 3, specks('B', '3', 0.18))
tile('red_paint', 2, 3, specks('E', 'e', 0.15))
tile('yellow_paint', 3, 3, specks('Y', 'y', 0.15))
tile('black', 4, 3, noise('nN'))
tile('white_enamel', 5, 3, specks('z', 'S', 0.12))
tile('glow', 6, 3, noise('FvY', 0.05))
tile('glass', 7, 3, noise('cC', 0.03))
# rząd 4: drewno skrzyń, sklejka, karton, guma
tile('plank', 0, 4, grain('d', 'D', 'W'))
tile('plank_dark', 1, 4, grain('W', 'd', 'w'))
tile('cardboard', 2, 4, specks('D', 's', 0.2))
tile('rubber', 3, 4, noise('nk'))
tile('rust_heavy', 4, 4, specks('r', 'R', 0.4))
tile('concrete', 5, 4, specks('u', 'T', 0.2))
tile('green_led', 6, 4, noise('hH', 0.02))
tile('screen', 7, 4, noise('gG', 0.04))

ATLAS = _img

def uv(name):
    col, row = TILES[name]
    return [col * 2, row * 2, col * 2 + 2, row * 2 + 2]
