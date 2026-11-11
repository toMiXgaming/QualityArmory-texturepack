#!/usr/bin/env python3
"""Dopisuje płaskie warstwy pancerza z gen_warstwy.py (equipment axon:<zestaw> + tekstury humanoid/leggings)
do gotowych zipów paczki, bez przebudowy całości. build_pack.py robi to samo przy pełnej przebudowie.
Bez argumentów obrabia wszystkie trzy zipy z katalogu głównego repo."""
import hashlib, os, sys, zipfile
from gen_warstwy import pliki

HERE = os.path.dirname(os.path.abspath(__file__))
ZIPS = ['QualityArmory-21-axon.zip', 'QualityArmory-21-axon-1.21.11.zip', 'QualityArmory-21-axon-1.21.11-shadery.zip']


def dodaj(path, files):
    zin = zipfile.ZipFile(path)
    entries = [(i, zin.read(i.filename)) for i in zin.infolist() if i.filename not in files]
    zin.close()
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as zout:
        for info, data in entries:
            zout.writestr(info, data)
        for fn, data in sorted(files.items()):
            zi = zipfile.ZipInfo(fn, date_time=(2026, 11, 11, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            zout.writestr(zi, data)
    print(os.path.basename(path), len(files), 'plików, sha1', hashlib.sha1(open(path, 'rb').read()).hexdigest())


def main():
    files = pliki()
    paths = sys.argv[1:] or [os.path.join(HERE, '..', z) for z in ZIPS]
    for p in paths:
        dodaj(p, files)


if __name__ == '__main__':
    main()
