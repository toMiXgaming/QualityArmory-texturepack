#!/usr/bin/env python3
"""Sprawdza zip paczki: modele bloków nie mogą używać tekstur spoza atlasu bloków.

Modele nadpisujące zwykłe bloki (assets/minecraft/models/block/*.json) są rysowane z atlasu bloków. Od 1.21.9
atlas bloków czyta tylko katalog block/ (plus źródła z assets/minecraft/atlases/blocks.json), więc tekstura z item/
daje fioletowo-czarną kostkę, o ile nie ma jej na liście atlasu. Brakujący plik tekstury też jest błędem.
Użycie: python3 zrodla/sprawdz_paczke.py plik.zip [...]
"""
import json
import sys
import zipfile


def tex_refs(z, model, seen=()):
    """Tekstury z modelu i jego rodziców zapisanych w paczce (rodzice z vanilli pomijamy)."""
    d = json.loads(z.read(model))
    out = {k: v for k, v in d.get('textures', {}).items() if not v.startswith('#')}
    par = d.get('parent', '')
    ns, _, p = par.rpartition(':') if ':' in par else ('minecraft', '', par)
    ppath = 'assets/%s/models/%s.json' % (ns or 'minecraft', p)
    if ppath in z.namelist() and ppath not in seen:
        for k, v in tex_refs(z, ppath, seen + (ppath,)).items():
            out.setdefault(k, v)
    return out


def sprawdz(path):
    errs = []
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        atlas = json.loads(z.read('assets/minecraft/atlases/blocks.json'))['sources']
        singles = {s['resource'] for s in atlas if s.get('type') in ('single', 'minecraft:single')}
        dirs = [(s['source'], s.get('prefix', '')) for s in atlas if 'directory' in s.get('type', '')]
        for m in sorted(n for n in names if n.startswith('assets/minecraft/models/block/') and n.endswith('.json')):
            for key, ref in tex_refs(z, m).items():
                ns, _, p = ref.rpartition(':') if ':' in ref else ('minecraft', '', ref)
                ns = ns or 'minecraft'
                if ns == 'minecraft':
                    continue   # tekstury vanilli
                if 'assets/%s/textures/%s.png' % (ns, p) not in names:
                    errs.append('%s: brak pliku tekstury %s' % (m, ref))
                    continue
                in_atlas = p.startswith('block/') or ref in singles or any(
                    p.startswith(pre) and ('%s/%s' % (src, p[len(pre):])) for src, pre in dirs if pre)
                if not in_atlas:
                    errs.append('%s: tekstura %s nie jest w atlasie bloków (fioletowo-czarny blok)' % (m, ref))
    return sorted(set(errs))


def main(argv):
    bad = 0
    for path in argv:
        errs = sprawdz(path)
        for e in errs:
            print('%s: %s' % (path, e))
        bad += len(errs)
        if not errs:
            print('%s: OK' % path)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
