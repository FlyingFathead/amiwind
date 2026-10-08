#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Index original voice INFO records locally; never ship the generated table."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from mwad.npc import load_master,outfit
from mwad.dialogue_lookup import build_lookup
from mwad.paths import ensure_external
from known_inputs import input_sha256

def prepare(data,out):
    data=ensure_external(data,'owned game data');out=ensure_external(out,'private dialogue lookup')
    if out.exists():raise ValueError('Output already exists')
    master=data/'Morrowind.esm';kinds,_,topics=load_master(master)
    result=build_lookup(topics,[outfit(kinds,a) for a in ('fargoth','imperial guard')])
    result['master_sha256']=input_sha256(master)
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('x') as f:json.dump(result,f,separators=(',',':'));f.write('\n')
    return {'responses':len(result['responses']), 'bytes':out.stat().st_size,
            'static_candidates':{a:{t:len(v) for t,v in d['topics'].items()} for a,d in result['actors'].items()}}
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-files',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();print(json.dumps(prepare(a.data_files,a.out),indent=2))
