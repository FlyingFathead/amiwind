#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Compile owned static meshes to shared BSP29 submodels with original UVs."""
import argparse, json, math, re, shutil, struct, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image
from mesh_geometry import surface_polygons, collision_parts, split_surface, shell_collision_parts
from prepare_quake import miptex, CENTRE, SCALE
from mwad.paths import ensure_external
from player_hull import MINS, MAXS, PROFILE, rebuild_world_hull
from mwad.scene import read_asset, unpack_geometry
from scenery_selection import select_runtime_refs
from static_lod import reduce_mesh


def bounded_planes(points, equations):
    """Constrain a convex piece before expanding it by the player box.

    Facet offsets alone produce long spikes at acute corners. Six axial
    support planes bound that conservative approximation. These planes are
    redundant for the unexpanded hull, so point/visibility traces are intact.
    This remains an approximate Minkowski sum, not an exact bevel generator.
    """
    low = points.min(axis=0)
    high = points.max(axis=0)
    axial = []
    for axis in range(3):
        n = np.zeros(3); n[axis] = 1
        axial.append([*n, -high[axis]])
        axial.append([*(-n), low[axis]])
    return np.unique(np.round(np.vstack((equations, axial)), 5), axis=0)


def _prepare_model(task):
    mi, m, profile, archive_path = task
    name = m['source']
    with Path(archive_path).open('rb') as archive:
        vv,ff,_=unpack_geometry(read_asset(archive,m));v=np.array(vv);f=np.array(ff)
        lod={};visual_v,visual_f=v,f
        if profile:
         prefixes=profile.get('preserve_shape_prefixes',[])
         matched={prefix:[i for i,mat in enumerate(m['materials'])
                          if mat.get('source_shape','').casefold().startswith(prefix.casefold())]
                  for prefix in prefixes}
         if any(not values for values in matched.values()):raise ValueError('Missing preserved structural shape in '+name)
         keep={i for values in matched.values() for i in values}
         visual_v,visual_f,lod=reduce_mesh(v,f,profile['ratio'],keep)
        collision_v,collision_f=v,f
        if m.get('collision'):
         cv,cf,_=unpack_geometry(read_asset(archive,m['collision']))
         collision_v,collision_f=np.array(cv),np.array(cf)
         lod['collision']='authored RootCollisionNode, approximate convex conversion'
        pieces=(shell_collision_parts(collision_v,collision_f) if profile.get("hollow_collision") else collision_parts(collision_v,collision_f,2))
    polys = surface_polygons(visual_v, visual_f)
    texsize = profile.get('texture_size', 64)
    if texsize not in (16, 32, 64):
        raise ValueError('Unsupported static texture size')
    polys = [(patch, mat, ax, off, normal) for poly, mat, ax, off, normal in polys
             for patch in split_surface(poly, np.column_stack((ax.T*texsize, off*texsize)))]
    # The assembly pass recomputes world-space hulls after each placement.
    pieces = [(points, None, ids, error) for points, hull, ids, error in pieces]
    return mi, (v, f, polys, pieces, lod)


def _instance_key(ref, lighting):
    key=(ref['model_index'],round(ref['scale'],6),round(ref['rotation_radians'][0],6),round(ref['rotation_radians'][1],6))
    return (*key,ref['number']) if lighting and not lighting.get('shared_ambient') else key


def _prepare_placement(task):
    from scipy.spatial import ConvexHull
    from types import SimpleNamespace
    ref, data, texsize, centre, lighting = task
    v,f,polys,components,lod=data
    origin=(np.array(ref['position'])-np.array([*centre,0]))*SCALE
    o=np.zeros(3);yaw=-ref['rotation_radians'][2]*180/math.pi
    rx,ry,rz=-np.array(ref['rotation_radians']);rz=0;cx,sx,cy,sy,cz,sz=np.cos(rx),np.sin(rx),np.cos(ry),np.sin(ry),np.cos(rz),np.sin(rz)
    r=np.array([[cz,-sz,0],[sz,cz,0],[0,0,1]])@np.array([[cy,0,sy],[0,1,0],[-sy,0,cy]])@np.array([[1,0,0],[0,cx,-sx],[0,sx,cx]]);scale=ref['scale']
    yr=math.radians(yaw);rotation=np.array([[math.cos(yr),-math.sin(yr),0],[math.sin(yr),math.cos(yr),0],[0,0,1]])
    surfaces=[]
    for polygon,material,axes,offset,source_normal in polys:
        q=polygon@r.T*scale+o;n=np.cross(q[1]-q[0],q[2]-q[0]);n/=np.linalg.norm(n)
        normal=r@source_normal
        if n@normal<0:q=q[::-1];n=-n
        ax=r@axes/scale*texsize;off=offset*texsize-o@ax
        samples=None
        if lighting:
            from interior_lighting import bake_surface
            samples=bake_surface(q,ax,off,rotation,origin,lighting)
        surfaces.append((q,n,ax,off,material,samples))
    worldparts=[]
    for points,hull,ids,error in components:
        points=points@r.T*scale+o
        worldparts.append((points,SimpleNamespace(equations=ConvexHull(points).equations),ids,error))
    points=v[:,:3]@r.T*SCALE*scale+o
    return surfaces,worldparts,points.min(axis=0)-1,points.max(axis=0)+1


