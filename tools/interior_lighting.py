# SPDX-License-Identifier: GPL-3.0-only
"""Small offline BSP lightmaps: scalar ambient and bounded lamp falloff.

This first pass has no shadows, flicker, moving lights or colored lightmaps.
Maps may opt in to the original attenuation (lighting['falloff']='original'),
the facing term (lighting['facing']), box zones (lighting['zones']) and warm
surfaces (lighting['warm_style']); the default stays the first-pass linear
falloff until the original attenuation is judged against OpenMW
(LIGHT-FALLOFF-31). Per-cell choices live in CELL_PROFILES, judged against
OpenMW at the same poses (OPENING-BRIGHT-31: the prison ship).
Material colors remain in the shared palette. It is an approximation, not TES3
lighting parity; no per-frame light solve is added to the Amiga renderer.

Actors: the same light function is sampled on a coarse grid over the map
(light_grid), stored as worldspawn keys, so the engine lights a character by
the light where its body is, not only by the floor below it
(NPC-LIGHT-COHERENCE-32).
"""
import re

import numpy as np


OFF_BY_DEFAULT = 0x20  # original LHDT flag
# Lightstyle of faces lit mainly by warm (orange) lights. The engine shows it
# exactly like style 0 but builds those surfaces with the warm colour table
# (r_surf.c R_SurfaceWarm, AW_WARM_STYLE). Below the lamp styles (32 and up).
WARM_STYLE = 31
# A face is warm when warm lights add at least this much light at its centre.
WARM_MIN_LIGHT = 24

# Per-cell lighting choices (cell name, case-insensitive). Cells without an
# entry bake exactly as before. Coordinates are local units (original / 4).
CELL_PROFILES = {
    # Owner, opening scene (OPENING-BRIGHT-31): the start end of the hold at
    # about half its v0.0.32 light, the lantern above Jiub warm. The original
    # attenuation and facing term as in the original. At the stern end (y
    # below about 0) all light at 0.71 and the ambient at a further 0.35
    # (0.25 in all), so the lanterns stand out; the lantern glass glows warm.
    # Judged in FS-UAE at the start poses against v0.0.32 and OpenMW
    # (start views 0.50 to 0.51 of v0.0.32, 0.86 to 0.94 of the original).
    'imperial prison ship': {
        'falloff': 'original', 'facing': True, 'warm_style': True, 'glowing_glass': 7,
        'zones': [{'box': [[-140, -240, -90], [140, 24, 140]], 'scale': 0.35, 'soft': 24, 'scope': 'ambient'},
                  {'box': [[-140, -240, -90], [140, 24, 140]], 'scale': 0.71, 'soft': 24}],
    },
}


def cell_lighting(cell):
    """Bake settings of an original interior cell: its ambient and placed
    lights, plus the cell's entry in CELL_PROFILES (if any)."""
    lighting = {**cell['lighting'], 'lights': [dict(r['light'], position=r['position'])
                                               for r in cell['refs'] if r.get('light') and not r.get('deleted')]}
    profile = CELL_PROFILES.get(str(cell.get('name', '')).casefold())
    if profile:
        lighting.update({k: (list(v) if isinstance(v, list) else v) for k, v in profile.items()})
    return lighting


GLASS = re.compile(r'pane|glass', re.I)


def glass_glow(model, material, lighting):
    """Self-lit level (emitN texture) for the glass of a lantern with a flame
    inside, in cells that opt in with lighting['glowing_glass'] (1..9), else 0.
    The original shows the candle through translucent glass; AmiWind draws
    glass opaque, so the pane carries the glow instead (OPENING-JIUB-LANTERN-32)."""
    level=int(lighting.get('glowing_glass',0)) if lighting else 0
    if not level or not model.get('flames'):return 0
    return max(0,min(9,level)) if GLASS.search(material.get('texture_source') or '') else 0


def warm_light(light):
    """Orange/yellow light (lanterns, candles, fires), as light_sources.colour_class."""
    r, g, b = light['color'][:3]
    return r > b + 32 and not (b > r and b > g)


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
    front=face_normal(polygon) if lighting.get('facing') else None
    world_normal=None if front is None else rotation@front
    for t in range(size[1]):
        for s in range(size[0]):
            local=(inverse@np.array([low[0]+s*16-offset[0],low[1]+t*16-offset[1],distance])
                   if inverse is not None else polygon.mean(axis=0))
            point=local@rotation.T+origin
            samples.append(round(max(0,min(255,point_light(point,lighting,world_normal)))))
    return bytes(samples)


LUMA = (.299, .587, .114)


def face_normal(polygon):
    """Unit front normal of a polygon from its whole area vector (merged
    polygons may start with collinear vertices), or None if it has no area."""
    rel=np.asarray(polygon,float)-polygon[0]
    area=np.cross(rel,np.roll(rel,-1,axis=0)).sum(axis=0);length=np.linalg.norm(area)
    return area/length if length>0 else None


