#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Aggregate user-provided BSP29 polygon centroids; export no asset geometry."""
import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
import hashlib
import html
import json
import math
import os
from pathlib import Path
import re
import struct


def bounds(value):
    if (len(value) != 2 or any(len(p) != 2 for p in value)
            or not all(math.isfinite(v) for p in value for v in p)
            or any(value[0][i] >= value[1][i] for i in range(2))):
        raise ValueError('Expected finite nonempty XY bounds')
    return value


def world(point, centre, scale):
    return [point[i] / scale + centre[i] for i in range(2)]


def axes(angles):
    p, y, r = map(math.radians, angles)
    sp, cp, sy, cy, sr, cr = math.sin(p), math.cos(p), math.sin(y), math.cos(y), math.sin(r), math.cos(r)
    return ((cp*cy, cp*sy, -sp), (sr*sp*cy-cr*sy, sr*sp*sy+cr*cy, sr*cp),
            (cr*sp*cy+sr*sy, cr*sp*sy-sr*cy, cr*cp))


def polygon_samples(raw):
    """Yield placed centroid + fan triangle equivalent, not unique disk faces.

    Each referenced inline brush placement contributes separately. Model zero
    contributes once. Vertices, entities and material data stay inside Python.
    The centroid is the arithmetic vertex mean (not surface area weighting).
    """
    if len(raw) < 124 or struct.unpack_from('<i', raw)[0] != 29:
        raise ValueError('Expected BSP29')
    lumps = []
    for i in range(15):
        offset, length = struct.unpack_from('<ii', raw, 4 + i*8)
        if length < 0 or offset < 0 or offset + length > len(raw) or (length and offset < 124):
            raise ValueError('Invalid BSP lump bounds')
        lumps.append(raw[offset:offset+length])
    formats = {3:'<3f', 7:'<Hhihh4Bi', 12:'<HH', 13:'<i', 14:'<9f7i'}
    try:
        rows = {i:list(struct.iter_unpack(fmt, lumps[i])) for i,fmt in formats.items()}
    except struct.error as exc:
        raise ValueError('Invalid BSP record size') from exc
    if not rows[14]:
        raise ValueError('Missing BSP world model')
    placements = [(0, (0,0,0), axes((0,0,0)))]
    for block in re.findall(r'\{[^{}]*\}', lumps[0].decode('cp1252')):
        entity = dict(re.findall(r'"([^"\n]*)"\s+"([^"\n]*)"', block))
        model = entity.get('model', '')
        if model.startswith('*'):
            index = int(model[1:])
            if index <= 0 or index >= len(rows[14]):
                raise ValueError('Invalid inline model index')
            origin = tuple(map(float, entity.get('origin','0 0 0').split()))
            rotation = tuple(map(float, entity.get('angles', '0 '+entity.get('angle','0')+' 0').split()))
            if len(origin)!=3 or len(rotation)!=3 or not all(math.isfinite(v) for v in origin+rotation):
                raise ValueError('Invalid entity transform')
            placements.append((index, origin, axes(rotation)))
    def samples():
        for index, origin, basis in placements:
            first, count = rows[14][index][14:16]
            if first < 0 or count < 0 or first+count > len(rows[7]):
                raise ValueError('Invalid model face range')
            for face in rows[7][first:first+count]:
                start, count = face[2:4]
                if start < 0 or count < 3 or start+count > len(rows[13]):
                    raise ValueError('Invalid face surfedge range')
                points = []
                for (signed,) in rows[13][start:start+count]:
                    if abs(signed) >= len(rows[12]):
                        raise ValueError('Invalid edge index')
                    edge = rows[12][abs(signed)]
                    vertex = edge[0 if signed >= 0 else 1]
                    if vertex >= len(rows[3]):
                        raise ValueError('Invalid vertex index')
                    points.append(rows[3][vertex])
                centroid = [sum(p[i] for p in points)/len(points) for i in range(3)]
                if not all(math.isfinite(v) for v in centroid):
                    raise ValueError('Nonfinite BSP vertex')
                yield [origin[i]+sum(centroid[j]*basis[j][i] for j in range(3)) for i in range(2)], count-2
    return samples(), len(rows[7])


