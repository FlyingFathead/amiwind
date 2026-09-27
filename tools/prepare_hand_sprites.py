#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Bake the locally converted first-person MDL into bounded opaque sprite spans.

The 3D model is retained byte-for-byte. Only the selected runtime build changes.
160x100 source frames are drawn at integer scale; transparent pixels use no span.
"""
from pathlib import Path
import argparse,json,struct
import numpy as np


def decode_mdl(raw):
    h=struct.unpack_from('<4si3f3ff3f8if',raw)
    if h[:2]!=(b'IDPO',6):raise ValueError('Expected generated MDL6')
    scale=np.array(h[2:5]);origin=np.array(h[5:8]);skins,w,height,nv,nt,nf=h[12:18]
    if skins!=1 or not 1<=nf<=32 or not 1<=nv<=1999:raise ValueError('Unsupported first-person model')
    at=84
    if struct.unpack_from('<i',raw,at)[0]:raise ValueError('Grouped skin unsupported')
    at+=4;skin=np.frombuffer(raw,np.uint8,w*height,at).reshape(height,w);at+=w*height
    uv=np.frombuffer(raw,'<i4',nv*3,at).reshape(nv,3)[:,1:];at+=nv*12
    faces=np.frombuffer(raw,'<i4',nt*4,at).reshape(nt,4)[:,1:];at+=nt*16
    frames=[]
    for i in range(nf):
        if struct.unpack_from('<i',raw,at)[0]:raise ValueError('Grouped frame unsupported')
        at+=28;frames.append(np.frombuffer(raw,np.uint8,nv*4,at).reshape(nv,4)[:,:3]*scale+origin);at+=nv*4
    if at!=len(raw):raise ValueError('Unexpected model data')
    return np.array(frames),faces,uv,skin


def render_frame(points,faces,uv,skin):
    width,height=160,100;image=np.full((height,width),255,np.uint8);depth=np.zeros((height,width))
    # One stable camera, no walk bob, world depth or fog baked into first person.
    for face in faces:
        poly=[np.r_[points[i],uv[i]] for i in face];out=[]
        for a,b in zip(poly,poly[1:]+poly[:1]):
            if a[0]>=.5:out.append(a)
            if (a[0]>=.5)!=(b[0]>=.5):out.append(a+(b-a)*((.5-a[0])/(b[0]-a[0])))
        if len(out)<3:continue
        for k in range(1,len(out)-1):
            v=np.array([out[0],out[k],out[k+1]]);iz=1/v[:,0]
            xy=np.column_stack((80-v[:,1]*iz*80,50-v[:,2]*iz*80))
            low=np.maximum(np.floor(xy.min(0)).astype(int),0);high=np.minimum(np.ceil(xy.max(0)).astype(int),[159,99])
            if np.any(low>high):continue
            matrix=np.vstack((xy.T,np.ones(3)))
            if abs(np.linalg.det(matrix))<1e-6:continue
            yy,xx=np.mgrid[low[1]:high[1]+1,low[0]:high[0]+1]
            weights=(np.linalg.inv(matrix)@np.stack((xx+.5,yy+.5,np.ones_like(xx)),axis=0).reshape(3,-1)).T
            z=weights@iz;inside=np.all(weights>=-1e-7,axis=1)
            target=depth[low[1]:high[1]+1,low[0]:high[0]+1];mask=inside.reshape(xx.shape)&(z.reshape(xx.shape)>target)
            if not mask.any():continue
            tex=((weights@(v[:,3:]*iz[:,None]))/np.maximum(z[:,None],1e-9)).reshape(*xx.shape,2)
            u=np.clip(np.rint(tex[:,:,0]).astype(int),0,skin.shape[1]-1);t=np.clip(np.rint(tex[:,:,1]).astype(int),0,skin.shape[0]-1)
            pixels=skin[t,u].copy();pixels[pixels==255]=0 # opaque black, not a transparency hole
            dst=image[low[1]:high[1]+1,low[0]:high[0]+1];dst[mask]=pixels[mask];target[mask]=z.reshape(xx.shape)[mask]
    return image


def pack_frame(frame):
    rows=[]
    for row in frame:
        runs=[];x=0
        while x<len(row):
            if row[x]==255:x+=1;continue
            start=x
            while x<len(row) and row[x]!=255:x+=1
            runs.append(struct.pack('>HH',start,x-start)+row[start:x].tobytes())
        rows.append(struct.pack('>H',len(runs))+b''.join(runs))
    return b''.join(rows)


def prepare(scene):
    frames,faces,uv,skin=decode_mdl((scene/'id1/progs/v_nord.mdl').read_bytes())
    rendered=[render_frame(p,faces,uv,skin) for p in frames];payload=[pack_frame(f) for f in rendered]
    header=12+4*(len(frames)+1);offsets=[header]
    for data in payload:offsets.append(offsets[-1]+len(data))
    raw=struct.pack('>4s4H',b'AWS1',160,100,len(frames),0)+struct.pack('>'+str(len(offsets))+'I',*offsets)+b''.join(payload)
    if len(raw)>512*1024:raise ValueError('Sprite memory budget exceeded')
    (scene/'id1/gfx/hands.aws').write_bytes(raw)
    report={'frames':len(frames),'source_size':[160,100],'bytes':len(raw),'opaque_pixels':[int((f!=255).sum()) for f in rendered],
            'source_model_retained':True,'lighting':'fixed neutral bake; no dynamic first-person lighting yet','format':'AWS1 bounded row spans'}
    (scene/'hand-sprites-report.json').write_text(json.dumps(report,indent=2)+'\n')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--scene',type=Path,required=True);a=p.parse_args();print(json.dumps(prepare(a.scene),indent=2))
