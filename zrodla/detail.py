#!/usr/bin/env python3
"""Extra detail pass for the AXON gun models (called from gen.py after every build_<gun>()).

Every helper adds small real cuboids on the surfaces of elements that build_<gun>() already
made: serrations, ribs, rail teeth, screws, pins, vent holes (dark boxes), sight ticks, muzzle
bores ...  Nothing here moves or resizes an existing element, and every new part sticks out of
its host by at most ~0.1 gun unit, so the outline, the hand position and the sight line (ADS)
stay exactly as they were.  New elements are called dt_*, so the decals of build_<gun>() that
select elements by name (mag_*, grip_* ...) do not touch them.

No text is ever added: gun names are not written on the models (the AXON mark stays as it was).

Coordinates are gun space like in gen.py: u = back from the muzzle, v = up, w = to the right.
"""

HOLE = 'reticle'     # flat near-black material: a dark box 0.02-0.04 proud of the surface reads as a hole


def H(g, name):
    for e in g.els:
        if e.name == name:
            return e
    raise KeyError('%s: no element %s' % (g.name, name))


def _nm(g, tag):
    k = sum(1 for e in g.els if e.name.startswith('dt_' + tag))
    return 'dt_%s%d' % (tag, k)


def _rot(e):
    if e.rot:
        return dict(rot=(e.rot[0], (e.rot[1][2], e.rot[1][1])))
    return {}


def box_on(g, host, side, a, b, d=0.05, mat=None, tag='x'):
    """Box of depth d standing on the face `side` of host (R/L: a=u,b=v; T/B: a=u,b=w; K/F: a=w,b=v)."""
    e = H(g, host)
    mat = mat or e.mat
    kw = _rot(e)
    n = _nm(g, tag)
    if side in 'RL':
        wr = (e.hi[0], e.hi[0] + d) if side == 'R' else (e.lo[0] - d, e.lo[0])
        assert e.lo[2] - 1e-6 <= a[0] and a[1] <= e.hi[2] + 1e-6 and e.lo[1] - 1e-6 <= b[0] and b[1] <= e.hi[1] + 1e-6, \
            (g.name, host, side, a, b)
        return g.b(n, a, b, wr, mat, **kw)
    if side in 'TB':
        vr = (e.hi[1], e.hi[1] + d) if side == 'T' else (e.lo[1] - d, e.lo[1])
        assert e.lo[2] - 1e-6 <= a[0] and a[1] <= e.hi[2] + 1e-6 and e.lo[0] - 1e-6 <= b[0] and b[1] <= e.hi[0] + 1e-6, \
            (g.name, host, side, a, b)
        return g.b(n, a, vr, b, mat, **kw)
    ur = (e.hi[2], e.hi[2] + d) if side == 'K' else (e.lo[2] - d, e.lo[2])
    assert e.lo[0] - 1e-6 <= a[0] and a[1] <= e.hi[0] + 1e-6 and e.lo[1] - 1e-6 <= b[0] and b[1] <= e.hi[1] + 1e-6, \
        (g.name, host, side, a, b)
    return g.b(n, ur, b, a, mat, **kw)


def studs(g, host, pts, r=0.13, d=0.05, sides='RL', mat=None, rb=None, tag='st'):
    """Round-ish pins / screws / holes: small boxes centred on pts=(a,b)."""
    rb = rb or r
    for (a, b) in pts:
        for s in sides:
            box_on(g, host, s, (a - r, a + r), (b - rb, b + rb), d, mat, tag)


def holes(g, host, pts, r=0.15, rb=None, sides='RL', tag='ho'):
    studs(g, host, pts, r, 0.03, sides, HOLE, rb, tag)


def ridges(g, host, sides, lo, hi, n, width, cross=None, d=0.05, mat=None, tag='rb', along='a'):
    """n equal ridges of `width` between lo and hi, running across `cross` (default: whole face minus 0.12)."""
    e = H(g, host)
    step = (hi - lo) / n
    for s in sides:
        if s in 'RL':
            full = (e.lo[1] + 0.12, e.hi[1] - 0.12) if along == 'a' else (e.lo[2] + 0.12, e.hi[2] - 0.12)
        elif s in 'TB':
            full = (e.lo[0] + 0.12, e.hi[0] - 0.12) if along == 'a' else (e.lo[2] + 0.12, e.hi[2] - 0.12)
        else:
            full = (e.lo[1] + 0.12, e.hi[1] - 0.12) if along == 'a' else (e.lo[0] + 0.12, e.hi[0] - 0.12)
        cr = cross or full
        for i in range(n):
            c = lo + (i + 0.5) * step
            span = (c - width / 2, c + width / 2)
            if along == 'a':
                box_on(g, host, s, span, cr, d, mat, tag)
            else:
                box_on(g, host, s, cr, span, d, mat, tag)


def ring(g, name, u, vc, r, mat, dw=0.0, k=0.68, pad=0.05):
    """Thin collar around a round-ish part of half-size r (same cross outline as g.cyl)."""
    g.cyl(_nm(g, name), u, vc, r + pad, mat, dw, k)


def stepped_mag(g, prefix, n, d=0.05, width=0.2, tag='mr', sides='RL'):
    """One horizontal witness rib on every step of a stepped magazine."""
    for i in range(n):
        e = H(g, '%s_%d' % (prefix, i))
        c = (e.lo[1] + e.hi[1]) / 2
        box_on(g, e.name, sides[0], (e.lo[2] + 0.2, e.hi[2] - 0.2), (c - width / 2, c + width / 2), d, None, tag)
        if len(sides) > 1:
            box_on(g, e.name, sides[1], (e.lo[2] + 0.2, e.hi[2] - 0.2), (c - width / 2, c + width / 2), d, None, tag)


def stepped_grip(g, prefix, n, per=2, d=0.035, width=0.1, tag='gr', inset=0.2):
    """Checkering ridges on every segment of a stepped grip (pistols, SMGs)."""
    for i in range(n):
        e = H(g, '%s_%d' % (prefix, i))
        ridges(g, e.name, 'RL', e.lo[1] + inset, e.hi[1] - inset, per, width,
               cross=(e.lo[2] + 0.28, e.hi[2] - 0.28), d=d, tag=tag, along='b')


def muzzle_bore(g, host, vc=0.0, dw=0.0, r=0.17):
    """Dark bore at the muzzle end (front face of host)."""
    box_on(g, host, 'F', (dw - r, dw + r), (vc - r, vc + r), 0.03, HOLE, 'bore')


def rear_sight_ticks(g, host, u0, u1, n, cross=None, d=0.05):
    ridges(g, host, 'T', u0, u1, n, (u1 - u0) / n * 0.45, cross, d, tag='tick')


def pistol(g, slide, slide_top, frame, grips, mag_base=None, ser_rear=7, ser_front=3, has_port=True, ngrip=5):
    """Common pistol/handgun details."""
    s = H(g, slide)
    # slide serrations (rear and front) on both flanks
    ridges(g, slide, 'RL', s.hi[2] - 1.7, s.hi[2] - 0.25, ser_rear, 0.11, cross=(s.lo[1] + 0.12, s.hi[1] - 0.1), d=0.045,
           tag='ser')
    if ser_front:
        ridges(g, slide, 'RL', s.lo[2] + 1.0, s.lo[2] + 1.55, ser_front, 0.1, cross=(s.lo[1] + 0.12, s.hi[1] - 0.1),
               d=0.04, tag='serf')
    if has_port:      # ejection port + extractor
        holes(g, slide, [((s.hi[2] - 3.0 + s.hi[2] - 2.0) / 2, s.hi[1] - 0.3)], r=0.55, rb=0.17, sides='R', tag='port')
        box_on(g, slide, 'R', (s.hi[2] - 2.0, s.hi[2] - 1.85), (s.hi[1] - 0.45, s.hi[1] - 0.2), 0.05, None, 'ext')
    # slide-top slits / lightening grooves behind the front sight
    st = H(g, slide_top)
    ridges(g, slide_top, 'T', st.hi[2] - 1.7, st.hi[2] - 0.35, 5, 0.1, d=0.035, tag='stt')
    # frame: dust-cover rail grooves, takedown pins
    f = H(g, frame)
    ridges(g, frame, 'RL', f.lo[2] + 0.4, f.lo[2] + 1.6, 3, 0.1, cross=(f.hi[1] - 0.4, f.hi[1] - 0.12), d=0.03,
           mat=None, tag='rail')
    stepped_grip(g, grips, ngrip)
    if mag_base:
        m = H(g, mag_base)
        ridges(g, mag_base, 'RL', m.lo[2] + 0.35, m.hi[2] - 0.35, 3, 0.1, d=0.03, tag='mb')
        box_on(g, mag_base, 'B', (m.lo[2] + 0.1, m.hi[2] - 0.1), (m.lo[0] + 0.1, m.hi[0] - 0.1), 0.05, None, 'mbp')


