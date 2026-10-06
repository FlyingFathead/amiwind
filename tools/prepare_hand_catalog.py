#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Generate owned first-person hands and matching torch arms for playable races."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from mwad.npc import first
from mwad.paths import child_ci,ensure_external
from prepare_hands import bake_appearance
from prepare_torch import TorchSource,prepare as prepare_torch

RECORD_SIZE=196

def model_paths(race,female):
    slug=race.casefold().replace(' ','_')
    if not re.fullmatch('[a-z0-9_]+',slug) or len(slug)>35:
        raise ValueError('Race ID cannot form a portable hand-model path')
    stem='progs/hands/'+slug+('_f' if female else '_m')
    return stem+'.mdl',stem+'_t.mdl'

def pack_catalog(entries):
    if not 1<=len(entries)<=32:raise ValueError('Hand catalogue count outside bounds')
    output=bytearray(struct.pack('>4sHH',b'AWH1',len(entries),RECORD_SIZE));seen=set()
    for entry in entries:
        race=entry['race'];female=entry['female'];paths=model_paths(race,female)
        if type(female) is not bool or (race,female) in seen:raise ValueError('Duplicate or invalid hand appearance')
        seen.add((race,female));raw=race.encode('ascii')
        if not raw or len(raw)>63 or race!=race.casefold():raise ValueError('Invalid race ID')
        if (entry['hand_model'],entry['torch_model'])!=paths:raise ValueError('Unexpected appearance model path')
        output.extend(raw.ljust(64,b'\0')+bytes((female,0,0,0)))
        for path in paths:
            raw=path.encode('ascii')
            if len(raw)>63:raise ValueError('Hand model path too long')
            output.extend(raw.ljust(64,b'\0'))
    return bytes(output)

def prepare(data_files,palette_path,out,budget=320,topology='reduced'):
    data_files=ensure_external(data_files,'owned data')
    palette_path=ensure_external(palette_path,'palette');out=ensure_external(out,'hand catalogue output')
    if out.exists():raise ValueError('Hand catalogue output must be fresh')
    palette=palette_path.read_bytes()
    if len(palette)!=768:raise ValueError('Expected a 256-colour palette')
    source=TorchSource(data_files);kinds=source.kinds;assets=source.assets
    races=sorted(name for name,record in kinds['RACE'].items()
                 if len(first(record,'RADT'))>=20 and struct.unpack_from('<I',first(record,'RADT'),len(first(record,'RADT'))-4)[0]&1)
    if not races or len(races)*2>32:raise ValueError('Playable race count outside runtime catalogue bounds')
    if len({model_paths(r,False)[0] for r in races})!=len(races):raise ValueError('Race model names collide')
    out.mkdir(parents=True);(out/'progs/hands').mkdir(parents=True);(out/'gfx').mkdir();(out/'reports').mkdir()
    entries=[];common_torch=None;common_clips=None
    # Partial output is retained on failure; an AWH1 catalogue appears only
    # after every race/sex pair and matching torch conversion has succeeded.
    for race in races:
        for female in (False,True):
            hand,torch=model_paths(race,female)
            raw,report=bake_appearance(assets,kinds,palette,race,female,budget,topology)
            if common_clips is None:common_clips=report['clips']
            elif report['clips']!=common_clips:raise ValueError('Hand timing differs between race models')
            (out/hand).write_bytes(raw);report['model']=hand
            stage=out/'reports'/(Path(hand).stem+'-torch');(stage/'gfx').mkdir(parents=True)
            (stage/'gfx/palette.lmp').write_bytes(palette)
            torch_report=prepare_torch(data_files,stage,race=race,female=female,topology=topology,source=source)
            torch_raw=(stage/'progs/v_torch.mdl').read_bytes();meta=(stage/'gfx/torch.awt').read_bytes()
            if common_torch is None:common_torch=meta
            elif meta!=common_torch:raise ValueError('Torch emitter metadata differs between race models')
            (out/torch).write_bytes(torch_raw)
            (out/'reports'/(Path(hand).stem+'.json')).write_text(json.dumps({'hands':report,'torch':torch_report},indent=2)+'\n')
            entries.append({'race':race,'female':female,'hand_model':hand,'torch_model':torch,
                            'hand_sha256':hashlib.sha256(raw).hexdigest(),'torch_sha256':hashlib.sha256(torch_raw).hexdigest(),
                            'hand_bytes':len(raw),'torch_bytes':len(torch_raw)})
    (out/'gfx/hand-torch.awt').write_bytes(common_torch)
    catalog=pack_catalog(entries);(out/'gfx/hand-models.awh').write_bytes(catalog)
    result={'format':'AWH1','budget':budget,'topology':topology,'entries':entries,'clips':common_clips,
            'catalog_sha256':hashlib.sha256(catalog).hexdigest(),'torch_metadata_sha256':hashlib.sha256(common_torch).hexdigest(),
            'torch_metadata':'gfx/hand-torch.awt',
            'scope':'Owned race/sex 3D hand and torch models. Install matching models, catalogue and shared torch metadata together; legacy v_nord remains available.'}
    (out/'hand-catalog-report.json').write_text(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-files',type=Path,required=True);p.add_argument('--palette',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--budget',type=int,choices=(320,480),default=320)
    p.add_argument('--topology',choices=('source','reduced'),default='reduced',help='Preserve authored topology or retain bounded legacy reduction')
    a=p.parse_args();print(json.dumps(prepare(a.data_files,a.palette,a.out,a.budget,a.topology),indent=2))
