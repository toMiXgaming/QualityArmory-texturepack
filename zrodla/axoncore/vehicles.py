"""Wraki pojazdów z PRL (wyświetlacz przedmiotu jak auta z gen_auta.py, transformacja NONE).

Pojazd budujemy w decymetrach (1 kratka = 1 m), przodem na zachód (x = 0); gen_axoncore.py obraca go
przodem na północ. Model mieści się w zakresie -16..32, więc wymiary są zmniejszone o f jednostek
na decymetr i plugin rysuje go ze skalą `scale` = 1.6 / f. Spód kół leży na y = 0, więc środek modelu
(8 8 8) jest scale / 2 kratki nad gruntem, w środku obrysu pojazdu.

Tekstury: każdy wrak ma własną teksturę (surface.SolidModel), ok. 48 pikseli na metr, z materiałami
liczonymi w prawdziwej skali (lakier z odpryskami i zaciekami rdzy, szkło z odbiciem i pęknięciami,
chrom, opony z bieżnikiem, lampy). Wcześniej cały bok auta był jednym kafelkiem 8×8 z atlasu
rozciągniętym na 3–10 m, przez co wraki wyglądały jak plamy pikseli.
"""
import numpy as np

from .surface import (SolidModel, MATS, paint, metal, rust_over, rubber, fabric, edge_wear, rgb, lerp,
                      smooth, vnoise)

V = {}

PX_PER_M = 48


# ---------------------------------------------------------------- materiały wraków

def car_paint(ctx, color, worn=0.35, grime=0.45, rust=0.35):
    """Lakier samochodowy: odpryski przy krawędziach, zacieki rdzy spod spodu, kurz na dole."""
    col = paint(ctx, color, chip=(122, 116, 108), chips=0.25, worn=worn, grime=grime)
    # zacieki rdzy pionowo w dół od krawędzi (progi, nadkola)
    if rust > 0 and ctx.face not in ('up', 'down'):
        streak = vnoise(ctx.X * 1.3 + ctx.Z * 1.3, ctx.Y * 0.08, ctx.Y * 0, ctx.seed + 401)
        low = 1 - smooth(4, 16, ctx.Y)
        m = smooth(0.62, 0.8, streak * 0.8 + low * 0.45) * rust
        col = lerp(col, rgb((118, 64, 34)) * (0.85 + 0.3 * ctx.noise(3, 3, 3, 403))[..., None], m)
    # kurz na dachu i masce
    if ctx.face == 'up':
        dust = ctx.noise(0.6, 0.6, 0.6, 405, 3)
        col = lerp(col, rgb((150, 140, 118)), smooth(0.45, 0.85, dust) * 0.45)
    return col


def glass(ctx, broken=False):
    """Szyba: ciemna, z jaśniejszym ukośnym odbiciem nieba, brudem przy ramce i pęknięciami."""
    t = smooth(0.0, 1.2, ctx.E)
    base = lerp(rgb((22, 28, 34)), rgb((44, 58, 70)), t)
    diag = (ctx.X + ctx.Z) * 0.35 + ctx.Y * 0.5
    refl = smooth(0.35, 0.0, np.abs(((diag % 6.0) - 3.0)) - 1.6)
    col = base + rgb((70, 86, 98)) * (refl * 0.55 * t)[..., None]
    dirt = ctx.noise(1.5, 1.5, 1.5, 411, 3)
    col = lerp(col, rgb((92, 86, 70)), smooth(0.55, 0.9, dirt) * 0.35 + smooth(0.6, 0.0, ctx.E) * 0.4)
    if broken:
        # pajączek: promienie i okręgi wokół punktu uderzenia
        cx, cy = ctx.center[0] * 0.6 + ctx.center[2] * 0.4, ctx.center[1]
        dx = (ctx.X * 0.6 + ctx.Z * 0.4) - cx + 2.0
        dy = ctx.Y - cy - 1.0
        r = np.hypot(dx, dy)
        ang = np.arctan2(dy, dx)
        rays = smooth(0.08, 0.0, np.abs(np.sin(ang * 7.0 + vnoise(r, r, r, ctx.seed + 413) * 0.6)) * r * 0.5)
        rings = smooth(0.12, 0.0, np.abs(np.sin(r * 1.4))) * (r < 6)
        crack = np.clip((rays + rings * 0.6) * (r < 9), 0, 1)
        col = lerp(col, rgb((176, 186, 190)), crack * 0.75)
    return col


