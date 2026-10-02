# SPDX-License-Identifier: GPL-3.0-only
"""Self-contained private planning atlas and north-up static overview."""
import base64
import json
import math
from pathlib import Path
from PIL import Image, ImageDraw


def terrain_regions(report):
    """Match prepare_world_regions.plan naming; bounds are source game units."""
    result = []
    for cell in sorted(report['cells'], key=lambda c: tuple(c['cell'])):
        n = cell['screen']['candidate']
        if n not in (1, 2, 4, 8) or cell['unresolved_placements']:
            raise ValueError('Unresolved terrain subdivision in atlas')
        step = report['cell_size'] / n
        for y in range(n):
            for x in range(n):
                lo = [cell['cell'][0]*report['cell_size'] + x*step,
                      cell['cell'][1]*report['cell_size'] + y*step]
                result.append(dict(name=f'vf{len(result):04d}', cell=cell['cell'],
                                   bounds=[lo, [v+step for v in lo]]))
    return result


def render(report, out):
    out = Path(out)
    source = Image.open(out/'terrain.png').convert('RGBA')
    background = Image.new('RGBA', source.size, (19, 40, 53, 255)); background.alpha_composite(source)
    draw = ImageDraw.Draw(background)
    x0,y0,x1,y1 = report['terrain_bounds']
    def xy(p):return ((p[0]/8192-x0)*32, (y1-p[1]/8192)*32)
    for area in report['areas']:
        for r in area['regions']:
            a,b=xy(r['core'][0]),xy(r['core'][1])
            draw.rectangle((a[0],b[1],b[0],a[1]),outline='#ffda74',width=1)
        point=xy(area['centre']);draw.text((point[0]+5,point[1]+5),area['name'],fill='white',stroke_width=2,stroke_fill='black')
    background.convert('RGB').save(out/'overview.png')
    report = dict(report, terrain_regions=terrain_regions(report))
    payload = json.dumps(report,separators=(',',':')).replace('<', r'<')
    picture = base64.b64encode((out/'terrain.png').read_bytes()).decode()
    html=HTML.replace('__DATA__',payload).replace('__IMAGE__',picture)
    (out/'Vvardenfell-atlas.html').write_text(html)


