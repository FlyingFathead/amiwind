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
from prepare_hand_normals import normal_table,rewrite as rewrite_normals

RECORD_SIZE=196
# The armed first-person stances (PLAYER-GEAR-VISUAL-59): one arms model per stance and appearance, beside the bare
# hands, and one Weapon Bone tag table for all appearances (engine/aga/src/aw_hand_models.h, gfx/hand-weapons.aww).
# The order is the engine's stance index (0 one-handed, 1 two-handed close, 2 two-handed wide).
WEAPON_STANCES=('1h','2c','2w')
# FIRST-PERSON-WEAPONS-56 (v0.0.61): the Weapon Bone table also holds the ranged stances (engine stance 3 bow, 4 crossbow,
# 5 thrown). They have no baked arms: the arms from parts (tools/prepare_player_fp_parts.py) pose them; with the baked
# arms (aw_hand_parts 0) those weapons keep the bare hands. An older catalogue with the three melee stances still installs.
WEAPON_TAG_STANCES=WEAPON_STANCES+('bow','xb','1t')
WEAPON_FRAMES=28
WEAPON_METADATA='gfx/hand-weapons.aww'

def stance_path(race,female,stance):
    if stance not in WEAPON_STANCES:raise ValueError('Unknown armed stance '+str(stance))
    return model_paths(race,female)[0][:-4]+'_'+stance+'.mdl'

def stance_weapon_tags(skeleton,stance):
    """The Weapon Bone (origin, angles) per frame of STANCE's arms, in the space prepare_hands bakes the arms in
    (the stance's first Camera, then the view axes): npc_items.view_tags, as the block view does for the shield."""
    import numpy as np
    from prepare_hands import sample_clips
    from npc_items import view_tags
    times,_=sample_clips(skeleton.events,stance)
    camera=skeleton.pose(float(times[0]))('Camera')[3,:3]*.25
    tags=np.array(view_tags(skeleton,times,camera,{'weapon':True,'shield':None}))[:,:6]
    if tags.shape!=(WEAPON_FRAMES,6):raise ValueError('Armed stance frame count differs from the hand contract')
    return tags

def weapon_view_tags(source):
    """One Weapon Bone table for every appearance (the skeleton, base_anim.1st.nif, is shared, as for the block
    view): per stance of WEAPON_TAG_STANCES, 28 frames of six values."""
    from npc_geometry import Skeleton
    skeleton=Skeleton(source.assets,'meshes/base_anim.1st.nif')
    return [stance_weapon_tags(skeleton,stance) for stance in WEAPON_TAG_STANCES]

def pack_weapon_tags(tags):
    """AWW1: magic, 0, stance count, 0, frames (28), then per stance and frame six big-endian 16.16 values."""
    import numpy as np
    tags=np.asarray(tags,float)
    if (tags.ndim!=3 or not 1<=tags.shape[0]<=len(WEAPON_TAG_STANCES) or tags.shape[1:]!=(WEAPON_FRAMES,6)
            or not np.isfinite(tags).all() or np.max(abs(tags[:,:,:3]))>128 or np.max(abs(tags[:,:,3:]))>720):
        raise ValueError('First-person weapon tags outside runtime bounds')
    raw=bytearray(b'AWW1'+bytes((0,tags.shape[0],0,WEAPON_FRAMES)))
    for value in np.rint(tags*65536).astype(np.int64).reshape(-1):raw.extend(struct.pack('>i',int(value)))
    return bytes(raw)

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

_SOURCES={}


def _torch_source(data_files):
    """One owned-data cache per worker process (and per data folder)."""
    if data_files not in _SOURCES:_SOURCES[data_files]=TorchSource(data_files)
    return _SOURCES[data_files]


