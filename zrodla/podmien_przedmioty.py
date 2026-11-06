#!/usr/bin/env python3
"""Podmienia (lub dopisuje) modele i tekstury przedmiotów qualityarmory:misc/* w gotowych zipach paczki
modelami z zrodla/build/ (wynik `python3 gen_przedmioty.py`). Użycie: python3 podmien_przedmioty.py [zip ...]"""
import os, shutil, sys, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from gen_przedmioty import NAMES, OUT

DEFAULT = ['QualityArmory-21-axon.zip', 'QualityArmory-21-axon-1.21.11.zip', 'QualityArmory-21-axon-1.21.11-shadery.zip']
MODEL = 'assets/qualityarmory/models/misc/%s.json'
TEX = 'assets/qualityarmory/textures/axon/misc_%s.png'


def pliki():
    f = {}
    for n in NAMES:
        f[MODEL % n] = open(os.path.join(OUT, 'misc_%s.json' % n), 'rb').read()
        f[TEX % n] = open(os.path.join(OUT, 'misc_%s.png' % n), 'rb').read()
    return f


def patch(path, new):
    tmp = path + '.tmp'
    seen = set()
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
        for info in zin.infolist():
            if info.filename in new:
                zout.writestr(info, new[info.filename])
                seen.add(info.filename)
            else:
                zout.writestr(info, zin.read(info.filename))
        for k in sorted(set(new) - seen):
            zout.writestr(k, new[k])
    os.replace(tmp, path)
    return len(new)


def main():
    paths = sys.argv[1:] or [os.path.join(ROOT, n) for n in DEFAULT]
    new = pliki()
    from sprawdz_paczke import main as sprawdz
    for p in paths:
        print(os.path.basename(p), 'plików:', patch(p, new))
    return sprawdz(paths)


if __name__ == '__main__':
    sys.exit(main())
