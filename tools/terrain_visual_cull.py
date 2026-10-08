# SPDX-License-Identifier: GPL-3.0-only
"""Conservative offline clipping against verified opaque LAND prisms.

Never infer invisibility from camera sampling. Ground triangles are explicit
trusted converter input, never water/sky. Collision is deliberately not input.
"""
import math
import re
import struct
from collections import defaultdict


def _area(p):
    if len(p)<3:return 0.
    a=p[0];v=[0.,0.,0.]
    for b,c in zip(p[1:],p[2:]):
        x=[b[i]-a[i] for i in range(3)];y=[c[i]-a[i] for i in range(3)]
        z=[x[1]*y[2]-x[2]*y[1],x[2]*y[0]-x[0]*y[2],x[0]*y[1]-x[1]*y[0]]
        v=[v[i]+z[i] for i in range(3)]
    return math.sqrt(sum(x*x for x in v))/2


def _cut(poly,n,d):
    """Return positive and negative convex pieces, including exact boundary."""
    a=[];b=[]
    for i,p in enumerate(poly):
        q=poly[(i+1)%len(poly)];x=sum(p[k]*n[k] for k in range(3))+d;y=sum(q[k]*n[k] for k in range(3))+d
        if x>=0:a.append(p)
        if x<=0:b.append(p)
        if (x>0 and y<0) or (x<0 and y>0):
            t=x/(x-y);r=[p[k]+(q[k]-p[k])*t for k in range(3)];a.append(r);b.append(r)
    # Zero-area pieces cannot occlude a nonzero area. Tiny pieces remain.
    return (a if _area(a)>0 else []),(b if _area(b)>0 else [])


def _subtract(poly,planes):
    remaining=poly;outside=[]
    for n,d in planes:
        if not remaining:break
        # A polygon on a closed half-space boundary belongs to the prism.
        # Keeping it on BOTH sides duplicates full-area faces in a union.
        if all(sum(p[k]*n[k] for k in range(3))+d == 0 for p in remaining):
            continue
        remaining,part=_cut(remaining,n,d)
        if part:outside.append(part)
    return outside


class TerrainVolume:
    def __init__(self,triangles,bottom,overlap=.5):
        if not math.isfinite(bottom) or not math.isfinite(overlap) or overlap<0:raise ValueError('Finite nonnegative terrain overlap required')
        self.prisms=[];self.grid=defaultdict(list);self.bottom=bottom;self.overlap=overlap
        for tri in triangles:
            if len(tri)!=3 or any(len(p)!=3 or not all(map(math.isfinite,p)) for p in tri):raise ValueError('Invalid ground triangle')
            a,b,c=tri;u=[b[i]-a[i] for i in range(3)];v=[c[i]-a[i] for i in range(3)]
            n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
            if n[2]==0:continue
            if n[2]<0:tri=[a,c,b];n=[-x for x in n]
            # z <= exact sloping ground minus overlap; keep terrain-contact skirt.
            top=([-n[0]/n[2],-n[1]/n[2],-1.],sum(n[i]*a[i] for i in range(3))/n[2]-overlap)
            planes=[top,([0.,0.,1.],-bottom-overlap)]
            for p,q in zip(tri,tri[1:]+tri[:1]):
                dx=q[0]-p[0];dy=q[1]-p[1];planes.append(([-dy,dx,0.],dy*p[0]-dx*p[1]))
            low=[min(p[i] for p in tri) for i in range(2)];high=[max(p[i] for p in tri) for i in range(2)]
            j=len(self.prisms);self.prisms.append((planes,low,high))
            for x in range(math.floor(low[0]/128),math.floor(high[0]/128)+1):
                for y in range(math.floor(low[1]/128),math.floor(high[1]/128)+1):self.grid[x,y].append(j)

    def clip(self,polygon,max_fragments=256):
        original=[list(map(float,p)) for p in polygon]
        if len(original)<3 or any(not all(map(math.isfinite,p)) for p in original):raise ValueError('Invalid visual polygon')
        lo=[min(p[i] for p in original) for i in range(2)];hi=[max(p[i] for p in original) for i in range(2)]
        candidates=set()
        for x in range(math.floor(lo[0]/128),math.floor(hi[0]/128)+1):
            for y in range(math.floor(lo[1]/128),math.floor(hi[1]/128)+1):candidates.update(self.grid[x,y])
        pieces=[original]
        for j in sorted(candidates):
            planes,low,high=self.prisms[j]
            if any(hi[k]<low[k] or lo[k]>high[k] for k in range(2)):continue
            pieces=[part for p in pieces for part in _subtract(p,planes)]
            if len(pieces)>max_fragments:return [original],'uncertain_fragment_budget'
            if not pieces:return [],'fully_buried'
        if abs(sum(_area(p) for p in pieces)-_area(original))<=1e-8:return [original],'unchanged'
        return pieces,'crossing_clipped'



