"""Dźwięki AXON w paczce (namespace axon). Pliki .ogg robi gen_dzwieki.py (synteza) i leżą w zrodla/dzwieki/.

- axon:drzewo.trzeszczenie – drzewo trzeszczy przed upadkiem (AxonMapGenerator, ścinanie drzew);
  trzy warianty, gra losuje jeden, słychać do 32 bloków.

`pliki()` zwraca {ścieżka w zipie: bajty}; woła ją gen_axoncore.pliki() (pełna przebudowa)
i dodaj_dzwieki.py (łatka gotowych zipów)."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '..', 'dzwieki')

SOUNDS = {
    'drzewo.trzeszczenie': {
        'files': ['trzeszczenie1', 'trzeszczenie2', 'trzeszczenie3'],
        'attenuation_distance': 32,
    },
}


def pliki():
    files = {}
    defs = {}
    for event, spec in SOUNDS.items():
        folder = event.split('.')[0]
        entries = []
        for name in spec['files']:
            with open(os.path.join(SRC, name + '.ogg'), 'rb') as f:
                files['assets/axon/sounds/%s/%s.ogg' % (folder, name)] = f.read()
            entries.append({'name': 'axon:%s/%s' % (folder, name),
                            'attenuation_distance': spec['attenuation_distance']})
        defs[event] = {'sounds': entries}
    files['assets/axon/sounds.json'] = (json.dumps(defs, indent=2, ensure_ascii=False) + '\n').encode()
    return files
