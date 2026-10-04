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
# „könnyű” profil (visszautakhoz): ugyanaz a v2 költség, de a nem aszfaltos utak 1,4× drágábbak
def easy_cost(e):
    base=e['cost']-12.0*e.get('climb',0)
    f=1.0 if e['cat']=='asphalt' else 1.4
    return base*f+14.0*e.get('climb',0)
# „főút-kerülő” profil: a fő- és mellékutak (primary/secondary) 3×/2,2× drágábbak – ahol van
# párhuzamos bringaút/kerékpáros murvaút (pl. Tauernradweg), arra tereli az útvonalat
def nomain_cost(e):
    base=e['cost']-12.0*e.get('climb',0)
    f={'primary':3.0,'trunk':4.0,'secondary':2.2}.get(e['cls'],1.0)
    return base*f+12.0*e.get('climb',0)
_A={'gravel':A}
_COST={'easy':easy_cost,'nomain':nomain_cost}
def matrix(profile):
    if profile not in _A:
        we=np.array([_COST[profile](E[i]) for i in idx])
        _A[profile]=csr_matrix((np.r_[we,we],(np.r_[u[idx],v[idx]],np.r_[v[idx],u[idx]])),shape=(n,n))
    return _A[profile]
def path(a,b,avoid=None,profile='gravel'):
    M=matrix(profile)
    if avoid:
        M=M.copy().tolil()
        for (p,q) in avoid: 
            M[p,q]=M[p,q]*1.6; M[q,p]=M[q,p]*1.6
        M=M.tocsr()
    dist,pred=dijkstra(M,directed=True,indices=a,return_predecessors=True,limit=np.inf)
    if not np.isfinite(dist[b]): raise RuntimeError('no path')
    seq=[b]
    while seq[-1]!=a: seq.append(pred[seq[-1]])
    return seq[::-1]
def route(wps, penalize_reuse=True, profile='gravel', used=None, must=(), spur_max=1500.0):
    """wps: (lat,lon) lista. Visszaad: [(él index, fordított)] lépések + snap távolságok.
    A köztes útpontoknál a zsákutca-kitérőt (be és ugyanott vissza, < spur_max m) levágja,
    kivéve a `must` indexű útpontokat."""
    sn=[snap(*p) for p in wps]
    legs=[]; used=set() if used is None else used
    for (a,da),(b,db) in zip(sn[:-1],sn[1:]):
        seq=path(a,b,avoid=used if (penalize_reuse and used) else None,profile=profile)
        leg=[EDGE[(p,q)] for p,q in zip(seq[:-1],seq[1:])]
        for p,q in zip(seq[:-1],seq[1:]): used.add((p,q))
        legs.append(leg)
    for k in range(len(legs)-1):
        if k+1 in must: continue
        inn, out = legs[k], legs[k+1]; n=0; L=0.0
        while n < min(len(inn), len(out)) and inn[-1-n][0]==out[n][0] and inn[-1-n][1]!=out[n][1]:
            L += E[out[n][0]]['L']; n+=1
        if n and L < spur_max:
            legs[k]=inn[:-n]; legs[k+1]=out[n:]
    steps=[s_ for leg in legs for s_ in leg]
    return steps,[d for _,d in sn]
def geometry(steps):
    pts=[];cats=[];names=[];clss=[]
    for i,r in steps:
        e=E[i]; p=e['pts'][::-1] if r else e['pts']
        if pts: p=p[1:]
        pts.extend(p.tolist()); cats.extend([e['cat']]*len(p)); clss.extend([e['cls']]*len(p)); names.extend([e['name']]*len(p))
    return np.array(pts),cats,clss,names

def edge_ids(steps):
    """pontonként az él indexe (a geometry() pontsorrendjével egyezően)"""
    out=[]
    for i,r in steps:
        m=len(E[i]['pts']); out.extend([i]*(m if not out else m-1))
    return out
