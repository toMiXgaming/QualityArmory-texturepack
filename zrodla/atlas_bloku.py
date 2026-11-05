#!/usr/bin/env python3
"""Naprawia atlasy tekstur w zipie pod klienta 1.21.9+, gdzie atlas bloków i atlas przedmiotów są osobne.

W 1.21.11 tekstura z katalogu item/ trafia tylko do atlasu przedmiotów, a z block/ tylko do atlasu bloków,
i obowiązują dwie reguły (klient loguje je jako „Rejecting block model ... outside of supported atlas” i
„Multiple atlases used in model”):
- model nadpisujący zwykły blok (assets/minecraft/models/block/*.json) może używać tylko tekstur z block/,
- jeden model przedmiotu nie może mieszać tekstur z block/ i z item/.
Skrypt (1) kopiuje tekstury z item/ użyte przez modele zwykłych bloków do textures/block/vanilla/ i przepisuje
te modele, (2) w modelach axon mieszających oba atlasy zamienia axon:block/axoncore_atlas na kopię
axon:item/axoncore_atlas, (3) usuwa z atlases/blocks.json wpisy `single` dodane wcześniej jako obejście.
Użycie: python3 zrodla/atlas_bloku.py plik.zip [...]  (build_pack.py i buduj_1_21_11.py wołają to same).
"""
import json
import re
import shutil
import sys
import zipfile

ATLAS = 'assets/minecraft/atlases/blocks.json'
SHARED = ('axon', 'block/axoncore_atlas', 'item/axoncore_atlas')


def kind(ref):
    p = ref.split(':', 1)[1] if ':' in ref else ref
    return p.split('/')[0]


def patch(path):
    with zipfile.ZipFile(path) as z:
        files = {n: z.read(n) for n in z.namelist()}
        infos = {i.filename: i for i in z.infolist()}
    changed = 0
    for n in sorted(files):
        m = re.match(r'assets/minecraft/models/block/[^/]+\.json$', n)
        if not m:
            continue
        d = json.loads(files[n])
        mod = False
        for k, r in list((d.get('textures') or {}).items()):
            if r.startswith('#') or ':' not in r or r.startswith('minecraft:'):
                continue
            ns, p = r.split(':', 1)
            if p.split('/')[0] == 'block':
                continue
            new = 'block/vanilla/' + p.split('/')[-1]
            for ext in ('.png', '.png.mcmeta'):
                src = 'assets/%s/textures/%s%s' % (ns, p, ext)
                if src in files:
                    files['assets/%s/textures/%s%s' % (ns, new, ext)] = files[src]
            d['textures'][k] = '%s:%s' % (ns, new)
            mod = True
        if mod:
            files[n] = json.dumps(d, indent=2).encode()
            changed += 1
    for n in sorted(files):
        if not re.match(r'assets/axon/models/block/.*\.json$', n):
            continue
        d = json.loads(files[n])
        kinds = {kind(r) for r in (d.get('textures') or {}).values() if not r.startswith('#')}
        if {'block', 'item'} <= kinds:
            ns, a, b = SHARED
            for k, r in d['textures'].items():
                if r == '%s:%s' % (ns, a):
                    d['textures'][k] = '%s:%s' % (ns, b)
            files['assets/axon/textures/item/axoncore_atlas.png'] = files['assets/axon/textures/block/axoncore_atlas.png']
            files[n] = json.dumps(d, indent=2).encode()
            changed += 1
    atlas = json.loads(files[ATLAS])
    keep = [s for s in atlas['sources'] if not ('single' in s.get('type', '') and s.get('resource', '').startswith('axon:item/'))]
    if len(keep) != len(atlas['sources']):
        atlas['sources'] = keep
        files[ATLAS] = json.dumps(atlas, indent=4).encode()
        changed += 1
    if not changed:
        return 0
    tmp = path + '.tmp'
    with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
        for n, data in files.items():
            zout.writestr(infos.get(n) or n, data)
    shutil.move(tmp, path)
    return changed


if __name__ == '__main__':
    for p in sys.argv[1:]:
        print(p, patch(p), 'zmian')
