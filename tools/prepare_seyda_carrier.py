#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Prepare only a fresh Seyda exterior entity carrier for the CHIM town adapter."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from mwad.paths import copy_tree, ensure_external, resolve_data_files, child_ci
from mwad.npc import load_master
from mwad.interior import read_interior
from player_hull import lumps
from hand_metadata import hand_fields, stamp
from prepare_hand_catalog import runtime_palette
from prepare_intro import populate_intro_actors
from prepare_area import populate
from prepare_opening_refs import prepare as bind_opening
from ui_palette import reserved_palette, reserve

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def file_digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def validate_inputs(scene,hand_report,catalog,source_bsp=None):
    palette=(scene/'id1/gfx/palette.lmp').read_bytes()
    if len(palette)!=768:
        raise ValueError('Carrier conversion palette must contain exactly 768 bytes')
    if hand_report.get('clips')!=catalog.get('clips'):
        raise ValueError('Carrier hand timing differs from the selected current catalogue')
    fields=hand_fields(hand_report)
    raw=source_bsp
    if raw is None:
        raw=(scene/'id1/maps/seyda.bsp').read_bytes()
        if (scene/'seyda.bsp').read_bytes()!=raw:
            raise ValueError('Source carrier BSP copies differ')
    elif any((scene/name).exists() for name in ('seyda.bsp','id1/maps/seyda.bsp')):
        raise ValueError('Direct source carrier requires fresh alias input without a BSP')
    entities=lumps(raw)[0]
    if re.search(rb'"aw_intro_role"\s+"',entities):
        raise ValueError('Source carrier already has intro actors')
    if any((scene/'id1/maps'/(name+'.bsp')).exists() for name in ('prison','census')):
        raise ValueError('Use the fresh exterior source, not an inherited interior bundle')
    # Validates worldspawn and duplicate hand fields before cloning or baking.
    stamp(raw,fields)
    return palette,raw,fields

def prepare(data_files,scene,out,hand_report_path,hand_catalog_report_path,jobs=1,ffmpeg='ffmpeg',
            scenery=None,opening_source=None):
    data=resolve_data_files(data_files)
    scene=ensure_external(scene,'fresh exterior source')
    out=ensure_external(out,'fresh carrier output')
    if out.exists() or scene==out or scene in out.parents or out in scene.parents:
        raise ValueError('Choose a separate new carrier output')
    hand_raw=Path(hand_report_path).read_bytes()
    catalog_raw=Path(hand_catalog_report_path).read_bytes()
    hand_report=json.loads(hand_raw);catalog=json.loads(catalog_raw)
    source_record=None
    source_bsp=None
    if scenery is not None:
        from prepare_seyda_source import seed
        from prepare_opening_refs import BARREL, opening_references
        _,wanted,_=opening_references(data)
        barrel=next(r for r in wanted if r['id'].casefold()==BARREL)
        source_bsp,source_record=seed(scene,scenery,barrel,opening_source)
    elif opening_source is not None:
        raise ValueError('Opening source is only valid with --scenery')
    palette,source_bsp,fields=validate_inputs(scene,hand_report,catalog,source_bsp)
    ui,_=reserved_palette(data,palette)
    final=runtime_palette(data,scene/'id1/gfx/palette.lmp')
    if digest(ui)!=catalog.get('scene_palette_sha256') or digest(final)!=catalog.get('palette_sha256'):
        raise ValueError('Carrier conversion/UI/runtime palette stages differ from the selected catalogue')
    original_inputs={name:file_digest(child_ci(data,name)) for name in ('Morrowind.esm','Morrowind.bsa')}
    kinds,cells,_=load_master(child_ci(data,'Morrowind.esm'))
    prison=read_interior(child_ci(data,'Morrowind.esm'),'Imperial Prison Ship')
    copy_tree(scene,out)
    (out/'id1/maps').mkdir(parents=True,exist_ok=True)
    if source_record is not None:
        (out/'source-entities.json').write_text(json.dumps(source_record,indent=2)+'\n',encoding='utf-8',newline='\n')
    timed=stamp(source_bsp,fields)
    (out/'id1/maps/seyda.bsp').write_bytes(timed);(out/'seyda.bsp').write_bytes(timed)
    actors=populate_intro_actors(data,out,kinds,cells,prison,palette,jobs,
                                 map_names=('seyda',),include_prototypes=False)
    ui_receipt=reserve(data,out/'id1')
    if (out/'id1/gfx/palette.lmp').read_bytes()!=ui:
        raise ValueError('UI reservation differs from the preflight palette')
    area=populate(data,out,rooms={},reports=[],ffmpeg=ffmpeg,jobs=jobs,
                  include_exterior=True,doors=False,report_name='carrier-exterior-residents.json')
    opening=bind_opening(data,out) if source_record is None else bind_opening(data,out,allow_append=False)
    record={'scope':'source entity carrier only; no interiors, movie, native or package acceptance',
            'source_only':source_record is not None,
            'source_entities_sha256':file_digest(out/'source-entities.json') if source_record is not None else None,
            'source_bsp_sha256':digest(source_bsp),'original_inputs_sha256':original_inputs,
            'producer_sources_sha256':{name:file_digest(Path(__file__).with_name(name)) for name in
                ('prepare_intro.py','prepare_hands.py','prepare_seyda_carrier.py')},
            'source_hand_report_sha256':digest(hand_raw),
            'selected_hand_catalog_report_sha256':digest(catalog_raw),
            'palette_sha256':{'conversion':digest(palette),'ui':digest(ui),'runtime':digest(final)},
            'hand_fields':fields,'intro_actors':actors,'ui_reservation':ui_receipt,
            'exterior_residents':area,'opening_refs':opening,
            'carrier_bsp_sha256':digest((out/'id1/maps/seyda.bsp').read_bytes()),
            'independent_interior_or_movie_conversion':False,
            'regional_bsp_compilation':False}
    (out/'seyda-carrier.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8',newline='\n')
    return record

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('data-files','scene','out','hand-report','hand-catalog-report'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--scenery',type=Path,help='Fresh scenery source: create a non-runtime metadata carrier, not a compiled town BSP')
    p.add_argument('--opening-source',type=Path,help='Canonical CHIM opening-barrel-source when absent from normal scenery')
    p.add_argument('--jobs',type=int,default=1)
    p.add_argument('--ffmpeg',default='ffmpeg')
    a=p.parse_args()
    if a.jobs<1:p.error('--jobs must be positive')
    print(json.dumps(prepare(a.data_files,a.scene,a.out,a.hand_report,a.hand_catalog_report,a.jobs,a.ffmpeg,a.scenery,a.opening_source),indent=2))

if __name__=='__main__':
    main()