def _bake_pair(task):
    """Worker: one race/sex hand and torch model; writes only its own files."""
    data_files,palette,race,female,budget,topology,surface_normals,table,out=task
    out=Path(out);source=_torch_source(data_files)
    hand,torch=model_paths(race,female)
    raw,report=bake_appearance(source.assets,source.kinds,palette,race,female,budget,topology)
    if surface_normals:
        raw,normal_report=rewrite_normals(raw,table)
        report['lighting_normals']=normal_report
        report['sha256']=normal_report['output_sha256']
    (out/hand).write_bytes(raw);report['model']=hand
    stage=out/'reports'/(Path(hand).stem+'-torch');(stage/'gfx').mkdir(parents=True)
    (stage/'gfx/palette.lmp').write_bytes(palette)
    torch_report=prepare_torch(Path(data_files),stage,race=race,female=female,topology=topology,source=source)
    torch_raw=(stage/'progs/v_torch.mdl').read_bytes();meta=(stage/'gfx/torch.awt').read_bytes()
    if surface_normals:
        torch_raw,normal_report=rewrite_normals(torch_raw,table)
        torch_report['lighting_normals']=normal_report
        torch_report['files']['progs/v_torch.mdl']=normal_report['output_sha256']
        # The retained conversion-stage model and its manifest must
        # describe the same final bytes as the installed catalogue.
        (stage/'progs/v_torch.mdl').write_bytes(torch_raw)
    (out/torch).write_bytes(torch_raw)
    # The armed arms (PLAYER-GEAR-VISUAL-59): the same appearance in each weapon stance, loaded only while armed.
    stances={};stance_reports={}
    for stance in WEAPON_STANCES:
        armed,armed_report=bake_appearance(source.assets,source.kinds,palette,race,female,budget,topology,stance=stance)
        if surface_normals:
            armed,normal_report=rewrite_normals(armed,table)
            armed_report['lighting_normals']=normal_report
        if armed_report['frames']!=WEAPON_FRAMES or len(armed)>512*1024:
            raise ValueError('Armed arms outside the hand model contract: '+race+' '+stance)
        path=stance_path(race,female,stance);(out/path).write_bytes(armed);armed_report['model']=path
        stances[stance]={'model':path,'sha256':hashlib.sha256(armed).hexdigest(),'bytes':len(armed),
                         'triangles':armed_report['triangles'],'vertices':armed_report['vertices']}
        stance_reports[stance]=armed_report
    (out/'reports'/(Path(hand).stem+'.json')).write_text(json.dumps({'hands':report,'torch':torch_report,'armed':stance_reports},indent=2)+'\n')
    return report['clips'],meta,{'race':race,'female':female,'hand_model':hand,'torch_model':torch,
                                 'hand_sha256':hashlib.sha256(raw).hexdigest(),'torch_sha256':hashlib.sha256(torch_raw).hexdigest(),
                                 'hand_bytes':len(raw),'torch_bytes':len(torch_raw),'stances':stances}