def chrome(ctx):
    """Chrom (zderzaki, felgi): jasny pas odbicia, ciemny dół, wżery rdzy."""
    v = smooth(0.0, 1.0, (ctx.Y - ctx.box.frm[1]) / max(0.2, ctx.box.to[1] - ctx.box.frm[1]))
    col = lerp(rgb((70, 74, 80)), rgb((196, 200, 204)), np.clip(v * 1.6 - 0.2, 0, 1))
    col = col * (1 + 0.06 * (ctx.streak(0.5, 20.0, 421, 2) - 0.5))[..., None]
    return rust_over(ctx, col, 0.45)


def tire(ctx):
    """Opona: guma z bieżnikiem na obwodzie i wytartym bokiem."""
    col = rubber(ctx, (36, 36, 38))
    if ctx.face in ('up', 'down', 'east', 'west'):
        tread = (np.floor((ctx.X + ctx.Z) * 1.2) % 2) * smooth(0.2, 0.5, ctx.E)
        col = col * (1 - 0.35 * tread)[..., None]
    side = smooth(0.4, 1.6, ctx.E)
    return col * (0.92 + 0.12 * side)[..., None]


def lamp(ctx, inner, outer):
    """Klosz lampy: jaśniejszy środek, ciemna obwódka, brud i pęknięcie."""
    t = smooth(0.0, 0.9, ctx.E)
    col = lerp(rgb(outer), rgb(inner), t)
    dirt = ctx.noise(2.5, 2.5, 2.5, 431, 2)
    return col * (0.78 + 0.25 * dirt)[..., None]


def corrosion(ctx, heavy=False):
    """Przerdzewiała blacha: ciemny brąz z pomarańczowymi wykwitami, wżery i dziury."""
    n = ctx.noise(0.5, 0.5, 0.5, 451, 4)
    fine = ctx.noise(4.0, 4.0, 4.0, 453, 2)
    col = lerp(rgb((74, 44, 30)), rgb((150, 82, 40)), smooth(0.3, 0.75, n * 0.7 + fine * 0.3))
    col = col * (0.85 + 0.3 * ctx.noise(9, 9, 9, 455))[..., None]
    pits = ctx.noise(2.2, 2.2, 2.2, 457, 2)
    col = col * (1 - 0.45 * smooth(0.72, 0.8, pits))[..., None]
    if heavy:
        holes = ctx.noise(0.9, 0.9, 0.9, 459, 3)
        col = lerp(col, rgb((22, 18, 16)), smooth(0.74, 0.78, holes))
    return edge_wear(ctx, col, 0.12, -0.15)


def tarp(ctx):
    """Plandeka: płótno w kolorze khaki z fałdami i plamami."""
    col = fabric(ctx, (124, 120, 86))
    fold = 0.5 + 0.5 * np.sin((ctx.X + ctx.Z) * 0.9 + vnoise(ctx.X * 0.3, ctx.Y * 0.3, ctx.Z * 0.3, ctx.seed) * 3)
    col = col * (0.9 + 0.12 * fold)[..., None]
    stain = ctx.noise(0.5, 0.5, 0.5, 441, 3)
    return lerp(col, rgb((82, 80, 60)), smooth(0.6, 0.85, stain) * 0.5)


CAR_MATS = {
    'red_paint': lambda c: car_paint(c, (150, 44, 34)),
    'cardboard': lambda c: car_paint(c, (190, 166, 118), worn=0.3),
    'white_enamel': lambda c: car_paint(c, (214, 210, 194), worn=0.3, rust=0.45),
    'blue_chipped': lambda c: car_paint(c, (52, 88, 138), worn=0.45),
    'olive': lambda c: car_paint(c, (84, 98, 60), worn=0.3, rust=0.25),
    'olive_chipped': lambda c: car_paint(c, (78, 92, 56), worn=0.55, rust=0.4),
    'rust': corrosion,
    'rust_heavy': lambda c: corrosion(c, heavy=True),
    'steel': lambda c: metal(c, (122, 126, 130), rust=0.4),
    'steel_dark': lambda c: metal(c, (66, 68, 72), brushed=0.05, rust=0.3),
    'steel_light': lambda c: metal(c, (150, 154, 158), rust=0.3),
    'black': lambda c: paint(c, (32, 32, 34), chip=(70, 70, 74), chips=0.15, grime=0.3),
    'glass': glass,
    'glass_broken': lambda c: glass(c, broken=True),
    'chrome': chrome,
    'rubber': tire,
    'headlight': lambda c: lamp(c, (214, 214, 196), (120, 120, 112)),
    'taillight': lambda c: lamp(c, (176, 40, 30), (88, 26, 22)),
    'cloth': tarp,
    'cord': lambda c: fabric(c, (110, 96, 70)),
    'plank_dark': MATS['plank_dark'],
}
for _k, _fn in CAR_MATS.items():
    MATS['car_' + _k] = _fn