class IntersectedTerrainVolume:
    """Cull only below BOTH global terrain and the actual rendered local LAND.

    A global high-resolution facet must not erase geometry exposed by a lower
    local terrain approximation. This is exact union/intersection clipping,
    not camera sampling or a single Z plane.
    """
    def __init__(self, local, global_terrain):
        self.local=local;self.global_terrain=global_terrain
        self.prisms=local.prisms;self.bottom=max(local.bottom,global_terrain.bottom)
        self.overlap=local.overlap

    def clip(self, polygon, max_fragments=256):
        original=[list(map(float,p)) for p in polygon]
        if len(original)<3 or any(not all(map(math.isfinite,p)) for p in original):
            raise ValueError('Invalid visual polygon')
        lo=[min(p[i] for p in original) for i in range(2)]
        hi=[max(p[i] for p in original) for i in range(2)]
        candidates=set()
        for x in range(math.floor(lo[0]/128),math.floor(hi[0]/128)+1):
            for y in range(math.floor(lo[1]/128),math.floor(hi[1]/128)+1):
                candidates.update(self.local.grid[x,y])
        pieces=[original]
        for j in sorted(candidates):
            planes,low,high=self.local.prisms[j]
            if any(hi[k]<low[k] or lo[k]>high[k] for k in range(2)):continue
            output=[]
            for piece in pieces:
                inside=piece
                for n,d in planes:
                    if not inside:break
                    if all(sum(p[k]*n[k] for k in range(3))+d==0 for p in inside):continue
                    inside,outside=_cut(inside,n,d)
                    if outside:output.append(outside)
                if inside:
                    outside,status=self.global_terrain.clip(inside,max_fragments)
                    if status=='uncertain_fragment_budget':
                        return [original],'uncertain_fragment_budget'
                    output.extend(outside)
            pieces=output
            if len(pieces)>max_fragments:return [original],'uncertain_fragment_budget'
            if not pieces:return [],'fully_buried'
        if abs(sum(_area(p) for p in pieces)-_area(original))<=1e-8:return [original],'unchanged'
        return pieces,'crossing_clipped'


def ground_from_bsp(raw,overlap=.5):
    """Only upward g<material> LAND faces; lowest LAND vertex bounds depth.

    These names are emitted by prepare_quake/prepare_world_regions. An arbitrary
    BSP with no recognized LAND fails closed. Lowest LAND vertex is at or above
    the authored prism bottom, so choosing it cannot extend terrain solids.
    """
    if len(raw)<124 or struct.unpack_from('<i',raw)[0]!=29:raise ValueError('Expected BSP29')
    lumps=[]
    for i in range(15):
        o,s=struct.unpack_from('<ii',raw,4+i*8)
        if o<124 or s<0 or o+s>len(raw):raise ValueError('Invalid BSP lump')
        lumps.append(raw[o:o+s])
    vertices=list(struct.iter_unpack('<3f',lumps[3]));edges=list(struct.iter_unpack('<HH',lumps[12]));se=[v[0] for v in struct.iter_unpack('<i',lumps[13])]
    planes=list(struct.iter_unpack('<4fi',lumps[1]));texinfos=list(struct.iter_unpack('<8fii',lumps[6]));faces=list(struct.iter_unpack('<HhihH4Bi',lumps[7]));models=list(struct.iter_unpack('<9f7i',lumps[14]))
    nt=struct.unpack_from('<i',lumps[2])[0];names=[]
    for i in range(nt):
        o=struct.unpack_from('<i',lumps[2],4+4*i)[0];names.append('' if o<0 else lumps[2][o:o+16].split(b'\0')[0].decode('ascii','replace'))
    first,count=models[0][14:16];ground=[];allpoints=[]
    for face in faces[first:first+count]:
        plane,side,start,n,tex=face[:5];name=names[texinfos[tex][8]]
        if not re.fullmatch(r'g\d+',name):continue
        p=[list(vertices[edges[abs(e)][0 if e>=0 else 1]]) for e in se[start:start+n]];allpoints.extend(p)
        if planes[plane][2]*(1 if side==0 else -1)<=.001:continue
        ground.extend([p[0],p[i],p[i+1]] for i in range(1,len(p)-1))
    bottom=min((p[2] for p in allpoints),default=0.)
    return TerrainVolume(ground,bottom,overlap),dict(ground_triangles=len(ground),bounded_bottom=bottom,ground_policy='world model upward gN LAND faces; excludes water, sky, stone',overlap=overlap)