def picatinny(g, host, n, width=None, d=0.05, tag='pic', sides='T', mat=None):
    """Rail teeth: n raised segments along the top face of a rail element."""
    e = H(g, host)
    L = e.hi[2] - e.lo[2]
    ridges(g, host, sides, e.lo[2] + 0.1, e.hi[2] - 0.1, n, width or (L - 0.2) / n * 0.5, d=d, mat=mat, tag=tag,
           cross=None)


# ================================================================ guns
def d_ak47(g):
    studs(g, 'brake_a', [(0.9, 0.0), (1.4, 0.0), (1.9, 0.0)], 0.12, 0.03, 'RL', HOLE, 0.28, 'bk')
    for u in (3.2, 9.4):
        ring(g, 'brl', (u, u + 0.28), 0.0, 0.43, 'steel')
    studs(g, 'fsb_collar', [(5.15, -0.1)], 0.14, 0.05, 'RL', tag='fs')
    studs(g, 'fsb_ear_l', [(5.15, 2.3)], 0.12, 0.04, 'L', HOLE, tag='fsh')
    ridges(g, 'fsb_tower', 'RL', 4.5, 5.8, 3, 0.12, cross=(0.8, 1.5), d=0.04, tag='fst')
    studs(g, 'gas_block', [(10.9, 1.4), (11.8, 1.4)], 0.13, 0.05, 'RL', tag='gb')
    holes(g, 'gas_block', [(11.4, 0.3)], 0.2, 0.2, 'RL', 'gbh')
    ridges(g, 'hg_swell_f', 'RL', 14.0, 15.6, 4, 0.12, cross=(-1.4, 0.35), d=0.045, tag='hgf')
    ridges(g, 'hg_swell_r', 'RL', 16.7, 18.4, 4, 0.12, cross=(-1.4, 0.35), d=0.045, tag='hgr')
    holes(g, 'hg_upper', [(14.45, 1.62), (15.95, 1.62), (17.45, 1.62)], 0.4, 0.17, 'RL', 'hgv')
    ridges(g, 'hg_upper_top', 'T', 13.4, 18.5, 8, 0.2, d=0.04, tag='hgt')
    studs(g, 'hg_retainer', [(19.32, -1.2), (19.32, 0.3)], 0.12, 0.05, 'RL', tag='hr')
    ridges(g, 'rs_leaf', 'T', 20.8, 22.5, 7, 0.1, cross=(-0.45, 0.45), d=0.045, mat='parts', tag='rsl')
    studs(g, 'rs_base', [(20.4, 1.15), (21.6, 1.15)], 0.12, 0.05, 'RL', tag='rsb')
    studs(g, 'receiver', [(20.2, -1.3), (20.2, 0.25), (22.55, -1.35), (22.55, 0.35), (23.35, -1.4), (31.95, -0.6),
                          (31.95, 0.45), (28.9, -1.15), (29.85, -0.5), (30.6, -1.25)], 0.15, 0.05, 'RL', tag='rv')
    holes(g, 'receiver', [(25.1, -0.35)], 0.7, 0.3, 'RL', 'mw')
    ridges(g, 'dust_cover_top', 'T', 29.4, 32.4, 6, 0.2, d=0.045, tag='dct')
    ridges(g, 'dust_cover', 'RL', 29.4, 32.4, 6, 0.2, cross=(1.35, 1.85), d=0.04, tag='dcs')
    studs(g, 'rear_trunnion', [(33.0, 0.4), (33.0, -0.5)], 0.14, 0.05, 'RL', tag='tr')
    ridges(g, 'sel_lever', 'R', 25.6, 31.0, 6, 0.14, cross=(0.55, 0.9), d=0.04, tag='sel')
    stepped_mag(g, 'mag', 7)
    for i in range(7):
        e = H(g, 'mag_%d' % i)
        ridges(g, e.name, 'K', e.lo[1] + 0.15, e.hi[1] - 0.15, 2, 0.12, cross=(-0.5, 0.5), d=0.04, tag='mk', along='b')
    ridges(g, 'mag_floor', 'B', 21.2, 23.6, 5, 0.18, cross=(-0.6, 0.6), d=0.04, tag='mf')
    studs(g, 'tg_bottom', [(29.0, 0.0)], 0.1, 0.04, 'B', tag='tgs')
    ridges(g, 'grip', 'RL', -7.0, -2.9, 9, 0.12, cross=(30.2, 31.7), d=0.04, tag='gc', along='b')
    studs(g, 'grip', [(31.0, -2.7)], 0.17, 0.05, 'RL', tag='gs')
    ridges(g, 'stock_comb', 'RL', 34.2, 41.2, 3, 0.12, cross=(-1.2, -0.9), d=0.035, tag='sc')
    studs(g, 'stock_comb', [(37.5, -0.3), (40.5, -0.2), (35.0, -0.9)], 0.17, 0.045, 'RL', tag='ss')
    studs(g, 'buttplate', [(0.0, 0.5), (0.0, -4.9), (0.0, -2.2)], 0.2, 0.05, 'K', tag='bp')
    ridges(g, 'buttplate', 'K', -5.4, 0.7, 7, 0.14, cross=(-0.75, 0.75), d=0.035, tag='bpr', along='b')
    studs(g, 'swivel_r_plate', [(39.7, -2.25)], 0.12, 0.04, 'L', tag='sw')
    ridges(g, 'rod', 'T', 6.5, 19.5, 6, 0.1, d=0.03, mat='parts', tag='rod')


def d_m4a1s(g):
    for u in (2.0, 4.4, 6.8):
        ring(g, 'sup', (u, u + 0.3), 0.0, 1.02, 'black')
    holes(g, 'supp_body_a', [(1.4, 0.0), (3.2, 0.0), (5.6, 0.0), (7.4, 0.0)], 0.2, 0.34, 'RL', 'sph')
    studs(g, 'fsb_collar', [(12.2, -0.1)], 0.14, 0.05, 'RL', tag='fs')
    picatinny(g, 'rail_t_crown', 16, 0.2, tag='rt')
    picatinny(g, 'up_rail_crown', 14, 0.2, tag='ur')
    picatinny(g, 'rail_b_crown', 10, 0.2, 0.05, 'rb', 'B')
    picatinny(g, 'rail_r_crown', 8, 0.2, 0.05, 'rr', 'R')
    picatinny(g, 'rail_l_crown', 8, 0.2, 0.05, 'rl', 'L')
    studs(g, 'delta_ring_b', [(22.72, 0.0)], 0.12, 0.05, 'RL', tag='dr')
    studs(g, 'upper', [(24.6, 0.5), (26.4, 0.9), (32.9, 0.2), (32.9, -0.4)], 0.14, 0.05, 'RL', tag='up')
    holes(g, 'upper', [(25.9, 0.7)], 0.6, 0.18, 'L', 'ejp')
    studs(g, 'lower', [(24.9, -1.6), (33.2, -1.0), (30.5, -2.1)], 0.14, 0.05, 'RL', tag='lo')
    ridges(g, 'magwell_lip', 'RL', 24.3, 27.3, 4, 0.14, cross=(-3.7, -3.5), d=0.04, tag='mwl')
    stepped_mag(g, 'mag', 4, width=0.22)
    ridges(g, 'mag_floor', 'B', 23.6, 26.4, 5, 0.18, cross=(-0.55, 0.55), d=0.04, tag='mf')
    ridges(g, 'grip', 'RL', -6.8, -3.0, 9, 0.12, cross=(31.5, 33.0), d=0.04, tag='gc', along='b')
    studs(g, 'grip', [(32.3, -2.8)], 0.17, 0.05, 'RL', tag='gs')
    ridges(g, 'stock_house', 'RL', 37.4, 42.8, 5, 0.14, cross=(-0.7, 0.8), d=0.04, tag='sh')
    ridges(g, 'stock_ridge', 'T', 38.2, 42.8, 8, 0.2, d=0.04, tag='sr')
    ridges(g, 'buttpad', 'K', -3.6, 1.2, 9, 0.14, cross=(-0.7, 0.7), d=0.035, tag='bpr', along='b')
    studs(g, 'stock_house', [(41.8, -0.55)], 0.17, 0.05, 'RL', tag='ss')


