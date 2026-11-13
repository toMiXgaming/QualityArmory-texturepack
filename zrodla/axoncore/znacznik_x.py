"""Znacznik X na pniu drzewa (ścinanie drzew w AxonMapGenerator): X namalowany sprayem.

Jak w prawdziwym lesie, gdzie drzewa do wycinki znakuje się fluorescencyjną farbą: pomarańczowo-czerwony X
z rozpyloną mgiełką na brzegach, kilkoma zaciekami i drobnymi kropkami farby. Na korze każdego gatunku
(ciemny świerk, jasna brzoza, palma) jest dobrze widoczny. Plugin pokazuje go jako ItemDisplay na ścianie pnia,
tylko graczowi, który rąbie, i z pełną jasnością (widać go też w nocy i w cieniu lasu).

Dwa przedmioty (komponent item_model, jak beczki i meble):
- axon:znacznik_x – zwykły X; tekstura lekko pulsuje (animacja .mcmeta), żeby oko go wyłapało,
- axon:znacznik_x_trafiony – błysk przy trafieniu: X rozgrzany do żółto-białego, z poświatą.

Model to cienka płytka 16×16 (grubość 0,5 px) z teksturą z przodu i z tyłu, bez boków: z każdej strony
X wygląda tak samo, a zacieki zawsze lecą w dół. Środek płytki to środek modelu, więc ItemDisplay
z transformacją NONE stoi dokładnie w punkcie X.

`pliki()` zwraca {ścieżka w zipie: bajty}; woła ją gen_axoncore.pliki() (pełna przebudowa w build_pack.py)
i dodaj_znacznik_x.py (łatka gotowych zipów)."""
import io
import json
import math
import random

from PIL import Image, ImageDraw, ImageFilter

SIZE = 32        # tekstura 32×32: na płytce ok. 0,75 bloku to wciąż ostre krawędzie
SS = 8           # nadpróbkowanie przy rysowaniu (gładkie, antyaliasowane pociągnięcia)
FRAMES = 8       # klatki pulsowania zwykłego X

# Fluorescencyjna farba leśna: od cienia (gęsta, ciemniejsza farba w środku pociągnięcia) do światła.
PAINT_DEEP = (150, 26, 8)
PAINT = (255, 74, 18)
PAINT_MID = (255, 104, 32)
PAINT_LIGHT = (255, 150, 74)
# Błysk przy trafieniu.
HOT_EDGE = (255, 150, 30)
HOT = (255, 232, 120)
HOT_CORE = (255, 255, 236)

NAMES = ('znacznik_x', 'znacznik_x_trafiony')


def _stroke_mask(rnd, a, b, width):
    """Maska jednego pociągnięcia sprayem od a do b (współrzędne w pikselach tekstury)."""
    big = SIZE * SS
    core = Image.new('L', (big, big), 0)
    d = ImageDraw.Draw(core)
    steps = 40
    for i in range(steps + 1):
        t = i / steps
        # pociągnięcie jest grubsze w środku i lekko faluje, jak ręka z puszką
        w = width * (0.82 + 0.22 * math.sin(math.pi * t)) * (0.95 + 0.1 * rnd.random())
        x = (a[0] + (b[0] - a[0]) * t) * SS
        y = (a[1] + (b[1] - a[1]) * t) * SS
        r = w * SS / 2
        d.ellipse((x - r, y - r, x + r, y + r), fill=255)
    return core


def _drip(d, rnd, x, y, length, width):
    """Zaciek farby spływający w dół z kroplą na końcu."""
    x *= SS
    y *= SS
    w = width * SS
    end = y + length * SS
    d.rounded_rectangle((x - w / 2, y, x + w / 2, end), radius=w / 2, fill=255)
    r = w * 0.75
    d.ellipse((x - r, end - r, x + r, end + r), fill=255)


