#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Bake private world-map pixels and indexed journal text from owned base data."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import struct
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from PIL import Image
from mwad.audit import records, subrecords, string
from mwad.paths import ensure_external, child_ci
from build_scratch import scratch_dir

WORLD_UI_FILES = ('map.awm', 'journal.awj', 'entries.dat', 'quests.awq', 'region-names.awn')
NO_NAME = 0xFFFFFFFF  # region-names.awn row without a region or place


def display_name(raw_name, what):
    encoded = raw_name.encode('cp1252')
    if not encoded or len(encoded) >= 64 or any(c < 32 for c in encoded):
        raise ValueError('Invalid original '+what+' display name')
    return encoded


def region_names(raw):
    """Original exterior CELL coordinates -> RGNN ID -> REGN display name,
    plus the cell's own original name (Balmora, Seyda Neen, a camp or ruin):
    the area of interest the player is in. Format ARN2.

    Keep the source names intact. A cell without RGNN has no known region;
    neither a nearby region nor a generated vf map number supplies one.
    """
    regions = {}; cells = {}
    for tag, flags, payload in records(raw):
        if tag not in ('REGN', 'CELL'): continue
        fields = {}
        for key, value in subrecords(payload):
            if tag == 'CELL' and key == 'FRMR': break
            fields[key] = value
        if 'DELE' in fields: continue
        if tag == 'REGN':
            identifier = string(fields['NAME']).casefold()
            encoded = display_name(string(fields.get('FNAM', b'')), 'region')
            if identifier in regions: raise ValueError('Duplicate original region ID')
            regions[identifier] = encoded
        else:
            if len(fields.get('DATA', b'')) != 12: raise ValueError('Invalid CELL header')
            cell_flags, x, y = struct.unpack('<Iii', fields['DATA'])
            if cell_flags & 1: continue
            if (x, y) in cells: raise ValueError('Duplicate exterior cell coordinate')
            place = string(fields.get('NAME', b''))
            cells[x, y] = (string(fields.get('RGNN', b'')).casefold(),
                           display_name(place, 'cell') if place else b'')
    names = sorted(regions); places = sorted({p for r, p in cells.values() if p})
    if len(names) > 1024 or len(places) > 1024 or len(cells) > 65536:
        raise ValueError('Region catalogue exceeds runtime bounds')
    indices = {name: i for i, name in enumerate(names)}
    place_indices = {name: i for i, name in enumerate(places)}
    rows = []
    for (x, y), (identifier, place) in sorted(cells.items()):
        if not identifier and not place: continue
        if identifier and identifier not in indices: raise ValueError('CELL references missing REGN: '+identifier)
        rows.append(struct.pack('<iiII', x, y, indices[identifier] if identifier else NO_NAME,
                                place_indices[place] if place else NO_NAME))
    return (b'ARN2' + struct.pack('<III', len(names), len(places), len(rows))
            + b''.join(regions[name].ljust(64, b'\0') for name in names)
            + b''.join(place.ljust(64, b'\0') for place in places) + b''.join(rows))


def fixed(value,size):
    raw=value.encode('ascii')
    if not raw or len(raw)>=size or any(c<32 for c in raw):raise ValueError('Invalid journal identifier')
    return raw.ljust(size,b'\0')


def journal_assets(raw):
    kind=None;quest=None;entries={}
    for tag,flags,payload in records(raw):
        if tag not in ('DIAL','INFO'):continue
        f=dict(subrecords(payload))
        if tag=='DIAL':
            kind=f.get('DATA',b'\xff')[0];quest=string(f.get('NAME',b'')).lower()
        elif kind==4:
            if len(f.get('DATA',b''))!=12:raise ValueError('Malformed journal INFO data')
            stage=struct.unpack_from('<i',f['DATA'],4)[0]
            text=string(f['NAME']).replace('\r\n','\n').replace('\r','\n')
            body=text.encode('cp1252')+b'\0'
            if len(body)>8192 or b'\0' in body[:-1]:raise ValueError('Journal entry exceeds runtime text bounds')
            key=(quest,stage)
            if key in entries:raise ValueError('Ambiguous journal stage: '+str(key))
            entries[key]=body
    index=bytearray(b'AWJ1'+struct.pack('<I',len(entries)));blob=bytearray()
    for (quest,stage),body in sorted(entries.items()):
        index.extend(fixed(quest,64)+struct.pack('<iII',stage,len(blob),len(body)));blob.extend(body)
    return bytes(index),bytes(blob),len({key[0] for key in entries})


def quest_labels(raw, overrides):
    labels={}
    for tag,flags,payload in records(raw):
        if tag!='DIAL':continue
        f=dict(subrecords(payload))
        if f.get('DATA')!=b'\x04':continue
        source=string(f['NAME']);identifier=source.lower()
        # Base master has no QSTN quest titles. Derived labels are display-only;
        # source identifiers remain the lookup/save identity.
        words=re.sub(r'^[A-Za-z]+[0-9]*(?:_[0-9]+)?_', '', source)
        words=re.sub(r'(?<=[a-z])(?=[A-Z])',' ',words).replace('_',' ')
        label=overrides.get(identifier,words or source)
        labels[identifier]=label
    result=bytearray(b'AWQ1'+struct.pack('<I',len(labels)))
    for identifier,label in sorted(labels.items()):
        value=label.encode('cp1252')
        if len(value)>=96 or b'\0' in value:raise ValueError('Quest label exceeds 95 bytes')
        result.extend(fixed(identifier,64)+value.ljust(96,b'\0'))
    return bytes(result)


