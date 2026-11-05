#!/usr/bin/env python3
"""Dopisuje do zipów assets/minecraft/items/barrier.json: numer custom_model_data -> model axon:<nazwa>.

Plugin Axon-items stawia stanowiska (warsztaty, piece, recykler...) jako ItemDisplay z przedmiotem
minecraft:barrier i custom_model_data = abs(hashCode("axon:<nazwa>")) % 100000 + 1 (np. axon:warsztat_t3 -> 93667),
a nie z komponentem item_model. Bez tej definicji gra nie ma modelu dla takiego przedmiotu i rysuje
fioletowo-czarną kostkę. Wpis jest dla każdego axon:<nazwa> z assets/axon/items/, którego model używa tylko tekstur z item/
(jedna definicja przedmiotu nie może mieszać atlasów, inaczej klient 1.21.11 odrzuca całego barriera).
Użycie: python3 zrodla/dodaj_barrier.py plik.zip [...]  (buduj_1_21_11.py woła to sam).
"""
import json
import shutil
import sys
import zipfile

PATH = 'assets/minecraft/items/barrier.json'


def java_hash(s):
    h = 0
    for c in s:
        h = (31 * h + ord(c)) & 0xffffffff
    return h - (1 << 32) if h >= (1 << 31) else h


def cmd_for(name):
    return abs(java_hash('axon:' + name)) % 100000 + 1


def definicja(names):
    by_cmd = {}
    for n in sorted(names):
        c = cmd_for(n)
        if c in by_cmd:
            raise SystemExit('kolizja custom_model_data %d: %s i %s' % (c, by_cmd[c], n))
        by_cmd[c] = n
    entries = [{'threshold': c, 'model': {'type': 'minecraft:model', 'model': 'axon:block/' + n}}
               for c, n in sorted(by_cmd.items())]
    # wartości między wpisami nie mogą łapać cudzego modelu: przed każdym wpisem i za nim wraca zwykła bariera
    out = []
    for e in entries:
        out.append({'threshold': e['threshold'] - 0.5, 'model': {'type': 'minecraft:model', 'model': 'minecraft:item/barrier'}})
        out.append(e)
        out.append({'threshold': e['threshold'] + 0.5, 'model': {'type': 'minecraft:model', 'model': 'minecraft:item/barrier'}})
    out.sort(key=lambda e: e['threshold'])
    return {'model': {'type': 'minecraft:range_dispatch', 'property': 'minecraft:custom_model_data', 'index': 0,
                      'fallback': {'type': 'minecraft:model', 'model': 'minecraft:item/barrier'}, 'entries': out}}


def patch(path):
    with zipfile.ZipFile(path) as z:
        names = []
        for n in z.namelist():
            if not (n.startswith('assets/axon/items/') and n.endswith('.json')):
                continue
            name = n[len('assets/axon/items/'):-5]
            mp = 'assets/axon/models/block/%s.json' % name
            if mp not in z.namelist():
                continue
            tex = [v for v in (json.loads(z.read(mp)).get('textures') or {}).values() if not v.startswith('#')]
            # jedna definicja przedmiotu może używać tylko jednego atlasu: bierzemy modele z samym item/
            if tex and all(v.split(':', 1)[-1].startswith('item/') for v in tex):
                names.append(name)
    data = (json.dumps(definicja(names), indent=2) + '\n').encode()
    tmp = path + '.tmp'
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
        for i in zin.infolist():
            if i.filename != PATH:
                zout.writestr(i, zin.read(i.filename))
        zout.writestr(PATH, data)
    shutil.move(tmp, path)
    return len(names)


if __name__ == '__main__':
    for p in sys.argv[1:]:
        print(p, patch(p), 'modeli')