def d_m16(g):
    holes(g, 'fh_a', [(0.9, 0.0), (1.7, 0.0)], 0.14, 0.2, 'RL', 'fhh')
    for u in (3.5, 6.0):
        ring(g, 'brl', (u, u + 0.25), 0.0, 0.38, 'black')
    studs(g, 'fsb_collar', [(8.15, -0.1)], 0.14, 0.05, 'RL', tag='fs')
    ridges(g, 'fsb_tower_lo', 'RL', 7.65, 8.75, 3, 0.1, cross=(0.78, 1.3), d=0.04, tag='fst')
    ridges(g, 'hg_a', 'RL', -0.5, 0.95, 4, 0.14, cross=(10.8, 23.0), d=0.045, tag='hgs', along='b')
    ridges(g, 'hg_b', 'T', 10.6, 23.2, 14, 0.2, cross=(-0.6, 0.6), d=0.04, tag='hgt')
    ridges(g, 'hg_b', 'B', 10.6, 23.2, 14, 0.2, cross=(-0.6, 0.6), d=0.04, tag='hgb')
    studs(g, 'hg_cap_b', [(10.1, 0.2)], 0.1, 0.05, 'RL', tag='hc')
    studs(g, 'delta_b', [(23.8, 0.2)], 0.12, 0.05, 'RL', tag='dr')
    studs(g, 'upper', [(25.0, 0.2), (30.0, 0.9), (33.3, 0.2), (33.3, -0.4)], 0.14, 0.05, 'RL', tag='up')
    holes(g, 'upper', [(27.2, 0.45)], 0.8, 0.2, 'L', 'ejp')
    ridges(g, 'ch_top', 'T', 25.0, 32.2, 14, 0.18, cross=(-0.5, 0.5), d=0.05, tag='cht')
    studs(g, 'lower', [(25.2, -1.7), (33.4, -1.2), (30.5, -2.2)], 0.14, 0.05, 'RL', tag='lo')
    ridges(g, 'magwell_lip', 'RL', 24.7, 28.1, 4, 0.14, cross=(-3.72, -3.5), d=0.04, tag='mwl')
    stepped_mag(g, 'mag', 4, width=0.22)
    ridges(g, 'mag_floor', 'B', 24.2, 27.0, 5, 0.18, cross=(-0.55, 0.55), d=0.04, tag='mf')
    ridges(g, 'grip', 'RL', -6.8, -3.0, 9, 0.12, cross=(32.0, 33.3), d=0.04, tag='gc', along='b')
    studs(g, 'grip', [(32.8, -2.8)], 0.17, 0.05, 'RL', tag='gs')
    ridges(g, 'stock_comb', 'RL', 36.2, 46.2, 3, 0.12, cross=(-0.7, -0.3), d=0.035, tag='sc')
    ridges(g, 'buttplate', 'K', -7.3, 1.1, 14, 0.14, cross=(-0.8, 0.8), d=0.035, tag='bpr', along='b')
    studs(g, 'buttplate', [(0.0, 0.7), (0.0, -6.9)], 0.18, 0.05, 'K', tag='bp')
    studs(g, 'stock_comb', [(40.0, 0.4)], 0.17, 0.045, 'RL', tag='ss')


def d_remmington(g):
    ridges(g, 'vent_rib', 'T', 0.6, 24.2, 24, 0.2, d=0.04, tag='vr')
    for u in (2.0, 9.0, 16.0):
        ring(g, 'brl', (u, u + 0.25), 0.0, 0.44, 'blued', pad=0.04)
    muzzle_bore(g, 'barrel_a', 0.0, 0.0, 0.3)
    studs(g, 'magcap_b', [(5.2, -1.3)], 0.14, 0.05, 'RL', tag='mc')
    ridges(g, 'barrel_ring', 'RL', 6.0, 6.6, 2, 0.12, cross=(-1.75, 0.55), d=0.04, tag='brr')
    ridges(g, 'action_bar_r', 'R', 21.9, 25.0, 5, 0.18, cross=(-1.8, -1.55), d=0.03, tag='ab')
    holes(g, 'receiver', [(30.9, 0.1)], 0.8, 0.4, 'R', 'ej')
    studs(g, 'receiver', [(26.1, -1.8), (32.9, -1.8), (32.9, 0.1), (26.1, 0.3)], 0.14, 0.05, 'RL', tag='rv')
    ridges(g, 'receiver_top', 'T', 26.0, 33.0, 10, 0.2, d=0.03, tag='rt')
    ridges(g, 'trigger_plate', 'B', 27.6, 33.4, 3, 0.16, cross=(-0.8, 0.8), d=0.03, tag='tp')
    studs(g, 'trigger_plate', [(28.0, 0.7), (33.0, -0.7)], 0.12, 0.04, 'B', tag='tps')
    ridges(g, 'bolt', 'R', 26.7, 29.1, 6, 0.14, cross=(-0.4, 0.45), d=0.03, mat='steel', tag='bo')
    for i in range(6):
        sh = 'shell%d' % i
        e = H(g, sh)
        box_on(g, sh, 'B', (e.lo[2] + 0.05, e.hi[2] - 0.05), (e.lo[0] + 0.05, e.hi[0] - 0.05), 0.07, 'brass', 'sb')
        box_on(g, sh, 'T', (e.lo[2] + 0.15, e.hi[2] - 0.15), (e.lo[0] + 0.15, e.hi[0] - 0.15), 0.05, 'brass', 'st')
    ridges(g, 'stock_grip', 'RL', 34.0, 36.6, 5, 0.12, cross=(-3.2, -2.5), d=0.035, tag='sg')
    studs(g, 'stock_body', [(38.0, -0.4), (43.5, -0.6)], 0.16, 0.045, 'RL', tag='ss')
    ridges(g, 'recoil_pad', 'K', -6.0, 0.8, 12, 0.14, cross=(-0.8, 0.8), d=0.035, tag='rp', along='b')
    studs(g, 'swivel_f_stud', [(5.2, -2.05)], 0.1, 0.04, 'RL', tag='sw')


def d_makarov(g):
    pistol(g, 'slide', 'slide_top', 'frame', 'grip', 'mag_floor', ser_rear=7, ser_front=0, ngrip=4)
    muzzle_bore(g, 'slide_nose', 0.1, 0.0, 0.17)
    ridges(g, 'safety', 'T', 6.3, 7.0, 4, 0.1, cross=(-0.7, -0.64), d=0.03, tag='sf')
    studs(g, 'frame', [(2.9, -0.95), (6.2, -0.95)], 0.13, 0.04, 'RL', tag='fr')
    studs(g, 'grip_2', [(6.3, -3.6)], 0.2, 0.04, 'RL', tag='gs')


