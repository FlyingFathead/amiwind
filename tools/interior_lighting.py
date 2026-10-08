# SPDX-License-Identifier: GPL-3.0-only
"""Small offline BSP lightmaps: scalar ambient and bounded lamp falloff.

This first pass has no shadows, flicker, moving lights or colored lightmaps.
Maps may opt in to the original attenuation (lighting['falloff']='original')
and to box zones (lighting['zones']); the default stays the first-pass linear
falloff until the original attenuation is judged against OpenMW
(LIGHT-FALLOFF-31).
Material colors remain in the shared palette. It is an approximation, not TES3
lighting parity; no per-frame light solve is added to the Amiga renderer.
"""
import numpy as np


OFF_BY_DEFAULT = 0x20  # original LHDT flag


def original_weight(dist, radius):
    """Morrowind's default attenuation as OpenMW applies it (lightutil.cpp:
    linear method 1, value 3.0, no constant term; lighting_util.glsl fade):
    min(1, radius / (3 d)), faded to zero between radius and 2 radius."""
    weight = 1.0 if dist <= radius / 3 else radius / (3 * dist)
    x = min(1.0, max(0.0, dist / radius - 1)); x = 1 - x * x; x = 1 - x * x
    return weight * (1 - x)


def zone_scale(point, zones):
    """Box zones: a light multiplier inside an axis-aligned box (local units),
    blended in over `soft` units inside the box edge so no step shows."""
    scale = 1.0
    for zone in zones:
        low, high = np.asarray(zone['box'][0], float), np.asarray(zone['box'][1], float)
        inside = np.minimum(point - low, high - point)
        if np.any(inside <= 0): continue
        soft = float(zone.get('soft', 16))
        weight = float(np.prod(np.clip(inside / soft, 0, 1))) if soft > 0 else 1.0
        scale *= 1 + (float(zone['scale']) - 1) * weight
    return scale


def bake_grid(polygon, axes, offset):
    """Grid of the unstored double-precision polygon (the default bake grid).

    The engine computes the grid from the stored single-precision values
    (tools/surface_grid.py); the mesh converter compares the two after
    writing each face and rebakes with sample_grid where they differ."""
    uv=polygon@axes+offset
    low=np.floor(uv.min(0)/16)*16;high=np.ceil(uv.max(0)/16)*16
    return low,((high-low)/16).astype(int)+1


def bake_surface(polygon, axes, offset, rotation, origin, lighting, *, sample_grid=None):
    # Converters and repairs pass the engine's grid of the serialized BSP
    # coordinates as sample_grid; without it the unstored polygon's grid is used.
    if sample_grid is None:
        low,size=bake_grid(polygon, axes, offset)
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
    original=lighting.get('falloff','linear')=='original';zones=lighting.get('zones',())
    for t in range(size[1]):
        for s in range(size[0]):
            local=(inverse@np.array([low[0]+s*16-offset[0],low[1]+t*16-offset[1],distance])
                   if inverse is not None else polygon.mean(axis=0))
            point=local@rotation.T+origin;value=base
            for light in lighting['lights']:
                radius=light['radius']*.25
                # Original Off-by-default lights (burnt-out torches, unlit candles) give none.
                if radius<=0 or light.get('flags',0)&OFF_BY_DEFAULT:continue
                delta=np.array(light['position'])*.25-point;dist=np.linalg.norm(delta)
                if original:
                    if dist<2*radius:value+=np.dot(light['color'],[.299,.587,.114])*original_weight(dist,radius)
                elif dist<radius:
                    value+=np.dot(light['color'],[.299,.587,.114])*(1-dist/radius)
            if zones:value*=zone_scale(point,zones)
            samples.append(round(max(0,min(255,value))))
    return bytes(samples)
