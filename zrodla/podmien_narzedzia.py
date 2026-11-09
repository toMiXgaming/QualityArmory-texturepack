#!/usr/bin/env python3
"""Wstawia nowe modele i tekstury narzędzi (vanilla drewniane/kamienne, steel_*, hardened_*) oraz broni białych
z zrodla/build/ (wynik `python3 gen_narzedzia.py`) do gotowych zipów, nic innego nie ruszając.
Użycie: python3 zrodla/podmien_narzedzia.py [zip ...]   (bez argumentów: trzy zipy w katalogu głównym repo).
Modele przechodzą te same granice co w build_pack.py, a po zapisie zip sprawdza sprawdz_paczke.py."""
import json, os, sys, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import gen_narzedzia

DEFAULT = ['QualityArmory-21-axon.zip', 'QualityArmory-21-axon-1.21.11.zip', 'QualityArmory-21-axon-1.21.11-shadery.zip']


def sprawdz_modele(files):
    errs = []
    for fn, data in files.items():
        if not fn.endswith('.json'):
            continue
        for e in json.loads(data).get('elements', []):
            if any(not -16 <= c <= 32 for c in e['from'] + e['to']):
                errs.append('%s: element poza -16..32' % fn)
            r = e.get('rotation')
            if r and r['angle'] not in (-45, -22.5, 0, 22.5, 45):
                errs.append('%s: obrót %s' % (fn, r['angle']))
            if any(not 0 <= u <= 16 for f in e['faces'].values() for u in f['uv']):
                errs.append('%s: uv poza 0..16' % fn)
    return errs


# żelazne narzędzia wracają do vanilla: usuwamy nadpisane modele i tekstury
USUN = ['assets/minecraft/models/item/iron_%s.json' % k for k in ('axe', 'pickaxe', 'shovel', 'hoe')] + \
       ['assets/axon/textures/item/narz_iron_%s.png' % k for k in ('axe', 'pickaxe', 'shovel', 'hoe')]


def patch(path, files):
    tmp = path + '.tmp'
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
        have = set(zin.namelist())
        for info in zin.infolist():
            if info.filename in USUN:
                continue
            if info.filename in files:
                zout.writestr(info, files[info.filename])
            else:
                zout.writestr(info, zin.read(info.filename))
        for fn, data in sorted(files.items()):          # nowe pliki (np. tekstury narz_*.png)
            if fn not in have:
                zi = zipfile.ZipInfo(fn, date_time=(2026, 10, 29, 0, 0, 0))
                zi.compress_type = zipfile.ZIP_DEFLATED
                zi.external_attr = 0o644 << 16
                zout.writestr(zi, data)
    os.replace(tmp, path)
    return len(files)


def main():
    paths = sys.argv[1:] or [os.path.join(ROOT, n) for n in DEFAULT]
    files = gen_narzedzia.pliki()
    errs = sprawdz_modele(files)
    if errs:
        raise SystemExit('\n'.join(errs[:10]))
    for p in paths:
        print(os.path.basename(p), 'plików:', patch(p, files))
    from sprawdz_paczke import main as sprawdz
    return sprawdz(paths)


if __name__ == '__main__':
    sys.exit(main())
