#!/usr/bin/env python3
"""Dopisuje pancerze z gen_pancerze.py (build/ albo modele/) do gotowego QualityArmory-21-axon.zip, bez przebudowy
całej paczki. Stare pliki tych mebli są zastępowane. build_pack.py robi to samo przy pełnej przebudowie."""
import hashlib, json, os, sys, zipfile
from gen_pancerze import PANCERZE

HERE = os.path.dirname(os.path.abspath(__file__))
ZIP = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', 'QualityArmory-21-axon.zip')


def pancerze_files():
    files = {}
    for name in PANCERZE:
        src = os.path.join(HERE, 'build')
        if not os.path.exists(os.path.join(src, name + '.json')):
            src = os.path.join(HERE, '..', 'modele')
        files['assets/axon/models/block/%s.json' % name] = open(os.path.join(src, name + '.json'), 'rb').read()
        files['assets/axon/textures/item/%s.png' % name] = open(os.path.join(src, name + '.png'), 'rb').read()
        files['assets/axon/items/%s.json' % name] = json.dumps(
            {'model': {'type': 'minecraft:model', 'model': 'axon:block/' + name}}, indent=1).encode()
        files['axon_1_21_0/assets/axon/models/item/%s.json' % name] = json.dumps(
            {'parent': 'axon:block/' + name}, indent=2).encode()   # 1.21.2-1.21.3: item_model
    return files


def main():
    files = pancerze_files()
    zin = zipfile.ZipFile(ZIP)
    entries = [(i, zin.read(i.filename)) for i in zin.infolist() if i.filename not in files]
    zin.close()
    with zipfile.ZipFile(ZIP, 'w', zipfile.ZIP_DEFLATED) as zout:
        for info, data in entries:
            zout.writestr(info, data)
        for fn, data in sorted(files.items()):
            zi = zipfile.ZipInfo(fn, date_time=(2026, 10, 29, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            zout.writestr(zi, data)
    print('pancerze:', len(files), 'plików, sha1', hashlib.sha1(open(ZIP, 'rb').read()).hexdigest())


if __name__ == '__main__':
    main()
