#!/usr/bin/env python3
"""Dopisuje do atlases/blocks.json teksturę z item/ (i innych katalogów poza block/) użytą przez model zwykłego bloku.

Modele nadpisujące bloki z Minecrafta (assets/minecraft/models/block/*.json: beczka, stół rzemieślniczy, piec,
ognisko) są rysowane z atlasu bloków. Od 1.21.9 ten atlas czyta tylko katalog block/ (i źródła z blocks.json),
więc tekstura z item/ daje fioletowo-czarny blok. Skrypt dopisuje każdą taką teksturę jako źródło `single`.
Użycie: python3 zrodla/atlas_bloku.py plik.zip [...]  (build_pack.py i buduj_1_21_11.py wołają to same).
"""
import json
import re
import shutil
import sys
import zipfile

ATLAS = 'assets/minecraft/atlases/blocks.json'


def patch(path):
    with zipfile.ZipFile(path) as z:
        atlas = json.loads(z.read(ATLAS))
        have = {s.get('resource') for s in atlas['sources'] if 'single' in s.get('type', '')}
        prefixes = [s['prefix'] for s in atlas['sources'] if 'directory' in s.get('type', '') and s.get('prefix')]
        add = []
        for n in sorted(z.namelist()):
            if re.match(r'assets/minecraft/models/block/[^/]+\.json$', n):
                for r in json.loads(z.read(n)).get('textures', {}).values():
                    if r.startswith('#') or ':' not in r or r.startswith('minecraft:'):
                        continue
                    p = r.split(':', 1)[1]
                    if not p.startswith('block/') and r not in have and r not in add and not any(p.startswith(x) for x in prefixes):
                        add.append(r)
        if not add:
            return 0
        atlas['sources'] += [{'type': 'single', 'resource': r} for r in add]
        data = json.dumps(atlas, indent=4).encode()
        tmp = path + '.tmp'
        with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
            for i in z.infolist():
                zout.writestr(i, data if i.filename == ATLAS else z.read(i.filename))
    shutil.move(tmp, path)
    return len(add)


if __name__ == '__main__':
    for p in sys.argv[1:]:
        print(p, patch(p), 'tekstur dopisanych')
