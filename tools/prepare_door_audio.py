#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Resolve authored DOOR sound IDs and SOUN files for every converted door, and the table of ordinary hinged doors.

door-sounds.txt (AWSFX2) lists every load door of the game data (a placed DOOR reference with a destination) and the
opening scene's placed-reference links (the Census hall door), each with its DOOR record's opening and closing sound
(SNAM/ANAM -> SOUN). It covers every form a converted door takes: room maps, CHIM rooms, CHIM frames and town
interiors all name their doors by the game's reference number, and that is the catalogue's key.

AW-20260928-10: the catalogue was made from the opening scene's links only (id1/scene-doors*.txt), so it held the
28 Seyda Neen and prison ship doors and none of the door banks the room and town stages write (doors-<room>.txt,
the CHIM towns' door banks, which are written after this stage); every Balmora door was silent. AWSFX1 (one row per
reference, at most 256 rows) could not hold every door: AWSFX2 stores each sound pair once and one short row per
door reference (engine/aga/src/aw_door_audio.c reads both).

hinged-doors.txt (AWHD1, AW-20260928-12): every placed DOOR reference of Morrowind.esm without a destination
(DODT), the doors the engine turns on the use key (engine/aga/src/aw_hinged_door.c):
  W <doors/d<16 hex>.wav> <volume> <seconds>    converted samples (the same names as door-sounds.txt)
  B <open W or -1> <close W or -1> <name>       DOOR records: Open Sound (SNAM), Close Sound (ANAM), FNAM
  D <reference> <B> <lock level> <flags>        placed doors, references ascending
  L <W>                                         the locked sound (SOUN "LockedDoor", OpenMW Door::activate)
flags: 1 locked (a lock level above 0 or a key: OpenMW components/esm3/cellref.cpp for content files), 2 key
(KNAM), 4 trap (TNAM), 8 the DOOR record has a script. The census hall door keeps its story rule in the engine.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from mwad.audit import BSA,records,subrecords,string,cell_data
from mwad.paths import resolve_data_files,child_ci,ensure_external
from npc_geometry import Assets
from prepare_intro import voice_convert

HINGED_FORMAT='AWHD1'
# The engine's bounds (aw_hinged_door.c HD_ROWS, HD_BASES, HD_SOUNDS, HD_NAME - 1).
HINGED_ROWS,HINGED_BASES,HINGED_SOUNDS,HINGED_NAME=2048,256,64,31
LOCKED,KEY,TRAP,SCRIPT=1,2,4,8
LOCKED_SOUND='lockeddoor'


MAX_PAIRS = 64      # engine/aga/src/aw_door_audio.c AW_DOOR_PAIRS
MAX_REFERENCES = 8192   # AW_DOOR_REFS


def catalogue(raw, wanted, load_doors=True):
    """[{reference, base, sounds}] by reference: the WANTED references that are doors, and with LOAD_DOORS every
    placed door with a destination (a load door) as well."""
    doors={};sounds={};cells=[]
    for tag,_,payload in records(raw):
        if tag not in ('DOOR','SOUN','CELL'):continue
        parts=list(subrecords(payload));s=dict(parts)
        # a CELL's own DELE comes before its first reference; a deleted reference's DELE does not delete the cell
        head=parts[:next((i for i,(t,_) in enumerate(parts) if t=='FRMR'),len(parts))] if tag=='CELL' else parts
        if any(t=='DELE' for t,_ in head):continue
        if tag=='DOOR':doors[string(s['NAME']).casefold()]=[string(s.get(k,b'')).casefold() for k in ('SNAM','ANAM')]
        elif tag=='SOUN':sounds[string(s['NAME']).casefold()]={'source':string(s['FNAM']),'volume':s['DATA'][0]/255}
        else:cells.append(cell_data(parts))
    out={}
    for cell in cells:
        for ref in cell['refs']:
            if ref.get('deleted') or not (ref['number'] in wanted or (load_doors and 'destination' in ref)):continue
            ids=doors.get(ref['id'].casefold())
            if ids is None or ref['number'] in out:continue
            row={'reference':ref['number'],'base':ref['id'],'sounds':[]}
            for identifier in ids:
                if identifier and identifier not in sounds:raise ValueError('Missing authored door sound '+identifier)
                row['sounds'].append(dict(id=identifier,**sounds[identifier]) if identifier else None)
            out[ref['number']]=row
    return [out[number] for number in sorted(out)]