def d_awp(g):
    holes(g, 'brake_a', [(0.8, 0.0), (1.3, 0.0), (1.8, 0.0), (2.3, 0.0)], 0.1, 0.3, 'RL', 'bh')
    for u in (5.5, 11.0, 17.0):
        ring(g, 'brl', (u, u + 0.3), 0.0, 0.5, 'black')
    ridges(g, 'forend', 'RL', -2.0, -0.6, 3, 0.1, cross=(14.2, 30.2), d=0.045, tag='fe', along='b')
    holes(g, 'forend', [(16.5, -1.4), (19.0, -1.4), (21.5, -1.4), (24.0, -1.4), (26.5, -1.4), (29.0, -1.4)], 0.5, 0.2, 'RL', 'fv')
    ridges(g, 'forend', 'B', 14.2, 29.8, 14, 0.24, cross=(-0.7, 0.7), d=0.04, tag='fb')
    studs(g, 'bipod_mount', [(14.7, -2.75)], 0.14, 0.05, 'RL', tag='bm')
    picatinny(g, 'rail', 18, 0.22, tag='rl')
    studs(g, 'receiver_a', [(32.0, 0.1), (36.0, 0.3), (40.0, 0.1)], 0.15, 0.05, 'RL', tag='rv')
    holes(g, 'receiver_a', [(34.0, 0.0)], 0.8, 0.22, 'R', 'ej')
    ridges(g, 'bolt_knob', 'R', 39.5, 40.3, 3, 0.12, cross=(-1.0, -0.5), d=0.04, tag='bk')
    ridges(g, 'turret_el', 'RL', 4.2, 4.72, 4, 0.07, cross=(31.5, 32.7), d=0.03, tag='kn', along='b')
    ridges(g, 'turret_wi', 'R', 31.5, 32.7, 5, 0.12, cross=(2.8, 3.8), d=0.04, tag='kw')
    ridges(g, 'scope_t', 'T', 28.2, 36.0, 8, 0.2, cross=(-0.5, 0.5), d=0.035, tag='sc')
    ridges(g, 'power_t', 'T', 36.6, 37.2, 3, 0.12, cross=(-0.5, 0.5), d=0.04, tag='pw')
    ridges(g, 'eyecup_t', 'T', 41.7, 42.3, 3, 0.1, cross=(-0.7, 0.7), d=0.035, tag='ey')
    studs(g, 'ring_f_nut', [(29.7, 1.85)], 0.14, 0.05, 'R', tag='nf')
    studs(g, 'ring_r_nut', [(35.3, 1.85)], 0.14, 0.05, 'R', tag='nr')
    studs(g, 'ring_f_t', [(29.7, 0.0)], 0.1, 0.04, 'T', tag='rf')
    studs(g, 'ring_r_t', [(35.3, 0.0)], 0.1, 0.04, 'T', tag='rr')
    ridges(g, 'mag', 'RL', -3.7, -2.7, 4, 0.12, cross=(33.4, 36.0), d=0.04, tag='mg', along='b')
    ridges(g, 'grip', 'RL', -6.2, -1.3, 9, 0.12, cross=(41.9, 44.0), d=0.04, tag='gc', along='b')
    studs(g, 'grip', [(43.0, -1.6)], 0.17, 0.05, 'RL', tag='gs')
    ridges(g, 'cheek', 'T', 46.8, 54.2, 8, 0.2, cross=(-0.7, 0.7), d=0.035, tag='ck')
    studs(g, 'butt', [(50.0, -0.8), (53.5, -0.8)], 0.17, 0.05, 'RL', tag='bs')
    ridges(g, 'buttpad', 'K', -6.4, 1.8, 14, 0.14, cross=(-0.85, 0.85), d=0.035, tag='bp', along='b')
    studs(g, 'sling_stud', [(53.0, -6.7)], 0.1, 0.04, 'RL', tag='sl')


def d_mac10(g):
    holes(g, 'upper', [(8.0, 0.7)], 0.9, 0.28, 'R', 'ej')
    studs(g, 'upper', [(2.5, 0.3), (6.0, 0.9), (11.5, 0.3), (12.8, 0.9)], 0.14, 0.05, 'RL', tag='rv')
    ridges(g, 'upper', 'RL', 3.0, 12.0, 3, 0.35, cross=(-0.7, -0.35), d=0.03, tag='sr')
    studs(g, 'lower', [(2.6, -1.5), (12.8, -1.5), (7.4, -1.7)], 0.14, 0.05, 'RL', tag='lo')
    muzzle_bore(g, 'barrel_a', 0.0, 0.0, 0.14)
    ridges(g, 'knob', 'T', 3.4, 4.1, 4, 0.1, cross=(-0.25, 0.25), d=0.03, tag='kn')
    ridges(g, 'grip', 'RL', -7.2, -2.4, 10, 0.12, cross=(7.25, 10.05), d=0.04, tag='gc', along='b')
    ridges(g, 'mag', 'RL', -12.0, -8.0, 8, 0.14, cross=(7.4, 9.8), d=0.035, tag='mg', along='b')
    ridges(g, 'mag_floor', 'B', 7.3, 9.9, 5, 0.18, cross=(-0.7, 0.7), d=0.04, tag='mf')
    ridges(g, 'butt_plate', 'K', -3.2, 0.4, 7, 0.14, cross=(-1.1, 1.1), d=0.035, tag='bp', along='b')
    studs(g, 'butt_plate', [(0.0, -1.5)], 0.2, 0.05, 'K', tag='bs')
    ridges(g, 'stock_rod_r', 'R', 3.0, 13.0, 8, 0.2, cross=(-1.5, -1.35), d=0.03, mat='steel', tag='rd')
    ridges(g, 'safety', 'T', 4.7, 5.7, 4, 0.12, cross=(1.16, 1.24), d=0.03, tag='sf')
    studs(g, 'strap_lug', [(2.3, -2.4)], 0.13, 0.04, 'RL', tag='sl')


def d_sks(g):
    muzzle_bore(g, 'barrel_a', 0.0, 0.0, 0.14)
    for u in (3.0, 6.5, 15.5):
        ring(g, 'brl', (u, u + 0.25), 0.0, 0.4, 'blued', pad=0.04)
    ridges(g, 'fs_hood', 'T', 1.3, 2.2, 3, 0.12, cross=(-0.3, 0.3), d=0.03, tag='fh')
    studs(g, 'gas_block', [(8.6, 0.5), (8.6, -0.1)], 0.13, 0.05, 'RL', tag='gb')
    ridges(g, 'hg_upper_top', 'T', 14.0, 20.2, 8, 0.2, d=0.035, tag='ht')
    holes(g, 'hg_upper', [(15.0, 1.0), (16.6, 1.0), (18.2, 1.0), (19.6, 1.0)], 0.35, 0.16, 'RL', 'hv')
    ridges(g, 'forend', 'RL', -1.3, 0.3, 3, 0.1, cross=(12.8, 22.1), d=0.04, tag='fe', along='b')
    ridges(g, 'forend', 'B', 12.8, 22.0, 9, 0.22, cross=(-0.7, 0.7), d=0.035, tag='fb')
    studs(g, 'band', [(14.1, 0.9), (14.1, -1.0)], 0.12, 0.05, 'RL', tag='bd')
    ridges(g, 'rs_leaf', 'T', 21.3, 22.9, 7, 0.1, d=0.04, mat='parts', tag='rl')
    studs(g, 'receiver', [(23.0, -0.6), (23.0, 0.3), (31.2, -0.6), (31.2, 0.3), (26.0, -0.7)], 0.13, 0.05, 'RL', tag='rv')
    ridges(g, 'cover', 'RL', 23.6, 31.2, 4, 0.14, cross=(0.85, 1.15), d=0.035, tag='cv')
    ridges(g, 'cover_top', 'T', 23.6, 31.2, 12, 0.2, d=0.03, tag='ct')
    ridges(g, 'mag', 'RL', -2.5, -1.2, 3, 0.1, cross=(23.2, 27.0), d=0.035, tag='mg', along='b')
    ridges(g, 'bolt_knob', 'R', 27.4, 28.2, 3, 0.12, cross=(0.2, 0.8), d=0.04, tag='bk')
    ridges(g, 'wrist', 'RL', 31.9, 33.2, 4, 0.14, cross=(-1.9, 0.3), d=0.03, tag='wr')
    studs(g, 'stock_5', [(39.2, -1.5)], 0.17, 0.045, 'RL', tag='ss')
    ridges(g, 'buttplate', 'K', -6.0, -0.2, 11, 0.14, cross=(-0.8, 0.8), d=0.035, tag='bp', along='b')
    studs(g, 'buttplate', [(0.0, -0.9), (0.0, -5.3)], 0.17, 0.05, 'K', tag='bs')
    studs(g, 'tg_bottom', [(29.3, 0.0)], 0.1, 0.04, 'B', tag='tgs')


