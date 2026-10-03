import pyarrow.parquet as pq, shapely, sys, re, pickle, os
if not os.path.exists('gaz.pkl'):
    rows=[]
    for fn,kind in [('themeplaces_typeplace.parquet','place'),('themebase_typewater.parquet','water'),('segment.parquet','seg')]:
        t=pq.read_table(fn,columns=['names','geometry']+(['basic_category'] if kind=='place' else ['class'] if kind=='seg' else ['subtype']))
        names=t.column('names').to_pylist(); geoms=shapely.from_wkb(t.column('geometry').to_pylist())
        extra=t.column(t.schema.names[2]).to_pylist()
        for n,g,e in zip(names,geoms,extra):
            if not n or not n.get('primary'): continue
            c=shapely.centroid(g) if kind!='seg' else shapely.line_interpolate_point(g,0.5,normalized=True)
            cat=e
            rows.append((n['primary'],kind,cat,round(c.y,5),round(c.x,5)))
    pickle.dump(rows,open('gaz.pkl','wb'))
rows=pickle.load(open('gaz.pkl','rb'))
for q in sys.argv[1:]:
    r=re.compile(q,re.I); hits=[x for x in rows if r.search(x[0]) or (x[2] and r.search(str(x[2])))]
    print(f'== {q} ({len(hits)})')
    for h in hits[:12]: print('  ',h)