class Vehicle(SolidModel):
    def __init__(self, length, width):
        super().__init__(display=None, gui_light='side')
        self.L, self.W = length, width
        self.f = min(1.6, 46 / length)          # jednostki modelu na decymetr
        self.scale = round(1.6 / self.f, 3)
        self.unit = 1.6 / self.f                # jednostka modelu w 1/16 m (dla materiałów)
        self.density = PX_PER_M / (10 * self.f)  # pikseli na jednostkę modelu
        self.wreck_rot = None
        self.display = {
            'gui': {'rotation': [30, 225, 0], 'translation': [0, 0, 0], 'scale': [0.35, 0.35, 0.35]},
            'ground': {'rotation': [0, 0, 0], 'translation': [0, 2, 0], 'scale': [0.25, 0.25, 0.25]},
        }

    def p(self, x, y, z):
        f = self.f
        return (round(8 + (x - self.L / 2) * f, 3), round(y * f, 3), round(8 + (z - self.W / 2) * f, 3))

    def b(self, a, c, tex, **faces):
        faces = {k: ('car_' + v if isinstance(v, str) else v) for k, v in faces.items()}
        if self.wreck_rot:
            faces['rot'] = dict(self.wreck_rot)
        return self.solid(self.p(*a), self.p(*c), 'car_' + tex, **faces)

    def wheel(self, x, z0, z1, r, tire='rubber', rim='chrome'):
        """Koło jako dwa skrzyżowane prostopadłościany (ośmiokąt) + felga."""
        k = r * 0.42
        self.b((x - r, r - k, z0), (x + r, r + k, z1), tire)
        self.b((x - k, 0, z0), (x + k, 2 * r, z1), tire)
        side = z0 if z0 < self.W / 2 else z1
        d = -0.2 if side == z0 else 0.2
        self.b((x - r * 0.45, r * 0.55, side), (x + r * 0.45, r * 1.45, side + d), rim)

    def windows(self, x0, x1, y0, y1, z_in=0.0, glass='glass'):
        """Szyby boczne (cienkie płaty na obu bokach)."""
        self.b((x0, y0, -0.15 + z_in), (x1, y1, 0 + z_in), glass)
        self.b((x0, y0, self.W - z_in), (x1, y1, self.W + 0.15 - z_in), glass)

# ---------------------------------------------------------------- Fiat 126p: mały, zaokrąglony, czerwony wyblakły
def maluch():
    v = Vehicle(31, 14)
    v.b((1, 3, 0.5), (30, 8, 13.5), 'red_paint', up='rust')                 # dół nadwozia
    v.b((0, 3, 1.5), (31, 7, 12.5), 'red_paint')
    v.b((8, 8, 1), (24, 12.5, 13), 'red_paint', up='rust_heavy')             # kabina
    v.b((9, 12.5, 1.5), (23, 13, 12.5), 'red_paint')
    v.windows(9, 23, 8.5, 12, 0.85)
    v.b((7.6, 8.2, 1.5), (8, 12, 12.5), 'glass_broken')                      # szyba przednia (zbita)
    v.b((24, 8.2, 2), (24.4, 12, 12), 'glass')
    v.b((-0.3, 4, 3), (0.2, 5.5, 5), 'headlight')                            # reflektory
    v.b((-0.3, 4, 9), (0.2, 5.5, 11), 'headlight')
    v.b((30.8, 4.5, 1.5), (31.3, 5.8, 3.5), 'taillight')                     # lampy tylne
    v.b((30.8, 4.5, 10.5), (31.3, 5.8, 12.5), 'taillight')
    v.b((-0.5, 2.5, 0.5), (0.5, 3.5, 13.5), 'chrome')                        # zderzaki
    v.b((30.5, 2.5, 0.5), (31.5, 3.5, 13.5), 'chrome')
    v.b((27, 6.5, 3), (31.2, 7.5, 11), 'steel_dark')                         # kratka silnika z tyłu
    v.b((15.5, 3.5, 0.3), (15.8, 8, 0.5), 'black')                           # szczelina drzwi
    v.b((15.5, 3.5, 13.5), (15.8, 8, 13.7), 'black')
    v.b((12, 6.6, 0.2), (13.5, 7, 0.5), 'chrome')                            # klamki
    v.b((12, 6.6, 13.5), (13.5, 7, 13.8), 'chrome')
    v.wheel(6, 0.2, 2.5, 2.5)
    v.wheel(6, 11.5, 13.8, 2.5)
    v.wheel(24.5, 11.5, 13.8, 2.5)
    v.b((23, 0, 0.5), (26, 2, 3), 'rust')                                    # brak koła: cegły
    return v
