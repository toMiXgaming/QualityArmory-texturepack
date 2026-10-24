#!/usr/bin/env python3
"""Dopisuje lokomotywę (gen_lokomotywa.py -> build/) do gotowego QualityArmory-21-axon.zip, bez przebudowy
całej paczki. Stare pliki lokomotywy są zastępowane. build_pack.py robi to samo przy pełnej przebudowie."""
import hashlib, os, sys, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ZIP = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', 'QualityArmory-21-axon.zip')
NAME = 'lokomotywa'


def main():
    build = os.path.join(HERE, 'build')
    files = {'assets/axon/models/block/%s.json' % NAME: open(os.path.join(build, NAME + '.json'), 'rb').read(),
             'assets/axon/textures/item/%s.png' % NAME: open(os.path.join(build, NAME + '.png'), 'rb').read(),
             'assets/axon/items/%s.json' % NAME: open(os.path.join(build, NAME + '_item.json'), 'rb').read()}
    zin = zipfile.ZipFile(ZIP)
    entries = [(i, zin.read(i.filename)) for i in zin.infolist() if i.filename not in files]
    zin.close()
    with zipfile.ZipFile(ZIP, 'w', zipfile.ZIP_DEFLATED) as zout:
        for info, data in entries:
            zout.writestr(info, data)
        for fn, data in sorted(files.items()):
            zi = zipfile.ZipInfo(fn, date_time=(2026, 10, 24, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            zout.writestr(zi, data)
    print('lokomotywa: sha1', hashlib.sha1(open(ZIP, 'rb').read()).hexdigest())


if __name__ == '__main__':
    main()
