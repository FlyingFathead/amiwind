# SPDX-License-Identifier: GPL-3.0-only
"""Direct canonical LAND world render cuts; physical LAND alignment is a gate.

Authored upward LAND render faces remain unchanged in this bounded host stage.
Consequently the result MUST remain INCOMPLETE until surface/physics agreement
is demonstrated or coherent terrain reconstruction is applied upstream.
"""
import struct,collections
import numpy as np
from player_hull import lumps,pack_lumps
from replace_bsp_world import rows,FORMATS,texture_blobs,verify_collision
from compact_bsp import compact
from canonical_face_clip import CanonicalClipper
from terrain_visual_cull import _area
def name(blob):return '' if blob is None else blob[:16].split(b'\0')[0].decode('ascii')
def pack_textures(blobs):
 out=bytearray(struct.pack('<i',len(blobs))+bytes(4*len(blobs)))
 for i,blob in enumerate(blobs):
  struct.pack_into('<i',out,4+4*i,-1 if blob is None else len(out))
  if blob is not None:out.extend(blob)
 return out
def retain_sky_textures(compacted,original):
 """Append exact original sky resources; existing texture indices stay stable."""
 blobs=texture_blobs(compacted);present={name(b):b for b in blobs if b is not None};added=[]
 for blob in texture_blobs(original):
  if not name(blob).startswith('sky'):continue
  if name(blob) in present:
   if present[name(blob)]!=blob:raise ValueError('Sky resource bytes changed')
  else:blobs.append(blob);present[name(blob)]=blob;added.append(name(blob))
 return pack_textures(blobs),added
def _quantize_horizontal_water(polygon, source, clip):
    """Keep float32 cuts on the retained side without changing water height.

    A nearest float32 XY rounding can cross the terrain boundary. Move by the
    smallest representable XY steps down the actual LAND gradient, only when
    the declared boundary tolerance is exceeded. Never widen tolerance or leave
    the convex source face. Nonhorizontal water uses the ordinary writer.
    """
    original=np.asarray(polygon,dtype=float)
    p=np.asarray(polygon,dtype='<f4').astype(float)
    if np.ptp(np.asarray(source)[:,2])!=0:return p,0
    source=np.asarray(source,dtype=float);signed=sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(source,np.roll(source,-1,axis=0)))
    sign=1 if signed>0 else -1;steps=0
    for original_point,point in zip(original,p):
        gx=original_point[0]+clip.land.origin[0];gy=original_point[1]+clip.land.origin[1]
        on_x=abs(gx/32-round(gx/32))<1e-10
        on_y=abs(gy/32-round(gy/32))<1e-10
        diagonal=original_point[0]-original_point[1]
        on_diagonal=abs((gx-gy)/32-round((gx-gy)/32))<1e-10
        # Tile lines are exact powers-of-two coordinates. A diagonal's two
        # coordinates need common precision to keep their difference exact.
        quantum=max(abs(float(np.spacing(np.float32(point[0])))),abs(float(np.spacing(np.float32(point[1])))))
        if on_diagonal and not on_x and not on_y:
            point[0]=float(np.float32(round(original_point[0]/quantum)*quantum))
            point[1]=float(np.float32(point[0]-diagonal))
        sample=clip.land.sample(float(point[0]),float(point[1]))
        if sample is None:raise ValueError('Missing canonical water boundary coverage')
        if point[2]+clip.overlap-sample['height']>=-clip.boundary_tolerance:continue
        for attempt in range(16):
            gx=point[0]+clip.land.origin[0];gy=point[1]+clip.land.origin[1]
            tx=int(np.floor(gx/32));ty=int(np.floor(gy/32))
            u=gx/32-tx;v=gy/32-ty
            tri=clip.tile(tx,ty)[0 if v<=u else 1]
            n=np.cross(tri[1]-tri[0],tri[2]-tri[0]);gradient=-n[:2]/n[2]
            candidate=point.copy()
            if on_x and on_y:raise ValueError('Cannot move a canonical tile corner')
            if on_diagonal and not on_x and not on_y:
                rate=float(gradient.sum())
                if rate==0:raise ValueError('Cannot snap constant-height diagonal')
                offset=-quantum if rate>0 else quantum
                candidate[:2]=[float(np.float32(point[0]+offset)),float(np.float32(point[1]+offset))]
            else:
                axis=1 if on_x else (0 if on_y else int(np.argmax(abs(gradient))))
                if gradient[axis]==0:raise ValueError('Cannot snap horizontal water to retained LAND side')
                candidate[axis]=float(np.nextafter(np.float32(point[axis]),np.float32(-np.inf if gradient[axis]>0 else np.inf)))
            if any(sign*((b[0]-a[0])*(candidate[1]-a[1])-(b[1]-a[1])*(candidate[0]-a[0])) < -1e-8 for a,b in zip(source,np.roll(source,-1,axis=0))):
                raise ValueError('Water retention snap would leave the source face')
            point[:]=candidate;steps+=1
            sample=clip.land.sample(float(point[0]),float(point[1]))
            if sample is None:raise ValueError('Missing canonical water snap coverage')
            if point[2]+clip.overlap-sample['height']>=0:break
        else:raise ValueError('Water retention snap did not converge')
    return p,steps

