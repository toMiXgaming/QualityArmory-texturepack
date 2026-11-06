#!/usr/bin/env python3
"""Podmienia modele i tekstury beczek i skrzyń AxonCore (gen_pojemniki.py) w trzech zipach paczki, nic poza nimi nie ruszając.
Użycie: python3 podmien_pojemniki.py [zip ...]"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from podmien_przedmioty import patch, DEFAULT, ROOT
from gen_pojemniki import pliki


def main():
    paths = sys.argv[1:] or [os.path.join(ROOT, n) for n in DEFAULT]
    new = pliki()
    from sprawdz_paczke import main as sprawdz
    for p in paths:
        print(os.path.basename(p), 'plików:', patch(p, new))
    return sprawdz(paths)


if __name__ == '__main__':
    sys.exit(main())
