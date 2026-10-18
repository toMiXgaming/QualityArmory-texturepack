#!/usr/bin/env python3
"""Builds QualityArmory-21-axon.zip = full copy of QA's 1.21.4 pack (QA21.zip) with only
the AK-47 / M4A1-S / Remington models replaced, the AXON textures added under
assets/qualityarmory/textures/axon/, and an 'axon' directory source added to the blocks
atlas (QA's atlas file only lists 'all/', so new texture folders must be registered)."""
import hashlib, io, json, os, sys, zipfile
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1] if len(sys.argv) > 1 else '/tmp/qa/QA21.zip'
DST = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, 'QualityArmory-21-axon.zip')
GUNS = ['ak47', 'm4a1s', 'remmington', 'makarov']
ATLAS = 'assets/minecraft/atlases/blocks.json'
NO_HEAD = {'makarov'}   # QA's own model has no head transform either


def validate(model, tex_png, name):
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
    for k in ('thirdperson_righthand', 'thirdperson_lefthand', 'firstperson_righthand',
              'firstperson_lefthand', 'gui', 'ground', 'fixed', 'head'):
        if k == 'head' and name in NO_HEAD:
            continue
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
        errs, n = validate(mj, png, g)
        if errs:
            raise SystemExit('%s: %s' % (g, errs))
        report[g] = n
        repl['assets/qualityarmory/models/gun/%s.json' % g] = mj
        repl['assets/qualityarmory/textures/axon/%s.png' % g] = png
    atlas = json.loads(zin.read(ATLAS))
    if not any(s.get('source') == 'axon' for s in atlas['sources']):
        atlas['sources'].append({'type': 'directory', 'source': 'axon', 'prefix': 'axon/'})
    repl[ATLAS] = json.dumps(atlas, indent=4).encode()
    shaders = os.path.join(HERE, 'shadery')   # AxonMap: full screen map shader (rendertype_text)
    for fn in sorted(os.listdir(shaders)):
        repl['assets/minecraft/shaders/core/' + fn] = open(os.path.join(shaders, fn), 'rb').read()
    axon = os.path.join(HERE, 'axonmap')   # AxonMap: font for the panel over the hotbar
    for root, _, files in os.walk(axon):
        for fn in sorted(files):
            path = os.path.join(root, fn)
            repl['assets/axonmap/' + os.path.relpath(path, axon).replace(os.sep, '/')] = open(path, 'rb').read()
    mc = os.path.join(HERE, 'pack.mcmeta')   # owner-edited description, carried over
    if os.path.exists(mc):
        repl['pack.mcmeta'] = open(mc, 'rb').read()
    names = zin.namelist()
    with zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED) as zout:
        for info in zin.infolist():
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
