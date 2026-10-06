#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Report source inventory and evidence-backed conversion/image progress.

Counts are paths, not placed objects. Unmapped conversion coverage stays unknown.
Game-derived reports belong outside the public source repository.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from mwad.audit import BSA
from mwad.paths import child_ci, ensure_external, resolve_data_files

CATEGORIES=('voices','effects','music','videos','meshes','animations','textures','icons','fonts','other')

def canonical(value):
    return str(value).replace('\\','/').casefold()

def category(path):
    path=canonical(path);suffix=Path(path).suffix
    if path.startswith('sound/vo/') and suffix in ('.mp3','.wav','.ogg','.flac'):return 'voices'
    if path.startswith('sound/') and suffix in ('.mp3','.wav','.ogg','.flac'):return 'effects'
    if path.startswith('music/') and suffix in ('.mp3','.wav','.ogg','.flac'):return 'music'
    if path.startswith('video/') and suffix in ('.bik','.avi','.mp4'):return 'videos'
    if suffix=='.nif':return 'meshes'
    if suffix=='.kf':return 'animations'
    if path.startswith('icons/'):return 'icons'
    if path.startswith('fonts/'):return 'fonts'
    if path.startswith('textures/'):return 'textures'
    return 'other'

def inventory(data):
    """TES3 archive order plus loose overrides; exclude archive/master containers."""
    assets={};archives=[];seen=set()
    for name in ('Morrowind.bsa','Tribunal.bsa','Bloodmoon.bsa'):
        p=child_ci(data,name,required=False)
        if p is None:continue
        bsa=BSA(p);archives.append({'name':name,'entries':len(bsa.entries)})
        for name,record in bsa.entries.items():assets[canonical(name)]=record['bytes']
    for path in sorted(p for p in data.rglob('*') if p.is_file()):
        relative=canonical(path.relative_to(data).as_posix())
        if '/' not in relative and path.suffix.casefold() in ('.bsa','.esm','.esp'):continue
        if relative in seen:raise ValueError('Case-ambiguous loose asset path: '+relative)
        seen.add(relative);assets[relative]=path.stat().st_size
    return assets,archives

def checked_image(readback):
    files={}
    for partition in readback:
        if partition.get('readback')!='passed':raise ValueError('Image readback has not passed')
        for entry in partition['files']:
            path=canonical(entry['path'])
            if path in files and files[path]!=entry:raise ValueError('Conflicting duplicate image path: '+path)
            files[path]=entry
    return files

def report(assets,media,image):
    totals=Counter(category(p) for p in assets)
    rows={name:{'category':name,'source_paths':totals[name],
               'converted_sources':None,'current_input_verified_sources':None,
               'same_output_in_image':None,
               'missing_referenced_sources':None,'failed_outputs':None,
               'runtime_accepted_sources':None} for name in CATEGORIES}
    media_seen=set();media_groups={name:[] for name in ('voices','effects','music','videos')}
    for entry in media['entries']:
        source=canonical(entry['source'])
        if source in media_seen:raise ValueError('Duplicate media source row: '+source)
        media_seen.add(source)
        if entry['category'] not in media_groups:raise ValueError('Unexpected media category')
        if entry['category']!=category(source):raise ValueError('Media category differs from source path: '+source)
        if entry['status']=='included' and source not in assets:raise ValueError('Included source absent from inventory: '+source)
        media_groups[entry['category']].append(entry)
    for name,entries in media_groups.items():
        converted=[e for e in entries if e['status']=='included']
        identical=0
        for entry in converted:
            target=image.get(canonical('id1/'+entry['path']))
            if target and target['sha256']==entry['sha256'] and target['bytes']==entry['bytes']:identical+=1
        rows[name].update(converted_sources=len(converted),same_output_in_image=identical,
                         missing_referenced_sources=media['categories'][name]['missing_source'],
                         failed_outputs=media['categories'][name]['missing_output'])
    artifacts=Counter(Path(name).suffix or '(none)' for name in image)
    return {'schema':'AW-ASSET-PROGRESS1','unit':'unique canonical source paths; not object placements',
            'rows':list(rows.values()),'source_paths_total':len(assets),
            'conversion_evidence_scope':'supplied_media_report',
            'current_input_verification':'not_checked',
            'image_artifact_count':len(image),'image_artifacts_by_extension':dict(sorted(artifacts.items())),
            'limits':['Unknown means no complete source-to-converted provenance was supplied; it is not zero.',
              'Recorded conversions and missing/failed counts describe the supplied media batch; zero means no such rows recorded in that batch.',
              'Current selected source bytes are not rehashed. A recorded source hash or matching path does not verify that the current input is unchanged; current-input verification stays unknown.',
              'Image column counts byte-identical outputs from this media batch, not all older or alternate conversions.',
              'Artifact counts and source paths are different units; no overall imported percentage is claimed.',
              'Runtime event coverage requires separate measured acceptance; conversion and readback do not prove it.']}

def markdown(result):
    lines=['# Asset progress','',result['unit']+'.','',
           '| Category | Source paths | Recorded converted | Current input verified | Same output in image | Missing references | Failed outputs | Runtime accepted |',
           '|---|---:|---:|---:|---:|---:|---:|---:|']
    def value(v):return 'unknown' if v is None else f'{v:,}'
    for row in result['rows']:
        lines.append('| '+row['category']+' | '+' | '.join(value(row[k]) for k in
          ('source_paths','converted_sources','current_input_verified_sources','same_output_in_image','missing_referenced_sources','failed_outputs','runtime_accepted_sources'))+' |')
    lines+=['','## Image artifact inventory','', '| Extension | Files |','|---|---:|']
    lines += [f'| `{extension}` | {count:,} |' for extension,count in result['image_artifacts_by_extension'].items()]
    lines+=['','## Interpretation','']+['- '+s for s in result['limits']]
    return '\n'.join(lines)+'\n'

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-files',type=Path,required=True)
    p.add_argument('--media-report',type=Path,required=True)
    p.add_argument('--image-readback',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args();out=ensure_external(args.out,'private asset progress');out.mkdir(parents=True,exist_ok=False)
    assets,archives=inventory(resolve_data_files(args.data_files))
    media=json.loads(args.media_report.read_text());image=checked_image(json.loads(args.image_readback.read_text()))
    result=report(assets,media,image);result['archives']=archives
    result['input_reports']={name:hashlib.sha256(path.read_bytes()).hexdigest() for name,path in
                            [('media',args.media_report),('image_readback',args.image_readback)]}
    (out/'progress.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    (out/'progress.md').write_text(markdown(result),encoding='utf-8')
    print(markdown(result))

if __name__=='__main__':main()