def map_asset(report, image, palette):
    if len(palette)!=768:raise ValueError('Expected runtime palette')
    bounds=report['terrain_bounds'];dx=bounds[2]-bounds[0];dy=bounds[3]-bounds[1]
    height=512;width=round(height*dx/dy)
    if not 1<=width<=512: # Keep the longest dimension bounded.
        width=512;height=round(width*dy/dx)
    pal=Image.new('P',(1,1));pal.putpalette(palette)
    background=Image.new('RGBA',image.size,(34,66,84,255));background.alpha_composite(image.convert('RGBA'))
    pixels=background.convert('RGB').resize((width,height),Image.Resampling.BOX).quantize(palette=pal,dither=Image.Dither.NONE).tobytes()
    areas=report['areas']
    raw=bytearray(b'AWM1'+struct.pack('<HH4iII',width,height,*[v*8192 for v in bounds],len(areas),Image.new('RGB',(1,1),(34,66,84)).quantize(palette=pal,dither=Image.Dither.NONE).getpixel((0,0))))
    for area in areas:
        stem={'Balmora':'balmora','Seyda Neen':'seyda'}[area['name']]
        raw.extend(fixed(stem,16)+fixed(area['name'],32)+struct.pack('<3f',*area['centre'],area['scale']))
    raw.extend(pixels)
    return bytes(raw)


def prepare(data_files,survey,scene):
    scene=ensure_external(scene,'private world UI');dest=scene/'id1/world';dest.mkdir(parents=True,exist_ok=True)
    master=child_ci(data_files,'Morrowind.esm').read_bytes()
    if survey is None:
        # Normal image builds need only the terrain overview, not the much
        # broader scenery-density survey. Use the same source terrain routine.
        from mwad.audit import load_esm, BSA
        from npc_geometry import Assets
        from survey_vvardenfell import terrain_arrays
        from world_survey import area_catalogue
        with scratch_dir('amiwind-world-map-') as directory:
            temp=Path(directory);source=load_esm(child_ci(data_files,'Morrowind.esm'))
            bounds,stats,terrain=terrain_arrays(source,temp,Assets(data_files,BSA(child_ci(data_files,'Morrowind.bsa'))))
            report={'master_sha256':source['sha256'],'terrain_bounds':bounds,
                    'areas':area_catalogue(Path(__file__).resolve().parents[1])}
            (temp/'world-survey.json').write_text(json.dumps(report))
            return prepare(data_files,temp,scene)
    report=json.loads((survey/'world-survey.json').read_text())
    if hashlib.sha256(master).hexdigest()!=report['master_sha256']:raise ValueError('Survey/master mismatch')
    palette=(scene/'id1/gfx/palette.lmp').read_bytes()
    index,blob,quests=journal_assets(master)
    labels=quest_labels(master,json.loads((Path(__file__).resolve().parents[1]/'config/journal_titles.json').read_text()))
    worldmap=map_asset(report,Image.open(survey/'terrain.png'),palette)
    for name,raw in [('map.awm',worldmap),('journal.awj',index),('entries.dat',blob),('quests.awq',labels),
                     ('region-names.awn',region_names(master))]:
        (dest/name).write_bytes(raw)
    receipt={'format':'AmiWind world UI 1','master_sha256':report['master_sha256'],
             'palette_sha256':hashlib.sha256(palette).hexdigest(),'journal_quests':quests,
             'journal_entries':(len(index)-8)//76,'journal_text_bytes':len(blob),'map_bytes':len(worldmap),
             'files':{name:hashlib.sha256((dest/name).read_bytes()).hexdigest() for name in WORLD_UI_FILES}}
    (dest/'conversion.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt

def validate(id1):
    dest=Path(id1)/'world';receipt=json.loads((dest/'conversion.json').read_text())
    expected=set(WORLD_UI_FILES)
    if receipt.get('format')!='AmiWind world UI 1' or set(receipt.get('files',{}))!=expected:
        raise ValueError('Incomplete world/journal conversion receipt')
    if receipt['palette_sha256']!=hashlib.sha256((Path(id1)/'gfx/palette.lmp').read_bytes()).hexdigest():
        raise ValueError('World map palette is stale; regenerate world UI assets')
    for name,digest in receipt['files'].items():
        if hashlib.sha256((dest/name).read_bytes()).hexdigest()!=digest:raise ValueError('World UI hash mismatch: '+name)
    return receipt


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-files',type=Path,required=True);p.add_argument('--survey',type=Path,help='Reuse a complete survey; absent builds only the overview');p.add_argument('--scene',type=Path,required=True)
    a=p.parse_args();prepare(a.data_files,a.survey,a.scene)
    print(json.dumps(validate(a.scene/'id1'),indent=2))