def scene_links(scene):
    """References of the opening scene's placed-reference links (id1/scene-doors*.txt, AWD3)."""
    wanted=set()
    for p in sorted((scene/'id1').glob('scene-doors*.txt')):
        lines=p.read_text(encoding='cp1252').splitlines()
        if not lines or lines[0]!='AWD3':raise ValueError('Door audio needs placed-reference AWD3 links')
        wanted.update(int(line.split()[2]) for line in lines[1:] if line.strip())
    return wanted


def table(rows, converted):
    """The AWSFX2 lines of ROWS: each distinct sound pair once ('p' rows, in first-use order), then one
    '<reference> <pair>' row per door, ascending. CONVERTED: {source: {'path', 'seconds'}}."""
    pairs={};lines=['AWSFX2'];body=[]
    for row in rows:
        names=[];volumes=[];durations=[]
        for sound in row['sounds']:
            if sound is None:names.append('-');volumes.append(0);durations.append(0);continue
            entry=converted[sound['source'].replace('\\','/').casefold()]
            names.append(entry['path']);volumes.append(sound['volume']);durations.append(entry['seconds'])
        text=' '.join(names)+' '+' '.join(f'{v:.6f}' for v in (*volumes,*durations))
        if text not in pairs:
            pairs[text]=len(pairs);lines.append('p '+text)
        body.append(f"{row['reference']} {pairs[text]}")
    if len(pairs)>MAX_PAIRS:raise ValueError(f'Door sound pairs exceed the runtime bound ({len(pairs)} > {MAX_PAIRS})')
    return lines+body


def hinged_catalogue(raw):
    """(bases, rows, sounds): the DOOR records placed without a destination and their placed references.

    bases: {door id (casefolded): {'id','name','open','close','script'}}; rows: [{'reference','base','lock','key',
    'trap','cell'}] ascending; sounds: {sound id (casefolded): {'id','source','volume'}}. The lock data are the
    reference's own FLTV (lock level), KNAM (key) and TNAM (trap) subrecords."""
    doors={};sounds={};refs=[]
    for tag,_,payload in records(raw):
        if tag not in ('DOOR','SOUN','CELL'):continue
        parts=list(subrecords(payload));s=dict(parts)
        if tag!='CELL' and 'DELE' in s:continue
        if tag=='DOOR':
            doors[string(s['NAME']).casefold()]={'id':string(s['NAME']),'name':string(s.get('FNAM',b'')),
                'open':string(s.get('SNAM',b'')).casefold(),'close':string(s.get('ANAM',b'')).casefold(),
                'script':bool(string(s.get('SCRI',b'')))}
        elif tag=='SOUN':
            sounds[string(s['NAME']).casefold()]={'id':string(s['NAME']),'source':string(s['FNAM']),'volume':s['DATA'][0]/255}
        else:
            cell=None;ref=None
            for t,data in parts:
                if t=='NAME' and ref is None and cell is None:cell=string(data)
                elif t=='FRMR':
                    ref={'number':struct.unpack('<I',data)[0],'cell':cell or ''};refs.append(ref)
                elif ref is None:continue
                elif t=='NAME':ref['id']=string(data)
                elif t=='DODT':ref['destination']=True
                elif t=='DELE':ref['deleted']=True
                elif t=='FLTV':ref['lock']=struct.unpack('<i',data[:4])[0]
                elif t=='KNAM':ref['key']=string(data)
                elif t=='TNAM':ref['trap']=string(data)
    rows=[];used={}
    for ref in refs:
        base=doors.get(ref.get('id','').casefold())
        if base is None or ref.get('deleted') or ref.get('destination'):continue
        lock=max(0,ref.get('lock',0))
        if lock>255:raise ValueError('Lock level above 255: reference %d' % ref['number'])
        rows.append({'reference':ref['number'],'base':base['id'],'lock':lock,'key':ref.get('key',''),
                     'trap':ref.get('trap',''),'cell':ref['cell']})
        used[base['id'].casefold()]=base
    rows.sort(key=lambda r:r['reference'])
    if any(a['reference']==b['reference'] for a,b in zip(rows,rows[1:])):raise ValueError('Duplicate hinged door reference')
    for base in used.values():
        for identifier in (base['open'],base['close']):
            if identifier and identifier not in sounds:raise ValueError('Missing authored door sound '+identifier)
    return used,rows,sounds


def flags(row,base):
    return (LOCKED if row['lock']>0 or row['key'] else 0)|(KEY if row['key'] else 0)|(TRAP if row['trap'] else 0)|\
        (SCRIPT if base['script'] else 0)


def safe_name(text):
    out=''.join(c if 32<=ord(c)<127 else '?' for c in text).strip()
    return out[:HINGED_NAME]


