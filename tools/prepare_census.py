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
    The network model index is a byte, so the engine holds 256 models (BUILD-BUDGET-ENGINE-LIMITS-35); with an own
    lit model each, the 124 items took the office to 284. The shared bake is the first equal item's lightmap.
    Scoped to this converter so no other map's placements change."""
    import prepare_mesh_bsp
    original=prepare_mesh_bsp._instance_key
    def key(ref,lighting,unlit=False):
        return original(ref,lighting,unlit or ref['number'] in numbers)
    prepare_mesh_bsp._instance_key=key
    try:yield
    finally:prepare_mesh_bsp._instance_key=original


# The engine's MAX_MODELS is 256 (byte model index); the office keeps a margin under it.
CENSUS_MODEL_LIMIT = 240


# Model slots the map does not name: slot 0, the worldspawn precaches (player, view model) and the engine's
# run-time slots. tests/test_map_engine_limits.py keeps it equal to map_engine_limits' count; the engine source
# is not read here, so an engine edit does not re-key this stage.
FIXED_MODEL_SLOTS = 20


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
        raise ValueError('%s: %d models, the office keeps under %d (the engine holds 256: MAX_MODELS)'%(
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
    names=Background(actor_names,child_ci(data_files,'Morrowind.esm'),[i for i,_,_ in CENSUS_ACTORS],jobs=jobs)
    from ui_palette import reserve
    reserve(data_files,scene/'id1')
    target=scene/'id1/maps/census.bsp'
    if target.exists():raise ValueError('Census map already exists; use a fresh scene')
    cell=read_interior(child_ci(data_files,'Morrowind.esm'),'Seyda Neen, Census and Excise Office')
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
    with items_share_models(taken):
        report=append_meshes(base,scene/'census.bsp',parts,scene/'id1/gfx/palette.lmp',centre=(0,0),lighting=lighting,jobs=jobs,
                             retain_dressing=interior_dressing())
    netnames=names.result();entities=[]
    for identifier,stem,role in CENSUS_ACTORS:
        ref=next(r for r in cell['refs'] if r['id'].casefold()==identifier and not r.get('deleted'))
        model='progs/np_'+stem+'.mdl'
        if not (scene/'id1'/model).is_file():raise ValueError('Run intro actor conversion first: '+model)
        fields={'classname':'aw_npc','model':model,'origin':' '.join(f'{v*.25:.5f}' for v in ref['position']),
                'angles':f"0 {-math.degrees(ref['rotation_radians'][2]):.5f} 0",'netname':netnames[identifier],
                'aw_intro_role':role,'aw_ref':ref['number'],'aw_idle_step':'.15','aw_walk_step':'.125'}
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