def aggregate(samples, centre, scale, bin_size, regions):
    if scale <= 0 or not math.isfinite(scale) or bin_size <= 0 or not math.isfinite(bin_size):
        raise ValueError('Scale and bin size must be positive finite numbers')
    if len(centre)!=2 or not all(math.isfinite(v) for v in centre):
        raise ValueError('Expected finite XY centre')
    bins = defaultdict(lambda:[0,0])
    counts = [[0,0] for _ in regions]
    total = [0,0]
    for point, triangles in samples:
        if len(point)!=2 or not all(math.isfinite(v) for v in point) or triangles < 1:
            raise ValueError('Invalid aggregate sample')
        position = world(point, centre, scale)
        key = tuple(math.floor(v/bin_size) for v in position)
        bins[key][0] += 1
        bins[key][1] += triangles
        total[0] += 1
        total[1] += triangles
        for i, region in enumerate(regions):
            for j, label in enumerate(('core','coverage')):
                lo, hi = bounds(region[label])
                if all(lo[k] <= position[k] < hi[k] for k in range(2)):
                    counts[i][j] += 1
    return {'bins':[[*key,*value] for key,value in sorted(bins.items())],
            'placed_polygons':total[0], 'triangle_equivalent':total[1],
            'region_centroid_counts':counts}


def read_world_directory(raw, scale=0.25):
    """Decode AWR2 metadata only; origins and selectors are runtime coordinates."""
    if len(raw)<64 or raw[:4]!=b'AWR2':
        raise ValueError('Expected AWR2 world region directory')
    count=struct.unpack_from('<I',raw,4)[0]
    if count>8192 or len(raw)!=64+count*52:
        raise ValueError('Invalid AWR2 entry count or length')
    if not math.isfinite(scale) or scale<=0:
        raise ValueError('Invalid directory scale')
    result=[]
    for i in range(count):
        values=struct.unpack_from('<8s11f',raw,64+i*52)
        name=values[0].split(b'\0')[0].decode('ascii')
        if not re.fullmatch(r'vf[0-9]{4}',name):
            raise ValueError('Unexpected world region name')
        origin=values[1:4]
        if not all(math.isfinite(v) for v in origin):
            raise ValueError('Invalid world origin')
        result.append({'name':name,'centre':[v/scale for v in origin[:2]],'scale':scale,
                       'core':bounds([list(values[4:6]),list(values[6:8])]),
                       'coverage':bounds([list(values[8:10]),list(values[10:12])])})
    return result


def owned_samples(samples, core):
    """Drop apron copies by half-open centroid ownership, before world transform.

    This is an inventory of compiled pieces owned by disjoint selectors. It is
    not an original mesh deduplication: compiler split polygons can differ.
    """
    lo,hi=bounds(core)
    for point,triangles in samples:
        if all(lo[i]<=point[i]<hi[i] for i in range(2)):
            yield point,triangles


def _source_mosaic(job):
    source,bin_size=job
    path=Path(source['bsp'])
    if not path.is_file():
        return {'missing':source['name']}
    raw=path.read_bytes()
    digest=hashlib.sha256(raw).hexdigest()
    if source.get('expected_sha256') and digest!=source['expected_sha256']:
        raise ValueError('BSP source identity mismatch: '+source['name'])
    samples,disk=polygon_samples(raw)
    stats=aggregate(owned_samples(samples,source['core']),source['centre'],source['scale'],bin_size,[])
    return {'name':source['name'],'source_sha256':digest,'disk_faces':disk,**stats}


