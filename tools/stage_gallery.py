#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Stage successful private gallery models and existing bounded greetings.

Run after prepare_gallery.py and audit_gallery_budgets.py. Failed records stay
in the catalogue; this staging step does not certify visual acceptance.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
from audit_gallery_budgets import write_allowances
from check_actor_ground import entities
from mwad.paths import ensure_external


def _voiced_actors(path):
    """Worker: the voiced actor entities of one map, in file order."""
    return [e for e in entities(Path(path).read_bytes())
            if e.get('classname')=='aw_npc' and e.get('aw_source_id') and e.get('aw_voice')]


def stage(gallery, id1):
    gallery=ensure_external(gallery,'converted gallery');id1=ensure_external(id1,'private game data')
    audit=json.loads((gallery/'gallery-audit.json').read_text())
    dest=id1/'gallery';dest.mkdir(exist_ok=True)
    copied=0
    for key,result in audit['models'].items():
        if result['status']!='ready':continue
        model=gallery/'gallery'/(key+'.mdl')
        if hashlib.sha256(model.read_bytes()).hexdigest()!=result['sha256']:
            raise ValueError('Gallery receipt mismatch: '+key)
        for name in (key+'.mdl','f'+key[1:]+'.mdl'):
            shutil.copyfile(gallery/'gallery'/name,dest/name);copied+=1
    for name in ('catalog.txt','inspection.tsv','poses.txt'):
        shutil.copyfile(gallery/'gallery'/name,dest/name)
    report=write_allowances(gallery/'gallery',audit['models'],audit['entries'],id1/'model-budgets.txt')
    voices={}
    # Every staged map is read (the world maps too): in the worker pool, applied
    # in map order so a later map's greeting wins as before.
    from build_parallel import ordered_map
    from build_jobs import resolve_jobs
    paths=sorted((id1/'maps').glob('*.bsp'))
    for found in ordered_map(_voiced_actors,[str(p) for p in paths],max(1,min(resolve_jobs(None),len(paths) or 1))):
        for e in found:
            if not (id1/'sound'/e['aw_voice']).is_file():continue
            line=e.get('aw_line','').replace('\n',' ').replace('\t',' ')
            voices[e['aw_source_id'].casefold()]=(e['aw_voice'],e.get('aw_greet_duration','8'),line)
    (dest/'voices.txt').write_text('AWGV1\n'+''.join('\t'.join([key,*value])+'\n' for key,value in sorted(voices.items())),encoding='cp1252')
    return dict(model_files=copied,greetings=len(voices),exceptions=len(report['exceptions']),unresolved=len(report['unresolved']))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--gallery',type=Path,required=True);p.add_argument('--id1',type=Path,required=True)
    a=p.parse_args();print(json.dumps(stage(a.gallery,a.id1),indent=2))
