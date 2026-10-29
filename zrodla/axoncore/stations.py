"""Stanowiska (ItemDisplay): warsztaty T1-T3 z etapami zużycia, piec hutniczy, recykler, stół badań.
Budowane przodem na północ; gen_axoncore.py obraca je przodem na południe jak meble."""
from .model import Model

# wyświetlanie jak blok: w GUI rzut izometryczny, w ramce/ItemDisplay 1:1
BLOCKLIKE = {
    'gui': {'rotation': [30, 225, 0], 'translation': [0, 0, 0], 'scale': [0.5, 0.5, 0.5]},
    'ground': {'rotation': [0, 0, 0], 'translation': [0, 3, 0], 'scale': [0.25, 0.25, 0.25]},
    'fixed': {'rotation': [0, 0, 0], 'translation': [0, 0, 0], 'scale': [1, 1, 1]},
    'head': {'rotation': [0, 0, 0], 'translation': [0, 0, 0], 'scale': [1, 1, 1]},
    'thirdperson_righthand': {'rotation': [75, 45, 0], 'translation': [0, 2.5, 0], 'scale': [0.3, 0.3, 0.3]},
    'firstperson_righthand': {'rotation': [0, 45, 0], 'translation': [0, 0, 0], 'scale': [0.3, 0.3, 0.3]},
}

# etapy zużycia: 0 nowy, 1 porysowany, 2 rdza, 3 rozbity (bez części oznaczonych fragile)
WEAR = [
    {},
    {'olive': 'olive_chipped', 'blue_enamel': 'blue_chipped', 'steel_light': 'steel'},
    {'olive': 'rust', 'olive_chipped': 'rust', 'blue_enamel': 'rust', 'blue_chipped': 'rust',
     'steel_light': 'rail', 'steel': 'rail', 'yellow_paint': 'rust', 'plank': 'plank_dark', 'red_paint': 'rust'},
    {'olive': 'rust_heavy', 'olive_chipped': 'rust_heavy', 'blue_enamel': 'rust_heavy', 'blue_chipped': 'rust_heavy',
     'steel_light': 'rust', 'steel': 'rust', 'rail': 'rust', 'yellow_paint': 'rust_heavy', 'plank': 'wood_dark',
     'plank_dark': 'wood_dark', 'red_paint': 'rust_heavy', 'green_led': 'black', 'glow': 'black', 'brass': 'rust'},
]

class Station(Model):
    def __init__(self, wear=0):
        super().__init__(display=BLOCKLIKE, rotation=None, gui_light='side')
        self.wear = wear

    def part(self, frm, to, tex, fragile=False, **faces):
        if fragile and self.wear >= 3:
            return self
        m = WEAR[self.wear]
        tex = m.get(tex, tex) if tex else tex
        faces = {k: (m.get(v, v) if isinstance(v, str) else v) for k, v in faces.items()}
        return self.box(frm, to, tex, **faces)

S = {}

# ---------------------------------------------------------------- Warsztat T1: stół z desek, tablica z narzędziami
def warsztat_t1(w):
    m = Station(w)
    for x, z in ((0.5, 0.5), (13.5, 0.5), (0.5, 9.5), (13.5, 9.5)):
        m.part((x, 0, z), (x + 2, 10, z + 2), 'plank_dark')
    m.part((0, 10, 0), (16, 12, 12), 'plank', down='plank_dark')                 # blat
    m.part((1, 3, 1), (15, 4, 11), 'plank_dark')                                 # półka
    m.part((0.5, 0, 12), (2, 26, 13.5), 'plank_dark')                            # słupki tablicy
    m.part((14, 0, 12), (15.5, 26, 13.5), 'plank_dark')
    m.part((1, 12, 12.6), (15, 25, 13.2), 'cardboard')                           # tablica (płyta pilśniowa)
    m.part((0, 25, 12), (16, 26.5, 13.8), 'plank')                               # daszek tablicy
    # narzędzia na tablicy
    m.part((3, 15, 12), (3.8, 22, 12.6), 'wood', fragile=True)                   # młotek
    m.part((2, 20.5, 11.8), (4.8, 22.5, 12.6), 'steel_dark', fragile=True)
    m.part((6.5, 14.5, 12.1), (7.3, 22.5, 12.6), 'steel', fragile=True)          # klucz
    m.part((6, 21.5, 12), (7.8, 23, 12.6), 'steel', fragile=True)
    m.part((10, 16, 12.1), (13, 22, 12.6), 'red_paint', fragile=True)            # piła kabłąkowa
    m.part((10.4, 16.4, 12), (12.6, 21.6, 12.65), 'cardboard', fragile=True)
    m.part((11, 12, 12.1), (11.8, 16, 12.6), 'wood', fragile=True)
    # imadło i złom na blacie
    m.part((11, 12, 1), (15, 13.5, 4), 'steel_light', fragile=True)
    m.part((11.5, 13.5, 1), (14.5, 15, 2), 'steel_dark', fragile=True)
    m.part((11.5, 13.5, 3), (14.5, 15, 4), 'steel_dark', fragile=True)
    m.part((12.7, 14, 4), (13.3, 14.6, 6.5), 'steel', fragile=True)
    m.part((2, 12, 2), (7, 12.3, 7), 'steel_dark')                               # blacha
    m.part((3, 4, 3), (7, 6, 7), 'rust')                                         # złom na półce
    m.part((9, 4, 6), (13, 5, 9), 'steel')
    return m