def _shape(seed=31):
    """Wspólny kształt X: (maska farby, maska mgiełki), obie w pełnej rozdzielczości SIZE×SIZE."""
    rnd = random.Random(seed)
    big = SIZE * SS
    paint = Image.new('L', (big, big), 0)
    m = 4.6   # margines od brzegu tekstury
    for a, b in (((m, m + 0.6), (SIZE - m, SIZE - m - 0.4)), ((SIZE - m + 0.3, m), (m - 0.2, SIZE - m + 0.2))):
        paint = Image.composite(Image.new('L', (big, big), 255), paint, _stroke_mask(rnd, a, b, 4.6))
    d = ImageDraw.Draw(paint)
    # zacieki z dolnych końców i ze środka (tam farby jest najwięcej)
    for x, y, length, w in ((SIZE - m - 1.6, SIZE - m - 1.0, 3.6, 1.5), (m + 1.0, SIZE - m - 0.8, 2.6, 1.3),
                            (SIZE / 2 + 0.8, SIZE / 2 + 1.0, 7.0, 1.5), (SIZE / 2 - 2.2, SIZE / 2 + 2.2, 3.4, 1.2)):
        _drip(d, rnd, x, y, length, w)
    paint = paint.filter(ImageFilter.GaussianBlur(SS * 0.35))
    # mgiełka: szeroka, miękka otoczka i rozprysk kropek wokół pociągnięć
    haze = paint.filter(ImageFilter.GaussianBlur(SS * 1.6))
    hd = ImageDraw.Draw(haze)
    cx = cy = SIZE / 2
    for _ in range(70):
        ang = rnd.random() * math.tau
        # kropki gęściej wzdłuż przekątnych (tam szło pociągnięcie)
        diag = math.pi / 4 + (math.pi / 2) * rnd.randrange(4)
        ang = diag + (ang - math.pi) * 0.18
        dist = (0.25 + rnd.random() * 0.75) * SIZE * 0.62
        x = (cx + math.cos(ang) * dist) * SS
        y = (cy + math.sin(ang) * dist) * SS
        r = (0.25 + rnd.random() * 0.45) * SS
        hd.ellipse((x - r, y - r, x + r, y + r), fill=150 + rnd.randrange(100))
    # głębokość farby: odległość od brzegu pociągnięcia (erozja maski), do cieniowania środka
    depth = paint.point(lambda v: 255 if v > 127 else 0)
    depth = depth.filter(ImageFilter.MinFilter(SS * 2 + 1)).filter(ImageFilter.GaussianBlur(SS * 1.1))
    small = lambda im: im.resize((SIZE, SIZE), Image.LANCZOS)
    return small(paint), small(haze), small(depth)


PAINT_MASK, HAZE_MASK, DEPTH_MASK = _shape()


def _mix(c1, c2, t):
    return tuple(int(round(a + (b - a) * t)) for a, b in zip(c1, c2))


def _texture(edge, mid, core, light=1.0, haze_alpha=0.55, outline=None):
    """Tekstura X: obrys -> farba -> jaśniejszy środek pociągnięcia, z mgiełką o przezroczystości haze_alpha.

    Cieniowanie bierze się z rozmytej maski (im dalej od brzegu pociągnięcia, tym jaśniej), a ciemniejszy
    obrys o szerokości ok. 1 px odcina X od jasnej kory (brzoza)."""
    outline = outline or _mix(edge, (40, 8, 4), 0.35)
    img = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    rnd = random.Random(7)
    for y in range(SIZE):
        for x in range(SIZE):
            p = PAINT_MASK.getpixel((x, y)) / 255.0
            depth = DEPTH_MASK.getpixel((x, y)) / 255.0
            h = HAZE_MASK.getpixel((x, y)) / 255.0
            if p > 0.08:
                if depth < 0.35:      # brzeg pociągnięcia
                    c = _mix(outline, edge, depth / 0.35)
                elif depth < 0.75:
                    c = _mix(edge, mid, (depth - 0.35) / 0.4)
                else:
                    c = _mix(mid, core, (depth - 0.75) / 0.25)
                grain = 1.0 + (rnd.random() - 0.5) * 0.08   # ziarno farby z puszki
                c = tuple(max(0, min(255, int(v * grain * light))) for v in c)
                a = int(round(255 * min(1.0, p * 1.6)))
                img.putpixel((x, y), c + (a,))
            elif h > 0.05:
                c = tuple(max(0, min(255, int(v * light))) for v in edge)
                img.putpixel((x, y), c + (int(round(255 * h * haze_alpha)),))
    return img


