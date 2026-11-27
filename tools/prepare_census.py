#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Build the owned Census Office cell and retain placed-reference identities."""
import argparse
import contextlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
import numpy as np
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from mwad.paths import resolve_data_files, child_ci, ensure_external
from mwad.masters import master_path
from mwad.interior import read_interior, select_geometry
from mwad.npc import load_master, text
from prepare_scenery import export_refs
from prepare_mesh_bsp import add_dressing_option, append_meshes, apply_dressing_option, interior_dressing
from prepare_quake import box, wad, miptex
from prepare_npcs import quote
from player_hull import lumps, pack_lumps, rebuild_world_hull
from prepare_doors import prepare as prepare_doors
from build_jobs import add_jobs, resolve_jobs
from vis_options import add_vis_option, light_args, vis_args


CENSUS_ACTORS = [('chargen class','census',6),('chargen captain','captain',7),('chargen door guard','hall',8)]
# Record types of the items a player can take (the original's carryable classes; lights are kept as scenery).
ITEM_TYPES = ('ALCH','APPA','ARMO','BOOK','CLOT','INGR','LOCK','MISC','PROB','REPA','WEAP')


def is_census_item(ref):
    """A placed, takeable item of the office with a model of its own (actors and levelled lists stay out)."""
    return (ref.get('type') in ITEM_TYPES and not ref.get('deleted') and bool(ref.get('model'))
            and 'marker' not in ref['model'].replace('\\','/').lower())


@contextlib.contextmanager
def items_share_models(numbers):
    """Equal item placements share one model even on the lit office map: one model slot per item model, not per item.
    The engine held 256 models then (a byte model index; 512 since ENGINE-MODEL-TABLE-58, BUILD-BUDGET-ENGINE-LIMITS-35);
    with an own lit model each, the 124 items took the office to 284. The shared bake is the first equal item's lightmap.
    Scoped to this converter so no other map's placements change."""
    import prepare_mesh_bsp
    original=prepare_mesh_bsp._instance_key
    def key(ref,lighting,unlit=False):
        return original(ref,lighting,unlit or ref['number'] in numbers)
    prepare_mesh_bsp._instance_key=key
    try:yield
    finally:prepare_mesh_bsp._instance_key=original


# ITEM-AIM-UNDER-OTHERS-69: the office's item models that keep every drawn triangle, by their entry in
# config/room-item-faces.json (read by this converter alone, so only this stage keys it). The converter's surface pass
# (mesh_geometry.surface_polygons) leaves out a triangle whose doubled area at the quarter scale is under
# SURFACE_FLOOR: right for the world, but on a small item it takes the fine parts. The Iron Dagger (chargen dagger,
# w_iron_dagger.nif, upright in the note on the table) lost its guard's ends that way: 88 of its 206 triangles drawn,
# the guard at 0.7 of its width, a 1-2 pixel stick. tests/test_census_item_faces.py keeps SURFACE_FLOOR equal to that
# pass's own floor.
ROOM_ITEM_FACES_PATH = Path(__file__).resolve().parents[1] / 'config/room-item-faces.json'
SURFACE_FLOOR = .05


