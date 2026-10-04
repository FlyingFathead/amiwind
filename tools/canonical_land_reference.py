# SPDX-License-Identifier: GPL-3.0-only
"""Direct, read-only canonical LAND heightfield in an explicit compiled frame."""
from pathlib import Path
import hashlib,math
import numpy as np

class CanonicalLand:
    def __init__(self,path,origin,scale=.25):
        self.path=Path(path);self.origin=np.asarray(origin,dtype=float)
        if self.origin.shape!=(3,) or not np.isfinite(self.origin).all() or scale!=.25:
            raise ValueError('Explicit finite XYZ origin and supported scale0.25 required')
        self.scale=scale
        with np.load(self.path,allow_pickle=False) as packet:
            cells=packet['cells'].copy();self.heights=packet['heights'].copy();self.materials=packet['materials'].copy()
            if int(packet['spacing'])!=128 or cells.ndim!=2 or cells.shape[1]!=2 or self.heights.shape!=(len(cells),65,65):
                raise ValueError('Unexpected canonical full-resolution LAND grid')
            if not np.isfinite(self.heights).all() or np.any(packet['water']!=0):
                raise ValueError('Nonfinite LAND or unsupported water level')
            if not np.isfinite(cells).all() or np.any(cells!=np.floor(cells)):
                raise ValueError('LAND cell coordinates must be finite integers')
            if self.materials.shape!=(len(cells),16,16) or not np.isfinite(self.materials).all() or np.any(self.materials!=np.floor(self.materials)) or np.any(self.materials<0):
                raise ValueError('Expected nonnegative integer LAND materials')
        self.cells={tuple(map(int,c)):i for i,c in enumerate(cells)}
        if len(self.cells)!=len(cells):raise ValueError('Duplicate LAND cell')
        for (cx,cy),i in self.cells.items():
            for key,left,right in [((cx+1,cy),self.heights[i,:,64],None),((cx,cy+1),self.heights[i,64,:],None)]:
                if key in self.cells:
                    j=self.cells[key];other=self.heights[j,:,0] if key[0]!=cx else self.heights[j,0,:]
                    if not np.array_equal(left,other):raise ValueError('Canonical LAND cell seam mismatch')
        self.sha256=hashlib.sha256(self.path.read_bytes()).hexdigest()

    def sample(self,x,y):
        if not math.isfinite(x) or not math.isfinite(y):raise ValueError('Finite sample coordinates required')
        gx=x+self.origin[0];gy=y+self.origin[1]
        cx=math.floor(gx/2048);cy=math.floor(gy/2048);ix=(gx-cx*2048)/32;iy=(gy-cy*2048)/32
        key=(cx,cy)
        if key not in self.cells:
            for other,xx,yy in [((cx-1,cy),64.,iy),((cx,cy-1),ix,64.),((cx-1,cy-1),64.,64.)]:
                if other in self.cells and (xx!=64 or ix==0) and (yy!=64 or iy==0):key,ix,iy=other,xx,yy;break
        if key not in self.cells:return None
        tx=min(63,math.floor(ix));ty=min(63,math.floor(iy));u=ix-tx;v=iy-ty;h=self.heights[self.cells[key]]
        a,b,c,d=[float(h[yy,xx])*self.scale-self.origin[2] for xx,yy in ((tx,ty),(tx+1,ty),(tx+1,ty+1),(tx,ty+1))]
        z=a+(b-a)*u+(c-b)*v if v<=u else a+(c-d)*u+(d-a)*v
        return {'height':z,'cell':list(key),'grid_tile':[tx,ty],'fraction':[u,v],'material':int(self.materials[self.cells[key],min(15,int(iy)//4),min(15,int(ix)//4)]),'water_is_receiver':False}

    def triangles(self,bounds):
        low,high=bounds
        if len(low)!=2 or len(high)!=2 or not all(math.isfinite(v) for v in (*low,*high)) or any(low[k]>=high[k] for k in range(2)):raise ValueError('Finite nonempty XY bounds required')
        for (cx,cy),index in sorted(self.cells.items()):
            ox=cx*2048-self.origin[0];oy=cy*2048-self.origin[1]
            if ox+2048<=low[0] or ox>=high[0] or oy+2048<=low[1] or oy>=high[1]:continue
            h=self.heights[index]
            for y in range(64):
                if oy+(y+1)*32<=low[1] or oy+y*32>=high[1]:continue
                for x in range(64):
                    if ox+(x+1)*32<=low[0] or ox+x*32>=high[0]:continue
                    corners=[[ox+xx*32,oy+yy*32,float(h[yy,xx])*self.scale-self.origin[2]] for xx,yy in ((x,y),(x+1,y),(x+1,y+1),(x,y+1))]
                    yield [corners[i] for i in (0,1,2)]
                    yield [corners[i] for i in (0,2,3)]

    def metadata(self):
        return {'kind':'DIRECT canonical terrain-source.npz','path':str(self.path),'sha256':self.sha256,'source_scale':self.scale,'global_runtime_origin':self.origin.tolist(),'transform':'compiled XYZ = source XYZ*0.25 - global_runtime_origin','source_spacing':128,'compiled_spacing':32,'diagonal':[[0,1,2],[0,2,3]],'unknown_land':'INCOMPLETE: missing authored coverage blocks acceptance; no invented ocean ground','water':'never a receiver; original negative LAND heights are seabed'}
