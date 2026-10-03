import pickle, os, numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra, connected_components
from scipy.spatial import cKDTree
G=pickle.load(open(os.environ.get('GRAPH','graph.pkl'),'rb'))
N=G['nodes']; E=G['E']; n=len(N)
u=np.array([e['u'] for e in E]); v=np.array([e['v'] for e in E]); w=np.array([e['cost'] for e in E])
# keep cheapest parallel edge
best={}
for i,e in enumerate(E):
    k=(min(e['u'],e['v']),max(e['u'],e['v']))
    if k not in best or E[best[k]]['cost']>e['cost']: best[k]=i
idx=np.array(list(best.values()))
A=csr_matrix((np.r_[w[idx],w[idx]],(np.r_[u[idx],v[idx]],np.r_[v[idx],u[idx]])),shape=(n,n))
ncomp,lab=connected_components(A,directed=False)
main=np.bincount(lab).argmax()
ok=np.where(lab==main)[0]
tree=cKDTree(np.c_[N[ok,0]*111.2,N[ok,1]*74.9])
def snap(lat,lon):
    d,i=tree.query([lat*111.2,lon*74.9]); return ok[i],d*1000
EDGE={}
for i in idx:
    e=E[i]; EDGE[(e['u'],e['v'])]=(i,False); EDGE[(e['v'],e['u'])]=(i,True)
# „könnyű” profil (visszautakhoz): kerékpárút és kis forgalmú aszfalt előnyben, murva/ösvény, főút és emelkedő büntetve
EASY_BASE={'cycleway':0.8,'residential':1.0,'living_street':1.1,'unclassified':1.0,'service':1.2,'track':1.25,'tertiary':1.6,'secondary':3.2,'primary':6.0,'pedestrian':2.0,'path':2.2,'footway':3.0,'bridleway':3.0,'unknown':3.0}
EASY_CAT={'asphalt':1.0,'hard':1.25,'loose':2.0,'trail':3.5}
def easy_cost(e):
    f=EASY_BASE.get(e['cls'],3.0)*EASY_CAT[e['cat']]
    if e['acc']=='designated': f*=0.75
    if e.get('sub')=='driveway': f*=2.0
    if e['acc'] in('private','restricted'): f*=3.0
    return e['L']*f+9.0*e.get('climb',0)
_A={'gravel':A}
def matrix(profile):
    if profile not in _A:
        we=np.array([easy_cost(E[i]) for i in idx])
        _A[profile]=csr_matrix((np.r_[we,we],(np.r_[u[idx],v[idx]],np.r_[v[idx],u[idx]])),shape=(n,n))
    return _A[profile]
def path(a,b,avoid=None,profile='gravel'):
    M=matrix(profile)
    if avoid:
        M=M.copy().tolil()
        for (p,q) in avoid: 
            M[p,q]=M[p,q]*4; M[q,p]=M[q,p]*4
        M=M.tocsr()
    dist,pred=dijkstra(M,directed=True,indices=a,return_predecessors=True,limit=np.inf)
    if not np.isfinite(dist[b]): raise RuntimeError('no path')
    seq=[b]
    while seq[-1]!=a: seq.append(pred[seq[-1]])
    return seq[::-1]
def route(wps, penalize_reuse=True, profile='gravel', used=None):
    """wps: list of (lat,lon). returns list of edge-steps [(edge_index,reversed)] and snap info"""
    sn=[snap(*p) for p in wps]
    steps=[]; used=set() if used is None else used
    for (a,da),(b,db) in zip(sn[:-1],sn[1:]):
        seq=path(a,b,avoid=used if (penalize_reuse and used) else None,profile=profile)
        for p,q in zip(seq[:-1],seq[1:]):
            steps.append(EDGE[(p,q)]); used.add((p,q))
    return steps,[d for _,d in sn]
def geometry(steps):
    pts=[];cats=[];names=[];clss=[]
    for i,r in steps:
        e=E[i]; p=e['pts'][::-1] if r else e['pts']
        if pts: p=p[1:]
        pts.extend(p.tolist()); cats.extend([e['cat']]*len(p)); clss.extend([e['cls']]*len(p)); names.extend([e['name']]*len(p))
    return np.array(pts),cats,clss,names
