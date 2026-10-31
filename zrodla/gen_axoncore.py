#!/usr/bin/env python3
"""Modele i tekstury AxonCore (styl PRL) z pakietu axoncore/: ikony przedmiotów Axon-items, narzędzia 3D,
podmienione bloki vanilla (stół rzemieślniczy, piec, ognisko, beczka, skrzynia), stanowiska craftingu,
pojemniki z łupem i wraki pojazdów.

Wszystkie modele 3D używają jednego atlasu materiałów 64×64 (axon:block/axoncore_atlas, kafelki 8×8).
Przedmioty mają postać axon:<nazwa> (komponent item_model), model axon:block/<nazwa>, tak jak meble.
`pliki()` zwraca {ścieżka w zipie: bajty}; build_pack.py i dodaj_axoncore.py dopisują je do paczki,
a `python3 gen_axoncore.py` zapisuje je też do ../modele/axoncore/ i wypisuje skale wraków."""
import io, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from axoncore.atlas import ATLAS
from axoncore.model import rotate_y
from axoncore.items import ITEMS
from axoncore.tools import T
from axoncore.blocks import B
from axoncore.chest import TEX as CHEST
from axoncore.stations import S
from axoncore.containers import C
from axoncore.vehicles import V
from axoncore.barrels import TEX as BARREL_TEX
from axoncore.crates import TEX as CRATE_TEX

ATLAS_PNG = 'assets/axon/textures/block/axoncore_atlas.png'


def _png(img):
    buf = io.BytesIO()
    img.save(buf, 'PNG', optimize=True)
    return buf.getvalue()


def _json(data):
    return (json.dumps(data, indent=2, ensure_ascii=False) + '\n').encode()


def _przedmiot(files, name, model):
    files['assets/axon/models/block/%s.json' % name] = _json(model)
    files['assets/axon/items/%s.json' % name] = _json(
        {'model': {'type': 'minecraft:model', 'model': 'axon:block/' + name}})


def modele_3d():
    """Stanowiska i pojemniki przodem na południe (jak meble), wraki przodem na północ (jak auta)."""
    out = {}
    for group, quarters in ((S, 2), (C, 2), (V, 1)):
        for name, m in group.items():
            out[name] = rotate_y(m, quarters)
    return out


MODELE_3D = modele_3d()
IKONY = list(ITEMS)
NARZEDZIA = [k.split(':')[1] for k in T if k.startswith('axon:')]
NAZWY = IKONY + NARZEDZIA + list(MODELE_3D)   # wszystkie przedmioty axon:<nazwa> z tego pliku


def pliki():
    files = {ATLAS_PNG: _png(ATLAS)}
    for name, img in ITEMS.items():   # ikony 2D, nazwy jak w items.yml pluginu Axon-items
        files['assets/axon/textures/item/%s.png' % name] = _png(img)
        _przedmiot(files, name, {'parent': 'minecraft:item/generated', 'textures': {'layer0': 'axon:item/' + name}})
    for key, m in T.items():   # narzędzia Axon jako przedmioty, drewniane i kamienne podmieniają vanilla
        ns, name = key.split(':')
        if ns == 'axon':
            _przedmiot(files, name, m.json())
        else:
            files['assets/minecraft/models/item/%s.json' % name] = _json(m.json())
    for key, m in B.items():   # bloki vanilla podmienione u wszystkich
        ns, path = key.split(':')
        files['assets/%s/models/%s.json' % (ns, path)] = _json({'parent': 'minecraft:block/block', **m.json()})
    for key, img in CHEST.items():
        ns, path = key.split(':')
        files['assets/%s/textures/%s.png' % (ns, path)] = _png(img)
    for name, img in {**BARREL_TEX, **CRATE_TEX}.items():   # tekstury beczek i skrzyń 128×128 (barrels.py, crates.py)
        files['assets/axon/textures/item/%s.png' % name] = _png(img)
    for name, m in MODELE_3D.items():
        _przedmiot(files, name, m.json())
    return files


def sprawdz(files):
    """Te same granice co validate() w build_pack.py."""
    errs = []
    for fn, data in files.items():
        if not fn.endswith('.json') or '/models/' not in fn:
            continue
        for e in json.loads(data).get('elements', []):
            if any(not -16 <= c <= 32 for c in e['from'] + e['to']):
                errs.append('%s: element poza -16..32' % fn)
            r = e.get('rotation')
            if r and r['angle'] not in (-45, -22.5, 0, 22.5, 45):
                errs.append('%s: obrót %s' % (fn, r['angle']))
            if any(not 0 <= u <= 16 for f in e['faces'].values() for u in f['uv']):
                errs.append('%s: uv poza 0..16' % fn)
    return errs


def main():
    files = pliki()
    errs = sprawdz(files)
    if errs:
        raise SystemExit('\n'.join(errs))
    out = os.path.join(HERE, '..', 'modele', 'axoncore')
    for fn, data in files.items():
        path = os.path.join(out, fn)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, 'wb').write(data)
    print('axoncore: %d plików, %d przedmiotów axon:<nazwa>' % (len(files), len(NAZWY)))
    for name in V:
        print('  %-18s skala %s, środek modelu %.2f kratki nad gruntem' % (name, V[name].scale, V[name].scale / 2))


if __name__ == '__main__':
    main()