V['wrak_fiat_126p'] = maluch()

# ---------------------------------------------------------------- Polonez: kanciasty hatchback, beżowy
def polonez():
    v = Vehicle(43, 17)
    v.b((0, 3, 0.5), (43, 9, 16.5), 'cardboard')
    v.b((11, 9, 1), (36, 14, 16), 'cardboard')                               # kabina
    v.b((36, 9, 1), (41, 12, 16), 'cardboard')                               # opadający tył
    v.windows(12, 35, 9.5, 13.5, 0.85)
    v.b((10.5, 9.3, 1.5), (11, 13.5, 15.5), 'glass')
    v.b((40.8, 9.3, 2), (41.3, 11.6, 15), 'glass_broken')                    # tylna szyba
    v.b((-0.4, 5.5, 2), (0.1, 7.5, 6), 'headlight')                          # prostokątne lampy
    v.b((-0.4, 5.5, 11), (0.1, 7.5, 15), 'headlight')
    v.b((-0.4, 5.6, 6.5), (0.1, 7.4, 10.5), 'black')                         # grill
    v.b((42.9, 6, 1), (43.4, 7.5, 5), 'taillight')
    v.b((42.9, 6, 12), (43.4, 7.5, 16), 'taillight')
    v.b((-0.8, 2.5, 0.3), (0.5, 4, 16.7), 'black')                           # zderzaki
    v.b((42.5, 2.5, 0.3), (43.8, 4, 16.7), 'black')
    v.b((-0.3, 5, 0.3), (43.3, 5.4, 16.7), 'chrome')                         # listwa boczna
    for x in (12, 24):
        v.b((x, 3.5, 0.3), (x + 0.3, 9, 0.5), 'black')                       # szczeliny drzwi
        v.b((x, 3.5, 16.5), (x + 0.3, 9, 16.7), 'black')
    v.b((14, 14, 2), (32, 14.6, 15), 'rust_heavy')                           # rdza na dachu
    v.wheel(8, 0.2, 2.6, 3)
    v.wheel(34, 0.2, 2.6, 3)
    v.wheel(8, 14.4, 16.8, 3)
    v.b((32, 0, 14.4), (36, 1.5, 16.8), 'rubber')                            # leżąca opona
    return v
V['wrak_polonez'] = polonez()

# ---------------------------------------------------------------- Żuk: dostawczy z budą, niebieski
def zuk():
    v = Vehicle(45, 19)
    v.b((0, 3, 1), (12, 10, 18), 'blue_chipped')                            # maska i kabina dół
    v.b((3, 10, 1), (13, 17, 18), 'blue_chipped', up='white_enamel')        # kabina
    v.windows(4, 12, 11, 15.5, 0.9)
    v.b((2.6, 11, 2), (3, 15.5, 17), 'glass_broken')
    v.b((13, 3, 0), (45, 19, 19), 'white_enamel', down='steel_dark')        # buda
    v.b((20, 19, 3), (38, 19.5, 14), 'rust')
    v.b((12.8, 3, -0.2), (45.2, 4, 19.2), 'blue_chipped')                   # pas
    v.b((44.9, 4.5, 2), (45.3, 17, 9.4), 'steel')                            # drzwi tylne
    v.b((44.9, 4.5, 9.6), (45.3, 17, 17), 'steel')
    v.b((45.1, 5, 1), (45.5, 6.5, 2.5), 'taillight')
    v.b((45.1, 5, 16.5), (45.5, 6.5, 18), 'taillight')
    v.b((-0.4, 5, 2.5), (0.1, 7, 5), 'headlight')
    v.b((-0.4, 5, 14), (0.1, 7, 16.5), 'headlight')
    v.b((-0.4, 4.5, 5.5), (0.1, 8.5, 13.5), 'steel_dark')                   # grill
    v.b((-0.8, 2.5, 0.5), (0.4, 4, 18.5), 'chrome')                          # zderzak
    v.wheel(7, 0, 2.5, 3)
    v.wheel(7, 16.5, 19, 3)
    v.wheel(36, 0, 2.5, 3)
    v.wheel(36, 16.5, 19, 3)
    return v
