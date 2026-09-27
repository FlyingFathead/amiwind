#!/usr/bin/env python3
"""Bake private eight-view scenery and conservative building collision for 68000."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from mwad.paths import ensure_external
from mwad.scene import read_asset, unpack_geometry
from preview_scenery import render

ORIGIN = (-24576, -81920)
SIZE = (32, 64)
SCENERY_RGB = [(34,34,34),(68,51,34),(85,85,68),(119,102,68),
               (153,136,102),(187,170,136),(102,119,85),(153,153,136)]


def encode_columns(pixels):
    """Column offsets followed by (first row, exclusive end, colour) runs; 255 ends."""
    height, width = pixels.shape
    if not 1 <= height <= 254 or not 1 <= width <= 255:
        raise ValueError('Unsupported sprite size')
    body = bytearray(); offsets = []
    for x in range(width):
        offsets.append(width * 2 + len(body))
        y = 0
        while y < height:
            colour = int(pixels[y,x]); start = y; y += 1
            while y < height and pixels[y,x] == colour: y += 1
            if colour: body.extend((start, y, colour))
        body.append(255)
    if width * 2 + len(body) > 65535: raise ValueError('Sprite exceeds 16-bit extent')
    return struct.pack('>'+'H'*width,*offsets) + body


def decode_columns(raw, width=32, height=64):
    """Independent bounded decoder for format checks and host previews."""
    import numpy as np
    if len(raw) < width*2: raise ValueError('Short column table')
    out = np.zeros((height,width), dtype=np.uint8)
    for x in range(width):
        offset = struct.unpack_from('>H',raw,x*2)[0]
        end = struct.unpack_from('>H',raw,(x+1)*2)[0] if x+1 < width else len(raw)
        if not width*2 <= offset < end <= len(raw): raise ValueError('Invalid column extent')
        previous = 0
        while offset < end and raw[offset] != 255:
            if offset+3 >= end: raise ValueError('Unterminated column')
            first,last,colour=raw[offset:offset+3]; offset+=3
            if not previous <= first < last <= height or not 8 <= colour <= 15:
                raise ValueError('Invalid run')
            out[first:last,x]=colour; previous=last
        if offset != end-1 or raw[offset] != 255: raise ValueError('Invalid terminator')
    return out


def building(name):
    return any(x in name for x in ('house_', 'shack_02', 'shack_03', 'lighthouse', 'tower_thatch'))


def prepare(area, out):
    import numpy as np
    from PIL import Image,ImageDraw
    area=ensure_external(area,'scenery input'); out=ensure_external(out,'town bake')
    if out.exists(): raise ValueError('Town bake already exists')
    index=json.loads((area/'scenery-index.json').read_text())
    out.mkdir(parents=True)
    names=[]; model_map={}; models=[]; data=bytearray(); thumbs=[]
    palette=np.array(SCENERY_RGB, dtype=np.int32)
    with (area/'scenery.mwpak').open('rb') as archive:
        textures={}
        for i,t in enumerate(index['textures']):
            raw=read_asset(archive,t); magic,w,h=struct.unpack_from('>4sHH',raw)
            if magic != b'MWT1' or len(raw) != 8+w*h*4: raise ValueError('Invalid texture')
            textures[i]=np.frombuffer(raw[8:],dtype=np.uint8).reshape(h,w,4)
        for old,m in enumerate(index['models']):
            name=m['source']
            if any(x in name for x in ('marker_', 'terrain_bc_scum', 'lantern_hook', 'furn_de_rope', 'window_', 'ex_nord_win')): continue
            vertices,faces,_=unpack_geometry(read_asset(archive,m))
            v=np.array(vertices); centre=(v[:,:2].min(axis=0)+v[:,:2].max(axis=0))/2
            v[:,:2]-=centre
            radius=math.ceil(float(np.linalg.norm(v[:,:2],axis=1).max())+1)
            bottom=math.floor(v[:,2].min()); top=math.ceil(v[:,2].max())
            if top-bottom < 8: continue
            model_map[old]=len(models); views=[]
            for view in range(8):
                rgba=np.array(render(v,faces,m['materials'],textures,view*math.tau/8,
                                     SIZE,(-radius,radius,bottom,top)))
                rgb=rgba[:,:,:3].astype(np.int32)
                # Fixed shared OCS palette. A modest ambient lift preserves dark walls.
                rgb=np.minimum(255,rgb*5//4)
                distances=((rgb[:,:,None,:]-palette[None,None,:,:])**2).sum(axis=3)
                pixels=(distances.argmin(axis=2)+8).astype(np.uint8)
                pixels[rgba[:,:,3]<128]=0
                raw=encode_columns(pixels)
                if not np.array_equal(decode_columns(raw),pixels): raise ValueError('Column round trip')
                if len(data)%2: data.append(0)
                views.append({'offset':len(data),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
                data.extend(raw)
                if view==0:
                    im=Image.fromarray(pixels,'P'); im.putpalette([0]*24+sum((list(c) for c in SCENERY_RGB),[])+[0]*(768-48))
                    thumbs.append(im.convert('RGB').resize((64,128),Image.Resampling.NEAREST))
            models.append({'source':name,'centre_xy':centre.tolist(),'radius':radius,'bottom':bottom,'top':top,
                           'bounds':m['bounds'],'views':views})
            print('baked',len(models),name,flush=True)
    refs=[]; boxes=[]
    for r in index['references']:
        if r['model_index'] not in model_map: continue
        mi=model_map[r['model_index']]; m=models[mi]; scale=r['scale']; rx,ry,rz=r['rotation_radians']
        c,s=math.cos(rz),math.sin(rz); cx,cy=m['centre_xy']
        wx=r['position'][0]+scale*(cx*c+cy*s); wy=r['position'][1]+scale*(-cx*s+cy*c)
        z=r['position'][2]
        ref={'id':r['id'],'model':mi,'x':round((wx-ORIGIN[0])/16), 'y':round((wy-ORIGIN[1])/16),
             'bottom':round((z+m['bottom']*scale)/16),'top':round((z+m['top']*scale)/16),
             'width':max(1,round(m['radius']*2*scale/16)),
             'rotation':round(rz*256/math.tau)&255,'tilted':abs(rx)+abs(ry)>0.01}
        refs.append(ref)
        if building(m['source']):
            # OBB footprint excludes roof overhang: conservative proxy, not NIF collision.
            lo,hi=m['bounds']; hx=(hi[0]-lo[0])*scale*.40/16+2; hy=(hi[1]-lo[1])*scale*.40/16+2
            boxes.append({'x':ref['x'],'y':ref['y'],'hx':math.ceil(hx),'hy':math.ceil(hy),
                          'cos':round(c*256),'sin':round(s*256),'id':r['id']})
    if len(refs)>512 or len(data)>1800*1024: raise ValueError('Town exceeds this checkpoint budget')
    report={'format':'MWI1','views':8,'source_size':list(SIZE),'palette':SCENERY_RGB,
            'models':models,'references':refs,'collision_boxes':boxes,'sprite_bytes':len(data),
            'source_index_sha256':hashlib.sha256((area/'scenery-index.json').read_bytes()).hexdigest(),
            'limitations':['Upright eight-view impostors; X/Y placement tilt omitted',
                          'Building footprint collision only; no interiors, actors, stairs or physics',
                          'Finite source study radius; scenery resident, music streamed']}
    (out/'town-sprites.bin').write_bytes(data)
    (out/'town.json').write_text(json.dumps(report,indent=2)+'\n')
    sheet=Image.new('RGB',(640,math.ceil(len(thumbs)/10)*150),(35,39,42)); draw=ImageDraw.Draw(sheet)
    for i,im in enumerate(thumbs):
        x=(i%10)*64;y=(i//10)*150;sheet.paste(im,(x,y));draw.text((x,y+130),str(i),fill='white')
    sheet.save(out/'town-atlas-preview.png')
    return report


def include(town, out):
    """Copy derived assets outside source and emit bounded native tables."""
    import shutil
    town=ensure_external(town,'town bake'); out=ensure_external(out,'native build')
    j=json.loads((town/'town.json').read_text()); raw=(town/'town-sprites.bin').read_bytes()
    for m in j['models']:
        for v in m['views']:
            part=raw[v['offset']:v['offset']+v['bytes']]
            if hashlib.sha256(part).hexdigest()!=v['sha256']: raise ValueError('Town payload changed')
            decode_columns(part)
    shutil.copyfile(town/'town-sprites.bin',out/'converted/town-sprites.bin')
    shutil.copyfile(town/'town.json',out/'town.json')
    lines=[f"TOWN_COUNT equ {len(j['references'])}",f"TOWN_BOXES equ {len(j['collision_boxes'])}",
           '        section town_tables,data','town_refs:']
    for r in j['references']:
        lines.append('        dc.w '+','.join(str(r[k]) for k in ('x','y','bottom','top','width','rotation')))
        lines.append(f"        dc.l town_model_{r['model']}")
    lines.append('town_boxes:')
    for b in j['collision_boxes']:
        lines.append('        dc.w '+','.join(str(b[k]) for k in ('x','y','hx','hy','cos','sin')))
    for i,m in enumerate(j['models']):
        lines.append(f'town_model_{i}:')
        lines.append('        dc.l '+','.join('town_pixels+'+str(v['offset']) for v in m['views']))
    lines+=['        section town_images,data','town_pixels:', '        incbin "converted/town-sprites.bin"','        even']
    (out/'town-assets.i').write_text('\n'.join(lines)+'\n')
    return {'models':len(j['models']),'references':len(j['references']),'views_per_model':8,
            'sprite_bytes':len(raw),'collision_boxes':len(j['collision_boxes']), 'limitations':j['limitations']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--area',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();r=prepare(a.area,a.out);print('References:',len(r['references']),'sprite bytes:',r['sprite_bytes'])
