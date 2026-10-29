#!/usr/bin/env python3
"""Builds QualityArmory-21-axon.zip = full copy of QA's 1.21.4 pack (QA21.zip) with only
the AXON gun models (GUNS) replaced, the AXON textures added under
assets/qualityarmory/textures/axon/, and an 'axon' directory source added to the blocks
atlas (QA's atlas file only lists 'all/', so new texture folders must be registered).

One zip for every 1.21.x (pack.mcmeta lists formats 34-75 and the overlays):
- axon_1_21_0 (1.21-1.21.3): those versions do not read assets/*/items/, so the
  custom_model_data entries are written again as old-style "overrides" on the vanilla
  item models (legacy_1_21_0/), and axon:<name> gets a models/item/ model for item_model.
- axon_shadery (1.21.2-1.21.5) and axon_shadery_1_21_0 (1.21-1.21.1): the AxonMap core
  shaders. 1.21.6+ uses a different shader format, so there they are left out."""
import hashlib, io, json, os, sys, zipfile
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen import SKINS

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1] if len(sys.argv) > 1 else '/tmp/qa/QA21.zip'
DST = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, 'QualityArmory-21-axon.zip')
GUNS = ['ak47', 'm4a1s', 'remmington', 'makarov', 'awp', 'mac10', 'm16', 'sks',
        'deagle', 'sw1911', 'p30', 'mp5', 'uzi', 'sg553', 'famas', 'dragunov', 'kar98k', 'spas'] + list(SKINS)
ITEMS = 'assets/minecraft/items/crossbow.json'
ATLAS = 'assets/minecraft/atlases/blocks.json'
DROP = ('assets/minecraft/shaders/',   # base pack shaders from an older build: now in overlays only
        'assets/minecraft/items/crossbow_arrow.json')   # a stray model file in QA's items/ (load error on 1.21.4+)
LEGACY = 'axon_1_21_0/'


def legacy_models(zin, repl):
    """1.21-1.21.3 versions of every items/*.json of the pack (see the module docstring)."""
    def read(fn):
        return repl[fn] if fn in repl else zin.read(fn)
    out = {}
    items = sorted(set(n for n in zin.namelist() + list(repl) if '/items/' in n and n.endswith('.json')))
    for fn in items:
        ns, name = fn.split('/')[1], fn.split('/')[-1][:-5]
        m = json.loads(read(fn)).get('model')
        if m is None:
            continue
        kind = m['type'].split(':')[-1]
        if kind == 'model':        # axon:<name> on the item_model component (1.21.2-1.21.3)
            out['%sassets/%s/models/item/%s.json' % (LEGACY, ns, name)] = json.dumps(
                {'parent': m['model']}, indent=2).encode()
            continue
        if kind != 'range_dispatch' or m['property'].split(':')[-1] != 'custom_model_data':
            raise SystemExit('%s: no 1.21.0 form for %s' % (fn, kind))
        base = json.load(open(os.path.join(HERE, 'legacy_1_21_0', name + '.json')))
        ov = base.setdefault('overrides', [])
        for e in sorted(m['entries'], key=lambda e: e['threshold']):   # the last match wins
            if e['model']['type'].split(':')[-1] != 'model':
                raise SystemExit('%s: entry %s is not a plain model' % (fn, e['threshold']))
            ov.append({'predicate': {'custom_model_data': e['threshold']}, 'model': e['model']['model']})
        out['%sassets/%s/models/item/%s.json' % (LEGACY, ns, name)] = json.dumps(base, indent=2).encode()
    return out


def validate(model, tex_png, name, need):
    errs = []
    m = json.loads(model)
    im = Image.open(io.BytesIO(tex_png))
    if im.size not in ((64, 64), (128, 128)):
        errs.append('texture size %s' % (im.size,))
    tex = m['textures']
    for k, v in tex.items():
        if not v.startswith('qualityarmory:axon/'):
            errs.append('texture ref %s' % v)
    for e in m['elements']:
        for c in e['from'] + e['to']:
            if not -16 <= c <= 32:
                errs.append('%s coord %s out of range' % (e['name'], c))
        if any(f > t for f, t in zip(e['from'], e['to'])):
            errs.append('%s from>to' % e['name'])
        r = e.get('rotation')
        if r and (r['angle'] not in (-45, -22.5, 0, 22.5, 45) or r['axis'] not in 'xyz'):
            errs.append('%s bad rotation %s' % (e['name'], r))
        for fn, fd in e['faces'].items():
            if fd['texture'][1:] not in tex:
                errs.append('%s.%s unresolved texture %s' % (e['name'], fn, fd['texture']))
            if not all(0 <= u <= 16 for u in fd['uv']):
                errs.append('%s.%s uv out of range' % (e['name'], fn))
    for k in need:       # every transform QA's own model has (missing ones fall back to defaults)
        d = m['display'].get(k)
        if d is None:
            errs.append('missing display ' + k)
            continue
        if any(abs(t) > 80 for t in d.get('translation', [])) or any(abs(s) > 4 for s in d.get('scale', [])):
            errs.append('display %s out of range' % k)
    return errs, len(m['elements'])


