#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Compile owned static meshes to shared BSP29 submodels with original UVs."""
import os
import argparse, json, math, re, shutil, struct, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image
from mesh_geometry import surface_polygons, split_surface, collision_pieces
from prepare_quake import miptex, CENTRE, SCALE
from mwad.paths import ensure_external
from player_hull import MINS, MAXS, PROFILE, rebuild_world_hull
from mwad.scene import read_asset, unpack_geometry
from scenery_selection import select_runtime_refs
from static_lod import reduce_mesh, rock_profile
import scenery_reduce
from surface_grid import check_lumps, engine_grid, face_points, sample_dimensions, texinfo_vecs
# Build switch: AMIWIND_NO_EMISSIVE=1 converts without self-lit material marking
# (no emitN_ textures), reproducing pre-emissive maps.
NO_EMISSIVE = os.environ.get('AMIWIND_NO_EMISSIVE') == '1'
# Build switch: AMIWIND_NO_FLAMES=1 writes no aw_flame entities.
NO_FLAMES = os.environ.get('AMIWIND_NO_FLAMES') == '1'


# Dressing: mesh path fragments append_meshes leaves out unless the caller
# retains them. retain_dressing=True keeps all (world, towns, Balmora regions,
# door overlays); a collection keeps those fragments only. Each omission is
# receipted ("omitted"), each retained piece too ("dressing_retained").
DRESSING_EXCLUDED = ('flora_', 'marker_', 'scum_', 'lantern_hook', 'furn_de_rope')
# Interiors keep their dressing (owner decision A, BUILD-DRESSING-EXCLUDED-32):
# lantern hooks, ropes, potted ferns and grass. Editor markers stay out. The
# earlier rule (skip all dressing) stays selectable: --skip-dressing.
INTERIOR_DRESSING = ('flora_', 'scum_', 'lantern_hook', 'furn_de_rope')
_SKIP_DRESSING = [False]


def add_dressing_option(parser):
    parser.add_argument('--skip-dressing', action='store_true',
                        help='Earlier interior rule: leave out lantern hooks, ropes, ferns and other dressing '
                             '(receipted); default keeps them (BUILD-DRESSING-EXCLUDED-32)')


def apply_dressing_option(args):
    _SKIP_DRESSING[0] = bool(getattr(args, 'skip_dressing', False))


def interior_dressing():
    """retain_dressing value for the interior converters (census, prison, areas)."""
    return () if _SKIP_DRESSING[0] else INTERIOR_DRESSING


def flame_entities(ref, model, centre):
    """aw_flame entities for a placement's particle flames (prepare_scenery
    model_flames); same transform as the placed geometry."""
    if NO_FLAMES or not model.get('flames'):
        return []
    rotation = reference_rotation(ref)
    origin = (np.array(ref['position']) - np.array([*centre, 0])) * SCALE
    out = []
    for flame in model['flames']:
        x, y, z, size = flame[:4]
        p = origin + rotation @ np.array([x, y, z], dtype=float) * SCALE * ref['scale']
        text = '{\n"classname" "aw_flame"\n"origin" "%.2f %.2f %.2f"\n"aw_flame_size" "%.2f"\n' % (
            p[0], p[1], p[2], size * ref['scale'])
        if len(flame) >= 7:
            # Emitter shape in map units: particle size, rise and cone spread.
            k = SCALE * ref['scale']
            text += '"aw_flame_shape" "%.2f %.2f %.2f"\n' % (flame[4] * k, flame[5] * k, flame[6] * k)
        out.append(text + '}')
    return out
from prepare_scenery import reference_rotation
from exterior_visibility import apply_exterior_selection, VisibilityPolicyError


def mipadjust(axes):
    """Engine mip factor of a texture mapping (model.c Mod_LoadTexinfo)."""
    length=(float(np.linalg.norm(axes[:,0]))+float(np.linalg.norm(axes[:,1])))/2
    return 4 if length<0.32 else 3 if length<0.49 else 2 if length<0.99 else 1


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


def standing_planes(points, equations, exact=False):
    """Obstacle planes after expansion by the standing player box.

    Open stair shells need edge bevels as well as face/axial planes: offsetting
    those planes alone can close a narrow arch even when the box fits through.
    Build the complete convex sum offline; the native clipper stays unchanged.
    """
    if exact:
        from itertools import product
        from scipy.spatial import ConvexHull
        corners = np.array(list(product(*zip(MINS, MAXS))))
        expanded = (points[:, None, :] - corners[None, :, :]).reshape(-1, 3)
        return np.unique(np.round(ConvexHull(expanded).equations, 5), axis=0)
    result = bounded_planes(points, equations).copy()
    result[:, 3] -= np.where(result[:, :3] >= 0,
                            -result[:, :3]*MINS, -result[:, :3]*MAXS).sum(axis=1)
    return result