def _pulse():
    """Klatki pulsowania jedna pod drugą (format animacji Minecrafta): jasność 0,86–1,0."""
    sheet = Image.new('RGBA', (SIZE, SIZE * FRAMES), (0, 0, 0, 0))
    for i in range(FRAMES):
        k = 0.5 - 0.5 * math.cos(math.tau * i / FRAMES)
        frame = _texture(PAINT, PAINT_MID, PAINT_LIGHT, light=0.88 + 0.12 * k, haze_alpha=0.45 + 0.2 * k,
                         outline=PAINT_DEEP)
        sheet.paste(frame, (0, SIZE * i))
    return sheet


TEXTURES = {
    'znacznik_x': _pulse(),
    'znacznik_x_trafiony': _texture(HOT_EDGE, HOT, HOT_CORE, haze_alpha=0.9, outline=(214, 70, 8)),
}
MCMETA = {'znacznik_x': {'animation': {'frametime': 2, 'interpolate': True}}}


def model(name):
    """Płytka 16×16×0,5 px, tekstura z przodu (south) i z tyłu (north), bez boków."""
    tex = '#x'
    return {
        'textures': {'x': 'axon:item/' + name, 'particle': 'axon:item/' + name},
        'elements': [{
            'from': [0, 0, 7.75], 'to': [16, 16, 8.25],
            'shade': False,
            'faces': {
                'south': {'uv': [0, 0, 16, 16], 'texture': tex},
                'north': {'uv': [16, 0, 0, 16], 'texture': tex},
            },
        }],
        'display': {
            # gdyby ktoś wziął przedmiot do ręki albo położył w ramce: mały X przed oczami / w ramce
            'gui': {'rotation': [0, 0, 0], 'translation': [0, 0, 0], 'scale': [1, 1, 1]},
            'fixed': {'rotation': [0, 0, 0], 'translation': [0, 0, 0], 'scale': [1, 1, 1]},
        },
    }


def _png(img):
    buf = io.BytesIO()
    img.save(buf, 'PNG', optimize=True)
    return buf.getvalue()


def _json(data):
    return (json.dumps(data, indent=2, ensure_ascii=False) + '\n').encode()


def pliki():
    """Wszystkie pliki znacznika X do paczki."""
    files = {}
    for name in NAMES:
        files['assets/axon/textures/item/%s.png' % name] = _png(TEXTURES[name])
        if name in MCMETA:
            files['assets/axon/textures/item/%s.png.mcmeta' % name] = _json(MCMETA[name])
        files['assets/axon/models/block/%s.json' % name] = _json(model(name))
        files['assets/axon/items/%s.json' % name] = _json(
            {'model': {'type': 'minecraft:model', 'model': 'axon:block/' + name}})
        # 1.21.2–1.21.3 nie czytają items/: odpowiednik dla komponentu item_model (jak build_pack.legacy_models)
        files['axon_1_21_0/assets/axon/models/item/%s.json' % name] = _json({'parent': 'axon:block/' + name})
    return files


if __name__ == '__main__':
    # podgląd: python3 -m axoncore.znacznik_x (z zrodla/) zapisuje ../podglady/znacznik-x.png
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, '..', '..', 'podglady', 'znacznik-x.png')
    bark = [(66, 48, 34), (214, 210, 196), (92, 70, 48), (140, 112, 74)]   # świerk, brzoza, dąb, palma
    scale = 8
    pad = 16
    w = (SIZE * scale + pad) * 2 + pad
    h = (SIZE * scale + pad) * len(bark) + pad
    prev = Image.new('RGBA', (w, h), (28, 28, 30, 255))
    rnd = random.Random(3)
    for row, col in enumerate(bark):
        for i, name in enumerate(NAMES):
            tile = Image.new('RGBA', (SIZE, SIZE), col + (255,))
            for y in range(SIZE):   # słoje kory
                for x in range(SIZE):
                    v = 1.0 + 0.16 * math.sin(x * 0.9 + math.sin(y * 0.3) * 2) + (rnd.random() - 0.5) * 0.12
                    tile.putpixel((x, y), tuple(max(0, min(255, int(c * v))) for c in col) + (255,))
            tex = TEXTURES[name].crop((0, 0, SIZE, SIZE))
            tile.alpha_composite(tex)
            tile = tile.resize((SIZE * scale, SIZE * scale), Image.NEAREST)
            prev.paste(tile, (pad + i * (SIZE * scale + pad), pad + row * (SIZE * scale + pad)))
    prev.convert('RGB').save(out)
    print('podgląd:', os.path.abspath(out))