V['wrak_zuk'] = zuk()

# ---------------------------------------------------------------- Nysa: mikrobus, oliwkowy z białym dachem
def nysa():
    v = Vehicle(46, 19)
    v.b((0, 3, 1), (46, 9, 18), 'olive_chipped')
    v.b((1, 9, 1), (46, 19, 18), 'olive', up='white_enamel')
    v.b((0, 9, 1.5), (1, 17, 17.5), 'olive')
    v.b((-0.2, 11, 2), (0.6, 17, 17), 'glass')                               # szyba przednia
    for x in (4, 14, 24, 34):
        v.windows(x, x + 8, 11, 17, 0.9, glass='glass_broken' if x == 24 else 'glass')
    v.b((-0.4, 5, 2), (0.1, 7, 4.5), 'headlight')
    v.b((-0.4, 5, 14.5), (0.1, 7, 17), 'headlight')
    v.b((-0.4, 4.5, 6), (0.1, 6.5, 13), 'chrome')
    v.b((45.9, 5, 1.5), (46.3, 7, 3.5), 'taillight')
    v.b((45.9, 5, 15.5), (46.3, 7, 17.5), 'taillight')
    v.b((10, 3.5, 0.8), (10.4, 17, 1), 'black')                              # szczelina drzwi
    v.b((5, 19, 4), (40, 19.6, 15), 'rust')
    v.wheel(8, 0, 2.5, 3)
    v.wheel(8, 16.5, 19, 3)
    v.wheel(38, 0, 2.5, 3)
    v.b((36, 0, 16.5), (40, 2, 19), 'rust')
    return v
V['wrak_nysa'] = nysa()

# ---------------------------------------------------------------- Star 266: wojskowa ciężarówka z plandeką
def star():
    v = Vehicle(70, 25)
    v.b((0, 5, 2), (70, 7, 23), 'steel_dark')                                # rama
    v.b((0, 7, 2), (13, 15, 23), 'olive', up='olive_chipped')                # maska
    v.b((-0.4, 8, 4), (0.4, 14, 21), 'black')                                # grill
    v.b((13, 7, 1), (25, 24, 24), 'olive', up='olive_chipped')               # kabina
    v.windows(15, 23, 15, 22, 1.0)
    v.b((12.6, 15.5, 2), (13, 22.5, 23), 'glass')
    v.b((27, 7, 0), (70, 12, 25), 'olive_chipped', up='plank_dark')          # skrzynia
    v.b((27, 12, 0), (70, 27, 25), 'cloth')                                  # plandeka
    v.b((26.8, 12, -0.2), (70.2, 13, 25.2), 'olive_chipped')
    for x in (30, 40, 50, 60):
        v.b((x, 12, -0.3), (x + 1, 27, 25.3), 'cord')                        # pasy plandeki
    v.b((-0.6, 9, 2), (0.2, 11, 5), 'headlight')
    v.b((-0.6, 9, 20), (0.2, 11, 23), 'headlight')
    v.b((69.8, 8, 1), (70.4, 9.5, 3), 'taillight')
    v.b((69.8, 8, 22), (70.4, 9.5, 24), 'taillight')
    v.b((-1, 4.5, 0.5), (0.5, 6.5, 24.5), 'steel_dark')                      # zderzak
    v.b((22, 8, -0.6), (26, 11, 0), 'steel_dark')                            # zbiornik
    for x in (9, 48, 60):
        v.wheel(x, -0.2, 3.5, 5, rim='steel_dark')
        v.wheel(x, 21.5, 25.2, 5, rim='steel_dark')
    return v
V['wrak_star_266'] = star()