def mosaic(view,directory,bin_size,jobs=1):
    sources=[];regions=[]
    for item in view['sources']:
        source=dict(item)
        path=Path(source['bsp'])
        if not path.is_absolute():path=Path(directory)/path
        source['bsp']=str(path)
        region={'name':str(source['name']),
                **{k:[world(p,source['centre'],source['scale']) for p in bounds(source[k])] for k in ('core','coverage')},
                'peak_bytes':source.get('peak_bytes'),'clearance_bytes':source.get('clearance_bytes')}
        sources.append(source);regions.append(region)
    # Fail instead of silently pooling overlapping owners. Adjacent edges are OK.
    ordered=sorted(regions,key=lambda r:r['core'][0][0])
    for i,a in enumerate(ordered):
        for b in ordered[i+1:]:
            if b['core'][0][0]>=a['core'][1][0]:break
            if min(a['core'][1][1],b['core'][1][1])>max(a['core'][0][1],b['core'][0][1]):
                raise ValueError('Mosaic owner cores overlap: '+a['name']+' / '+b['name'])
    jobs=max(1,int(jobs));work=[(s,bin_size) for s in sources]
    if jobs==1:
        results=list(map(_source_mosaic,work))
    else:
        with ProcessPoolExecutor(max_workers=jobs) as pool:
            results=list(pool.map(_source_mosaic,work,chunksize=4))
    bins=defaultdict(lambda:[0,0]);missing=[];counts=[];disk=0;provenance=[]
    for result in results:
        if 'missing' in result:
            missing.append(result['missing']);counts.append([None,None]);continue
        disk+=result['disk_faces'];counts.append([result['placed_polygons'],None])
        provenance.append({'name':result['name'],'sha256':result['source_sha256']})
        for x,y,faces,triangles in result['bins']:
            bins[x,y][0]+=faces;bins[x,y][1]+=triangles
    if not bins:raise ValueError('No available owned polygon samples')
    return {'name':str(view['name']),'note':str(view.get('note','Disjoint owner-core centroid mosaic; apron copies excluded; not original mesh deduplication')),
            'centre':[0,0],'scale':1,'regions':regions,'region_centroid_counts':counts,
            'disk_faces':disk,'placed_polygons':sum(v[0] for v in bins.values()),
            'triangle_equivalent':sum(v[1] for v in bins.values()),
            'bins':[[*k,*v] for k,v in sorted(bins.items())],
            'missing_regions':missing,'expected_regions':len(sources),'available_regions':len(provenance),
            'source_sha256':hashlib.sha256(json.dumps(provenance,sort_keys=True).encode('utf-8')).hexdigest()}


def generate(config, directory, jobs=1):
    """Strict output allowlist; input extras, filenames and assets never copied."""
    bin_size = config.get('bin_size', 512)
    audit = config.get('audit_scope',{})
    scope = {k:int(audit[k]) for k in ('baseline_maps','baseline_failures','trial_maps','trial_failures') if k in audit}
    if 'trial_values' in audit:
        scope['trial_values'] = [{'map':str(row['map']), 'peak_bytes':int(row['peak_bytes']),
                                  'clearance_bytes':int(row['clearance_bytes'])} for row in audit['trial_values']]
    output = {'title':str(config.get('title','AmiWind polygon density')),
              'bin_size':bin_size, 'cell_size':8192, 'views':[],
              'scope':str(config.get('scope','User-provided converted BSPs; no target acceptance')),
              'audit_scope':scope}
    for view in config['views']:
        if 'sources' in view:
            output['views'].append(mosaic(view,directory,bin_size,jobs))
            continue
        centre, scale = view['centre'], view['scale']
        regions = []
        for region in view.get('regions',[]):
            regions.append({'name':str(region['name']),
                            **{k:[world(p,centre,scale) for p in bounds(region[k])] for k in ('core','coverage')},
                            'peak_bytes':region.get('peak_bytes'), 'clearance_bytes':region.get('clearance_bytes')})
        path = Path(view['bsp'])
        if not path.is_absolute():
            path = Path(directory)/path
        raw = path.read_bytes()
        samples, disk_faces = polygon_samples(raw)
        stats = aggregate(samples, centre, scale, bin_size, regions)
        if not stats['bins']:
            raise ValueError('No referenced polygons in BSP')
        output['views'].append({'name':str(view['name']), 'note':str(view.get('note','One independent BSP; views are never added together')),
                                'coordinate_space':'interior' if view.get('coordinate_space')=='interior' else 'exterior',
                                'centre':centre, 'scale':scale, 'regions':regions,
                                'source_sha256':hashlib.sha256(raw).hexdigest(), 'disk_faces':disk_faces, **stats})
    return output


def render(data):
    payload = json.dumps(data, separators=(',',':'), allow_nan=False).replace('<','\\u003c')
    return HTML.replace('__TITLE__',html.escape(data['title'])).replace('__DATA__',payload)