HTML = r'''<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>AmiWind · Vvardenfell original cells</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#101c24;color:#e6e7e3;font:15px system-ui,sans-serif}header{padding:16px 22px;border-bottom:1px solid #32434d;display:flex;gap:16px;align-items:center;flex-wrap:wrap}h1{font:600 22px Georgia,serif;margin:0}small{color:#b9c9d1}main{display:grid;grid-template-columns:minmax(0,1fr) 340px;height:calc(100vh - 88px);min-height:480px}#map{width:100%;height:100%;touch-action:none;display:block;background:#132835;cursor:grab}aside{padding:18px 20px;overflow:auto;border-left:1px solid #32434d}button,select,input{background:#1e303c;color:#f3efe3;border:1px solid #506471;border-radius:4px;padding:7px}button{cursor:pointer}button:hover{background:#334e5d}button:focus-visible,input:focus-visible,select:focus-visible{outline:2px solid #ffdb7c;outline-offset:3px}label{display:block;margin:12px 0;cursor:pointer}input[type=checkbox]{accent-color:#e7d394;vertical-align:middle;margin-right:6px}input[type=number]{width:76px}h2{font:600 18px Georgia,serif;color:#f0d699;margin:20px 0 8px}h2:first-child{margin-top:0}pre{white-space:pre-wrap;font:13px/1.6 ui-monospace,monospace;overflow-wrap:anywhere}p{line-height:1.5;margin:10px 0}#legend,.note{color:#b9c9d1;font-size:13px}#status{margin-left:auto;font-size:13px;max-width:270px}a{color:#efce88}.row{display:flex;gap:5px;flex-wrap:wrap}.swatch{display:inline-block;width:18px;margin-right:7px;border-top:2px solid #e9eff2;vertical-align:middle}.vf{border-top:2px dashed #60cbd9}.town{border-color:#ffdb7c}.metadata{font-size:12px;overflow-wrap:anywhere;color:#b9c9d1}#celltitle{color:#eaf4f7}#selectedCell{border-top:1px solid #32434d;border-bottom:1px solid #32434d;margin-top:18px;padding:0 0 12px}@media(max-width:800px){main{grid-template-columns:1fr;height:auto}#map{height:62vh;min-height:330px}aside{border-left:0;border-top:1px solid #32434d}header{padding:12px;gap:10px}#status{margin:0;max-width:none}}
</style></head>
<body><header><div><h1>AmiWind · Vvardenfell</h1><small>Original Morrowind cells &amp; AmiWind subdivisions</small></div><select id="layer" aria-label="Map colour layer"><option value="terrain">Terrain colours</option><option value="density">Triangle density</option><option value="candidates">Subdivision screening</option></select><button id="reset">Fit island</button><span id="status" aria-live="polite"></span></header>
<main><canvas id="map" aria-label="Vvardenfell atlas. Drag to pan, scroll to zoom and click an original cell for details."></canvas><aside>
<h2>Map overlays</h2>
<label><input id="grid" type="checkbox" checked><span class="swatch"></span>Original Morrowind cells</label>
<label><input id="vf" type="checkbox"><span class="swatch vf"></span>AmiWind vfXXXX subdivisions</label>
<label><input id="regions" type="checkbox" checked><span class="swatch town"></span>Surveyed town cores</label>
<label><input id="overlap" type="checkbox">Town loading overlap</label>
<p class="note">Original cells are 8,192 × 8,192 game units. Zoom in for their (x, y) labels. Names and regions come from the base master.</p>
<p id="legend"></p>
<section id="selectedCell"><h2 id="celltitle">Choose an original cell</h2><pre id="details">Click the map to inspect source coordinates, the original name and region, and the matching vf subdivision.</pre></section>
<h2>Locate runtime coordinates</h2><select id="area" aria-label="Runtime coordinate area"></select><div class="row"><label>X <input id="lx" type="number" value="0"></label><label>Y <input id="ly" type="number" value="0"></label><label>Z <input id="lz" type="number" value="0"></label></div><button id="locate">Place marker</button><p id="location"></p>
<h2>Survey scope</h2><p id="intro"></p><p class="note">Drag to pan. Wheel to zoom. North is up. The vf overlay follows the terrain subdivision plan; it does not certify converted scenery. Town cores are a separate layer.</p><p class="note">Density assigns source triangles by their centres. Loading estimates include complete intersecting objects and overlap. Original-cell boundaries are distinct from the 4 × 4 density samples.</p><p class="note">Terrain and survey values are retained from the supplied atlas. This update adds clearer original-cell inspection and the vf overlay; it does not regenerate game terrain.</p><details class="metadata"><summary>Source identity</summary><p id="source"></p></details>
</aside></main>
<script>
'use strict';
const data=__DATA__;
const cv=document.getElementById('map'),ctx=cv.getContext('2d');const $=id=>document.getElementById(id);
const img=new Image();const [x0,y0,x1,y1]=data.terrain_bounds;const CELL=data.cell_size;
let scale=1,ox=0,oy=0,selected=null,selectedVf=null,marker=null,drag=null,moved=false,ready=false;
const byCell=new Map(data.cells.map(c=>[c.cell.join(','),c]));
const vfByCell=new Map();for(const r of data.terrain_regions){const key=r.cell.join(',');if(!vfByCell.has(key))vfByCell.set(key,[]);vfByCell.get(key).push(r)}
const maxDensity=Math.max(1,...data.cells.map(c=>Math.max(...c.subtiles)));const colors={1:'#48b7a2',2:'#e2c45a',4:'#ed9253',8:'#d86869',null:'#b085cf'};
$('intro').textContent=`${data.cells.length.toLocaleString()} original exterior cells; ${data.summary.terrain_cells.toLocaleString()} with terrain. ${data.terrain_regions.length.toLocaleString()} vf subdivisions. ${data.summary.measured_placements.toLocaleString()} placements measured by the survey, not a count of packaged assets.`;
$('source').textContent=`Morrowind.esm SHA-256: ${data.master_sha256}`;
for(const a of data.areas){let o=document.createElement('option');o.textContent=a.name;$('area').append(o)}
function world(px,py){return [(px-ox)/scale,(oy-py)/scale]}
function pixel(x,y){return [ox+x*scale,oy-y*scale]}
function rect(a,b,fill,stroke){const p=pixel(a[0],b[1]),w=(b[0]-a[0])*scale,h=(b[1]-a[1])*scale;if(fill){ctx.fillStyle=fill;ctx.fillRect(p[0],p[1],w,h)}if(stroke){ctx.strokeStyle=stroke;ctx.strokeRect(p[0],p[1],w,h)}}
function label(text,x,y,color,align='center'){ctx.save();ctx.font='12px ui-monospace,monospace';ctx.textAlign=align;ctx.textBaseline='middle';ctx.lineWidth=3;ctx.strokeStyle='#10202b';ctx.strokeText(text,x,y);ctx.fillStyle=color;ctx.fillText(text,x,y);ctx.restore()}
function visible(a,b){const p=pixel(a[0],b[1]);return p[0]<=cv.clientWidth&&p[1]<=cv.clientHeight&&p[0]+(b[0]-a[0])*scale>=0&&p[1]+(b[1]-a[1])*scale>=0}
function fit(){scale=Math.min(cv.clientWidth/((x1-x0+4)*CELL),cv.clientHeight/((y1-y0+4)*CELL));ox=cv.clientWidth/2-(x0+x1)*CELL/2*scale;oy=cv.clientHeight/2+(y0+y1)*CELL/2*scale;draw()}
function resize(){const d=devicePixelRatio||1;cv.width=Math.round(cv.clientWidth*d);cv.height=Math.round(cv.clientHeight*d);ctx.setTransform(d,0,0,d,0,0);if(!ready){ready=true;fit()}else draw()}
function draw(){const w=cv.clientWidth,h=cv.clientHeight;ctx.clearRect(0,0,w,h);ctx.fillStyle='#132835';ctx.fillRect(0,0,w,h);const p=pixel(x0*CELL,y1*CELL);ctx.imageSmoothingEnabled=false;if(img.complete&&img.naturalWidth)ctx.drawImage(img,p[0],p[1],(x1-x0)*CELL*scale,(y1-y0)*CELL*scale);const mode=$('layer').value;
for(const c of data.cells){const a=c.cell.map(v=>v*CELL),b=a.map(v=>v+CELL);if(!visible(a,b))continue;if(mode==='density'){for(let y=0;y<4;y++)for(let x=0;x<4;x++){const n=c.subtiles[y*4+x];if(n){const f=Math.log1p(n)/Math.log1p(maxDensity),t=CELL/4;rect([a[0]+x*t,a[1]+y*t],[a[0]+(x+1)*t,a[1]+(y+1)*t],`hsla(${230-230*f},85%,55%,.83)`)}}}else if(mode==='candidates'){ctx.globalAlpha=.68;rect(a,b,c.unresolved_placements?'#ed42c1':colors[c.screen.candidate]);ctx.globalAlpha=1}}
if($('vf').checked){ctx.save();ctx.setLineDash([3,3]);ctx.lineWidth=1;for(const r of data.terrain_regions){if(!visible(r.bounds[0],r.bounds[1]))continue;rect(r.bounds[0],r.bounds[1],null,'#60cbd9b0');const side=(r.bounds[1][0]-r.bounds[0][0])*scale;if(side>=74){const p=pixel((r.bounds[0][0]+r.bounds[1][0])/2,(r.bounds[0][1]+r.bounds[1][1])/2);label(r.name,p[0],p[1],'#b3f3f6')}}ctx.restore()}
for(const area of data.areas){for(const r of area.regions){if($('overlap').checked)rect(r.coverage[0],r.coverage[1],null,'#e6a54045');if($('regions').checked)rect(r.core[0],r.core[1],null,'#ffdb7c')}}
if($('grid').checked){ctx.save();ctx.lineWidth=1;for(const c of data.cells){const a=c.cell.map(v=>v*CELL),b=a.map(v=>v+CELL);if(!visible(a,b))continue;rect(a,b,null,'#eff7ff8c');const side=CELL*scale;if(side>=58){const p=pixel(a[0]+CELL/2,b[1]);label(`(${c.cell[0]}, ${c.cell[1]})`,p[0],p[1]+12,'#fff4dc')}}ctx.restore()}
for(const a of data.areas){const p=pixel(...a.centre);label(a.name,p[0]+7,p[1]-7,'#ffdb7c','left')}
if(selected){ctx.save();ctx.lineWidth=2.5;rect(selected.cell.map(v=>v*CELL),selected.cell.map(v=>(v+1)*CELL),null,'#ffffff');ctx.restore()}
if(selectedVf&&$('vf').checked){ctx.save();ctx.setLineDash([3,3]);ctx.lineWidth=2;rect(selectedVf.bounds[0],selectedVf.bounds[1],null,'#a5fbff');ctx.restore()}
if(marker){const p=pixel(marker[0],marker[1]);ctx.strokeStyle='white';ctx.beginPath();ctx.arc(...p,7,0,Math.PI*2);ctx.moveTo(p[0]-12,p[1]);ctx.lineTo(p[0]+12,p[1]);ctx.moveTo(p[0],p[1]-12);ctx.lineTo(p[0],p[1]+12);ctx.stroke()}
$('status').textContent=`${Math.round(CELL*scale)} px / original cell${CELL*scale<58?' · zoom in for labels':''}`;
$('legend').textContent=mode==='candidates'?'Subdivision screening: green 1×1; yellow 2×2; orange 4×4; red 8×8. These are geometry estimates, not native memory limits.':mode==='density'?'Blue → red: logarithmic source triangle density. Placed copies included; actors excluded.':'Solid white: original CELL boundaries. Dashed cyan: vf subdivisions. Gold: surveyed town cores.'}
function inspect(c,point){selected=c;selectedVf=null;if(!c){$('celltitle').textContent='No source CELL record';$('details').textContent='Outside the exterior cells in this survey. Ocean background does not imply an authored cell.';draw();return}
const regions=vfByCell.get(c.cell.join(','))||[];if(point)selectedVf=regions.find(r=>point.every((v,i)=>v>=r.bounds[0][i]&&v<r.bounds[1][i]))||null;
$('celltitle').textContent=c.name||c.region||'Unnamed exterior';const s=c.screen,lo=c.cell.map(v=>v*CELL),hi=lo.map(v=>v+CELL);
const lines=[`Original CELL: (${c.cell.join(', ')})`,`Name: ${c.name||'(unnamed)'}`,`Region: ${c.region||'(none recorded)'}`,`World X: ${lo[0]} … ${hi[0]}`,`World Y: ${lo[1]} … ${hi[1]}`,`Terrain: ${c.has_terrain?'present':'absent'}`,`Height: ${c.min_height??'?'} … ${c.max_height??'?'}`,'',`vf subdivisions: ${regions.length}`,`At clicked point: ${selectedVf?selectedVf.name:'—'}`,`Range: ${regions.length?regions[0].name+' … '+regions[regions.length-1].name:'none'}`,'',`Source triangles in cell: ${c.spatial_source_triangles.toLocaleString()}`,`Owned placed triangles: ${c.owned_source_triangles.toLocaleString()}`,`Unresolved survey placements: ${c.unresolved_placements}`,`Subdivision: ${s.candidate?s.candidate+'×'+s.candidate:'requires further work'}`,'',...s.options.map(o=>`${o.divisions}×${o.divisions}: peak ${o.peak_source_triangles.toLocaleString()} tris / ${o.peak_references} refs`),'',`NPC / creature records: ${(c.types.NPC_||0)+(c.types.CREA||0)}`,`Leveled creatures: ${c.types.LEVC||0}`];$('details').textContent=lines.join('\n');draw()}
cv.addEventListener('pointerdown',e=>{cv.setPointerCapture(e.pointerId);drag={x:e.offsetX,y:e.offsetY,ox,oy};moved=false});
cv.addEventListener('pointermove',e=>{if(drag){const dx=e.offsetX-drag.x,dy=e.offsetY-drag.y;if(Math.hypot(dx,dy)>3)moved=true;ox=drag.ox+dx;oy=drag.oy+dy;draw()}});
cv.addEventListener('pointerup',e=>{if(!moved){const p=world(e.offsetX,e.offsetY);inspect(byCell.get(p.map(v=>Math.floor(v/CELL)).join(',')),p)}drag=null});
cv.addEventListener('pointercancel',()=>drag=null);
cv.addEventListener('wheel',e=>{e.preventDefault();const p=world(e.offsetX,e.offsetY);scale=Math.max(.0002,Math.min(.05,scale*Math.exp(-e.deltaY*.001)));ox=e.offsetX-p[0]*scale;oy=e.offsetY+p[1]*scale;draw()},{passive:false});
for(const id of ['grid','vf','regions','overlap','layer'])$(id).addEventListener('change',draw);
$('reset').onclick=fit;$('locate').onclick=()=>{const a=data.areas[$('area').selectedIndex],v=['lx','ly','lz'].map(id=>Number($(id).value));if(!v.every(Number.isFinite))return;marker=v.map((n,i)=>n/a.scale+(i<2?a.centre[i]:0));$('location').textContent=`World XYZ: ${marker.map(n=>n.toFixed(1)).join(', ')}; original cell (${marker.slice(0,2).map(n=>Math.floor(n/CELL)).join(', ')}). Exterior transforms only.`;ox=cv.clientWidth/2-marker[0]*scale;oy=cv.clientHeight/2+marker[1]*scale;inspect(byCell.get(marker.slice(0,2).map(n=>Math.floor(n/CELL)).join(',')),marker.slice(0,2))};
new ResizeObserver(resize).observe(cv);img.onload=draw;img.src='data:image/png;base64,__IMAGE__';
</script></body></html>
'''