def room_item_faces(room, path=None):
    """{model path (meshes/..., lower case): entry} of config/room-item-faces.json for ROOM, every entry validated
    (ValueError naming it): the room, the model, extra_faces (the triangles it may keep beyond the surface floor), a
    reason, the measured cost (before + added = total, added at most extra_faces) and the Pi check."""
    data = json.loads(Path(path or ROOM_ITEM_FACES_PATH).read_text(encoding='utf-8'))
    if data.get('schema') != 1 or not isinstance(data.get('entries'), list):
        raise ValueError('room-item-faces: schema 1 with an entries list expected')
    out, seen = {}, set()
    for entry in data['entries']:
        model = str(entry.get('model', '')).strip().replace('\\', '/').lower()
        where = str(entry.get('room', '')).strip().lower()
        extra = entry.get('extra_faces')
        cost = entry.get('cost') or {}
        if not model.startswith('meshes/') or not where:
            raise ValueError('room-item-faces: entry without a room or a meshes/ model: %r' % entry)
        if type(extra) is not int or extra <= 0:
            raise ValueError('room-item-faces: %s: extra_faces must be a positive integer' % model)
        if not str(entry.get('reason', '')).strip():
            raise ValueError('room-item-faces: %s: a reason is required' % model)
        if not all(type(cost.get(k)) is int for k in ('before', 'added', 'total')) or \
                cost['before'] + cost['added'] != cost['total'] or cost['added'] > extra:
            raise ValueError('room-item-faces: %s: cost must be before + added = total, added <= extra_faces' % model)
        if not str(entry.get('pi_check', '')).strip():
            raise ValueError('room-item-faces: %s: pi_check (pending or the bench that passed) is required' % model)
        if (where, model) in seen:
            raise ValueError('room-item-faces: %s listed twice for %s' % (model, where))
        seen.add((where, model))
        if where == room:
            out[model] = entry
    return out


def small_polygons(v, f, floor=SURFACE_FLOOR):
    """The triangles of V F (vertices x y z u v, faces a b c material) that the surface pass leaves out (doubled area
    under FLOOR at the quarter scale), each a polygon of its own in that pass's form: (points, material, texture axes,
    texture offset, normal). Degenerate triangles stay out."""
    out = []
    for face in np.asarray(f):
        p = np.asarray(v, float)[face[:3], :3] * .25
        uv = np.asarray(v, float)[face[:3], 3:5]
        n = np.cross(p[1] - p[0], p[2] - p[0])
        area = float(np.linalg.norm(n))
        if area >= floor or area < 1e-9:
            continue
        n = n / area
        try:
            axes = np.linalg.solve(np.vstack((p[1] - p[0], p[2] - p[0], n)),
                                   np.vstack((uv[1] - uv[0], uv[2] - uv[0], [0, 0])))
        except np.linalg.LinAlgError:
            continue
        out.append((p, int(face[3]), axes, uv[0] - p[0] @ axes, n))
    return out


def drawn_measure(polys):
    """The drawn box (per axis low and high) and the drawn area of surface polygons (points at the quarter scale)."""
    points = np.concatenate([np.asarray(poly, float) for poly, *_ in polys]) if polys else np.zeros((1, 3))
    area = 0.
    for poly, *_ in polys:
        q = np.asarray(poly, float)
        for k in range(1, len(q) - 1):     # a convex polygon: the fan of its triangles
            area += float(np.linalg.norm(np.cross(q[k] - q[0], q[k + 1] - q[0]))) / 2
    return points.min(axis=0), points.max(axis=0), area


def source_measure(v, f):
    """The box and the area of the source triangles at the quarter scale (degenerate ones left out), as drawn_measure."""
    v = np.asarray(v, float)[:, :3] * .25
    tris = v[np.asarray(f)[:, :3].astype(int)]
    cross = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    used = v[np.unique(np.asarray(f)[:, :3])]
    return used.min(axis=0), used.max(axis=0), float(np.linalg.norm(cross, axis=1).sum()) / 2