def hinged_text(bases,rows,sounds,sample):
    """The AWHD1 table. sample(source) -> (path, seconds) converts (or reuses) one SOUN file."""
    samples=[];index={}
    def w(identifier):
        if not identifier:return -1
        sound=sounds[identifier]
        if identifier not in index:
            path,seconds=sample(sound['source'])
            index[identifier]=len(samples);samples.append((path,sound['volume'],seconds))
        return index[identifier]
    order=sorted(bases)
    base_rows=[(w(bases[k]['open']),w(bases[k]['close']),safe_name(bases[k]['name'])) for k in order]
    locked=w(LOCKED_SOUND) if LOCKED_SOUND in sounds else -1
    if len(rows)>HINGED_ROWS or len(order)>HINGED_BASES or len(samples)>HINGED_SOUNDS:
        raise ValueError('Hinged door table exceeds the runtime bounds (%d rows, %d bases, %d samples)'
                         % (len(rows),len(order),len(samples)))
    number={k:i for i,k in enumerate(order)}
    lines=[HINGED_FORMAT]
    lines+=['W %s %.6f %.6f' % s for s in samples]
    lines+=[('B %d %d %s' % b).rstrip() for b in base_rows]
    lines+=['D %d %d %d %d' % (r['reference'],number[r['base'].casefold()],r['lock'],flags(r,bases[r['base'].casefold()]))
            for r in rows]
    if locked>=0:lines.append('L %d' % locked)
    return '\n'.join(lines)+'\n'


def sample_name(source):
    """The converted sample's name: doors/d + 16 hex of the source path (shared by both tables)."""
    return 'doors/d'+hashlib.sha256(source.replace('\\','/').casefold().encode()).hexdigest()[:16]+'.wav'


def prepare(data,scene,ffmpeg='ffmpeg'):
    data=resolve_data_files(data);scene=ensure_external(scene,'door audio')
    from mwad.paths import unshare_tree
    unshare_tree(scene)  # in place: BUILD-POOL-READONLY-SCENE-WRITE-35
    wanted={172860}|scene_links(scene)   # the Census hall door (a story door, no destination) and the scene's links
    raw=child_ci(data,'Morrowind.esm').read_bytes()
    rows=catalogue(raw,wanted)
    if len(rows)>MAX_REFERENCES:raise ValueError(f'Door sound catalogue exceeds the runtime bound ({len(rows)} > {MAX_REFERENCES})')
    assets=Assets(data,BSA(child_ci(data,'Morrowind.bsa')));converted={}
    def sample(original):
        """Convert one SOUN file once (both tables share the converted samples); -> (path, seconds)."""
        source=original.replace('\\','/').casefold();name=sample_name(original)
        if source not in converted:
            receipt=voice_convert(assets,original,scene/'id1/sound'/name,ffmpeg,speech=False)
            converted[source]=dict(receipt,path=name)
        return name,converted[source]['seconds']
    for row in rows:
        for sound in row['sounds']:
            if sound is not None:sample(sound['source'])
    lines=table(rows,converted)
    (scene/'id1/door-sounds.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    bases,hinged,sounds=hinged_catalogue(raw)
    (scene/'id1/hinged-doors.txt').write_text(hinged_text(bases,hinged,sounds,sample),encoding='ascii',newline='\n')
    pairs=sum(1 for line in lines if line.startswith('p '))
    report={'doors':rows,'files':list(converted.values()),'format':'AWSFX2','pairs':pairs,
            'load_doors':sum(1 for row in rows if row['reference'] not in wanted),'scene_links':sorted(wanted),
            'runtime':'11025 Hz mono unsigned PCM; source SOUN volume',
            'hinged':{'format':HINGED_FORMAT,'doors':len(hinged),'records':len(bases),
                      'locked':sum(1 for r in hinged if flags(r,bases[r['base'].casefold()])&LOCKED),
                      'key':sum(1 for r in hinged if r['key']),'trap':sum(1 for r in hinged if r['trap']),
                      'unlocked_trapped':sum(1 for r in hinged if r['trap'] and not flags(r,bases[r['base'].casefold()])&LOCKED),
                      'scripted':sum(1 for r in hinged if bases[r['base'].casefold()]['script'])}}
    (scene/'door-audio.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n');return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--data-files',type=Path,required=True);p.add_argument('--scene',type=Path,required=True);p.add_argument('--ffmpeg',default='ffmpeg')
    a=p.parse_args();r=prepare(a.data_files,a.scene,a.ffmpeg)
    print('Door audio:',len(r['doors']),'doors,',r['pairs'],'sound pairs,',len(r['files']),'unique samples;',r['hinged']['doors'],'hinged doors')
