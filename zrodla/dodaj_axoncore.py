#!/usr/bin/env python3
"""Dopisuje modele AxonCore (gen_axoncore.py) do gotowego QualityArmory-21-axon.zip i jego kopii
QualityArmory-21-axon-1.21.11.zip, bez przebudowy całej paczki. Stare pliki tych modeli są zastępowane.
Dodaje też modele dla item_model na 1.21.2-1.21.3 (nakładka axon_1_21_0), jak legacy_models() w build_pack.py,
które przy pełnej przebudowie robi to samo."""
import hashlib, json, os, shutil, sys, zipfile

from gen_axoncore import NAZWY, pliki, sprawdz

HERE = os.path.dirname(os.path.abspath(__file__))
ZIP = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', 'QualityArmory-21-axon.zip')
KOPIA = os.path.join(HERE, '..', 'QualityArmory-21-axon-1.21.11.zip')


def main():
    files = pliki()
    errs = sprawdz(files)
    if errs:
        raise SystemExit('\n'.join(errs))
    for name in NAZWY:
        files['axon_1_21_0/assets/axon/models/item/%s.json' % name] = json.dumps(
            {'parent': 'axon:block/' + name}, indent=2).encode()
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
    if len(sys.argv) <= 1:   # kopia zostawiona dla starych linków (README)
        shutil.copyfile(ZIP, KOPIA)
    print('axoncore: %d plików, sha1' % len(files), hashlib.sha1(open(ZIP, 'rb').read()).hexdigest())


if __name__ == '__main__':
    main()
