import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt, numpy as np
from router import E
_bg=None
def plot(tracks,fn,pad=0.02):
    allp=np.vstack([t for t in tracks]); la0,la1=allp[:,0].min()-pad,allp[:,0].max()+pad; lo0,lo1=allp[:,1].min()-pad,allp[:,1].max()+pad
    fig,ax=plt.subplots(figsize=(10,10*(la1-la0)*111/((lo1-lo0)*75)))
    col={'primary':'#d33','secondary':'#e80','tertiary':'#cc0','track':'#963','path':'#090','cycleway':'#00f'}
    for e in E:
        p=e['pts']
        if p[:,0].max()<la0 or p[:,0].min()>la1 or p[:,1].max()<lo0 or p[:,1].min()>lo1: continue
        ax.plot(p[:,1],p[:,0],color=col.get(e['cls'],'#bbb'),lw=0.4)
    for t,c in zip(tracks,['#f0f','#0cf','#0a0','#fa0']): ax.plot(t[:,1],t[:,0],color=c,lw=2.2,alpha=.8)
    ax.set_xlim(lo0,lo1); ax.set_ylim(la0,la1); ax.set_aspect(111/75); fig.savefig(fn,dpi=90,bbox_inches='tight'); plt.close(fig)
