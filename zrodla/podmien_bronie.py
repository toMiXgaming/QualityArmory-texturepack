#!/usr/bin/env python3
"""Podmienia modele i tekstury WSZYSTKICH broni (i ich skinów) w gotowych zipach paczki
modelami z zrodla/build/ (wynik `python3 gen.py`), nic poza nimi nie ruszając.

Użycie:  python3 zrodla/podmien_bronie.py [zip ...]
Bez argumentów: trzy zipy w katalogu głównym repo. Każdy model przechodzi walidację z build_pack.py
(zakres współrzędnych, obroty, UV, tekstury, transformacje display), a po zapisie zip sprawdza
sprawdz_paczke.py. Zip jest zapisywany do pliku tymczasowego i podmieniany dopiero po sukcesie."""
import json, os, shutil, sys, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from build_pack import GUNS, validate
from gen import SKINS

DEFAULT = ['QualityArmory-21-axon.zip', 'QualityArmory-21-axon-1.21.11.zip', 'QualityArmory-21-axon-1.21.11-shadery.zip']
MODEL = 'assets/qualityarmory/models/gun/%s.json'
TEX = 'assets/qualityarmory/textures/axon/%s.png'


def load_build():
    out = {}
    for g in GUNS:
        out[g] = (open(os.path.join(HERE, 'build', g + '.json'), 'rb').read(),
                  open(os.path.join(HERE, 'build', g + '.png'), 'rb').read())
    return out


def patch(path, new):
    tmp = path + '.tmp'
    n = 0
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
        repl = {}
        for g, (mj, png) in new.items():
            qa = SKINS[g][0] if g in SKINS else g
            need = json.loads(zin.read(MODEL % qa)).get('display', {}).keys()
            errs, cnt = validate(mj, png, g, set(need) | {'firstperson_lefthand'})
            if errs:
                raise SystemExit('%s: %s' % (g, errs))
            repl[MODEL % g] = mj
            repl[TEX % g] = png
        seen = set()
        for info in zin.infolist():
            if info.filename in repl:
                zout.writestr(info, repl[info.filename])
                seen.add(info.filename)
                n += 1
            else:
                zout.writestr(info, zin.read(info.filename))
        missing = set(repl) - seen
        if missing:
            raise SystemExit('%s: brak w zipie %s' % (path, sorted(missing)[:3]))
    os.replace(tmp, path)
    return n


def main():
    paths = sys.argv[1:] or [os.path.join(ROOT, n) for n in DEFAULT]
    new = load_build()
    from sprawdz_paczke import main as sprawdz
    for p in paths:
        print(os.path.basename(p), 'podmieniono plików:', patch(p, new))
    return sprawdz(paths)


if __name__ == '__main__':
    sys.exit(main())
