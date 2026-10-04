"""Direct canonical LAND clipping without finite-depth or placement exemptions."""
import math
import numpy as np
from functools import lru_cache
from terrain_visual_cull import _cut,_area,merge_convex_parts

def _area_vector(polygon):
    p=np.asarray(polygon,dtype=float)
    return sum((np.cross(p[i]-p[0],p[i+1]-p[0]) for i in range(1,len(p)-1)),np.zeros(3))

def _source_orientation(polygon,source_normal):
    """Restore directed source winding after projection-based hull ordering."""
    p=np.asarray(polygon,dtype=float)
    return p[::-1] if float(_area_vector(p)@source_normal)<0 else p

def bsp_front_winding(polygon,plane_normal,side=0):
    """Orient newly authored BSP surfaces for the native edge rasterizer.

    Quake stores front-facing loops clockwise: their directed area vector
    opposes the outward plane normal (including the face's plane-side bit).
    This differs from the upward CCW loops used for canonical LAND math.
    Only edge order changes; coordinates, shape and plane remain untouched.
    """
    if side not in (0,1):raise ValueError('BSP face side must be zero or one')
    return _source_orientation(polygon,np.asarray(plane_normal)*(1 if side else -1))

def coalesce_convex_union(parts):
    """Combine a convex complete union; never fill a concave notch or a hole."""
    if len(parts)<2:return parts
    from scipy.spatial import ConvexHull,QhullError
    points=np.unique(np.concatenate(parts),axis=0)
    area=sum(_area(p) for p in parts)
    normal=sum((np.cross(parts[0][i]-parts[0][0],parts[0][i+1]-parts[0][0]) for i in range(1,len(parts[0])-1)),np.zeros(3))
    dims=[i for i in range(3) if i!=int(np.argmax(abs(normal)))]
    projected=[np.column_stack((p[:,dims],np.zeros(len(p)))) for p in parts]
    for i,a in enumerate(projected):
        for b in projected[i+1:]:
            if any(a[:,k].max()<=b[:,k].min() or b[:,k].max()<=a[:,k].min() for k in (0,1)):continue
            signed=sum(x[0]*y[1]-x[1]*y[0] for x,y in zip(b,np.roll(b,-1,axis=0)))
            sign=1 if signed>0 else -1;intersection=a
            for x,y in zip(b,np.roll(b,-1,axis=0)):
                edge=y-x;n=np.array([-edge[1],edge[0],0])*sign
                intersection,_=_cut(intersection,n,-float(n@x))
                if not intersection:break
            if _area(intersection)>1e-10:return parts
    try:poly=points[ConvexHull(points[:,dims]).vertices]
    except QhullError:return parts
    # Input pieces partition canonical XY tiles, hence have disjoint interiors.
    # Hull equal to the partition's sum is an exact convex union up to roundoff.
    if not math.isclose(_area(poly),area,rel_tol=1e-12,abs_tol=1e-10):return parts
    return [_source_orientation(poly,normal)]

class CanonicalClipper:
    def __init__(self,land,overlap=.5,*,boundary_tolerance=0.0):
        if not math.isfinite(overlap) or overlap<0:raise ValueError('Finite nonnegative overlap required')
        # Vertical compiled units; this is numerical classification, not contact overlap.
        # Callers must justify a nonzero tolerance against their serialization/transform
        # error budget. The default preserves exact classification for existing callers.
        if not math.isfinite(boundary_tolerance) or boundary_tolerance<0:
            raise ValueError('Finite nonnegative vertical boundary tolerance required')
        self.land=land;self.overlap=overlap;self.boundary_tolerance=boundary_tolerance
    @lru_cache(maxsize=65536)
    def tile(self,x,y):
        # Compiled grid is source-aligned after explicit origin translation.
        ox=x*32-self.land.origin[0];oy=y*32-self.land.origin[1]
        pts=[]
        for dx,dy in ((0,0),(32,0),(32,32),(0,32)):
            sample=self.land.sample(ox+dx,oy+dy)
            if sample is None:raise ValueError('INCOMPLETE: missing canonical LAND coverage')
            pts.append(np.array([ox+dx,oy+dy,sample['height']]))
        return tuple(np.array([pts[i] for i in ids]) for ids in ((0,1,2),(0,2,3)))
    def clip(self,polygon,*,merge=True):
        q=np.asarray(polygon,dtype=float)
        lo=q[:,:2].min(axis=0)+self.land.origin[:2];hi=q[:,:2].max(axis=0)+self.land.origin[:2]
        # Select one adjacent tile for faces exactly on a grid boundary. Source
        # height seams are validated; the boundary interpolation is identical.
        starts=np.floor(lo/32).astype(int);ends=np.ceil(hi/32).astype(int)-1
        ends=np.maximum(starts,ends);parts=[];keys=set();removed=False
        for y in range(starts[1],ends[1]+1):
            for x in range(starts[0],ends[0]+1):
                for tri in self.tile(x,y):
                    p=q
                    for a,b in zip(tri,np.roll(tri,-1,axis=0)):
                        edge=b-a;n=np.array([-edge[1],edge[0],0.]);p,_=_cut(p,n,-float(n@a))
                        if len(p)<3:break
                    if len(p)<3 or _area(p)==0:continue
                    normal=np.cross(tri[1]-tri[0],tri[2]-tri[0]);normal/=np.linalg.norm(normal)
                    # Retain overlap below the varying surface; no bottom plane.
                    distance=p@normal-float(normal@tri[0])+normal[2]*self.overlap
                    if np.any(distance < -normal[2]*self.boundary_tolerance):
                        removed=True
                        # Intersect with the intended boundary, not an offset tolerance
                        # plane. Repeated passes still evaluate actual canonical LAND.
                        p,_=_cut(p,normal,-float(normal@tri[0])+normal[2]*self.overlap)
                    if len(p)<3 or _area(p)==0:continue
                    key=tuple(sorted(tuple(np.round(point,10)) for point in p))
                    if key not in keys:keys.add(key);parts.append(p)
        if not merge:
            normal=_area_vector(q)
            return [_source_orientation(p,normal) for p in parts]
        if not removed:return [q]
        # Both convex merge stages may order projected hulls independently of
        # the original 3D loop. Restore winding without moving any vertex or UV.
        normal=_area_vector(q)
        merged=[_source_orientation(p,normal) for p in merge_convex_parts(parts)]
        return [_source_orientation(p,normal) for p in coalesce_convex_union(merged)]