def keep_small_faces(task, entry):
    """prepare_mesh_bsp._prepare_model for an item model of config/room-item-faces.json, in this process: the surface
    pass also keeps the triangles under its floor (small_polygons). Refuses (ValueError) when it keeps more than the
    entry's extra_faces, or when the drawn model is not the source's size (every axis of its box at 0.99 or more,
    its area at 0.99 or more): the census stage stops in its first seconds, never ships a thinner model."""
    import prepare_mesh_bsp
    plain = prepare_mesh_bsp.surface_polygons
    added = []

    def polygons(v, f, geometry_only=False, snap=None, stats=None):
        polys = plain(v, f, geometry_only, snap, stats)
        if snap is None and not geometry_only:
            extra = small_polygons(v, f)
            added.append(len(extra))
            polys = list(polys) + extra
        return polys
    prepare_mesh_bsp.surface_polygons = polygons
    try:
        mi, (v, f, polys, pieces, lod) = prepare_mesh_bsp._prepare_model(task)
    finally:
        prepare_mesh_bsp.surface_polygons = plain
    name = task[1]['source']
    kept = sum(added)
    if not added:
        raise ValueError('room-item-faces: %s: its surface pass did not run as planned (snapped or merged faces)' % name)
    if kept > entry['extra_faces']:
        raise ValueError('room-item-faces: %s keeps %d triangles under the floor, its entry allows %d'
                         % (name, kept, entry['extra_faces']))
    low, high, area = drawn_measure(polys)
    s_low, s_high, s_area = source_measure(v, f)
    widths = [float(high[k] - low[k]) / float(s_high[k] - s_low[k]) if s_high[k] > s_low[k] else 1. for k in range(3)]
    record = {'kept_under_floor': kept, 'faces': len(polys), 'extra_faces': entry['extra_faces'],
              'drawn_width_ratio': [round(w, 4) for w in widths],
              'drawn_area_ratio': round(float(area) / float(s_area), 4) if s_area else 1.}
    if min(widths) < .99 or record['drawn_area_ratio'] < .99:
        raise ValueError('room-item-faces: %s is drawn smaller than its source: %r' % (name, record))
    lod['room_item_faces'] = record
    return mi, (v, f, polys, pieces, lod)


@contextlib.contextmanager
def items_keep_small_faces(entries):
    """The office's item models of ENTRIES (room_item_faces) are prepared by keep_small_faces, in this process; every
    other model as before, in the converter's workers. Scoped to this converter (prepare_mesh_bsp's ordered_map is
    restored on the way out), so no other map changes. Yields {model: record} of what each kept."""
    import prepare_mesh_bsp
    kept = {}
    if not entries:
        yield kept
        return
    real = prepare_mesh_bsp.ordered_map

    def ordered_map(function, items, *args, **kwargs):
        if function is not prepare_mesh_bsp._prepare_model:
            yield from real(function, items, *args, **kwargs)
            return
        items = list(items)
        listed = {i for i, t in enumerate(items) if t[1]['source'].lower() in entries}
        rest = real(function, [t for i, t in enumerate(items) if i not in listed], *args, **kwargs)
        for i, t in enumerate(items):
            if i in listed:
                result = keep_small_faces(t, entries[t[1]['source'].lower()])
                kept[t[1]['source'].lower()] = result[1][4]['room_item_faces']
                yield result
            else:
                yield next(rest)
    prepare_mesh_bsp.ordered_map = ordered_map
    try:
        yield kept
    finally:
        prepare_mesh_bsp.ordered_map = real


# The engine's MAX_MODELS is 512 (ENGINE-MODEL-TABLE-58: a 16-bit model index on the local path); the office keeps a
# margin under it.
CENSUS_MODEL_LIMIT = 480


# Model slots the map does not name: slot 0, the worldspawn precaches (player, view model) and the engine's
# run-time slots (the arena's, the dropped items' and the placed items' room, WORLD-OBJECT-PLACEMENT-59).
# tests/test_map_engine_limits.py keeps it equal to map_engine_limits' count; the engine source is not read here,
# so an engine edit does not re-key this stage.
FIXED_MODEL_SLOTS = 116


def check_model_room(path, limit=CENSUS_MODEL_LIMIT):
    """The finished office map's model slots: the fixed slots, the world and its inline models, and every other
    model an entity names (actors). Refuses at this stage when it passes LIMIT, so a room over the engine's model
    table never reaches the image step's preflight (BUILD-BUDGET-ENGINE-LIMITS-35)."""
    import struct
    data=Path(path).read_bytes()
    offset,size=struct.unpack_from('<ii',data,4)
    _,models_size=struct.unpack_from('<ii',data,4+14*8)
    text=data[offset:offset+size].decode('latin-1').split('\0',1)[0]
    named={m for m in re.findall(r'"model"\s+"([^"\n]*)"',text) if m and not m.startswith('*')}
    models=FIXED_MODEL_SLOTS+models_size//64+len(named)
    if models>limit:
        raise ValueError('%s: %d models, the office keeps under %d (the engine holds 512: MAX_MODELS)'%(
            Path(path).name,models,limit))
    return {'models':models}


