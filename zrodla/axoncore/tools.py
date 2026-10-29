from .model import tool

T = {}

def handle(m, tex, top, wrap=None, wrap_to=4.5, cap=None):
    m.box((7.5, 0.5, 7.5), (8.5, top, 8.5), tex)
    if wrap:
        m.box((7.3, 1, 7.3), (8.7, wrap_to, 8.7), wrap)
    if cap:
        m.box((7.35, 0, 7.35), (8.65, 0.6, 8.65), cap)
    return m

# --- AxonCore: stalowe (złom, resor, szyna, saperka)
m = handle(tool(), 'steel_dark', 13, wrap='tape', cap='steel')
m.box((7.3, 8.8, 7.3), (8.7, 9.6, 8.7), 'tape')
m.box((8.5, 9.5, 7.7), (13, 14.5, 8.3), 'leafspring')
m.box((13, 9, 7.8), (13.6, 15, 8.2), 'edge')
m.box((6.6, 10.5, 7.4), (8.5, 13.5, 8.6), 'steel')
m.box((9.2, 11, 7.5), (9.8, 11.6, 8.5), 'brass')
m.box((9.2, 12.6, 7.5), (9.8, 13.2, 8.5), 'brass')
T['axon:steel_axe'] = m

m = handle(tool(), 'wood', 12, wrap='leather')
m.box((4, 11.6, 7.1), (12, 12.2, 8.9), 'rail')
m.box((3, 12.2, 7.6), (13, 13.4, 8.4), 'rail')
m.box((2.5, 13.4, 7.2), (13.5, 14.6, 8.8), 'rail', up='rust')
m.box((1.5, 12.9, 7.6), (2.5, 14.1, 8.4), 'steel')
m.box((13.5, 12.9, 7.6), (14.5, 14.1, 8.4), 'steel')
m.box((7.2, 12.4, 7.0), (8.8, 13.0, 9.0), 'brass')
T['axon:steel_pickaxe'] = m

m = handle(tool(), 'wood', 9.5, wrap='leather', wrap_to=3.5)
m.box((7.3, 9, 7.3), (8.7, 10.5, 8.7), 'olive')
m.box((5, 10.5, 7.75), (11, 15, 8.25), 'olive_chipped')
m.box((6, 15, 7.75), (10, 16, 8.25), 'olive_chipped')
m.box((7.6, 11, 7.6), (8.4, 11.8, 8.4), 'steel')
T['axon:steel_shovel'] = m

m = handle(tool(), 'ash', 13.5, wrap='leather')
m.box((8.5, 9.5, 7.65), (12, 14.5, 8.35), 'forged')
m.box((12, 9, 7.7), (13.5, 15, 8.3), 'tempered')
m.box((13.5, 8.5, 7.75), (14, 15.5, 8.25), 'edge')
m.box((5.5, 11, 7.4), (8.5, 13.5, 8.6), 'forged')
m.box((7.6, 13.5, 7.6), (8.4, 14, 8.4), 'brass')
T['axon:hardened_axe'] = m

m = handle(tool(), 'ash', 12, wrap='leather')
m.box((3, 12, 7.3), (13, 14, 8.7), 'forged')
m.box((6.5, 11.5, 7.1), (9.5, 14.5, 8.9), 'forged', up='steel')
m.box((1.8, 12.4, 7.5), (3, 13.6, 8.5), 'tempered')
m.box((13, 12.4, 7.5), (14.2, 13.6, 8.5), 'tempered')
m.box((1.2, 12.7, 7.7), (1.8, 13.3, 8.3), 'diamond')
m.box((14.2, 12.7, 7.7), (14.8, 13.3, 8.3), 'diamond')
T['axon:hardened_pickaxe'] = m

# --- vanilla: drewniane i kamienne (prymitywne, wiązane)
def primitive(head, lash, stick):
    return {
        'axe': lambda: (handle(tool(), stick, 13.5)
                        .box((8.5, 10, 7.6), (12, 14.5, 8.4), head)
                        .box((7.3, 11, 7.3), (8.7, 12, 8.7), lash)
                        .box((7.3, 13, 7.3), (8.7, 13.8, 8.7), lash)),
        'pickaxe': lambda: (handle(tool(), stick, 12.5)
                            .box((3, 12.5, 7.5), (13, 14, 8.5), head)
                            .box((1.8, 12.8, 7.7), (3, 13.7, 8.3), head)
                            .box((13, 12.8, 7.7), (14.2, 13.7, 8.3), head)
                            .box((7.2, 11.8, 7.2), (8.8, 12.6, 8.8), lash)),
        'shovel': lambda: (handle(tool(), stick, 10.5)
                           .box((6, 10.5, 7.6), (10, 15, 8.4), head)
                           .box((6.8, 15, 7.6), (9.2, 15.8, 8.4), head)
                           .box((7.3, 9.6, 7.3), (8.7, 10.6, 8.7), lash)),
        'hoe': lambda: (handle(tool(), stick, 14)
                        .box((8.5, 12.8, 7.6), (12, 14.3, 8.4), head)
                        .box((11, 11.5, 7.7), (12, 12.8, 8.3), head)
                        .box((7.3, 12.6, 7.3), (8.7, 13.6, 8.7), lash)),
    }

for kind, fn in primitive('wood_light', 'leather', 'wood').items():
    T['minecraft:wooden_' + kind] = fn()
for kind, fn in primitive('stone', 'cord', 'wood_dark').items():
    T['minecraft:stone_' + kind] = fn()