def merge_convex_parts(parts):
    """Merge only adjacent coplanar convex pieces without filling missing area."""
    import numpy as np
    from scipy.spatial import ConvexHull, QhullError
    parts=[np.asarray(p,dtype=float) for p in parts]
    changed=True
    while changed:
        changed=False
        for i in range(len(parts)):
            if changed:break
            for j in range(i+1,len(parts)):
                a,b=parts[i],parts[j]
                if sum(any(np.linalg.norm(x-y)<1e-7 for y in b) for x in a)<2:continue
                n=np.cross(a[1]-a[0],a[2]-a[0]);drop=int(np.argmax(abs(n)));dims=[k for k in range(3) if k!=drop]
                points=np.unique(np.concatenate((a,b)),axis=0)
                try:hull=ConvexHull(points[:,dims]);poly=points[hull.vertices]
                except QhullError:continue
                if abs(_area(poly)-_area(a)-_area(b))>1e-7:continue
                parts[i]=poly;parts.pop(j);changed=True;break
    return parts


def normalize_identity(value):
    from pathlib import PurePath
    if not isinstance(value,str) or not value.strip() or '/' in value or '\\' in value:raise ValueError('Invalid terrain cull identity')
    value=value.strip().casefold()
    return value[:-4] if value.endswith('.bsp') else value


def _overlap(value):
    if type(value) not in (int,float) or not math.isfinite(value) or value<0:raise ValueError('Terrain overlap must be finite nonnegative number')
    return float(value)


def resolve_policy(config=None, *, map_identity=None,cell_identity=None,subcell_identity=None,force=None,overlap_force=None):
    config={} if config is None else config
    if not isinstance(config,dict) or set(config)-{'default','overlap','cells','subcells','bsps'}:raise ValueError('Invalid terrain cull configuration')
    enabled=config.get('default',True)
    if type(enabled) is not bool:raise ValueError('Terrain cull default must be boolean')
    receipt={'enabled':enabled,'provenance':'global_default','overlap':_overlap(config.get('overlap',.5)),
             'overlap_provenance':'global_default','map':map_identity,'cell':cell_identity,'subcell':subcell_identity}
    for table,identity in [('cells',cell_identity),('subcells',subcell_identity),('bsps',map_identity)]:
        values=config.get(table,{})
        if not isinstance(values,dict):raise ValueError('Override table must be object')
        normalized={}
        for name,value in values.items():
            key=normalize_identity(name)
            if key in normalized:raise ValueError('Duplicate terrain override identity')
            if type(value) is bool:value={'enabled':value}
            if not isinstance(value,dict) or not value or set(value)-{'enabled','overlap'}:raise ValueError('Invalid terrain override')
            if 'enabled' in value and type(value['enabled']) is not bool:raise ValueError('Terrain enabled must be boolean')
            if 'overlap' in value:_overlap(value['overlap'])
            normalized[key]=value
        if identity is not None and normalize_identity(identity) in normalized:
            value=normalized[normalize_identity(identity)]
            if 'enabled' in value:receipt.update(enabled=value['enabled'],provenance=table)
            if 'overlap' in value:receipt.update(overlap=_overlap(value['overlap']),overlap_provenance=table)
    if force is not None:
        if type(force) is not bool:raise ValueError('Terrain cull force must be boolean')
        receipt.update(enabled=force,provenance='explicit_force')
    if overlap_force is not None:receipt.update(overlap=_overlap(overlap_force),overlap_provenance='explicit_force')
    return receipt


def cull_surfaces(surfaces,terrain,placements):
    """Keep one shared representation, requiring burial at every placement.

    A unique unlightmapped placement may be clipped with unchanged UV affine
    mapping. Shared/illuminated crossing faces remain original in phase 1.
    """
    import numpy as np
    counts=defaultdict(int);output=[]
    for surface in surfaces:
        q,n,ax,off,material,samples=surface
        results=[]
        for origin,yaw in placements:
            r=math.radians(yaw);rotation=np.array([[math.cos(r),-math.sin(r),0],[math.sin(r),math.cos(r),0],[0,0,1.]])
            parts,status=terrain.clip(q@rotation.T+origin);results.append((parts,status,rotation,origin))
        if all(status=='fully_buried' for parts,status,r,o in results):counts['fully_buried_removed']+=1;continue
        if len(results)==1 and samples is None and results[0][1]=='crossing_clipped':
            parts,status,r,o=results[0];parts=merge_convex_parts(parts)
            if len(parts)==1:
                poly=(parts[0]-o)@r
                if np.cross(poly[1]-poly[0],poly[2]-poly[0])@n<0:poly=poly[::-1]
                if len(poly)<=len(q)+2:
                    output.append((poly,n,ax,off,material,samples));counts['crossing_clipped']+=1;continue
            counts['crossing_fragment_growth_retained']+=1
        elif any(status=='crossing_clipped' or status=='fully_buried' for parts,status,r,o in results):counts['shared_or_lightmapped_retained']+=1
        else:counts['unchanged']+=1
        output.append(surface)
    counts.update(input_faces=len(surfaces),output_faces=len(output),placement_count=len(placements))
    return output,dict(counts)
