#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Upgrade staged Balmora maps from owned cached source before final build gates.

Only the three measured replacement cores invoke installed map compilers. Other
regions keep their terrain/PVS/collision and remove whole off-apron mesh faces.
All candidates are prepared before replacing any input; failed commits roll back.
This receipt is conversion evidence, never a target playtest or heap acceptance.
"""
import hashlib
import json
from pathlib import Path
import os
import shutil

from balmora_regions import config, regions, audit_coverage, owner
from bound_balmora_visuals import bound_visuals
from rebuild_balmora_region import rebuild_cached_region


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def repair(maps_dir, *, cache, palette, ericw_bin, work_dir, threads=None, vis_mode='fast'):
    # threads: the builder's --jobs (None: the stage budget, resolve_jobs).
    from build_jobs import resolve_jobs
    threads=resolve_jobs(threads)
    from vis_options import vis_kwargs
    maps_dir=Path(maps_dir);cache=Path(cache);palette=Path(palette)
    work=Path(work_dir);work.mkdir(parents=True,exist_ok=True)
    receipt=work/'balmora-repair.json'
    candidates=work/'candidates';candidates.mkdir(exist_ok=False)
    backups=work/'originals';backups.mkdir()
    settings=config();entries=regions(settings)
    metadata=maps_dir.parent/'balmora-regions.txt'
    original_metadata=metadata.read_text().splitlines()
    header=original_metadata[0].split()
    if len(header)!=12 or header[:2]!=['AWBR1','64']:
        raise ValueError('Expected verified 64-region Balmora directory')
    if float(header[2])!=settings['hysteresis'] or float(header[3])!=settings['draw_distance']:
        raise ValueError('Balmora runtime overlap policy changed')
    if {line.split()[0] for line in original_metadata[1:] if line.strip()}!={e['name'] for e in entries}:
        raise ValueError('Balmora source directory names differ')
    index_path=cache/'scenery/scenery-index.json'
    coverage=audit_coverage(json.loads(index_path.read_text()),entries,settings)
    source_names={'bm000':'bm000','bm001':'bm027','bm027':'bm027'}
    input_paths=[maps_dir/(e['name']+'.bsp') for e in entries]+[maps_dir/'balmora.bsp',metadata]
    for p in input_paths:shutil.copyfile(p,backups/p.name)
    input_hashes={p.name:sha(p) for p in input_paths}
    outputs=[]
    report={'status':'preparing','source_hashes':input_hashes,'coverage':coverage,
            'settings':settings,'regions':entries,'maps':outputs,
            'acceptance':'final heap, actor contact and target playtest gates pending'}
    def save():receipt.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    save()
    committed=[]
    try:
        for entry in entries:
            name=entry['name'];target=candidates/(name+'.bsp')
            if name in source_names:
                detail=rebuild_cached_region(cache,backups/(source_names[name]+'.bsp'),palette,
                            entry,settings,work/('rebuild-'+name),ericw_bin,threads=threads,**vis_kwargs(vis_mode))
                shutil.copyfile(detail['candidate_path'],target)
                proof={'rebuilt':True,'receipt':str(work/('rebuild-'+name)/'repair.json')}
            else:
                raw,proof=bound_visuals((backups/(name+'.bsp')).read_bytes(),entry['coverage'])
                target.write_bytes(raw)
            outputs.append({'name':name,'sha256':sha(target),'proof':proof})
            print('Balmora staged repair:',name,flush=True)
        arrival=[float(v) for v in header[4:7]]
        default=entries[owner(arrival,entries)]['name']
        shutil.copyfile(candidates/(default+'.bsp'),candidates/'balmora.bsp')
        rows=[original_metadata[0]]
        for e in entries:
            rows.append(e['name']+' '+' '.join(map(str,[*e['core'][0],*e['core'][1],*e['coverage'][0],*e['coverage'][1]])))
        (candidates/metadata.name).write_text('\n'.join(rows)+'\n',encoding='ascii')
        if any(sha(p)!=input_hashes[p.name] for p in input_paths):
            raise ValueError('Staged Balmora source changed during repair')
        for dest in input_paths:
            temp=dest.with_name(dest.name+'.repair-tmp')
            shutil.copyfile(candidates/dest.name,temp)
            os.replace(temp,dest);committed.append(dest)
        report.update(status='complete',default_region=default,
                      output_hashes={p.name:sha(p) for p in input_paths})
        save();return report
    except BaseException as error:
        for dest in reversed(committed):shutil.copyfile(backups/dest.name,dest)
        report.update(status='failed',error=f'{type(error).__name__}: {error}',rolled_back=bool(committed))
        save();raise
