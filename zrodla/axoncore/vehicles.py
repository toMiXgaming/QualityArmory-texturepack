"""Wraki pojazdów z PRL (wyświetlacz przedmiotu jak auta z gen_auta.py, transformacja NONE).

Pojazd budujemy w decymetrach (1 kratka = 1 m), przodem na zachód (x = 0); gen_axoncore.py obraca go
przodem na północ. Model mieści się w zakresie -16..32, więc wymiary są zmniejszone o f jednostek
na decymetr i plugin rysuje go ze skalą `scale` = 1.6 / f. Spód kół leży na y = 0, więc środek modelu
(8 8 8) jest scale / 2 kratki nad gruntem, w środku obrysu pojazdu.
"""
from .model import Model

V = {}

class Vehicle(Model):
    def __init__(self, length, width):
        super().__init__(display=None, rotation=None, gui_light='side')
        self.L, self.W = length, width
        self.f = min(1.6, 46 / length)          # jednostki modelu na decymetr
        self.scale = round(1.6 / self.f, 3)
        self.display = {
            'gui': {'rotation': [30, 225, 0], 'translation': [0, 0, 0], 'scale': [0.35, 0.35, 0.35]},
            'ground': {'rotation': [0, 0, 0], 'translation': [0, 2, 0], 'scale': [0.25, 0.25, 0.25]},
        }

    def p(self, x, y, z):
        f = self.f
        return (round(8 + (x - self.L / 2) * f, 3), round(y * f, 3), round(8 + (z - self.W / 2) * f, 3))

    def b(self, a, c, tex, **faces):
        return self.box(self.p(*a), self.p(*c), tex, **faces)

    def wheel(self, x, z0, z1, r, tire='rubber', rim='steel_dark'):
        """Koło jako dwa skrzyżowane prostopadłościany (ośmiokąt) + felga."""
        k = r * 0.42
        self.b((x - r, r - k, z0), (x + r, r + k, z1), tire)
        self.b((x - k, 0, z0), (x + k, 2 * r, z1), tire)
        side = z0 if z0 < self.W / 2 else z1
        d = -0.2 if side == z0 else 0.2
        self.b((x - r * 0.45, r * 0.55, side), (x + r * 0.45, r * 1.45, side + d), rim)

    def windows(self, x0, x1, y0, y1, z_in=0.0, glass='black'):
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
    v.b((7.6, 8.2, 1.5), (8, 12, 12.5), 'black')                             # szyba przednia (zbita)
    v.b((24, 8.2, 2), (24.4, 12, 12), 'black')
    v.b((-0.3, 4, 3), (0.2, 5.5, 5), 'white_enamel')                         # reflektory
    v.b((-0.3, 4, 9), (0.2, 5.5, 11), 'white_enamel')
    v.b((-0.5, 2.5, 0.5), (0.5, 3.5, 13.5), 'steel')                         # zderzaki
    v.b((30.5, 2.5, 0.5), (31.5, 3.5, 13.5), 'steel')
    v.b((27, 6.5, 3), (31.2, 7.5, 11), 'steel_dark')                         # kratka silnika z tyłu
    v.wheel(6, 0.2, 2.5, 2.5)
    v.wheel(6, 11.5, 13.8, 2.5)
    v.wheel(24.5, 11.5, 13.8, 2.5)
    v.b((23, 0, 0.5), (26, 2, 3), 'rust')                                    # brak koła: cegły
    return v
V['wrak_fiat_126p'] = maluch()

