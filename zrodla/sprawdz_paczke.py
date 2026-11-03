#!/usr/bin/env python3
"""Sprawdza gotowy zip paczki (python3 sprawdz_paczke.py plik.zip ...), kod wyjścia 1 przy błędach.
Wywoływany na końcu build_pack.py i buduj_1_21_11.py, żeby przebudowa nigdy nie zgubiła broni ani tekstur:
- każdy model z items/ (i z nakładki axon_1_21_0) istnieje, ma parenta i tekstury (po rozwiązaniu #kluczy),
- każdy plik items/*.json ma klucz "model",
- każda broń z GUNS i każdy skin z SKINS ma model, teksturę i wpis custom_model_data na kuszy,
- numery 1-85 z QualityArmory na kuszy wskazują na swoje modele (nie na model sąsiada)."""
import json, os, re, sys, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))


def sprawdz(path):
    z = zipfile.ZipFile(path); names = set(z.namelist())
    def rl(r): return r.split(':', 1) if ':' in r else ['minecraft', r]
    def mpath(r): ns, p = rl(r); return 'assets/%s/models/%s.json' % (ns, p)
    def walk(o, out):
        if isinstance(o, dict):
            if isinstance(o.get('model'), str): out.add(o['model'])
            for v in o.values(): walk(v, out)
        elif isinstance(o, list):
            for v in o: walk(v, out)
    bad = []
    roots = set()

    for n in names:
        if re.match(r'(axon_1_21_0/)?assets/[^/]+/items/.*\.json$',n):
            walk(json.loads(z.read(n)),roots)
    for n in names:   # legacy overlay overrides
        if n.startswith('axon_1_21_0/') and '/models/item/' in n:
            d=json.loads(z.read(n))
            for o in d.get('overrides',[]): roots.add(o['model'])
            if d.get('parent'): roots.add(d['parent'])
    def resolve(r):
        ns,p=rl(r); n=mpath(r)
        if n not in names:
            if ns=='minecraft': return None  # vanilla model, assume ok
            bad.append(('brak modelu',r)); return None
        d=json.loads(z.read(n)); t=dict(d.get('textures') or {}); els=d.get('elements')
        par=d.get('parent')
        if par and not par.startswith('builtin/') and par not in ('minecraft:builtin/generated',):
            pr=resolve(par)
            if pr: pt,pe=pr; pt.update(t); t=pt; els=els or pe
        return t,els
    checked=0
    for r in sorted(roots):
        res=resolve(r)
        if not res: continue
        t,els=res; checked+=1
        used=set()
        for e in els or []:
            for fn,f in e['faces'].items(): used.add(f['texture'])
        for k in list(used)+[v for k,v in t.items() if k=='particle']:
            x=k; seen=set()
            while x.startswith('#'):
                if x[1:] in seen or x[1:] not in t: bad.append(('nierozwiazana tekstura',r,k)); x=None; break
                seen.add(x[1:]); x=t[x[1:]]
            if x:
                ns,p=rl(x)
                if ns!='minecraft' and f'assets/{ns}/textures/{p}.png' not in names: bad.append(('brak tekstury',r,x))
        for k,v in t.items():
            if not v.startswith('#') and rl(v)[0]!='minecraft' and f'assets/{rl(v)[0]}/textures/{rl(v)[1]}.png' not in names: bad.append(('brak tekstury',r,v))

    for n in sorted(names):
        if re.match(r'assets/[^/]+/items/.*\.json$', n) and 'model' not in json.loads(z.read(n)):
            bad.append(('items/ bez klucza model', n))
    sys.path.insert(0, HERE)
    from gen import SKINS
    cb = json.loads(z.read('assets/minecraft/items/crossbow.json'))['model']['entries']
    thr = {e['threshold']: e['model']['model'] for e in cb}
    guns = ['ak47', 'm4a1s', 'remmington', 'makarov', 'awp', 'mac10', 'm16', 'sks', 'deagle', 'sw1911', 'p30',
            'mp5', 'uzi', 'sg553', 'famas', 'dragunov', 'kar98k', 'spas'] + list(SKINS)
    for g in guns:
        for f in ('assets/qualityarmory/models/gun/%s.json' % g, 'assets/qualityarmory/textures/axon/%s.png' % g):
            if f not in names: bad.append(('brak pliku broni', f))
    for g, (base, _, cmd, _) in SKINS.items():
        if thr.get(cmd) != 'qualityarmory:gun/' + g: bad.append(('skin bez wpisu na kuszy', g, cmd, thr.get(cmd)))
    for cmd, m in thr.items():   # numer QA nie może wskazywać na model innej broni niż w README (1-85 = własne nazwy QA)
        if cmd > 85: continue
    for cmd, g in {4: 'ak47', 7: 'remmington', 25: 'm4a1s', 53: 'makarov', 20: 'awp', 48: 'mac10', 6: 'm16', 51: 'sks',
                   78: 'deagle', 11: 'sw1911', 1: 'p30', 3: 'mp5', 49: 'uzi', 27: 'sg553', 64: 'famas',
                   16: 'dragunov', 60: 'kar98k', 17: 'spas'}.items():
        if thr.get(cmd) != 'qualityarmory:gun/' + g: bad.append(('zły model broni', cmd, g, thr.get(cmd)))
    if len(set(thr)) != len(cb): bad.append(('powtórzone custom_model_data na kuszy',))
    for f in ('assets/minecraft/items/crossbow_arrow.json',):
        if f in names: bad.append(('zbędny plik', f))
    return sorted(set(bad), key=str), checked


def main(paths):
    code = 0
    for p in paths:
        bad, n = sprawdz(p)
        for b in bad: print('  BŁĄD', b)
        print('%s: modele %d, błędy %d' % (os.path.basename(p), n, len(bad)))
        code |= bool(bad)
    return code


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
