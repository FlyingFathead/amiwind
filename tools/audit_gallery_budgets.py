#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Find oversized gallery conversions and emit byte-specific model allowances.

Normal models retain the original budget. Optional retries preserve the existing
shell/extent protection and use only the tested 777-triangle ceiling. Cases
beyond it remain explicit failures, never progressively crushed to get green.
All reports and converted assets stay in the owner's private build directory.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
import zlib
from build_jobs import add_jobs
from build_parallel import ordered_map
from prepare_gallery import catalogue, convert_model, finish_catalogue
from mwad.paths import ensure_external


def model_allowance(key, raw, receipt):
    if len(raw)<84 or raw[:8]!=b'IDPO\x06\0\0\0':raise ValueError('Invalid model header')
    vertices,triangles=struct.unpack_from('<ii',raw,60)
    digest=hashlib.sha256(raw).hexdigest()
    if digest!=receipt.get('sha256'):raise ValueError('Model bytes differ from conversion receipt')
    if vertices<=2000:return None
    if vertices>2331 or triangles>777:raise ValueError('Beyond tested renderer ceiling')
    return dict(model='gallery/'+key+'.mdl',vertices=vertices,triangles=triangles,
                bytes=len(raw),crc32=f'{zlib.crc32(raw):08x}',sha256=digest,
                reason='Normal conversion exceeds the alias budget while retaining protected geometry.',
                visual_review='unreviewed')


def write_allowances(directory, results, entries, output):
    directory=Path(directory);exceptions=[];unresolved=[]
    for key,result in sorted(results.items()):
        owners=[dict(number=e['number'],source_id=e['id'],name=e['name']) for e in entries if key in e['models']]
        if result.get('status')!='ready':
            unresolved.append(dict(model=key,error=result.get('error','No successful conversion'),records=owners));continue
        try:exception=model_allowance(key,(directory/(key+'.mdl')).read_bytes(),result)
        except (ValueError,OSError) as exc:
            unresolved.append(dict(model=key,error=str(exc),records=owners));continue
        if exception:exception['records']=owners;exceptions.append(exception)
    Path(output).write_text('AWPB1\n'+''.join(f"{e['model']} {e['vertices']} {e['triangles']} {e['bytes']} {e['crc32']}\n" for e in exceptions))
    return dict(format=1,normal_vertex_limit=2000,trial_triangle_ceiling=777,
                exceptions=exceptions,unresolved=unresolved)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-files',type=Path,required=True);p.add_argument('--gallery',type=Path,required=True)
    p.add_argument('--palette',type=Path,required=True);p.add_argument('--retry',action='store_true');add_jobs(p)
    a=p.parse_args();out=ensure_external(a.gallery,'gallery');directory=out/'gallery'
    entries,specs=catalogue(a.data_files);results={};tasks=[];palette=a.palette.read_bytes()
    for key,spec in specs.items():
        path=directory/(key+'.json')
        result=json.loads(path.read_text()) if path.is_file() else dict(key=key,status='failed',error='Missing receipt')
        results[key]=result
        if a.retry and result.get('status')!='ready' and 'Alias' in result.get('error',''):
            tasks.append((str(a.data_files),str(directory),key,dict(spec,face_limit=777),palette))
    print(f'{len(tasks)} oversized models to retry; ordinary models retained.',flush=True)
    for result in ordered_map(convert_model,tasks,a.jobs):
        results[result['key']]=result
        print(result['key'],result['status'],result.get('triangles'),result.get('error',''),flush=True)
    report=write_allowances(directory,results,entries,out/'model-budgets.txt')
    (out/'model-budget-audit.json').write_text(json.dumps(report,indent=2)+'\n')
    finish_catalogue(entries,results,out,palette)
    print(f"{len(report['exceptions'])} explicit exceptions; {len(report['unresolved'])} unresolved models.",flush=True)
    if report['unresolved']:return 2
    return 0


if __name__=='__main__':sys.exit(main())
