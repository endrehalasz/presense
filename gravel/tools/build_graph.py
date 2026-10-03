import pyarrow.parquet as pq, shapely, numpy as np, pickle
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dem import elev
KX,KY=74900.0,111200.0
t=pq.read_table('segment.parquet',columns=['id','names','subtype','class','subclass','connectors','road_surface','access_restrictions','geometry'])
d={c:t.column(c).to_pylist() for c in ['id','names','subtype','class','subclass','connectors','road_surface','access_restrictions']}
geoms=shapely.from_wkb(t.column('geometry').to_pylist())
BLOCK={'motorway','trunk','steps',None}
def surf_at(rs,f):
    for r in rs or []:
        b=r.get('between')
        if not b or b[0]<=f<=b[1]: return r['value']
    return None
def bike_access(ar,f):
    rules=[]
    for r in ar or []:
        b=r.get('between')
        if b and not (b[0]<=f<=b[1]): continue
        w=r.get('when') or {}
        if w.get('heading') or w.get('during'): continue
        rules.append((r['access_type'],w.get('mode') or [],bool(w.get('using') or w.get('recognized') or w.get('vehicle'))))
    for at,modes,cond in rules:
        if 'bicycle' in modes and at=='designated': return 'designated'
    for at,modes,cond in rules:
        if 'bicycle' in modes and at=='allowed': return 'yes'
    for at,modes,cond in rules:
        if 'bicycle' in modes and at=='denied': return 'no'
    for at,modes,cond in rules:
        if at=='denied' and (not modes or 'vehicle' in modes) and not cond: return 'restricted'
    for at,modes,cond in rules:
        if at=='allowed' and not modes and cond: return 'private'
    return 'yes'
def category(cls,surf):
    paved = surf in ('paved','paving_stones','metal')
    if cls in ('path','footway','bridleway'):
        if paved: return 'asphalt'
        if surf=='gravel': return 'hard'
        return 'trail'
    if paved: return 'asphalt'
    if surf=='gravel': return 'hard'
    if surf=='dirt': return 'loose'
    if surf=='unpaved': return 'hard' if cls in('track','service','unclassified') else 'loose'
    if cls=='track': return 'hard'
    return 'asphalt'
BASE={'cycleway':1.0,'track':1.0,'residential':1.25,'living_street':1.3,'unclassified':1.2,'service':1.35,'tertiary':1.7,'secondary':2.8,'primary':5.0,'pedestrian':2.2,'path':1.8,'footway':3.0,'bridleway':2.5,'unknown':2.5}
nodes={}; ncoord=[]
def nid(cid,x,y):
    if cid not in nodes: nodes[cid]=len(ncoord); ncoord.append((y,x))
    return nodes[cid]
E=[]
for i in range(len(geoms)):
    if d['subtype'][i]!='road' or d['class'][i] in BLOCK: continue
    cls=d['class'][i]; sub=d['subclass'][i]
    c=shapely.get_coordinates(geoms[i])
    if len(c)<2: continue
    seg=np.hypot(np.diff(c[:,0])*KX,np.diff(c[:,1])*KY); cum=np.concatenate([[0],np.cumsum(seg)]); L=cum[-1]
    if L<=0: continue
    cons=sorted(d['connectors'][i] or [],key=lambda k:k['at'])
    if len(cons)<2: continue
    name=(d['names'][i] or {}).get('primary')
    for a,b in zip(cons[:-1],cons[1:]):
        da,db=a['at']*L,b['at']*L
        if db-da<0.5: 
            continue
        inner=c[(cum>da)&(cum<db)]
        pa=np.array([np.interp(da,cum,c[:,0]),np.interp(da,cum,c[:,1])]); pb=np.array([np.interp(db,cum,c[:,0]),np.interp(db,cum,c[:,1])])
        pts=np.vstack([pa,inner,pb]) if len(inner) else np.vstack([pa,pb])
        f=(a['at']+b['at'])/2
        surf=surf_at(d['road_surface'][i],f); acc=bike_access(d['access_restrictions'][i],f)
        if acc=='no': continue
        u=nid(a['connector_id'],*pa); v=nid(b['connector_id'],*pb)
        E.append(dict(u=u,v=v,pts=pts[:,::-1].astype(np.float64),L=db-da,cls=cls,sub=sub,surf=surf,acc=acc,cat=category(cls,surf),name=name))
ncoord=np.array(ncoord)
# egybeeső (<1,5 m) végpontok összevonása – az Overture néha külön connectort ad azonos pontnak
from scipy.spatial import cKDTree
par=np.arange(len(ncoord))
def find(x):
    while par[x]!=x:
        par[x]=par[par[x]]; x=par[x]
    return x
for a,b in cKDTree(np.c_[ncoord[:,0]*KY,ncoord[:,1]*KX]).query_pairs(1.5):
    ra,rb=find(a),find(b)
    if ra!=rb: par[max(ra,rb)]=min(ra,rb)
root=np.array([find(i) for i in range(len(ncoord))])
merged=int((root!=np.arange(len(ncoord))).sum())
for e in E: e['u']=int(root[e['u']]); e['v']=int(root[e['v']])
E=[e for e in E if e['u']!=e['v']]
print('merged nodes',merged)
z=elev(ncoord[:,0],ncoord[:,1])
allp=np.vstack([e['pts'] for e in E]); allz=elev(allp[:,0],allp[:,1]); k=0
for e in E:
    m=len(e['pts']); zz=allz[k:k+m]; k+=m
    dz=np.diff(zz); e['climb']=float((np.abs(dz).sum())/2)
for e in E:
    f=BASE.get(e['cls'],2.5)
    if e['sub']=='driveway': f*=2.0
    if e['sub']=='parking_aisle': f*=2.0
    if e['sub']=='sidewalk': f*=1.6
    if e['acc']=='designated': f*=0.85
    if e['acc']=='private': f*=2.5
    if e['acc']=='restricted': f*=3.0
    if e['cls'] in('track','unclassified','service','path') and e['cat'] in('hard',): f*=0.85
    if e['cls']=='track' and e['cat']=='loose': f*=1.05
    if e['cls'] in('path','footway') and e['cat']=='trail': f*=1.3
    g=abs(z[e['u']]-z[e['v']])/max(e['L'],30)
    if g>0.12: f*=1.4
    if g>0.18: f*=2.5
    e['cost']=e['L']*f+5.0*e['climb']
pickle.dump(dict(nodes=ncoord,z=z,E=E),open('graph.pkl','wb'))
print(len(ncoord),len(E))
