# SPDX-License-Identifier: GPL-3.0-only
"""Small offline BSP lightmaps: scalar ambient and bounded lamp falloff.

This first pass has no shadows, flicker, moving lights or colored lightmaps.
Material colors remain in the shared palette. It is an approximation, not TES3
lighting parity; no per-frame light solve is added to the Amiga renderer.
"""
import numpy as np


def bake_surface(polygon, axes, offset, rotation, origin, lighting, *, sample_grid=None):
    # Audited repairs supply the exact grid of serialized BSP coordinates.
    # Existing conversion callers retain their historical grid pending the
    # separate cross-FPU precision correction.
    if sample_grid is None:
        uv=polygon@axes+offset
        low=np.floor(uv.min(0)/16)*16;high=np.ceil(uv.max(0)/16)*16
        size=((high-low)/16).astype(int)+1
    else:
        low=np.asarray(sample_grid[0],dtype=float)
        size=np.asarray(sample_grid[1],dtype=int)
        if low.shape!=(2,) or size.shape!=(2,) or not np.all(np.isfinite(low)):
            raise ValueError('Invalid explicit lightmap grid')
    if np.any(size<1) or np.any(size>17):raise ValueError('Lightmap extent exceeds runtime budget')
    normal=np.cross(polygon[1]-polygon[0],polygon[2]-polygon[0]);normal/=np.linalg.norm(normal)
    matrix=np.vstack((axes.T,normal));distance=normal@polygon[0]
    # Constant/degenerate UVs have no unique inverse. Bake one face-centre
    # value for those materials instead of inventing texture coordinates.
    inverse=np.linalg.inv(matrix) if abs(np.linalg.det(matrix))>1e-10 else None
    samples=[]
    base=float(np.dot(lighting['ambient'],[.299,.587,.114]))
    for t in range(size[1]):
        for s in range(size[0]):
            local=(inverse@np.array([low[0]+s*16-offset[0],low[1]+t*16-offset[1],distance])
                   if inverse is not None else polygon.mean(axis=0))
            point=local@rotation.T+origin;value=base
            for light in lighting['lights']:
                radius=light['radius']*.25
                if radius<=0:continue
                delta=np.array(light['position'])*.25-point;dist=np.linalg.norm(delta)
                if dist<radius:
                    value+=np.dot(light['color'],[.299,.587,.114])*(1-dist/radius)
            samples.append(round(max(0,min(255,value))))
    return bytes(samples)