def prepare(data_files,palette_path,out,budget=320,topology='reduced',normal_mode='auto',runtime=False,jobs=None):
    if topology not in ('source','reduced') or normal_mode not in ('auto','legacy'):
        raise ValueError('Unknown hand topology or lighting-normal mode')
    # Source topology uses encoded surface normals; legacy reduction and an
    # explicit rollback keep their previous index bytes. Geometry is untouched.
    surface_normals=topology=='source' and normal_mode=='auto'
    table=normal_table(Path(__file__).resolve().parents[1]/'engine/aga/src/anorms.h') if surface_normals else None
    data_files=ensure_external(data_files,'owned data')
    palette_path=ensure_external(palette_path,'palette');out=ensure_external(out,'hand catalogue output')
    if out.exists():raise ValueError('Hand catalogue output must be fresh')
    palette=palette_path.read_bytes()
    if len(palette)!=768:raise ValueError('Expected a 256-colour palette')
    scene_palette_sha256=hashlib.sha256(palette).hexdigest()
    if runtime:palette=runtime_palette(data_files,palette_path)
    source=TorchSource(data_files);kinds=source.kinds
    _SOURCES[str(data_files)]=source  # the serial path (one job) reuses it
    races=sorted(name for name,record in kinds['RACE'].items()
                 if len(first(record,'RADT'))>=20 and struct.unpack_from('<I',first(record,'RADT'),len(first(record,'RADT'))-4)[0]&1)
    if not races or len(races)*2>32:raise ValueError('Playable race count outside runtime catalogue bounds')
    if len({model_paths(r,False)[0] for r in races})!=len(races):raise ValueError('Race model names collide')
    out.mkdir(parents=True);(out/'progs/hands').mkdir(parents=True);(out/'gfx').mkdir();(out/'reports').mkdir()
    entries=[];common_torch=None;common_clips=None
    # Partial output is retained on failure; an AWH1 catalogue appears only
    # after every race/sex pair and matching torch conversion has succeeded.
    # Pairs are independent (own model files and conversion stage): up to `jobs`
    # bake at once in the shared pool; the checks below run in pair order.
    from build_parallel import ordered_map
    from build_jobs import resolve_jobs
    pairs=[(race,female) for race in races for female in (False,True)]
    tasks=[(str(data_files),palette,race,female,budget,topology,surface_normals,table,str(out)) for race,female in pairs]
    for clips,meta,entry in ordered_map(_bake_pair,tasks,max(1,min(resolve_jobs(jobs),len(tasks)))):
        if common_clips is None:common_clips=clips
        elif clips!=common_clips:raise ValueError('Hand timing differs between race models')
        if common_torch is None:common_torch=meta
        elif meta!=common_torch:raise ValueError('Torch emitter metadata differs between race models')
        entries.append(entry)
    (out/'gfx/hand-torch.awt').write_bytes(common_torch)
    catalog=pack_catalog(entries);(out/'gfx/hand-models.awh').write_bytes(catalog)
    weapon_tags=weapon_view_tags(source)
    weapon_meta=pack_weapon_tags(weapon_tags);(out/WEAPON_METADATA).write_bytes(weapon_meta)
    weapon_view={'metadata':WEAPON_METADATA,'metadata_sha256':hashlib.sha256(weapon_meta).hexdigest(),
                 'stances':list(WEAPON_TAG_STANCES),'frames':WEAPON_FRAMES,'tags':[[list(map(float,row)) for row in t] for t in weapon_tags]}
    # The normal 3D hand stage also owns its matching first-person block arms.
    # Use these exact final palette bytes, rather than the earlier scene palette.
    from prepare_block_view import prepare as prepare_block_view
    block_palette=out/'reports/block-palette.lmp';block_palette.write_bytes(palette)
    block_view=prepare_block_view(data_files,out,block_palette)
    (out/'reports/block-view.json').write_text(json.dumps(block_view,indent=2)+'\n',encoding='utf-8',newline='\n')
    result={'format':'AWH1','budget':budget,'topology':topology,'normal_mode':'surface' if surface_normals else 'legacy','entries':entries,'clips':common_clips,
            'catalog_sha256':hashlib.sha256(catalog).hexdigest(),'torch_metadata_sha256':hashlib.sha256(common_torch).hexdigest(),
            'torch_metadata':'gfx/hand-torch.awt',
            'palette_sha256':hashlib.sha256(palette).hexdigest(),'scene_palette_sha256':scene_palette_sha256,
            'runtime_palette':bool(runtime),'block_view':block_view,'weapon_view':weapon_view,
            'scope':'Owned race/sex 3D hand and torch models. Install matching models, catalogue and shared torch metadata together; legacy v_nord remains available.'}
    (out/'hand-catalog-report.json').write_text(json.dumps(result,indent=2)+'\n');return result

def runtime_palette(data_files,palette_path):
    """The palette the image step ends with, derived from the scene palette.

    The image step first reserves the original status-bar colours
    (ui_palette.reserve; a scene palette with its UI receipt already has them)
    and then, on the default owned-sky path, applies the sky colour bank
    (prepare_shared_sky_assets -> sky_palette_overlay). The catalogue is
    converted against those final bytes and installed after the sky step, so
    no remap touches it; install() refuses any other palette
    (BUILD-HANDS-NOT-BUILT-32).
    """
    from ui_palette import reserved_palette
    from sky_palette_overlay import EXPECTED_PALETTE,banked_palette,approved
    from ui_palette import legacy_bank_or_none
    palette_path=Path(palette_path);raw=palette_path.read_bytes()
    marker=palette_path.parent/'ui-palette.json'
    if not (marker.is_file() and json.loads(marker.read_text()).get('palette_sha256')==hashlib.sha256(raw).hexdigest()):
        raw=reserved_palette(data_files,raw)[0]
    if hashlib.sha256(raw).hexdigest()==EXPECTED_PALETTE or approved(raw,legacy_bank_or_none(data_files)):raw=banked_palette(raw)
    return raw