# ---------------------------------------------------------------- Autosan: autobus, kremowy z czerwonym pasem
def autosan():
    v = Vehicle(100, 25)
    v.b((0, 4, 0.5), (100, 12, 24.5), 'white_enamel', down='steel_dark')
    v.b((0, 12, 0.5), (100, 28, 24.5), 'white_enamel')
    v.b((-0.2, 9, 0.3), (100.2, 12, 24.7), 'red_paint')                       # pas
    v.b((-0.2, 4, 0.3), (100.2, 5, 24.7), 'red_paint')
    v.b((-0.3, 13, 1.5), (0.2, 25, 23.5), 'glass_broken')                    # szyba przednia
    for x in range(6, 94, 11):
        v.windows(x, x + 9, 15, 25, 0.5, glass='glass_broken' if x in (39, 72) else 'glass')
    v.b((10, 4.5, 24.5), (16, 25, 24.8), 'steel_dark')                       # drzwi
    v.b((-0.6, 6, 2), (0.1, 8, 6), 'headlight')
    v.b((-0.6, 6, 19), (0.1, 8, 23), 'headlight')
    v.b((99.9, 6, 1.5), (100.5, 8.5, 4), 'taillight')
    v.b((99.9, 6, 21), (100.5, 8.5, 23.5), 'taillight')
    v.b((-0.8, 3, 0.5), (0.4, 4.5, 24.5), 'chrome')                          # zderzak
    v.b((20, 28, 4), (80, 28.6, 21), 'rust_heavy')
    for x in (15, 80):
        v.wheel(x, 0, 3, 5)
        v.wheel(x, 22, 25, 5)
    return v
V['wrak_autosan'] = autosan()

# ---------------------------------------------------------------- Ursus: ciągnik, czerwony, wielkie tylne koła
def ursus():
    v = Vehicle(36, 18)
    v.b((0, 6, 6), (22, 13, 12), 'red_paint')                                # maska
    v.b((-0.3, 7, 6.5), (0.2, 12, 11.5), 'steel_dark')                       # grill
    v.b((-0.4, 10, 6.8), (0.1, 11.5, 8), 'headlight')
    v.b((-0.4, 10, 10), (0.1, 11.5, 11.2), 'headlight')
    v.b((2, 13, 8.3), (3, 19, 9.7), 'rust')                                  # wydech
    v.b((18, 5, 5), (30, 10, 13), 'steel_dark')                              # skrzynia biegów
    v.b((24, 10, 7), (28, 13, 11), 'black')                                  # siedzenie
    v.b((22, 10, 8.5), (23, 15, 9.5), 'steel_dark')                          # kolumna kierownicy
    v.b((21, 15, 6.5), (24, 15.5, 11.5), 'black')
    v.b((22, 10, 3), (32, 11, 6), 'red_paint')                               # błotniki
    v.b((22, 10, 12), (32, 11, 15), 'red_paint')
    v.b((30, 4, 7), (36, 5, 11), 'steel')                                    # zaczep
    v.wheel(5, 2, 5, 3.5, rim='red_paint')
    v.wheel(5, 13, 16, 3.5, rim='red_paint')
    v.wheel(27, -0.3, 4, 7, rim='red_paint')
    v.wheel(27, 14, 18.3, 7, rim='red_paint')
    return v
V['wrak_ursus'] = ursus()

# ---------------------------------------------------------------- WSK: motocykl na boku
def wsk():
    v = Vehicle(20, 7)
    v.wreck_rot = {'angle': -45, 'axis': 'x', 'origin': [8, 0, 8]}           # przewrócony na bok
    v.b((4, 2, 2.5), (16, 4, 4.5), 'steel_dark')                             # rama
    v.b((6, 4, 2), (12, 7, 5), 'red_paint')                                  # bak
    v.b((11, 7, 2.2), (16, 8, 4.8), 'black')                                 # siodło
    v.b((7, 1.5, 2.2), (11, 4, 4.8), 'steel')                                # silnik
    v.b((3, 4, 3), (4, 10, 4), 'chrome')                                     # widelec
    v.b((1, 10, 0.5), (5, 10.7, 6.5), 'black')                               # kierownica
    v.b((2, 8, 2.5), (3.5, 9.5, 4.5), 'headlight')                           # lampa
    v.b((12, 1, 1.5), (18, 2, 2.5), 'chrome')                                # tłumik
    v.wheel(3, 2.8, 4.2, 3)
    v.wheel(17, 2.8, 4.2, 3)
    return v
V['wrak_wsk'] = wsk()