def d_deagle(g):
    pistol(g, 'slide', 'slide_top', 'frame', 'grip', 'mag_floor', ser_rear=8, ser_front=4)
    muzzle_bore(g, 'barrel', 0.0, 0.0, 0.3)
    picatinny(g, 'rail', 12, 0.2, 0.04, 'rl')
    ridges(g, 'barrel', 'RL', 1.0, 6.4, 4, 0.12, cross=(-0.5, 0.45), d=0.035, tag='bs')
    studs(g, 'grip_2', [(11.5, -3.8)], 0.22, 0.04, 'RL', tag='gs')


def d_sw1911(g):
    pistol(g, 'slide', 'slide_top', 'frame', 'grip', 'mag_base', ser_rear=7, ser_front=3)
    muzzle_bore(g, 'bushing_a', 0.0, 0.0, 0.12)
    studs(g, 'grip_2', [(8.6, -3.7)], 0.2, 0.04, 'RL', tag='gs')
    ridges(g, 'beavertail', 'T', 9.7, 10.35, 3, 0.1, d=0.03, tag='bv')
    ridges(g, 'hammer_spur', 'T', 10.1, 10.3, 2, 0.06, d=0.03, tag='hm')
    studs(g, 'dust_cover', [(3.2, -1.2)], 0.12, 0.04, 'RL', tag='dc')


def d_p30(g):
    pistol(g, 'slide', 'slide_top', 'frame', 'grip', 'mag_base', ser_rear=6, ser_front=3)
    muzzle_bore(g, 'slide_nose', 0.05, 0.0, 0.14)
    studs(g, 'grip_3', [(7.5, -4.3)], 0.2, 0.04, 'RL', tag='gs')
    for s in 'RL':
        box_on(g, 'release_' + s.lower(), s, (4.6, 5.2), (-0.8, -0.65), 0.02, 'black', 'rl')


def d_glock(g):
    pistol(g, 'slide', 'slide_top', 'frame', 'grip', 'mag_base', ser_rear=6, ser_front=3)
    muzzle_bore(g, 'slide_nose', 0.05, 0.0, 0.14)
    studs(g, 'grip_3', [(7.6, -4.3)], 0.2, 0.04, 'RL', tag='gs')
    ridges(g, 'frame_nose', 'B', 1.0, 3.6, 4, 0.2, cross=(-0.4, 0.4), d=0.04, tag='fn')
    studs(g, 'frame_nose', [(2.0, -0.8), (3.2, -0.8)], 0.1, 0.03, 'RL', tag='fp')


def d_mp5(g):
    muzzle_bore(g, 'muzzle_a', 0.0, 0.0, 0.14)
    ridges(g, 'handguard', 'RL', -1.35, 0.55, 4, 0.12, cross=(3.7, 10.1), d=0.04, tag='hg', along='b')
    ridges(g, 'handguard', 'B', 3.7, 10.1, 9, 0.22, cross=(-0.55, 0.55), d=0.04, tag='hb')
    studs(g, 'handguard', [(3.8, -0.4)], 0.12, 0.04, 'RL', tag='hs')
    studs(g, 'receiver', [(11.0, -0.2), (14.5, 0.3), (20.4, -0.2), (17.5, 1.2)], 0.14, 0.05, 'RL', tag='rv')
    holes(g, 'receiver', [(15.5, 0.9)], 0.8, 0.22, 'R', 'ej')
    ridges(g, 'rs_drum_l', 'L', 19.7, 20.3, 3, 0.1, cross=(2.3, 2.9), d=0.03, tag='rdl')
    ridges(g, 'rs_drum_r', 'R', 19.7, 20.3, 3, 0.1, cross=(2.3, 2.9), d=0.03, tag='rdr')
    ridges(g, 'ch_knob', 'T', 4.8, 5.3, 2, 0.1, d=0.03, tag='ck')
    ridges(g, 'magwell', 'RL', 10.8, 12.4, 3, 0.14, cross=(-1.6, -0.8), d=0.035, tag='mw')
    stepped_mag(g, 'mag', 6)
    ridges(g, 'mag_floor', 'B', 9.4, 10.7, 3, 0.18, cross=(-0.4, 0.4), d=0.04, tag='mf')
    stepped_grip(g, 'grip', 4, per=2, d=0.04, width=0.12, inset=0.22)
    ridges(g, 'selector', 'L', 16.8, 17.4, 3, 0.1, d=0.03, tag='sl')
    ridges(g, 'buttpad', 'K', -3.3, 1.0, 8, 0.14, cross=(-0.55, 0.55), d=0.035, tag='bp', along='b')
    studs(g, 'stock_5', [(26.0, -0.3)], 0.17, 0.045, 'RL', tag='ss')
    studs(g, 'lower', [(14.0, -1.1), (18.5, -1.1)], 0.13, 0.05, 'RL', tag='lo')


def d_uzi(g):
    muzzle_bore(g, 'barrel_a', 0.0, 0.0, 0.13)
    ridges(g, 'barrel_nut_a', 'RL', 3.1, 3.6, 2, 0.1, cross=(-0.3, 0.3), d=0.04, tag='bn')
    ridges(g, 'receiver', 'RL', 5.0, 19.8, 3, 0.35, cross=(-0.6, 0.55), d=0.03, tag='sr')
    studs(g, 'receiver', [(4.5, 0.6), (20.6, 0.6), (4.5, -0.5), (20.6, -0.5), (12.0, 0.8)], 0.13, 0.05, 'RL', tag='rv')
    ridges(g, 'cover', 'T', 4.4, 20.4, 14, 0.3, cross=(-0.5, 0.5), d=0.03, tag='cv')
    holes(g, 'receiver', [(8.0, 0.45)], 0.9, 0.2, 'R', 'ej')
    ridges(g, 'ch_knob', 'T', 9.1, 9.7, 3, 0.1, d=0.03, tag='ck')
    ridges(g, 'forend', 'RL', -1.8, -1.05, 3, 0.1, cross=(4.9, 10.5), d=0.04, tag='fe', along='b')
    ridges(g, 'forend', 'B', 4.9, 10.5, 8, 0.2, cross=(-0.7, 0.7), d=0.04, tag='fb')
    studs(g, 'lower', [(11.5, -1.3), (18.0, -1.3)], 0.13, 0.05, 'RL', tag='lo')
    stepped_grip(g, 'grip', 3, per=3, d=0.04, width=0.12, inset=0.25)
    ridges(g, 'mag', 'RL', -9.2, -6.8, 6, 0.14, cross=(13.9, 15.1), d=0.035, tag='mg', along='b')
    ridges(g, 'mag_floor', 'B', 13.8, 15.2, 4, 0.14, cross=(-0.4, 0.4), d=0.04, tag='mf')
    ridges(g, 'butt_pad', 'K', -2.7, -1.6, 4, 0.1, cross=(-0.7, 0.7), d=0.03, tag='bp', along='b')
    ridges(g, 'selector', 'L', 14.3, 15.1, 3, 0.1, d=0.03, tag='sl')
    ridges(g, 'stock_arm_r', 'T', 17.2, 21.0, 5, 0.2, cross=(0.74, 0.84), d=0.03, tag='sa')
    studs(g, 'hinge', [(21.5, -0.3)], 0.15, 0.05, 'RL', tag='hn')