def main():
    zin = zipfile.ZipFile(SRC)
    repl = {}
    report = {}
    for g in GUNS:
        mj = open(os.path.join(HERE, 'build', g + '.json'), 'rb').read()
        png = open(os.path.join(HERE, 'build', g + '.png'), 'rb').read()
        qa = SKINS[g][0] if g in SKINS else g          # a skin carries its base gun's transforms
        need = json.loads(zin.read('assets/qualityarmory/models/gun/%s.json' % qa)).get('display', {}).keys()
        errs, n = validate(mj, png, g, set(need) | {'firstperson_lefthand'})
        if errs:
            raise SystemExit('%s: %s' % (g, errs))
        report[g] = n
        repl['assets/qualityarmory/models/gun/%s.json' % g] = mj
        repl['assets/qualityarmory/textures/axon/%s.png' % g] = png
    from gen_ammo import NAZWY as AMMO   # amunicja (gen_ammo.py): podmiana modeli qualityarmory:ammo/*
    for a in AMMO:
        base = a.replace('ammo', 'ammo_', 1)
        repl['assets/qualityarmory/models/ammo/%s.json' % a] = open(os.path.join(HERE, 'build', base + '.json'), 'rb').read()
        repl['assets/qualityarmory/textures/axon/%s.png' % base] = open(os.path.join(HERE, 'build', base + '.png'), 'rb').read()
    atlas = json.loads(zin.read(ATLAS))
    if not any(s.get('source') == 'axon' for s in atlas['sources']):
        atlas['sources'].append({'type': 'directory', 'source': 'axon', 'prefix': 'axon/'})
    repl[ATLAS] = json.dumps(atlas, indent=4).encode()
    # premium skins: new custom_model_data entries on the crossbow (QA's own ids end at 85)
    items = json.loads(zin.read(ITEMS))
    ent = items['model']['entries']
    for n, (base, _, cmd, _) in SKINS.items():
        ref = 'qualityarmory:gun/' + n
        if any(e['threshold'] == cmd and e['model'].get('model') != ref for e in ent):
            raise SystemExit('custom_model_data %d already used' % cmd)
        ent[:] = [e for e in ent if e['threshold'] != cmd]
        ent.append({'threshold': cmd, 'model': {'type': 'model', 'model': ref}})
    ent.sort(key=lambda e: e['threshold'])
    repl[ITEMS] = json.dumps(items, indent=2).encode()
    shaders = os.path.join(HERE, 'shadery')   # AxonMap: full screen map shader (rendertype_text)
    for fn in sorted(os.listdir(shaders)):
        data = open(os.path.join(shaders, fn), 'rb').read()
        repl['axon_shadery/assets/minecraft/shaders/core/' + fn] = data
        # 1.21-1.21.1: shader names and #moj_import paths without a namespace
        old = data.replace(b'"minecraft:core/', b'"').replace(b'<minecraft:', b'<')
        repl['axon_shadery_1_21_0/assets/minecraft/shaders/core/' + fn] = old
    from dodaj_reaktor import reactor_files   # reaktor AxonPlot (gen_reactor.py)
    repl.update(reactor_files())
    # AXON-Structure: zrzut (gen_zrzut.py), przedmiot axon:zrzut z modelem axon:block/zrzut
    # oraz rekwizyty z gen_rekwizyty.py (wrak Mi-8, łóżko), lokomotywa z gen_lokomotywa.py i meble z gen_meble.py i gen_sklep.py
    from gen_meble import MEBLE
    from gen_sklep import SKLEP
    from gen_pancerze import PANCERZE   # zestawy pancerzy (gen_pancerze.py)
    from gen_bronie_biale import NAZWY as BRONIE_BIALE   # bronie białe (gen_bronie_biale.py)
    from gen_auta import AUTA_I_TV   # auta i telewizor do blokowiska (gen_auta.py)
    for name in ['zrzut', 'wrak_mi8', 'lozko', 'lokomotywa'] + MEBLE + SKLEP + AUTA_I_TV + PANCERZE + BRONIE_BIALE:
        for src, dst in ((name + '.json', 'assets/axon/models/block/%s.json' % name),
                         (name + '.png', 'assets/axon/textures/item/%s.png' % name),
                         (name + '_item.json', 'assets/axon/items/%s.json' % name)):
            repl[dst] = open(os.path.join(HERE, 'build', src), 'rb').read()
    from gen_axoncore import pliki as axoncore_pliki, sprawdz as axoncore_sprawdz   # AxonCore (gen_axoncore.py)
    axoncore = axoncore_pliki()
    if axoncore_sprawdz(axoncore):
        raise SystemExit('axoncore: %s' % axoncore_sprawdz(axoncore))
    repl.update(axoncore)
    repl.update(legacy_models(zin, repl))
    mc = os.path.join(HERE, 'pack.mcmeta')   # owner-edited description, carried over
    if os.path.exists(mc):
        repl['pack.mcmeta'] = open(mc, 'rb').read()
    names = zin.namelist()
    with zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED) as zout:
        for info in zin.infolist():
            if info.filename.startswith(DROP):
                continue
            data = repl.pop(info.filename, None)
            if data is None:
                data = zin.read(info.filename)
            zi = zipfile.ZipInfo(info.filename, date_time=info.date_time)
            zi.compress_type = zipfile.ZIP_STORED if info.filename.endswith('/') else zipfile.ZIP_DEFLATED
            zi.external_attr = info.external_attr
            zout.writestr(zi, data)
        if 'assets/qualityarmory/textures/axon/' not in names:
            zi = zipfile.ZipInfo('assets/qualityarmory/textures/axon/', date_time=(2026, 10, 18, 0, 0, 0))
            zi.external_attr = 0o40755 << 16 | 0x10
            zout.writestr(zi, b'')
        for fn, data in sorted(repl.items()):
            zi = zipfile.ZipInfo(fn, date_time=(2026, 10, 18, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            zout.writestr(zi, data)
    sha = hashlib.sha1(open(DST, 'rb').read()).hexdigest()
    print('wrote', DST, 'sha1', sha, 'elements', report)


if __name__ == '__main__':
    main()