# ---------------------------------------------------------------- Warsztat T2: stalowy stół w oliwce, szuflady, wiertarka
def warsztat_t2(w):
    m = Station(w)
    m.part((0, 0, 0), (6, 11, 12), 'olive', north='olive', up='steel_dark')       # szafka z szufladami
    for y in (1, 4.5, 8):
        m.part((0.5, y, -0.4), (5.5, y + 2.8, 0), 'olive_chipped')
        m.part((2, y + 1.6, -0.9), (4, y + 2.1, -0.4), 'steel_light', fragile=True)
    m.part((14, 0, 0.5), (15.5, 11, 2), 'steel_dark')                            # nogi
    m.part((14, 0, 10), (15.5, 11, 11.5), 'steel_dark')
    m.part((6, 1.5, 1), (15, 2.5, 11), 'steel_dark')                             # poprzeczka
    m.part((-0.5, 11, -0.5), (16.5, 12.5, 12.5), 'steel', up='steel_light', down='steel_dark')  # blat stalowy
    m.part((0, 12.5, 12), (16, 15, 13), 'steel_dark')                            # listwa tylna
    # wiertarka stołowa
    m.part((11, 12.5, 6), (15, 13.5, 11), 'blue_enamel')
    m.part((12.4, 13.5, 9), (13.6, 26, 10.2), 'steel')                           # kolumna
    m.part((11, 22, 6.5), (15, 26, 10.6), 'blue_enamel', up='blue_chipped')           # głowica
    m.part((14.8, 22.5, 7.5), (16, 25.5, 9.5), 'steel_dark')                     # silnik
    m.part((12.7, 19.5, 7.6), (13.3, 22, 8.2), 'steel_light', fragile=True)      # wiertło
    m.part((10, 23.6, 8), (11, 24.2, 8.6), 'black', fragile=True)                # dźwignia
    m.part((8, 23.6, 8), (10, 24.2, 8.6), 'steel', fragile=True)
    # imadło, lampa
    m.part((1, 12.5, 1), (5.5, 14, 4.5), 'steel_dark', fragile=True)
    m.part((1.5, 14, 1), (5, 15.6, 2), 'steel_dark', fragile=True)
    m.part((1.5, 14, 3.5), (5, 15.6, 4.5), 'steel_dark', fragile=True)
    m.part((7, 12.5, 10), (8, 22, 11), 'steel_dark', fragile=True)
    m.part((5.5, 20.5, 6), (9.5, 22.5, 10), 'steel_dark', fragile=True, down='glow')
    return m