def _stable_horizontal_water_parts(parts, source, clip):
    """Actually reclip quantized pieces; bounded failure never retains residuals."""
    if np.ptp(np.asarray(source)[:,2])!=0:return parts,0,0,0
    pending=[(p,0) for p in reversed(parts)];stable=[];steps=recuts=maximum_depth=0
    while pending:
        p,depth=pending.pop();quantized,moved=_quantize_horizontal_water(p,source,clip)
        steps+=moved;maximum_depth=max(maximum_depth,depth)
        if len(quantized)<3 or _area(quantized)==0:continue
        next_parts=clip.clip(quantized)
        if len(next_parts)==1 and np.array_equal(next_parts[0],quantized):
            stable.append(source if p is source and np.array_equal(quantized,source) else quantized)
            continue
        if depth>=8:
            if depth==8 and isinstance(clip,CanonicalClipper):
                # Only the exceptional merged piece gets partitioned. Each
                # atomic piece stays within one authoritative affine triangle.
                next_parts=clip.clip(quantized,merge=False)
            else:raise ValueError('Quantized canonical water cut is not repeat-stable')
        recuts+=1;pending.extend((piece,depth+1) for piece in reversed(next_parts))
    return stable,steps,recuts,maximum_depth

def cull_world_render(raw,land,policy):
    if not policy['enabled']:return raw,{'unchanged':True}
    data=lumps(raw);original_data=lumps(raw);r=rows(data);old=rows(data)
    worldcount=r[14][0][15];textures=texture_blobs(data[2])
    clip=CanonicalClipper(land,policy['overlap'],boundary_tolerance=policy.get('boundary_tolerance',0.0));newfaces=[];mapping={}
    counts=collections.Counter();details=[];vs={tuple(v):i for i,v in enumerate(r[3])}
    def polygon(f):return np.array([r[3][r[12][abs(r[13][i][0])][0 if r[13][i][0]>=0 else 1]] for i in range(f[2],f[2]+f[3])])
    for fid,f in enumerate(old[7]):
        name=textures[r[6][f[4]][8]][:16].split(b'\0')[0].decode();q=polygon(f);parts=[q]
        if fid<worldcount and not (name.startswith('g') and name[1:].isdigit() and r[1][f[0]][2]*(1 if not f[1] else -1) > 0.0):
            parts=[] if name.startswith('sky') else clip.clip(q);area=sum(_area(p) for p in parts)
            if area>_area(q)+1e-6:raise ValueError('World clip area growth')
            if name.startswith('*water'):
                parts,steps,recuts,depth=_stable_horizontal_water_parts(parts,q,clip)
                counts['water_float32_retention_steps']+=steps
                counts['water_post_quantize_recuts']+=recuts
                counts['water_maximum_recut_depth']=max(counts['water_maximum_recut_depth'],depth)
                area=sum(_area(p) for p in parts)
            status='removed' if not parts else ('unchanged' if len(parts)==1 and parts[0] is q else 'clipped')
            counts[status]+=1;details.append({'face':fid,'status':status,'parts':len(parts),'original_area':_area(q),'kept_area':area})
        mapping[fid]=[]
        for p in parts:
            record=list(f)
            if p is not q:
                p=np.asarray(p,dtype='<f4').astype(float)
                if name.startswith('*water'):
                    p,steps=_quantize_horizontal_water(p,q,clip)
                    counts['water_float32_retention_steps']+=steps
                p=np.array([point for i,point in enumerate(p) if not np.array_equal(point,p[i-1])])
                if len(p)<3 or _area(p)==0:counts['post_float32_zero_parts_removed']+=1;continue
                n=sum((np.cross(q[i]-q[0],q[i+1]-q[0]) for i in range(1,len(q)-1)),np.zeros(3))
                vector=sum((np.cross(p[i]-p[0],p[i+1]-p[0]) for i in range(1,len(p)-1)),np.zeros(3))
                if vector@n<0:p=p[::-1]
                ids=[]
                for point in p:
                    key=tuple(point)
                    if key not in vs:vs[key]=len(r[3]);r[3].append(list(point))
                    ids.append(vs[key])
                record[2:4]=[len(r[13]),len(ids)]
                for a,b in zip(ids,ids[1:]+ids[:1]):edge=len(r[12]);r[12].append([a,b]);r[13].append([edge])
            if p is not q and f[-1]>=0:
                info=np.array(r[6][f[4]][:8]).reshape(2,4)
                def extent(points):
                    uv=points@info[:,:3].T+info[:,3]
                    low=np.floor(uv.min(axis=0)/16).astype(int);high=np.ceil(uv.max(axis=0)/16).astype(int)
                    return low,high-low+1
                oldlow,oldsize=extent(q);newlow,newsize=extent(p);offset=newlow-oldlow
                if np.any(offset<0) or np.any(offset+newsize>oldsize):raise ValueError('Lightmap crop exceeds original extent')
                styles=sum(s!=255 for s in f[5:9]);oldoffset=f[-1];record[-1]=len(data[8])
                for style in range(styles):
                    start=oldoffset+style*int(np.prod(oldsize));size=int(np.prod(oldsize))
                    if start+size>len(original_data[8]):raise ValueError('Lightmap payload truncated')
                    block=np.frombuffer(original_data[8][start:start+size],dtype=np.uint8).reshape(oldsize[1],oldsize[0])
                    data[8].extend(block[offset[1]:offset[1]+newsize[1],offset[0]:offset[0]+newsize[0]].tobytes())
                counts['lightmapped_fragments_cropped']+=1
            mapping[fid].append(len(newfaces));newfaces.append(record)
    def span(first,count):
        selected=[j for fid in range(first,first+count) for j in mapping[fid]]
        return [selected[0],len(selected)] if selected else [0,0]
    for n in r[5]:n[9:11]=span(*n[9:11])
    for m in r[14]:m[14:16]=span(*m[14:16])
    marks=[]
    for leaf in r[10]:
        first,count=leaf[8:10];selected=[j for m in r[11][first:first+count] for j in mapping[m[0]]]
        leaf[8:10]=[len(marks),len(selected)];marks.extend([j] for j in selected)
    r[11]=marks;r[7]=newfaces
    for i,fmt in FORMATS.items():data[i]=bytearray().join(struct.pack(fmt,*row) for row in r[i])
    candidate,compaction=compact(pack_lumps(data));target=lumps(candidate);target[2],added=retain_sky_textures(target[2],lumps(raw)[2]);candidate=pack_lumps(target);new=rows(target);parsed=(old,new)
    for m in range(len(old[14])):
        for h in range(4):verify_collision(lumps(raw),target,m,m,h,parsed=parsed)
    assert target[4]==lumps(raw)[4]
    return candidate,{'counts':dict(counts),'faces':details,'collision_checks':len(old[14])*4,'PVS_exact':True,'canonical':land.metadata(),'acceptance':'INCOMPLETE: unchanged rendered LAND and physical LAND must agree with canonical source before acceptance'}
