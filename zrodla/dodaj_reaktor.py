#!/usr/bin/env python3
"""Dopisuje reaktor AxonPlot (gen_reactor.py -> build/reactor albo modele/reactor) do gotowego
QualityArmory-21-axon.zip, bez przebudowy całej paczki. Stare pliki reaktora są zastępowane.
build_pack.py robi to samo przy pełnej przebudowie."""
import hashlib, os, sys, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ZIP = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', 'QualityArmory-21-axon.zip')


def reactor_files():
    src = os.path.join(HERE, 'build', 'reactor')
    if not os.path.isdir(src):
        src = os.path.join(HERE, '..', 'modele', 'reactor')
    files = {}
    for root, _, names in os.walk(src):
        for n in names:
            p = os.path.join(root, n)
            files[os.path.relpath(p, src).replace(os.sep, '/')] = open(p, 'rb').read()
    return files


def main():
    files = reactor_files()
    zin = zipfile.ZipFile(ZIP)
    entries = [(i, zin.read(i.filename)) for i in zin.infolist()
               if i.filename not in files and not i.filename.startswith(('assets/axon/models/block/reactor/',
                                                                   'assets/axon/textures/block/reactor/'))]
    zin.close()
    with zipfile.ZipFile(ZIP, 'w', zipfile.ZIP_DEFLATED) as zout:
        for info, data in entries:
            zout.writestr(info, data)
        for fn, data in sorted(files.items()):
            zi = zipfile.ZipInfo(fn, date_time=(2026, 10, 19, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            zout.writestr(zi, data)
    print('reaktor:', len(files), 'plików, sha1', hashlib.sha1(open(ZIP, 'rb').read()).hexdigest())


if __name__ == '__main__':
    main()