def d_sg553(g):
    holes(g, 'fh_a', [(0.5, 0.0), (1.05, 0.0)], 0.12, 0.2, 'RL', 'fhh')
    ring(g, 'brl', (3.0, 3.25), 0.0, 0.3, 'black', pad=0.04)
    ridges(g, 'fsb', 'RL', 5.8, 7.0, 3, 0.12, cross=(-0.4, 0.95), d=0.04, tag='fs')
    ridges(g, 'handguard', 'RL', -1.2, 1.2, 5, 0.12, cross=(7.7, 14.3), d=0.04, tag='hg', along='b')
    ridges(g, 'handguard', 'B', 7.7, 14.3, 8, 0.2, cross=(-0.65, 0.65), d=0.035, tag='hb')
    picatinny(g, 'rail', 14, 0.22, tag='rl')
    holes(g, 'receiver', [(19.5, 0.9)], 0.85, 0.28, 'R', 'ej')
    studs(g, 'receiver', [(15.0, 0.4), (15.0, -0.6), (23.5, 0.4), (23.5, -0.6), (20.4, -0.7)], 0.13, 0.05, 'RL', tag='rv')
    ridges(g, 'ch_knob', 'T', 18.0, 18.5, 2, 0.1, d=0.03, tag='ck')
    ridges(g, 'rs_base', 'T', 22.4, 23.4, 4, 0.12, cross=(-0.4, 0.4), d=0.03, tag='rb')
    ridges(g, 'magwell', 'RL', 15.2, 17.4, 3, 0.14, cross=(-1.9, -1.2), d=0.035, tag='mw')
    stepped_mag(g, 'mag', 4)
    ridges(g, 'mag_floor', 'B', 14.6, 16.6, 4, 0.18, cross=(-0.45, 0.45), d=0.04, tag='mf')
    stepped_grip(g, 'grip', 4, per=2, d=0.04, width=0.12, inset=0.22)
    ridges(g, 'stock_top', 'T', 25.0, 34.0, 12, 0.22, cross=(-0.45, 0.45), d=0.03, tag='st')
    studs(g, 'stock_hinge', [(24.3, -0.3)], 0.15, 0.05, 'RL', tag='hn')
    ridges(g, 'buttpad', 'K', -2.4, 1.2, 8, 0.14, cross=(-0.5, 0.5), d=0.035, tag='bp', along='b')


def d_famas(g):
    holes(g, 'fh_a', [(0.4, 0.0), (0.8, 0.0)], 0.1, 0.18, 'RL', 'fhh')
    for k in ('gl_ring1', 'gl_ring2'):
        pass
    ridges(g, 'hg', 'RL', -1.5, 0.9, 5, 0.12, cross=(4.4, 12.8), d=0.04, tag='hg', along='b')
    ridges(g, 'hg', 'B', 4.4, 12.8, 9, 0.22, cross=(-0.7, 0.7), d=0.04, tag='hb')
    holes(g, 'body', [(24.0, 0.15)], 0.85, 0.3, 'R', 'ej')
    studs(g, 'body', [(14.0, 0.5), (14.0, -1.6), (33.8, 0.5), (33.8, -1.6), (20.0, -2.0), (28.0, -2.0)], 0.15, 0.05, 'RL',
          tag='rv')
    ridges(g, 'body', 'T', 13.4, 23.6, 10, 0.3, cross=(-0.6, 0.6), d=0.03, tag='bt')
    ridges(g, 'cheek', 'T', 24.2, 32.3, 10, 0.3, cross=(-0.5, 0.5), d=0.035, tag='ck')
    studs(g, 'body_low', [(19.0, -2.7), (33.5, -2.7)], 0.15, 0.05, 'RL', tag='bl')
    ridges(g, 'buttpad', 'K', -3.2, 1.2, 10, 0.14, cross=(-0.8, 0.8), d=0.035, tag='bp', along='b')
    ridges(g, 'bipod_l', 'L', 5.2, 12.0, 6, 0.2, cross=(-0.25, 0.1), d=0.03, tag='bl2')
    ridges(g, 'bipod_r', 'R', 5.2, 12.0, 6, 0.2, cross=(-0.25, 0.1), d=0.03, tag='br2')
    ridges(g, 'mag', 'RL', -6.4, -3.9, 6, 0.14, cross=(18.6, 20.6), d=0.035, tag='mg', along='b')
    stepped_grip(g, 'grip', 4, per=2, d=0.04, width=0.12, inset=0.22)
    ridges(g, 'ch_bar', 'T', 5.5, 22.0, 14, 0.25, cross=(-0.4, 0.4), d=0.035, tag='cb')
    ridges(g, 'rs_top', 'T', 21.6, 21.9, 2, 0.1, d=0.03, tag='rst')
    ridges(g, 'cock_lever', 'T', 13.6, 14.9, 4, 0.12, d=0.03, tag='cl')
    studs(g, 'magwell', [(19.6, -3.4)], 0.12, 0.03, 'RL', tag='mw')


def d_dragunov(g):
    holes(g, 'fh_a', [(0.6, 0.0), (1.2, 0.0), (1.8, 0.0), (2.4, 0.0)], 0.1, 0.2, 'RL', 'fhh')
    for u in (5.0, 8.0, 10.2):
        ring(g, 'brl', (u, u + 0.25), 0.0, 0.33, 'black', pad=0.04)
    ridges(g, 'fs_base', 'T', 4.1, 4.9, 3, 0.1, cross=(-0.3, 0.3), d=0.03, tag='fs')
    studs(g, 'gas_block', [(11.8, 0.4)], 0.14, 0.05, 'RL', tag='gb')
    holes(g, 'hg_upper', [(13.8, 0.85), (15.2, 0.85), (16.6, 0.85), (18.0, 0.85), (19.4, 0.85), (20.8, 0.85), (22.2, 0.85),
                          (23.6, 0.85)], 0.4, 0.14, 'RL', 'hv')
    ridges(g, 'hg_lower', 'RL', -0.9, 0.3, 3, 0.1, cross=(12.9, 24.3), d=0.04, tag='hl', along='b')
    ridges(g, 'hg_lower', 'B', 12.9, 24.3, 9, 0.24, cross=(-0.7, 0.7), d=0.04, tag='hb')
    studs(g, 'hg_retainer', [(24.9, -0.2)], 0.12, 0.05, 'RL', tag='hr')
    ridges(g, 'rs_leaf', 'T', 25.5, 27.1, 7, 0.1, cross=(-0.38, 0.38), d=0.04, mat='parts', tag='rl')
    studs(g, 'receiver', [(26.0, -0.8), (26.0, 0.5), (38.4, -0.8), (38.4, 0.5), (32.0, -1.0)], 0.14, 0.05, 'RL', tag='rv')
    ridges(g, 'cover', 'T', 27.2, 38.6, 12, 0.22, cross=(-0.55, 0.55), d=0.035, tag='cv')
    ridges(g, 'cover', 'RL', 27.2, 38.6, 4, 0.16, cross=(0.95, 1.3), d=0.03, tag='cs')
    ridges(g, 'ch_knob', 'R', 30.7, 31.3, 3, 0.1, cross=(0.2, 0.55), d=0.04, tag='ck')
    ridges(g, 'mount_arm', 'L', 28.7, 32.3, 4, 0.14, cross=(1.7, 2.75), d=0.03, tag='ma')
    studs(g, 'mount_base', [(28.7, 0.6), (32.3, 0.6)], 0.13, 0.05, 'L', tag='mb')
    ridges(g, 'scope_t', 'T', 27.6, 33.8, 8, 0.2, cross=(-0.5, 0.5), d=0.035, tag='sc')
    ridges(g, 'ocular_t', 'T', 34.2, 35.4, 4, 0.14, cross=(-0.6, 0.6), d=0.035, tag='oc')
    ridges(g, 'eyecup_t', 'T', 35.8, 37.4, 5, 0.14, cross=(-0.7, 0.7), d=0.035, tag='ey')
    ridges(g, 'turret_el', 'RL', 4.2, 4.72, 4, 0.07, cross=(30.2, 31.0), d=0.03, tag='kn', along='b')
    ridges(g, 'turret_wi', 'R', 30.2, 31.0, 3, 0.12, cross=(3.0, 3.8), d=0.04, tag='kw')
    ridges(g, 'obj_t', 'T', 26.5, 27.3, 3, 0.14, cross=(-0.7, 0.7), d=0.035, tag='ob')
    stepped_mag(g, 'mag', 3, width=0.2)
    stepped_grip(g, 'grip', 4, per=3, d=0.04, width=0.1, inset=0.2)
    ridges(g, 'cheek', 'T', 43.8, 50.2, 9, 0.26, cross=(-0.5, 0.5), d=0.035, tag='ck')
    studs(g, 'stock_top', [(46.0, 0.6), (53.0, 0.6)], 0.16, 0.045, 'RL', tag='ss')
    ridges(g, 'buttplate', 'K', -6.0, 0.9, 12, 0.14, cross=(-0.65, 0.65), d=0.035, tag='bp', along='b')
    studs(g, 'buttplate', [(0.0, 0.5), (0.0, -5.8)], 0.17, 0.05, 'K', tag='bs')