HTML = r'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title><style>body{margin:0;background:#111d29;color:#e8eff8;font:15px system-ui}header{padding:16px}h1{font-size:21px;margin:0 0 8px}main{display:grid;grid-template-columns:1fr 340px}canvas{width:100%;height:75vh;touch-action:none;background:#182432}aside{padding:15px}label{display:block;margin:12px 0}select,button{padding:7px;background:#253748;color:white}pre{white-space:pre-wrap;font-size:13px}p{line-height:1.5}#legend{height:14px;background:linear-gradient(90deg,hsl(230,85%,55%),hsl(115,85%,55%),hsl(0,85%,55%))}@media(max-width:800px){main{grid-template-columns:1fr}canvas{height:55vh}}</style>
<header><h1>__TITLE__</h1><strong>PRIVATE DEVELOPMENT · generated numeric statistics · NEVER ADD TO REPO</strong><p id="scope"></p><select id="view" aria-label="Independent BSP view"></select> <button id="fit">Fit view</button></header>
<main><canvas id="map" aria-label="North-up polygon centroid density; drag to pan, wheel to zoom, click a bin or core"></canvas><aside>
<label>Density metric <select id="metric"><option value="faces">Placed compiled polygons</option><option value="triangles">Fan triangle equivalent</option></select></label>
<div id="legend"></div><p id="range"></p><label><input type="checkbox" id="cells" checked>White: original TES3 8192-unit cells</label>
<div id="heaplegend" style="height:14px;background:linear-gradient(90deg,hsl(0,90%,48%),hsl(40,90%,48%),hsl(120,90%,48%))"></div><p id="heaprange"></p>
<label><input type="checkbox" id="cores" checked>Gold: owner / town subcell cores</label><label><input type="checkbox" id="coverage">Dashed cyan: loading coverage</label>
<label><input type="checkbox" id="heap">Secondary: modeled heap clearance on cores</label><pre id="totals"></pre><pre id="details">Click a density bin or town core.</pre>
<label>Warning margin <input id="warning" type="range" min="0" max="2048" step="16" value="1024"><span id="warningvalue"></span> KiB</label>
<label>Exploratory map growth <input id="growth" type="range" min="0" max="2" step="0.05" value="0"><span id="growthvalue"></span> MiB</label>
<p>Heap overlay: red × exceeds policy ceiling; amber ▲ warns when remaining margin ≤ adjustable KiB threshold; green has more margin. Symbols use the exploratory growth scenario when set. Growth slider adds modeled payload; policy remains 11 MiB Hunk − 3 MiB engine reserve − 2 MiB safety = 6 MiB map ceiling. Sliders are exploratory and never change the build gate.</p>
<p>Colors count polygon vertex-mean centroids in equal-size source-world bins, north up. They show spatial density, not whole-map counts painted over bounds. Triangle equivalents use edges − 2; these are compiled BSP polygons, not original NIF triangles.</p>
<p>Independent BSP views are never summed. Mosaic views count only centroids inside each BSP's disjoint half-open owner core, excluding repeated loading aprons. This counts compiled polygon pieces, not deduplicated original mesh triangles. Town and world layers remain separate. Magenta cores are missing data, not zero density. Repeated inline placements count separately. Disk-record totals for mosaics include repeated loaded apron records; they are not unique faces. Coverage counts are centroid inclusion, not complete polygon/model intersection; missing counts are unavailable. No runtime loading concurrency is implied.</p><pre id="audit"></pre></aside></main>
<script>'use strict';const D=__DATA__;const $=id=>document.getElementById(id),cv=$('map'),ctx=cv.getContext('2d');let vi=0,s=1,ox=0,oy=0,drag=null,moved=false;const V=()=>D.views[vi];
$('scope').textContent=D.scope;D.views.forEach((v,i)=>{let o=document.createElement('option');o.value=i;o.textContent=v.name;$('view').append(o)});$('audit').textContent='Audit scope (separate measurements):\n'+JSON.stringify(D.audit_scope,null,2);
function px(p){return [ox+p[0]*s,oy-p[1]*s]}function rect(b,fill,stroke){let p=px([b[0][0],b[1][1]]),w=(b[1][0]-b[0][0])*s,h=(b[1][1]-b[0][1])*s;if(fill){ctx.fillStyle=fill;ctx.fillRect(...p,w,h)}if(stroke){ctx.strokeStyle=stroke;ctx.strokeRect(...p,w,h)}}
function label(t,p,color){p=px(p);ctx.font='11px monospace';ctx.lineWidth=3;ctx.strokeStyle='#111d29';ctx.strokeText(t,...p);ctx.fillStyle=color;ctx.fillText(t,...p)}
function fit(){const v=V(),b=v.bins,t=D.bin_size;let lo=[Math.min(...b.map(x=>x[0]))*t,Math.min(...b.map(x=>x[1]))*t],hi=[(Math.max(...b.map(x=>x[0]))+1)*t,(Math.max(...b.map(x=>x[1]))+1)*t];s=Math.min((cv.clientWidth-40)/(hi[0]-lo[0]),(cv.clientHeight-40)/(hi[1]-lo[1]));ox=cv.clientWidth/2-(lo[0]+hi[0])*s/2;oy=cv.clientHeight/2+(lo[1]+hi[1])*s/2;draw()}
function draw(){let v=V(),t=D.bin_size,idx=$('metric').value==='faces'?2:3,max=Math.max(1,...v.bins.map(b=>b[idx]));ctx.clearRect(0,0,cv.clientWidth,cv.clientHeight);for(let b of v.bins){let f=Math.log1p(b[idx])/Math.log1p(max);rect([[b[0]*t,b[1]*t],[(b[0]+1)*t,(b[1]+1)*t]],`hsl(${230*(1-f)},85%,55%)`)}
if($('cells').checked&&v.coordinate_space!=='interior'){let left=(0-ox)/s,right=(cv.clientWidth-ox)/s,bottom=(oy-cv.clientHeight)/s,top=oy/s,C=D.cell_size;ctx.lineWidth=1;for(let x=Math.floor(left/C)*C;x<=right;x+=C)for(let y=Math.floor(bottom/C)*C;y<=top;y+=C){rect([[x,y],[x+C,y+C]],null,'#ffffff88');if(C*s>70)label(`(${x/C},${y/C})`,[x+30,y+C-80/s],'white')}}
const warning=Number($('warning').value)*1024,growth=Number($('growth').value)*1048576;$('warningvalue').textContent=$('warning').value;$('growthvalue').textContent=$('growth').value;
$('heaplegend').style.display=$('heap').checked?'block':'none';$('heaprange').textContent=$('heap').checked?`Heap: red × exceeds ceiling; amber ▲ margin ≤ ${$('warning').value} KiB; green more margin. Growth scenario +${$('growth').value} MiB; policy ceiling remains 6 MiB.`:'';
for(let r of v.regions){if((v.missing_regions||[]).includes(r.name))rect(r.core,'#e42de088','#ff66ff');if($('coverage').checked){ctx.setLineDash([5,5]);rect(r.coverage,null,'#60e0f5');ctx.setLineDash([])}if($('cores').checked||$('heap').checked){let margin=r.clearance_bytes-growth,fill=$('heap').checked&&r.clearance_bytes!=null?`hsla(${margin<0?0:Math.min(120,40+80*margin/Math.max(1,warning))},90%,48%,.8)`:null;ctx.lineWidth=2;rect(r.core,fill,'#ffdd66');if((r.core[1][0]-r.core[0][0])*s>50)label(r.name,r.core[0],'#ffe798');if($('heap').checked&&r.clearance_bytes!=null&&margin<=warning)label(margin<0?'×':'▲',r.core[0].map((n,i)=>(n+r.core[1][i])/2),margin<0?'#ff3333':'#ffdd00')}}
$('range').textContent=`Blue → red: 1 … ${max.toLocaleString()} per ${t} × ${t} source-world-unit bin (log scale; empty bins blank).`;$('totals').textContent=`${v.name}\nDisk face records (mosaics include aprons): ${v.disk_faces.toLocaleString()}\nOwned / placed polygons: ${v.placed_polygons.toLocaleString()}\nFan triangle equivalent: ${v.triangle_equivalent.toLocaleString()}\n${v.note}\nTransform: world = runtime / ${v.scale} + [${v.centre}]${v.expected_regions==null?'':`\nAvailable / expected owners: ${v.available_regions} / ${v.expected_regions}\nMissing (unavailable, not zero): ${(v.missing_regions||[]).join(', ')||'none'}`}`;}
function heapStatus(r){if(r.clearance_bytes==null)return 'Heap: unmeasured';const m=r.clearance_bytes-Number($('growth').value)*1048576,w=Number($('warning').value)*1024;return `${m<0?'× OVER POLICY CEILING':m<=w?'▲ WARNING: NEAR LIMIT':'Healthy margin'}; scenario margin ${m.toLocaleString()} bytes; warning threshold ${w.toLocaleString()} bytes`}
function resize(){let d=devicePixelRatio||1;cv.width=cv.clientWidth*d;cv.height=cv.clientHeight*d;ctx.setTransform(d,0,0,d,0,0);fit()}
cv.onpointerdown=e=>{cv.setPointerCapture(e.pointerId);drag=[e.offsetX,e.offsetY,ox,oy];moved=false};cv.onpointermove=e=>{if(!drag)return;let dx=e.offsetX-drag[0],dy=e.offsetY-drag[1];moved||=Math.hypot(dx,dy)>3;ox=drag[2]+dx;oy=drag[3]+dy;draw()};cv.onpointerup=e=>{if(!moved){let p=[(e.offsetX-ox)/s,(oy-e.offsetY)/s],v=V(),t=D.bin_size,b=v.bins.find(b=>b[0]===Math.floor(p[0]/t)&&b[1]===Math.floor(p[1]/t)),lines=[`World XY: ${p.map(n=>n.toFixed(1))}`,v.coordinate_space==='interior'?'Local interior coordinates; no exterior CELL identity':`Original cell: ${p.map(n=>Math.floor(n/8192))}`,`Bin polygons: ${b?b[2]:0}; triangle equivalent: ${b?b[3]:0}`,`Bin bounds: [${p.map(n=>Math.floor(n/t)*t)}] → [${p.map(n=>(Math.floor(n/t)+1)*t)}]`];v.regions.forEach((r,i)=>{if(p.every((n,k)=>n>=r.core[0][k]&&n<r.core[1][k]))lines.push(`Core ${r.name}: ${JSON.stringify(r.core)}\nCoverage: ${JSON.stringify(r.coverage)}\nCentroids in core / coverage: ${v.region_centroid_counts[i].join(' / ')}\nPeak bytes: ${r.peak_bytes??'unmeasured'}; clearance: ${r.clearance_bytes??'unmeasured'}\n${heapStatus(r)}`)});$('details').textContent=lines.join('\n')}drag=null};cv.onpointercancel=()=>drag=null;
cv.addEventListener('wheel',e=>{e.preventDefault();let p=[(e.offsetX-ox)/s,(oy-e.offsetY)/s];s=Math.max(.0001,Math.min(4,s*Math.exp(-e.deltaY*.001)));ox=e.offsetX-p[0]*s;oy=e.offsetY+p[1]*s;draw()},{passive:false});$('view').onchange=()=>{vi=Number($('view').value);$('details').textContent='Click a density bin or town core.';fit()};$('fit').onclick=fit;for(let id of ['metric','cells','cores','coverage','heap','warning','growth'])$(id).oninput=draw;new ResizeObserver(resize).observe(cv);
</script></html>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True,help='Private HTML destination outside public source')
    parser.add_argument('--stats',type=Path,help='Optional aggregate-only JSON')
    parser.add_argument('--jobs',type=int,default=os.cpu_count() or 1,help='Parallel BSP readers for owned-core mosaics')
    args = parser.parse_args()
    data = generate(json.loads(args.config.read_text(encoding='utf-8')),args.config.parent,args.jobs)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(render(data),encoding='utf-8',newline='\n')
    if args.stats:
        args.stats.parent.mkdir(parents=True,exist_ok=True)
        args.stats.write_text(json.dumps(data,indent=2,allow_nan=False)+'\n',encoding='utf-8',newline='\n')
    print(f'{len(data["views"])} independent views; aggregate-only output: {args.output}')


if __name__ == '__main__':
    main()