def actor_names(master, identifiers):
    """{identifier: displayed name} of NPC records (run beside the conversion: Background)."""
    kinds,_,_=load_master(master)
    return {identifier:text(kinds['NPC_'][identifier],'FNAM') for identifier in identifiers}


def prepare(data_files, scene, qbsp, vis, light, jobs=None, vis_mode='fast'):
    data_files=resolve_data_files(data_files);scene=ensure_external(scene,'census conversion')
    from mwad.paths import unshare_tree
    unshare_tree(scene)  # in place: BUILD-POOL-READONLY-SCENE-WRITE-35
    # Master-only reads (door catalogue, actor names) run beside the conversion.
    from build_parallel import Background
    from prepare_doors import door_sources
    doors=Background(door_sources,data_files,jobs=jobs)
    names=Background(actor_names,master_path(data_files),[i for i,_,_ in CENSUS_ACTORS],jobs=jobs)
    from ui_palette import reserve
    reserve(data_files,scene/'id1')
    target=scene/'id1/maps/census.bsp'
    if target.exists():raise ValueError('Census map already exists; use a fresh scene')
    cell=read_interior(master_path(data_files),'Seyda Neen, Census and Excise Office')
    refs,omitted=select_geometry(cell)
    # The small items (INTERIOR-PLACED-ITEMS-47): the registration paper, the Iron Dagger, the meal and the rest
    # are placed statics like the furniture (a func_wall with aw_ref each, identical items share one inline
    # model), so they are drawn, the focus box finds their edict and the activate key takes and hides them
    # (aw_mwhost.c AW_ObjectTake; kept in the saved game).
    items=[r for r in cell['refs'] if is_census_item(r)]
    taken={r['number'] for r in items}
    refs+=items;omitted=[o for o in omitted if o['reference'] not in taken]
    profiles={}
    for r in refs:
        model='meshes/'+r['model'].replace('\\','/').lower()
        if model.startswith('meshes/i/'):
            profiles[model]={'ratio':1.0,'texture_size':32,'collision_source':'root_node','hollow_collision':True}
    group='census_interior';groups={group:{'references':[r['number'] for r in refs],'visual_profiles':profiles}}
    refs=[dict(r,scene_groups=[group]) for r in refs]
    from interior_lighting import cell_lighting
    lighting=cell_lighting(cell)
    parts=scene/'census-source'
    # Retain detail in rectangular wall art until the final bounded BSP bake.
    # A 32-pixel intermediate reduced tall tapestries to only 16 pixels wide,
    # then the BSP upscaled that loss. Runtime texture budgets stay unchanged.
    export_refs(data_files,parts,refs,groups,[0,0,0],4096,128,{'scope':'Census Office geometry and registration paper','cell':cell['name'],'lighting':lighting},jobs=jobs)
    index=json.loads((parts/'scenery-index.json').read_text())
    if index['errors']:raise ValueError('Census conversion errors: '+str(index['errors']))
    low=np.floor(np.min([r['bounds'][0] for r in index['references']],axis=0)*.25)-32
    high=np.ceil(np.max([r['bounds'][1] for r in index['references']],axis=0)*.25)+32
    walls=[]
    for axis in range(3):
        a=low.copy();b=high.copy();b[axis]=low[axis]+8;walls.append(box(a,b,'voidwall'))
        a=low.copy();b=high.copy();a[axis]=high[axis]-8;walls.append(box(a,b,'voidwall'))
    palette=(scene/'id1/gfx/palette.lmp').read_bytes();tile=Image.new('P',(16,16),255);tile.putpalette(palette)
    (scene/'census.wad').write_bytes(wad([('voidwall',0x43,miptex('voidwall',tile))]))
    # the hand timings: the hands stage's report (BUILD-SEYDA-BSP-CARRIER-48)
    from hand_metadata import scene_timings
    timings=scene_timings(scene)
    # Actual exterior customs door destination supplies the default entry too.
    entrance=next(r for r in cell['entrances'] if r['id'].casefold()=='chargen customs door')
    spawn=[v*.25 for v in entrance['destination']['position']];spawn[2]+=16.875
    heading=(90-math.degrees(entrance['destination']['rotation_radians'][2]))%360
    source='{\n"classname" "worldspawn"\n"wad" "census.wad"\n"message" "Census and Excise Office"\n'+timings+'\n'+'\n'.join(walls)+'\n}\n'
    source+='{\n"classname" "info_player_start"\n"origin" "'+' '.join(map(str,spawn))+'"\n"angle" "'+str(heading)+'"\n}\n'
    (scene/'census.map').write_text(source)
    for exe,args in [(qbsp,['-nopercent','census.map']),(vis,vis_args('census.bsp',resolve_jobs(jobs),vis_mode)),(light,light_args('-minlight','24','census.bsp'))]:
        subprocess.run([str(Path(exe).resolve()),*args],cwd=scene,check=True)
    base=scene/'census-base.bsp';(scene/'census.bsp').rename(base);rebuild_world_hull(base,scene/'census.map',qbsp)
    faces=room_item_faces('census')
    with items_share_models(taken):
        with items_keep_small_faces(faces) as kept_faces:
            report=append_meshes(base,scene/'census.bsp',parts,scene/'id1/gfx/palette.lmp',centre=(0,0),lighting=lighting,
                                 jobs=jobs,retain_dressing=interior_dressing())
    # every entry's model is an office model that kept its faces (a renamed mesh must not pass unnoticed)
    if set(faces)-set(kept_faces):
        raise ValueError('room-item-faces: no census model for '+', '.join(sorted(set(faces)-set(kept_faces))))
    report['room_item_faces']=kept_faces
    netnames=names.result();entities=[]
    for identifier,stem,role in CENSUS_ACTORS:
        ref=next(r for r in cell['refs'] if r['id'].casefold()==identifier and not r.get('deleted'))
        model='progs/np_'+stem+'.mdl'
        if not (scene/'id1'/model).is_file():raise ValueError('Run intro actor conversion first: '+model)
        fields={'classname':'aw_npc','model':model,'origin':' '.join(f'{v*.25:.5f}' for v in ref['position']),
                'angles':f"0 {-math.degrees(ref['rotation_radians'][2]):.5f} 0",'netname':netnames[identifier],
                'aw_intro_role':role,'aw_ref':ref['number'],'aw_idle_step':'.15','aw_walk_step':'.125',
                # the record id: the dialogue table finds the speaker by it (CENSUS-INTRO-SCRIPTS-62: Sellus Gravius
                # talks through the dialogue window with his own greetings, topics and result scripts)
                'aw_source_id':identifier}
        entities.append('{\n'+'\n'.join(quote(k)+' '+quote(v) for k,v in fields.items())+'\n}')
    b=lumps((scene/'census.bsp').read_bytes());b[0]=b[0].rstrip(b'\0')+('\n'+'\n'.join(entities)+'\n\0').encode('cp1252')
    target.write_bytes(pack_lumps(b));shutil.copyfile(target,scene/'census.bsp')
    prepare_doors(data_files,scene,sources=doors.result())
    counts=check_model_room(target)
    report.update(cell=cell['name'],master_sha256=cell['master_sha256'],omitted=omitted+report['omitted'],spawn=spawn,
                  engine_models=counts['models'],engine_model_limit=CENSUS_MODEL_LIMIT,items=len(taken))
    (scene/'census-conversion.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('data-files','scene','qbsp','vis','light'):p.add_argument('--'+n,type=Path,required=True)
    add_jobs(p);add_vis_option(p);add_dressing_option(p);a=p.parse_args();apply_dressing_option(a)
    import build_profile;build_profile.instrument('census')
    prepare(a.data_files,a.scene,a.qbsp,a.vis,a.light,a.jobs,a.vis_mode)
