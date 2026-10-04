import sys,json,numpy as np
sys.path.insert(0,'/home/user/presense/gravel/tools'); import router
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra
E=router.E; idx=router.idx; n=router.n
ok=[i for i in idx if not (E[i]['cls'] in('path','footway','bridleway') and not E[i].get('bikeway') and E[i]['cat'] in('trail','loose'))]
ok=np.array(ok)
uu=np.array([E[i]['u'] for i in ok]); vv=np.array([E[i]['v'] for i in ok]); L=np.array([E[i]['L'] for i in ok]); C=np.array([E[i]['climb'] for i in ok])
A=csr_matrix((np.r_[L,L],(np.r_[uu,vv],np.r_[vv,uu])),shape=(n,n))
CL={}
for i in ok: CL[(E[i]['u'],E[i]['v'])]=E[i]['climb']; CL[(E[i]['v'],E[i]['u'])]=E[i]['climb']
d=json.loads(open(sys.argv[1]).read().split('= ',1)[1].rstrip(';\n'))
ids=sys.argv[2:]
for r in d['routes']:
    if ids and r['id'] not in ids: continue
    t=np.array([p[:4] for p in r['track']]); km=t[:,3]; z=t[:,2]
    samp=np.arange(0,km[-1],0.5); si=[int(np.abs(km-k).argmin()) for k in samp]
    nodes=[router.snap(t[i,0],t[i,1])[0] for i in si]
    flags=[]
    for a in range(len(si)):
        dist,pred=dijkstra(A,indices=nodes[a],return_predecessors=True,limit=9000)
        for b in range(a+4,min(len(si),a+17)):
            nb=nodes[b]
            if not np.isfinite(dist[nb]) or nb==nodes[a]: continue
            rl=(km[si[b]]-km[si[a]])*1000
            seg=z[si[a]:si[b]+1]; rc=np.clip(np.diff(seg),0,None).sum()
            # alt climb
            ac=0; x=nb
            while x!=nodes[a] and x>=0:
                p=pred[x]; ac+=CL.get((p,x),0); x=p
            if rl>1.2*dist[nb]+300 and rc>ac+35:
                flags.append((round(km[si[a]],1),round(km[si[b]],1),int(rl),int(dist[nb]),int(rc),int(ac)))
    # merge overlapping
    m=[]
    for f in flags:
        if m and f[0]<=m[-1][1]: 
            if f[2]-f[3] > m[-1][2]-m[-1][3]: m[-1]=(m[-1][0],f[1],f[2],f[3],f[4],f[5])
            else: m[-1]=(m[-1][0],max(m[-1][1],f[1]))+m[-1][2:]
        else: m.append(f)
    print(f"{r['id']:26s}", ' '.join(f"[{a}-{b}km út {rl/1000:.1f} vs {al/1000:.1f} km, szint {rc} vs {ac} m]" for a,b,rl,al,rc,ac in m) or 'OK')