def order_face_planes(lumps, face_planes):
    """Keep 16-bit face indices first; hull planes have full 32-bit indices."""
    count=len(lumps[1])//20
    visible=list(dict.fromkeys(face_planes))
    if len(visible)>65536:raise ValueError('Visible plane budget exceeded')
    seen=set(visible);order=visible+[i for i in range(count) if i not in seen]
    remap={old:new for new,old in enumerate(order)}
    lumps[1]=bytearray().join(lumps[1][i*20:(i+1)*20] for i in order)
    for i,plane in enumerate(face_planes):struct.pack_into('<H',lumps[7],i*20,remap[plane])
    for section,stride in ((5,24),(9,8)):
        for offset in range(0,len(lumps[section]),stride):
            old=struct.unpack_from('<i',lumps[section],offset)[0]
            struct.pack_into('<i',lumps[section],offset,remap[old])


def append_meshes(src, out, scenery, palette, centre=CENTRE, lighting=None, jobs=None):
    b=src.read_bytes();assert struct.unpack_from('<i',b)[0]==29
    lumps=[bytearray(b[o:o+s]) for o,s in [struct.unpack_from('<ii',b,4+k*8) for k in range(15)]]
    face_planes=[struct.unpack_from('<H',lumps[7],i)[0] for i in range(0,len(lumps[7]),20)]
    index=json.loads((scenery/'scenery-index.json').read_text());archive=(scenery/'scenery.mwpak').open('rb')
    pal=Image.new('P',(1,1));pal.putpalette(palette.read_bytes())
    texdata=lumps[2];nt=struct.unpack_from('<i',texdata)[0];offsets=list(struct.unpack_from('<'+str(nt)+'i',texdata,4));textures=[bytes(texdata[o:offsets[k+1] if k+1<nt else len(texdata)]) for k,o in enumerate(offsets)]
    texture_cache={};planes_cache={};texinfo_cache={};models={};report=[]
    profiles={name:profile for group in index.get('groups',{}).values()
              for name,profile in group.get('visual_profiles',{}).items()}
    empty_leaf=next(i for i in range(len(lumps[10])//28) if struct.unpack_from('<i',lumps[10],i*28)[0]==-1)
    def plane(n,d):
     key=tuple(np.round([*n,d],5))
     if key not in planes_cache:
      i=len(lumps[1])//20;planes_cache[key]=i;lumps[1]+=struct.pack('<4fi',*n,d,3)
     return planes_cache[key]
    def texture(m,mi,size):
     mat=m['materials'][mi];ti=mat['texture_index'];key=(ti,size,tuple(round(x,2) for x in mat['diffuse']))
     if key not in texture_cache:
      if ti is None:rgb=np.full((32,32,3),180.)
      else:
       raw=read_asset(archive,index['textures'][ti]);_,w,h=struct.unpack_from('>4sHH',raw);rgb=np.frombuffer(raw[8:],np.uint8).reshape(h,w,4)[:,:,:3].astype(float)
      rgb*=np.array(mat['diffuse']);im=Image.fromarray(np.clip(rgb,0,255).astype(np.uint8)).resize((size,size)).quantize(palette=pal,dither=Image.Dither.NONE)
      t=len(textures);texture_cache[key]=t;textures.append(miptex('surface'+str(t),im))
     return texture_cache[key]
    def collider(pieces):
     # A union of convex volumes. Outside each piece tries the next one.
     roots=[];noderoots=[]
     for k,(points,hull,ids,error) in enumerate(pieces):
      point_eq=np.unique(np.round(hull.equations,5),axis=0)
      eq=bounded_planes(points,point_eq);root=len(lumps[9])//8;noderoot=len(lumps[5])//24;roots.append(root);noderoots.append(noderoot)
      count=len(eq)
      nxt=root+count if k+1<len(pieces) else -1
      low=np.floor(points.min(axis=0)).astype(int);high=np.ceil(points.max(axis=0)).astype(int)
      for j,e in enumerate(eq):
       n=e[:3];d=-e[3]
       # Scaled humanoid standing hull, shared with runtime and world bake.
       expand=sum(-n[a]*MINS[a] if n[a]>=0 else -n[a]*MAXS[a] for a in range(3))
       pi=plane(n,d+expand);inside=root+j+1 if j+1<count else -2
       if max(nxt,inside)>=65520:raise ValueError('Clipnode budget exceeded')
       lumps[9]+=struct.pack('<iHH',pi,nxt&65535,inside&65535)
      # Point traces need no expansion or extra axial nodes. Retain their
      # original hull, saving nodes/RAM and LOS work for proximity greetings.
      nnxt=noderoot+len(point_eq) if k+1<len(pieces) else -empty_leaf-1
      for j,e in enumerate(point_eq):
       n=e[:3];d=-e[3]
       pn=plane(n,d);nin=noderoot+j+1 if j+1<len(point_eq) else -1
       lumps[5]+=struct.pack('<ihh6h2H',pn,nnxt,nin,*low,*high,0,0)
     return noderoots[0],roots[0]
    entities=[];instance_models={};collision_models={}
    def entity(modelnum,origin,yaw,reference):
     return '{\n"classname" "func_wall"\n"aw_ref" "'+str(reference)+'"\n"model" "*'+str(modelnum)+'"\n"origin" "'+' '.join(f'{x:.5f}' for x in origin)+'"\n"angles" "0 '+str(yaw)+' 0"\n}'

    selected, selection_report = select_runtime_refs(index, centre, SCALE, 736)
    unique = dict.fromkeys(ref['model_index'] for ref in selected
                           if not any(t in index['models'][ref['model_index']]['source']
                                      for t in ['flora_', 'marker_', 'scum_', 'lantern_hook', 'furn_de_rope']))
    tasks = [(mi, index['models'][mi], profiles.get(index['models'][mi]['source'], {}),
              scenery/'scenery.mwpak') for mi in unique]
    workers = min(resolve_jobs(jobs), max(1, len(tasks)))
    print(f'BSP geometry workers: {workers}; {len(tasks)} unique models', flush=True)
    models = dict(ordered_map(_prepare_model, tasks, workers))
    def placement_tasks():
     seen=set()
     for ref in selected:
       mi=ref['model_index']
       if mi not in models:continue
       key=_instance_key(ref,lighting)
       if key in seen:continue
       seen.add(key)
       yield ref,models[mi],profiles.get(index['models'][mi]['source'],{}).get('texture_size',64),centre,lighting
    # Geometry and lightmaps are private worker results. BSP offsets, shared
    # palettes and entity order are assigned by this single assembly writer.
    from contextlib import closing
    with closing(ordered_map(_prepare_placement,placement_tasks(),workers)) as placements:
     for ref in selected:
      mi=ref['model_index'];m=index['models'][mi];name=m['source']
      if any(t in name for t in ['flora_','marker_','scum_','lantern_hook','furn_de_rope']):continue
      o=(np.array(ref['position'])-np.array([*centre,0]))*SCALE
      origin=o.copy();o=np.zeros(3);yaw=-ref['rotation_radians'][2]*180/math.pi
      key=_instance_key(ref,lighting)
      if key in instance_models:
       entities.append(entity(instance_models[key],origin,yaw,ref['number']));continue

      v,f,polys,components,lod=models[mi]
      texsize=profiles.get(name,{}).get('texture_size',64)
      surfaces,worldparts,lo,hi=next(placements)
      firstface=len(lumps[7])//20;vmap={};emap={}
      def vertex(p):
       key=tuple(np.round(p,5))
       if key not in vmap:vmap[key]=len(lumps[3])//12;lumps[3]+=struct.pack('<3f',*p)
       return vmap[key]
      for q,n,ax,off,material,samples in surfaces:
       pi=plane(n,float(n@q[0]));t=texture(m,material,texsize);txkey=(*np.round(ax.flatten(),5),*np.round(off,4),t)
       if txkey not in texinfo_cache:
        tx=len(lumps[6])//40;texinfo_cache[txkey]=tx;lumps[6]+=struct.pack('<8fii',*ax[:,0],off[0],*ax[:,1],off[1],t,0)
       tx=texinfo_cache[txkey];verts=[vertex(p) for p in q[::-1]];firstedge=len(lumps[13])//4
       for a,c in zip(verts,verts[1:]+verts[:1]):
        if (a,c) in emap:ed=emap[a,c]
        elif (c,a) in emap:ed=-emap[c,a]
        else:ed=len(lumps[12])//4;emap[a,c]=ed;lumps[12]+=struct.pack('<HH',a,c)
        lumps[13]+=struct.pack('<i',ed)
       lightoffset=-1;styles=(255,255,255,255)
       if samples is not None:
        lightoffset=len(lumps[8]);lumps[8]+=samples;styles=(0,255,255,255)
       face_planes.append(pi)
       lumps[7]+=struct.pack('<Hhihh4Bi',0,0,firstedge,len(verts),tx,*styles,lightoffset)
      collision_key=_instance_key(ref,None)
      if collision_key not in collision_models:
       collision_models[collision_key]=collider(worldparts)
      nroot,croot=collision_models[collision_key]
      modelnum=len(lumps[14])//64;nf=len(lumps[7])//20-firstface
      lumps[14]+=struct.pack('<9f7i',*lo,*hi,0,0,0,nroot,croot,croot,croot,0,firstface,nf)
      instance_models[key]=modelnum;entities.append(entity(modelnum,origin,yaw,ref['number']))
      report.append({'model':name,'faces':nf,'collision_parts':len(components),'scale':ref['scale'],'visual_lod':lod,'texture_size':texsize});print(len(report),name,nf,len(lumps[9])//8,len(lumps[5])//24,flush=True)
      if len(lumps[5])//24>32767 or len(lumps[9])//8>=65520:raise ValueError('Node budget exceeded')
    order_face_planes(lumps,face_planes)
    # New texture table, preserving the original texture payloads.
    tex=bytearray();offs=[]
    for t in textures:offs.append(4+4*len(textures)+len(tex));tex+=t
    lumps[2]=bytearray(struct.pack('<i',len(textures))+struct.pack('<'+'i'*len(offs),*offs)+tex)
    # WAD is compiler input metadata, not a runtime worldspawn field.
    lumps[0]=bytearray(re.sub(rb'(?m)^"wad" "[^"\n]*"\n',b'',bytes(lumps[0])))
    lumps[0]=lumps[0].rstrip(b'\0')+('\n'+'\n'.join(entities)+'\n\0').encode()
    header=bytearray(struct.pack('<i',29)+bytes(120));data=bytearray()
    for k,lump in enumerate(lumps):
     data+=bytes((-len(data))%4);struct.pack_into('<ii',header,4+8*k,124+len(data),len(lump));data+=lump
    out.write_bytes(header+data)
    archive.close()
    result={'models':report,'selection':selection_report,
            'groups':index.get('groups',{}),
            'faces':len(lumps[7])//20,'vertices':len(lumps[3])//12,
            'nodes':len(lumps[5])//24,'clipnodes':len(lumps[9])//8,'bytes':out.stat().st_size,
            'instances':len(entities),'unique_models':len(instance_models),
            'collision':'axis-bounded approximate multipart convex union; standing player hull only',
            'scope':'resident bounded scene, shared building meshes, no cells streamed during play'}
    return result


from build_jobs import add_jobs, resolve_jobs
from build_parallel import ordered_map

def prepare(scene, out, scenery, qbsp, vis, light, jobs=None):
    scene=ensure_external(scene,'source scene');out=ensure_external(out,'mesh BSP scene')
    scenery=ensure_external(scenery,'scenery input')
    shutil.copytree(scene,out)
    text=(out/'seyda.map').read_text()
    pattern=r'\{\n"classname" "aw_static"\n"model" "([^"\n]+\.mdl)"\n"origin" "[^"\n]+"\n"angles" "[^"\n]+"\n\}'
    removed=re.findall(pattern,text)
    if not removed:raise ValueError('No static mesh entities found in scene')
    text=re.sub(pattern,'',text)
    # Replace the old solid house footprints with the separate model hulls.
    text=re.sub(r'\{[^{}]*\bclip\b[^{}]*\}', '', text)
    (out/'seyda.map').write_text(text)
    for name in set(removed):(out/'id1'/name).unlink()
    for executable,options,target in [(qbsp,['-nopercent'],'seyda.map'),(vis,['-fast'],'seyda.bsp'),(light,['-minlight','100'],'seyda.bsp')]:
        subprocess.run([str(Path(executable).resolve()),*(['-threads',str(resolve_jobs(jobs))] if executable!=qbsp else []),*options,target],cwd=out,check=True)
    base=out/'seyda-base.bsp';(out/'seyda.bsp').rename(base)
    rebuild_world_hull(base,out/'seyda.map',qbsp)
    result=append_meshes(base,out/'seyda.bsp',scenery,out/'id1/gfx/palette.lmp',jobs=jobs)
    shutil.copyfile(out/'seyda.bsp',out/'id1/maps/seyda.bsp')
    result['format']='AmiWind compiled mesh BSP29'
    result['standing_hull_profile']=PROFILE
    result['standing_hull']=[MINS,MAXS]
    (out/'scene-ready.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['scene','out','scenery','qbsp','vis','light']:p.add_argument('--'+name,type=Path,required=True)
    add_jobs(p);a=p.parse_args()
    try:print(json.dumps(prepare(a.scene,a.out,a.scenery,a.qbsp,a.vis,a.light,a.jobs),indent=2))
    except (OSError,ValueError,subprocess.CalledProcessError) as e:p.exit(1,str(e)+'\n')

if __name__=='__main__':main()
