#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Rebuild a measured region from the complete owned Balmora conversion cache.

Uses the same terrain/scenery/collision path as prepare_balmora. Cache inputs are
read-only; all generated maps, WADs, logs and collision cache go to a new folder.
This invokes the explicitly configured installed map tools when called.
"""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

from balmora_regions import select_references, collision_coverage
from prepare_balmora import terrain_map, terrain_at, entity
from prepare_mesh_bsp import append_meshes
from player_hull import rebuild_world_hull, lumps, pack_lumps
from compact_bsp import entities
from bound_balmora_visuals import bound_visuals
from share_bsp_geometry import share_geometry
from deduplicate_bsp import deduplicate
from check_geometry_render_inputs import compare_render_inputs, compare_sample_sharing
from vis_options import light_args, vis_args


def rebuild_cached_region(cache, source_runtime, palette, entry, settings, out, ericw_bin, threads=None, vis_mode='fast'):
    from build_jobs import resolve_jobs
    threads=resolve_jobs(threads)  # the builder's --jobs; None: the stage budget
    cache=Path(cache);source_runtime=Path(source_runtime);palette=Path(palette);out=Path(out)
    out.mkdir(parents=True,exist_ok=False)
    index_path=cache/'scenery/scenery-index.json'
    index=json.loads(index_path.read_text())
    grids_path=cache/'audit/terrain-source.json'
    grids={tuple(g['cell']):g for g in json.loads(grids_path.read_text())}
    original=source_runtime.read_bytes()
    original_entities=entities(lumps(original)[0])
    timings='\n'.join(re.findall(r'"aw_(?:hand_[^"\n]+|eye_height)" "[^"\n]+"',
                                lumps(original)[0].decode('cp1252')))
    spawn=[sum(entry['core'][j][i] for j in (0,1))/2 for i in range(2)]
    spawn.append(terrain_at(grids,settings,*spawn)[0]+40)
    selected=select_references(index,entry,settings)
    if len(selected)+32>settings['entity_budget']:
        raise ValueError('New region exceeds entity budget')
    # Original region WAD contains the complete shared terrain material set.
    wad=cache/'bm000/terrain.wad'
    shutil.copyfile(wad,out/'terrain.wad')
    (out/'terrain.map').write_text(terrain_map(entry,grids,settings,spawn,timings),encoding='ascii')
    binary=Path(ericw_bin)
    def exe(name):
        path=binary/name
        return path if path.is_file() else binary/(name+'.exe')
    with (out/'compile.log').open('w') as log:
        for name,args in (('qbsp',['-nopercent','terrain.map']),
                          ('vis',vis_args('terrain.bsp',threads,vis_mode)),
                          ('light',light_args('-minlight','24','terrain.bsp'))):
            subprocess.run([str(exe(name)),*args],cwd=out,stdout=log,stderr=subprocess.STDOUT,check=True)
    base=out/'base.bsp';shutil.copyfile(out/'terrain.bsp',base)
    rebuild_world_hull(base,out/'terrain.map',exe('qbsp'))
    mesh=append_meshes(base,out/'scene.bsp',cache/'scenery',palette,
                       centre=settings['centre'],jobs=threads,references=selected,
                       retain_dressing=True,collision_bounds=collision_coverage(entry,settings),
                       collision_compiler=exe('qbsp'),collision_cache=out/'collision-cache',
                       map_identity=entry['name'],cell_identity=','.join(map(str,entry['cell'])) if entry.get('cell') else None,subcell_identity=entry['name'] if entry.get('subcell') is not None else None)
    if mesh['unique_models']>settings['model_budget']:
        raise ValueError('New region exceeds model budget')
    data=lumps((out/'scene.bsp').read_bytes())
    # Existing exterior maps seed the entire stable NPC population. Keep those
    # exact gameplay records; static scene placements were rebuilt above.
    actors=[e for e in original_entities if e.get('classname')=='aw_npc']
    text=data[0].decode('cp1252').rstrip('\0\n')
    data[0]=(text+'\n'+'\n'.join(entity(e) for e in actors)+'\n\0').encode('cp1252')
    bounded,coverage_report=bound_visuals(pack_lumps(data),entry['coverage'])
    shared,sharing=share_geometry(bounded)
    geometry_oracle=compare_render_inputs(bounded,shared)
    final,deduplication=deduplicate(shared)
    sample_oracle=compare_sample_sharing(shared,final)
    target=out/(entry['name']+'.bsp');target.write_bytes(final)
    inputs={'scenery_index':index_path,'terrain_source':grids_path,'terrain_wad':wad,
            'source_runtime':source_runtime,'palette':palette,'scenery_archive':cache/'scenery/scenery.mwpak'}
    report={'region':entry,'candidate_path':str(target),'candidate_sha256':hashlib.sha256(final).hexdigest(),
            'inputs':{k:{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for k,p in inputs.items()},
            'selected_references':selected,'stable_npc_records':len(actors),'mesh':mesh,
            'coverage':coverage_report,'geometry_sharing':sharing,'geometry_oracle':geometry_oracle,
            'sample_sharing':deduplication,'sample_oracle':sample_oracle,
            'acceptance':'rebuilt from complete owned source cache; final heap/contact/target gates pending'}
    (out/'repair.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report
