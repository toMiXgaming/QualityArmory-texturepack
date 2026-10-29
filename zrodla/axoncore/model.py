"""Budowanie modeli Minecrafta (JSON) z prostopadłościanów z kafelkami atlasu."""
from .atlas import uv

ATLAS_REF = 'axon:block/axoncore_atlas'
FACES = ('north', 'south', 'east', 'west', 'up', 'down')

class Model:
    def __init__(self, display=None, rotation=None, gui_light='side'):
        self.elements = []
        self.display = display
        self.rotation = rotation  # wspólny obrót wszystkich elementów
        self.gui_light = gui_light

    def box(self, frm, to, tex, **face_tex):
        faces = {}
        for f in FACES:
            t = face_tex.get(f, tex)
            if t is None:
                continue
            if t == 'fire':
                faces[f] = {'uv': [0, 0, 16, 16], 'texture': '#fire'}
            else:
                faces[f] = {'uv': uv(t), 'texture': '#a'}
        el = {'from': list(frm), 'to': list(to), 'faces': faces}
        rot = face_tex.get('rot') or self.rotation
        if rot:
            el['rotation'] = rot
        self.elements.append(el)
        return self

    def json(self):
        textures = {'a': ATLAS_REF, 'particle': ATLAS_REF}
        if any(f.get('texture') == '#fire' for e in self.elements for f in e['faces'].values()):
            textures['fire'] = 'minecraft:block/campfire_fire'
        out = {'textures': textures, 'elements': self.elements}
        if self.gui_light:
            out['gui_light'] = self.gui_light
        if self.display:
            out['display'] = self.display
        return out

HANDHELD = {
    'thirdperson_righthand': {'rotation': [0, -90, 55], 'translation': [0, 4, 0.5], 'scale': [0.85, 0.85, 0.85]},
    'thirdperson_lefthand': {'rotation': [0, 90, -55], 'translation': [0, 4, 0.5], 'scale': [0.85, 0.85, 0.85]},
    'firstperson_righthand': {'rotation': [0, -90, 25], 'translation': [1.13, 3.2, 1.13], 'scale': [0.68, 0.68, 0.68]},
    'firstperson_lefthand': {'rotation': [0, 90, -25], 'translation': [1.13, 3.2, 1.13], 'scale': [0.68, 0.68, 0.68]},
    'ground': {'rotation': [0, 0, 0], 'translation': [0, 2, 0], 'scale': [0.5, 0.5, 0.5]},
    'head': {'rotation': [0, 180, 0], 'translation': [0, 13, 7], 'scale': [1, 1, 1]},
    'fixed': {'rotation': [0, 180, 0], 'translation': [0, 0, 0], 'scale': [1, 1, 1]},
    'gui': {'rotation': [0, 0, 0], 'translation': [0, 0, 0], 'scale': [1, 1, 1]},
}

def tool():
    return Model(display=HANDHELD, rotation={'angle': -45, 'axis': 'z', 'origin': [8, 8, 8]}, gui_light='front')


# obrót o 90° wokół osi y (środek 8, 8): kierunek zachodni przechodzi w północny
_FACE_90 = {'west': 'north', 'north': 'east', 'east': 'south', 'south': 'west', 'up': 'up', 'down': 'down'}

def _point_90(p):
    x, y, z = p
    return [round(16 - z, 4), y, round(x, 4)]

def rotate_y(model, quarters):
    """Obraca wszystkie elementy modelu o quarters × 90° (przód z zachodu na północ, z północy na wschód...)."""
    for _ in range(quarters % 4):
        for e in model.elements:
            a, b = _point_90(e['from']), _point_90(e['to'])
            e['from'] = [min(a[i], b[i]) for i in range(3)]
            e['to'] = [max(a[i], b[i]) for i in range(3)]
            e['faces'] = {_FACE_90[k]: v for k, v in e['faces'].items()}
            r = e.get('rotation')
            if r:
                r = dict(r, origin=_point_90(r['origin']))
                if r['axis'] == 'x':
                    r['axis'] = 'z'
                elif r['axis'] == 'z':
                    r['axis'], r['angle'] = 'x', -r['angle']
                e['rotation'] = r
    return model
