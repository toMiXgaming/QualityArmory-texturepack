"""Bloki podmieniane globalnie (nadpisują modele vanilla)."""
from .model import Model
from .barrels import barrel

BLOCK_DISPLAY = None  # bloki dziedziczą wyświetlanie z block/block przez "parent"
B = {}

def block():
    return Model(display=None, rotation=None, gui_light=None)

# --- stół rzemieślniczy T0: blat z desek obity blachą, imadło, młotek, półka
m = block()
# Podłoga z desek: stół podmienia pełny blok vanilla, więc gra nie rysuje górnej ściany bloku pod spodem.
# Bez niej między nogami widać dziurę w ziemi.
m.box((0, 0, 0), (16, 0.5, 16), 'plank_dark', up='plank')
for x, z in ((1, 1), (13, 1), (1, 13), (13, 13)):
    m.box((x, 0, z), (x + 2, 13, z + 2), 'plank_dark')
m.box((0, 13, 0), (16, 16, 16), 'plank', down='plank_dark')
m.box((1.5, 3, 1.5), (14.5, 4.5, 14.5), 'plank_dark')
m.box((1, 16, 1), (9, 16.3, 9), 'steel_dark')                       # blacha na blacie
m.box((10.5, 16, 1.5), (14.5, 17.5, 4.5), 'steel', up='steel_light')  # imadło: korpus
m.box((11, 17.5, 1.5), (14, 19, 2.5), 'steel_dark')                   # szczęka tylna
m.box((11, 17.5, 3.5), (14, 19, 4.5), 'steel_dark')                   # szczęka przednia
m.box((12.2, 18, 4.5), (12.8, 18.6, 7), 'steel_light')                # śruba imadła
m.box((3, 16.3, 11), (11, 16.9, 11.6), 'wood')                        # młotek: trzonek
m.box((10, 16.3, 10), (12, 17.5, 12.6), 'steel_dark')                 # młotek: obuch
m.box((2, 4.5, 3), (6, 6, 7), 'rust')                                 # złom na półce
m.box((9, 4.5, 9), (13, 5.5, 12), 'steel')
B['minecraft:block/crafting_table'] = m

# --- piec: blaszana skrzynia na kamieniach, drzwiczki z kratką, komin
def furnace(lit):
    m = block()
    m.box((0, 0, 0), (16, 3, 16), 'stone', up='stone_dark')
    m.box((1, 3, 1), (15, 14, 15), 'rust_heavy', north='steel_dark', up='steel_dark')
    m.box((0.6, 13.5, 0.6), (15.4, 14.5, 15.4), 'steel')                 # rant
    m.box((4, 5, 0.4), (12, 11.5, 1), 'glow' if lit else 'black', north='glow' if lit else 'black')
    for x in (5, 7, 9, 11):
        m.box((x - 0.3, 5, 0.1), (x + 0.3, 11.5, 0.6), 'steel_dark')    # kratka
    m.box((3.6, 11.5, 0.2), (12.4, 12.2, 1), 'steel')
    m.box((12.5, 7.5, 0), (13.5, 9, 0.6), 'brass')                       # zasuwka
    m.box((10, 14, 10), (13, 16, 13), 'steel_dark', up='black')           # komin
    return m
B['minecraft:block/furnace'] = furnace(False)
B['minecraft:block/furnace_on'] = furnace(True)

# --- ognisko: krąg kamieni, polana, rożen z garnkiem
def campfire(lit):
    m = block()
    for x, z in ((1, 1), (6, 0), (11, 1), (0, 6), (13, 6), (1, 11), (6, 13), (11, 11)):
        m.box((x, 0, z), (x + 4, 2.5, z + 3), 'stone', up='stone_dark')
    m.box((3, 0, 5), (13, 2, 7), 'wood_dark', up='wood')
    m.box((5, 0, 3), (7, 2.5, 13), 'wood_dark', up='wood')
    m.box((9, 0, 4), (11, 2, 12), 'wood_dark', up='wood')
    m.box((1, 0, 7.4), (2, 12, 8.6), 'wood')                             # stojaki
    m.box((14, 0, 7.4), (15, 12, 8.6), 'wood')
    m.box((0.5, 11, 7.6), (15.5, 11.8, 8.4), 'steel_dark')                # rożen
    m.box((5.5, 5, 5.5), (10.5, 9.5, 10.5), 'black', up='steel_dark')      # garnek
    m.box((7.6, 9.5, 7.6), (8.4, 11, 8.4), 'steel_dark')                  # ucho
    if lit:
        m.box((0.8, 1, 8), (15.2, 13, 8), None, north='fire', south='fire',
              rot={'angle': 45, 'axis': 'y', 'origin': [8, 8, 8]})
        m.box((8, 1, 0.8), (8, 13, 15.2), None, east='fire', west='fire',
              rot={'angle': 45, 'axis': 'y', 'origin': [8, 8, 8]})
    return m
B['minecraft:block/campfire'] = campfire(True)
B['minecraft:block/campfire_off'] = campfire(False)

# --- beczka: ten sam model i tekstura co axon:beczka (barrels.py), otwarta pokazuje wnętrze
def _vanilla_barrel(open_):
    m = barrel('beczka', open_)
    m.display = None
    return m
B['minecraft:block/barrel'] = _vanilla_barrel(False)
B['minecraft:block/barrel_open'] = _vanilla_barrel(True)
