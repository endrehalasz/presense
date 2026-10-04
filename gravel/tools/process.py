# -*- coding: utf-8 -*-
"""Útvonalak generálása és feldolgozása.

Futtatás a munkakönyvtárból (ahol graph.pkl és a DEM található):
    python3 process.py <kimeneti gravel mappa>
"""
import sys, os, json, math, datetime, collections
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from routes_def import ROUTES, HOTEL, STATIONS, PARKINGS
import router
from dem import elev

OUT = sys.argv[1] if len(sys.argv) > 1 else '.'
KX, KY = 74900.0, 111200.0
CAT_SPEED = {'asphalt': 22.0, 'hard': 17.5, 'loose': 13.5, 'trail': 9.0}
CAT_LABEL = {'asphalt': 'aszfalt', 'hard': 'kemény murva', 'loose': 'laza murva / erdei', 'trail': 'ösvény'}


def hav(a, b):
    return math.hypot((a[0] - b[0]) * KY, (a[1] - b[1]) * KX)


def densify(pts, cats, step=20.0):
    out, oc = [pts[0]], [cats[0]]
    for i in range(1, len(pts)):
        d = hav(pts[i - 1], pts[i])
        k = int(d // step)
        for j in range(1, k + 1):
            f = j * step / d
            if f < 1:
                out.append(pts[i - 1] + (pts[i] - pts[i - 1]) * f); oc.append(cats[i])
        out.append(pts[i]); oc.append(cats[i])
    return np.array(out), oc


def smooth(z, d, win=120.0):
    """távolság-alapú mozgóátlag (±win/2)"""
    zs = np.empty_like(z)
    j0 = j1 = 0
    cs = np.concatenate([[0], np.cumsum(z)])
    for i in range(len(z)):
        while d[j0] < d[i] - win / 2: j0 += 1
        while j1 < len(z) and d[j1] <= d[i] + win / 2: j1 += 1
        zs[i] = (cs[j1] - cs[j0]) / (j1 - j0)
    return zs


def ascent(z, thr=3.0):
    up = dn = 0.0; ref = z[0]
    for v in z[1:]:
        if v - ref >= thr: up += v - ref; ref = v
        elif ref - v >= thr: dn += ref - v; ref = v
    return up, dn


def climbs(d, z, dip=15.0, min_gain=40.0):
    """emelkedők: felfelé tartó szakaszok, max `dip` m visszaeséssel"""
    res = []; i = 0; n = len(z)
    while i < n - 1:
        lo = i; hi = i; j = i
        while j < n - 1:
            j += 1
            if z[j] > z[hi]: hi = j
            if z[hi] - z[j] > dip: break
        if z[hi] - z[lo] >= min_gain and d[hi] > d[lo]:
            res.append(dict(start=d[lo], end=d[hi], gain=z[hi] - z[lo], len=d[hi] - d[lo], grade=(z[hi] - z[lo]) / (d[hi] - d[lo]) * 100))
            i = hi
        else:
            i = max(j, i + 1) if z[j] < z[lo] else i + 1
    return res


HARD_GAIN, HARD_GRADE = 250.0, 8.0


def find_climbs(d, z, dip=15.0):
    """ClimbPro-szerű emelkedő-felismerés: helyi minimumtól a csúcsig, max. `dip` (vagy a
    nyereség 10%-a) visszaeséssel; legalább 30 m szint, 400 m hossz és 3% átlag."""
    res = []; i = 0; n = len(z)
    while i < n - 1:
        while i < n - 1 and z[i + 1] <= z[i]: i += 1
        s = top = j = i
        while j < n - 1:
            j += 1
            if z[j] > z[top]: top = j
            elif z[top] - z[j] > max(dip, 0.1 * (z[top] - z[s])): break
        gain = z[top] - z[s]; L = d[top] - d[s]
        if gain >= 30 and L >= 400 and gain / L >= 0.03:
            res.append((s, top))
        i = top + 1 if top > s else j
    out = []
    for k, (s, e) in enumerate(res, 1):
        L = d[e] - d[s]; gain = z[e] - z[s]; avg = gain / L * 100
        # max meredekség 300 m-es ablakban (a 30 m-es DEM zaja miatt nem rövidebben)
        mx = 0.0; j = s
        for a in range(s, e):
            while j < e and d[j] - d[a] < 300: j += 1
            if d[j] - d[a] >= 250: mx = max(mx, (z[j] - z[a]) / (d[j] - d[a]) * 100)
        why = []
        if gain >= HARD_GAIN: why.append('hosszú')
        if avg >= HARD_GRADE and gain >= 50: why.append('meredek')
        steps = np.arange(d[s], d[e] + 1e-6, 100.0)
        if steps[-1] < d[e]: steps = np.r_[steps, d[e]]
        prof = np.interp(steps, d[s:e + 1], z[s:e + 1])
        out.append(dict(n=k, s=round(d[s] / 1000, 2), e=round(d[e] / 1000, 2), len=round(L / 1000, 2), gain=int(round(gain)),
                        avg=round(avg, 1), max=round(max(mx, avg), 1), bot=int(z[s]), top=int(z[e]), hard=bool(why), why=why,
                        prof=[int(round(v)) for v in prof]))
    return out


def steepest(d, z, win=500.0):
    best = (0, 0); j = 0
    for i in range(len(d)):
        while j < len(d) - 1 and d[j] - d[i] < win: j += 1
        if d[j] - d[i] >= win * 0.9:
            g = (z[j] - z[i]) / (d[j] - d[i]) * 100
            if g > best[0]: best = (g, d[i])
    return best


def dp_mask(xy, tol):
    n = len(xy); keep = np.zeros(n, bool); keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        a, b = stack.pop()
        if b <= a + 1: continue
        p, q = xy[a], xy[b]; seg = q - p; L = np.hypot(*seg)
        r = xy[a + 1:b] - p
        dist = np.abs(seg[0] * r[:, 1] - seg[1] * r[:, 0]) / L if L > 0 else np.hypot(r[:, 0], r[:, 1])
        k = int(np.argmax(dist))
        if dist[k] > tol:
            m = a + 1 + k; keep[m] = True; stack += [(a, m), (m, b)]
    return keep


def gmaps(lat, lon):
    return f"https://www.google.com/maps/search/?api=1&query={lat:.5f},{lon:.5f}"


def esc(s):
    return (s or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


routes_out = []
for R in ROUTES:
    # útpont-szabály: tó/kilátó/szurdok/történelmi pont alapból csak kiemelt pont ('hl'), kivéve ha 'via'-val jelölt;
    # település, állomás, kunyhó, hágó és a névtelen pontok útpontok
    def is_via(w):
        if len(w) >= 5: return w[4] == 'via'
        return len(w) < 4 or w[3] not in ('lake', 'view', 'gorge', 'history')
    vw = [w for w in R['wps'] if is_via(w)]
    if vw[0] is not R['wps'][0]: vw.insert(0, R['wps'][0])
    if vw[-1] is not R['wps'][-1]: vw.append(R['wps'][-1])
    # felesleges településközpont-kitérő kiszűrése: ha a 'town' útpont kihagyásával a nyomvonal
    # 0,3–3 km-rel rövidebb (be a központba, majd vissza ugyanoda), kihagyjuk (kiemelt pont marad)
    k_ = 1; skipped = []
    while k_ < len(vw) - 1:
        w = vw[k_]
        if len(w) >= 4 and w[3] == 'town' and not (len(w) >= 5 and w[4] == 'via'):
            a_, b_ = router.snap(*vw[k_-1][:2])[0], router.snap(*vw[k_+1][:2])[0]; m_ = router.snap(*w[:2])[0]
            Lp = lambda sq: sum(router.E[router.EDGE[(p_, q_)][0]]['L'] for p_, q_ in zip(sq[:-1], sq[1:]))
            if a_ != b_:
                via_len = Lp(router.path(a_, m_)) + Lp(router.path(m_, b_)); dir_len = Lp(router.path(a_, b_))
                if 300 < via_len - dir_len < 3000:
                    skipped.append((w[2], round((via_len - dir_len) / 1000, 1))); vw.pop(k_); continue
        k_ += 1
    if skipped: print('   kihagyott központ-kitérők:', skipped)
    wps = [w[:2] for w in vw]
    steps, snapd = router.route(wps)
    if R.get('wps_back'):
        # visszaút könnyű profillal; az odaúton használt éleket kerüli
        used = set()
        for i, rv in steps:
            e = router.E[i]; used.add((e['u'], e['v']) if not rv else (e['v'], e['u']))
        used |= {(q, p) for p, q in used}
        back, snapb = router.route([wps[-1]] + [w[:2] for w in R['wps_back']], profile='easy', used=used)
        steps += back; snapd += snapb
    pts, cats, clss, names = router.geometry(steps)
    eids0 = router.edge_ids(steps)
    pts_raw = pts
    pts, cats = densify(pts, cats)
    # élindex a sűrített pontokhoz (legközelebbi eredeti pont alapján, sorrendben)
    from scipy.spatial import cKDTree as _KD
    _t = _KD(np.c_[pts_raw[:, 0] * KY, pts_raw[:, 1] * KX]); _, _j = _t.query(np.c_[pts[:, 0] * KY, pts[:, 1] * KX])
    eids = [eids0[min(j, len(eids0) - 1)] for j in _j]
    seglen = np.r_[0, np.hypot(np.diff(pts[:, 0]) * KY, np.diff(pts[:, 1]) * KX)]
    d = np.cumsum(seglen)
    zr = elev(pts[:, 0], pts[:, 1])
    z = smooth(zr, d, 200.0)
    up, dn = ascent(z, 4.0)
    # --- tolós szakaszok: menetirányban felfelé; 200 m simítás + 250 m ablak (barométeren kalibrálva);
    #     aszfalton >12%, murván/földúton >10%
    z100 = smooth(zr, d, 200.0)
    gwin = np.zeros(len(d)); j = 0
    for a_ in range(len(d)):
        while j < len(d) - 1 and d[j] - d[a_] < 250: j += 1
        gwin[a_] = (z100[j] - z100[a_]) / max(1.0, d[j] - d[a_]) * 100
    lim = np.array([12.0 if c == 'asphalt' else 10.0 for c in cats])
    pushm = gwin > lim
    pushes = []; a_ = None
    for k_ in range(len(d)):
        if pushm[k_] and a_ is None: a_ = k_
        if (not pushm[k_] or k_ == len(d) - 1) and a_ is not None:
            e_ = k_
            j = e_
            while j < len(d) - 1 and d[j] - d[e_] < 250: j += 1   # az ablak végéig tart
            if pushes and d[a_] - pushes[-1][1] < 100: pushes[-1][1] = d[j]; pushes[-1][3] = max(pushes[-1][3], gwin[a_:e_+1].max())
            else: pushes.append([d[a_], d[j], cats[a_], float(gwin[a_:e_+1].max())])
            a_ = None
    pushes = [dict(s=round(p_[0]/1000, 2), e=round(p_[1]/1000, 2), len=int(p_[1]-p_[0]), surf=('aszfalt' if p_[2]=='asphalt' else 'murva/földút'), max=round(p_[3], 1)) for p_ in pushes if p_[1]-p_[0] >= 80]
    # --- ellenőrző metrikák
    EE = router.E
    def km_where(fn): return sum(L for L, ei in zip(np.r_[np.diff(d), 0], eids) if fn(EE[ei])) / 1000
    bike_km = km_where(lambda e: e.get('bikeway'))
    main_km = km_where(lambda e: e['cls'] in ('primary', 'secondary'))
    tert_km = km_where(lambda e: e['cls'] == 'tertiary')
    bad_track_km = km_where(lambda e: e['cls'] == 'track' and e['cat'] != 'asphalt' and e['surf'] != 'gravel')
    trail_runs = []; cur = 0.0
    for L, ei in zip(np.r_[np.diff(d), 0], eids):
        e = EE[ei]
        if e['cls'] in ('path', 'footway', 'bridleway') and not e.get('bikeway') and e['cat'] in ('trail', 'loose'): cur += L
        else:
            if cur: trail_runs.append(cur); cur = 0.0
    if cur: trail_runs.append(cur)
    flat_pct = float(np.mean(np.abs(gwin) < 2.0) * 100)
    steep_m = float(np.sum(np.r_[np.diff(d), 0][np.abs(gwin) > 10]))
    # hurok/visszatérés: a nyomvonal 40 m-en belül visszaér egy 0,4–4 km-rel korábbi pontra
    loops = []
    _kd = _KD(np.c_[pts[:, 0] * KY, pts[:, 1] * KX])
    for a_ in range(0, len(d), 5):
        for b_ in _kd.query_ball_point([pts[a_, 0] * KY, pts[a_, 1] * KX], 40):
            if 400 < d[b_] - d[a_] < 4000:
                seg_e = set(eids[a_:b_])
                # csak ha a közbenső rész jórészt más éleken fut, mint az oda-vissza (valódi kitérő/hurok)
                back = sum(1 for x in seg_e if eids.count(x) > 1) / max(1, len(seg_e))
                if back < 0.6: loops.append((round(d[a_]/1000, 1), round(d[b_]/1000, 1)))
                break
    # összevonás
    lp = []
    for x in loops:
        if lp and x[0] - lp[-1][1] < 0.3 or (lp and x[0] <= lp[-1][1]): lp[-1] = (lp[-1][0], max(lp[-1][1], x[1]))
        else: lp.append(x)
    review = dict(bikeKm=round(bike_km, 1), mainKm=round(main_km, 1), tertKm=round(tert_km, 1), badTrackKm=round(bad_track_km, 1),
                  trailMax=int(max(trail_runs) if trail_runs else 0), trailKm=round(sum(trail_runs)/1000, 2), flatPct=round(flat_pct),
                  steepM=int(steep_m), pushM=int(sum(p_['len'] for p_ in pushes)), loops=lp[:12])
    climbs_list = find_climbs(d, z)
    lc = max(climbs_list, key=lambda c: c['gain']) if climbs_list else None
    longest = dict(start=lc['s'] * 1000, len=lc['len'] * 1000, gain=lc['gain'], grade=lc['avg']) if lc else None
    st_g, st_at = steepest(d, z)
    surf = collections.Counter()
    for c, L in zip(cats, seglen): surf[c] += L
    tot = d[-1]
    surfpct = {k: round(surf[k] / tot * 100, 1) for k in CAT_SPEED}
    gravel_pct = round(surfpct['hard'] + surfpct['loose'] + surfpct['trail'], 1)
    t_h = sum(surf[k] / 1000 / CAT_SPEED[k] for k in CAT_SPEED) + up / 650.0
    km = tot / 1000
    # nehézség
    score = km / 12 + up / 160 + (surfpct['loose'] + surfpct['trail'] * 2) / 25 + max(0, st_g - 10) / 2
    rough = surfpct['loose'] + surfpct['trail']
    if up >= 1300 or km >= 85 or (up >= 1000 and rough >= 30) or z.max() >= 1300:
        diff = 'nehez'
    elif up <= 550 and km <= 50 and surfpct['trail'] <= 8:
        diff = 'konnyu'
    else:
        diff = 'kozepes'
    halfday = km <= 80 and up <= 1100
    # szállodából?
    start = pts[0]; end = pts[-1]
    hotel_d = hav(start, HOTEL) / 1000
    loop = hav(start, end) < 500
    # egyszerűsítés ~10 m
    xy = np.c_[pts[:, 1] * KX, pts[:, 0] * KY]
    keep = dp_mask(xy, 10.0)
    # magassági profil pontjai: DP pontok + 150 m-enként (hogy a profil sima maradjon)
    last = -1e9
    for i in range(len(d)):
        if d[i] - last >= 150: keep[i] = True; last = d[i]
        if keep[i]: last = d[i]
    idx = np.where(keep)[0]
    track = [[round(pts[i, 0], 5), round(pts[i, 1], 5), round(float(z[i]), 0), round(d[i] / 1000, 3)] for i in idx]
    # burkolati sávok
    sb = []
    for i in range(1, len(d)):
        c = cats[i]
        if sb and sb[-1][2] == c: sb[-1][1] = d[i] / 1000
        else: sb.append([d[i - 1] / 1000, d[i] / 1000, c])
    # apró (<150 m) szakaszok összevonása a szomszéddal
    merged = []
    for s in sb:
        if merged and (s[1] - s[0]) < 0.15: merged[-1][1] = s[1]
        else: merged.append(s)
    sb = [[round(a, 2), round(b, 2), c] for a, b, c in merged]
    # kiemelt pontok
    hl = []
    for w in R['wps'] + R.get('wps_back', []):
        if len(w) >= 4:
            k = int(np.argmin((pts[:, 0] - w[0]) ** 2 * KY ** 2 + (pts[:, 1] - w[1]) ** 2 * KX ** 2))
            off = hav(pts[k], w[:2])
            hl.append(dict(name=w[2], type=w[3], lat=round(w[0], 5), lon=round(w[1], 5), km=round(d[k] / 1000, 1), off=round(off)))
    # ismételt (oda-vissza) szakaszok aránya
    used = collections.Counter(i for i, _ in steps)
    rep = sum(router.E[i]['L'] for i, c in used.items() if c > 1) / tot * 100
    # indulási módok
    starts = []
    if hotel_d <= 3:
        starts.append(dict(mode='hotel', text=f"A szállodától indul ({hotel_d:.1f} km)" if hotel_d > 0.3 else "Közvetlenül a szálloda elől indul"))
    if R.get('car'):
        p = PARKINGS[R['car']]
        starts.append(dict(mode='car', name=p[0], lat=p[1], lon=p[2], min=p[3], text=f"Autóval ~{p[3]} perc: {p[0]}"))
    if R.get('train'):
        sk, note = R['train']; s = STATIONS[sk]
        txt = f"Vonattal: {s[0]}" + (f" (~{s[3]} perc Bad Reichenhall Hbf-ről)" if s[3] else " (gyalog/bringával 0,5 km a szállodától)")
        starts.append(dict(mode='train', name=s[0], lat=s[1], lon=s[2], min=s[3], text=txt, note=note))
    r = dict(id=R['id'], name=R['name'], creative=R['creative'], rating=R['rating'], desc=R['desc'],
             km=round(km, 1), up=int(round(up)), down=int(round(dn)), maxEle=int(z.max()), minEle=int(z.min()),
             timeH=round(t_h, 2), difficulty=diff, score=round(score, 1), halfday=bool(halfday), loop=bool(loop),
             gravel=gravel_pct, surface=surfpct, surfBands=sb,
             longestClimb=dict(km=round(longest['start'] / 1000, 1), len=round(longest['len'] / 1000, 1), gain=int(longest['gain']), grade=round(longest['grade'], 1)) if longest else None,
             climbs=climbs_list, hardClimbs=sum(c['hard'] for c in climbs_list), pushes=pushes, review=review,
             steepest=dict(grade=round(st_g, 1), km=round(st_at / 1000, 1)),
             hotelKm=round(hotel_d, 1), fromHotel=bool(hotel_d <= 3),
             starts=starts, highlights=hl, warn=R['warn'], photos=R['photos'],
             inspired=R.get('inspired'), variantOf=R.get('variant_of'), generated=True, repeatPct=round(rep, 1),
             snapMax=int(max(snapd)), track=track,
             gmaps=f"https://www.google.com/maps/dir/?api=1&origin={pts[0,0]:.5f},{pts[0,1]:.5f}&destination={pts[-1,0]:.5f},{pts[-1,1]:.5f}&travelmode=bicycling&waypoints=" + "%7C".join(f"{w[0]:.5f},{w[1]:.5f}" for w in (lambda l: l[::max(1, -(-len(l) // 9))])((R['wps'] + R.get('wps_back', []))[1:-1])))
    routes_out.append(r)
    rv = review
    print(f"{R['id']:24s} {km:6.1f}km {up:5.0f}m max{z.max():5.0f} | bringaút {rv['bikeKm']:5.1f} főút {rv['mainKm']:4.1f} rossz-erdei {rv['badTrackKm']:4.1f} ösvény max {rv['trailMax']:4d}m | tolós {rv['pushM']:4d}m ({len(pushes)}) sík {rv['flatPct']:2d}% | hurok {rv['loops']}")

    # GPX
    gx = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<gpx version="1.1" creator="Bad Reichenhall gravel – saját gravel-router (OSM/Overture + SRTM)" xmlns="http://www.topografix.com/GPX/1/1">',
          f'<metadata><name>{esc(R["name"])}</name><desc>GENERÁLT NYOMVONAL – {esc(R["desc"])}</desc>'
          f'<copyright author="OpenStreetMap contributors (via Overture Maps)"><license>https://opendatacommons.org/licenses/odbl/</license></copyright>'
          f'<time>{datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")}</time></metadata>']
    for h in hl:
        gx.append(f'<wpt lat="{h["lat"]}" lon="{h["lon"]}"><name>{esc(h["name"])}</name><type>{h["type"]}</type></wpt>')
    gx.append(f'<trk><name>{esc(R["name"])}</name><type>gravel</type><trkseg>')
    for i in idx:
        gx.append(f'<trkpt lat="{pts[i,0]:.6f}" lon="{pts[i,1]:.6f}"><ele>{zr[i]:.1f}</ele></trkpt>')
    gx.append('</trkseg></trk></gpx>')
    os.makedirs(f'{OUT}/gpx', exist_ok=True)
    open(f'{OUT}/gpx/{R["id"]}.gpx', 'w', encoding='utf-8').write('\n'.join(gx))

# ---------------------------------------------------------------- KML
COL = {'konnyu': 'ff3fa34a', 'kozepes': 'ff1c8de0', 'nehez': 'ff3c2bc8'}  # aabbggrr
DIFF_HU = {'konnyu': 'könnyű', 'kozepes': 'közepes', 'nehez': 'nehéz'}
k = ['<?xml version="1.0" encoding="UTF-8"?>', '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>',
     '<name>Gravel útvonalak – Bad Reichenhall</name>',
     '<description>Generált nyomvonalak (saját gravel-router, OSM-adatok az Overture Maps-en keresztül, ODbL; magasság: SRTM). Október eleji tervezéshez.</description>']
for dk, c in COL.items():
    k.append(f'<Style id="{dk}"><LineStyle><color>{c}</color><width>4</width></LineStyle></Style>')
k.append('<Style id="poi"><IconStyle><scale>0.8</scale></IconStyle></Style>')
k.append(f'<Placemark><name>Alpenstadthotels (szálloda)</name><Point><coordinates>{HOTEL[1]},{HOTEL[0]}</coordinates></Point></Placemark>')
for r in routes_out:
    s = r['surface']
    desc = (f"<b>{esc(r['name'])}</b> – GENERÁLT NYOMVONAL<br/>{esc(r['desc'])}<br/><br/>"
            f"Táv: {r['km']} km · Szint: {r['up']} m · Max: {r['maxEle']} m · Idő: ~{r['timeH']:.1f} ó<br/>"
            f"Nehézség: {DIFF_HU[r['difficulty']]} · Értékelés: {'★'*r['rating']}{'☆'*(5-r['rating'])}<br/>"
            f"Burkolat: aszfalt {s['asphalt']}%, kemény murva {s['hard']}%, laza/erdei {s['loose']}%, ösvény {s['trail']}%<br/>"
            f"Indulás: {esc(' | '.join(x['text'] for x in r['starts']))}<br/>"
            f"Október: {esc(' '.join(r['warn']))}")
    k.append(f'<Placemark><name>{esc(r["name"])} ({r["km"]} km, {r["up"]} m)</name><description><![CDATA[{desc}]]></description>'
             f'<styleUrl>#{r["difficulty"]}</styleUrl><LineString><tessellate>1</tessellate><coordinates>'
             + ' '.join(f'{p[1]},{p[0]},{int(p[2])}' for p in r['track']) + '</coordinates></LineString></Placemark>')
k.append('</Document></kml>')
open(f'{OUT}/gravel_utvonalak.kml', 'w', encoding='utf-8').write('\n'.join(k))

# ---------------------------------------------------------------- data.js
data = dict(generatedAt=datetime.date.today().isoformat(),
            hotel=dict(name='Alpenstadthotels', addr='Adolf-Schmid-Straße 2, 83435 Bad Reichenhall', lat=HOTEL[0], lon=HOTEL[1]),
            stations=[dict(id=k2, name=v[0], lat=v[1], lon=v[2], min=v[3]) for k2, v in STATIONS.items()],
            parkings=[dict(id=k2, name=v[0], lat=v[1], lon=v[2], min=v[3]) for k2, v in PARKINGS.items()],
            routes=routes_out)
with open(f'{OUT}/data.js', 'w', encoding='utf-8') as f:
    f.write('// Automatikusan generálva: tools/process.py – ne szerkeszd kézzel.\n')
    f.write('window.GRAVEL = ' + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + ';\n')
print('OK', len(routes_out), 'route; data.js', os.path.getsize(f'{OUT}/data.js') // 1024, 'kB')
