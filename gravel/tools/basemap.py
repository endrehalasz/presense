# -*- coding: utf-8 -*-
"""Offline alaptérkép: SRTM domborzatárnyékolás (Web Mercator) + Overture vektorok.
Futtatás a munkakönyvtárból: python3 basemap.py <gravel mappa>"""
import sys, os, json, math
import numpy as np, shapely, pyarrow.parquet as pq
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dem import elev

OUT = sys.argv[1]
W_, E_, S_, N_ = 12.40, 13.45, 47.45, 47.98
mx = lambda lon: lon
my = lambda lat: math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
inv_my = lambda y: math.degrees(2 * math.atan(math.exp(y)) - math.pi / 2)

# ---------------- hillshade
WPX = 2600
HPX = int(WPX * (my(N_) - my(S_)) / math.radians(E_ - W_))
lons = np.linspace(W_, E_, WPX)
ys = np.linspace(my(N_), my(S_), HPX)
lats = np.array([inv_my(y) for y in ys])
LA, LO = np.meshgrid(lats, lons, indexing='ij')
Z = elev(LA.ravel(), LO.ravel()).reshape(LA.shape)
Z = np.nan_to_num(Z, nan=np.nanmean(Z))
dx = (E_ - W_) / WPX * 74900.0
dy = np.abs(np.gradient(lats)).mean() * 111200.0
gy, gx = np.gradient(Z, dy, dx)
slope = np.arctan(np.hypot(gx, gy) * 1.4)
aspect = np.arctan2(-gx, gy)
az, alt = math.radians(315), math.radians(42)
hs = np.sin(alt) * np.cos(slope) + np.cos(alt) * np.sin(slope) * np.cos(az - aspect)
hs = np.clip(hs, 0, 1)
# hipszometrikus alapszín (völgy: zöldes-krém, magas: kőszürke, csúcs: fehér)
stops = [(300, (214, 226, 196)), (700, (226, 230, 200)), (1100, (230, 222, 196)), (1600, (214, 204, 186)), (2000, (206, 204, 202)), (2500, (244, 244, 246))]
def tint(z):
    out = np.zeros(z.shape + (3,))
    zs = [s[0] for s in stops]
    for c in range(3):
        out[..., c] = np.interp(z, zs, [s[1][c] for s in stops])
    return out
base = tint(Z)
shade = (0.35 + 0.75 * hs)[..., None]
img = np.clip(base * shade, 0, 255).astype(np.uint8)
os.makedirs(f'{OUT}/assets', exist_ok=True)
Image.fromarray(img).save(f'{OUT}/assets/hillshade.jpg', quality=80, optimize=True, progressive=True)
print('hillshade', img.shape, os.path.getsize(f'{OUT}/assets/hillshade.jpg') // 1024, 'kB')

# ---------------- vektorok
def rnd(coords):
    return [[round(y, 4), round(x, 4)] for x, y in coords]

feats = {'water': [], 'river': [], 'road': [], 'rail': []}
t = pq.read_table('themebase_typewater.parquet', columns=['subtype', 'class', 'names', 'geometry'])
for st, cl, nm, g in zip(t['subtype'].to_pylist(), t['class'].to_pylist(), t['names'].to_pylist(), t['geometry'].to_pylist()):
    geom = shapely.from_wkb(g)
    if geom.geom_type in ('Polygon', 'MultiPolygon'):
        if geom.area * 74900 * 111200 < 40000: continue
        geom = shapely.simplify(geom, 0.00025)
        polys = [geom] if geom.geom_type == 'Polygon' else list(geom.geoms)
        for p in polys:
            if p.is_empty: continue
            feats['water'].append(dict(n=(nm or {}).get('primary'), c=rnd(p.exterior.coords)))
    elif geom.geom_type in ('LineString', 'MultiLineString') and st == 'river' and cl in ('river',):
        geom = shapely.simplify(geom, 0.0003)
        for l in ([geom] if geom.geom_type == 'LineString' else geom.geoms):
            feats['river'].append(rnd(l.coords))
t = pq.read_table('segment.parquet', columns=['subtype', 'class', 'geometry'])
RK = {'motorway': 0, 'trunk': 0, 'primary': 1, 'secondary': 2, 'tertiary': 3}
for st, cl, g in zip(t['subtype'].to_pylist(), t['class'].to_pylist(), t['geometry'].to_pylist()):
    if st == 'road' and cl in RK:
        l = shapely.simplify(shapely.from_wkb(g), 0.0002)
        feats['road'].append([RK[cl], rnd(l.coords)])
    elif st == 'rail' and cl == 'standard_gauge':
        l = shapely.simplify(shapely.from_wkb(g), 0.0003)
        feats['rail'].append(rnd(l.coords))
towns = [("Bad Reichenhall", 47.7255, 12.877), ("Salzburg", 47.800, 13.044), ("Freilassing", 47.840, 12.977), ("Berchtesgaden", 47.631, 13.002),
         ("Laufen", 47.938, 12.930), ("Piding", 47.767, 12.913), ("Anger", 47.803, 12.857), ("Teisendorf", 47.849, 12.822), ("Inzell", 47.763, 12.754),
         ("Ruhpolding", 47.764, 12.641), ("Lofer", 47.587, 12.695), ("Unken", 47.647, 12.727), ("Ramsau", 47.606, 12.90), ("Bischofswiesen", 47.652, 12.96),
         ("Hallein", 47.683, 13.097), ("Golling", 47.598, 13.165), ("Abtenau", 47.563, 13.346), ("Grödig", 47.738, 13.035), ("Großgmain", 47.725, 12.910),
         ("Marktschellenberg", 47.697, 13.045), ("Schneizlreuth", 47.690, 12.80), ("Traunstein", 47.869, 12.644), ("Siegsdorf", 47.822, 12.645),
         ("Waging a. See", 47.934, 12.733), ("Oberndorf", 47.942, 12.942), ("Faistenau", 47.775, 13.225), ("Weißbach b. Lofer", 47.522, 12.752)]
peaks = [("Untersberg", 47.718, 13.007, 1973), ("Hochstaufen", 47.756, 12.856, 1771), ("Watzmann", 47.555, 12.922, 2713), ("Predigtstuhl", 47.705, 12.888, 1613),
         ("Zwiesel", 47.756, 12.812, 1782), ("Teisenberg", 47.813, 12.787, 1333), ("Gaisberg", 47.804, 13.112, 1287), ("Hoher Göll", 47.593, 13.066, 2522),
         ("Reiter Alpe", 47.630, 12.800, 2286), ("Sonntagshorn", 47.664, 12.701, 1961), ("Schafberg", 47.777, 13.433, 1783)]
base = dict(bounds=[[S_, W_], [N_, E_]], water=feats['water'], river=feats['river'], road=feats['road'], rail=feats['rail'],
            towns=[dict(n=a, lat=b, lon=c) for a, b, c in towns], peaks=[dict(n=a, lat=b, lon=c, e=d) for a, b, c, d in peaks])
with open(f'{OUT}/basemap.js', 'w', encoding='utf-8') as f:
    f.write('// Offline alaptérkép-vektorok (Overture Maps / OSM, ODbL) – tools/basemap.py\n')
    f.write('window.GRAVEL_BASE=' + json.dumps(base, ensure_ascii=False, separators=(',', ':')) + ';\n')
print('basemap.js', os.path.getsize(f'{OUT}/basemap.js') // 1024, 'kB', {k: len(v) for k, v in feats.items()})