def d_kar98k(g):
    muzzle_bore(g, 'barrel_a', 0.0, 0.0, 0.12)
    for u in (4.8, 8.0, 14.5, 18.0):
        ring(g, 'brl', (u, u + 0.22), 0.0, 0.33, 'blued', pad=0.04)
    ridges(g, 'fs_hood_top', 'T', 0.75, 1.45, 3, 0.1, cross=(-0.2, 0.2), d=0.03, tag='fh')
    ridges(g, 'nose_cap', 'RL', 2.7, 3.3, 2, 0.1, cross=(-0.8, 0.4), d=0.04, tag='nc')
    ridges(g, 'hg_top', 'T', 9.8, 20.3, 14, 0.2, cross=(-0.35, 0.35), d=0.03, tag='ht')
    studs(g, 'band_front', [(6.5, -0.3)], 0.1, 0.05, 'RL', tag='b1')
    studs(g, 'band_rear', [(12.85, -0.3)], 0.1, 0.05, 'RL', tag='b2')
    ridges(g, 'rs_leaf', 'T', 21.2, 22.7, 7, 0.1, cross=(-0.32, 0.32), d=0.04, mat='parts', tag='rl')
    studs(g, 'receiver', [(23.2, -0.3), (29.5, -0.3), (26.0, 0.3)], 0.12, 0.05, 'RL', tag='rv')
    ridges(g, 'receiver_top', 'T', 23.3, 29.3, 10, 0.2, cross=(-0.24, 0.24), d=0.03, tag='rt')
    holes(g, 'receiver', [(25.5, 0.3)], 0.9, 0.15, 'R', 'ej')
    ridges(g, 'bolt_ball', 'R', 30.1, 30.7, 3, 0.1, cross=(-1.1, -0.6), d=0.04, tag='bb')
    ridges(g, 'shroud', 'T', 32.3, 32.9, 2, 0.1, cross=(-0.2, 0.2), d=0.03, tag='sh')
    ridges(g, 'floorplate', 'B', 24.4, 28.4, 6, 0.2, cross=(-0.32, 0.32), d=0.04, tag='fp')
    ridges(g, 'forend', 'B', 3.6, 22.4, 12, 0.3, cross=(-0.5, 0.5), d=0.035, tag='fb')
    ridges(g, 'wrist', 'RL', 33.2, 35.2, 5, 0.12, cross=(-2.2, -0.2), d=0.03, tag='wr')
    studs(g, 'stock_4', [(40.8, -1.6)], 0.17, 0.045, 'RL', tag='ss')
    ridges(g, 'buttplate', 'K', -4.4, -0.4, 9, 0.14, cross=(-0.6, 0.6), d=0.035, tag='bp', along='b')
    studs(g, 'buttplate', [(0.0, -0.8), (0.0, -4.3)], 0.15, 0.05, 'K', tag='bs')
    studs(g, 'tg_bottom', [(30.2, 0.0)], 0.1, 0.04, 'B', tag='tgs')


def d_spas(g):
    ring(g, 'brl', (3.0, 3.25), 0.0, 0.36, 'black', pad=0.04)
    ridges(g, 'shield', 'T', 1.4, 20.6, 22, 0.24, cross=(-0.38, 0.38), d=0.04, tag='sh')
    holes(g, 'shield', [(3.0, 0.3), (6.0, 0.3), (9.0, 0.3), (12.0, 0.3), (15.0, 0.3), (18.0, 0.3)], 0.5, 0.12, 'RL', 'shv')
    for u in (6.0, 13.0, 19.0, 24.0):
        ring(g, 'mtr', (u, u + 0.25), -0.95, 0.42, 'black', pad=0.04)
    ridges(g, 'forend', 'RL', -1.7, 0.2, 5, 0.12, cross=(12.4, 23.6), d=0.04, tag='fe', along='b')
    ridges(g, 'forend', 'B', 12.4, 23.6, 11, 0.24, cross=(-0.7, 0.7), d=0.04, tag='fb')
    studs(g, 'clamp', [(1.7, -0.5)], 0.13, 0.05, 'RL', tag='cl')
    studs(g, 'receiver', [(27.0, 0.4), (34.5, 0.4), (27.0, -1.1), (34.5, -1.1), (30.5, 0.8)], 0.14, 0.05, 'RL', tag='rv')
    holes(g, 'receiver', [(30.0, 0.35)], 0.8, 0.28, 'R', 'ej')
    ridges(g, 'receiver', 'T', 26.4, 33.0, 8, 0.2, cross=(-0.55, 0.55), d=0.03, tag='rt')
    ridges(g, 'receiver_tail', 'RL', 35.6, 38.2, 4, 0.14, cross=(-1.2, 0.7), d=0.03, tag='rtl')
    ridges(g, 'mode_button', 'B', 24.7, 25.3, 3, 0.1, d=0.03, tag='mb')
    stepped_grip(g, 'grip', 4, per=2, d=0.04, width=0.12, inset=0.22)
    ridges(g, 'stock_bar', 'T', 23.8, 37.2, 12, 0.28, cross=(-0.98, -0.78), d=0.03, tag='sb')
    ridges(g, 'stock_bar', 'L', 24.0, 37.0, 8, 0.24, cross=(0.1, 0.4), d=0.03, tag='sl')
    studs(g, 'stock_hinge', [(37.4, 0.25)], 0.14, 0.05, 'RL', tag='hn')
    ridges(g, 'hook', 'L', 22.0, 22.8, 3, 0.1, cross=(-0.9, -0.65), d=0.03, tag='hk')
    ridges(g, 'rs_base', 'T', 33.4, 34.4, 4, 0.12, cross=(-0.2, 0.2), d=0.03, tag='rb')


def d_asval(g):
    holes(g, 'supp_a', [(1.5, 0.0), (2.5, 0.0), (3.5, 0.0), (4.5, 0.0), (6.5, 0.0), (7.5, 0.0), (8.5, 0.0), (9.5, 0.0),
                        (10.5, 0.0)], 0.14, 0.3, 'RL', 'sph')
    ring(g, 'sup', (0.7, 0.95), 0.0, 1.05, 'black')
    ring(g, 'sup', (10.9, 11.2), 0.0, 1.05, 'black')
    muzzle_bore(g, 'supp_cap_a', 0.0, 0.0, 0.2)
    ridges(g, 'hg', 'RL', -1.0, 0.8, 5, 0.12, cross=(12.4, 21.1), d=0.04, tag='hg', along='b')
    ridges(g, 'hg_top', 'T', 12.6, 20.9, 14, 0.22, cross=(-0.45, 0.45), d=0.035, tag='ht')
    ridges(g, 'hg', 'B', 12.4, 21.1, 8, 0.24, cross=(-0.6, 0.6), d=0.035, tag='hb')
    studs(g, 'fs_base', [(12.85, 1.35)], 0.12, 0.04, 'RL', tag='fb')
    studs(g, 'receiver', [(22.0, -0.8), (22.0, 0.6), (32.5, -0.8), (32.5, 0.6), (27.0, -1.2)], 0.14, 0.05, 'RL', tag='rv')
    holes(g, 'receiver', [(26.0, 0.65)], 0.9, 0.25, 'R', 'ej')
    ridges(g, 'cover', 'T', 22.0, 32.4, 12, 0.24, cross=(-0.5, 0.5), d=0.035, tag='cv')
    ridges(g, 'rail_plate', 'L', 22.2, 30.8, 10, 0.3, cross=(0.2, 0.9), d=0.05, tag='rp')
    ridges(g, 'rs_base', 'T', 23.8, 25.4, 5, 0.14, cross=(-0.4, 0.4), d=0.03, tag='rb')
    ridges(g, 'ch_handle', 'R', 27.2, 28.2, 4, 0.12, cross=(0.55, 0.9), d=0.04, tag='ch')
    ridges(g, 'selector', 'R', 29.4, 31.4, 5, 0.18, d=0.03, tag='sl')
    stepped_mag(g, 'mag', 6, width=0.22)
    ridges(g, 'mag_floor', 'B', 21.8, 26.9, 6, 0.22, cross=(-0.55, 0.55), d=0.04, tag='mf')
    stepped_grip(g, 'grip', 4, per=3, d=0.04, width=0.12, inset=0.22)
    ridges(g, 'grip_cap', 'B', 32.6, 34.8, 4, 0.16, cross=(-0.6, 0.6), d=0.03, tag='gcp')
    studs(g, 'hinge', [(33.7, -0.2)], 0.14, 0.05, 'RL', tag='hn')
    ridges(g, 'stock_top_r', 'R', 34.8, 42.8, 8, 0.24, cross=(0.15, 0.55), d=0.03, mat='steel', tag='sr')
    ridges(g, 'stock_top_l', 'L', 34.8, 42.8, 8, 0.24, cross=(0.15, 0.55), d=0.03, mat='steel', tag='sl')
    ridges(g, 'butt_pad', 'K', -4.2, 0.6, 10, 0.14, cross=(-0.65, 0.65), d=0.035, tag='bp', along='b')


