#!/usr/bin/env python3
"""Bake convex architectural proxies and facade textures for Quake BSP walls."""
import argparse,json,math,re,shutil,struct,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from mwad.paths import ensure_external
from prepare_quake import wad,miptex

def read_wad(path):
    data=path.read_bytes();magic,count,offset=struct.unpack_from('<4sii',data)
    if magic!=b'WAD2':raise ValueError('Expected WAD2')
    result=[]
    for i in range(count):
        pos,size,unpacked,kind,compressed,_,name=struct.unpack_from('<iiiBBH16s',data,offset+i*32)
        if compressed or size!=unpacked or pos<12 or pos+size>offset:raise ValueError('Unsupported WAD lump')
        result.append((name.split(b'\0')[0].decode(),kind,data[pos:pos+size]))
    return result

def prepare(scene,out,scenery):
    import numpy as np
    from PIL import Image
    from scipy.spatial import ConvexHull
    from mwad.scene import read_asset,unpack_geometry
    from preview_scenery import render
    scene=ensure_external(scene,'input scene');out=ensure_external(out,'BSP scene');scenery=ensure_external(scenery,'original scenery')
    shutil.copytree(scene,out)
    source=(out/'seyda.map').read_text();lumps=read_wad(out/'town.wad');models={};details=[];refs=faces_total=0
    index=json.loads((scenery/'scenery-index.json').read_text());archive=(scenery/'scenery.mwpak').open('rb');textures={}
    palette=(out/'id1/gfx/palette.lmp').read_bytes();pal=Image.new('P',(1,1));pal.putpalette(palette)
    for i,t in enumerate(index['textures']):
        raw=read_asset(archive,t);_,w,h=struct.unpack_from('>4sHH',raw);textures[i]=np.frombuffer(raw[8:],np.uint8).reshape(h,w,4)
    pattern=r'\{\n"classname" "aw_static"\n"model" "([^"\n]+\.mdl)"\n"origin" "([^"\n]+)"\n"angles" "([^"\n]+)"\n\}'
    def model(name):
        mi=int(Path(name).stem[1:]);m=index['models'][mi];vv,ff,_=unpack_geometry(read_asset(archive,m));v=np.array(vv);f=np.array(ff,int)
        points=v[:,:3]*.25
        # Fourteen support directions bound brush complexity instead of preserving
        # every tiny bevel from the source model.
        directions=[(x,y,z) for x in (-1,1) for y in (-1,1) for z in (-1,1)]+[(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)]
        selected=np.unique(np.argmax(points@np.array(directions).T,axis=0))
        proxy=np.unique(np.round(points[selected]/4)*4,axis=0)
        if len(proxy)<4 or np.linalg.matrix_rank(proxy-proxy[0])<3:
            low=np.floor(points.min(axis=0));high=np.maximum(low+2,np.ceil(points.max(axis=0)))
            proxy=np.array([(x,y,z) for x in (low[0],high[0]) for y in (low[1],high[1]) for z in (low[2],high[2])])
        hull=ConvexHull(proxy);planes=[];seen=set();lo=points.min(axis=0);hi=points.max(axis=0);texbase=Path(name).stem
        # Bake four facades plus a top projection from the original meshes/textures.
        projections=[]
        for k in range(5):
            view=v.copy()
            if k<4:
                angle=k*math.pi/2;c=math.cos(angle);sn=math.sin(angle)
                side=points[:,0]*c-points[:,1]*sn;bottom=lo[2];top=hi[2]
                low=side.min();high=side.max();u=np.array([c,-sn,0])*64/max(.01,high-low);vaxis=np.array([0,0,-64/max(.01,top-bottom)])
                offsets=[-low*64/max(.01,high-low),top*64/max(.01,top-bottom)]
                im=render(view,f,m['materials'],textures,angle,(64,64),(low/.25,high/.25,bottom/.25,top/.25))
            else:
                view[:,0]=v[:,0];view[:,1]=-v[:,2];view[:,2]=v[:,1]
                u=np.array([64/max(.01,hi[0]-lo[0]),0,0]);vaxis=np.array([0,-64/max(.01,hi[1]-lo[1]),0]);offsets=[-lo[0]*u[0],-hi[1]*vaxis[1]]
                im=render(view,f,m['materials'],textures,0,(64,64),(lo[0]/.25,hi[0]/.25,lo[1]/.25,hi[1]/.25))
            rgb=np.array(im)[:,:,:3].copy();alpha=np.array(im)[:,:,3]
            # Transparent silhouette gaps become muted facade colour on the convex proxy.
            fill=np.median(rgb[alpha>=128],axis=0) if (alpha>=128).any() else np.array([90,80,65])
            rgb[alpha<128]=fill
            pix=Image.fromarray(rgb,'RGB').quantize(palette=pal,dither=Image.Dither.NONE);tex=texbase+str(k);lumps.append((tex,68,miptex(tex,pix)))
            projections.append((tex,u,vaxis,offsets))
        for simplex,equation in zip(hull.simplices,hull.equations):
            normal=equation[:3];key=tuple(np.round(equation,3))
            if key in seen:continue
            seen.add(key)
            if abs(normal[2])>.5:k=4
            else:k=int(round(math.atan2(-normal[0],-normal[1])/(math.pi/2)))%4
            planes.append((proxy[simplex],projections[k]))
        return proxy.mean(axis=0),planes
    def replace(match):
        nonlocal refs,faces_total
        name,position,angles=match.groups();position=np.array(list(map(float,position.split())));yaw=math.radians(float(angles.split()[1]))
        if name not in models:models[name]=model(name)
        centre,planes=models[name];rotation=np.array([[math.cos(yaw),-math.sin(yaw),0],[math.sin(yaw),math.cos(yaw),0],[0,0,1]])
        worldcentre=rotation@centre+position;lines=['{']
        for points,(tex,u,vaxis,offsets) in planes:
            a,b,c=points@rotation.T+position
            if np.dot(np.cross(a-b,c-b),worldcentre-a)>0:b,c=c,b
            plane=' '.join('( '+' '.join(f'{n:.5f}' for n in pt)+' )' for pt in [a,b,c])
            axes=[]
            for axis,off in zip([u,vaxis],offsets):
                axis=rotation@axis;axes.append([*axis,off-float(axis@position)])
            mapping=' '.join('[ '+' '.join(f'{n:.8f}' for n in ax)+' ]' for ax in axes)
            lines.append(f'{plane} {tex} {mapping} 0 1 1')
        lines.append('}');details.append('{\n"classname" "func_detail"\n'+ '\n'.join(lines)+'\n}')
        refs+=1;faces_total+=len(planes);return ''
    source=re.sub(pattern,replace,source);archive.close()
    if not refs:raise ValueError('No static model entities found')
    (out/'seyda.map').write_text(source+'\n'+'\n'.join(details)+'\n');(out/'town.wad').write_bytes(wad(lumps))
    for name in models:(out/'id1'/name).unlink()
    report={'static_references_moved_to_bsp':refs,'convex_brushes':refs,'brush_planes':faces_total,'unique_models':len(models),'facade_size':64,'collision':'solid convex hull proxies plus existing footprint clips; doorways and undercuts simplified','scope':'bounded static wall-renderer experiment; no chunk streaming'}
    (out/'bsp-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--scene',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--scenery',type=Path,required=True);a=p.parse_args();prepare(a.scene,a.out,a.scenery)
