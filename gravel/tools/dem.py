import numpy as np, os
RAW=os.environ.get('DEM_DIR', os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','raw'))
_t={}
def tile(lat0,lon0):
    k=(lat0,lon0)
    if k not in _t:
        a=np.fromfile(f'{RAW}/N{lat0:02d}E{lon0:03d}.hgt','>i2').reshape(3601,3601).astype(np.float32)
        a[a<-1000]=np.nan; _t[k]=a
    return _t[k]
def elev(lat,lon):
    lat=np.asarray(lat,float); lon=np.asarray(lon,float); out=np.empty(lat.shape)
    for la0 in np.unique(np.floor(lat)).astype(int):
        for lo0 in np.unique(np.floor(lon)).astype(int):
            m=(np.floor(lat)==la0)&(np.floor(lon)==lo0)
            if not m.any(): continue
            a=tile(la0,lo0)
            r=(la0+1-lat[m])*3600; c=(lon[m]-lo0)*3600
            r0=np.clip(np.floor(r).astype(int),0,3599); c0=np.clip(np.floor(c).astype(int),0,3599)
            fr=r-r0; fc=c-c0
            out[m]=(a[r0,c0]*(1-fr)*(1-fc)+a[r0+1,c0]*fr*(1-fc)+a[r0,c0+1]*(1-fr)*fc+a[r0+1,c0+1]*fr*fc)
    return out
