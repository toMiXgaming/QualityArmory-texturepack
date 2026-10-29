"""Pojemniki z łupem (ItemDisplay nad blokiem-nośnikiem): beczki, skrzynie, apteczka, wojskowa, elitarna, spadochron.
Budowane przodem na północ; gen_axoncore.py obraca je przodem na południe jak meble."""
from .stations import Station

C = {}

def drum(body, hoop, top, cap=True, band=None):
    m = Station()
    m.part((2, 0, 1), (14, 15, 15), body, up=top, down='steel_dark')
    m.part((1, 0, 2), (15, 15, 14), body, up=top, down='steel_dark')
    for y in (0, 4.5, 10, 14.2):
        m.part((1.6, y, 0.6), (14.4, y + 0.8, 15.4), hoop)
        m.part((0.6, y, 1.6), (15.4, y + 0.8, 14.4), hoop)
    if band:
        m.part((1.7, 6, 0.7), (14.3, 9, 15.3), band)
        m.part((0.7, 6, 1.7), (15.3, 9, 14.3), band)
    if cap:
        m.part((10, 15, 10), (12, 15.6, 12), 'steel_dark')
        m.part((4, 15, 4), (5.5, 15.4, 5.5), 'steel_dark')
    return m

C['beczka'] = drum('blue_chipped', 'steel_dark', 'steel')
C['beczka_paliwa'] = drum('red_paint', 'steel_dark', 'black', band='yellow_paint')
C['beczka_rdza'] = drum('rust_heavy', 'rust', 'rust')

def rozbita(body, hoop, band=None):
    """Beczka po zniszczeniu: wgnieciony dół z poszarpanym brzegiem, wieko na ziemi, łup w środku."""
    m = Station()
    m.part((2, 0, 1), (14, 7, 15), body, up='black', down='steel_dark')
    m.part((1, 0, 2), (15, 7, 14), body, up='black', down='steel_dark')
    for x0, x1, h in ((2, 5, 10), (5, 8, 8.5), (8, 11, 11), (11, 14, 9)):           # poszarpany brzeg, przód
        m.part((x0, 7, 1), (x1, h, 2), body)
    for x0, x1, h in ((2, 6, 8.5), (6, 10, 10.5), (10, 14, 8)):                     # tył
        m.part((x0, 7, 14), (x1, h, 15), body)
    for z0, z1, h in ((2, 7, 9.5), (7, 11, 7.8), (11, 14, 10)):                     # boki
        m.part((1, 7, z0), (2, h, z1), body)
        m.part((14, 7, z0), (15, h + 0.8 if h < 9 else h - 1.5, z1), body)
    m.part((1.6, 3.5, 0.6), (14.4, 4.5, 15.4), hoop)                                # obręcz
    m.part((0.6, 3.5, 1.6), (15.4, 4.5, 14.4), hoop)
    if band:
        m.part((1.7, 5, 0.7), (14.3, 7, 15.3), band)
    m.part((3, 6.5, 3), (13, 7.2, 13), 'black')                                    # wnętrze
    m.part((4, 7, 5), (8, 9, 8), 'rust')                                            # łup: złom, puszka, szmata
    m.part((8.5, 7, 7), (11, 10, 9.5), 'steel', up='steel_light')
    m.part((5, 7, 9), (9, 7.8, 12), 'cloth')
    m.part((-3, 0, 6), (8, 1, 17), 'steel', up=body if body != 'red_paint' else 'black',
           rot={'angle': 22.5, 'axis': 'z', 'origin': [-3, 0, 11]})                # wieko oparte o beczkę
    m.part((13, 0, -2), (16, 1.2, 1), body)                                         # odłamki
    m.part((15.5, 0, 9), (18, 0.8, 11), hoop)
    return m

C['beczka_rozbita'] = rozbita('blue_chipped', 'steel_dark')
C['beczka_paliwa_rozbita'] = rozbita('red_paint', 'steel_dark', band='yellow_paint')
C['beczka_rdza_rozbita'] = rozbita('rust_heavy', 'rust')

def skrzynia():
    m = Station()
    m.part((0.5, 0, 0.5), (15.5, 13, 15.5), 'plank', up='plank_dark')
    for x, z in ((0, 0), (14, 0), (0, 14), (14, 14)):                  # narożniki
        m.part((x, 0, z), (x + 2, 13.5, z + 2), 'plank_dark')
    for y in (0, 11.5):                                                 # obwódki
        m.part((0, y, 0), (16, y + 2, 0.5), 'plank_dark')
        m.part((0, y, 15.5), (16, y + 2, 16), 'plank_dark')
        m.part((0, y, 0), (0.5, y + 2, 16), 'plank_dark')
        m.part((15.5, y, 0), (16, y + 2, 16), 'plank_dark')
    m.part((0, 5.75, -0.2), (16, 7.25, 16.2), 'plank_dark')            # deska środkowa
    m.part((-0.2, 5.75, 0), (16.2, 7.25, 16), 'plank_dark')
    m.part((6, 9, -0.4), (10, 11, 0.1), 'steel_dark')                    # tabliczka
    return m
C['skrzynia_drewniana'] = skrzynia()