# ---------------------------------------------------------------- Warsztat T3: tokarka na ciężkiej podstawie
def warsztat_t3(w):
    m = Station(w)
    m.part((0, 0, 1), (16, 9, 11), 'steel_dark', up='black')                     # podstawa
    m.part((0, 0, 0.6), (16, 1.2, 1), 'yellow_paint')                            # pas ostrzegawczy
    for x in range(1, 16, 3):
        m.part((x, 0, 0.5), (x + 1.4, 1.2, 0.6), 'black')
    m.part((0.5, 3, 0.6), (7.5, 8, 1), 'olive')                                  # drzwiczki
    m.part((8.5, 3, 0.6), (15.5, 8, 1), 'olive')
    m.part((6.5, 5, 0.2), (7, 6.5, 0.6), 'steel_light')
    m.part((9, 5, 0.2), (9.5, 6.5, 0.6), 'steel_light')
    m.part((-0.5, 9, 0.5), (16.5, 10.5, 11.5), 'steel', up='steel_dark')         # łoże
    m.part((0, 10.5, 2), (5, 18, 10), 'olive', up='olive_chipped')               # wrzeciennik
    m.part((0.5, 18, 3), (4.5, 20, 9), 'steel_dark')                             # osłona pasa
    m.part((5, 13, 5), (7, 15.5, 7.5), 'steel_light')                            # uchwyt
    for y, z in ((15.3, 5.8), (12.6, 5.8)):
        m.part((7, y, z), (7.6, y + 0.6, z + 0.9), 'steel_dark', fragile=True)
    m.part((7.6, 13.9, 6), (13, 14.5, 6.6), 'steel_light', fragile=True)         # obrabiany pręt
    m.part((13, 10.5, 3), (16, 16, 9.5), 'olive', up='olive_chipped')            # konik
    m.part((12, 13.5, 6), (13, 14.7, 7), 'steel', fragile=True)
    m.part((7.5, 10.5, 2), (11.5, 12, 10), 'steel')                              # suport
    m.part((8.5, 12, 5), (10.5, 13, 8.5), 'steel_dark', fragile=True)
    m.part((9, 11, 0.5), (11, 12.2, 2), 'black', fragile=True)                   # pokrętło
    # panel sterowania z grzybkiem awaryjnym
    m.part((0.5, 10.5, 10.5), (4, 25, 12), 'steel_dark')
    m.part((-0.5, 20, 9.5), (5, 26, 12.5), 'white_enamel', north='white_enamel')
    m.part((0.5, 23, 9), (2, 24.5, 9.5), 'green_led')
    m.part((3, 22.5, 8.6), (4.4, 24, 9.5), 'red_paint', fragile=True)
    m.part((0.5, 20.8, 9), (4, 22, 9.5), 'black')
    return m

for name, fn in (('warsztat_t1', warsztat_t1), ('warsztat_t2', warsztat_t2), ('warsztat_t3', warsztat_t3)):
    S[name] = fn(0)
    for w in (1, 2, 3):
        S[f'{name}_zuzycie{w}'] = fn(w)

# ---------------------------------------------------------------- Piec Hutniczy: ceglany trzon, tygiel, wysoki komin
def piec(lit):
    m = Station()
    m.part((0, 0, 0), (16, 4, 16), 'concrete', up='stone_dark')
    m.part((1, 4, 1), (15, 14, 15), 'red_paint', north='red_paint', up='stone_dark')    # ceglany trzon
    for y in (6.5, 9.5, 12.5):
        m.part((0.9, y, 0.9), (15.1, y + 0.4, 15.1), 'concrete')                       # fugi
    m.part((4, 5, 0.4), (12, 11, 1), 'glow' if lit else 'black')                       # palenisko
    m.part((3.5, 11, 0.2), (12.5, 12, 1), 'steel_dark')
    m.part((3.5, 4.4, 0.2), (12.5, 5, 1), 'steel_dark')
    m.part((2, 14, 2), (14, 15, 14), 'steel_dark')                                     # płyta
    m.part((4, 15, 4), (10, 20, 10), 'rust_heavy', up='glow' if lit else 'black')      # tygiel
    m.part((3.6, 19, 3.6), (10.4, 20, 10.4), 'steel_dark')
    m.part((11, 15, 10), (14, 32, 13), 'steel_dark', up='black')                       # komin
    m.part((10.6, 22, 9.6), (14.4, 23, 13.4), 'rust')
    m.part((10.6, 29, 9.6), (14.4, 30, 13.4), 'rust')
    m.part((15, 7, 4), (16.5, 9, 12), 'steel', east='steel_light')                     # dmuchawa
    m.part((16.5, 6, 6), (18, 10, 10), 'olive')
    return m
S['piec_hutniczy'] = piec(False)
S['piec_hutniczy_on'] = piec(True)