# ---------------------------------------------------------------- Polonez: kanciasty hatchback, beżowy
def polonez():
    v = Vehicle(43, 17)
    v.b((0, 3, 0.5), (43, 9, 16.5), 'cardboard', up='white_enamel')
    v.b((11, 9, 1), (36, 14, 16), 'cardboard', up='cardboard')                    # kabina
    v.b((36, 9, 1), (41, 12, 16), 'cardboard')                               # opadający tył
    v.windows(12, 35, 9.5, 13.5, 0.85)
    v.b((10.5, 9.3, 1.5), (11, 13.5, 15.5), 'black')
    v.b((-0.4, 5.5, 2), (0.1, 7.5, 6), 'white_enamel')                       # prostokątne lampy
    v.b((-0.4, 5.5, 11), (0.1, 7.5, 15), 'white_enamel')
    v.b((-0.4, 5.6, 6.5), (0.1, 7.4, 10.5), 'black')                         # grill
    v.b((42.9, 6, 1), (43.4, 7.5, 5), 'red_paint')
    v.b((42.9, 6, 12), (43.4, 7.5, 16), 'red_paint')
    v.b((-0.8, 2.5, 0.3), (0.5, 4, 16.7), 'black')
    v.b((42.5, 2.5, 0.3), (43.8, 4, 16.7), 'black')
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
    v.b((0, 3, 1), (12, 10, 18), 'blue_chipped', up='blue_chipped')         # maska i kabina dół
    v.b((3, 10, 1), (13, 17, 18), 'blue_chipped', up='white_enamel')        # kabina
    v.windows(4, 12, 11, 15.5, 0.9)
    v.b((2.6, 11, 2), (3, 15.5, 17), 'black')
    v.b((13, 3, 0), (45, 19, 19), 'white_enamel', down='steel_dark')
    v.b((20, 19, 3), (38, 19.5, 14), 'rust')  # buda
    v.b((12.8, 3, -0.2), (45.2, 4, 19.2), 'blue_chipped')                   # pas
    v.b((44.9, 4.5, 2), (45.3, 17, 9.4), 'steel', east='steel')              # drzwi tylne
    v.b((44.9, 4.5, 9.6), (45.3, 17, 17), 'steel')
    v.b((-0.4, 5, 2.5), (0.1, 7, 5), 'white_enamel')
    v.b((-0.4, 5, 14), (0.1, 7, 16.5), 'white_enamel')
    v.b((-0.4, 4.5, 5.5), (0.1, 8.5, 13.5), 'steel_dark')
    v.b((-0.8, 2.5, 0.5), (0.4, 4, 18.5), 'steel')
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
    v.b((-0.2, 11, 2), (0.6, 17, 17), 'black')                               # szyba przednia
    for x in (4, 14, 24, 34):
        v.windows(x, x + 8, 11, 17, 0.9)
    v.b((-0.4, 5, 2), (0.1, 7, 4.5), 'white_enamel')
    v.b((-0.4, 5, 14.5), (0.1, 7, 17), 'white_enamel')
    v.b((-0.4, 4.5, 6), (0.1, 6.5, 13), 'steel')
    v.b((10, 3.5, -0.2), (10.4, 17, 0), 'black')                             # szczelina drzwi
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
    v.b((0, 8, 4), (0.4, 14, 21), 'black')                                   # grill
    v.b((13, 7, 1), (25, 24, 24), 'olive', up='olive_chipped')               # kabina
    v.windows(15, 23, 15, 22, 1.0)
    v.b((12.6, 15.5, 2), (13, 22.5, 23), 'black')
    v.b((27, 7, 0), (70, 12, 25), 'olive', up='plank_dark')                  # skrzynia
    v.b((27, 12, 0), (70, 27, 25), 'cloth', up='cloth')                       # plandeka
    v.b((26.8, 12, -0.2), (70.2, 13, 25.2), 'olive_chipped')
    for x in (30, 40, 50, 60):
        v.b((x, 12, -0.3), (x + 1, 27, 25.3), 'cord')                        # łuki plandeki
    v.b((-0.6, 9, 2), (0.2, 11, 5), 'white_enamel')
    v.b((-0.6, 9, 20), (0.2, 11, 23), 'white_enamel')
    v.b((-1, 4.5, 0.5), (0.5, 6.5, 24.5), 'steel_dark')
    v.b((22, 10, -0.6), (26, 12, 0), 'steel_dark')                           # zbiornik
    for x in (9, 48, 60):
        v.wheel(x, -0.2, 3.5, 5)
        v.wheel(x, 21.5, 25.2, 5)
    return v