def install(catalog,id1):
    """Copy a verified catalogue into an image stage; never overwrite or mix.

    Every model, the AWH1 catalogue and the shared torch metadata must match
    the catalogue report, and the report's palette must be the stage's final
    palette, or nothing is installed (BUILD-HANDS-NOT-BUILT-32).
    """
    catalog=Path(catalog);id1=Path(id1)
    report=json.loads((catalog/'hand-catalog-report.json').read_text())
    if report.get('format')!='AWH1' or not report.get('entries'):raise ValueError('Invalid hand catalogue report')
    palette=hashlib.sha256((id1/'gfx/palette.lmp').read_bytes()).hexdigest()
    if report.get('palette_sha256')!=palette:
        raise ValueError('Hand catalogue was converted with another palette than this image; '
                         'rebuild it from the same scene with --runtime-palette and the default sky')
    files={}
    for entry in report['entries']:
        for kind in ('hand','torch'):
            path=entry[kind+'_model']
            if not re.fullmatch(r'progs/hands/[a-z0-9_]{1,35}_[mf](?:_t)?\.mdl',path) or path in files:
                raise ValueError('Invalid hand catalogue model path')
            files[path]=entry[kind+'_sha256']
    block=report.get('block_view')
    if not isinstance(block,dict) or block.get('palette_sha256')!=palette:
        raise ValueError('Hand catalogue lacks matching block assets; rebuild the 3D hand catalogue')
    expected={(e['race'],e['female'],model_paths(e['race'],e['female'])[0][:-4]+'_b.mdl')
              for e in report['entries']}
    actual=[]
    for entry in block.get('appearances',[]):
        path=entry['model']
        if not re.fullmatch(r'progs/hands/[a-z0-9_]{1,35}_[mf]_b\.mdl',path) or path in files:
            raise ValueError('Invalid block appearance model path')
        actual.append((entry['race'],entry['female'],path));files[path]=entry['sha256']
    if len(actual)!=len(expected) or set(actual)!=expected:
        raise ValueError('Block appearances differ from the hand catalogue')
    files['gfx/block-models.awb']=block['metadata_sha256']
    # The armed arms and their Weapon Bone table (PLAYER-GEAR-VISUAL-59): all of them or none (an older catalogue).
    weapon=report.get('weapon_view')
    if weapon is not None:
        if not isinstance(weapon,dict) or weapon.get('metadata')!=WEAPON_METADATA or \
                list(weapon.get('stances',[])) not in (list(WEAPON_TAG_STANCES),list(WEAPON_STANCES)):
            raise ValueError('Invalid first-person weapon assets in the hand catalogue')
        for entry in report['entries']:
            stances=entry.get('stances') or {}
            if sorted(stances)!=sorted(WEAPON_STANCES):raise ValueError('Hand catalogue entry lacks its armed arms')
            for stance,row in stances.items():
                path=row['model']
                if path!=stance_path(entry['race'],entry['female'],stance) or path in files:
                    raise ValueError('Invalid armed arms model path')
                files[path]=row['sha256']
        files[WEAPON_METADATA]=weapon['metadata_sha256']
    files['gfx/hand-models.awh']=report['catalog_sha256'];files['gfx/hand-torch.awt']=report['torch_metadata_sha256']
    payload={}
    for path,digest in files.items():
        raw=(catalog/path).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=digest:raise ValueError('Hand catalogue file differs from its report: '+path)
        if (id1/path).exists():raise ValueError('Image stage already has '+path)
        payload[path]=raw
    for path,raw in payload.items():
        (id1/path).parent.mkdir(parents=True,exist_ok=True);(id1/path).write_bytes(raw)
    return {'format':'AmiWind hand catalogue staging 1','files':len(payload),'entries':len(report['entries']),
            'palette_sha256':palette,'catalog_sha256':report['catalog_sha256'],
            'torch_metadata_sha256':report['torch_metadata_sha256'],
            'block_appearances':len(actual),'block_metadata_sha256':block['metadata_sha256']}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-files',type=Path,required=True);p.add_argument('--palette',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--budget',type=int,choices=(320,480),default=320)
    p.add_argument('--topology',choices=('source','reduced'),default='reduced',help='Preserve authored topology or retain bounded legacy reduction')
    p.add_argument('--normal-mode',choices=('auto','legacy'),default='auto',help='Source topology uses surface lighting normals; legacy preserves original index bytes')
    p.add_argument('--runtime-palette',action='store_true',help='Convert against the runtime palette the image step makes from this scene palette (builder default)')
    from build_jobs import add_jobs
    add_jobs(p)
    a=p.parse_args();print(json.dumps(prepare(a.data_files,a.palette,a.out,a.budget,a.topology,a.normal_mode,a.runtime_palette,a.jobs),indent=2))