# ---------------------------------------------------------------- Recykler: żółta maszyna z lejem i kołem zamachowym
def recykler():
    m = Station()
    m.part((0, 0, 1), (16, 2, 15), 'black')                                     # rama
    m.part((1, 2, 2), (15, 14, 14), 'yellow_paint', up='steel_dark')
    m.part((0.6, 6, 1.6), (15.4, 7, 14.4), 'black')                              # pas
    for x in range(1, 15, 3):
        m.part((x, 6, 1.5), (x + 1.4, 7, 1.6), 'yellow_paint')
    m.part((3, 14, 3), (13, 15, 13), 'steel_dark')
    m.part((2, 15, 2), (14, 20, 3), 'steel', north='steel_light')                # lej
    m.part((2, 15, 13), (14, 20, 14), 'steel', south='steel_light')
    m.part((2, 15, 3), (3, 20, 13), 'steel')
    m.part((13, 15, 3), (14, 20, 13), 'steel')
    m.part((4, 9, 0.4), (12, 12, 2), 'black')                                    # wylot
    m.part((4, 3, -3), (12, 4, 2), 'rubber')                                     # rynna
    m.part((3.5, 3, -3), (4, 5, 2), 'steel_dark')
    m.part((12, 3, -3), (12.5, 5, 2), 'steel_dark')
    m.part((11, 3, 1.6), (14, 5, 2), 'green_led')                                # kontrolka
    m.part((15, 7, 7), (16, 9, 9), 'steel_dark')                                 # oś koła
    return m
S['recykler'] = recykler()

def kolo():
    """Koło zamachowe recyklera: osobny model w osi X, obracany przez plugin."""
    m = Station()
    m.part((16, 2, 2), (17, 14, 14), None, east='steel_dark', west='steel_dark')
    m.part((15.8, 2, 7), (17.2, 14, 9), 'steel')                                 # szprychy
    m.part((15.8, 7, 2), (17.2, 9, 14), 'steel')
    m.part((15.6, 2, 2), (17.4, 3, 14), 'red_paint')                             # wieniec
    m.part((15.6, 13, 2), (17.4, 14, 14), 'red_paint')
    m.part((15.6, 3, 2), (17.4, 13, 3), 'red_paint')
    m.part((15.6, 3, 13), (17.4, 13, 14), 'red_paint')
    m.part((17.4, 7, 7), (18, 9, 9), 'brass')
    m.part((16.4, 11, 11), (18.5, 12, 12), 'black')                              # rączka
    return m
S['recykler_kolo'] = kolo()

# ---------------------------------------------------------------- Stół Badań: biurko z komputerem w stylu lat 80.
def stol_badan():
    m = Station()
    m.part((0, 0, 0), (5, 11, 12), 'plank_dark', north='plank')                  # szafka biurka
    m.part((1.5, 7, -0.3), (3.5, 7.6, 0), 'brass')
    m.part((1.5, 3, -0.3), (3.5, 3.6, 0), 'brass')
    m.part((14, 0, 0.5), (15.5, 11, 2), 'plank_dark')
    m.part((14, 0, 10), (15.5, 11, 11.5), 'plank_dark')
    m.part((-0.5, 11, -0.5), (16.5, 12.5, 12.5), 'plank', down='plank_dark')
    # monitor kineskopowy na jednostce centralnej
    m.part((3, 12.5, 4), (13, 15.5, 12), 'white_enamel')                         # jednostka
    m.part((4, 13.2, 3.7), (8, 13.8, 4), 'black')                                # stacja dyskietek
    m.part((10.5, 13.3, 3.7), (11.2, 14, 4), 'red_paint')
    m.part((4, 15.5, 5), (12, 23.5, 12.5), 'white_enamel', south='cardboard')   # obudowa CRT
    m.part((5, 16.5, 4.6), (11, 22.5, 5), 'screen')
    m.part((5.5, 17, 4.5), (10.5, 22, 4.6), None, north='green_led')            # świecący ekran
    m.part((5, 16.2, 13), (11, 22, 15.5), 'cardboard')                           # tył kineskopu
    m.part((10, 15.7, 4.6), (10.8, 16.3, 5), 'green_led')                        # dioda
    m.part((3, 12.5, 0), (12, 13.2, 3), 'white_enamel', up='black')              # klawiatura
    # notatki i lampka
    m.part((13, 12.5, 1), (16, 12.7, 5), 'white_enamel', fragile=True)
    m.part((13.5, 12.7, 1.5), (15.5, 12.9, 4), 'cloth', rot={'angle': 22.5, 'axis': 'y', 'origin': [14.5, 12.7, 3]})
    m.part((14, 12.5, 9), (16, 13.2, 11), 'black')
    m.part((14.7, 13.2, 9.7), (15.3, 20, 10.3), 'steel_dark')
    m.part((13, 19, 7.5), (16, 21, 10.5), 'olive', down='glow')
    return m
S['stol_badan'] = stol_badan()