V['wrak_star_266'] = star()

# ---------------------------------------------------------------- Autosan: autobus, kremowy z czerwonym pasem
def autosan():
    v = Vehicle(100, 25)
    v.b((0, 4, 0.5), (100, 12, 24.5), 'white_enamel', up='white_enamel', down='steel_dark')
    v.b((0, 12, 0.5), (100, 28, 24.5), 'white_enamel')
    v.b((-0.2, 9, 0.3), (100.2, 12, 24.7), 'red_paint')                       # pas
    v.b((-0.2, 4, 0.3), (100.2, 5, 24.7), 'red_paint')
    v.b((-0.3, 13, 1.5), (0.2, 25, 23.5), 'black')                           # szyba przednia
    for x in range(6, 94, 11):
        v.windows(x, x + 9, 15, 25, 0.5)
    v.b((10, 4.5, 24.5), (16, 25, 24.8), 'steel_dark')                       # drzwi
    v.b((-0.6, 6, 2), (0.1, 8, 6), 'white_enamel')
    v.b((-0.6, 6, 19), (0.1, 8, 23), 'white_enamel')
    v.b((20, 28, 4), (80, 28.6, 21), 'rust_heavy')
    for x in (15, 80):
        v.wheel(x, 0, 3, 5)
        v.wheel(x, 22, 25, 5)
    return v
V['wrak_autosan'] = autosan()

# ---------------------------------------------------------------- Ursus: ciągnik, czerwony, wielkie tylne koła
def ursus():
    v = Vehicle(36, 18)
    v.b((0, 6, 6), (22, 13, 12), 'red_paint', up='red_paint')                # maska
    v.b((-0.3, 7, 6.5), (0.2, 12, 11.5), 'steel_dark')                       # grill
    v.b((2, 13, 8.3), (3, 19, 9.7), 'black')                                 # wydech
    v.b((18, 5, 5), (30, 10, 13), 'steel_dark')                              # skrzynia biegów
    v.b((24, 10, 7), (28, 13, 11), 'black')                                  # siedzenie
    v.b((22, 10, 8.5), (23, 15, 9.5), 'steel_dark')                          # kolumna kierownicy
    v.b((21, 15, 6.5), (24, 15.5, 11.5), 'black')
    v.b((22, 10, 3), (32, 11, 6), 'red_paint')                               # błotniki
    v.b((22, 10, 12), (32, 11, 15), 'red_paint')
    v.b((30, 4, 7), (36, 5, 11), 'steel')                                    # zaczep
    v.wheel(5, 2, 5, 3.5)
    v.wheel(5, 13, 16, 3.5)
    v.wheel(27, -0.3, 4, 7)
    v.wheel(27, 14, 18.3, 7)
    return v
V['wrak_ursus'] = ursus()

# ---------------------------------------------------------------- WSK: motocykl na boku
def wsk():
    v = Vehicle(20, 7)
    v.rotation = {'angle': -45, 'axis': 'x', 'origin': [8, 0, 8]}            # przewrócony na bok
    v.b((4, 2, 2.5), (16, 4, 4.5), 'steel_dark')                             # rama
    v.b((6, 4, 2), (12, 7, 5), 'red_paint', up='red_paint')                  # bak
    v.b((11, 7, 2.2), (16, 8, 4.8), 'black')                                 # siodło
    v.b((7, 1.5, 2.2), (11, 4, 4.8), 'steel')                                # silnik
    v.b((3, 4, 3), (4, 10, 4), 'steel')                                      # widelec
    v.b((1, 10, 0.5), (5, 10.7, 6.5), 'black')                               # kierownica
    v.b((2, 8, 2.5), (3.5, 9.5, 4.5), 'white_enamel')                        # lampa
    v.b((12, 1, 1.5), (18, 2, 2.5), 'steel_light')                           # tłumik
    v.wheel(3, 2.8, 4.2, 3)
    v.wheel(17, 2.8, 4.2, 3)
    return v
V['wrak_wsk'] = wsk()