def light_weight(light, point, lighting, normal=None):
    """One light's falloff weight at a point (local units): the first-pass
    linear falloff, or the original attenuation with lighting['falloff'] =
    'original'; with lighting['facing'] and a surface normal, times the
    cosine toward the light (Lambert, as the original lights surfaces)."""
    radius=light['radius']*.25
    # Original Off-by-default lights (burnt-out torches, unlit candles) give none.
    if radius<=0 or light.get('flags',0)&OFF_BY_DEFAULT:return 0.0
    delta=np.array(light['position'])*.25-point;dist=np.linalg.norm(delta)
    if lighting.get('falloff','linear')=='original':
        weight=original_weight(dist,radius) if dist<2*radius else 0.0
    else:
        weight=(1-dist/radius) if dist<radius else 0.0
    if weight and normal is not None and lighting.get('facing'):
        weight*=max(0.0,float(normal@delta)/dist) if dist>0 else 1.0
    return weight


def point_light(point, lighting, normal=None):
    """Baked light value (0..255 before clamping) at a point in local units:
    the cell ambient's luma plus every light's luma times its weight, then
    the box zones. Surfaces (bake_surface) and actors (light_grid) use it."""
    value=float(np.dot(lighting['ambient'],[.299,.587,.114]))
    zones=lighting.get('zones',())
    # Zones with "ambient" scope scale only the cell's ambient light: the
    # lamps keep their full strength inside them.
    ambient_zones=[z for z in zones if z.get('scope','all')=='ambient']
    if ambient_zones:value*=zone_scale(point,ambient_zones)
    for light in lighting['lights']:
        weight=light_weight(light,point,lighting,normal)
        if weight:value+=np.dot(light['color'],[.299,.587,.114])*weight
    zones=[z for z in zones if z.get('scope','all')=='all']
    if zones:value*=zone_scale(point,zones)
    return value


def surface_style(polygon, rotation, origin, lighting):
    """Lightstyle for a baked face: WARM_STYLE when lighting['warm_style'] is
    set and warm lights add at least WARM_MIN_LIGHT at the face centre (after
    the facing term and zones), else 0 (unchanged)."""
    if not lighting.get('warm_style'):return 0
    normal=face_normal(polygon)
    if normal is None:return 0
    normal=rotation@normal;point=polygon.mean(axis=0)@rotation.T+origin
    warm=sum(np.dot(light['color'],[.299,.587,.114])*light_weight(light,point,lighting,normal)
             for light in lighting['lights'] if warm_light(light))
    zones=[z for z in lighting.get('zones',()) if z.get('scope','all')=='all']
    if zones:warm*=zone_scale(point,zones)
    return WARM_STYLE if warm>=WARM_MIN_LIGHT else 0


# Actor light grid: worldspawn keys "_aw_lightgrid" "step nx ny nz x y z" and
# "_aw_lightgrid0".. with GRID_CHUNK hex digits each (two per cell, x fastest,
# then y, then z), below Quake's 1024-character token. Keys starting with "_"
# are skipped by the server (pr_edict.c ED_ParseEdict).
GRID_STEPS = (16, 32, 64)
GRID_MAX_CELLS = 8192
GRID_CHUNK = 960
GRID_MARGIN = 32  # the sealing box sits 32 units outside the placed objects


def light_grid(lighting, low, high):
    """Light (no facing term: a body is lit from every side) sampled at the
    corners of the smallest grid step that covers low..high with at most
    GRID_MAX_CELLS points. Returns (step, dims, origin, bytes) or None when the
    cell has no lights and no zones (a uniform grid would equal the floor)."""
    if not lighting.get('lights') and not lighting.get('zones'):return None
    low=np.asarray(low,float);high=np.asarray(high,float)
    if np.any(high<=low):return None
    for step in GRID_STEPS:
        dims=(np.ceil((high-low)/step).astype(int)+1)
        if int(np.prod(dims))<=GRID_MAX_CELLS:break
    else:
        return None
    flat={**lighting,'facing':False}
    values=bytearray()
    for k in range(dims[2]):
        for j in range(dims[1]):
            for i in range(dims[0]):
                point=low+np.array([i,j,k])*step
                values.append(round(max(0,min(255,point_light(point,flat)))))
    return step,[int(d) for d in dims],[float(v) for v in low],bytes(values)


def light_grid_keys(grid):
    """Worldspawn key lines for a light_grid() result (empty for None)."""
    if grid is None:return []
    step,dims,origin,values=grid
    text=values.hex()
    keys=['"_aw_lightgrid" "%d %d %d %d %s"'%(step,*dims,' '.join('%g'%v for v in origin))]
    for n in range(0,len(text),GRID_CHUNK):
        keys.append('"_aw_lightgrid%d" "%s"'%(n//GRID_CHUNK,text[n:n+GRID_CHUNK]))
    return keys


def add_light_grid(entities, grid):
    """Entity lump text with the grid keys added to the worldspawn (first entity)."""
    keys=light_grid_keys(grid)
    if not keys:return entities
    close=entities.index('}')
    return entities[:close]+'\n'.join(keys)+'\n'+entities[close:]