def narzedziowa():
    m = Station()
    m.part((2, 0, 4), (14, 6, 12), 'red_paint', up='red_paint')
    m.part((1.8, 6, 3.8), (14.2, 7.5, 12.2), 'red_paint', up='steel_dark')
    m.part((2, 5.8, 3.6), (14, 6.3, 12.4), 'steel_dark')
    m.part((5, 7.5, 7.4), (6, 10, 8.6), 'steel_dark')                   # rączka
    m.part((10, 7.5, 7.4), (11, 10, 8.6), 'steel_dark')
    m.part((5, 9.5, 7.5), (11, 10.5, 8.5), 'black')
    m.part((3, 4.5, 3.5), (4.5, 6.5, 4), 'steel_light')                 # zatrzaski
    m.part((11.5, 4.5, 3.5), (13, 6.5, 4), 'steel_light')
    return m
C['skrzynka_narzedziowa'] = narzedziowa()

def apteczka():
    m = Station()
    m.part((1, 2, 10), (15, 16, 16), 'white_enamel')                   # szafka wisząca
    m.part((1.5, 2.5, 9.6), (14.5, 15.5, 10), 'white_enamel')            # drzwiczki
    m.part((7, 5, 9.4), (9, 13, 9.6), 'red_paint')                      # krzyż
    m.part((4, 8, 9.4), (12, 10, 9.6), 'red_paint')
    m.part((12.8, 8, 9.1), (13.6, 10.5, 9.6), 'steel_dark')             # klamka
    m.part((0.6, 1.6, 9.8), (15.4, 2.2, 16), 'steel')
    return m
C['szafka_medyczna'] = apteczka()

def jedzenie():
    m = Station()
    m.part((1, 0, 2), (15, 9, 14), 'cardboard')
    m.part((1, 9, 2), (15, 9.3, 14), None, up='black')
    m.part((0, 8.5, 2), (1, 12, 14), 'cardboard', rot={'angle': -22.5, 'axis': 'z', 'origin': [1, 9, 8]})   # klapy
    m.part((15, 8.5, 2), (16, 12, 14), 'cardboard', rot={'angle': 22.5, 'axis': 'z', 'origin': [15, 9, 8]})
    m.part((1, 4, 1.7), (15, 5.5, 2), 'tape')
    for x, z, t in ((2.5, 3.5, 'steel'), (6, 3.5, 'red_paint'), (9.5, 4, 'steel'), (3, 8, 'yellow_paint'), (7, 8.5, 'steel_light'), (10.5, 8, 'red_paint')):
        m.part((x, 7, z), (x + 3, 11, z + 3), t, up='steel_light')      # puszki
    return m
C['skrzynka_jedzenie'] = jedzenie()

def wojskowa():
    m = Station()
    m.part((0, 0, 2), (32, 10, 14), 'olive', up='olive_chipped')         # dwa bloki długości
    m.part((-0.3, 8, 1.7), (32.3, 10.6, 14.3), 'olive')                  # wieko
    for x in (2, 14.5, 27):
        m.part((x, 0, 1.6), (x + 3, 10.8, 14.4), 'black')                # opaski
    m.part((7, 3, 1.7), (13, 6, 2), 'yellow_paint')                      # szablon napisu
    m.part((19, 3, 1.7), (25, 6, 2), 'yellow_paint')
    for x in (8.5, 21.5):
        m.part((x, 6.5, 1.2), (x + 2, 8.5, 1.7), 'steel_light')          # zatrzaski
    m.part((-0.8, 4, 6), (0, 6, 10), 'steel_dark')                       # uchwyty
    m.part((32, 4, 6), (32.8, 6, 10), 'steel_dark')
    for e in m.elements:                                                 # przesunięcie w granice -16..32
        e['from'][0] -= 1
        e['to'][0] -= 1
    return m
C['skrzynia_wojskowa'] = wojskowa()

def elitarna():
    m = Station()
    m.part((0, 0, 1), (16, 11, 15), 'black', up='steel_dark')
    m.part((-0.3, 9, 0.7), (16.3, 11.5, 15.3), 'steel_dark', up='black')
    for x in range(0, 16, 4):
        m.part((x, 0.5, 0.6), (x + 2, 2.5, 1), 'yellow_paint')
        m.part((x + 2, 0.5, 0.6), (x + 4, 2.5, 1), 'black')
    m.part((5.5, 4, 0.5), (10.5, 8, 1), 'steel_light')                   # zamek szyfrowy
    m.part((6.5, 5, 0.3), (9.5, 7, 0.5), 'green_led')
    m.part((1, 4, 0.6), (3, 9, 1), 'steel')
    m.part((13, 4, 0.6), (15, 9, 1), 'steel')
    return m
C['skrzynia_elitarna'] = elitarna()

def spadochron():
    """Rozłożona czasza nad spadającym zrzutem (axon:zrzut z gen_zrzut.py); plugin zdejmuje ją po lądowaniu."""
    m = Station()
    for i, (r, y) in enumerate(((16, 23), (14, 26), (10, 28.5), (5, 30))):
        tex = 'red_paint' if i % 2 == 0 else 'white_enamel'
        m.part((8 - r, y, 8 - r), (8 + r, y + 3 if i < 3 else 31.5, 8 + r), tex, down='cloth' if i == 0 else tex)
    for x, z in ((-7, -7), (22, -7), (-7, 22), (22, 22)):
        m.part((x, 16.5, z), (x + 1, 23, z + 1), None, north='cord', south='cord', east='cord', west='cord')
    return m
C['spadochron'] = spadochron()
