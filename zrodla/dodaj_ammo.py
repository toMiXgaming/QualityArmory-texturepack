#!/usr/bin/env python3
"""Dopisuje amunicję z gen_ammo.py (build/) do gotowego QualityArmory-21-axon.zip, bez przebudowy
całej paczki. Modele qualityarmory:ammo/* są podmieniane (custom_model_data 1-10 bez zmian).
build_pack.py robi to samo przy pełnej przebudowie."""
import hashlib, os, sys, zipfile
from gen_ammo import NAZWY

HERE = os.path.dirname(os.path.abspath(__file__))
ZIP = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', 'QualityArmory-21-axon.zip')


def ammo_files():
    files = {}
    for name in NAZWY:
        base = name.replace('ammo', 'ammo_', 1)
        files['assets/qualityarmory/models/ammo/%s.json' % name] = open(os.path.join(HERE, 'build', base + '.json'), 'rb').read()
        files['assets/qualityarmory/textures/axon/%s.png' % base] = open(os.path.join(HERE, 'build', base + '.png'), 'rb').read()
    return files


def main():
    files = ammo_files()
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
    print('amunicja:', len(files), 'plików, sha1', hashlib.sha1(open(ZIP, 'rb').read()).hexdigest())


if __name__ == '__main__':
    main()
