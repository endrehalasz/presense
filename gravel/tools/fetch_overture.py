import pyarrow.fs as fs, pyarrow.parquet as pq, pyarrow as pa, os, sys
from concurrent.futures import ThreadPoolExecutor
W,E,S,N = 12.40,13.45,47.45,47.98
s3=fs.S3FileSystem(anonymous=True, region='us-west-2', proxy_options=os.environ['HTTPS_PROXY'])
typ=sys.argv[1]
base=f'overturemaps-us-west-2/release/2026-09-23.1/{typ}/'
files=[i.path for i in s3.get_file_info(fs.FileSelector(base))]
def colidx(md,name):
    for i in range(md.num_columns):
        if md.schema.column(i).path==name: return i
def scan(path):
    f=pq.ParquetFile(path, filesystem=s3)
    md=f.metadata
    ix={n:colidx(md,'bbox.'+n) for n in ['xmin','xmax','ymin','ymax']}
    rgs=[]
    for r in range(md.num_row_groups):
        rg=md.row_group(r); st={n:rg.column(i).statistics for n,i in ix.items()}
        if st['xmin'].min<=E and st['xmax'].max>=W and st['ymin'].min<=N and st['ymax'].max>=S: rgs.append(r)
    if not rgs: return None
    t=f.read_row_groups(rgs)
    b=t.column('bbox').combine_chunks()
    import pyarrow.compute as pc
    m=pc.and_(pc.and_(pc.less_equal(b.field('xmin'),E),pc.greater_equal(b.field('xmax'),W)),pc.and_(pc.less_equal(b.field('ymin'),N),pc.greater_equal(b.field('ymax'),S)))
    t=t.filter(m)
    print(path[-60:], len(rgs), t.num_rows, flush=True)
    return t
with ThreadPoolExecutor(16) as ex: res=[r for r in ex.map(scan,files) if r is not None and r.num_rows]
t=pa.concat_tables(res, promote_options='permissive')
pq.write_table(t, typ.replace('/','_').replace('=','')+'.parquet')
print('TOTAL',t.num_rows, t.schema)