def _prepare_model(task):
    mi, m, profile, archive_path, *extras = task
    name = m['source']
    with Path(archive_path).open('rb') as archive:
        vv,ff,_=unpack_geometry(read_asset(archive,m));v=np.array(vv);f=np.array(ff)
        visual_f=apply_exterior_selection(f,m)
        lod={};visual_v=v
        if m.get('exterior_visibility'):
         lod['exterior_visibility']={'source_triangles':len(f),'visible_triangles':len(visual_f),
                                    'excluded_triangles':len(f)-len(visual_f),
                                    'collision':'original input unchanged'}
        if len(visual_f)!=len(f) and profile.get('flatten'):
         raise VisibilityPolicyError('Combine flattening and source exclusions only after explicit pipeline validation')
        if profile.get('ratio'):
         prefixes=profile.get('preserve_shape_prefixes',[])
         matched={prefix:[i for i,mat in enumerate(m['materials'])
                          if mat.get('source_shape','').casefold().startswith(prefix.casefold())]
                  for prefix in prefixes}
         if any(not values for values in matched.values()):raise ValueError('Missing preserved structural shape in '+name)
         keep={i for values in matched.values() for i in values}
         visual_v,visual_f,details=reduce_mesh(v,visual_f,profile['ratio'],keep,profile.get('preserve_shared_seams',False))
         lod.update(details)
        texsize = profile.get('texture_size', 64)
        reduction=scenery_reduce.scenery_reduce()
        if reduction and scenery_reduce.eligible(profile) and len(visual_f):
         # Visual only: collision below keeps the original source mesh.
         visual_v,visual_f,details=scenery_reduce.reduce_scenery(visual_v,visual_f,reduction[0],reduction[1]/texsize)
         lod['scenery_reduce']=details
        if profile.get('flatten'):
         from surface_flatten import bake_panel
         texture_records=extras[0]
         def source_image(material):
          ti=m['materials'][material]['texture_index']
          if ti is None:return np.full((1,1,3),180,dtype=np.uint8)
          raw=read_asset(archive,texture_records[ti]);_,w,h=struct.unpack_from('>4sHH',raw)
          return np.frombuffer(raw[8:],np.uint8).reshape(h,w,4)
         visual_v,visual_f,baked,details=bake_panel(v,f,m['materials'],source_image,profile['flatten'])
         lod['flatten']=details;lod['_flat_rgb']=baked
        collision_v,collision_f=v,f
        if m.get('collision'):
         cv,cf,_=unpack_geometry(read_asset(archive,m['collision']))
         collision_v,collision_f=np.array(cv),np.array(cf)
         lod['collision']='authored RootCollisionNode, approximate convex conversion'
        pieces,exact,note=collision_pieces(collision_v,collision_f,profile)
        if note:lod['collision'] = note
        if exact:
         lod['collision_bevels'] = 'exact standing-box convex sum'
    if profile.get('collision_only'):
        # Sprite foliage retains source collision without a duplicate visible mesh.
        polys = []
        lod['representation'] = 'collision_only'
    else:
        budget = scenery_reduce.snap_budget()
        stats = {}
        polys = surface_polygons(visual_v, visual_f, snap=None if budget is None else budget[0]/texsize, stats=stats)
        if budget is not None:
            lod['texinfo_snap'] = {'tolerance_texels': budget[0], 'triangles': stats.get('triangles', 0),
                                   'mapping_clusters': stats.get('mapping_clusters', 0),
                                   'polygons': stats.get('polygons', 0),
                                   'max_texel_deviation': stats.get('max_deviation', 0.)*texsize}
    if texsize not in (16, 32, 64):
        raise ValueError('Unsupported static texture size')
    polys = [(patch, mat, ax, off, normal) for poly, mat, ax, off, normal in polys
             for patch in split_surface(poly, np.column_stack((ax.T*texsize, off*texsize)))]
    # The assembly pass recomputes world-space hulls after each placement.
    pieces = [(points, None, ids, error) for points, hull, ids, error in pieces]
    return mi, (v, f, polys, pieces, lod)


def _instance_key(ref, lighting):
    key=(ref['model_index'],round(ref['scale'],6),round(ref['rotation_radians'][0],6),round(ref['rotation_radians'][1],6))
    # Tilt and yaw do not commute. Flat instances can still share one bake.
    if any(abs(math.sin(a))>1e-7 or math.cos(a)<0 for a in ref['rotation_radians'][:2]):
        key=(*key,round(ref['rotation_radians'][2],6))
    return (*key,ref['number']) if lighting and not lighting.get('shared_ambient') else key


