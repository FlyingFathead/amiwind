#!/usr/bin/env python3
"""Convert a bounded owned Seyda Neen scene to Quake-format intermediates."""
import argparse, hashlib, io, json, math, struct, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from mwad.paths import ensure_external, read_workspace, resolve_data_files, child_ci
from mwad.scene import read_asset, unpack_geometry
from mwad.audit import BSA, normpath
from prepare_scenery import bsa_read
from preview_scenery import render
from debug_font import readable_atlas
from build_jobs import add_jobs, resolve_jobs
from area_config import BOUNDS
from build_parallel import ordered_map

CENTRE=(-11264,-71680)
SCALE=.25
# TEMPORARY DEMO PLACEHOLDER: a larger flat sea hides the small slice boundary.
# Replace with actual surrounding cells/coastline after the basics are stable.
# This does not convert islands, add world streaming or promise an infinite sea.
SEA_EXTENT=2048


def wad(lumps):
    body=bytearray(); directory=bytearray()
    for name,kind,data in lumps:
        if len(name.encode('ascii'))>15:raise ValueError('Long WAD name')
        directory.extend(struct.pack('<iiiBBH16s',12+len(body),len(data),len(data),kind,0,0,name.encode()))
        body.extend(data)
    return struct.pack('<4sii',b'WAD2',len(lumps),12+len(body))+body+directory


def miptex(name,pixels):
    from PIL import Image
    w,h=pixels.size
    if w%16 or h%16:raise ValueError('Texture dimensions must be multiples of 16')
    levels=[pixels.resize((w>>i,h>>i),Image.Resampling.NEAREST).tobytes() for i in range(4)]
    offsets=[40]
    for raw in levels[:-1]:offsets.append(offsets[-1]+len(raw))
    return struct.pack('<16s6I',name.encode(),w,h,*offsets)+b''.join(levels)


def mdl(points,faces,uv,skin):
    import numpy as np
    if not len(faces) or len(points)>1999:raise ValueError('Alias model vertex budget')
    points=np.asarray(points,float);lo=points.min(axis=0);hi=points.max(axis=0)
    scale=np.maximum((hi-lo)/255,.0001);xyz=np.clip(np.rint((points-lo)/scale),0,255).astype(np.uint8)
    w,h=skin.size
    header=struct.pack('<4si3f3ff3f8if',b'IDPO',6,*scale,*lo,float(np.linalg.norm(points,axis=1).max()),0,0,0,1,w,h,len(points),len(faces),1,0,0,1.)
    data=bytearray(header);data.extend(struct.pack('<i',0));data.extend(skin.tobytes())
    for u,v in uv:data.extend(struct.pack('<iii',0,u,v))
    for a,b,c in faces:data.extend(struct.pack('<4i',1,a,b,c))
    data.extend(struct.pack('<i4B4B16s',0,0,0,0,0,255,255,255,0,b'world'))
    for p in xyz:data.extend(bytes([*p,0]))
    return bytes(data)


def brush(points,faces,texture):
    """Convex face planes, Quake MAP winding; interior on the negative side."""
    import numpy as np
    points=np.array(points,float);centre=points.mean(axis=0);lines=['{']
    for ids in faces:
        a,b,c=points[list(ids)][:3]
        # MAP uses cross(a-b,c-b), opposite the usual triangle convention.
        if np.dot(np.cross(a-b,c-b),centre-a)>0:b,c=c,b
        line=' '.join('( '+' '.join(f'{v:.3f}' for v in p)+' )' for p in (a,b,c))
        lines.append(line+' '+texture+' 0 0 0 1 1')
    return '\n'.join(lines+['}'])


def box(lo,hi,tex,rotation=0):
    import numpy as np
    x0,y0,z0=lo;x1,y1,z1=hi
    p=np.array([[x0,y0,z0],[x1,y0,z0],[x1,y1,z0],[x0,y1,z0],[x0,y0,z1],[x1,y0,z1],[x1,y1,z1],[x0,y1,z1]],float)
    if rotation:
        centre=(p[:,:2].min(axis=0)+p[:,:2].max(axis=0))/2;c=math.cos(rotation);s=math.sin(rotation)
        p[:,:2]=(p[:,:2]-centre)@np.array([[c,s],[-s,c]])+centre
    return brush(p,[(0,1,2),(4,5,6),(0,1,5),(1,2,6),(2,3,7),(3,0,4)],tex)


