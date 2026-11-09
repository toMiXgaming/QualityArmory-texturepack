#!/usr/bin/env python3
"""Dopisuje Surową Siarkę (axoncore/siarka.py: ruda siarki zamiast rudy miedzi, ikona grudki siarki dla
żółtego barwnika z custom_model_data 10001) do gotowych zipów, bez przebudowy całej paczki.
Stare pliki o tych samych ścieżkach są zastępowane. build_pack.py (przez gen_axoncore.pliki()) robi to samo
przy pełnej przebudowie.

Bez argumentów łata QualityArmory-21-axon.zip, jego kopię -1.21.11.zip i QualityArmory-21-axon-1.21.11-shadery.zip
(ta ostatnia nie ma nakładki axon_1_21_0, więc dostaje tylko pliki z assets/)."""
import hashlib, os, sys, zipfile

from axoncore.siarka import pliki

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ZIPS = ['QualityArmory-21-axon.zip', 'QualityArmory-21-axon-1.21.11.zip', 'QualityArmory-21-axon-1.21.11-shadery.zip']


def patch(path, files):
    zin = zipfile.ZipFile(path)
    names = set(zin.namelist())
    if not any(n.startswith('axon_1_21_0/') for n in names):
        files = {k: v for k, v in files.items() if not k.startswith('axon_1_21_0/')}
    entries = [(i, zin.read(i.filename)) for i in zin.infolist() if i.filename not in files]
    zin.close()
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as zout:
        for info, data in entries:
            zout.writestr(info, data)
        for fn, data in sorted(files.items()):
            zi = zipfile.ZipInfo(fn, date_time=(2026, 11, 9, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            zout.writestr(zi, data)
    print('siarka: %s, %d plików, sha1 %s' % (os.path.basename(path), len(files),
                                             hashlib.sha1(open(path, 'rb').read()).hexdigest()))


def main():
    files = pliki()
    paths = sys.argv[1:] or [os.path.join(ROOT, z) for z in ZIPS]
    for p in paths:
        patch(p, dict(files))
    from sprawdz_paczke import main as sprawdz
    if sprawdz(paths):
        raise SystemExit('paczka nie przeszła sprawdz_paczke.py')


if __name__ == '__main__':
    main()
