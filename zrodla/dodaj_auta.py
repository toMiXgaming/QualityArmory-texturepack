#!/usr/bin/env python3
"""Dopisuje auta i telewizor (gen_auta.py -> build/) do gotowego QualityArmory-21-axon.zip, bez przebudowy
całej paczki. Stare pliki tych modeli są zastępowane. build_pack.py robi to samo przy pełnej przebudowie."""
import hashlib, os, sys, zipfile

from gen_auta import AUTA_I_TV

HERE = os.path.dirname(os.path.abspath(__file__))
ZIP = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', 'QualityArmory-21-axon.zip')


def main():
    build = os.path.join(HERE, 'build')
    files = {}
    for name in AUTA_I_TV:
        files['assets/axon/models/block/%s.json' % name] = open(os.path.join(build, name + '.json'), 'rb').read()
        files['assets/axon/textures/item/%s.png' % name] = open(os.path.join(build, name + '.png'), 'rb').read()
        files['assets/axon/items/%s.json' % name] = open(os.path.join(build, name + '_item.json'), 'rb').read()
    zin = zipfile.ZipFile(ZIP)
    entries = [(i, zin.read(i.filename)) for i in zin.infolist() if i.filename not in files]
    zin.close()
    with zipfile.ZipFile(ZIP, 'w', zipfile.ZIP_DEFLATED) as zout:
        for info, data in entries:
            zout.writestr(info, data)
        for fn, data in sorted(files.items()):
            zi = zipfile.ZipInfo(fn, date_time=(2026, 10, 25, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            zout.writestr(zi, data)
    print('auta i telewizor: sha1', hashlib.sha1(open(ZIP, 'rb').read()).hexdigest())


if __name__ == '__main__':
    main()