def d_ppsh41(g):
    holes(g, 'brake_a', [(0.5, 0.0), (1.0, 0.0), (1.5, 0.0), (2.0, 0.0), (2.5, 0.0)], 0.1, 0.45, 'RL', 'bh')
    muzzle_bore(g, 'brake_a', 0.0, 0.0, 0.25)
    holes(g, 'jacket_a', [(u + 0.5, v) for u in range(3, 12) for v in (-0.3, 0.3)], 0.2, 0.14, 'RL', 'jh')
    ridges(g, 'receiver_a', 'RL', 13.6, 23.4, 3, 0.4, cross=(-0.65, 0.65), d=0.03, tag='ra')
    studs(g, 'receiver_a', [(13.5, -0.5), (13.5, 0.5), (23.5, -0.5), (23.5, 0.5), (18.0, -0.5), (21.0, 0.5)], 0.13, 0.05, 'RL',
          tag='rv')
    holes(g, 'receiver_a', [(19.0, 0.35)], 1.0, 0.2, 'R', 'ej')
    ridges(g, 'rs_base', 'T', 14.2, 15.8, 6, 0.1, cross=(-0.4, 0.4), d=0.03, tag='rb')
    ridges(g, 'ch_knob', 'R', 18.7, 19.5, 3, 0.1, cross=(0.05, 0.5), d=0.04, tag='ck')
    ridges(g, 'safety', 'R', 21.7, 22.5, 3, 0.1, cross=(-0.4, -0.05), d=0.03, tag='sf')
    ridges(g, 'drum_b', 'RL', 13.9, 17.1, 6, 0.16, cross=(-7.2, -2.2), d=0.04, tag='dr')
    studs(g, 'drum_hub', [(15.5, -4.7)], 0.2, 0.05, 'R', tag='dh')
    ridges(g, 'drum_band', 'RL', 13.0, 18.0, 5, 0.14, cross=(-2.15, -2.05), d=0.03, tag='db')
    ridges(g, 'stock_front', 'RL', 17.8, 24.8, 4, 0.16, cross=(-1.9, -1.1), d=0.03, tag='sf2')
    stepped_grip(g, 'grip', 4, per=3, d=0.04, width=0.12, inset=0.25)
    ridges(g, 'stock_wrist', 'RL', 25.4, 28.6, 4, 0.14, cross=(-2.3, 0.2), d=0.03, tag='wr')
    studs(g, 'stock_4', [(34.4, -1.5)], 0.17, 0.045, 'RL', tag='ss')
    ridges(g, 'butt_plate', 'K', -6.2, -0.6, 10, 0.14, cross=(-0.75, 0.75), d=0.035, tag='bp', along='b')
    studs(g, 'butt_plate', [(0.0, -0.9), (0.0, -5.9)], 0.17, 0.05, 'K', tag='bs')


def d_rpg(g):
    ridges(g, 'fuze_a', 'RL', 0.2, 0.8, 2, 0.12, cross=(-0.25, 0.25), d=0.03, tag='fz')
    for u in (2.0, 4.4):
        ring(g, 'og', (u, u + 0.22), 0.0, 1.1 if u < 3 else 1.7, 'green', pad=0.04)
    ring(g, 'wb', (6.3, 6.55), 0.0, 2.0, 'green', pad=0.04)
    ring(g, 'wb', (9.7, 9.95), 0.0, 2.0, 'green', pad=0.04)
    studs(g, 'war_body_a', [(6.9, 0.0), (10.1, 0.0)], 0.13, 0.05, 'RL', tag='wr')
    for u in (13.7, 15.7):
        ring(g, 'tr', (u, u + 0.22), 0.0, 1.2, 'steel', pad=0.04)
    ridges(g, 'flare_a', 'RL', 11.3, 13.2, 5, 0.12, cross=(-0.8, 0.8), d=0.04, tag='fl')
    ridges(g, 'shield_f_a', 'RL', 17.8, 32.2, 9, 0.2, cross=(-0.9, 0.9), d=0.04, tag='sf')
    ridges(g, 'shield_r_a', 'RL', 38.6, 52.4, 9, 0.2, cross=(-0.9, 0.9), d=0.04, tag='sr')
    for u in (17.2, 24.6, 32.3, 38.2, 45.5, 52.4):
        ring(g, 'sb', (u, u + 0.3), 0.0, 1.5, 'steel', pad=0.04)
    for u in (33.4, 36.6):
        ring(g, 'tm', (u, u + 0.22), 0.0, 1.2, 'steel', pad=0.04)
    ridges(g, 'fgrip', 'RL', -6.7, -1.6, 9, 0.12, cross=(28.5, 31.5), d=0.04, tag='fg', along='b')
    stepped_grip(g, 'pgrip', 4, per=3, d=0.04, width=0.12, inset=0.25)
    studs(g, 'tg_bottom', [(34.3, 0.0)], 0.1, 0.04, 'B', tag='tgs')
    ridges(g, 'rs_base', 'T', 40.6, 42.4, 6, 0.1, cross=(-0.4, 0.4), d=0.03, tag='rb')
    studs(g, 'pgo_a', [(36.0, 2.0), (40.0, 2.0)], 0.13, 0.05, 'RL', tag='pg')
    ridges(g, 'pgo_a', 'T', 34.5, 41.5, 6, 0.2, cross=(-1.9, -1.2), d=0.035, tag='pgt')
    ridges(g, 'pgo_mount', 'T', 35.4, 39.6, 5, 0.2, cross=(-1.6, -0.6), d=0.03, tag='pm')
    ridges(g, 'hammer', 'T', 51.2, 52.2, 3, 0.1, d=0.03, tag='hm')
    ridges(g, 'vent_0_a', 'RL', 55.2, 57.1, 4, 0.14, cross=(-0.9, 0.9), d=0.04, tag='v0')
    ridges(g, 'vent_1_a', 'RL', 57.5, 59.6, 5, 0.14, cross=(-1.1, 1.1), d=0.04, tag='v1')
    ridges(g, 'vent_2_a', 'RL', 60.0, 62.3, 6, 0.14, cross=(-1.35, 1.35), d=0.04, tag='v2')
    ridges(g, 'fgrip_cap', 'B', 28.2, 31.8, 4, 0.16, cross=(-0.7, 0.7), d=0.03, tag='fc')
    ridges(g, 'pgrip_3', 'B', 36.4, 38.6, 4, 0.14, cross=(-0.6, 0.6), d=0.03, tag='pb')


DETAIL = {'ak47': d_ak47, 'm4a1s': d_m4a1s, 'remmington': d_remmington, 'makarov': d_makarov, 'awp': d_awp,
          'mac10': d_mac10, 'm16': d_m16, 'sks': d_sks, 'deagle': d_deagle, 'sw1911': d_sw1911, 'p30': d_p30,
          'mp5': d_mp5, 'uzi': d_uzi, 'sg553': d_sg553, 'famas': d_famas, 'dragunov': d_dragunov, 'kar98k': d_kar98k,
          'spas': d_spas, 'asval': d_asval, 'ppsh41': d_ppsh41, 'glock': d_glock, 'rpg': d_rpg}


def apply(g):
    """Add the extra detail to a freshly built gun (idempotent per gun object)."""
    n0 = len(g.els)
    DETAIL[g.name](g)
    return len(g.els) - n0