def _stable_face_normal(points):
    """Use the whole Temple polygon; merged leading edges may be collinear.

    Work relative to one vertex to avoid cancellation from large offsets.
    Retain authored vertices: reject a warped surface rather than projecting
    it or silently dropping geometry. The tolerance is in BSP world units.
    """
    relative=points-points[0]
    area=np.cross(relative,np.roll(relative,-1,axis=0)).sum(axis=0)
    magnitude=np.linalg.norm(area)
    if not np.isfinite(relative).all() or not np.isfinite(magnitude) or magnitude<=1e-12:
        raise ValueError('Degenerate Temple surface plane')
    normal=area/magnitude
    deviation=float(np.max(np.abs(relative@normal)))
    if deviation>.05:
        raise ValueError(f'Nonplanar Temple surface: {deviation:.6g} exceeds 0.05')
    return normal


def _placement_frame(ref, centre):
    """Entity origin and yaw matrix of a placement (the lightmap bake frame)."""
    origin=(np.array(ref['position'])-np.array([*centre,0]))*SCALE
    yr=math.radians(-ref['rotation_radians'][2]*180/math.pi)
    return origin,np.array([[math.cos(yr),-math.sin(yr),0],[math.sin(yr),math.cos(yr),0],[0,0,1]])


def _prepare_placement(task):
    from scipy.spatial import ConvexHull
    from types import SimpleNamespace
    ref, data, texsize, centre, lighting, *options = task
    stable_planes=bool(options and options[0])
    snap_planes=scenery_reduce.texinfo_snap() is not None
    v,f,polys,components,lod=data
    origin,rotation=_placement_frame(ref,centre)
    o=np.zeros(3)
    # Runtime applies the entity yaw. Bake its inverse first so the composed
    # transform is exactly the authored TES3 rotation, including tilted rocks.
    r=rotation.T @ reference_rotation(ref);scale=ref['scale']
    visual_delta=r @ np.asarray(ref.get("_visual_offset", [0,0,0]), dtype=float)*scale
    surfaces=[]
    for polygon,material,axes,offset,source_normal in polys:
        q=polygon@r.T*scale+o
        if stable_planes:n=_stable_face_normal(q)
        elif snap_planes:
            # Merged polygons may start with collinear vertices; the whole
            # polygon's area vector gives the plane (default path unchanged).
            rel=q-q[0];n=np.cross(rel,np.roll(rel,-1,axis=0)).sum(axis=0);n/=np.linalg.norm(n)
        else:
            n=np.cross(q[1]-q[0],q[2]-q[0]);n/=np.linalg.norm(n)
        normal=r@source_normal
        q=q+normal*ref.get('_flatten_shift',0)+visual_delta
        if n@normal<0:q=q[::-1];n=-n
        ax=r@axes/scale*texsize;off=offset*texsize-o@ax-visual_delta@ax
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
    bounds=np.concatenate([points, *(surface[0] for surface in surfaces)])
    return surfaces,worldparts,bounds.min(axis=0)-1,bounds.max(axis=0)+1


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


def append_meshes(src, out, scenery, palette, centre=CENTRE, lighting=None, jobs=None,
                  references=None, prepared_models=None, retain_dressing=False, collision_bounds=None, collision_compiler=None, collision_cache=None, terrain_visual_cull=None, terrain_cull_config=None,
                  map_identity=None, cell_identity=None, subcell_identity=None, terrain_cull_overlap=None, legacy_terrain_preview=False):
    with (scenery/'scenery.mwpak').open('rb') as archive:
        return _append_meshes(src, out, scenery, palette, archive, centre, lighting,
                              jobs, references, prepared_models, retain_dressing,
                              collision_bounds, collision_compiler, collision_cache, terrain_visual_cull,
                              terrain_cull_config, map_identity, cell_identity, subcell_identity, terrain_cull_overlap, legacy_terrain_preview)


