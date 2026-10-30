"""Pojemniki z łupem (ItemDisplay nad blokiem-nośnikiem): beczki, skrzynie, apteczka, wojskowa, elitarna, spadochron.
Budowane przodem na północ; gen_axoncore.py obraca je przodem na południe jak meble."""
from .stations import Station
from .barrels import MODELS as BARRELS
from .crates import MODELS as CRATES

C = {}

C.update(BARRELS)   # beczki i ich wersje rozbite mają własny model i tekstury (barrels.py)
C.update(CRATES)    # skrzynie, szafka i karton też mają własny model i tekstury (crates.py)

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