def _preview_model(task):
    import numpy as np
    from PIL import Image
    import fast_simplification
    mi, m, packet, textures, palette, grouped_models = task
    pal=Image.new('P',(1,1));pal.putpalette(palette)
    def quantize(im):return im.convert('RGB').quantize(palette=pal,dither=Image.Dither.NONE)
    name=m['source']
    if any(t in name for t in ['marker_','scum_','lantern_hook','furn_de_rope']):return mi,None,None,None
    # Assemblies go directly through the shared BSP mesh pass. The
    # discarded legacy alias preview cannot represent a whole ship;
    # forcing it through that vertex budget can stop a valid BSP build.
    if mi in grouped_models and 'flora_' not in name:
        return mi,None,None,{'model':name,'kind':'deferred BSP assembly'}
    vv,ff,_=unpack_geometry(packet);v=np.array(vv);f=np.array(ff,int)
    if 'flora_' in name:
        centre=(v[:,:2].min(axis=0)+v[:,:2].max(axis=0))/2;v[:,:2]-=centre
        radius=float(np.linalg.norm(v[:,:2],axis=1).max());bottom=v[:,2].min();top=v[:,2].max()
        w=max(1,math.ceil(radius*2*SCALE));h=max(1,math.ceil((top-bottom)*SCALE))
        rgba=render(v,f,m['materials'],textures,0,(w,h),(-radius,radius,bottom,top))
        pix=np.array(quantize(rgba));pix[np.array(rgba)[:,:,3]<128]=255
        raw=struct.pack('<4siifiiifi',b'IDSP',1,2,radius*SCALE,w,h,1,0.,0)
        raw+=struct.pack('<5i',0,-w//2,round(top*SCALE),w,h)+pix.tobytes()
        path=f'progs/m{mi:03}.spr'
        return mi,raw,(path,centre.tolist(),0),{'model':name,'kind':'sprite','bytes':len(raw)}
    # Weld positions, decimate, then bake a separate small texture triangle per face.
    points,inverse=np.unique(np.round(v[:,:3],5),axis=0,return_inverse=True)
    faces=inverse[f[:,:3]];target=280 if any(t in name for t in ['house','shack','tower','lighthouse']) else 100
    if len(faces)>target:
        points,faces=fast_simplification.simplify(points,faces.astype(np.int32),target_count=target)
    if len(faces)>600:raise ValueError('Simplification exceeded alias budget')
    skin=Image.new('RGB',(256,256));uv=[];outpoints=[];outfaces=[]
    orig_centres=v[f[:,:3],:3].mean(axis=1)
    for fi,face in enumerate(faces):
        triangle=points[face];mid=triangle.mean(axis=0)
        oi=int(np.argmin(((orig_centres-mid)**2).sum(axis=1)));old=v[f[oi,:3]];mat=m['materials'][f[oi,3]]
        # Project onto the nearest original triangle for a bounded UV bake.
        basis=np.column_stack((old[1,:3]-old[0,:3],old[2,:3]-old[0,:3]));inv=np.linalg.pinv(basis)
        coords=(triangle-old[0,:3])@inv.T
        texuv=old[0,3:5]+coords[:,0,None]*(old[1,3:5]-old[0,3:5])+coords[:,1,None]*(old[2,3:5]-old[0,3:5])
        tile=np.zeros((8,8,3),np.uint8)
        for y in range(8):
            for x in range(8):
                weights=np.array([max(0.,1-(x+y)/7),x/7,y/7]);weights/=weights.sum()
                if mat['texture_index'] is None:colour=np.array([180.,180.,180.])
                else:
                    t=textures[mat['texture_index']];u,w=weights@texuv
                    colour=t[int(math.floor(w*t.shape[0]))%t.shape[0],int(math.floor(u*t.shape[1]))%t.shape[1],:3].astype(float)
                colour*=np.array(mat['diffuse'])*np.mean(old[:,5:8],axis=0)/255
                tile[y,x]=np.clip(colour*1.25,0,255)
        tx=(fi%32)*8;ty=(fi//32)*8;skin.paste(Image.fromarray(tile,'RGB'),(tx,ty))
        uv.extend([(tx,ty),(tx+7,ty),(tx,ty+7)])
        start=len(outpoints);outpoints.extend((triangle*SCALE).tolist());outfaces.append([start,start+2,start+1])
    path=f'progs/m{mi:03}.mdl';raw=mdl(outpoints,outfaces,uv,quantize(skin))
    return mi,raw,(path,[0,0],len(faces)),{'model':name,'kind':'mesh','source_triangles':len(f),'triangles':len(faces),'bytes':len(raw)}


def prepare(workspace,scene,out,jobs=None):
    import numpy as np
    from PIL import Image,ImageDraw,ImageFont
    import fast_simplification
    workspace,state=read_workspace(workspace);scene=ensure_external(scene,'scenery');out=ensure_external(out,'Quake scene')
    if out.exists():raise ValueError('Output already exists')
    out.mkdir(parents=True);game=out/'id1';(game/'gfx').mkdir(parents=True);(game/'progs').mkdir();(game/'maps').mkdir()
    index=json.loads((scene/'scenery-index.json').read_text());textures={}
    with (scene/'scenery.mwpak').open('rb') as f:
        for i,t in enumerate(index['textures']):
            raw=read_asset(f,t);magic,w,h=struct.unpack_from('>4sHH',raw)
            if magic!=b'MWT1':raise ValueError('Texture magic')
            textures[i]=np.frombuffer(raw[8:],np.uint8).reshape(h,w,4)
    bsa=BSA(child_ci(resolve_data_files(state['data_files']),'Morrowind.bsa'))
    ground={};materials=json.loads((workspace/'generated/seyda-neen/materials.json').read_text())
    for key,m in materials.items():
        if not m.get('texture'):continue
        path=normpath('textures/'+m['texture']); candidates=[str(Path(path).with_suffix('.dds')),path]
        source=next(p for p in candidates if p in bsa.entries)
        ground[int(key)]=Image.open(io.BytesIO(bsa_read(bsa,source))).convert('RGB').resize((32,32),Image.Resampling.BOX)
    samples=np.concatenate([t[:,:,:3].reshape(-1,3)[::4] for t in textures.values()]+[np.array(i).reshape(-1,3) for i in ground.values()])
    strip=Image.fromarray(samples.astype(np.uint8).reshape(1,-1,3),'RGB').quantize(colors=224)
    palette=strip.getpalette()[:672]+[102,119,136]*30+[238,221,170,0,0,0]
    pal=Image.new('P',(1,1));pal.putpalette(palette)
    def quantize(im):return im.convert('RGB').quantize(palette=pal,dither=Image.Dither.NONE)
    (game/'gfx/palette.lmp').write_bytes(bytes(palette))
    colours=np.array(palette,float).reshape(256,3);fog=bytearray()
    for level in range(16):
        rgb=colours*(1-level/15)+np.array([102,119,136])*level/15
        fog.extend(np.argmin(((rgb[:,None,:]-colours[None,:,:])**2).sum(axis=2),axis=1).astype(np.uint8).tobytes())
    (game/'gfx/fog.lmp').write_bytes(fog)
    cmap=bytearray()
    for level in range(64):
        rgb=np.array(palette,np.uint8).reshape(1,256,3).astype(float)*max(.15,1-level/63)
        cmap.extend(quantize(Image.fromarray(rgb.astype(np.uint8),'RGB')).tobytes())
    (game/'gfx/colormap.lmp').write_bytes(cmap)
    # Original project graphics, generated from host fonts; no Quake artwork.
    font=ImageFont.truetype('DejaVuSansMono.ttf',8);chars=Image.new('P',(128,128),0);chars.putpalette(palette);d=ImageDraw.Draw(chars)
    for c in range(256):
        if 32<=c%128<127:d.text(((c%16)*8,(c//16)*8-1),chr(c%128),font=font,fill=254)
    # Preserve the prior atlas byte-for-byte on disk; only one font is active.
    (game/'gfx/font-retro.lmp').write_bytes(chars.tobytes())
    readable=readable_atlas()
    (game/'gfx/font-readable.lmp').write_bytes(readable)
    lumps=[('conchars',64,readable)]
    for name in ['disc','backtile','ram','net','turtle']:
        im=Image.new('P',(24,24),224);lumps.append((name,66,struct.pack('<ii',24,24)+im.tobytes()))
    (game/'gfx.wad').write_bytes(wad(lumps))
    for name,size,label in [('conback',(320,200),'AmiWind development console'),('loading',(160,24),'Loading AmiWind...'),('pause',(80,24),'Paused')]:
        im=Image.new('P',size,224);im.putpalette(palette);d=ImageDraw.Draw(im);d.text((8,8),label,font=font,fill=254)
        (game/'gfx'/f'{name}.lmp').write_bytes(struct.pack('<ii',*size)+im.tobytes())
    generated={};reports=[]
    grouped_models={r['model_index'] for r in index['references'] if r.get('scene_groups')}
    def tasks():
        with (scene/'scenery.mwpak').open('rb') as archive:
            for mi,m in enumerate(index['models']):
                used={mat['texture_index'] for mat in m['materials'] if mat['texture_index'] is not None}
                yield mi,m,read_asset(archive,m),{ti:textures[ti] for ti in used},palette,grouped_models
    workers=min(resolve_jobs(jobs),max(1,len(index['models'])))
    print(f'Scene preview workers: {workers}',flush=True)
    for mi,raw,generated_model,report in ordered_map(_preview_model,tasks(),workers):
        if report is not None:reports.append(report)
        if generated_model is not None:
            generated[mi]=generated_model
            (game/generated_model[0]).write_bytes(raw)
        print('preview',mi+1,'/',len(index['models']),flush=True)
    # A tiny original player placeholder; first-person view does not draw itself.
    skin=Image.new('P',(16,16),224)
    (game/'progs/player.mdl').write_bytes(mdl([[0,0,0],[1,0,0],[0,1,0]],[[0,1,2]],[(0,0),(1,0),(0,1)],skin))
    # Ground and liquids keep actual LAND heights and material assignment.
    grids=json.loads((workspace/'generated/seyda-neen/terrain-source.json').read_text());cells={tuple(g['cell']):g for g in grids}
    def terrain(wx,wy):
        cx=math.floor(wx/8192);cy=math.floor(wy/8192);g=cells[cx,cy]
        ix=round((wx-cx*8192)/128);iy=round((wy-cy*8192)/128)
        return g['heights'][iy][ix],g['materials'][min(15,iy//4)][min(15,ix//4)]
    terrain_lumps=[(f'g{k}',68,miptex(f'g{k}',quantize(im))) for k,im in ground.items()]
    for n,c in [('stone',(80,79,70)),('*water',(65,87,91)),('sky',(102,119,136)),('clip',(0,0,0))]:
        im=Image.new('RGB',(64 if n!='sky' else 256,64 if n!='sky' else 128),c)
        terrain_lumps.append((n,68,miptex(n,quantize(im))))
    (out/'town.wad').write_bytes(wad(terrain_lumps))
    brushes=[];extent=max(abs(v) for b in BOUNDS for v in b);step=128
    tiles=[]
    for y in range(BOUNDS[0][1],BOUNDS[1][1],step):
        for x in range(BOUNDS[0][0],BOUNDS[1][0],step):
            # Preserve original LAND vertices around the steep port approaches.
            # Coarse interpolation here cut through the original ground/rocks.
            detail=32 if 0<=x<896 and 256<=y<1024 else step
            tiles.extend((xx,yy,detail) for yy in range(y,y+step,detail) for xx in range(x,x+step,detail))
    for x,y,step in tiles:
        corners=[];material=0
        for dx,dy in [(0,0),(step,0),(step,step),(0,step)]:
            z,material=terrain(CENTRE[0]+(x+dx)/SCALE,CENTRE[1]+(y+dy)/SCALE);corners.append([x+dx,y+dy,z*SCALE])
        for ids in [(0,1,2),(0,2,3)]:
            tri=[corners[i] for i in ids];pts=tri+[[p[0],p[1],-512] for p in tri]
            brushes.append(brush(pts,[(0,1,2),(3,4,5),(0,1,4),(1,2,5),(2,0,3)],f'g{material}'))
    # Extend only the simple sea/enclosure. Terrain and object selection keep
    # their smaller bounds; this is a backdrop, not an archipelago conversion.
    sea=SEA_EXTENT
    brushes.append(box([-sea,-sea,-500],[sea,sea,0],'*water'))
    brushes+= [box([-sea-32,-sea-32,-544],[sea+32,sea+32,-512],'stone'),
               box([-sea-32,-sea-32,512],[sea+32,sea+32,544],'sky'),
               box([-sea-32,-sea-32,-512],[-sea,sea+32,512],'sky'),
               box([sea,-sea-32,-512],[sea+32,sea+32,512],'sky'),
               box([-sea,-sea-32,-512],[sea,-sea,512],'sky'),
               box([-sea,sea,-512],[sea,sea+32,512],'sky')]
    entities=[];refs=0
    for r in index['references']:
        mi=r['model_index']
        if mi not in generated:continue
        path,centre,tris=generated[mi];pos=list(r['position']);rx,ry,rz=r['rotation_radians'];scale=r['scale']
        # Alias format has no per-instance scale. Bake variants if needed in later pass.
        if abs(scale-1)>0.02:continue
        pos[0]+=centre[0]*math.cos(rz)+centre[1]*math.sin(rz);pos[1]+=-centre[0]*math.sin(rz)+centre[1]*math.cos(rz)
        local=[(pos[0]-CENTRE[0])*SCALE,(pos[1]-CENTRE[1])*SCALE,pos[2]*SCALE]
        if not all(BOUNDS[0][a]<=local[a]<=BOUNDS[1][a] for a in range(2)):continue
        name=index['models'][mi]['source'];refs+=1
        entities.append('{\n"classname" "aw_static"\n"model" "'+path+'"\n"origin" "'+' '.join(f'{n:.3f}' for n in local)+'"\n"angles" "0 '+str(-rz*180/math.pi)+' 0"\n}')
        if any(t in name for t in ['house_','shack_02','shack_03','lighthouse','tower_thatch']):
            lo,hi=index['models'][mi]['bounds'];cx=(lo[0]+hi[0])/2;cy=(lo[1]+hi[1])/2
            bx=(pos[0]-CENTRE[0]+cx*math.cos(rz)+cy*math.sin(rz))*SCALE;by=(pos[1]-CENTRE[1]-cx*math.sin(rz)+cy*math.cos(rz))*SCALE
            hx=(hi[0]-lo[0])*.38*SCALE;hy=(hi[1]-lo[1])*.38*SCALE
            brushes.append(box([bx-hx,by-hy,max(-500,(pos[2]+lo[2])*SCALE)],[bx+hx,by+hy,(pos[2]+hi[2])*SCALE],'clip',-rz))
    spawn=[(-11200-CENTRE[0])*SCALE,(-71504-CENTRE[1])*SCALE,terrain(-11200,-71504)[0]*SCALE+32]
    entities.append('{\n"classname" "info_player_start"\n"origin" "'+' '.join(map(str,spawn))+'"\n"angle" "90"\n}')
    text='{\n"classname" "worldspawn"\n"wad" "town.wad"\n"message" "AmiWind / Seyda Neen"\n'+ '\n'.join(brushes)+'\n}\n'+'\n'.join(entities)+'\n'
    (out/'seyda.map').write_text(text)
    config='''unbindall
bind w +forward
bind s +back
bind a +moveleft
bind d +moveright
bind LEFTARROW +left
bind RIGHTARROW +right
bind SPACE +jump
bind SHIFT +speed
bind ESCAPE quit
bind ` toggleconsole
bind F10 toggleconsole
bind e +moveup
bind q +movedown
+mlook
sensitivity 3
cl_forwardspeed 120
cl_backspeed 120
cl_sidespeed 120
cl_movespeedkey 1.8
viewsize 120
crosshair 1
r_ambient 128
r_fullbright 0
r_drawviewmodel 0
bind F6 aw_music_next
bind F8 aw_music_mode
bgmvolume 0.6
_snd_mixahead 0.3
r_maxsurfs 12288
r_maxedges 24576
map seyda
'''
    (game/'quake.rc').write_text('exec default.cfg\nexec autoexec.cfg\n');(game/'default.cfg').write_text(config);(game/'autoexec.cfg').write_text('')
    report={'format':'AmiWind Quake scene experiment','scale':SCALE,'centre':CENTRE,'extent':extent,'bounds':BOUNDS,'sea_extent':SEA_EXTENT,'references':refs,'models':reports,'spawn':spawn,
            'scope':'bounded LAND + reduced alias meshes + alpha tree sprites + approximate building clip brushes; no actors/interiors/quests; non-unit scale references currently omitted'}
    (out/'scene-report.json').write_text(json.dumps(report,indent=2)+'\n');print('references',refs,'brushes',len(brushes));return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--workspace',type=Path,required=True);p.add_argument('--scene',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    add_jobs(p);a=p.parse_args();prepare(a.workspace,a.scene,a.out,a.jobs)
