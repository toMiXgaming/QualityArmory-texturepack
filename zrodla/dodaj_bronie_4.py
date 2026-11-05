#!/usr/bin/env python3
"""Dopisuje ASVAL, PPSh-41, Glock i RPG-7 (gen.py, build/) do gotowych paczek, bez pełnej przebudowy.
Modele qualityarmory:gun/{asval,ppsh41,rpg} podmieniają oryginały (custom_model_data 58, 54, 9 bez zmian),
Glock (QualityArmory nie ma jego modelu) dostaje nowy wpis w crossbow.json: custom_model_data 86.
Sprawdza modele tą samą walidacją co build_pack.py. build_pack.py robi to samo przy pełnej przebudowie."""
import hashlib, json, os, sys, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen import NEW_GUNS, SKINS
from build_pack import validate

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
NAZWY = ['asval', 'ppsh41', 'glock', 'rpg']
ZIPS = ['QualityArmory-21-axon.zip', 'QualityArmory-21-axon-1.21.11.zip', 'QualityArmory-21-axon-1.21.11-shadery.zip']
ITEMS = 'assets/minecraft/items/crossbow.json'


def pliki():
    files = {}
    for n in NAZWY:
        mj = open(os.path.join(HERE, 'build', n + '.json'), 'rb').read()
        png = open(os.path.join(HERE, 'build', n + '.png'), 'rb').read()
        need = list(json.load(open(os.path.join(HERE, 'display_qa.json')))[n].keys())
        errs, _ = validate(mj, png, n, set(need) | {'firstperson_lefthand'})
        if errs:
            raise SystemExit('%s: %s' % (n, errs))
        files['assets/qualityarmory/models/gun/%s.json' % n] = mj
        files['assets/qualityarmory/textures/axon/%s.png' % n] = png
    for n, (base, _, cmd, _) in SKINS.items():     # skiny premium nowych broni (7 motywów każda)
        if base in NAZWY:
            errs, _ = validate(open(os.path.join(HERE, 'build', n + '.json'), 'rb').read(),
                               open(os.path.join(HERE, 'build', n + '.png'), 'rb').read(), n,
                               set(json.load(open(os.path.join(HERE, 'display_qa.json')))[base]) | {'firstperson_lefthand'})
            if errs:
                raise SystemExit('%s: %s' % (n, errs))
            for fn in ('assets/qualityarmory/models/gun/%s.json', 'assets/qualityarmory/textures/axon/%s.png'):
                files[fn % n] = open(os.path.join(HERE, 'build', fn.split('/')[-1] % n), 'rb').read()
    return files


def main():
    files = pliki()
    for zn in ZIPS:
        path = os.path.join(ROOT, zn)
        zin = zipfile.ZipFile(path)
        items = json.loads(zin.read(ITEMS))
        ent = items['model']['entries']
        for n, (base, _, cmd, _) in SKINS.items():
            if base in NAZWY:
                NEW_GUNS[n] = cmd
        for n, cmd in NEW_GUNS.items():
            ref = 'qualityarmory:gun/' + n
            if any(e['threshold'] == cmd and e['model'].get('model') != ref for e in ent):
                raise SystemExit('custom_model_data %d zajęty' % cmd)
            ent[:] = [e for e in ent if e['threshold'] != cmd] + [{'threshold': cmd, 'model': {'type': 'model', 'model': ref}}]
        ent.sort(key=lambda e: e['threshold'])
        new = dict(files)
        new[ITEMS] = json.dumps(items, indent=2).encode()
        entries = [(i, zin.read(i.filename)) for i in zin.infolist() if i.filename not in new]
        zin.close()
        with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as zout:
            for info, data in entries:
                zout.writestr(info, data)
            for fn, data in sorted(new.items()):
                zi = zipfile.ZipInfo(fn, date_time=(2026, 11, 5, 0, 0, 0))
                zi.compress_type = zipfile.ZIP_DEFLATED
                zi.external_attr = 0o644 << 16
                zout.writestr(zi, data)
        print(zn, hashlib.sha1(open(path, 'rb').read()).hexdigest())
    for n in NAZWY + [k for k, v in SKINS.items() if v[0] in NAZWY]:
        for ext in ('.json', '.png') + (('.meta.json',) if n in NAZWY else ()):
            open(os.path.join(ROOT, 'modele', n + ext), 'wb').write(open(os.path.join(HERE, 'build', n + ext), 'rb').read())


if __name__ == '__main__':
    main()
