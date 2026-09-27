#!/usr/bin/env python3
"""Render static packet turntables on the host to inspect extraction and alpha masks."""
import argparse
import io
import json
import math
from pathlib import Path
import struct
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from mwad.paths import ensure_external
from mwad.scene import read_asset, unpack_geometry


def render(vertices, faces, materials, textures, angle, size=(160,200), frame=None):
    import numpy as np
    from PIL import Image
    v=np.array(vertices); points=v[:,:3]
    c,s=math.cos(angle),math.sin(angle)
    side=points[:,0]*c-points[:,1]*s
    depth=points[:,0]*s+points[:,1]*c
    height=points[:,2]
    width,tall=size
    scale=min((width-12)/max(1,side.max()-side.min()),(tall-12)/max(1,height.max()-height.min()))
    if frame is None:
        x=(side-(side.max()+side.min())/2)*scale+width/2
        y=(height.max()-height)*scale+6
    else:
        lo, hi, bottom, top = frame
        x=(side-lo)*width/(hi-lo)
        y=(top-height)*tall/(top-bottom)
    screen=np.column_stack((x,y,depth)); zbuf=np.full((tall,width),np.inf)
    rgb=np.zeros((tall,width,4),dtype=np.uint8)
    for a,b,c,mi in faces:
        ids=[a,b,c]; t=screen[ids]
        x0=max(0,int(math.floor(t[:,0].min()))); x1=min(width-1,int(math.ceil(t[:,0].max())))
        y0=max(0,int(math.floor(t[:,1].min()))); y1=min(tall-1,int(math.ceil(t[:,1].max())))
        if x1<x0 or y1<y0:continue
        den=(t[1,1]-t[2,1])*(t[0,0]-t[2,0])+(t[2,0]-t[1,0])*(t[0,1]-t[2,1])
        if abs(den)<1e-7:continue
        yy,xx=np.mgrid[y0:y1+1,x0:x1+1];xx=xx+.5;yy=yy+.5
        w0=((t[1,1]-t[2,1])*(xx-t[2,0])+(t[2,0]-t[1,0])*(yy-t[2,1]))/den
        w1=((t[2,1]-t[0,1])*(xx-t[2,0])+(t[0,0]-t[2,0])*(yy-t[2,1]))/den
        w2=1-w0-w1;weights=np.stack((w0,w1,w2),axis=-1)
        z=weights@t[:,2]
        mask=(w0>=-1e-6)&(w1>=-1e-6)&(w2>=-1e-6)&(z<zbuf[y0:y1+1,x0:x1+1])
        if not mask.any():continue
        mat=materials[mi];ti=mat['texture_index']
        if ti is None:texel=np.full((*z.shape,4),255.,dtype=float)
        else:
            texture=textures[ti];uv=weights@v[ids,3:5]
            tx=np.floor(uv[:,:,0]*texture.shape[1]).astype(int)%texture.shape[1]
            ty=np.floor(uv[:,:,1]*texture.shape[0]).astype(int)%texture.shape[0]
            texel=texture[ty,tx].astype(float)
        colour=weights@v[ids,5:9]/255
        texel*=colour
        texel[:,:,:3]*=np.array(mat['diffuse'])
        texel[:,:,3]*=mat['alpha']
        mask &= texel[:,:,3]>=128
        if not mask.any():continue
        texel[:,:,3]=255
        rgb[y0:y1+1,x0:x1+1][mask]=np.clip(texel[mask],0,255).astype(np.uint8)
        zbuf[y0:y1+1,x0:x1+1][mask]=z[mask]
    return Image.fromarray(rgb,'RGBA')


def preview(area,out,queries):
    import numpy as np
    from PIL import Image,ImageDraw,ImageFont
    area=ensure_external(area,'scene input');out=ensure_external(out,'scene preview')
    if out.exists():raise ValueError('Preview already exists')
    index=json.loads((area/'scenery-index.json').read_text())
    chosen=[]
    for q in queries:
        matches=[m for m in index['models'] if q.casefold() in m['source']]
        if len(matches)!=1:raise ValueError('Model query must match exactly once: '+q)
        chosen+=matches
    sheet=Image.new('RGB',(640,len(chosen)*236+48),(25,29,35));draw=ImageDraw.Draw(sheet);font=ImageFont.load_default()
    draw.text((12,10),'STATIC ASSET TRANSLATION / HOST PREVIEW',font=font,fill=(221,204,153))
    draw.text((12,27),'Original geometry + 64px textures. Native scene renderer is pending.',font=font,fill=(180,186,192))
    with (area/'scenery.mwpak').open('rb') as f:
        for row,m in enumerate(chosen):
            vertices,faces,_=unpack_geometry(read_asset(f,m));textures={}
            for ti in m['textures']:
                raw=read_asset(f,index['textures'][ti]);magic,w,h=struct.unpack_from('>4sHH',raw)
                if magic!=b'MWT1' or len(raw)!=8+w*h*4:raise ValueError('Bad texture packet')
                textures[ti]=np.frombuffer(raw[8:],dtype=np.uint8).reshape(h,w,4)
            for i in range(4):
                tile=render(vertices,faces,m['materials'],textures,i*math.pi/2)
                sheet.paste(tile,(i*160,48+row*236),tile)
                draw.text((i*160+8,250+row*236),str(i*90)+' degrees',font=font,fill=(180,186,192))
            draw.text((8,268+row*236),Path(m['source']).name+' / '+str(m['triangles'])+' triangles',font=font,fill=(221,204,153))
    sheet.save(out)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--area',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--model',action='append',required=True)
    a=p.parse_args();preview(a.area,a.out,a.model)