def _append_meshes(src, out, scenery, palette, archive, centre, lighting, jobs,
                   references, prepared_models, retain_dressing, collision_bounds,
                   collision_compiler, collision_cache, terrain_visual_cull, terrain_cull_config,
                   map_identity, cell_identity, subcell_identity, terrain_cull_overlap, legacy_terrain_preview):
    b=src.read_bytes();assert struct.unpack_from('<i',b)[0]==29
    lumps=[bytearray(b[o:o+s]) for o,s in [struct.unpack_from('<ii',b,4+k*8) for k in range(15)]]
    face_planes=[struct.unpack_from('<H',lumps[7],i)[0] for i in range(0,len(lumps[7]),20)]
    index=json.loads((scenery/'scenery-index.json').read_text())
    from terrain_visual_cull import ground_from_bsp, resolve_policy, cull_surfaces
    config_path=Path(__file__).resolve().parents[1]/'config/terrain-visual-cull.json'
    if terrain_cull_config is None:
        terrain_cull_config=json.loads(config_path.read_text(encoding='utf-8')) if config_path.exists() else {}
    identity=map_identity or (out.parent.name if out.name=='scene.bsp' else out.stem)
    cull_policy=resolve_policy(terrain_cull_config,map_identity=identity,
                             cell_identity=cell_identity or index.get('cell'),
                             subcell_identity=subcell_identity,force=terrain_visual_cull,overlap_force=terrain_cull_overlap)
    # Production assembly stays unculled. Authoritative direct LAND processing
    # runs last, after every terrain/building/scenery component is present.
    terrain,terrain_receipt=ground_from_bsp(b,overlap=cull_policy['overlap']) if legacy_terrain_preview and cull_policy['enabled'] and 'cell' not in index else (None,{'stage':'deferred final canonical pass','unculled_seed_preserved':True})
    cull_reports=[]
    pal=Image.new('P',(1,1));pal.putpalette(palette.read_bytes())
    texdata=lumps[2];nt=struct.unpack_from('<i',texdata)[0];offsets=list(struct.unpack_from('<'+str(nt)+'i',texdata,4));textures=[bytes(texdata[o:offsets[k+1] if k+1<nt else len(texdata)]) for k,o in enumerate(offsets)]
    texture_cache={};planes_cache={};texinfo_cache={};models={};report=[];collision_fallbacks=[]
    base_faces=len(lumps[7])//20;regrids=0
    snap=scenery_reduce.snap_budget();snap=None if snap is None else snap[1];snap_buckets={};texinfo_vectors={};texinfo_keys={};snap_shared=[0,0.,0]
    from surface_flatten import load_profiles
    # Interior exporters record the named cell. Keep their authored window
    # geometry unless a profile explicitly approves interior mounting too.
    flatten_profiles=load_profiles(scene_kind='interior' if 'cell' in index else 'exterior')
    profiles={name:profile for group in index.get('groups',{}).values()
              for name,profile in group.get('visual_profiles',{}).items()}
    empty_leaf=next(i for i in range(len(lumps[10])//28) if struct.unpack_from('<i',lumps[10],i*28)[0]==-1)
    def plane(n,d):
     key=tuple(np.round([*n,d],5))
     if key not in planes_cache:
      i=len(lumps[1])//20;planes_cache[key]=i;lumps[1]+=struct.pack('<4fi',*n,d,3)
     return planes_cache[key]
    def texture(m,mi,size):
     if mi==len(m['materials']):
      key=('flatten',m['source'],size)
      if key not in texture_cache:
       im=Image.fromarray(models[model_ids[m['source']]][4]['_flat_rgb']).quantize(palette=pal,dither=Image.Dither.NONE)
       texture_cache[key]=len(textures);textures.append(miptex('flat'+str(len(textures)),im))
      return texture_cache[key]
     mat=m['materials'][mi];ti=mat['texture_index'];glow=0 if NO_EMISSIVE else int(mat.get('emissive',0))
     key=(ti,size,tuple(round(x,2) for x in mat['diffuse']),glow)
     if key not in texture_cache:
      if ti is None:rgb=np.full((32,32,3),180.)
      else:
       raw=read_asset(archive,index['textures'][ti]);_,w,h=struct.unpack_from('>4sHH',raw);rgb=np.frombuffer(raw[8:],np.uint8).reshape(h,w,4)[:,:,:3].astype(float)
      rgb*=np.array(mat['diffuse']);im=Image.fromarray(np.clip(rgb,0,255).astype(np.uint8)).resize((size,size)).quantize(palette=pal,dither=Image.Dither.NONE)
      # "emitN_" marks a self-lit material for the engine (r_surf.c R_EmissiveLevel).
      t=len(textures);texture_cache[key]=t;textures.append(miptex(('emit%d_%d'%(glow,t)) if glow else 'surface'+str(t),im))
     return texture_cache[key]
    def collider(pieces, exact=False, model_name='', reference=0):
     if not pieces:return -empty_leaf-1,-1
     # A union of convex volumes. Outside each piece tries the next one.
     compiled=None
     if exact and collision_compiler:
      from collision_bsp import compile_standing
      try:compiled=compile_standing(pieces,collision_compiler,collision_cache)
      except ValueError as error:
       collision_fallbacks.append({'model':model_name,'reference':reference,'reason':str(error),
                                   'fallback':'exact standing-box convex pieces'})
       print('Collision union fallback to exact planes:',model_name,reference,str(error)[-200:],flush=True)
     roots=[];noderoots=[]
     for k,(points,hull,ids,error) in enumerate(pieces):
      point_eq=np.unique(np.round(hull.equations,5),axis=0)
      eq=standing_planes(points,point_eq,exact) if compiled is None else [];root=len(lumps[9])//8;noderoot=len(lumps[5])//24;roots.append(root);noderoots.append(noderoot)
      count=len(eq)
      nxt=root+count if k+1<len(pieces) else -1
      low=np.floor(points.min(axis=0)).astype(int);high=np.ceil(points.max(axis=0)).astype(int)
      for j,e in enumerate(eq):
       n=e[:3];d=-e[3]
       pi=plane(n,d);inside=root+j+1 if j+1<count else -2
       if max(nxt,inside)>=65520:raise ValueError('Clipnode budget exceeded')
       lumps[9]+=struct.pack('<iHH',pi,nxt&65535,inside&65535)
      # Point traces need no expansion or extra axial nodes. Retain their
      # original hull, saving nodes/RAM and LOS work for proximity greetings.
      nnxt=noderoot+len(point_eq) if k+1<len(pieces) else -empty_leaf-1
      for j,e in enumerate(point_eq):
       n=e[:3];d=-e[3]
       pn=plane(n,d);nin=noderoot+j+1 if j+1<len(point_eq) else -1
       if max(nnxt,nin)>32767:raise ValueError('Point node budget exceeded')
       lumps[5]+=struct.pack('<ihh6h2H',pn,nnxt,nin,*low,*high,0,0)
     if compiled is not None:
      nodes,croot=compiled;start=len(lumps[9])//8
      if start+len(nodes)>=65520:raise ValueError('Compiled collision node budget exceeded')
      for equation,front,back in nodes:
       pi=plane(equation[:3],equation[3])
       children=[start+n if n>=0 else n&65535 for n in (front,back)]
       lumps[9]+=struct.pack('<iHH',pi,*children)
      return noderoots[0],start+croot if croot>=0 else croot
     return noderoots[0],roots[0]
    entities=[];instance_models={};collision_models={};visual_models={};part_cache={}
    def entity(modelnum,origin,yaw,reference):
     return '{\n"classname" "func_wall"\n"aw_ref" "'+str(reference)+'"\n"model" "*'+str(modelnum)+'"\n"origin" "'+' '.join(f'{x:.5f}' for x in origin)+'"\n"angles" "0 '+str(yaw)+' 0"\n}'

    if references is None:
        selected, selection_report = select_runtime_refs(index, centre, SCALE, 736)
    else:
        wanted = set(references)
        selected = [dict(r) for r in index['references'] if r['number'] in wanted]
        if {r['number'] for r in selected} != wanted:
            raise ValueError('Explicit BSP references were not all converted')
        selection_report = {'selected_groups': [], 'omitted': [], 'explicit_references': len(wanted)}
    def resident_parts(parts,ref):
        if collision_bounds is None:return tuple(range(len(parts)))
        yaw=-ref['rotation_radians'][2];co=math.cos(yaw);si=math.sin(yaw)
        rotation=np.array([[co,-si,0],[si,co,0],[0,0,1]])
        origin=(np.array(ref['position'])-np.array([*centre,0]))*SCALE
        kept=[]
        for i,part in enumerate(parts):
            points=part[0]@rotation.T+origin;lo=points.min(axis=0);hi=points.max(axis=0)
            if all(hi[a]>=collision_bounds[0][a] and lo[a]<=collision_bounds[1][a] for a in range(2)):kept.append(i)
        return tuple(kept)
    excluded = ([] if retain_dressing is True else
                [t for t in DRESSING_EXCLUDED if not retain_dressing or t not in retain_dressing])
    # No silent drops (BUILD-DRESSING-EXCLUDED-32): every placement left out
    # here is listed in the result's "omitted" with the rule that removed it,
    # and every dressing piece kept in "dressing_retained".
    def dressing_term(ref, terms):
        return next((t for t in terms if t in index['models'][ref['model_index']]['source']), None)
    omitted = [dict(reference=ref['number'], id=ref.get('id'), model=index['models'][ref['model_index']]['source'],
                    reason='dressing excluded by the mesh converter (%s)' % term)
               for ref in selected for term in [dressing_term(ref, excluded)] if term]
    dressing_retained = [dict(reference=ref['number'], id=ref.get('id'),
                              model=index['models'][ref['model_index']]['source'], rule=term)
                         for ref in selected for term in [dressing_term(ref, DRESSING_EXCLUDED)]
                         if term and term not in excluded]
    unique = dict.fromkeys(ref['model_index'] for ref in selected
                           if not any(t in index['models'][ref['model_index']]['source']
                                      for t in excluded))
    for mi in unique:
        model=index['models'][mi]
        profiles.setdefault(model['source'],rock_profile(model['source'],model['triangles']))
        if model['source'] in flatten_profiles:
            profiles[model['source']]={**profiles[model['source']], 'flatten':flatten_profiles[model['source']]}
    model_ids={m['source']:i for i,m in enumerate(index['models'])}
    tasks = [(mi, index['models'][mi], profiles.get(index['models'][mi]['source'], {}),
              scenery/'scenery.mwpak',index['textures']) for mi in unique]
    workers = min(resolve_jobs(jobs), max(1, len(tasks)))
    print(f'BSP geometry workers: {workers}; {len(tasks)} unique models', flush=True)
    models = ({mi: prepared_models[mi] for mi in unique} if prepared_models is not None
              else dict(ordered_map(_prepare_model, tasks, workers)))
    from surface_flatten import mount_references
    mount_references(index,selected,models,centre,SCALE)
    from visual_offsets import apply_visual_offsets, visual_key
    apply_visual_offsets(index,selected)
    placement_groups={}
    for ref in selected:
        key=(*_instance_key(ref,lighting),round(ref.get('_flatten_shift',0),5),visual_key(ref))
        origin=(np.array(ref['position'])-np.array([*centre,0]))*SCALE
        placement_groups.setdefault(key,[]).append((origin,-ref['rotation_radians'][2]*180/math.pi))
    def placement_tasks():
     seen=set()
     for ref in selected:
       mi=ref['model_index']
       if mi not in models:continue
       key=(*_instance_key(ref,lighting),round(ref.get('_flatten_shift',0),5),visual_key(ref))
       if key in seen:continue
       seen.add(key)
       # Explicit Temple opt-in only; inferred filenames must not alter other maps.
       yield ref,models[mi],profiles.get(index['models'][mi]['source'],{}).get('texture_size',64),centre,lighting,map_identity=='bmtemple'
    # Geometry and lightmaps are private worker results. BSP offsets, shared
    # palettes and entity order are assigned by this single assembly writer.
    from contextlib import closing
    with closing(ordered_map(_prepare_placement,placement_tasks(),workers)) as placements:
     for ref in selected:
      mi=ref['model_index'];m=index['models'][mi];name=m['source']
      if any(t in name for t in excluded):continue
      o=(np.array(ref['position'])-np.array([*centre,0]))*SCALE
      origin=o.copy();o=np.zeros(3);yaw=-ref['rotation_radians'][2]*180/math.pi
      key=(*_instance_key(ref,lighting),round(ref.get('_flatten_shift',0),5),visual_key(ref))
      v,f,polys,components,lod=models[mi]
      texsize=profiles.get(name,{}).get('texture_size',64)
      if key in visual_models:
       worldparts=part_cache[key];subset=resident_parts(worldparts,ref);variant=(key,subset)
       if variant not in instance_models:
        collision_key=(_instance_key(ref,None),subset)
        if collision_key not in collision_models:
         collision_models[collision_key]=collider([worldparts[i] for i in subset],bool(lod.get('collision_bevels')),name,ref['number'])
        nroot,croot=collision_models[collision_key]
        original=visual_models[key];header=bytearray(lumps[14][original*64:(original+1)*64])
        struct.pack_into('<4i',header,36,nroot,croot,croot,croot)
        instance_models[variant]=len(lumps[14])//64;lumps[14]+=header
       entities.append(entity(instance_models[variant],origin,yaw,ref['number']));entities.extend(flame_entities(ref,m,centre));continue
      surfaces,worldparts,lo,hi=next(placements);part_cache[key]=worldparts
      if terrain is not None and terrain.prisms:
       surfaces,cull_counts=cull_surfaces(surfaces,terrain,placement_groups[key])
       cull_reports.append({'model':name,'reference':ref['number'],**cull_counts})
      subset=resident_parts(worldparts,ref);variant=(key,subset)
      firstface=len(lumps[7])//20;vmap={};emap={};frame=None
      def vertex(p):
       key=tuple(np.round(p,5))
       if key not in vmap:vmap[key]=len(lumps[3])//12;lumps[3]+=struct.pack('<3f',*p)
       if vmap[key] >= 65536:raise ValueError('Vertex budget exceeded')
       return vmap[key]
      for q,n,ax,off,material,samples in surfaces:
       samples_stale=False
       if snap is not None:
        # A shared mapping may have a normal component; the engine picks
        # mip levels from the axis lengths (model.c mipadjust). Keep the
        # face's own mip choice: else store the exactly equal in-plane
        # mapping (same texels and lightmap grid on this face).
        inplane=ax-np.outer(n,n@ax);own_mip=mipadjust(inplane)
        if mipadjust(ax)!=own_mip:
         off=off+float(n@q[0])*(n@ax);ax=inplane;snap_shared[2]+=1
       pi=plane(n,float(n@q[0]));t=texture(m,material,texsize);txkey=(*np.round(ax.flatten(),5),*np.round(off,4),t)
       if snap is not None and txkey not in texinfo_cache and material<len(m['materials']):
        # Reuse a mapping of the map that gives this face's texels within
        # the snap tolerance (modulo the texture size); bake with it. The
        # face's texture coordinates must stay small: the engine keeps
        # texturemins in 16 bits.
        bucket=snap_buckets.setdefault((t,*np.round(ax.flatten(),3)),[])
        for cand in bucket:
         cax,coff=texinfo_vectors[cand]
         d=q@(cax-ax)+(coff-off);d=d-texsize*np.round(d.mean(axis=0)/texsize)
         dev=float(np.abs(d).max())
         if dev<=snap and mipadjust(cax)==own_mip and np.abs(q@cax+coff).max()<16384:
          snap_shared[0]+=1;snap_shared[1]=max(snap_shared[1],dev)
          txkey=texinfo_keys[cand]
          ax,off=cax,coff;samples_stale=True;break
       else:
        bucket=None
       if txkey not in texinfo_cache:
        tx=len(lumps[6])//40;texinfo_cache[txkey]=tx;lumps[6]+=struct.pack('<8fii',*ax[:,0],off[0],*ax[:,1],off[1],t,0)
        if snap is not None:
         texinfo_vectors[tx]=(ax,off);texinfo_keys[tx]=txkey
         if bucket is not None:bucket.append(tx)
       tx=texinfo_cache[txkey];verts=[vertex(p) for p in q[::-1]];firstedge=len(lumps[13])//4
       # BSP29 stores the face texinfo index in 16 bits; the engine reads it
       # unsigned (VIVEC-TEXINFO-31).
       if tx>65535:raise ValueError('Texture mapping budget exceeded: %d mappings, limit 65,536'%(tx+1))
       # The engine sizes the lightmap from the STORED single-precision vertex
       # and texinfo values (vertices and mappings are shared within 1e-5), so
       # compute the grid from them; rebake where the unstored grid differs
       # (LIGHTMAP-TAIL-31, LIGHTMAP-GRID-31).
       mins,extents=engine_grid(face_points(lumps[3],verts),texinfo_vecs(lumps[6],tx))
       for a,c in zip(verts,verts[1:]+verts[:1]):
        if (a,c) in emap:ed=emap[a,c]
        elif (c,a) in emap:ed=-emap[c,a]
        else:ed=len(lumps[12])//4;emap[a,c]=ed;lumps[12]+=struct.pack('<HH',a,c)
        lumps[13]+=struct.pack('<i',ed)
       lightoffset=-1;styles=(255,255,255,255)
       if samples is not None:
        from interior_lighting import bake_grid, bake_surface
        dims=sample_dimensions(extents);low,size=bake_grid(q,ax,off)
        if samples_stale or tuple(low)!=mins or tuple(size)!=dims:
         if frame is None:frame=_placement_frame(ref,centre)
         samples=bake_surface(q,ax,off,frame[1],frame[0],lighting,sample_grid=(mins,dims));regrids+=1
        if len(samples)!=dims[0]*dims[1]:raise ValueError('Lightmap sample count differs from the engine grid')
        lightoffset=len(lumps[8]);lumps[8]+=samples;styles=(0,255,255,255)
       face_planes.append(pi)
       lumps[7]+=struct.pack('<HhihH4Bi',0,0,firstedge,len(verts),tx,*styles,lightoffset)
      collision_key=(_instance_key(ref,None),subset)
      if collision_key not in collision_models:
       collision_models[collision_key]=collider([worldparts[i] for i in subset], bool(lod.get('collision_bevels')),name,ref['number'])
      nroot,croot=collision_models[collision_key]
      modelnum=len(lumps[14])//64;nf=len(lumps[7])//20-firstface
      lumps[14]+=struct.pack('<9f7i',*lo,*hi,0,0,0,nroot,croot,croot,croot,0,firstface,nf)
      visual_models[key]=modelnum;instance_models[variant]=modelnum;entities.append(entity(modelnum,origin,yaw,ref['number']));entities.extend(flame_entities(ref,m,centre))
      report.append({'model':name,'faces':nf,'collision_parts':len(components),'scale':ref['scale'],'visual_lod':{k:v for k,v in lod.items() if not k.startswith('_')},'texture_size':texsize});print(len(report),name,nf,len(lumps[9])//8,len(lumps[5])//24,flush=True)
      if len(lumps[5])//24>32767 or len(lumps[9])//8>=65520:raise ValueError('Node budget exceeded')
    order_face_planes(lumps,face_planes)
    # Every converted face must fit 256 texels under any FPU rule
    # (MESH-EXTENT-GRID-31); world faces from qbsp keep their own checks.
    checked_faces=check_lumps(lumps,base_faces)
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
    result={'models':report,'selection':selection_report,
            'terrain_visual_cull':{'policy':cull_policy,'terrain':terrain_receipt,'models':cull_reports,
                                  'collision':'unchanged original components and hull generation',
                                  'shared_geometry':'unculled assembly; final canonical pass owns placement variants',
                                  'legacy_preview':bool(legacy_terrain_preview),
                                  'acceptance':'Legacy preview is not canonical production acceptance' if legacy_terrain_preview else 'Deferred to final canonical source pass'},
            'collision_compiler_fallbacks':collision_fallbacks,
            'omitted':omitted,'dressing_retained':dressing_retained,
            'groups':index.get('groups',{}),
            'faces':len(lumps[7])//20,'vertices':len(lumps[3])//12,
            'texinfo':len(lumps[6])//40,
            'texinfo_snap':None if snap is None else {'tolerance_texels':scenery_reduce.texinfo_snap(),'map_reuse_texels':snap,'faces_sharing_by_tolerance':snap_shared[0],
                                                      'max_texel_deviation':snap_shared[1],
                                                      'mip_guard_inplane_faces':snap_shared[2]},
            'scenery_reduce':scenery_reduce.scenery_reduce(),
            'surface_check':{'faces':checked_faces,'lightmap_regrids':regrids,
             'rule':'engine grid from stored single-precision values; extents within 256 under engine, binary32 and extended rules'},
            'nodes':len(lumps[5])//24,'clipnodes':len(lumps[9])//8,'bytes':out.stat().st_size,
            'instances':len(entities),'unique_models':len(instance_models),
            'collision':'multipart convex union; exact standing-box bevels for open shells, axial bounds otherwise',
            'scope':'resident bounded scene, shared building meshes, no cells streamed during play'}
    return result


from build_jobs import add_jobs, resolve_jobs
from vis_options import light_args
from build_parallel import ordered_map

def prepare(scene, out, scenery, qbsp, vis, light, jobs=None, terrain_visual_cull=None, terrain_cull_config=None, map_identity=None, cell_identity=None, subcell_identity=None, terrain_cull_overlap=None, vis_mode='fast'):
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
    for executable,options,target in [(qbsp,['-nopercent'],'seyda.map'),(vis,['-fast'] if vis_mode=='fast' else [],'seyda.bsp'),(light,light_args('-minlight','100'),'seyda.bsp')]:
        subprocess.run([str(Path(executable).resolve()),*(['-threads',str(resolve_jobs(jobs))] if executable==vis else []),*options,target],cwd=out,check=True)
    base=out/'seyda-base.bsp';(out/'seyda.bsp').rename(base)
    rebuild_world_hull(base,out/'seyda.map',qbsp,discard_stock_hulls=True)
    result=append_meshes(base,out/'seyda.bsp',scenery,out/'id1/gfx/palette.lmp',jobs=jobs,terrain_visual_cull=terrain_visual_cull,terrain_cull_config=terrain_cull_config,map_identity=map_identity,cell_identity=cell_identity,subcell_identity=subcell_identity,terrain_cull_overlap=terrain_cull_overlap)
    shutil.copyfile(out/'seyda.bsp',out/'id1/maps/seyda.bsp')
    result['format']='AmiWind compiled mesh BSP29'
    result['standing_hull_profile']=PROFILE
    result['standing_hull']=[MINS,MAXS]
    (out/'scene-ready.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['scene','out','scenery','qbsp','vis','light']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--terrain-visual-cull',choices=('true','false'),default=None)
    p.add_argument('--terrain-cull-config',type=Path)
    p.add_argument('--terrain-cull-overlap',type=float)
    p.add_argument('--map-identity')
    p.add_argument('--cell-identity')
    p.add_argument('--subcell-identity')
    from vis_options import add_vis_option
    scenery_reduce.add_options(p)
    add_jobs(p);add_vis_option(p);a=p.parse_args();scenery_reduce.apply_options(a)
    try:print(json.dumps(prepare(a.scene,a.out,a.scenery,a.qbsp,a.vis,a.light,a.jobs,None if a.terrain_visual_cull is None else a.terrain_visual_cull=='true',json.loads(a.terrain_cull_config.read_text(encoding='utf-8')) if a.terrain_cull_config else None,a.map_identity,a.cell_identity,a.subcell_identity,a.terrain_cull_overlap,a.vis_mode),indent=2))
    except (OSError,ValueError,subprocess.CalledProcessError) as e:p.exit(1,str(e)+'\n')

if __name__=='__main__':main()
